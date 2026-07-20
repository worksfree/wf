# -*- coding: utf-8 -*-
"""Claude API로 각 카드의 '보고서 전용 상세 정보'(report_detail)를 생성한다.

카드 상세보기(더보기)는 건드리지 않고, 보고서에서만 사용하는 필드를 새로 추가한다.
- documents: 신청 시 필요서류 목록 (원문에서 확인 가능한 만큼)
- agency: 소관/신청 기관
- period: 처리기간·소요기간
- cautions: 유의사항 (중복적용 제한, 사후관리 등)
- next_steps: 실행 체크리스트 (2~4단계)

원문 텍스트(extracted/*.txt)에서 source 필드가 가리키는 절을 최대한 찾아 근거로 제공하고,
찾지 못하면 카드의 기존 필드(target/benefit/how/when)만으로 생성하되 과도한 추정을 피하도록 지시한다.
API 키는 secrets/.env 에서만 읽는다 (git 추적 금지 폴더).
"""
import json
import os
import re
import sys
import io
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
CARDS_DIR = BASE / "cards"
EXTRACTED_DIR = BASE / "extracted"
ENV_PATH = BASE / "secrets" / ".env"

MODEL = "claude-opus-4-8"

SCHEMA = {
    "type": "object",
    "properties": {
        "documents": {"type": "array", "items": {"type": "string"}, "description": "신청 시 필요서류 목록 (한국어, 짧은 항목 3~7개)"},
        "agency": {"type": "string", "description": "소관·신청 기관명 및 가능하면 접수 경로(사이트/전화)"},
        "period": {"type": "string", "description": "처리기간 또는 소요기간 (예: '접수 후 30일 이내')"},
        "cautions": {"type": "array", "items": {"type": "string"}, "description": "유의사항 2~4개 (중복적용 제한, 사후관리 추징, 신청기한 등)"},
        "next_steps": {"type": "array", "items": {"type": "string"}, "description": "신청 실행 체크리스트 2~4단계 (동사로 시작하는 짧은 문장)"},
    },
    "required": ["documents", "agency", "period", "cautions", "next_steps"],
    "additionalProperties": False,
}

SYSTEM = """당신은 한국 중소기업 지원제도 전문 컨설턴트입니다.
주어진 지원제도 카드 정보와 (있다면) 원문 발췌를 바탕으로, 신청 실무에 필요한 상세 정보를 구조화해 작성하세요.

규칙:
- 원문 발췌에 명시된 내용은 그대로 반영하고, 없는 내용은 일반적으로 통용되는 절차(사업자등록증, 관할 세무서/기관 신청 등) 수준에서만 채우되 구체적 수치·서식명을 지어내지 마세요.
- 확실하지 않은 사항은 cautions에 "정확한 요건은 최신 공고 확인 필요"처럼 명시하세요.
- 모든 문장은 한국어, 간결하게 작성하세요."""


def load_env():
    if not ENV_PATH.exists():
        raise SystemExit(f"환경변수 파일 없음: {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def find_source_text(source: str) -> str:
    """source 필드에서 파일명+섹션코드를 추출해 원문 발췌를 찾는다. 실패 시 빈 문자열."""
    m = re.match(r"^(.*?\.(?:pdf|pptx))\s*(?:\(([^)]+)\))?", source)
    if not m:
        return ""
    fname, section = m.group(1).strip(), (m.group(2) or "").strip()
    stem = fname.rsplit(".", 1)[0]
    candidates = list(EXTRACTED_DIR.glob(f"{stem}*.txt"))
    if not candidates:
        # 부분 일치로 재시도 (파일명이 살짝 다를 수 있음)
        for f in EXTRACTED_DIR.glob("*.txt"):
            if stem[:12] in f.stem:
                candidates = [f]
                break
    if not candidates:
        return ""
    text = candidates[0].read_text(encoding="utf-8", errors="ignore")

    sec_match = re.match(r"^(\d+)-(\d+)$", section)
    if not sec_match:
        return text[:4000]  # 섹션 특정 불가 — 앞부분만 (짧은 문서는 전체 커버)

    code = section
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^{re.escape(code)}[.\s]", ln.strip()):
            start = i
            break
    if start is None:
        return text[:4000]
    end = len(lines)
    for i in range(start + 1, min(start + 400, len(lines))):
        if re.match(r"^\d+-\d+[.\s]", lines[i].strip()) or re.match(r"^\d+-\d+\s", lines[i].strip()):
            end = i
            break
    snippet = "\n".join(lines[start:end])
    return snippet[:6000]


def generate_one(client, card: dict) -> dict:
    src_text = find_source_text(card.get("source", ""))
    user_content = f"""[카드 정보]
제도명: {card['name']}
대상: {card['target']}
혜택: {card['benefit']}
방법: {card['how']}
시기: {card['when']}
출처: {card['source']}

[원문 발췌]
{src_text if src_text else "(발췌 없음 — 카드 정보만으로 일반적 수준에서 작성)"}
"""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def main():
    load_env()
    import anthropic
    client = anthropic.Anthropic()

    force = "--force" in sys.argv
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)

    total = 0
    for f in sorted(CARDS_DIR.glob("*.json")):
        cards = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for c in cards:
            if only and c["id"] != only:
                continue
            if c.get("report_detail") and not force:
                continue
            print(f"생성 중: {c['id']}  {c['name']}")
            try:
                detail = generate_one(client, c)
                c["report_detail"] = detail
                changed = True
                total += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  실패: {e}")
        if changed:
            f.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료: {total}개 카드 report_detail 생성")


if __name__ == "__main__":
    main()
