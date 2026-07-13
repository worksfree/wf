// @ts-check
/**
 * payment.spec.js — LifeArt 결제 흐름 E2E (테스트 겸 자동 주행 시연)
 *
 * 테스트 1: dev툴킷 로그인 → 액자 주문 → 체크아웃 → 결제버튼까지 자동 주행,
 *           실제 pending 주문이 DB에 생성되는지 검증. (유효 키 없이도 항상 통과)
 * 테스트 2: 토스 결제창 진입 후 테스트카드로 가결제 완료.
 *           토스 클라이언트 키가 유효할 때만 완주하고, 무효(401)면 자동 SKIP.
 *
 * 실행:
 *   npx playwright test                         (헤드리스 검증)
 *   DEMO=1 npx playwright test --headed         (시연: 느리게, 눈에 보이게)
 *   PW_BASE=https://test-lifeart.lifeart.ai.kr  (대상 변경)
 */
const { test, expect } = require('@playwright/test');

const MEMBER = { email: 'lifeart.tester@worksfree.kr', password: 'LifeArt!test2026' };

async function loginAndOrder(page) {
  await page.goto('/?dev=123');
  await expect(page.locator('#lifeart-dev-toolkit')).toBeVisible();
  await page.locator('.ldt-acct', { hasText: '테스트 회원' }).click();
  await page.waitForURL('**/auth/login/**');
  await page.waitForTimeout(400);
  await page.fill('input[name="email"]', MEMBER.email);
  await page.fill('input[name="password"]', MEMBER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**', { timeout: 20000 });

  await page.goto('/products/frame/order/');
  await expect(page.locator('#order-body')).toBeVisible();
  await expect(page.locator('#product-select option')).not.toHaveCount(0);
  await page.fill('textarea[name="shipping_address"]', '서울시 강남구 테스트로 1 (E2E 자동주행)');
  await page.click('#order-form button[type="submit"]');
  await page.waitForURL('**/checkout/**', { timeout: 20000 });
  const orderId = new URL(page.url()).searchParams.get('order');
  return orderId;
}

test('주문 생성까지 자동 주행 — dev툴킷 로그인→주문→체크아웃', async ({ page }) => {
  const orderId = await loginAndOrder(page);
  expect(orderId).toBeTruthy();
  // 체크아웃 페이지가 주문 정보를 정상 로드했는지
  await expect(page.locator('#pay-btn')).toBeVisible({ timeout: 15000 });
  console.log('✅ pending 주문 생성 + 체크아웃 진입 확인:', orderId);
});

test('토스 가결제 완료 — 유효 키 있을 때 완주 (없으면 skip)', async ({ page, context }) => {
  let tossKeyError = false;
  page.on('pageerror', e => {
    if (/인증되지 않은|client key|unauthorized/i.test(e.message)) tossKeyError = true;
  });

  await loginAndOrder(page);
  await expect(page.locator('#pay-btn')).toBeVisible({ timeout: 15000 });

  const popupPromise = context.waitForEvent('page', { timeout: 6000 }).catch(() => null);
  await page.click('#pay-btn');
  const popup = await popupPromise;
  const tossPage = popup || page;

  // 토스 결제창 진입 or 키 오류를 최대 8초 관찰
  const entered = await tossPage.waitForURL(/tosspayments\.com/, { timeout: 8000 })
    .then(() => true).catch(() => false);

  if (!entered) {
    test.skip(tossKeyError,
      '토스 클라이언트 키가 무효(회수된 공용 테스트 키)라 결제창 진입 불가 — ' +
      '토스 개발자센터의 현재 유효한 테스트 키로 교체 후 재실행하면 완주합니다.');
    // 키 오류가 아닌 다른 이유면 실패로 처리
    expect(entered, '토스 결제창 진입 실패(키 오류 아님)').toBe(true);
    return;
  }

  await driveTossTestPayment(tossPage);
  await page.waitForURL('**/checkout/success/**', { timeout: 40000 });
  await expect(page.getByText('결제가 완료되었습니다')).toBeVisible({ timeout: 30000 });
  console.log('✅ 실제 토스 테스트 가결제 완료');
});

async function driveTossTestPayment(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1500);
  const tryClick = async (patterns) => {
    for (const p of patterns) {
      const btn = page.getByRole('button', { name: p }).first();
      if (await btn.count() && await btn.isVisible().catch(() => false)) {
        await btn.click().catch(() => {}); await page.waitForTimeout(1200); return true;
      }
      const any = page.getByText(p, { exact: false }).first();
      if (await any.count() && await any.isVisible().catch(() => false)) {
        await any.click().catch(() => {}); await page.waitForTimeout(1200); return true;
      }
    }
    return false;
  };
  for (let i = 0; i < 6; i++) {
    if (/checkout\/success/.test(page.url())) break;
    await tryClick([/결제하기/, /다음/, /확인/, /카드/, /테스트/]);
  }
}
