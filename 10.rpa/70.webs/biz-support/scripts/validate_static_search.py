# -*- coding: utf-8 -*-
"""허브 정적 페이지용 검색 알고리즘(문자 바이그램 TF-IDF 코사인 + 키워드 가점 + 관련도 임계값) 품질 검증.

JS(consulting/support/index.html)로 포팅한 알고리즘과 동일한 로직을 Python으로 구현해
1) top-1/top-3 정확도, 2) "무관한 카드로 8건을 억지로 채우지 않는지"(임계값 컷오프)를 함께 확인한다.
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

# 질문에서 흔히 붙는 서술어/조사 덩어리 — 제거해야 핵심 명사(가지급금, 연구소 등)의 비중이 커짐
STOPWORDS = [
    "혜택은", "혜택이", "혜택", "받을 수 있는", "받으면", "받고 싶어요", "있나요", "있죠",
    "뭐가 좋아요", "뭐가", "무엇", "어떻게", "해주는", "해야 할까요", "궁금해요",
    "싶은데", "싶어요", "싶습니다",
]

# 관련도 임계값 — top-1 대비 상대비율 / 절대 하한 / "매칭 없음" 판정선
# (파라미터 스윕으로 확정: 0.30/0.045 조합은 top-1이 낮은 질문에서 5위 밖 약한 카드까지 통과시킴)
REL_CUTOFF = 0.45
ABS_MIN = 0.07
NO_MATCH_FLOOR = 0.06
DEFAULT_TOPK = 6


def strip_stop(q: str) -> str:
    for s in STOPWORDS:
        q = q.replace(s, " ")
    return q


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


def score(q, cards, vecs, idf, apply_cutoff=True):
    q2 = strip_stop(q)
    if not words(q2):
        q2 = q  # 전부 불용어면 원문 사용
    qtf = Counter(bigrams(q2))
    qv = {g: (1 + math.log(tf)) * idf.get(g, 0.3) for g, tf in qtf.items()}
    qnorm = math.sqrt(sum(x * x for x in qv.values())) or 1
    qv = {g: x / qnorm for g, x in qv.items()}
    qwords = words(q2)
    out = []
    for i, c in enumerate(cards):
        cos = sum(w * vecs[i].get(g, 0) for g, w in qv.items())
        hay = c["name"] + " " + " ".join(c.get("purpose", []))
        hits = 0.0
        for w in qwords:
            if w in hay:
                hits += 1
            elif len(w) > 2 and w[:2] in hay:
                hits += 0.5  # 조사 제거 근사 (예: "직원을"→"직원")
        out.append((cos + min(hits * 0.03, 0.09), c["name"]))
    out.sort(reverse=True)
    if not apply_cutoff:
        return out
    top = out[0][0] if out else 0
    if top < NO_MATCH_FLOOR:
        return []
    cutoff = max(ABS_MIN, top * REL_CUTOFF)
    return [(s, n) for s, n in out if s >= cutoff][:DEFAULT_TOPK]


# (질문, 정답이 포함해야 할 키워드 — '|'로 복수 허용, "(무관련)"이면 결과가 비어야 정상)
QUESTIONS = [
    ("매출이 급감해서 직원을 줄여야 할 것 같아요", "고용유지지원금"),
    ("직원 5명 제조업인데 연구소를 만들려고 합니다", "기업부설연구소|벤처기업확인제도"),
    ("청년 직원을 새로 채용하면 받을 수 있는 지원금은?", "청년일자리도약장려금|통합고용세액공제"),
    ("개인사업자인데 매출이 늘어서 법인전환을 고민중입니다", "법인전환"),
    ("자녀에게 회사를 물려주려면 어떻게 준비해야 하나요", "가업상속공제|가업승계"),
    ("회사에 가수금이 많이 쌓여있는데 어떻게 정리하죠", "가수금 출자전환"),
    ("회사에 가지급금이 쌓여있어요", "가지급금 정리"),
    ("설비 투자 계획이 있는데 세금 혜택이 있나요", "통합투자세액공제"),
    ("벤처기업 인증 받으면 뭐가 좋아요", "벤처기업확인제도|이노비즈|벤처확인기업"),
    ("정년 지난 직원을 계속 쓰고 싶은데 지원이 있나요", "고령자 계속고용장려금"),
    ("공장을 지방으로 옮기려고 하는데요", "이전"),
    ("R&D 비용 세액공제 받으려면 뭐가 필요한가요", "연구·인력개발비"),
    ("퇴직연금 도입하고 싶은데 부담돼요", "푸른씨앗"),
    ("직원 소득세 감면해주는 제도 있죠?", "취업자에 대한 소득세"),
    ("창업자금 대출 받고 싶어요", "혁신창업사업화자금"),
    ("수출을 시작하려는데 지원 받을 수 있나요", "수출바우처"),
    ("스마트공장 만들고 싶어요", "스마트공장"),
    ("육아휴직 간 직원 대체인력 지원", "대체인력"),
    ("직원을 새로 뽑으면 받을 수 있는 혜택은?", "사회보험료|대체인력|청년|고용|장려금"),
    ("점심 메뉴 추천해줘", "(무관련)"),
]


def main():
    cards = []
    for f in sorted(CARDS_DIR.glob("*.json")):
        cards.extend(json.loads(f.read_text(encoding="utf-8")))
    vecs, idf = build(cards)

    hit1 = hit3 = ok_relevance = 0
    for q, expect in QUESTIONS:
        ranked = score(q, cards, vecs, idf, apply_cutoff=True)
        names = [n for _, n in ranked]
        pats = expect.split("|")

        if expect == "(무관련)":
            ok = len(ranked) == 0
            ok1 = ok3 = ok
        else:
            ok1 = bool(names) and any(p in names[0] for p in pats)
            ok3 = any(any(p in n for p in pats) for n in names[:3])
            ok = ok3

        hit1 += ok1
        hit3 += ok3
        ok_relevance += ok
        mark = "O" if ok else ("^" if ok3 else "X")
        print(f"[{mark}] ({len(ranked)}건) {q}")
        for s, n in ranked[:4]:
            print(f"      {s:.3f}  {n}")

    total = len(QUESTIONS)
    print(f"\ntop-1: {hit1}/{total}, top-3(cutoff 적용): {hit3}/{total}")
    print("※ cutoff 적용 결과는 무관한 카드를 억지로 채우지 않으므로 3건 미만으로 끝날 수 있음 — 정답 포함 여부만 확인")


if __name__ == "__main__":
    main()
