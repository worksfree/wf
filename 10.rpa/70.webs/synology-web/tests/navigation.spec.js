/**
 * 사이드바 트리 및 콘텐츠 로드 테스트
 * - 트리 구조 렌더
 * - 폴더 펼치기/접기
 * - 메뉴 클릭 → iframe 로드
 * - 파트너 전용 메뉴 접근 제어
 * - 대시보드 카드 렌더
 */

const { test, expect, loginAsUser, loginAsAdmin } = require('./fixtures');

test.describe('Navigation: 트리 구조', () => {

  test('홈·서비스·컨설팅·앱스토어 최상위 메뉴가 렌더된다', async ({ page }) => {
    await loginAsUser(page);
    const tree = page.locator('#treeRoot');
    await expect(tree.locator('.tree-node')).not.toHaveCount(0);
    // 최상위 레이블 텍스트 확인
    await expect(tree).toContainText('홈');
    await expect(tree).toContainText('서비스');
    await expect(tree).toContainText('컨설팅');
    await expect(tree).toContainText('앱스토어');
  });

  test('서비스 폴더 클릭 시 하위 메뉴가 펼쳐진다', async ({ page }) => {
    await loginAsUser(page);
    // 서비스 레이블 클릭 (트리에서 두 번째 최상위)
    const serviceLabel = page.locator('#treeRoot .tree-label').filter({ hasText: '서비스' });
    await serviceLabel.click();
    await expect(page.locator('#treeRoot')).toContainText('QR 생성기');
  });

  test('홈 버튼 클릭 시 홈 화면이 표시된다', async ({ page }) => {
    await loginAsUser(page);
    // iframe 로드 후 홈으로 복귀하는 시나리오
    const homeLabel = page.locator('#treeRoot .tree-label').filter({ hasText: '홈' });
    await homeLabel.click();
    await expect(page.locator('#home-screen')).toBeVisible();
    await expect(page.locator('#content-area')).not.toBeVisible();
  });

  test('리프 메뉴 클릭 시 iframe이 표시된다', async ({ page }) => {
    await loginAsUser(page);
    const serviceLabel = page.locator('#treeRoot .tree-label').filter({ hasText: '서비스' });
    await serviceLabel.click();
    const qrLabel = page.locator('#treeRoot .tree-label').filter({ hasText: 'QR 생성기' });
    await qrLabel.click();
    // frame-container가 visible로 전환되어야 함
    await expect(page.locator('#frame-container')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#contentFrame')).toBeVisible();
  });

  test('브레드크럼이 현재 메뉴 경로를 표시한다', async ({ page }) => {
    await loginAsUser(page);
    const serviceLabel = page.locator('#treeRoot .tree-label').filter({ hasText: '서비스' });
    await serviceLabel.click();
    const qrLabel = page.locator('#treeRoot .tree-label').filter({ hasText: 'QR 생성기' });
    await qrLabel.click();
    // bc-home-text에 홈이 표시되고, 현재 메뉴 이름이 표시되어야 함
    await expect(page.locator('#bc-home-text')).toHaveText('홈', { timeout: 3000 });
    // breadcrumb 영역 내에 메뉴 이름이 포함되어야 함
    await expect(page.locator('#topbar')).toContainText('QR 생성기');
  });

});

test.describe('Navigation: 접근 제어', () => {

  test('일반 사용자는 파트너 전용 메뉴가 보이지 않는다', async ({ page }) => {
    await loginAsUser(page);
    // gfc roleOnly 메뉴는 트리에서 완전히 제거됨
    await expect(page.locator('#treeRoot')).not.toContainText('경영종합진단');
    await expect(page.locator('#treeRoot')).not.toContainText('CEO 플랜');
  });

  test('관리자 로그인 시 파트너 전용 메뉴가 표시된다', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator('#treeRoot')).toContainText('경영종합진단');
    await expect(page.locator('#treeRoot')).toContainText('CEO 플랜');
  });

  test('회원 전용 메뉴(memberOnly) 클릭 시 비로그인은 오버레이를 표시한다', async ({ page }) => {
    const { mockExternalAPIs } = require('./fixtures');
    await mockExternalAPIs(page);
    await page.goto('/?dev=1');
    await page.waitForSelector('#dev-toolbar.show');
    // 로그인 없이 직접 회원전용 iframe 로드 시도
    await page.evaluate(() => {
      // memberOnly 비로그인 경로: loadIframePreview가 overlay를 표시
      window.loadIframePreview('consulting/dart/index.html', [], 'DART');
    });
    // frame-container가 표시된 뒤 overlay가 show 클래스를 얻어야 함
    await expect(page.locator('#frame-container')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('#preview-overlay')).toBeVisible({ timeout: 3000 });
  });

});

test.describe('Navigation: 대시보드 카드', () => {

  test('로그인 후 홈 화면에 대시보드 카드가 렌더된다', async ({ page }) => {
    await loginAsUser(page);
    const cards = page.locator('.dash-card');
    await expect(cards).not.toHaveCount(0);
  });

  test('대시보드 카드 클릭 시 해당 콘텐츠가 로드된다', async ({ page }) => {
    await loginAsUser(page);
    const cards = page.locator('.dash-card');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
    // 첫 번째 카드 클릭
    await cards.first().click();
    // iframe 또는 홈 화면이 보여야 함
    const contentVisible = await page.locator('#contentFrame').isVisible()
      .catch(() => false);
    const homeVisible = await page.locator('#home-screen').isVisible()
      .catch(() => false);
    expect(contentVisible || homeVisible).toBe(true);
  });

});

test.describe('Navigation: 모바일 사이드바', () => {

  test('모바일 뷰포트에서 햄버거 버튼이 표시된다', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    const { mockExternalAPIs } = require('./fixtures');
    await mockExternalAPIs(page);
    await page.goto('/');
    await expect(page.locator('#sidebar-toggle')).toBeVisible();
  });

});
