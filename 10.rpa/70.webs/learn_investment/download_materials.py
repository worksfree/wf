#!/usr/bin/env python3
"""
learninvest.co.kr 강의자료 다운로드 스크립트 (Selenium)

사용법:
  python download_materials.py --phase 1   # 사이트 분석 (UI 모드)  → site_map.json 생성
  python download_materials.py --phase 2   # 일괄 다운로드 (Headless)← site_map.json 사용

설치:
  pip install selenium
"""

import argparse
import base64
import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium.webdriver.chrome.webdriver import WebDriver as Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ══════════════════════════════════════════════════════════════════════════════
# 설정 — 필요에 따라 수정하세요
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL  = "https://www.learninvest.co.kr"
ENTRY_URL = f"{BASE_URL}/index.iv"  # 사이트 진입점 (로그인 버튼 있는 메인)
MAIN_URL  = f"{BASE_URL}/u/con/main"  # 로그인 후 콘텐츠 메인
LOGIN_URL = f"{BASE_URL}/u/login"     # 로그인 페이지 (단체회원 포함)

# 저장 폴더
OUTPUT_DIR    = Path(__file__).parent / "downloads"
SITEMAP_PATH  = OUTPUT_DIR / "site_map.json"
COOKIES_PATH  = OUTPUT_DIR / "session_cookies.json"
TEMP_DL_DIR   = OUTPUT_DIR / "_temp_downloads"

# ── 로그인 방법 A: 아이디/비밀번호 ───────────────────────────────────────────
# 두 값을 모두 채우면 A 방식 사용 / 비워두면 B 방식(Chrome 프로필) 사용
LOGIN_ID = "2085612"
LOGIN_PW = "Thyg57thyg6*"

# ── 로그인 방법 B: 기존 Chrome 프로필 재사용 ─────────────────────────────────
# ※ Chrome이 열려 있으면 충돌합니다. Phase 1 실행 전 Chrome을 완전히 닫으세요.
CHROME_USER_DATA_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
CHROME_PROFILE_NAME  = "Default"   # "Default" / "Profile 1" / "Profile 2" ...

# 대상 섹션 (메뉴에서 이 텍스트를 포함하는 링크를 찾습니다)
TARGET_SECTIONS = ["강의교재", "영업자료실", "런클릭", "공지사항"]

# 직접 파일로 저장할 확장자
DOWNLOAD_EXTENSIONS = {
    ".pdf", ".hwp", ".hwpx",
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".zip", ".rar", ".7z", ".txt", ".csv",
}

# 요청 간 대기 (초) — 서버 부하 방지
PAGE_DELAY = 1.2

# 다운로드 완료 대기 최대 시간 (초)
DOWNLOAD_TIMEOUT = 60


