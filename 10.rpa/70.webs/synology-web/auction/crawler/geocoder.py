"""
카카오 로컬 API — 주소 → 위도/경도 변환
발급: https://developers.kakao.com → REST API 키
"""

import time
import requests

from config import KAKAO_API_KEY, KAKAO_GEO_URL, CRAWL_DELAY
from db import get_conn, get_geocache, set_geocache


def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (lat, lng). 캐시 우선."""
    cached = get_geocache(address)
    if cached:
        return cached

    if not KAKAO_API_KEY:
        return None

    try:
        resp = requests.get(
            KAKAO_GEO_URL,
            headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"},
            params={"query": address, "size": 1},
            timeout=5,
        )
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if not docs:
            return None
        lat = float(docs[0]["y"])
        lng = float(docs[0]["x"])
        set_geocache(address, lat, lng)
        return lat, lng
    except Exception as e:
        print(f"  [geo] error for '{address}': {e}")
        return None


def fill_missing_coords(batch_size: int = 100, delay: float = 0.2) -> int:
    """auction_items 중 좌표 없는 물건에 좌표 채우기."""
    if not KAKAO_API_KEY:
        print("[geo] ⚠  KAKAO_API_KEY 미설정.")
        print("      발급: https://developers.kakao.com → 앱 만들기 → REST API 키")
        return 0

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, address FROM auction_items WHERE lat IS NULL AND address IS NOT NULL LIMIT ?",
            (batch_size,)
        ).fetchall()

    updated = 0
    for row in rows:
        result = geocode(row["address"])
        if result:
            lat, lng = result
            with get_conn() as conn:
                conn.execute(
                    "UPDATE auction_items SET lat=?, lng=? WHERE id=?",
                    (lat, lng, row["id"])
                )
            updated += 1
        time.sleep(delay)

    print(f"[geo] 좌표 채우기 완료: {updated}/{len(rows)}건")
    return updated


if __name__ == "__main__":
    # 단일 테스트
    result = geocode("서울특별시 강남구 대치동 996")
    print(result)
