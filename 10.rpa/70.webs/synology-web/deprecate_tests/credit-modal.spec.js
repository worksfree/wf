/**
 * 크레딧 구매 모달 테스트
 * - 모달 열기/닫기
 * - 패키지 선택 및 버튼 상태
 * - 비로그인 시 로그인 모달로 유도
 * - 결제 URL 파라미터 처리 (토스/Stripe 리다이렉트 시뮬레이션)
 */

const { test, expect, gotoDevPage, loginAsUser, mockExternalAPIs } = require('./fixtures');

// 공통: 로그인 후 크레딧 모달 열기
async function openCreditModal(page) {
  await loginAsUser(page);
  await page.click('.user-pill');
  await page.waitForSelector('#userDropdown', { state: 'visible' });
  await page.click(`#userDropdown button:text("크레딧 구매")`);
  await page.waitForSelector('#credit-modal.show');
}

test.describe('Credit Modal: 열기/닫기', () => {

  test('로그인 상태에서 드롭다운에 크레딧 구매 버튼이 보인다', async ({ page }) => {
    await loginAsUser(page);
    await page.click('.user-pill');
    await page.waitForSelector('#userDropdown', { state: 'visible' });
    await expect(page.locator(`#userDropdown button:text("크레딧 구매")`)).toBeVisible();
  });

  test('크레딧 구매 클릭 시 모달이 열린다', async ({ page }) => {
    await openCreditModal(page);
    await expect(page.locator('#credit-modal')).toHaveClass(/show/);
    await expect(page.locator('#credit-modal-title')).toBeVisible();
  });

  test('X 버튼으로 모달이 닫힌다', async ({ page }) => {
    await openCreditModal(page);
    await page.click('.credit-close');
    await expect(page.locator('#credit-modal')).not.toHaveClass(/show/);
  });

  test('모달 바깥 클릭 시 닫힌다', async ({ page }) => {
    await openCreditModal(page);
    await page.click('#credit-modal', { position: { x: 10, y: 10 } });
    await expect(page.locator('#credit-modal')).not.toHaveClass(/show/);
  });

  test('비로그인 상태에서 크레딧 구매 시도 시 로그인 모달로 이동한다', async ({ page }) => {
    await gotoDevPage(page);
    // 로그인하지 않고 JS에서 직접 openCreditModal() 호출
    await page.evaluate(() => window.openCreditModal());
    await expect(page.locator('#auth-modal')).toHaveClass(/show/, { timeout: 2000 });
  });

});

test.describe('Credit Modal: 패키지 선택', () => {

  test('패키지 카드가 3개 렌더된다', async ({ page }) => {
    await openCreditModal(page);
    const cards = page.locator('.credit-pkg');
    await expect(cards).toHaveCount(3);
  });

  test('초기에는 결제 버튼이 비활성화된다', async ({ page }) => {
    await openCreditModal(page);
    await expect(page.locator('#credit-btn-toss')).toBeDisabled();
    await expect(page.locator('#credit-btn-stripe')).toBeDisabled();
  });

  test('패키지 선택 시 결제 버튼이 활성화된다', async ({ page }) => {
    await openCreditModal(page);
    // 두 번째 패키지(스탠다드) 클릭
    await page.click('#credit-pkg-1');
    await expect(page.locator('#credit-btn-toss')).toBeEnabled();
    await expect(page.locator('#credit-btn-stripe')).toBeEnabled();
  });

  test('선택된 패키지에 selected 클래스가 붙는다', async ({ page }) => {
    await openCreditModal(page);
    await page.click('#credit-pkg-0');
    await expect(page.locator('#credit-pkg-0')).toHaveClass(/selected/);
    await expect(page.locator('#credit-pkg-1')).not.toHaveClass(/selected/);
    await expect(page.locator('#credit-pkg-2')).not.toHaveClass(/selected/);
  });

  test('다른 패키지 선택 시 이전 선택이 해제된다', async ({ page }) => {
    await openCreditModal(page);
    await page.click('#credit-pkg-0');
    await page.click('#credit-pkg-2');
    await expect(page.locator('#credit-pkg-0')).not.toHaveClass(/selected/);
    await expect(page.locator('#credit-pkg-2')).toHaveClass(/selected/);
  });

  test('패키지 카드에 가격 정보가 표시된다', async ({ page }) => {
    await openCreditModal(page);
    // 첫 번째 패키지 (베이직: 50크레딧, ₩5,500)
    const card0 = page.locator('#credit-pkg-0');
    await expect(card0.locator('.credit-pkg-amount')).toHaveText('50');
    await expect(card0.locator('.credit-pkg-kr')).toContainText('5,500');
  });

  test('인기 패키지에 배지가 표시된다', async ({ page }) => {
    await openCreditModal(page);
    // 두 번째 패키지가 popular: true
    await expect(page.locator('#credit-pkg-1 .credit-pkg-badge')).toBeVisible();
  });

});

test.describe('Credit Modal: 결제 리다이렉트 처리', () => {

  test('?payment=toss_ok 파라미터 — 성공 토스트 표시', async ({ page }) => {
    // Toss 검증 Worker가 성공 응답 반환 (fixtures에서 모킹됨)
    await loginAsUser(page);
    // 결제 성공 URL 파라미터 시뮬레이션
    await page.goto('/?dev=1&payment=toss_ok&orderId=wf_test_order&credits=150&amount=14000');
    await page.waitForSelector('#dev-toolbar.show');
    await page.click('#dev-btn-user');
    // 토스트 메시지 확인 (성공 메시지)
    await expect(page.locator('#wf-toast')).toHaveClass(/show/, { timeout: 5000 });
    await expect(page.locator('#wf-toast')).toContainText('크레딧');
  });

  test('?payment=toss_fail 파라미터 — 취소 토스트 표시', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/?dev=1&payment=toss_fail');
    await page.waitForSelector('#dev-toolbar.show');
    await page.click('#dev-btn-user');
    await expect(page.locator('#wf-toast')).toHaveClass(/show/, { timeout: 5000 });
  });

  test('?payment=stripe_cancel 파라미터 — 취소 토스트 표시', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/?dev=1&payment=stripe_cancel');
    await page.waitForSelector('#dev-toolbar.show');
    await page.click('#dev-btn-user');
    await expect(page.locator('#wf-toast')).toHaveClass(/show/, { timeout: 5000 });
  });

  test('결제 파라미터 처리 후 URL에서 파라미터가 제거된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await page.goto('/?dev=1&payment=toss_fail');
    await page.waitForSelector('#dev-toolbar.show');
    await page.click('#dev-btn-user');
    // URL 파라미터가 history.replaceState로 제거되는지 확인
    await page.waitForTimeout(500);
    const url = page.url();
    expect(url).not.toContain('payment=');
  });

});
