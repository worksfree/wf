// @ts-check
/**
 * asset-demo.spec.js — 자산 통합 관리 페이지 종합 검증
 *
 * 검증 범위:
 *  1. 소스 코드 구조 (관리자 게이트, 워터마크, 스냅샷 방어로직)
 *  2. 비로그인 데모 모드 DOM/UI
 *  3. 관리자 전용 UI 요소
 *  4. 스냅샷 함수 동작
 *
 * 주의: 실제 Supabase 세션 없이 페이지를 직접 로드하여 검증 (비로그인 = 데모 모드)
 */
const { test, expect } = require('@playwright/test');

const ASSET_PAGE = '/consulting/asset/index.html';

// ─────────────────────────────────────────────────────────
// 1. 소스 코드 구조 검증 (무인증 / 소스 검사)
// ─────────────────────────────────────────────────────────

test.describe('Asset — 소스 코드 구조', () => {

  test('asset 페이지 로드 성공 (200)', async ({ page }) => {
    const resp = await page.goto(ASSET_PAGE);
    expect([200, 304]).toContain(resp?.status() ?? 200);
  });

  // ── 관리자 게이트 ───────────────────────────────────────

  test('saveData — if(!sbIsAdmin) return 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    // 비관리자는 saveData 초입에서 즉시 return
    expect(src).toMatch(/if\s*\(\s*!sbIsAdmin\s*\)\s*return/);
  });

  test('loadData — if(!sbIsAdmin) return 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    // 비관리자는 loadData 초입에서 즉시 return
    // saveData와 loadData 둘 다에 있어야 하므로 2회 이상
    const matches = (src.match(/if\s*\(\s*!sbIsAdmin\s*\)\s*return/g) || []).length;
    expect(matches).toBeGreaterThanOrEqual(2);
  });

  test('초기화 블록 — !sbIsAdmin 시 DEMO_HOLDINGS_INIT 복사 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/!sbIsAdmin/);
    expect(src).toMatch(/DEMO_HOLDINGS_INIT/);
    expect(src).toMatch(/isDemoMode\s*=\s*true/);
  });

  // ── 워터마크 구조 ──────────────────────────────────────

  test('demo-overlay — div#demo-overlay 소스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/id="demo-overlay"/);
  });

  test('demo-overlay — wm-main 클래스 소스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/class="wm-main"/);
  });

  test('demo-overlay — wm-pill 클래스 제거됨 (소스에 없어야 함)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).not.toMatch(/wm-pill/);
  });

  test('워터마크 CSS — opacity 0.38 이상 (진하게)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    // rgba(245,158,11,.38) 이상
    expect(src).toMatch(/rgba\(245\s*,\s*158\s*,\s*11\s*,\s*\.(3[5-9]|[4-9]\d?)\)/);
  });

  test('워터마크 CSS — top:33% (상부 1/3 위치)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/\.wm-main[^}]*top:\s*33%/);
  });

  // ── 스냅샷 방어 로직 ──────────────────────────────────

  test('saveQuoteSnapshot — 이상값 스킵 로직 소스 확인 (price > prev * 3)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/price\s*>\s*prev\s*\*\s*3/);
  });

  test('saveQuoteSnapshot — 이상값 스킵 로직 소스 확인 (price < prev / 3)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/price\s*<\s*prev\s*\/\s*3/);
  });

  test('buildMonthlySnapshots — SNAP_KEY fallback 제거됨 (priceSnap 미사용)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    // buildMonthlySnapshots 함수 소스를 직접 평가
    const fnSrc = await page.evaluate(() =>
      typeof window.buildMonthlySnapshots === 'function'
        ? window.buildMonthlySnapshots.toString()
        : ''
    );
    // PORTFOLIO_SNAP_KEY만 사용 — 단독 SNAP_KEY 직접 접근 없어야 함 (부분 매칭 방지: (?<!PORTFOLIO_))
    expect(fnSrc).not.toMatch(/(?<!PORTFOLIO_)SNAP_KEY|priceSnap|priceDates/);
    // PORTFOLIO_SNAP_KEY만 사용
    expect(fnSrc).toMatch(/PORTFOLIO_SNAP_KEY/);
  });

  test('resetSnapshots 함수 소스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/function resetSnapshots/);
  });

  test('snapResetBtn — HTML에 button#snapResetBtn 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/id="snapResetBtn"/);
  });

  // ── updateModeBadge 구조 ──────────────────────────────

  test('updateModeBadge — isDemoMode 시 body.pv 제거 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/isDemoMode.*body\.classList\.remove\('pv'\)|body\.classList\.remove\('pv'\).*isDemoMode/s);
  });

  test('updateModeBadge — snapResetBtn 가시성 제어 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/snapResetBtn/);
    expect(src).toMatch(/snapResetBtn.*style\.display/);
  });

  // ── devClearAssetDB (index.html) ──────────────────────

  test('index.html — devClearAssetDB 함수 소스 존재', async ({ page }) => {
    await page.goto('/');
    const src = await page.content();
    expect(src).toMatch(/devClearAssetDB|dev-btn.*danger/);
  });

});


