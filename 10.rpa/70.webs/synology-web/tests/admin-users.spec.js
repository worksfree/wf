// ================================================================
// admin-users.spec.js  —  사용자 관리 / 타코매니저 UI 검증 (mock 모드)
//
// 실행: npx playwright test tests/admin-users.spec.js
//
// 검증 전략:
//   1. wf_dev_session=admin  →  auth 우회
//   2. page.route()로 Supabase CDN 스크립트를 mock JS로 교체
//      → 네트워크 요청 없이 즉시 mock 데이터 반환
//   3. 실제 DB 검증은 .realdb.spec.js 에서 별도 실행
// ================================================================
const { test, expect } = require('@playwright/test');

/* ── Mock 데이터 ── */
const MOCK_PROFILES = [
  { id: 'd0000001-0000-4000-8000-000000000000', email: 'admin@test.com',   name: '관리자',    role: 'admin',      agreed_at: '2025-01-01T00:00:00Z' },
  { id: 'd0000002-0000-4000-8000-000000000000', email: 'user1@test.com',   name: '테스트유저1', role: 'general',    agreed_at: '2025-02-01T00:00:00Z' },
  { id: 'd0000003-0000-4000-8000-000000000000', email: 'consult@test.com', name: '컨설턴트',   role: 'consultant', agreed_at: '2025-03-01T00:00:00Z' },
];
const MOCK_CREDITS = [
  { user_id: 'd0000002-0000-4000-8000-000000000000', balance: 500, total_charged: 1000, total_used: 500 },
];
const MOCK_LOGINS  = [
  { id: 'd0000001-0000-4000-8000-000000000000', last_sign_in_at: new Date(Date.now() - 86400000).toISOString() },
  { id: 'd0000002-0000-4000-8000-000000000000', last_sign_in_at: new Date(Date.now() - 10 * 86400000).toISOString() },
];

/** Supabase CDN 스크립트를 완전한 mock JS로 교체 */
function buildMockSupabaseScript(profiles, credits, logins, session = true) {
  return `
(function() {
  "use strict";
  var _profiles = ${JSON.stringify(profiles)};
  var _credits  = ${JSON.stringify(credits)};
  var _logins   = ${JSON.stringify(logins)};
  var _session  = ${session ? JSON.stringify({ user: { id: profiles[0].id } }) : 'null'};

  function makeQuery(rows) {
    var q = {
      _rows: rows,
      select: function() { return q; },
      eq:     function() { return q; },
      order:  function() { return q; },
      limit:  function() { return q; },
      'in':   function() { return q; },
      then: function(resolve, reject) {
        Promise.resolve({ data: q._rows, error: null }).then(resolve, reject);
      },
      catch: function() { return q; },
      maybeSingle: function() { return Promise.resolve({ data: q._rows[0] || null, error: null }); },
      single:      function() { return Promise.resolve({ data: q._rows[0] || null, error: null }); },
    };
    return q;
  }

  var mockClient = {
    auth: {
      getSession: function() {
        return Promise.resolve({ data: { session: _session }, error: null });
      },
      onAuthStateChange: function() {
        return { data: { subscription: { unsubscribe: function() {} } } };
      },
    },
    from: function(table) {
      if (table === 'profiles')       return makeQuery(_profiles);
      if (table === 'credit_balance') return makeQuery(_credits);
      if (table === 'page_views')     return makeQuery([]);
      return makeQuery([]);
    },
    rpc: function(fn) {
      if (fn === 'admin_get_all_profiles') return Promise.resolve({ data: _profiles, error: null });
      if (fn === 'admin_get_user_logins')  return Promise.resolve({ data: _logins,   error: null });
      if (fn === 'admin_page_view_stats')  return Promise.resolve({ data: [],        error: null });
      return Promise.resolve({ data: null, error: { message: 'mock: unknown rpc ' + fn } });
    },
  };

  window.supabase = {
    createClient: function() { return mockClient; },
  };
})();
`;
}

/** 공통 셋업: Supabase CDN mock + dev session */
async function setupMock(page, opts = {}) {
  const {
    profiles = MOCK_PROFILES,
    credits  = MOCK_CREDITS,
    logins   = MOCK_LOGINS,
    session  = true,
  } = opts;

  // dev session for auth bypass
  await page.addInitScript(() => {
    window.localStorage.setItem('wf_dev_session', 'admin');
  });

  // Supabase CDN JS → mock JS로 교체
  await page.route(/cdn\.jsdelivr\.net\/npm\/@supabase\/supabase-js/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: buildMockSupabaseScript(profiles, credits, logins, session),
    });
  });
}

