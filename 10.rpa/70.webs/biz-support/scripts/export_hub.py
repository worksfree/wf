# -*- coding: utf-8 -*-
"""cards/*.json 을 병합해 허브 노드(synology-web/consulting/support/cards.json)로 내보낸다.

자료 갱신 절차: 카드 수정 → 본 스크립트 실행 → deploy.ps1 배포
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = Path(__file__).resolve().parent.parent
CARDS_DIR = BASE / "cards"
HUB_OUT = BASE.parent / "synology-web" / "consulting" / "support" / "cards.json"


def main():
    cards = []
    for f in sorted(CARDS_DIR.glob("*.json")):
        cards.extend(json.loads(f.read_text(encoding="utf-8")))
    HUB_OUT.parent.mkdir(parents=True, exist_ok=True)
    HUB_OUT.write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    print(f"허브 내보내기: {len(cards)}개 카드 → {HUB_OUT} ({HUB_OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
