/**
 * 스모크 테스트 — 페이지 기본 구조 및 로드 검증
 * 배포 환경 접근성 테스트는 DEPLOY_TARGET 환경변수로 URL을 지정:
 *   DEPLOY_TARGET=https://test.worksfree.co.kr npx playwright test tests/smoke.spec.js
 */

const { test, expect, mockExternalAPIs, gotoDevPage } = require('./fixtures');

test.describe('Smoke: 페이지 기본 로드', () => {

  test('타이틀이 WorksFree Hub 이다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await expect(page).toHaveTitle('WorksFree Hub');
  });

  test('사이드바가 렌더된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await expect(page.locator('#sidebar')).toBeVisible();
  });

  test('푸터에 버전 정보가 표시된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    const footer = page.locator('#footer-ver');
    await expect(footer).toBeVisible();
    await expect(footer).toContainText('WorksFree');
  });

  test('로그인 버튼이 비로그인 시 표시된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    // Supabase가 null 세션을 반환하므로 로그인 버튼이 보여야 함
    await expect(page.locator('button.login-btn')).toBeVisible({ timeout: 5000 });
  });

  test('dev=1 없으면 dev 툴바가 숨겨진다', async ({ page }) => {
    // 주의: localhost 개발 환경에서는 IS_DEV가 hostname 조건으로 항상 true가 될 수 있음
    // 프로덕션 배포(portal.worksfree.kr)에서만 완전히 검증 가능
    test.skip(true, 'localhost 환경에서는 IS_DEV=true 조건 충족 — 프로덕션 배포 후 검증 필요');
  });

  test('?dev=1 이면 dev 툴바가 표시된다', async ({ page }) => {
    await gotoDevPage(page);
    await expect(page.locator('#dev-toolbar')).toHaveClass(/show/);
  });

  test('JS 콘솔 에러가 없다', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await mockExternalAPIs(page);
    await page.goto('/');
    // 1초 대기 (비동기 초기화 완료 대기)
    await page.waitForTimeout(1000);
    expect(errors, `콘솔 에러: ${errors.join(', ')}`).toHaveLength(0);
  });

  test('KO/EN 언어 버튼이 표시된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await expect(page.locator('#btnKo')).toBeVisible();
    await expect(page.locator('#btnEn')).toBeVisible();
  });

});

/* ─────────────────────────────────────────────────────────────────
   Smoke: 배포 환경 접근성 (Cloudflare Tunnel 생존 여부)
   실행: DEPLOY_TARGET=https://test.worksfree.co.kr npx playwright test tests/smoke.spec.js --project=mock
   CI/CD나 배포 후 서버 점검 시 사용.
───────────────────────────────────────────────────────────────── */
const DEPLOY_TARGET = process.env.DEPLOY_TARGET;

test.describe('Smoke: 배포 환경 접근성', () => {
  test.skip(!DEPLOY_TARGET, 'DEPLOY_TARGET 환경변수 미설정 시 건너뜀');

  test('배포 서버에서 페이지가 200으로 응답한다', async ({ page }) => {
    const response = await page.goto(DEPLOY_TARGET, { timeout: 15000 });
    expect(response?.status(), `${DEPLOY_TARGET} 접속 실패 — Cloudflare Tunnel 또는 NAS nginx 확인 필요`).toBe(200);
  });

  test('배포 서버에서 WorksFree Hub 타이틀이 표시된다', async ({ page }) => {
    await page.goto(DEPLOY_TARGET, { timeout: 15000 });
    await expect(page).toHaveTitle('WorksFree Hub');
  });

  test('배포 서버에서 JS 콘솔 에러가 없다', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto(DEPLOY_TARGET, { timeout: 15000 });
    await page.waitForTimeout(2000);
    expect(errors, `콘솔 에러: ${errors.join(', ')}`).toHaveLength(0);
  });

  test('배포 서버에서 로그인 버튼이 표시된다', async ({ page }) => {
    await page.goto(DEPLOY_TARGET, { timeout: 15000 });
    await expect(page.locator('button.login-btn')).toBeVisible({ timeout: 8000 });
  });

  test('배포 서버에서 dev 로그인이 동작한다', async ({ page }) => {
    await page.goto(`${DEPLOY_TARGET}?dev=1`, { timeout: 15000 });
    await page.waitForSelector('#dev-toolbar.show', { timeout: 8000 });
    await page.click('#dev-btn-user');
    await expect(page.locator('.user-pill')).toBeVisible({ timeout: 8000 });
  });

  test('배포 서버에서 dev 관리자 로그인이 동작한다', async ({ page }) => {
    await page.goto(`${DEPLOY_TARGET}?dev=1`, { timeout: 15000 });
    await page.waitForSelector('#dev-toolbar.show', { timeout: 8000 });
    // 관리자 로그인 (비밀번호 모달 → 확인)
    await page.click('#dev-btn-admin');
    await page.waitForSelector('#dev-pw-modal', { state: 'visible', timeout: 3000 });
    await page.click('#dev-pw-modal button:text("확인")');
    await expect(page.locator('.user-pill')).toBeVisible({ timeout: 8000 });
  });

});
