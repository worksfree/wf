/**
 * 스모크 테스트 — 페이지 기본 구조 및 로드 검증
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
    await mockExternalAPIs(page);
    await page.goto('/');
    const toolbar = page.locator('#dev-toolbar');
    await expect(toolbar).not.toHaveClass(/show/);
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
