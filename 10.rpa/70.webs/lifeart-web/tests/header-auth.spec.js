// @ts-check
const { test, expect } = require('@playwright/test');
const MEMBER = { email: 'lifeart.tester@worksfree.kr', password: 'LifeArt!test2026' };
const ADMIN  = { email: 'lifeart.admin.tester@worksfree.kr', password: 'LifeArt!admin2026' };

async function login(page, acct) {
  await page.goto('/auth/login/');
  await page.fill('input[name="email"]', acct.email);
  await page.fill('input[name="password"]', acct.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**', { timeout: 20000 });
}

test('비로그인 헤더: 회원가입 + 로그인 노출, 로그아웃 없음', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#nav-signup-btn')).toBeVisible();
  await expect(page.locator('#nav-login-btn')).toHaveText('로그인');
  await expect(page.locator('#nav-logout-btn')).toHaveCount(0);
});

test('회원 로그인 헤더: 마이페이지 + 로그아웃, 회원가입 숨김, 관리자 없음', async ({ page }) => {
  await login(page, MEMBER);
  await page.goto('/');
  await expect(page.locator('#nav-login-btn')).toHaveText('마이페이지');
  await expect(page.locator('#nav-logout-btn')).toBeVisible();
  await expect(page.locator('#nav-signup-btn')).toBeHidden();
  await expect(page.locator('#nav-admin-btn')).toHaveCount(0);
});

test('로그아웃 동작: 클릭 → 홈 이동 + 비로그인 헤더 복귀', async ({ page }) => {
  await login(page, MEMBER);
  await page.goto('/');
  await page.locator('#nav-logout-btn').click();
  await page.waitForURL(/lifeart\.ai\.kr\/?$|\/$/, { timeout: 15000 });
  await expect(page.locator('#nav-signup-btn')).toBeVisible();
  await expect(page.locator('#nav-login-btn')).toHaveText('로그인');
});

test('관리자 로그인 헤더: ⚙관리자 + 마이페이지 + 로그아웃', async ({ page }) => {
  await login(page, ADMIN);
  await page.goto('/');
  await expect(page.locator('#nav-admin-btn')).toBeVisible();
  await expect(page.locator('#nav-login-btn')).toHaveText('마이페이지');
  await expect(page.locator('#nav-logout-btn')).toBeVisible();
});
