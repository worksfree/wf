"""
DB → ../data/auctions.json 내보내기

index.html에서 fetch('data/auctions.json')으로 로드.
mock 데이터와 동일한 필드명 사용.

사용:
  cd crawler
  python export_json.py
  python export_json.py --max 500
"""

import argparse
import json
from datetime import datetime, date
from pathlib import Path

from db import get_conn, init_db

OUT_PATH = Path(__file__).parent.parent / "data" / "auctions.json"


def _avg_trade_price(conn, sido: str, sigungu: str) -> int:
    row = conn.execute("""
        SELECT AVG(trade_price) AS avg_p
        FROM real_estate_trades
        WHERE sido = ? AND (sigungu = ? OR ? = '')
          AND trade_year >= ?
    """, (sido, sigungu, sigungu, date.today().year - 1)).fetchone()
    val = row["avg_p"] if row else None
    return int(val) if val else 0


def _predicted_rate(appraisal: int, minimum: int, fail_count: int) -> int:
    """낙찰 예상률 (정수 %)"""
    if not appraisal or not minimum:
        return 75
    base = minimum / appraisal
    factor = max(0.55, min(0.95, base - fail_count * 0.03))
    return round(factor * 100)


def export(max_items: int = 2000) -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    init_db()

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, case_number, court_name, item_type, address, sido, sigungu, dong,
                   lat, lng, area_exclusive, appraisal_price, minimum_price,
                   bid_date, fail_count, status, detail_url
            FROM auction_items
            WHERE status = 'active' AND lat IS NOT NULL
            ORDER BY bid_date ASC
            LIMIT ?
        """, (max_items,)).fetchall()

        items = []
        for r in rows:
            sido    = r["sido"] or ""
            sigungu = r["sigungu"] or ""
            app     = r["appraisal_price"] or 0
            minP    = r["minimum_price"] or 0
            fc      = r["fail_count"] or 0
            area    = r["area_exclusive"] or 0
            avg_trade = _avg_trade_price(conn, sido, sigungu)
            if not avg_trade and app:
                avg_trade = round(app * 1.15 / 500000) * 500000  # 감정가 대비 추정
            pred = _predicted_rate(app, minP, fc)

            items.append({
                # 식별자
                "id":          r["id"],
                "case_number": r["case_number"] or "",
                "court":       r["court_name"] or "",
                "type":        r["item_type"] or "other",
                # 주소
                "sido":    sido,
                "gu":      sigungu,
                "dong":    r["dong"] or "",
                "address": r["address"] or "",
                # 좌표
                "lat": r["lat"],
                "lng": r["lng"],
                # 면적/정보
                "area":  round(area, 1) if area else None,
                "floor": None,
                "yr":    None,
                # 가격
                "app":  app,
                "minP": minP,
                "avgT": avg_trade,
                # 상태
                "fc":       fc,
                "bid_date": r["bid_date"] or "",
                "pred":     pred,
                # 상세링크
                "detail_url": r["detail_url"] or "",
                # 마크: 실데이터 여부
                "is_real": True,
            })

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"[export] {len(items)}건 → {OUT_PATH}  ({size_kb} KB)")
    return len(items)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=2000)
    args = parser.parse_args()
    export(args.max)
