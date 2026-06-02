"""
jobkorea_auto.py — 잡코리아 인재검색 & 포지션 제안 자동화 (Playwright)

사용법:
  python jobkorea_auto.py                  # 기본 실행
  python jobkorea_auto.py --dry-run        # 실제 발송 없이 후보자만 수집
  python jobkorea_auto.py --limit 10       # 최대 10명에게만 발송

실행 전 준비:
  pip install -r requirements.txt
  playwright install chromium
  .env 파일에 JOBKOREA_ID, JOBKOREA_PW, SUPABASE_URL, SUPABASE_SERVICE_KEY 설정
"""

import asyncio
import argparse
import os
import re
import json
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

load_dotenv()

# ── 환경변수 ─────────────────────────────────────────────────────────
JOBKOREA_ID   = os.getenv('JOBKOREA_ID', '')
JOBKOREA_PW   = os.getenv('JOBKOREA_PW', '')
SUPABASE_URL  = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY  = os.getenv('SUPABASE_SERVICE_KEY', '')
KEYWORDS_RAW  = os.getenv('SEARCH_KEYWORDS', '법인영업')
KEYWORDS      = [k.strip() for k in KEYWORDS_RAW.split(',') if k.strip()]
MAX_PAGES     = int(os.getenv('SEARCH_MAX_PAGES', '3'))
HEADLESS      = os.getenv('HEADLESS', 'false').lower() == 'true'
DELAY_SEC     = float(os.getenv('DELAY_BETWEEN_CANDIDATES', '2'))
PROFILE_DIR   = os.getenv('PROFILE_DIR', str(Path.home() / '.jobkorea_profile'))

TALENT_URL    = 'https://www.jobkorea.co.kr/Recruit/Co_Read/C/personsearch'
LOGIN_URL     = 'https://www.jobkorea.co.kr/Login'

# ── 메시지 템플릿 로드 ─────────────────────────────────────────────────
def load_template() -> str:
    tmpl_path = os.getenv('PROPOSAL_TEMPLATE_FILE', '')
    if tmpl_path and Path(tmpl_path).exists():
        return Path(tmpl_path).read_text(encoding='utf-8')
    return """\
안녕하세요, {name}님!

삼성생명(주)에서 채용의뢰를 받은 용산HR 이인성 팀장입니다.

{name}님의 {career_short} 경험이 매우 인상적이어서 연락드립니다.

현재 삼성생명 법인영업(GFC) 포지션을 모집 중입니다.
기업 CEO를 대상으로 세무·재무·리스크 컨설팅을 담당하는 전문직으로,
입사 후 13개월간 세무사·회계사·노무사 강의와 1:1 멘토링을 제공합니다.

10분 정도 편하신 시간에 통화 가능할까요?

이인성 팀장 | 삼성생명 용산HR
"""

PROPOSAL_TEMPLATE = load_template()

# ── Supabase 헬퍼 ─────────────────────────────────────────────────────
def sb_headers() -> dict:
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }

async def get_already_sent(client: httpx.AsyncClient) -> set[str]:
    """이미 제안한 후보자 ID 집합 반환 (중복 방지)"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return set()
    try:
        r = await client.get(
            f'{SUPABASE_URL}/rest/v1/jobkorea_proposals?select=candidate_id&limit=10000',
            headers=sb_headers(),
        )
        if r.status_code == 200:
            return {row['candidate_id'] for row in r.json()}
    except Exception as e:
        print(f'[Supabase] 기발송 목록 조회 실패: {e}')
    return set()

async def record_proposal(client: httpx.AsyncClient, row: dict) -> bool:
    """발송 기록 저장"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        r = await client.post(
            f'{SUPABASE_URL}/rest/v1/jobkorea_proposals',
            headers={**sb_headers(), 'Prefer': 'resolution=merge-duplicates,return=minimal'},
            json=row,
        )
        return r.status_code in (200, 201, 204)
    except Exception as e:
        print(f'[Supabase] 기록 실패: {e}')
        return False