// ─────────────────────────────────────────────────────────
// 2. DOM 구조 검증 (비로그인 = 데모 모드)
// ─────────────────────────────────────────────────────────

test.describe('Asset — 비로그인 데모 모드 DOM', () => {

  test('demo-overlay 요소 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const overlay = page.locator('#demo-overlay');
    expect(await overlay.count()).toBe(1);
  });

  test('wm-main 요소 존재 (예시 데이터 텍스트)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const wm = page.locator('#demo-overlay .wm-main');
    expect(await wm.count()).toBe(1);
  });

  test('wm-main 텍스트 — 예시 데이터', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const text = await page.locator('#demo-overlay .wm-main').textContent();
    expect(text?.trim()).toBe('예시 데이터');
  });

  test('wm-pill 요소 없음 (제거됨)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.wm-pill').count()).toBe(0);
  });

  test('demo-overlay — 비로그인 시 show 클래스 활성화', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    // 비로그인이므로 sbIsAdmin=false, isDemoMode=true → show 클래스 있어야 함
    await page.waitForTimeout(1000); // 초기화 완료 대기
    const hasShow = await page.evaluate(() =>
      document.getElementById('demo-overlay')?.classList.contains('show') ?? false
    );
    expect(hasShow).toBe(true);
  });

  test('비로그인 — body.pv 클래스 없음 (블러 미적용)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1000);
    const hasPv = await page.evaluate(() =>
      document.body.classList.contains('pv')
    );
    expect(hasPv).toBe(false);
  });

  test('비로그인 — pv-toggle 숨김 (display:none)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1000);
    const visible = await page.evaluate(() => {
      const el = document.querySelector('.pv-toggle');
      if (!el) return null;
      const style = el.style.display || getComputedStyle(el).display;
      return style !== 'none';
    });
    // 비로그인이면 pv-toggle이 없거나 숨겨져야 함
    expect(visible).not.toBe(true);
  });

  test('비로그인 — divSyncBtn 숨김 (demo 모드에서 불필요)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1000);
    const btnDisplay = await page.evaluate(() => {
      const btn = document.getElementById('divSyncBtn');
      if (!btn) return 'none';
      return (btn).style.display || getComputedStyle(btn).display;
    });
    expect(btnDisplay).toBe('none');
  });

  test('비로그인 — snapResetBtn 숨김', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1000);
    const btnDisplay = await page.evaluate(() => {
      const btn = document.getElementById('snapResetBtn');
      if (!btn) return 'none';
      return (btn).style.display || getComputedStyle(btn).display;
    });
    expect(btnDisplay).toBe('none');
  });

  test('비로그인 — modeBadge 숨김', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1000);
    const badgeDisplay = await page.evaluate(() => {
      const el = document.getElementById('modeBadge');
      if (!el) return 'none';
      return (el).style.display || getComputedStyle(el).display;
    });
    expect(badgeDisplay).toBe('none');
  });

  test('비로그인 — 데모 보유 종목 표시됨 (holdings 셀 존재)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(2000); // 렌더 완료 대기
    const rows = await page.locator('#holdingsTbody tr').count();
    expect(rows).toBeGreaterThan(0);
  });

  test('비로그인 — #demo-overlay CSS show 클래스 표시 방식 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    // #demo-overlay.show 가 CSS에서 display:flex 또는 visible되는지 확인
    const src = await page.content();
    expect(src).toMatch(/#demo-overlay\.show|#demo-overlay[^{]*\.show/);
  });

});


// ─────────────────────────────────────────────────────────
// 3. 함수 존재 및 구조 검증
// ─────────────────────────────────────────────────────────

