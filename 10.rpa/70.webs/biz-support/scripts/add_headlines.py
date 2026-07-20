# -*- coding: utf-8 -*-
"""카드에 헤드라인 수치 배지(headline)를 주입한다.

원문에서 확인된 수치가 있는 카드만 대상 — 근거 없는 수치 생성 금지.
value(큰 숫자) / label(수치의 의미) / note(조건 한정어)
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CARDS_DIR = Path(__file__).resolve().parent.parent / "cards"

HEADLINES = {
    # 조세지원
    "tax-01": {"value": "최대 100%", "label": "법인세 감면", "note": "5년간 · 청년/수도권 밖 창업"},
    "tax-02": {"value": "5~30%", "label": "법인세 감면", "note": "매년 · 업종/지역/규모별"},
    "tax-03": {"value": "연 600만원", "label": "소득공제 한도", "note": "소득 4천만원 이하 기준"},
    "tax-04": {"value": "10%+", "label": "투자액 세액공제", "note": "중소기업 기본 · 증가분 +10%"},
    "tax-05": {"value": "25~40%", "label": "R&D비용 세액공제", "note": "중소기업 · 기술유형별"},
    "tax-06": {"value": "취득세 50%", "label": "경감 + 양도세 이월", "note": "법인전환 시"},
    "tax-07": {"value": "최대 2,000만원", "label": "고용증가 인당 공제", "note": "청년 등 · 3년 누적"},
    "tax-09": {"value": "소득세 90%", "label": "감면 (청년 5년)", "note": "연 200만원 한도"},
    # 고용지원금
    "emp-01": {"value": "720만원", "label": "청년 채용 인당 지원", "note": "1년간 · 월 60만원"},
    "emp-02": {"value": "부담금 10%", "label": "퇴직연금 지원", "note": "3년간 · 인당 최대 80.4만원"},
    "emp-03": {"value": "최대 1,440만원", "label": "취약계층 채용 인당", "note": "특정대상 2년 기준"},
    "emp-04": {"value": "360만원", "label": "근로시간 단축 인당", "note": "1년간 · 월 30만원"},
    "emp-05": {"value": "최대 600만원", "label": "단축근무 허용 인당", "note": "1년간"},
    "emp-06": {"value": "최대 990만원", "label": "육아휴직 허용 인당", "note": "1년 기준"},
    "emp-07": {"value": "최대 720만원", "label": "육아기 단축 인당", "note": "1년간 · 30인 미만"},
    "emp-08": {"value": "월 140만원", "label": "대체인력 인건비", "note": "30인 미만 사업장"},
    # R&D·인증
    "rnd-01": {"value": "연구원 2~3명", "label": "설립 인적요건", "note": "벤처 2명 · 소기업 3명"},
    "rnd-02": {"value": "법인세 50%", "label": "창업벤처 감면 (5년)", "note": "+ 보증·특허·가점 다수"},
    "rnd-03": {"value": "보증 50억", "label": "기보 한도 우대", "note": "+ 세제/입지/인력/광고"},
    # 법인운영·승계
    "corp-03": {"value": "연 4.6%", "label": "인정이자 (방치 비용)", "note": "특허권 상환 시 60% 경비 인정"},
    # 정책자금
    "prg-01": {"value": "연 60억원", "label": "융자 한도", "note": "청년전용 연 2.5% 고정"},
    "prg-03": {"value": "긴급 운전자금", "label": "융자 지원", "note": "재해·일시적 경영애로"},
    "prg-04": {"value": "2,000만원+", "label": "5년 재직 성과보상", "note": "기업 납입금 25% 세액공제"},
    "prg-05": {"value": "최대 70%", "label": "해외마케팅 보조", "note": "매출 100억 미만 기업"},
}


def main():
    total = 0
    for f in sorted(CARDS_DIR.glob("*.json")):
        cards = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for c in cards:
            if c["id"] in HEADLINES:
                c["headline"] = HEADLINES[c["id"]]
                changed = True
                total += 1
            elif "headline" in c:
                del c["headline"]
                changed = True
        if changed:
            f.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"헤드라인 주입: {total}개 카드")


if __name__ == "__main__":
    main()
