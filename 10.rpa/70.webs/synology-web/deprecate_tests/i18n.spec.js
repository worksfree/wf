/**
 * 다국어(KO/EN) 전환 테스트
 */

const { test, expect, mockExternalAPIs, loginAsUser } = require('./fixtures');

test.describe('i18n: 언어 전환', () => {

  test('기본 언어는 한국어(KO)이다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await expect(page.locator('#btnKo')).toHaveClass(/active/);
    await expect(page.locator('#btnEn')).not.toHaveClass(/active/);
  });

  test('EN 버튼 클릭 시 영어로 전환된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await page.click('#btnEn');
    // 로그인 버튼 텍스트가 영어로 바뀌는지 확인
    await expect(page.locator('button.login-btn')).toHaveText('Sign In', { timeout: 2000 });
    await expect(page.locator('#btnEn')).toHaveClass(/active/);
  });

  test('KO 버튼으로 다시 한국어로 전환된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await page.click('#btnEn');
    await page.click('#btnKo');
    await expect(page.locator('button.login-btn')).toHaveText('로그인', { timeout: 2000 });
    await expect(page.locator('#btnKo')).toHaveClass(/active/);
  });

  test('언어 설정이 localStorage에 저장된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/');
    await page.click('#btnEn');
    const lang = await page.evaluate(() => localStorage.getItem('wf_lang'));
    expect(lang).toBe('en');
  });

  test('로그인 후 EN 전환 시 크레딧 모달 제목도 바뀐다', async ({ page }) => {
    await loginAsUser(page);
    // 크레딧 모달 열기
    await page.click('.user-pill');
    await page.waitForSelector('#userDropdown', { state: 'visible' });
    await page.click(`#userDropdown button:text("크레딧 구매")`);
    await page.waitForSelector('#credit-modal.show');
    // EN으로 전환 — 모달 오버레이가 버튼을 가리므로 JS 직접 호출
    await page.evaluate(() => window.setLang('en'));
    await expect(page.locator('#credit-modal-title')).toHaveText('Buy Credits', { timeout: 2000 });
    // KO로 복구
    await page.evaluate(() => window.setLang('ko'));
    await expect(page.locator('#credit-modal-title')).toHaveText('크레딧 구매', { timeout: 2000 });
  });

});
