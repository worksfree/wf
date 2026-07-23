// @ts-check
/**
 * smoke.spec.js — LifeArt 전 페이지·전 기능 스모크 테스트
 * 콘솔 치명 오류·깨진 렌더·RLS 오류를 잡는다.
 * O&M 테이블(공지/FAQ) 미생성 상태에서도 페이지가 graceful 하게 동작하는지 포함.
 */
const { test, expect } = require('@playwright/test');

const MEMBER = { email: 'lifeart.tester@worksfree.kr', password: 'LifeArt!test2026' };
const ADMIN  = { email: 'lifeart.admin.tester@worksfree.kr', password: 'LifeArt!admin2026' };

// 무해한(무시 가능한) 콘솔 오류 패턴 — O&M 테이블 미생성 404, 파비콘 등
const IGNORABLE = [
  /favicon/i, /tosspayments/i, /인증되지 않은/, /lifeart_notices/i, /lifeart_faqs/i,
  /404 \(\)/, /Failed to load resource.*40[034]/i,
];

function watchConsole(page, bag) {
  page.on('console', m => { if (m.type() === 'error') bag.push(m.text()); });
  page.on('pageerror', e => bag.push('PAGEERROR: ' + e.message));
}
function fatalErrors(bag) {
  return bag.filter(t => !IGNORABLE.some(re => re.test(t)));
}

const PAGES = [
  '/', '/about/story/', '/about/ceo/', '/about/location/', '/about/press/',
  '/products/', '/products/instant-album/', '/products/vip-album/', '/products/frame/',
  '/howto/', '/business/', '/support/', '/auth/login/', '/auth/signup/',
];

test.describe('전 페이지 로드 + 콘솔 치명오류 없음', () => {
  for (const path of PAGES) {
    test(`페이지 로드: ${path}`, async ({ page }) => {
      const errs = [];
      watchConsole(page, errs);
      const resp = await page.goto(path, { waitUntil: 'networkidle' });
      expect(resp?.status(), `${path} HTTP`).toBeLessThan(400);
      // 헤더/푸터 파트셜이 주입됐는지 (레이아웃 정상)
      await expect(page.locator('header .logo')).toBeVisible();
      await expect(page.locator('footer')).toBeVisible();
      const fatal = fatalErrors(errs);
      expect(fatal, `${path} 콘솔 치명오류: ${fatal.join(' | ')}`).toEqual([]);
    });
  }
});

test('헤더 네비게이션 링크가 모두 유효(4xx 없음)', async ({ page }) => {
  await page.goto('/');
  const hrefs = await page.$$eval('header a[href^="/"]', els => [...new Set(els.map(e => e.getAttribute('href')))]);
  for (const h of hrefs) {
    const r = await page.request.get(h);
    expect(r.status(), `${h}`).toBeLessThan(400);
  }
});

test('문의 폼 제출 — lifeart_inquiries INSERT (비회원)', async ({ page }) => {
  const errs = []; watchConsole(page, errs);
  await page.goto('/support/');
  await page.fill('#qna-form input[name="name"]', 'E2E 스모크');
  await page.fill('#qna-form input[name="phone"]', '010-1234-5678');
  await page.fill('#qna-form textarea[name="message"]', '스모크 테스트 문의입니다.');
  await page.click('#qna-form button[type="submit"]');
  await expect(page.locator('#qna-msg')).toContainText('접수', { timeout: 15000 });
});

test('회원 로그인 → 마이페이지 탭 동작', async ({ page }) => {
  const errs = []; watchConsole(page, errs);
  await page.goto('/auth/login/');
  await page.fill('input[name="email"]', MEMBER.email);
  await page.fill('input[name="password"]', MEMBER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**', { timeout: 20000 });
  // 탭 전환
  for (const tab of ['estimates', 'partnership', 'profile', 'orders']) {
    await page.locator(`.tab-btn[data-tab="${tab}"]`).click();
    await expect(page.locator(`#tab-${tab}`)).toBeVisible();
  }
  // 회원정보에 이메일 채워졌는지
  await page.locator('.tab-btn[data-tab="profile"]').click();
  await expect(page.locator('#profile-form input[name="email"]')).toHaveValue(MEMBER.email);
  expect(fatalErrors(errs), errs.join(' | ')).toEqual([]);
});

test('상품 조회 + 주문 페이지 상품 로드', async ({ page }) => {
  await page.goto('/auth/login/');
  await page.fill('input[name="email"]', MEMBER.email);
  await page.fill('input[name="password"]', MEMBER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**');
  await page.goto('/products/frame/order/');
  await expect(page.locator('#product-select option')).not.toHaveCount(0);
  const amount = await page.locator('#order-amount').textContent();
  expect(amount).toMatch(/원/);
});

test('액자 주문 페이지 — 옵션상품(추가구성상품) 선택 시 총액 반영', async ({ page }) => {
  await page.goto('/auth/login/');
  await page.fill('input[name="email"]', MEMBER.email);
  await page.fill('input[name="password"]', MEMBER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**');
  await page.goto('/products/frame/order/');
  await expect(page.locator('.pd-addon-row').first()).toBeVisible();
  const before = await page.locator('#order-amount').textContent();
  await page.locator('.pd-addon-row input[type="checkbox"]').first().check();
  const after = await page.locator('#order-amount').textContent();
  expect(after).not.toEqual(before);
});

test('관리자 로그인 → O&M 4탭 로드(테이블 미생성이어도 graceful)', async ({ page }) => {
  const errs = []; watchConsole(page, errs);
  await page.goto('/auth/login/');
  await page.fill('input[name="email"]', ADMIN.email);
  await page.fill('input[name="password"]', ADMIN.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**', { timeout: 20000 });
  await page.goto('/admin/');
  // 게이트 해제 확인
  await expect(page.locator('#admin-gate')).toBeHidden({ timeout: 15000 });
  for (const tab of ['orders', 'inquiries', 'notices', 'faqs']) {
    await page.locator(`.tab-btn[data-tab="${tab}"]`).click();
    await expect(page.locator(`#tab-${tab}`)).toBeVisible();
  }
  // 공지 테이블(미생성)이어도 '공지가 없습니다' 등으로 graceful
  await page.locator('.tab-btn[data-tab="notices"]').click();
  await expect(page.locator('#notice-table tbody')).toContainText(/공지|없습니다/);
  const fatal = fatalErrors(errs);
  expect(fatal, `admin 콘솔 치명오류: ${fatal.join(' | ')}`).toEqual([]);
});

test('비관리자(회원)는 admin 게이트 차단', async ({ page }) => {
  await page.goto('/auth/login/');
  await page.fill('input[name="email"]', MEMBER.email);
  await page.fill('input[name="password"]', MEMBER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/mypage/**');
  await page.goto('/admin/');
  // 회원은 게이트가 계속 보여야 함
  await expect(page.locator('#admin-gate')).toBeVisible();
});
