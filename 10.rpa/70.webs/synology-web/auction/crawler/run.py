"""
경매지도 데이터 파이프라인 — 메인 실행 스크립트

사용법:
  python run.py             # 전체 수집 (법원경매 + 실거래가 + 좌표)
  python run.py --court     # 법원경매만
  python run.py --trades    # 실거래가만
  python run.py --geo       # 좌표 채우기만
  python run.py --stats     # DB 현황 확인
  python run.py --test      # 연결 테스트 (API 키 유효성)
  python run.py --export    # DB → JSON 내보내기
  python run.py --upload    # JSON → NAS SCP 업로드 (로컬에서 실행)
  python run.py --court --upload  # 수집 + JSON + NAS 업로드 한 번에
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from db import init_db, get_stats
from court_scraper import scrape_all_courts
from molit_api import collect_all_trades
from geocoder import fill_missing_coords
from export_json import export as export_json
from geocode_overlay import build_overlay as build_geo_overlay
from config import MOLIT_API_KEY, KAKAO_API_KEY, WORKER_URL

NAS_USER = "wfadmin"
NAS_HOST = "192.168.100.38"
NAS_PATH = "/volume1/web/auction/data/auctions.json"
GEO_NAS_PATH = "/volume1/web/auction/data/geocode.json"

JSON_PATH = Path(__file__).parent.parent / "data" / "auctions.json"
GEO_PATH  = Path(__file__).parent.parent / "data" / "geocode.json"


def check_keys():
    ok = True
    if not MOLIT_API_KEY:
        print("⚠  MOLIT_API_KEY 없음 → 실거래가 수집 불가")
        ok = False
    else:
        print(f"✅ MOLIT_API_KEY: {MOLIT_API_KEY[:8]}...")
    if not KAKAO_API_KEY:
        print("⚠  KAKAO_API_KEY 없음 → 주소→좌표 변환 불가 (크롤링은 가능)")
    else:
        print(f"✅ KAKAO_API_KEY: {KAKAO_API_KEY[:8]}...")
    return ok


def upload_to_nas():
    """로컬 auctions.json → NAS SCP 업로드."""
    if not JSON_PATH.exists():
        print(f"❌ {JSON_PATH} 없음 — 먼저 --export 실행")
        return False

    # NAS data 폴더 생성 (없을 수 있음)
    ssh_mkdir = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{NAS_USER}@{NAS_HOST}",
        "mkdir -p /volume1/web/auction/data",
    ]
    subprocess.run(ssh_mkdir, check=False)

    # Git Bash (tar 방식) 먼저 시도, 실패 시 scp 직접 시도
    local_posix = JSON_PATH.as_posix().replace("D:", "/d").replace("\\", "/")
    bash_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    bash = next((p for p in bash_paths if Path(p).exists()), None)

    if bash:
        cmd = f'scp -o StrictHostKeyChecking=no "{local_posix}" {NAS_USER}@{NAS_HOST}:{NAS_PATH}'
        result = subprocess.run([bash, "-c", cmd], capture_output=True, text=True)
    else:
        result = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no", str(JSON_PATH), f"{NAS_USER}@{NAS_HOST}:{NAS_PATH}"],
            capture_output=True, text=True,
        )

    if result.returncode == 0:
        size = JSON_PATH.stat().st_size // 1024
        print(f"✅ NAS 업로드 완료 — {NAS_HOST}:{NAS_PATH} ({size} KB)")
    else:
        print(f"❌ NAS 업로드 실패: {result.stderr.strip()}")
        return False

    # geocode.json 도 있으면 함께 업로드
    if GEO_PATH.exists():
        geo_posix = GEO_PATH.as_posix().replace("D:", "/d").replace("\\", "/")
        if bash:
            cmd2 = f'scp -o StrictHostKeyChecking=no "{geo_posix}" {NAS_USER}@{NAS_HOST}:{GEO_NAS_PATH}'
            r2 = subprocess.run([bash, "-c", cmd2], capture_output=True, text=True)
        else:
            r2 = subprocess.run(
                ["scp", "-o", "StrictHostKeyChecking=no", str(GEO_PATH), f"{NAS_USER}@{NAS_HOST}:{GEO_NAS_PATH}"],
                capture_output=True, text=True,
            )
        if r2.returncode == 0:
            geo_size = GEO_PATH.stat().st_size // 1024
            print(f"✅ geocode.json 업로드 — {NAS_HOST}:{GEO_NAS_PATH} ({geo_size} KB)")
        else:
            print(f"⚠  geocode.json 업로드 실패: {r2.stderr.strip()}")

    return True


def run_full():
    print(f"\n{'='*50}")
    print(f" 경매지도 데이터 수집 시작 — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'='*50}\n")

    init_db()
    check_keys()

    print("\n[1/4] 법원경매 물건 수집")
    court_n = scrape_all_courts(max_items_per_run=300)

    print("\n[2/4] 국토교통부 실거래가 수집")
    trade_n = collect_all_trades(trade_types=["apartment"])

    print("\n[3/4] 좌표 변환 (카카오 API)")
    geo_n = fill_missing_coords(batch_size=500)

    print("\n[4/4] JSON 내보내기")
    exp_n = export_json()

    stats = get_stats()
    print(f"\n{'='*50}")
    print(f" 완료 | 경매:{court_n}건 | 실거래:{trade_n}건 | 좌표:{geo_n}건 | 내보내기:{exp_n}건")
    print(f" DB 현황: {stats}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="경매지도 데이터 수집")
    parser.add_argument("--court",       action="store_true", help="법원경매 수집")
    parser.add_argument("--trades",      action="store_true", help="실거래가 수집")
    parser.add_argument("--geo",         action="store_true", help="좌표 채우기 (SQLite 기반)")
    parser.add_argument("--geo-overlay", action="store_true", help="Worker KV 데이터 → Kakao 지오코딩 → geocode.json 생성")
    parser.add_argument("--geo-max",     type=int, default=0, help="--geo-overlay 처리 건수 제한 (0=전체)")
    parser.add_argument("--stats",       action="store_true", help="DB 현황")
    parser.add_argument("--test",        action="store_true", help="API 키 테스트")
    parser.add_argument("--export",      action="store_true", help="DB → JSON 내보내기")
    parser.add_argument("--upload",      action="store_true", help="JSON → NAS SCP 업로드")
    args = parser.parse_args()

    init_db()

    if args.test:
        check_keys()
        print(f"  WORKER_URL: {WORKER_URL or '(미설정)'}")
        return

    if args.stats:
        print(get_stats())
        return

    # 개별 단계 실행
    ran_any = False
    if args.court:
        scrape_all_courts()
        ran_any = True
    if args.trades:
        collect_all_trades()
        ran_any = True
    if args.geo:
        fill_missing_coords()
        ran_any = True
    if getattr(args, 'geo_overlay', False):
        build_geo_overlay(max_items=args.geo_max)
        ran_any = True

    # export: 명시적으로 요청했거나, 수집 단계가 있었고 upload 전에 필요한 경우
    need_export = args.export or ran_any or args.upload
    if need_export:
        export_json()

    if args.upload:
        upload_to_nas()
        return

    if not ran_any and not args.export:
        run_full()


if __name__ == "__main__":
    main()
