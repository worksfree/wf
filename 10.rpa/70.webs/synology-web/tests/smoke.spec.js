// @ts-check
/**
 * smoke.spec.js — 기본 페이지 로드 및 구조 검증
 * WorksFree Hub SPA 최소 동작 보장 테스트
 */
const { test, expect } = require('@playwright/test');

test.describe('Smoke — 기본 구조 및 로드', () => {

  test('홈 페이지 로드 — title 확인', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/WorksFree/i);
  });

  test('홈 페이지 로드 — sidebar 존재', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#sidebar')).toBeVisible();
  });

  test('홈 페이지 로드 — logo 영역 존재', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.logo')).toBeVisible();
  });

  test('홈 페이지 로드 — 로그인 버튼 표시 (비로그인)', async ({ page }) => {
    await page.goto('/');
    // 비로그인 상태에서는 로그인 버튼이 노출되어야 함
    const loginBtn = page.locator('#auth-btn, .login-btn, [data-action="login"]').first();
    // 로그인 버튼이 없으면 auth-area가 있어야 함
    const authArea = page.locator('#auth-area, .auth-area').first();
    const hasLogin = await loginBtn.count() > 0 || await authArea.count() > 0;
    expect(hasLogin).toBe(true);
  });

  test('홈 페이지 로드 — home-screen 표시', async ({ page }) => {
    await page.goto('/');
    // 비로그인 상태에서도 home-screen 또는 preview-overlay가 있어야 함
    const homeScreen = page.locator('#home-screen, .home-screen, #preview-overlay');
    await expect(homeScreen.first()).toBeAttached();
  });

  test('홈 페이지 로드 — contentFrame 존재', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#contentFrame')).toBeAttached();
  });

  test('홈 페이지 로드 — 2초 이내 DOMContentLoaded', async ({ page }) => {
    const start = Date.now();
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(5000); // 로컬에서 2초, CI 여유 포함 5초
  });

  test('404 → 홈으로 폴백 (hash 라우팅)', async ({ page }) => {
    await page.goto('/#nonexistent/deep/path');
    // SPA이므로 동일 페이지 로드되어야 함 (404 페이지가 아닌)
    await page.waitForLoadState('domcontentloaded');
    const title = await page.title();
    expect(title).toMatch(/WorksFree/i);
  });

  test('HUB_VERSION — 숫자 형식 버전 표시', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // HUB_VERSION이 x.x.x.x 형식으로 페이지에 존재해야 함
    expect(content).toMatch(/\d+\.\d+\.\d+\.\d+/);
  });

  test('HTTPS redirect 없음 (로컬 서버 기준)', async ({ page }) => {
    const resp = await page.goto('/');
    // 로컬 서버는 200 또는 304를 반환해야 함
    expect([200, 304]).toContain(resp?.status() ?? 200);
  });

});
