"""
대법원 법원경매정보 크롤러 — Cloudflare Worker 프록시 경유

아키텍처:
  로컬/NAS → Cloudflare Worker (엣지 IP) → courtauction.go.kr
  → 로컬 IP 차단 우회, Playwright 불필요

Worker 설정: config.py 의 WORKER_URL / WORKER_SECRET
"""

import copy
import time
from typing import Optional

import requests

from config import COURT_BASE_URL, CRAWL_DELAY, WORKER_URL, WORKER_SECRET
from db import upsert_auction

BASE_BODY = {
    "dma_pageInfo": {
        "pageNo": 1, "pageSize": 20,
        "bfPageNo": "", "startRowNo": "",
        "totalCnt": "", "totalYn": "Y", "groupTotalCount": "",
    },
    "dma_srchGdsDtlSrchInfo": {
        "rletDspslSpcCondCd": "", "bidDvsCd": "",
        "mvprpRletDvsCd": "00031R",
        "cortAuctnSrchCondCd": "0004601",
        "rprsAdongSdCd": "", "rprsAdongSggCd": "", "rprsAdongEmdCd": "",
        "rdnmSdCd": "", "rdnmSggCd": "", "rdnmNo": "",
        "mvprpDspslPlcAdongSdCd": "", "mvprpDspslPlcAdongSggCd": "",
        "mvprpDspslPlcAdongEmdCd": "", "rdDspslPlcAdongSdCd": "",
        "rdDspslPlcAdongSggCd": "", "rdDspslPlcAdongEmdCd": "",
        "cortOfcCd": "",
        "jdbnCd": "", "execrOfcDvsCd": "",
        "lclDspslGdsLstUsgCd": "", "mclDspslGdsLstUsgCd": "", "sclDspslGdsLstUsgCd": "",
        "cortAuctnMbrsId": "",
        "aeeEvlAmtMin": "", "aeeEvlAmtMax": "",
        "lwsDspslPrcRateMin": "", "lwsDspslPrcRateMax": "",
        "flbdNcntMin": "", "flbdNcntMax": "",
        "objctArDtsMin": "", "objctArDtsMax": "",
        "lafjOrderBy": "", "pgmId": "PGJ151F01",
        "csNo": "", "cortStDvs": "1", "statNum": 1,
        "bidBgngYmd": "", "bidEndYmd": "",
        "dspslDxdyYmd": "",
        "sideDvsCd": "",
    },
}


def _item_type(item: dict) -> str:
    lc = item.get("lclsUtilCd", "")
    mc = item.get("mclsUtilCd", "")
    if mc in ("20200", "20300"):
        return "apartment"
    if mc == "20400":
        return "house"
    if mc in ("20500", "20600", "20700"):
        return "commercial"
    if lc == "10000":
        return "land"
    return "other"


def _to_date(s: str) -> Optional[str]:
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return None


def _parse_item(item: dict) -> dict:
    sido  = item.get("hjguSido", "") or item.get("bgPlaceSido", "")
    sigu  = item.get("hjguSigu", "") or item.get("bgPlaceSigu", "")
    dong  = item.get("hjguDong", "") or item.get("bgPlaceDong", "")
    lotno = item.get("daepyoLotno", "")
    buld  = item.get("buldNm", "")
    buld_l = item.get("buldList", "")
    addr_parts = [p for p in [sido, sigu, dong, lotno] if p]
    address = " ".join(addr_parts)
    if buld:
        address += f" ({buld}{' ' + buld_l if buld_l else ''})"

    lat = float(item["wgs84Ycordi"]) if item.get("wgs84Ycordi") else None
    lng = float(item["wgs84Xcordi"]) if item.get("wgs84Xcordi") else None

    raw_area = item.get("objctAr") or item.get("objctArDts") or ""
    try:
        area_exclusive = float(raw_area) if raw_area else None
    except (ValueError, TypeError):
        area_exclusive = None

    return {
        "source":          "court",
        "case_number":     item.get("srnSaNo", ""),
        "court_name":      item.get("jiwonNm", ""),
        "item_type":       _item_type(item),
        "address":         address,
        "sido":            sido,
        "sigungu":         sigu,
        "dong":            dong,
        "lat":             lat,
        "lng":             lng,
        "area_exclusive":  area_exclusive,
        "appraisal_price": int(item.get("gamevalAmt") or 0) or None,
        "minimum_price":   int(item.get("minmaePrice") or 0) or None,
        "bid_date":        _to_date(item.get("maeGiil", "")),
        "fail_count":      int(item.get("yuchalCnt") or 0),
        "status":          "active",
        "detail_url":      f"{COURT_BASE_URL}/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ151F02.xml&docid={item.get('docid','')}",
    }


