// @ts-check
/**
 * payment.spec.js — LifeArt 실제 토스 테스트 가결제 E2E (테스트 겸 자동 주행 시연)
 *
 * 흐름: ?dev=123 → dev 툴킷으로 테스트 회원 로그인 → 액자 주문 →
 *       토스 테스트 결제창 자동 진행(테스트카드) → 결제 성공 → 주문 paid 확인
 *
 * 실행:
 *   테스트:  npx playwright test
 *   시연:    DEMO=1 npx playwright test --headed        (느리게, 눈에 보이게)
 *   대상변경: PW_BASE=https://test-lifeart.lifeart.ai.kr ...
 */
const { test, expect } = require('@playwright/test');

const MEMBER = { email: 'lifeart.tester@worksfree.kr', password: 'LifeArt!test2026' };

test('실제 토스 테스트 가결제 — 로그인→주문→결제→완료 자동 주행', async ({ page, context }) => {
  page.on('console', m => { if (m.type() === 'error') console.log('  [console.error]', m.text()); });
  page.on('pageerror', e => console.log('  [pageerror]', e.message));

  // 1) dev 툴킷 활성화
  await page.goto('/?dev=123');
  await expect(page.locator('#lifeart-dev-toolkit')).toBeVisible();

  // 2) dev 툴킷 "테스트 회원" 클릭 → 로그인 페이지 프리필
  await page.locator('.ldt-acct', { hasText: '테스트 회원' }).click();
  await page.waitForURL('**/auth/login/**');
  // 프리필 안정화 대기 후 값 보정(프리필 타이밍 방어)
  await page.waitForTimeout(400);
  await page.fill('input[name="email"]', MEMBER.email);
  await page.fill('input[name="password"]', MEMBER.password);

  // 3) 로그인 → 마이페이지
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**', { timeout: 20000 });

  // 4) 액자 주문 페이지
  await page.goto('/products/frame/order/');
  await expect(page.locator('#order-body')).toBeVisible();
  await expect(page.locator('#product-select option')).not.toHaveCount(0);

  // 배송지 입력 + 주문
  await page.fill('textarea[name="shipping_address"]', '서울시 강남구 테스트로 1 (E2E 자동주행)');
  const amountText = await page.locator('#order-amount').textContent();
  console.log('주문 금액:', amountText);
  await page.click('#order-form button[type="submit"]');

  // 5) 체크아웃 페이지
  await page.waitForURL('**/checkout/**', { timeout: 20000 });
  await expect(page.locator('#pay-btn')).toBeVisible({ timeout: 15000 });

  // 결제 버튼 클릭 — 토스는 같은 창 이동 또는 팝업 중 하나. 둘 다 대비.
  const popupPromise = context.waitForEvent('page', { timeout: 8000 }).catch(() => null);
  await page.click('#pay-btn');
  const popup = await popupPromise;
  const tossPage = popup || page;
  console.log('토스 결제 대상:', popup ? 'popup' : 'same-window', '→', tossPage.url());

  // 6) 토스 결제창(교차 출처) 테스트 결제 자동 진행
  await tossPage.waitForURL(/tosspayments\.com|checkout\/(success|fail)/, { timeout: 30000 });
  if (/tosspayments\.com/.test(tossPage.url())) {
    await driveTossTestPayment(tossPage);
  }

  // 7) 결제 성공 페이지 → Worker 승인 검증까지 (팝업이면 원 페이지가 redirect될 수 있음)
  const successTarget = popup ? page : page;
  await successTarget.waitForURL('**/checkout/success/**', { timeout: 40000 });
  await expect(successTarget.getByText('결제가 완료되었습니다')).toBeVisible({ timeout: 30000 });
  console.log('✅ 가결제 완료 확인');
});

/**
 * 토스 테스트 결제창 자동 진행.
 * 토스 UI 셀렉터는 토스가 관리하므로 텍스트 기반으로 방어적으로 클릭.
 */
async function driveTossTestPayment(page) {
  // 토스 페이지 로드 대기
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1500);

  // 결제수단(카드)·결제하기·확인 계열 버튼을 순차적으로 시도
  const clickByText = async (patterns) => {
    for (const p of patterns) {
      const btn = page.getByRole('button', { name: p }).first();
      if (await btn.count() && await btn.isVisible().catch(() => false)) {
        await btn.click().catch(() => {});
        await page.waitForTimeout(1200);
        return true;
      }
      const any = page.getByText(p, { exact: false }).first();
      if (await any.count() && await any.isVisible().catch(() => false)) {
        await any.click().catch(() => {});
        await page.waitForTimeout(1200);
        return true;
      }
    }
    return false;
  };

  // 최대 6단계까지 진행 버튼을 눌러 결제 완료로 유도
  for (let i = 0; i < 6; i++) {
    if (/checkout\/success/.test(page.url())) break;
    await clickByText([/결제하기/, /다음/, /확인/, /completePayment/i, /카드/, /테스트/]);
  }
}
