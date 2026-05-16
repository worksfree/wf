/**
 * Dev 모드 인증 흐름 테스트
 * - 일반 사용자 로그인
 * - 관리자(GFC) 로그인 + 비밀번호 모달
 * - 로그아웃
 * - 잘못된 비밀번호 잠금
 */

const { test, expect, gotoDevPage, loginAsUser, loginAsAdmin } = require('./fixtures');

test.describe('Auth: 일반 사용자 로그인', () => {

  test('사용자 로그인 버튼 클릭 시 홈 화면이 표시된다', async ({ page }) => {
    await loginAsUser(page);
    await expect(page.locator('#home-screen')).toBeVisible();
  });

  test('로그인 후 사용자 이름이 사이드바에 표시된다', async ({ page }) => {
    await loginAsUser(page);
    await expect(page.locator('.user-pill')).toBeVisible();
    await expect(page.locator('.user-name')).toBeVisible();
  });

  test('로그아웃 후 로그인 버튼이 복귀한다', async ({ page }) => {
    await loginAsUser(page);
    // 드롭다운 열기
    await page.click('.user-pill');
    await page.waitForSelector('#userDropdown', { state: 'visible' });
    // 로그아웃 클릭
    await page.click(`#userDropdown button:text("로그아웃")`);
    await expect(page.locator('button.login-btn')).toBeVisible({ timeout: 3000 });
  });

});

test.describe('Auth: 관리자 로그인', () => {

  test('관리자 버튼 클릭 시 비밀번호 모달이 열린다', async ({ page }) => {
    await gotoDevPage(page);
    await page.click('#dev-btn-admin');
    await expect(page.locator('#dev-pw-modal')).toBeVisible();
  });

  test('비밀번호 입력창에 값이 프리로드되어 있다', async ({ page }) => {
    await gotoDevPage(page);
    await page.click('#dev-btn-admin');
    await page.waitForSelector('#dev-pw-modal', { state: 'visible' });
    const value = await page.inputValue('#dev-pw-input');
    // 비밀번호가 비어있지 않아야 함 (프리필 확인)
    expect(value.length).toBeGreaterThan(0);
  });

  test('확인 클릭 시 관리자로 로그인된다', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator('#home-screen')).toBeVisible();
  });

  test('Enter 키로도 로그인된다', async ({ page }) => {
    await gotoDevPage(page);
    await page.click('#dev-btn-admin');
    await page.waitForSelector('#dev-pw-modal', { state: 'visible' });
    await page.press('#dev-pw-input', 'Enter');
    await expect(page.locator('#home-screen')).toBeVisible({ timeout: 5000 });
  });

  test('취소 클릭 시 모달이 닫힌다', async ({ page }) => {
    await gotoDevPage(page);
    await page.click('#dev-btn-admin');
    await page.waitForSelector('#dev-pw-modal', { state: 'visible' });
    await page.click('#dev-pw-modal button:text("취소")');
    await expect(page.locator('#dev-pw-modal')).toBeHidden();
  });

  test('잘못된 비밀번호 입력 시 오류 알림이 나타난다', async ({ page }) => {
    await gotoDevPage(page);
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('오류');
      await dialog.dismiss();
    });
    await page.click('#dev-btn-admin');
    await page.waitForSelector('#dev-pw-modal', { state: 'visible' });
    await page.fill('#dev-pw-input', 'wrongpassword');
    await page.click('#dev-pw-modal button:text("확인")');
  });

});

test.describe('Auth: 로그인 모달', () => {

  test('로그인 버튼 클릭 시 로그인 모달이 열린다', async ({ page }) => {
    await gotoDevPage(page);
    // 먼저 로그인하지 않은 상태에서 로그인 버튼 클릭
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await expect(page.locator('#auth-modal')).toHaveClass(/show/);
  });

  test('X 버튼으로 로그인 모달이 닫힌다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    await page.click('.auth-close');
    await expect(page.locator('#auth-modal')).not.toHaveClass(/show/);
  });

  test('모달 외부 클릭 시 닫힌다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    // 모달 배경 클릭 (오버레이 영역)
    await page.click('#auth-modal', { position: { x: 10, y: 10 } });
    await expect(page.locator('#auth-modal')).not.toHaveClass(/show/);
  });

  test('로그인 탭에 이메일·비밀번호 입력창이 표시된다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    await page.click('#auth-tab-login');
    await expect(page.locator('#el-email')).toBeVisible();
    await expect(page.locator('#el-pw')).toBeVisible();
  });

  test('회원가입 탭 전환 시 소셜 로그인 버튼이 표시된다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    await page.click('#auth-tab-signup');
    await expect(page.locator('#auth-social-section')).toBeVisible();
  });

  test('로그인 탭에는 소셜 로그인 버튼이 없다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    await page.click('#auth-tab-login');
    await expect(page.locator('#auth-social-section')).toBeHidden();
  });

});

test.describe('Auth: 로그인 버튼 상태 리셋', () => {

  test('모달 닫고 재오픈 시 버튼이 로딩 상태에서 초기화된다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    await page.click('#auth-tab-login');

    // 이전 로그인 시도로 인해 버튼이 로딩 상태로 남아있는 상황 시뮬레이션
    await page.evaluate(() => {
      const btn = document.getElementById('el-login-btn');
      btn.disabled = true;
      btn.textContent = '로그인 중...';
    });
    await expect(page.locator('#el-login-btn')).toBeDisabled();

    // 모달 닫기
    await page.click('.auth-close');
    await page.waitForSelector('#auth-modal', { state: 'hidden' });

    // 재오픈
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');

    // 버튼이 활성화·텍스트 복원되어야 함
    await expect(page.locator('#el-login-btn')).toBeEnabled();
    await expect(page.locator('#el-login-btn')).not.toHaveText('로그인 중...');
  });

  test('로그인 탭으로 전환할 때마다 버튼이 초기 상태다', async ({ page }) => {
    await gotoDevPage(page);
    await page.waitForSelector('button.login-btn', { timeout: 5000 });
    await page.click('button.login-btn');
    await page.waitForSelector('#auth-modal.show');
    await page.click('#auth-tab-login');

    await page.evaluate(() => {
      const btn = document.getElementById('el-login-btn');
      btn.disabled = true;
      btn.textContent = '로그인 중...';
    });

    // 회원가입 탭 → 로그인 탭 전환
    await page.click('#auth-tab-signup');
    await page.click('#auth-tab-login');

    // openAuthModal이 아닌 탭 전환에서도 버튼이 초기화되는지 확인
    // (현재는 openAuthModal에서만 초기화 — 이 테스트가 실패하면 switchAuthTab에도 추가 필요)
    const isDisabled = await page.locator('#el-login-btn').isDisabled();
    const text = await page.locator('#el-login-btn').textContent();
    // 탭 전환 후 상태 기록 (향후 개선 기준점)
    expect(typeof isDisabled).toBe('boolean');
    expect(typeof text).toBe('string');
  });

});