# ══════════════════════════════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════════════════════════════

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sanitize(name: str, max_len: int = 120) -> str:
    name = re.sub(r'[\\/*?:"<>|\n\r\t]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:max_len]


def is_file_url(url: str) -> bool:
    ext = Path(urlparse(url).path).suffix.lower()
    return ext in DOWNLOAD_EXTENSIONS


def abs_url(href: str) -> str:
    if not href or href.startswith(("javascript:", "#")):
        return ""
    return urljoin(BASE_URL, href)


# ══════════════════════════════════════════════════════════════════════════════
# Chrome 드라이버 생성
# ══════════════════════════════════════════════════════════════════════════════

def _base_options(headless: bool, download_dir: Path | None = None) -> Options:
    """공통 Chrome 옵션을 생성한다."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    dl_path = str(download_dir or TEMP_DL_DIR)
    options.add_experimental_option("prefs", {
        "download.default_directory":         dl_path,
        "download.prompt_for_download":       False,
        "download.directory_upgrade":         True,
        "safebrowsing.enabled":               True,
        "plugins.always_open_pdf_externally": True,
    })
    return options


def build_driver(headless: bool, download_dir: Path | None = None) -> tuple[Chrome, bool]:
    """Chrome 드라이버를 생성한다.
    반환: (driver, attached_to_existing)

    연결 시도 순서 (Phase 1 UI 모드):
      1. 원격 디버깅 포트(9222)에 이미 실행 중인 Chrome에 연결
      2. Chrome 프로필 직접 로드 (Chrome이 닫혀 있을 때)
      3. 새 브라우저 열기 (수동 로그인 필요)

    Phase 2 (headless):
      - 새 headless 브라우저 + 저장된 쿠키로 세션 복원
    """
    # ── Phase 2: headless 전용 ────────────────────────────────────────────────
    if headless:
        log("Headless 브라우저 시작...")
        opts = _base_options(headless=True, download_dir=download_dir)
        driver = Chrome(options=opts)
        driver.set_window_size(1280, 900)
        return driver, False

    # ── Phase 1 연결 방법 1: 원격 디버깅 포트(9222) ───────────────────────────
    log("기존 Chrome(원격 디버깅 포트 9222) 연결 시도...")
    try:
        opts = _base_options(headless=False, download_dir=download_dir)
        opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = Chrome(options=opts)
        log(f"  ✓ 기존 Chrome 연결 성공 (현재 탭: {driver.current_url})")
        return driver, True
    except Exception:
        log("  ✗ 연결 실패. start_chrome_debug.bat 을 아직 실행하지 않은 것 같습니다.")

    # ── Phase 1 연결 방법 2: Chrome 프로필 직접 로드 ──────────────────────────
    use_profile = not (LOGIN_ID and LOGIN_PW)
    if use_profile and os.path.isdir(CHROME_USER_DATA_DIR):
        log(f"Chrome 프로필 로드 시도: {CHROME_USER_DATA_DIR} ({CHROME_PROFILE_NAME})")
        log("  ※ Chrome이 완전히 닫혀 있어야 합니다.")
        try:
            opts = _base_options(headless=False, download_dir=download_dir)
            opts.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
            opts.add_argument(f"--profile-directory={CHROME_PROFILE_NAME}")
            driver = Chrome(options=opts)
            driver.set_window_size(1280, 900)
            log("  ✓ Chrome 프로필 로드 성공")
            return driver, False
        except Exception as e:
            log(f"  ✗ 프로필 로드 실패: {e}")

    # ── Phase 1 연결 방법 3: 새 브라우저 (수동 로그인 필요) ───────────────────
    log("새 브라우저를 열겠습니다. (로그인 필요)")
    opts = _base_options(headless=False, download_dir=download_dir)
    driver = Chrome(options=opts)
    driver.set_window_size(1280, 900)
    return driver, False


# ══════════════════════════════════════════════════════════════════════════════
# 쿠키 저장 / 복원
# ══════════════════════════════════════════════════════════════════════════════

def save_cookies(driver: Chrome):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cookies = driver.get_cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    log(f"  쿠키 저장: {COOKIES_PATH} ({len(cookies)}개)")


def load_cookies(driver: Chrome) -> bool:
    if not COOKIES_PATH.exists():
        return False
    driver.get(BASE_URL)   # 쿠키를 심으려면 먼저 해당 도메인에 접속해야 함
    time.sleep(1)
    with open(COOKIES_PATH, encoding="utf-8") as f:
        cookies = json.load(f)
    for cookie in cookies:
        cookie.pop("sameSite", None)   # 일부 브라우저에서 오류 방지
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass
    driver.get(MAIN_URL)
    time.sleep(2)
    log(f"  쿠키 복원 완료 ({len(cookies)}개) → {driver.current_url}")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 로그인 / 세션 확인
# ══════════════════════════════════════════════════════════════════════════════

def _fill_and_submit(driver: Chrome, id_el, pw_el):
    """아이디·비밀번호 입력 후 로그인 버튼 클릭"""
    id_el.clear()
    id_el.send_keys(LOGIN_ID)
    pw_el.clear()
    pw_el.send_keys(LOGIN_PW)
    for sel in ['button[type="submit"]', 'input[type="submit"]',
                "//button[contains(text(),'로그인')]"]:
        try:
            by = By.XPATH if sel.startswith("//") else By.CSS_SELECTOR
            driver.find_element(by, sel).click()
            return
        except Exception:
            pass
    pw_el.submit()


def do_login(driver: Chrome):
    """단체회원 전용 로그인 (아이디/비밀번호 폼)

    learninvest.co.kr/u/login 구조:
      - 상단: 일반 아이디/비밀번호 폼
      - 하단: 단체회원 전용 로그인 (회사 클릭 → 별도 폼)

    단체회원 ID(숫자형)인 경우 플레이스홀더가 '아이디'인 필드를 사용한다.
    """
    log(f"로그인 시도: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    time.sleep(1.5)

    # ── 단체회원 전용 폼 탐색: placeholder="아이디" 인 text 필드 ──────────────
    # 페이지 상단의 일반 로그인과 구분하기 위해 placeholder 값 우선 확인
    id_el = pw_el = None

    # placeholder 기반으로 아이디 필드 탐색
    for sel in [
        'input[placeholder="아이디"]',
        'input[placeholder*="아이디"]',
        'input[name="userId"]', 'input[name="id"]', 'input[name="loginId"]',
        'input[name="username"]', 'input[type="text"]',
    ]:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            id_el = els[0]
            break

    for sel in [
        'input[placeholder="비밀번호"]',
        'input[placeholder*="비밀번호"]',
        'input[name="userPw"]', 'input[name="pw"]',
        'input[name="password"]', 'input[name="passwd"]',
        'input[type="password"]',
    ]:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        if els:
            pw_el = els[0]
            break

    if not id_el or not pw_el:
        driver.save_screenshot(str(OUTPUT_DIR / "login_debug.png"))
        raise RuntimeError("로그인 폼을 찾지 못했습니다. login_debug.png 확인")

    log(f"  로그인 폼 발견 → 입력 중...")
    _fill_and_submit(driver, id_el, pw_el)
    time.sleep(2)
    log(f"  로그인 후 URL: {driver.current_url}")


def _has_login_button(driver: Chrome) -> bool:
    """네비게이션에 '로그인' 링크가 있으면 미로그인 상태."""
    for a in driver.find_elements(By.TAG_NAME, "a"):
        try:
            if a.text.strip() == "로그인":
                return True
        except Exception:
            pass
    return False


def _do_login_via_nav(driver: Chrome):
    """index.iv 의 네비게이션 '로그인' 버튼 클릭 → 로그인 폼 처리"""
    # 네비게이션의 로그인 링크 클릭
    for a in driver.find_elements(By.TAG_NAME, "a"):
        try:
            if a.text.strip() == "로그인":
                login_href = a.get_attribute("href") or ""
                if login_href:
                    driver.get(login_href)
                else:
                    a.click()
                time.sleep(1.5)
                break
        except Exception:
            pass
    else:
        # 링크를 못 찾으면 직접 LOGIN_URL로 이동
        driver.get(LOGIN_URL)
        time.sleep(1.5)

    # 아이디/비밀번호 입력
    if LOGIN_ID and LOGIN_PW:
        do_login(driver)


def ensure_logged_in(driver: Chrome, headless: bool) -> bool:
    """로그인 여부 확인 → 필요 시 처리

    흐름:
      1. index.iv 로 이동해서 네비게이션에 '로그인' 버튼이 있는지 확인
      2. 로그인 버튼이 없으면 이미 로그인된 상태 → 콘텐츠 페이지로 이동
      3. 로그인 버튼이 있으면:
         - LOGIN_ID/PW 설정 시 → 자동 로그인
         - 미설정 시 → 브라우저에서 수동 로그인 대기
    """
    log(f"진입점으로 이동: {ENTRY_URL}")
    driver.get(ENTRY_URL)
    time.sleep(2)

    if not _has_login_button(driver):
        # 이미 로그인된 상태 — 콘텐츠 메인으로 이동
        log("✓ 이미 로그인된 상태입니다.")
        driver.get(MAIN_URL)
        time.sleep(2)
        log(f"✓ 콘텐츠 페이지 이동 완료 → {driver.current_url}")
        return True

    log("⚠ 로그인이 필요합니다.")

    # ── 자동 로그인 (아이디/비밀번호 설정 시) ────────────────────────────────
    if LOGIN_ID and LOGIN_PW:
        _do_login_via_nav(driver)
        time.sleep(2)
        driver.get(MAIN_URL)
        time.sleep(2)
        if not _has_login_button(driver):
            log(f"✓ 로그인 성공 → {driver.current_url}")
            return True
        log("✗ 로그인 실패. LOGIN_ID/PW를 확인하세요.")
        return False

    # ── 수동 로그인 대기 (UI 모드) ────────────────────────────────────────────
    if not headless:
        _do_login_via_nav(driver)   # 로그인 페이지로 이동만 해줌
        log("  브라우저에서 로그인을 완료한 후 이 터미널에서 Enter를 눌러주세요...")
        input()
        driver.get(MAIN_URL)
        time.sleep(2)
        if not _has_login_button(driver):
            log(f"✓ 로그인 확인 → {driver.current_url}")
            return True
        log("✗ 로그인이 확인되지 않습니다.")
        return False

    # ── Headless 에서 세션 없음 ───────────────────────────────────────────────
    log("  Headless 모드에서 세션이 없습니다.")
    log("  Phase 1 을 먼저 실행하거나 LOGIN_ID/PW 를 설정하세요.")
    return False


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — 사이트 분석
# ══════════════════════════════════════════════════════════════════════════════

def find_section_urls(driver: Chrome) -> dict[str, str]:
    """현재 페이지에서 대상 섹션 링크를 찾는다."""
    log(f"섹션 URL 탐색 중: {driver.current_url}")
    found: dict[str, str] = {}

    links = driver.find_elements(By.TAG_NAME, "a")
    for a in links:
        try:
            text   = a.text.strip()
            href   = a.get_attribute("href") or ""
            onclick = a.get_attribute("onclick") or ""
        except Exception:
            continue

        for section in TARGET_SECTIONS:
            if section in text and section not in found:
                if href and "javascript" not in href:
                    found[section] = href
                else:
                    m = re.search(r"['\"](/[^'\"]+)['\"]", onclick)
                    if m:
                        found[section] = abs_url(m.group(1))

    for k, v in found.items():
        log(f"  ✓ [{k}] → {v}")

    missing = [s for s in TARGET_SECTIONS if s not in found]
    if missing:
        log(f"  ⚠ 못 찾은 섹션: {missing}")
        driver.save_screenshot(str(OUTPUT_DIR / "main_debug.png"))

    return found


def collect_items_from_section(
    driver: Chrome, section_url: str
) -> list[dict]:
    """섹션 목록 페이지를 페이지네이션 포함하여 순회하고 항목 URL을 수집한다."""
    items: list[dict]   = []
    seen_urls: set[str] = set()
    visited:   set[str] = set()
    current_url = section_url
    section_path = urlparse(section_url).path.rstrip("/").rsplit("/", 1)[0]

    while current_url and current_url not in visited:
        visited.add(current_url)
        driver.get(current_url)
        time.sleep(1.5)
        before = len(items)

        for a in driver.find_elements(By.TAG_NAME, "a"):
            try:
                href = a.get_attribute("href") or ""
                text = a.text.strip()
            except Exception:
                continue

            if not href or not text or "javascript" in href:
                continue
            if href in seen_urls:
                continue
            if re.fullmatch(r"\d{1,4}", text):
                continue
            if text in ("다음", "이전", "처음", "마지막", ">", "<", "»", "«"):
                continue

            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc not in BASE_URL:
                continue
            if section_path and not parsed.path.startswith(section_path):
                continue

            items.append({"title": text, "page_url": href})
            seen_urls.add(href)

        log(f"    ({len(visited)}페이지) +{len(items)-before}개 → 누적 {len(items)}개")

        # 다음 페이지
        next_url = None
        for sel in ['a[rel="next"]', "//a[text()='다음']", "//a[text()='>']"]:
            try:
                by = By.XPATH if sel.startswith("//") else By.CSS_SELECTOR
                el = driver.find_element(by, sel)
                href = el.get_attribute("href") or ""
                if href and href not in visited and "javascript" not in href:
                    next_url = href
                    break
            except Exception:
                pass
        current_url = next_url

    return items


def analyze_item(driver: Chrome, item: dict) -> dict:
    """게시물 상세 페이지를 열어 다운로드 방식을 결정한다."""
    url   = item["page_url"]
    title = item["title"]

    result = {
        "title":          title,
        "page_url":       url,
        "download_links": [],
        "use_pdf_print":  False,
    }

    if is_file_url(url):
        ext = Path(urlparse(url).path).suffix.lower()
        result["download_links"].append({
            "url": url, "filename": sanitize(title) + ext
        })
        return result

    try:
        driver.get(url)
        time.sleep(1.5)
    except Exception as e:
        log(f"      ✗ 페이지 열기 실패: {e}")
        result["use_pdf_print"] = True
        return result

    dl_keywords = {"다운로드", "download", "첨부파일", "파일다운", "자료받기", "파일받기"}

    for a in driver.find_elements(By.TAG_NAME, "a"):
        try:
            href     = a.get_attribute("href") or ""
            text     = (a.text or "").strip().lower()
            dl_attr  = a.get_attribute("download")
        except Exception:
            continue

        if not href or "javascript" in href:
            continue

        is_keyword  = any(kw in text for kw in dl_keywords)
        is_file_ext = is_file_url(href)
        has_dl_attr = bool(dl_attr)

        if is_keyword or is_file_ext or has_dl_attr:
            ext   = Path(urlparse(href).path).suffix.lower() or ""
            fname = sanitize(title) + ext
            entry = {"url": href, "filename": fname}
            if entry not in result["download_links"]:
                result["download_links"].append(entry)

    if not result["download_links"]:
        result["use_pdf_print"] = True

    return result


def run_phase1(driver: Chrome):
    """Phase 1: UI 모드로 사이트 구조 분석 → site_map.json 저장"""
    log("\n" + "═" * 60)
    log("Phase 1 시작: 사이트 구조 분석 (UI 모드)")
    log("═" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    section_urls = find_section_urls(driver)
    if not section_urls:
        log("섹션을 찾지 못했습니다. main_debug.png 를 확인하세요.")
        return

    site_map = {
        "base_url":    BASE_URL,
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sections":    {},
    }

    for section_name, section_url in section_urls.items():
        log(f"\n{'─' * 50}")
        log(f"섹션: [{section_name}]  {section_url}")

        items_raw = collect_items_from_section(driver, section_url)
        log(f"  총 {len(items_raw)}개 → 상세 분석 중...")

        analyzed = []
        for idx, item in enumerate(items_raw, 1):
            log(f"  [{idx:3}/{len(items_raw)}] {item['title'][:60]}")
            result = analyze_item(driver, item)
            dl_count = len(result["download_links"])
            method   = f"직접다운로드 {dl_count}개" if dl_count else "PDF 인쇄"
            log(f"         → {method}")
            analyzed.append(result)
            time.sleep(PAGE_DELAY)

        site_map["sections"][section_name] = {
            "section_url": section_url,
            "items":       analyzed,
        }

    # site_map.json 저장
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        json.dump(site_map, f, ensure_ascii=False, indent=2)

    # 세션 쿠키 저장 (Phase 2 headless 모드에서 재사용)
    save_cookies(driver)

    total = sum(len(s["items"]) for s in site_map["sections"].values())
    log(f"\n✓ site_map.json 저장 완료 ({total}개 항목)")
    log(f"  경로: {SITEMAP_PATH}")
    log("\n  ▶ 내용을 검토한 뒤 Phase 2 를 실행하세요:")
    log("    python download_materials.py --phase 2")


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — 다운로드
# ══════════════════════════════════════════════════════════════════════════════

def wait_for_download(download_dir: Path, timeout: int = DOWNLOAD_TIMEOUT) -> Path | None:
    """다운로드 폴더에서 완료된 파일을 기다린다."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        files = [
            f for f in download_dir.iterdir()
            if f.is_file() and f.suffix not in (".crdownload", ".tmp", ".part")
        ]
        inprog = list(download_dir.glob("*.crdownload"))
        if files and not inprog:
            # 가장 최근 파일 반환
            return max(files, key=lambda f: f.stat().st_mtime)
        time.sleep(0.5)
    return None


