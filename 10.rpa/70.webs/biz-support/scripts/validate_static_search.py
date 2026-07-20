# -*- coding: utf-8 -*-
"""허브 정적 페이지용 검색 알고리즘(문자 바이그램 TF-IDF 코사인 + 키워드 가점) 품질 검증.

JS로 포팅할 알고리즘과 동일한 로직을 Python으로 구현해 13문항 top-1 정확도를 확인한다.
"""
import json
import math
import re
import sys
import io
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CARDS_DIR = Path(__file__).resolve().parent.parent / "cards"


def card_text(c):
    # 제도명·목적 태그는 3배 가중 (제목 매칭 우선)
    head = " ".join([c["name"], " ".join(c.get("purpose", []))])
    return " ".join([
        head, head, head, c.get("category", ""),
        c.get("summary", ""), c.get("target", ""), c.get("benefit", ""),
    ])


def bigrams(s):
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", s.lower())
    grams = []
    for tok in s.split():
        if len(tok) == 1:
            grams.append(tok)
        for i in range(len(tok) - 1):
            grams.append(tok[i:i+2])
    return grams


def words(s):
    return [t for t in re.split(r"[^0-9a-zA-Z가-힣]+", s.lower()) if len(t) >= 2]


def build(cards):
    docs = [Counter(bigrams(card_text(c))) for c in cards]
    n = len(docs)
    df = Counter()
    for d in docs:
        for g in d:
            df[g] += 1
    idf = {g: math.log(1 + n / (1 + df[g])) for g in df}
    vecs = []
    for d in docs:
        v = {g: (1 + math.log(tf)) * idf.get(g, 0) for g, tf in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        vecs.append({g: x / norm for g, x in v.items()})
    return vecs, idf


def score(q, cards, vecs, idf):
    qtf = Counter(bigrams(q))
    qv = {g: (1 + math.log(tf)) * idf.get(g, 0.3) for g, tf in qtf.items()}
    qnorm = math.sqrt(sum(x * x for x in qv.values())) or 1
    qv = {g: x / qnorm for g, x in qv.items()}
    qwords = words(q)
    out = []
    for i, c in enumerate(cards):
        cos = sum(w * vecs[i].get(g, 0) for g, w in qv.items())
        hay = c["name"] + " " + " ".join(c.get("purpose", []))
        boost = min(sum(1 for w in qwords if w in hay) * 0.03, 0.09)
        out.append((cos + boost, c["name"]))
    out.sort(reverse=True)
    return out


QUESTIONS = [
    ("매출이 급감해서 직원을 줄여야 할 것 같아요", "고용유지지원금"),
    ("직원 5명 제조업인데 연구소를 만들려고 합니다", "기업부설연구소"),
    ("청년 직원을 새로 채용하면 받을 수 있는 지원금은?", "청년일자리도약장려금"),
    ("개인사업자인데 매출이 늘어서 법인전환을 고민중입니다", "법인전환"),
    ("자녀에게 회사를 물려주려면 어떻게 준비해야 하나요", "가업상속공제"),
    ("회사에 가수금이 많이 쌓여있는데 어떻게 정리하죠", "가수금 출자전환"),
    ("설비 투자 계획이 있는데 세금 혜택이 있나요", "통합투자세액공제"),
    ("벤처기업 인증 받으면 뭐가 좋아요", "벤처기업확인제도"),
    ("정년 지난 직원을 계속 쓰고 싶은데 지원이 있나요", "고령자 계속고용장려금"),
    ("공장을 지방으로 옮기려고 하는데요", "이전"),
    ("R&D 비용 세액공제 받으려면 뭐가 필요한가요", "연구·인력개발비"),
    ("퇴직연금 도입하고 싶은데 부담돼요", "푸른씨앗"),
    ("직원 소득세 감면해주는 제도 있죠?", "취업자에 대한 소득세"),
    ("창업자금 대출 받고 싶어요", "혁신창업사업화자금"),
    ("수출을 시작하려는데 지원 받을 수 있나요", "수출바우처"),
    ("스마트공장 만들고 싶어요", "스마트공장"),
]


def main():
    cards = []
    for f in sorted(CARDS_DIR.glob("*.json")):
        cards.extend(json.loads(f.read_text(encoding="utf-8")))
    vecs, idf = build(cards)
    hit1 = hit3 = 0
    for q, expect in QUESTIONS:
        ranked = score(q, cards, vecs, idf)
        top3 = [name for _, name in ranked[:3]]
        ok1 = expect in top3[0]
        ok3 = any(expect in n for n in top3)
        hit1 += ok1
        hit3 += ok3
        mark = "O" if ok1 else ("^" if ok3 else "X")
        print(f"[{mark}] {q}")
        for s, n in ranked[:3]:
            print(f"      {s:.3f}  {n}")
    print(f"\ntop-1: {hit1}/{len(QUESTIONS)}, top-3: {hit3}/{len(QUESTIONS)}")


if __name__ == "__main__":
    main()