def _make_session() -> requests.Session:
    sess = requests.Session()
    sess.headers["Content-Type"] = "application/json"
    if WORKER_SECRET:
        sess.headers["X-Proxy-Secret"] = WORKER_SECRET
    return sess


def _fetch_page(sess: requests.Session, page_no: int,
                extra_params: dict = None, page_size: int = 20) -> tuple:
    body = copy.deepcopy(BASE_BODY)
    body["dma_pageInfo"]["pageNo"]   = page_no
    body["dma_pageInfo"]["pageSize"] = page_size
    if extra_params:
        body["dma_srchGdsDtlSrchInfo"].update(extra_params)

    try:
        resp = sess.post(f"{WORKER_URL}/search", json=body, timeout=30)
    except Exception as e:
        print(f"  [court] Worker 연결 오류: {e}")
        return [], 0

    if resp.status_code == 401:
        print("  [court] Worker 인증 실패 — WORKER_SECRET 확인")
        return [], 0
    if resp.status_code == 403:
        data = resp.json()
        if data.get("error") == "IP_BLOCKED":
            print("  [court] ⛔ Worker IP도 차단됨 — 잠시 후 재시도 필요")
        return [], -1

    try:
        result = resp.json()
    except Exception:
        print(f"  [court] 응답 파싱 오류: {resp.text[:200]}")
        return [], 0

    if result.get("status") != 200:
        print(f"  [court] API 오류: status={result.get('status')}")
        return [], 0

    data  = result.get("data", {})
    items = data.get("dlt_srchResult", [])
    total = int(data.get("dma_pageInfo", {}).get("totalCnt", 0) or 0)
    return items, total


def scrape_court_auction(
    court_code: str = "",
    sido_code:  str = "",
    max_items:  int = 1000,
    page_size:  int = 20,
) -> int:
    if not WORKER_URL:
        print("  [court] WORKER_URL 미설정 — config.py 확인")
        print("          Cloudflare Worker 배포 후 URL 입력 필요")
        return 0

    extra = {}
    if court_code:
        extra["cortOfcCd"] = court_code
    if sido_code:
        extra["rprsAdongSdCd"] = sido_code

    print(f"  [court] Worker 경유 수집 — {WORKER_URL}")
    sess = _make_session()

    items, total_cnt = _fetch_page(sess, 1, extra, page_size)
    if total_cnt == -1:
        return 0
    if not items:
        print("  [court] 검색 결과 없음")
        return 0

    total_pages = min(
        (total_cnt + page_size - 1) // page_size,
        (max_items  + page_size - 1) // page_size,
    )
    print(f"  [court] 총 {total_cnt}건 / {total_pages}페이지")

    total_saved = 0
    for p_no in range(1, total_pages + 1):
        if p_no > 1:
            time.sleep(CRAWL_DELAY)
            items, _ = _fetch_page(sess, p_no, extra, page_size)

        saved = sum(
            1 for item in items
            if item.get("srnSaNo") and upsert_auction(_parse_item(item))
        )
        total_saved += saved
        print(f"  [court] p{p_no}/{total_pages} — {saved}/{len(items)}건 (누계:{total_saved})")

        if total_saved >= max_items:
            break

    print(f"[court] 완료 — {total_saved}건")
    return total_saved


def scrape_all_courts(max_items_per_run: int = 500) -> int:
    return scrape_court_auction(max_items=max_items_per_run)


if __name__ == "__main__":
    from db import init_db
    init_db()
    scrape_court_auction(max_items=50)
