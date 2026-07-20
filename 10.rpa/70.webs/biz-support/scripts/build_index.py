# -*- coding: utf-8 -*-
"""cards/*.json 을 읽어 로컬 임베딩 인덱스(index.json)를 생성한다.

- 모델: intfloat/multilingual-e5-small (한국어 지원, 무료, 로컬 실행)
- e5 계열은 "passage: " / "query: " 접두사가 필수
- 자료 갱신 시 카드 수정 후 본 스크립트 재실행만 하면 됨
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
CARDS_DIR = BASE / "cards"
INDEX_PATH = BASE / "index.json"
MODEL_NAME = "intfloat/multilingual-e5-base"


def card_to_text(c: dict) -> str:
    """임베딩 대상 텍스트: 이름 + 카테고리 + 목적 + 요약 + 대상"""
    parts = [
        c["name"],
        c.get("category", ""),
        " ".join(c.get("purpose", [])),
        c.get("summary", ""),
        c.get("target", ""),
    ]
    return " ".join(p for p in parts if p)


def main():
    cards = []
    for f in sorted(CARDS_DIR.glob("*.json")):
        cards.extend(json.loads(f.read_text(encoding="utf-8")))
    print(f"카드 {len(cards)}개 로드")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    texts = ["passage: " + card_to_text(c) for c in cards]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    index = {
        "model": MODEL_NAME,
        "cards": cards,
        "embeddings": [[round(float(x), 6) for x in row] for row in emb],
    }
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"인덱스 저장: {INDEX_PATH} ({INDEX_PATH.stat().st_size/1024:.0f} KB, dim={emb.shape[1]})")


if __name__ == "__main__":
    main()