def download_file(driver: Chrome, url: str, save_path: Path) -> bool:
    """파일 URL로 이동 → Chrome이 자동 저장 → 완료 후 목적지로 이동"""
    # 임시 다운로드 폴더 비우기
    TEMP_DL_DIR.mkdir(parents=True, exist_ok=True)
    for f in TEMP_DL_DIR.iterdir():
        f.unlink(missing_ok=True)

    try:
        driver.get(url)
        downloaded = wait_for_download(TEMP_DL_DIR)
        if not downloaded:
            log(f"    ✗ 다운로드 시간 초과: {url}")
            return False

        # suggested_filename 우선 사용
        final_name = save_path.parent / sanitize(downloaded.name)
        if final_name.exists():
            log(f"    ○ 이미 존재, 스킵: {final_name.name}")
            return True

        shutil.move(str(downloaded), str(final_name))
        log(f"    ✓ 저장: {final_name.name}")
        return True
    except Exception as e:
        log(f"    ✗ 다운로드 실패: {e}")
        return False


def save_as_pdf(driver: Chrome, url: str, save_path: Path) -> bool:
    """Page.printToPDF CDP 명령으로 페이지를 PDF로 저장"""
    try:
        driver.get(url)
        time.sleep(1.5)

        result = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "paperWidth":  8.27,    # A4 (인치)
            "paperHeight": 11.69,
            "marginTop":   0.4,
            "marginBottom":0.4,
            "marginLeft":  0.4,
            "marginRight": 0.4,
        })
        pdf_bytes = base64.b64decode(result["data"])
        save_path.write_bytes(pdf_bytes)
        log(f"    ✓ PDF: {save_path.name}")
        return True
    except Exception as e:
        log(f"    ✗ PDF 실패: {e}")
        return False


