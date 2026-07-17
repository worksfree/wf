# 경매지도 크롤러 설정
# API 키는 환경변수 또는 .env 파일로 관리 (이 파일은 git에 커밋)

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── 공공데이터포털 (data.go.kr) ────────────────────────────────
# 발급: https://www.data.go.kr → 국토교통부 실거래가 API 신청
# 환경변수: MOLIT_API_KEY=인증키
MOLIT_API_KEY = os.getenv("MOLIT_API_KEY", "")

MOLIT_BASE_URL = "http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc"

# ── 카카오 Developers ──────────────────────────────────────────
# 발급: https://developers.kakao.com → 앱 등록 → REST API 키
# 환경변수: KAKAO_API_KEY=REST API 키
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY", "")

KAKAO_GEO_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# ── Cloudflare Worker 프록시 ────────────────────────────────────
# Worker 배포 후 URL 입력 (예: https://auction-proxy.ACCOUNT.workers.dev)
# 환경변수: WORKER_URL, WORKER_SECRET
WORKER_URL    = os.getenv("WORKER_URL", "https://auction-proxy.worksfree.workers.dev")
WORKER_SECRET = os.getenv("WORKER_SECRET", "")

# ── 법원경매정보 ────────────────────────────────────────────────
COURT_BASE_URL = "https://www.courtauction.go.kr"
COURT_SEARCH_URL = f"{COURT_BASE_URL}/RetrieveRealEstList.laf"
COURT_DETAIL_URL = f"{COURT_BASE_URL}/RetrieveRealEstDetailList.laf"

COURT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": COURT_BASE_URL + "/",
}

# 크롤링 딜레이 (초) — robots.txt 준수 및 서버 부하 최소화
CRAWL_DELAY = 1.5

# ── 수집 대상 지역 코드 (법정동 코드 앞 5자리) ─────────────────
# 시도코드: 서울=11, 부산=26, 인천=28, 경기=41, 대전=30, 대구=27, 광주=29, 제주=50
LAWD_CODES = {
    # 서울
    "서울 강남구": "11680", "서울 서초구": "11650", "서울 마포구": "11440",
    "서울 송파구": "11710", "서울 노원구": "11350", "서울 강서구": "11500",
    "서울 용산구": "11170", "서울 도봉구": "11320",
    # 경기
    "경기 수원시": "41111", "경기 성남시": "41131", "경기 고양시": "41281", "경기 용인시": "41461",
    # 인천
    "인천 남동구": "28245", "인천 부평구": "28237",
    # 부산
    "부산 해운대구": "26350", "부산 수영구": "26380", "부산 부산진구": "26230",
    # 대전
    "대전 서구": "30170", "대전 유성구": "30200",
    # 대구
    "대구 수성구": "27260", "대구 달서구": "27290",
    # 광주
    "광주 서구": "29140",
    # 제주
    "제주 제주시": "50110",
}

# 수집할 최근 개월 수
TRADE_MONTHS = 6