test.describe('Asset — 함수 구조', () => {

  test('buildMonthlySnapshots 함수 존재 (window)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.buildMonthlySnapshots === 'function');
    expect(exists).toBe(true);
  });

  test('saveQuoteSnapshot 함수 존재 (window)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.saveQuoteSnapshot === 'function');
    expect(exists).toBe(true);
  });

  test('savePortfolioSnapshot 함수 존재 (window)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.savePortfolioSnapshot === 'function');
    expect(exists).toBe(true);
  });

  test('resetSnapshots 함수 존재 (window)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.resetSnapshots === 'function');
    expect(exists).toBe(true);
  });

  test('updateModeBadge 함수 존재 (window)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.updateModeBadge === 'function');
    expect(exists).toBe(true);
  });

  test('initDemoSnapshots 함수 존재 (window)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.initDemoSnapshots === 'function');
    expect(exists).toBe(true);
  });

  test('saveLocal 함수 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.saveLocal === 'function');
    expect(exists).toBe(true);
  });

  test('loadLocal 함수 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.loadLocal === 'function');
    expect(exists).toBe(true);
  });

  test('saveData 함수 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.saveData === 'function');
    expect(exists).toBe(true);
  });

  test('refreshQuotes 함수 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.refreshQuotes === 'function');
    expect(exists).toBe(true);
  });

  test('renderCharts 함수 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.renderCharts === 'function');
    expect(exists).toBe(true);
  });

  test('syncDividends 함수 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const exists = await page.evaluate(() => typeof window.syncDividends === 'function');
    expect(exists).toBe(true);
  });

  // ── savePortfolioSnapshot — 관리자 게이트 소스 확인 ──

  test('savePortfolioSnapshot — sbIsAdmin 체크 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const fnSrc = await page.evaluate(() => window.savePortfolioSnapshot?.toString() ?? '');
    expect(fnSrc).toMatch(/sbIsAdmin/);
  });

  // ── buildMonthlySnapshots — PORTFOLIO_SNAP_KEY 전용 ──

  test('buildMonthlySnapshots — PORTFOLIO_SNAP_KEY localStorage 읽기', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const fnSrc = await page.evaluate(() => window.buildMonthlySnapshots?.toString() ?? '');
    expect(fnSrc).toMatch(/PORTFOLIO_SNAP_KEY/);
    // validCount >= 1 반환 로직
    expect(fnSrc).toMatch(/validCount/);
  });

  test('buildMonthlySnapshots — null 반환 시 DEMO_SNAPSHOTS 폴백 (renderCharts)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    // renderCharts에서 real || DEMO_SNAPSHOTS 패턴
    expect(src).toMatch(/DEMO_SNAPSHOTS/);
    expect(src).toMatch(/real\s*\|\|\s*DEMO_SNAPSHOTS/);
  });

  // ── saveQuoteSnapshot 방어 로직 ──────────────────────

  test('saveQuoteSnapshot — 비관리자도 호출 가능 (sbIsAdmin 게이트 없음)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const fnSrc = await page.evaluate(() => window.saveQuoteSnapshot?.toString() ?? '');
    // saveQuoteSnapshot 자체는 관리자 게이트 없음 (시세 저장은 허용)
    expect(fnSrc).not.toMatch(/^.*if.*!sbIsAdmin.*return/m);
  });

  test('saveQuoteSnapshot — prevPrices 참조해 이상값 검사', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const fnSrc = await page.evaluate(() => window.saveQuoteSnapshot?.toString() ?? '');
    expect(fnSrc).toMatch(/prevPrices|prev/);
    expect(fnSrc).toMatch(/\*\s*3|\/\s*3/);
  });

});


// ─────────────────────────────────────────────────────────
// 4. 데모 데이터 상수 구조 확인
// ─────────────────────────────────────────────────────────

test.describe('Asset — 데모 데이터 상수', () => {

  test('DEMO_HOLDINGS_INIT 소스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/DEMO_HOLDINGS_INIT/);
  });

  test('DEMO_NW 소스 존재 (순자산 데모)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/DEMO_NW/);
  });

  test('DEMO_SNAPSHOTS — 12개월 배열 생성 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/DEMO_SNAPSHOTS/);
    // i = 11 → 0 루프 확인
    expect(src).toMatch(/i\s*=\s*11.*i\s*>=\s*0.*i--/s);
  });

  test('DEMO_QUOTES 소스 존재 (비관리자 시세)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/DEMO_QUOTES/);
  });

  test('CODE_MIGRATION — 473150→498400, 471290→475720 매핑 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/'473150'\s*:\s*'498400'/);
    expect(src).toMatch(/'471290'\s*:\s*'475720'/);
  });

  test('SAVE_KEY — asset_mgr_v1 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/SAVE_KEY.*asset_mgr_v1|asset_mgr_v1.*SAVE_KEY/);
  });

  test('SNAP_KEY — asset_snapshots_v1 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/SNAP_KEY.*asset_snapshots_v1|asset_snapshots_v1.*SNAP_KEY/);
  });

  test('PORTFOLIO_SNAP_KEY — asset_portfolio_snap_v1 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/PORTFOLIO_SNAP_KEY.*asset_portfolio_snap_v1|asset_portfolio_snap_v1.*PORTFOLIO_SNAP_KEY/);
  });

});