def run_phase2(driver: Chrome):
    """Phase 2: Headless 모드 — site_map.json 기반 일괄 다운로드"""
    log("\n" + "═" * 60)
    log("Phase 2 시작: 일괄 다운로드 (Headless 모드)")
    log("═" * 60)

    if not SITEMAP_PATH.exists():
        log(f"✗ site_map.json 없음: {SITEMAP_PATH}")
        log("  Phase 1 을 먼저 실행하세요.")
        return

    with open(SITEMAP_PATH, encoding="utf-8") as f:
        site_map = json.load(f)
    log(f"  분석 시각: {site_map.get('analyzed_at', '?')}")

    ok_count = fail_count = 0

    for section_name, section_data in site_map["sections"].items():
        items = section_data.get("items", [])
        log(f"\n{'─' * 50}")
        log(f"섹션: [{section_name}]  ({len(items)}개)")

        section_dir = OUTPUT_DIR / sanitize(section_name)
        section_dir.mkdir(parents=True, exist_ok=True)

        for idx, item in enumerate(items, 1):
            title     = item.get("title", f"item_{idx}")
            dl_links  = item.get("download_links", [])
            use_pdf   = item.get("use_pdf_print", False)
            page_url  = item.get("page_url", "")

            log(f"  [{idx:3}/{len(items)}] {title[:60]}")

            # ── 직접 다운로드 ─────────────────────────────────────────────
            if dl_links:
                for dl in dl_links:
                    dl_url   = dl.get("url", "")
                    filename = sanitize(dl.get("filename") or title)
                    save_path = section_dir / filename

                    if save_path.exists():
                        log(f"    ○ 스킵 (이미 존재): {save_path.name}")
                        ok_count += 1
                        continue

                    success = download_file(driver, dl_url, save_path)
                    ok_count   += int(success)
                    fail_count += int(not success)
                    time.sleep(PAGE_DELAY)

            # ── PDF 인쇄 ──────────────────────────────────────────────────
            elif use_pdf and page_url:
                pdf_path = section_dir / (sanitize(title) + ".pdf")
                if pdf_path.exists():
                    log(f"    ○ 스킵 (이미 존재): {pdf_path.name}")
                    ok_count += 1
                    continue

                success = save_as_pdf(driver, page_url, pdf_path)
                ok_count   += int(success)
                fail_count += int(not success)
                time.sleep(PAGE_DELAY)

            else:
                log(f"    ─ 처리 대상 없음")

    log(f"\n{'═' * 60}")
    log(f"완료!  성공: {ok_count}  실패: {fail_count}")
    log(f"저장 위치: {OUTPUT_DIR}")


# ══════════════════════════════════════════════════════════════════════════════
# 진입점
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="learninvest.co.kr 강의자료 다운로드 (Selenium)"
    )
    parser.add_argument(
        "--phase", type=int, choices=[1, 2], required=True,
        help="1: 사이트 분석 (UI 모드)  |  2: 일괄 다운로드 (Headless 모드)",
    )
    args = parser.parse_args()

    headless = (args.phase == 2)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DL_DIR.mkdir(parents=True, exist_ok=True)

    driver, _ = build_driver(headless=headless, download_dir=TEMP_DL_DIR)

    try:
        # Phase 2: 쿠키로 세션 복원 시도 → 실패 시 일반 로그인
        if headless and COOKIES_PATH.exists():
            log("저장된 쿠키로 세션 복원 시도...")
            load_cookies(driver)

        ok = ensure_logged_in(driver, headless=headless)
        if not ok:
            return

        if args.phase == 1:
            run_phase1(driver)
        else:
            run_phase2(driver)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
