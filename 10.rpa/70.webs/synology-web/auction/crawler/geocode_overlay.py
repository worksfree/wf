"""
Worker KV 데이터 → 카카오 로컬 API 주소 검색 → geocode.json 오버레이 생성

geocode.json 구조: { "2025타경12345": {"lat": 37.4512, "lng": 127.1234}, ... }

사용:
  python geocode_overlay.py               # 전체 처리 (기존 캐시 활용, 이어서 처리)
  python geocode_overlay.py --max 200     # 이번 실행에서 최대 N건 처리
  python geocode_overlay.py --force       # 기존 오버레이 무시하고 재처리
  python geocode_overlay.py --stats       # 현황 출력만
  python geocode_overlay.py --test        # API 키 동작 확인

API 키 설정 (REST API 키):
  $env:KAKAO_API_KEY = "키값"   ← 현재 터미널에 즉시 적용
  setx KAKAO_API_KEY "키값"     ← 영구 저장 (새 터미널부터)
  발급: developers.kakao.com → 앱 → 앱 키 → REST API 키
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests

from config import KAKAO_API_KEY, WORKER_URL
from db import init_db, get_geocache, set_geocache

OUT_PATH = Path(__file__).parent.parent / "data" / "geocode.json"
WORKER_DEFAULT = "https://auction-proxy.worksfree.workers.dev"
KAKAO_GEO_URL = "https://dapi.kakao.com/v2/local/search/address.json"
CALL_DELAY = 0.12  # 카카오 API: 초당 10건 제한 → 0.12초로 여유


def _clean_address(address: str) -> str:
    """건물명·층·호 괄호 정보 제거 → 지번 주소만 남김."""
    return re.sub(r'\s*\(.*?\)\s*$', '', address).strip()


def _geocode(address: str) -> tuple[float, float] | None:
    """카카오 로컬 API 주소 검색. 캐시 우선."""
    clean = _clean_address(address)

    cached = get_geocache(clean)
    if cached:
        return cached

    try:
        resp = requests.get(
            KAKAO_GEO_URL,
            headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"},
            params={"query": clean, "size": 1},
            timeout=8,
        )
        if resp.status_code == 401:
            print("  [ERROR] 401 인증 실패 -- KAKAO_API_KEY 를 확인하세요")
            return None
        if resp.status_code == 403:
            print("  [ERROR] 403 권한 없음 -- REST API 키인지, 카카오맵 활성화 여부를 확인하세요")
            return None
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if not docs:
            return None
        lat = float(docs[0]["y"])
        lng = float(docs[0]["x"])
        set_geocache(clean, lat, lng)
        time.sleep(CALL_DELAY)
        return lat, lng
    except Exception as e:
        print(f"  [geo] 오류 '{clean[:35]}': {e}")
        return None


def _test_api():
    """API 키 동작 확인."""
    if not KAKAO_API_KEY:
        print("[ERROR] KAKAO_API_KEY 환경변수가 비어 있습니다.")
        print("   $env:KAKAO_API_KEY = '키값'  (현재 터미널)")
        print("   setx KAKAO_API_KEY '키값'    (영구 저장)")
        return
    print(f"KAKAO_API_KEY: {KAKAO_API_KEY[:8]}...{KAKAO_API_KEY[-4:]}")
    result = _geocode("서울특별시 강남구 개포동 1188")
    if result:
        print(f"[OK] API 정상 작동 -- 서울 강남구 개포동: lat={result[0]}, lng={result[1]}")
    else:
        print("[FAIL] API 호출 실패 -- 위 오류 메시지를 확인하세요")


def _needs_geocoding(item: dict) -> bool:
    lat, lng = item.get("lat"), item.get("lng")
    if lat is None or lng is None:
        return True
    ls, rs = str(lat), str(lng)
    ld = len(ls.split(".")[1]) if "." in ls else 0
    rd = len(rs.split(".")[1]) if "." in rs else 0
    return ld < 3 or rd < 3


def _load_overlay() -> dict:
    if OUT_PATH.exists():
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_overlay(overlay: dict):
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(overlay, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"  → 저장: {OUT_PATH}  ({size_kb} KB, {len(overlay)}건)")


def print_stats(items: list, overlay: dict):
    total = len(items)
    need = sum(1 for it in items if _needs_geocoding(it))
    covered = sum(1 for it in items if it["case_number"] in overlay)
    print(f"\n[현황] 전체 {total}건 | 좌표 부정확 {need}건 | 오버레이 커버 {covered}건"
          f" | 미처리 {max(0, need - covered)}건")


def build_overlay(max_items: int = 0, force: bool = False) -> dict:
    if not KAKAO_API_KEY:
        print("[ERROR] KAKAO_API_KEY 미설정.")
        print("   $env:KAKAO_API_KEY = '키값'  (현재 터미널에 즉시 적용)")
        print("   setx KAKAO_API_KEY '키값'    (영구 저장, 새 터미널부터)")
        return {}

    worker = (WORKER_URL or WORKER_DEFAULT).rstrip("/")
    print(f"[overlay] Worker에서 데이터 다운로드: {worker}/data?tenant=worksfree")
    try:
        resp = requests.get(f"{worker}/data", params={"tenant": "worksfree"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [ERROR] Worker 연결 실패: {e}")
        return {}

    items = data.get("items", [])
    if not items:
        print("  [WARN] 데이터 없음 (Worker에 수집된 데이터가 없습니다)")
        return {}
    print(f"[overlay] {len(items)}건 로드 완료")

    overlay = {} if force else _load_overlay()
    if overlay and not force:
        print(f"[overlay] 기존 오버레이 {len(overlay)}건 로드 (이어서 처리)")

    print_stats(items, overlay)

    need = [
        it for it in items
        if it.get("address") and _needs_geocoding(it) and it["case_number"] not in overlay
    ]
    if max_items > 0:
        need = need[:max_items]

    if not need:
        print("[overlay] 처리할 항목이 없습니다.")
        return overlay

    est_min = len(need) * CALL_DELAY / 60
    print(f"[overlay] 이번 처리: {len(need)}건 (예상 {est_min:.1f}분)")
    print("  Ctrl+C로 중단해도 중간 저장본이 유지됩니다.\n")

    ok = fail = 0
    for i, item in enumerate(need):
        result = _geocode(item["address"])
        if result:
            overlay[item["case_number"]] = {"lat": result[0], "lng": result[1]}
            ok += 1
        else:
            fail += 1
            # 연속 실패 5건 이상이면 API 문제 — 중단
            if fail >= 5 and ok == 0:
                print(f"\n  [WARN] 처음 {fail}건이 모두 실패했습니다. API 키/권한을 확인하세요.")
                print("    python geocode_overlay.py --test")
                _save_overlay(overlay)
                return overlay

        if (i + 1) % 100 == 0:
            _save_overlay(overlay)
            pct = (i + 1) / len(need) * 100
            print(f"  [{i+1:>5}/{len(need)}] {pct:.0f}% | 성공:{ok} 실패:{fail}")

    _save_overlay(overlay)
    remaining = sum(1 for it in items if _needs_geocoding(it) and it["case_number"] not in overlay)
    print(f"\n[overlay] 완료: 성공 {ok}건 | 실패 {fail}건 | 오버레이 총 {len(overlay)}건 | 잔여 {remaining}건")
    if remaining > 0:
        print("  → 다시 실행하면 이어서 처리됩니다: python geocode_overlay.py")
    return overlay


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Worker 데이터 지오코딩 오버레이 생성")
    parser.add_argument("--max",   type=int, default=0,   help="최대 처리 건수 (0=전체)")
    parser.add_argument("--force", action="store_true",   help="기존 오버레이 무시")
    parser.add_argument("--stats", action="store_true",   help="현황만 출력")
    parser.add_argument("--test",  action="store_true",   help="API 키 동작 확인")
    args = parser.parse_args()

    init_db()

    if args.test:
        _test_api()
    elif args.stats:
        worker = (WORKER_URL or WORKER_DEFAULT).rstrip("/")
        try:
            items = requests.get(f"{worker}/data", params={"tenant": "worksfree"}, timeout=15).json().get("items", [])
            print_stats(items, _load_overlay())
        except Exception as e:
            print(f"오류: {e}")
    else:
        build_overlay(max_items=args.max, force=args.force)