# ── 팝업·얼럿 처리 ───────────────────────────────────────────────────
async def close_popups(page):
    """일반적인 팝업 닫기 시도"""
    for sel in ['button.btn-close', '.layer-close', '.popup-close', 'button:has-text("닫기")', 'button:has-text("확인")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=800):
                await btn.click()
                await asyncio.sleep(0.3)
        except Exception:
            pass

async def dismiss_alert(page) -> str | None:
    """alert 닫기 (있으면 텍스트 반환)"""
    try:
        dlg_text = []
        page.once('dialog', lambda d: (dlg_text.append(d.message), asyncio.create_task(d.accept())))
        await asyncio.sleep(0.5)
        return dlg_text[0] if dlg_text else None
    except Exception:
        return None

# ── 로그인 ────────────────────────────────────────────────────────────
async def ensure_logged_in(page) -> bool:
    """로그인 상태 확인, 필요시 로그인"""
    await page.goto(TALENT_URL, wait_until='domcontentloaded')
    await asyncio.sleep(1.5)
    await close_popups(page)

    # 이미 로그인 상태면 인재검색 URL에 그대로 있음
    if TALENT_URL.split('?')[0] in page.url:
        print('[로그인] 기존 세션 재사용 ✓')
        return True

    # 로그인 페이지로 이동
    print('[로그인] 세션 만료 → 재로그인 시도...')
    await page.goto(LOGIN_URL, wait_until='domcontentloaded')
    await asyncio.sleep(1)

    try:
        await page.fill('input[name="id"]', JOBKOREA_ID, timeout=5000)
        await page.fill('input[name="pw"]', JOBKOREA_PW, timeout=5000)
        await page.click('button[type="submit"], input[type="submit"]', timeout=5000)
        await asyncio.sleep(2)
        await close_popups(page)

        # 로그인 성공 확인
        await page.goto(TALENT_URL, wait_until='domcontentloaded')
        await asyncio.sleep(1.5)
        if TALENT_URL.split('?')[0] in page.url:
            print('[로그인] 성공 ✓')
            return True
        print('[로그인] 실패 — 아이디/비밀번호 확인 필요')
        return False
    except Exception as e:
        print(f'[로그인] 오류: {e}')
        return False

# ── 후보자 수집 ───────────────────────────────────────────────────────
async def collect_candidates(page, keyword: str, max_pages: int) -> list[dict]:
    """키워드로 후보자 목록 수집"""
    candidates = []
    print(f'\n[수집] 키워드: "{keyword}" · 최대 {max_pages}페이지')

    # 검색창 입력
    search_box = None
    for sel in ['input[name="stext"]', '#searchText', 'input[placeholder*="검색"]', 'input[type="search"]']:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=1500):
                search_box = el
                break
        except Exception:
            pass

    if not search_box:
        print('[수집] 검색창을 찾을 수 없음')
        return candidates

    await search_box.fill(keyword)
    await search_box.press('Enter')
    await asyncio.sleep(2)
    await close_popups(page)

    for pg in range(1, max_pages + 1):
        print(f'  페이지 {pg}/{max_pages} 수집 중...')
        await asyncio.sleep(1)

        # 후보자 카드/행 추출
        items = []
        for sel in ['.resumeList li', '.person-item', 'li.people-item', '.userinfo-wrap', 'tr.resume-row']:
            items = await page.locator(sel).all()
            if items:
                break

        if not items:
            print(f'  후보자 목록 없음 (페이지 {pg})')
            break

        for item in items:
            try:
                # 이름
                name = ''
                for ns in ['.name', '.userName', 'strong.name', '.user-name', 'td.name']:
                    try:
                        name = (await item.locator(ns).first.inner_text(timeout=500)).strip()
                        if name:
                            break
                    except Exception:
                        pass

                # 경력 요약
                career = ''
                for cs in ['.career', '.userCareer', '.career-info', 'td.career']:
                    try:
                        career = (await item.locator(cs).first.inner_text(timeout=500)).strip()
                        if career:
                            break
                    except Exception:
                        pass

                # 후보자 ID (URL 또는 data 속성)
                cid = ''
                for id_attr in ['data-uIdx', 'data-idx', 'data-person-idx']:
                    cid = await item.get_attribute(id_attr) or ''
                    if cid:
                        break

                if not cid:
                    # 포지션 제안 링크에서 ID 추출
                    try:
                        link = await item.locator('a[href*="uIdx"], a[href*="idx"]').first.get_attribute('href', timeout=500)
                        m = re.search(r'[uU]?[Ii]dx=(\d+)', link or '')
                        if m:
                            cid = m.group(1)
                    except Exception:
                        pass

                if not cid or not name:
                    continue

                candidates.append({
                    'candidate_id': cid,
                    'name': name,
                    'career': career,
                    'keyword': keyword,
                })
            except Exception:
                continue

        # 다음 페이지
        if pg < max_pages:
            try:
                next_btn = page.locator(f'a[href*="page={pg+1}"], .paging a:has-text("{pg+1}")').first
                if await next_btn.is_visible(timeout=1500):
                    await next_btn.click()
                    await asyncio.sleep(1.5)
                else:
                    break
            except Exception:
                break

    print(f'  수집 완료: {len(candidates)}명')
    return candidates

