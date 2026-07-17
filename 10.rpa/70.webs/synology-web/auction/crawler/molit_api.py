"""
국토교통부 실거래가 공개 API 수집기
공공데이터포털: https://www.data.go.kr
API: 국토교통부_아파트매매 실거래 상세 자료 (getRTMSDataSvcAptTradeDev)
"""

import time
import xml.etree.ElementTree as ET
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import requests

from config import MOLIT_API_KEY, MOLIT_BASE_URL, LAWD_CODES, TRADE_MONTHS
from db import bulk_insert_trades


# API 엔드포인트 (각 물건 유형별)
ENDPOINTS = {
    "apartment": "getRTMSDataSvcAptTradeDev",   # 아파트 매매
    "row_house":  "getRTMSDataSvcRHTradeDev",     # 연립/다세대
    "house":      "getRTMSDataSvcSHTradeDev",     # 단독/다가구
}


def _fetch_page(endpoint: str, lawd_cd: str, deal_ymd: str, page: int = 1, size: int = 1000) -> list[dict]:
    """API 단일 페이지 호출 → 파싱된 row list 반환."""
    url = f"{MOLIT_BASE_URL}/{endpoint}"
    params = {
        "serviceKey": MOLIT_API_KEY,
        "LAWD_CD":    lawd_cd,
        "DEAL_YMD":   deal_ymd,
        "numOfRows":  str(size),
        "pageNo":     str(page),
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [molit] request error {e}")
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        print(f"  [molit] xml parse error: {e}")
        return []

    result_code = root.findtext(".//resultCode", "")
    if result_code != "00":
        msg = root.findtext(".//resultMsg", "")
        print(f"  [molit] API error {result_code}: {msg}")
        return []

    rows = []
    for item in root.findall(".//item"):
        def g(tag): return (item.findtext(tag) or "").strip()
        price_raw = g("거래금액").replace(",", "")
        if not price_raw.isdigit():
            continue
        rows.append({
            "building_name":   g("아파트") or g("연립다세대") or "",
            "dong":            g("법정동"),
            "jibun":           g("지번"),
            "area_exclusive":  float(g("전용면적") or 0),
            "trade_price":     int(price_raw) * 10000,  # 만원 → 원
            "trade_year":      int(g("년") or 0),
            "trade_month":     int(g("월") or 0),
            "trade_day":       int(g("일") or 0),
            "floor":           int(g("층") or 0) or None,
            "build_year":      int(g("건축년도") or 0) or None,
            "lawd_cd":         g("지역코드") or lawd_cd,
        })
    return rows


def collect_trades_for_region(region_name: str, lawd_cd: str, trade_type: str = "apartment") -> int:
    """특정 지역·유형의 최근 N개월 실거래 수집."""
    endpoint = ENDPOINTS.get(trade_type)
    if not endpoint:
        return 0

    # 시도/시군구 추출 (지역명 "서울 강남구" → sido="서울특별시", sigungu="강남구")
    parts = region_name.split()
    sido_map = {
        "서울": "서울특별시", "부산": "부산광역시", "인천": "인천광역시",
        "경기": "경기도", "대전": "대전광역시", "대구": "대구광역시",
        "광주": "광주광역시", "제주": "제주특별자치도",
    }
    sido = sido_map.get(parts[0], parts[0])
    sigungu = " ".join(parts[1:]) if len(parts) > 1 else ""

    total = 0
    today = date.today()

    for m in range(TRADE_MONTHS):
        target = today - relativedelta(months=m)
        deal_ymd = target.strftime("%Y%m")
        print(f"  [molit] {region_name} ({trade_type}) {deal_ymd} ...", end=" ", flush=True)
        rows = _fetch_page(endpoint, lawd_cd, deal_ymd)

        # 공통 필드 보강
        for row in rows:
            row["trade_type"] = trade_type
            row["sido"]       = sido
            row["sigungu"]    = sigungu

        bulk_insert_trades(rows)
        print(f"{len(rows)}건")
        total += len(rows)
        time.sleep(0.3)  # API 쿼터 보호

    return total


def collect_all_trades(trade_types: list[str] = None) -> int:
    """전체 대상 지역 실거래 수집."""
    if not MOLIT_API_KEY:
        print("[molit] ⚠  MOLIT_API_KEY 미설정. config.py 또는 환경변수 확인.")
        print("        발급: https://www.data.go.kr → '아파트매매 실거래' API 신청")
        return 0

    if trade_types is None:
        trade_types = ["apartment"]  # 기본은 아파트만. 전체: list(ENDPOINTS.keys())

    total = 0
    for region_name, lawd_cd in LAWD_CODES.items():
        for ttype in trade_types:
            total += collect_trades_for_region(region_name, lawd_cd, ttype)

    print(f"\n[molit] 수집 완료 — 총 {total:,}건")
    return total


if __name__ == "__main__":
    from db import init_db
    init_db()
    collect_all_trades()