// ─────────────────────────────────────────────────────────
// 5. UI 구조 검증 (탭, 버튼, 레이아웃)
// ─────────────────────────────────────────────────────────

test.describe('Asset — UI 구조', () => {

  test('헤더 제목 — 자산 통합 관리', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const title = await page.locator('.hdr-title').textContent();
    expect(title?.trim()).toMatch(/자산 통합 관리/);
  });

  test('탭 버튼 — 포트폴리오 탭 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const tab = page.locator('[id*="tabBtn"], .tab-btn').first();
    expect(await tab.count()).toBeGreaterThan(0);
  });

  test('시세갱신 버튼 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const btn = page.locator('button:has-text("시세갱신"), button:has-text("↻ 시세갱신")');
    expect(await btn.count()).toBeGreaterThan(0);
  });

  test('내보내기 버튼 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const btn = page.locator('button:has-text("내보내기")');
    expect(await btn.count()).toBeGreaterThan(0);
  });

  test('trendChart 캔버스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#trendChart').count()).toBe(1);
  });

  test('weightChart 캔버스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#weightChart').count()).toBeGreaterThan(0);
  });

  test('#modeBadge 요소 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#modeBadge').count()).toBe(1);
  });

  test('snapResetBtn 요소 존재 (초기 display:none)', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#snapResetBtn').count()).toBe(1);
  });

  test('snapResetBtn 초기 display:none', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const display = await page.locator('#snapResetBtn').getAttribute('style');
    expect(display).toMatch(/display:\s*none/);
  });

  test('divSyncBtn 요소 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#divSyncBtn').count()).toBe(1);
  });

  test('histModal 또는 변동 이력 모달 소스 존재', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/histModal|histChart|변동 이력/);
  });

  test('pv-toggle — body.pv 토글 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/body\.classList\.toggle\('pv'/);
  });

  test('Chart.js CDN 로드됨', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/chart\.js|chart\.umd/i);
  });

  test('WORKER_BASE — CF Worker URL 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/asset-api\.worksfree\.workers\.dev/);
  });

  test('SUPABASE_URL — 소스 확인', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/rkycwfpkzorfpcxfvaqt\.supabase\.co/);
  });

});


// ─────────────────────────────────────────────────────────
// 6. 비로그인 시 localStorage 보호 (관리자 데이터 오염 방지)
// ─────────────────────────────────────────────────────────

test.describe('Asset — localStorage 보안', () => {

  test('비로그인 — asset_mgr_v1 localStorage에 쓰지 않음', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(2000); // 초기화 완료 대기

    const saved = await page.evaluate(() => localStorage.getItem('asset_mgr_v1'));
    // 비로그인(비관리자) 상태에서는 saveData/saveLocal이 실행되지 않아야 함
    // (saveData if(!sbIsAdmin) return → saveLocal도 saveData 안에서만 호출)
    // 단, initDemoSnapshots는 SNAP_KEY에 쓸 수 있음 (별도 키)
    expect(saved).toBeNull();
  });

  test('비로그인 — 페이지 재방문 시 동일한 데모 데이터 표시 (localStorage 오염 없음)', async ({ page }) => {
    // 1차 방문
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1500);

    // 2차 방문 후 데모 워터마크 확인
    await page.goto(ASSET_PAGE);
    await page.waitForTimeout(1500);

    const hasShow = await page.evaluate(() =>
      document.getElementById('demo-overlay')?.classList.contains('show') ?? false
    );
    expect(hasShow).toBe(true);
  });

  test('saveData — 소스에 async 함수로 정의됨', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/async\s+function\s+saveData/);
  });

  test('loadData — 소스에 async 함수로 정의됨', async ({ page }) => {
    await page.goto(ASSET_PAGE);
    const src = await page.content();
    expect(src).toMatch(/async\s+function\s+loadData/);
  });

});
