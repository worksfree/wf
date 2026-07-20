# -*- coding: utf-8 -*-
"""로컬 지원제도 검색 서버 (1단계 검증용).

실행:  python scripts/app.py  →  http://localhost:8777
- 질문 임베딩: 로컬 모델 (외부 API 호출 없음, 비용 0)
- 검색: 카드 임베딩과 코사인 유사도 브루트포스 비교
"""
import json
import re
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, send_from_directory

BASE = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE / "index.json"
WEB_DIR = BASE / "web"

app = Flask(__name__)

print("인덱스 로드 중...")
_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
CARDS = _index["cards"]
EMB = np.array(_index["embeddings"], dtype=np.float32)  # (N, dim) 정규화됨

print(f"임베딩 모델 로드 중... ({_index['model']})")
from sentence_transformers import SentenceTransformer
MODEL = SentenceTransformer(_index["model"])
print(f"준비 완료: 카드 {len(CARDS)}개")


def keyword_boost(query: str, card: dict) -> float:
    """제도명·목적 태그에 질문 단어가 직접 등장하면 가점 (임베딩 보완)"""
    tokens = [t for t in re.split(r"[\s,.\?!]+", query) if len(t) >= 2]
    hay = card["name"] + " " + " ".join(card.get("purpose", []))
    hits = sum(1 for t in tokens if t in hay)
    return min(hits * 0.02, 0.06)


@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    top_k = int(request.args.get("k", 8))
    if not q:
        return jsonify({"error": "질문을 입력하세요"}), 400

    q_emb = MODEL.encode(["query: " + q], normalize_embeddings=True)[0]
    scores = EMB @ q_emb  # 코사인 유사도 (정규화 벡터 내적)

    ranked = []
    for i, s in enumerate(scores):
        ranked.append((float(s) + keyword_boost(q, CARDS[i]), float(s), i))
    ranked.sort(reverse=True)

    results = []
    for boosted, raw, i in ranked[:top_k]:
        c = dict(CARDS[i])
        c["score"] = round(boosted, 4)
        c["raw_score"] = round(raw, 4)
        results.append(c)
    return jsonify({"query": q, "results": results})


@app.route("/")
def home():
    return send_from_directory(WEB_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8777, debug=False)