# ── 포지션 제안 발송 ──────────────────────────────────────────────────
async def send_proposal(page, candidate: dict, dry_run: bool) -> tuple[str, str]:
    """
    포지션 제안 발송
    반환: (status, notes)  status = 'sent' | 'error' | 'skipped'
    """
    cid     = candidate['candidate_id']
    name    = candidate['name']
    career  = candidate['career']
    career_short = career[:20] if career else '풍부한'

    message = PROPOSAL_TEMPLATE.format(name=name, career_short=career_short)

    if dry_run:
        print(f'  [DRY-RUN] {name} ({cid}) — 발송 스킵')
        return 'skipped', 'dry-run'

    # 포지션 제안 버튼 클릭 시도
    try:
        # 해당 후보자 행 찾기
        proposal_btn = None
        for sel in [
            f'[data-uIdx="{cid}"] button:has-text("포지션")',
            f'[data-idx="{cid}"] button:has-text("포지션")',
            f'a[href*="uIdx={cid}"]',
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=500):
                    proposal_btn = el
                    break
            except Exception:
                pass

        if not proposal_btn:
            return 'error', '포지션 제안 버튼 없음'

        await proposal_btn.click()
        await asyncio.sleep(1.5)
        await close_popups(page)

        # 메시지 입력창 찾기
        for ms in ['textarea.message', '#proposalMsg', 'textarea[name="message"]', 'textarea']:
            try:
                ta = page.locator(ms).first
                if await ta.is_visible(timeout=1500):
                    await ta.fill(message)
                    break
            except Exception:
                pass

        # 발송 버튼 클릭
        for ss in ['button:has-text("발송")', 'button:has-text("제안")', 'input[value="발송"]']:
            try:
                btn = page.locator(ss).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await asyncio.sleep(1.5)
                    print(f'  ✅ 발송: {name} ({cid})')
                    return 'sent', message
            except Exception:
                pass

        return 'error', '발송 버튼 클릭 실패'

    except PWTimeoutError:
        return 'error', 'Timeout'
    except Exception as e:
        return 'error', str(e)[:200]

# ── 메인 ─────────────────────────────────────────────────────────────
async def main(dry_run: bool = False, limit: int = 0):
    if not JOBKOREA_ID or not JOBKOREA_PW:
        print('[오류] .env 파일에 JOBKOREA_ID, JOBKOREA_PW를 설정하세요')
        return

    async with httpx.AsyncClient(timeout=15) as http:
        # 기발송 목록 로드 (중복 방지)
        already_sent = await get_already_sent(http)
        print(f'[중복 방지] 기발송 {len(already_sent)}건 로드 완료')

        async with async_playwright() as pw:
            browser = await pw.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ],
                ignore_https_errors=True,
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()

            # 로그인 확인
            if not await ensure_logged_in(page):
                await browser.close()
                return

            total_sent = 0

            for keyword in KEYWORDS:
                # 후보자 수집
                candidates = await collect_candidates(page, keyword, MAX_PAGES)

                # 이미 발송한 후보자 제외
                new_candidates = [c for c in candidates if c['candidate_id'] not in already_sent]
                print(f'[필터] 신규 {len(new_candidates)}명 (전체 {len(candidates)}명 중 {len(candidates)-len(new_candidates)}명 중복 제외)')

                if limit:
                    new_candidates = new_candidates[:limit - total_sent]

                # 포지션 제안 발송
                for cand in new_candidates:
                    if limit and total_sent >= limit:
                        print(f'[제한] 최대 {limit}건 도달 — 종료')
                        break

                    status, notes = await send_proposal(page, cand, dry_run)

                    if not dry_run:
                        await record_proposal(http, {
                            'candidate_id': cand['candidate_id'],
                            'name':         cand['name'],
                            'career':       cand['career'],
                            'keyword':      keyword,
                            'status':       status,
                            'message_used': notes if status == 'sent' else None,
                            'notes':        None if status == 'sent' else notes,
                        })

                    if status == 'sent':
                        already_sent.add(cand['candidate_id'])
                        total_sent += 1

                    await asyncio.sleep(DELAY_SEC)

            await browser.close()

        print(f'\n[완료] 총 {total_sent}건 발송')

# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='잡코리아 포지션 제안 자동화')
    parser.add_argument('--dry-run', action='store_true', help='실제 발송 없이 후보자만 수집')
    parser.add_argument('--limit',   type=int, default=0,  help='최대 발송 건수 (0=무제한)')
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, limit=args.limit))
