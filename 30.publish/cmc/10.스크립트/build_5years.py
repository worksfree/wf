"""
build_5years.py — 5개년 통합 파일 생성 스크립트
  36-40회_경영지도사_생산관리분야_예시답안.md

사용법:
    python 10.스크립트/build_5years.py

동작:
1. 기존 통합 파일에서 헤더(1~207행)와 푸터(마지막 <div class="page"></div> 이후) 추출
2. 각 회차 개별 파일에서 본문 추출 후 변환:
   - <!-- SRC:*.md --> 행 제거
   - 헤딩 레벨 상향 (# → ##, ## → ###, ### → ####, #### → #####)
   - 해당 위치에 <a id> 앵커 삽입
   - 개별 파일 목차 앵커(#{N}회-{subject}-목차) → 통합 앵커(#{N}회-{subject}) 치환
3. 회차 간 더블 페이지 구분자 삽입
4. 통합 파일 출력
"""

import re
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDIVIDUAL_DIR = os.path.join(BASE, "40.출판물")
OUTPUT_DIR = os.path.join(BASE, "40.출판물")
EXISTING_UNIFIED = os.path.join(OUTPUT_DIR, "36-40회_경영지도사_생산관리분야_예시답안.md")
OUTPUT_FILE = EXISTING_UNIFIED

SESSIONS = [36, 37, 38, 39, 40]
SUBJECTS = ["생산관리", "품질경영", "경영과학"]


def heading_to_anchor(text: str) -> str:
    return text.strip().replace(" ", "-")


def h1_section_anchor(text: str) -> str | None:
    if text.endswith(" 문제"):
        base = text[: -len(" 문제")]
        return base.replace(" ", "-")
    return None


def process_body_lines(lines: list[str], session: int) -> list[str]:
    out = []
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if re.match(r"<!-- /?SRC:.+\.md -->", stripped):
            continue

        if line.startswith("#### "):
            out.append("##### " + line[5:])
            continue
        if line.startswith("### "):
            out.append("#### " + line[4:])
            continue
        if line.startswith("## ") and not line.startswith("## #"):
            heading_text = line[3:]
            anchor_id = heading_to_anchor(heading_text)
            out.append(f'<a id="{anchor_id}"></a>')
            out.append("### " + heading_text)
            continue
        if line.startswith("# ") and not line.startswith("## "):
            heading_text = line[2:]
            anchor_id = h1_section_anchor(heading_text)
            if anchor_id:
                out.append(f'<a id="{anchor_id}"></a>')
            out.append("## " + heading_text)
            continue

        for subj in SUBJECTS:
            old = f"#{session}회-{subj}-목차"
            new = f"#{session}회-{subj}"
            line = line.replace(old, new)

        out.append(line)

    return out


def extract_individual_body(filepath: str) -> list[str]:
    with open(filepath, encoding="utf-8") as f:
        all_lines = f.readlines()

    body_start = None
    body_end = None
    for i, line in enumerate(all_lines):
        if body_start is None and re.match(r"^# \d+회 ", line):
            body_start = i
        if line.strip().startswith('<table style="border:none"'):
            body_end = i
            break

    if body_start is None or body_end is None:
        raise ValueError(f"본문 범위를 찾지 못했습니다: {filepath}")

    lines = all_lines[body_start:body_end]

    # 말미 trailing page break 제거 (double_break와 중복되어 공백 2페이지 발생 방지)
    while lines and lines[-1].strip() in ("", '<div class="page"></div>'):
        lines.pop()

    return lines


def extract_header_footer(filepath: str):
    with open(filepath, encoding="utf-8") as f:
        all_lines = f.readlines()

    header_end = None
    for i, line in enumerate(all_lines):
        if '<a id="36회-생산관리">' in line:
            header_end = i
            break
    if header_end is None:
        raise ValueError("헤더 끝을 찾지 못했습니다.")

    header = all_lines[:header_end]

    footer_start = None
    for i in range(len(all_lines) - 1, -1, -1):
        if all_lines[i].strip() == '<div class="page"></div>':
            footer_start = i
            break
    if footer_start is None:
        raise ValueError("푸터 시작을 찾지 못했습니다.")

    footer = all_lines[footer_start:]
    return header, footer


def main():
    header, footer = extract_header_footer(EXISTING_UNIFIED)

    body_parts = []
    for n in SESSIONS:
        fname = f"{n}회_경영지도사_생산관리분야_예시답안.md"
        fpath = os.path.join(INDIVIDUAL_DIR, fname)
        raw_lines = extract_individual_body(fpath)
        processed = process_body_lines(raw_lines, n)
        body_parts.append(processed)
        print(f"  {n}회 처리 완료: {len(raw_lines)} → {len(processed)} 행")

    out_lines = list(header)
    # 회차 간 page break: trailing page break는 extract_individual_body에서 이미 제거했으므로
    # 1개만 삽입 → 0개 blank page (연속 2개면 빈 페이지 1개, 3개면 2개 발생)
    double_break = ["\n", '<div class="page"></div>\n', "\n"]

    for i, part in enumerate(body_parts):
        for line in part:
            out_lines.append(line + "\n" if not line.endswith("\n") else line)
        if i < len(body_parts) - 1:
            out_lines.extend(double_break)

    out_lines.extend(footer)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    print(f"\n통합 파일 생성 완료: {OUTPUT_FILE}")
    print(f"총 {len(out_lines)} 행")


if __name__ == "__main__":
    main()