/** 미인증 mock: session=null 반환 */
async function setupDeniedMock(page) {
  await page.route(/cdn\.jsdelivr\.net\/npm\/@supabase\/supabase-js/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/javascript; charset=utf-8',
      body: buildMockSupabaseScript(MOCK_PROFILES, [], [], false),
    });
  });
}

/* ─────────────────────────────────────────────
   사용자 관리 페이지 테스트
───────────────────────────────────────────── */
test.describe('사용자 관리 페이지 (admin/users)', () => {

  test('페이지 로드 — #app 가시화', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await expect(page.locator('#app')).toBeVisible({ timeout: 5000 });
  });

  test('탭 2개 (회원 목록 / 역할·크레딧)', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#app').waitFor({ state: 'visible', timeout: 5000 });

    await expect(page.locator('.tab-btn')).toHaveCount(2);
    await expect(page.locator('.tab-btn').nth(0)).toContainText('회원 목록');
    await expect(page.locator('.tab-btn').nth(1)).toContainText('역할');
  });

  test('회원 목록 — mock 3명 행 표시', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#app').waitFor({ state: 'visible', timeout: 5000 });

    await expect(page.locator('#member-tbody tr')).toHaveCount(3, { timeout: 5000 });
  });

  test('status-bar — 로딩 완료 후 인원 수 표시', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#app').waitFor({ state: 'visible', timeout: 5000 });

    await expect(page.locator('#member-status')).not.toHaveText('로딩 중…', { timeout: 5000 });
    await expect(page.locator('#member-status')).toContainText('3명 표시', { timeout: 5000 });
  });

  test('통계 카드 — 총 3명, 관리자 1명', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#app').waitFor({ state: 'visible', timeout: 5000 });

    await expect(page.locator('#cnt-total')).toHaveText('3', { timeout: 5000 });
    await expect(page.locator('#cnt-admin')).toHaveText('1', { timeout: 5000 });
    await expect(page.locator('#cnt-general')).toHaveText('1', { timeout: 5000 });
    await expect(page.locator('#cnt-consultant')).toHaveText('1', { timeout: 5000 });
  });

  test('크레딧 칩 — 잔액 500cr 표시', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#member-tbody tr').first().waitFor({ state: 'visible', timeout: 5000 });

    // 회원 목록 탭 내에서만 확인 (역할 탭에도 같은 chip 있으므로 스코프 지정)
    const chips = page.locator('#member-tbody .credit-chip');
    await expect(chips).toHaveCount(1, { timeout: 5000 });
    await expect(chips.first()).toContainText('500 cr');
  });

  test('로그인 상태 — 관리자 1일 전 → login-active(녹색)', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#member-tbody tr').first().waitFor({ state: 'visible', timeout: 5000 });

    const adminRow = page.locator('#member-tbody tr').nth(0);
    await expect(adminRow.locator('.login-active')).toBeAttached({ timeout: 5000 });
  });

  test('탭 전환 — 역할·크레딧 탭', async ({ page }) => {
    await setupMock(page);
    await page.goto('/admin/users/index.html');
    await page.locator('#app').waitFor({ state: 'visible', timeout: 5000 });

    await page.locator('.tab-btn[data-tab="roles"]').click();
    await expect(page.locator('#tab-roles')).toBeVisible();
    await expect(page.locator('#tab-members')).not.toBeVisible();
  });

  test('denied 화면 — 미인증 접근 차단', async ({ page }) => {
    await setupDeniedMock(page);
    await page.goto('/admin/users/index.html');
    await page.waitForTimeout(1500);

    await expect(page.locator('#denied')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#app')).not.toBeVisible();
  });

});

/* ─────────────────────────────────────────────
   타코매니저 지도 테스트
───────────────────────────────────────────── */
test.describe('타코매니저 지도 (consulting/tacomanager)', () => {

  test('지도 컨테이너 높이 585px', async ({ page }) => {
    await page.goto('/consulting/tacomanager/index.html');
    const box = await page.locator('.map-container').boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(580);
    expect(box?.height).toBeLessThanOrEqual(590);
  });

  test('#leaflet-map 요소 존재', async ({ page }) => {
    await page.goto('/consulting/tacomanager/index.html');
    await expect(page.locator('#leaflet-map')).toBeAttached();
  });

  test('Leaflet 마커 pane 초기화', async ({ page }) => {
    await page.goto('/consulting/tacomanager/index.html');
    await page.locator('#screens').waitFor({ timeout: 5000 });
    await page.waitForTimeout(1500);
    await expect(page.locator('.leaflet-marker-pane')).toBeAttached({ timeout: 5000 });
  });

});
