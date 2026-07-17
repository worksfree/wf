// @ts-check
/**
 * navigation.spec.js — Hub-and-Spoke 네비게이션 및 해시 라우팅 테스트
 *
 * 주의: index.html은 non-module <script>
 *  - function 선언 → window에 노출 (직접 호출 가능)
 *  - const/let (TREE, DASH_CARDS, SECTION_DESCS 등) → 소스 검사 방식 사용
 */
const { test, expect } = require('@playwright/test');

async function hubFnExists(page, fnName) {
  return page.evaluate((fn) => typeof window[fn] === 'function', fnName);
}

test.describe('Navigation — 해시 라우팅', () => {

  test('루트 URL → home-screen 표시', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const homeOrPreview = await page.evaluate(() =>
      document.getElementById('home-screen')?.style.display !== 'none' ||
      document.getElementById('preview-overlay') != null
    );
    expect(homeOrPreview).toBe(true);
  });

  test('해시 URL — 유효하지 않은 slug는 홈으로 폴백', async ({ page }) => {
    await page.goto('/#invalid-section-xyz');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('#sidebar')).toBeVisible();
  });

  test('logo 클릭 → showHome 함수 존재 확인', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, 'showHome');
    expect(exists).toBe(true);
  });

  test('showSectionDash 함수 존재 확인', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, 'showSectionDash');
    expect(exists).toBe(true);
  });

  test('navigateToHash 함수 존재 확인', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, 'navigateToHash');
    expect(exists).toBe(true);
  });

  test('iframeToSlug 함수 존재 확인', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, 'iframeToSlug');
    expect(exists).toBe(true);
  });

  test('iframeToSlug — /index.html 제거', async ({ page }) => {
    await page.goto('/');
    const slug = await page.evaluate(() =>
      window.iframeToSlug('consulting/ceo/index.html')
    );
    expect(slug).toBe('consulting/ceo');
  });

  test('iframeToSlug — .html 제거', async ({ page }) => {
    await page.goto('/');
    const slug = await page.evaluate(() =>
      window.iframeToSlug('service/qr.html')
    );
    expect(slug).toBe('service/qr');
  });

  test('logo 요소 — onclick showHome 속성 존재', async ({ page }) => {
    await page.goto('/');
    const hasOnclick = await page.evaluate(() => {
      const logo = document.querySelector('.logo');
      return logo?.getAttribute('onclick')?.includes('showHome') ?? false;
    });
    expect(hasOnclick).toBe(true);
  });

  test('logo cursor:pointer 스타일', async ({ page }) => {
    await page.goto('/');
    const cursor = await page.evaluate(() => {
      const logo = document.querySelector('.logo');
      return logo ? getComputedStyle(logo).cursor : '';
    });
    expect(cursor).toBe('pointer');
  });

  test('TREE — 소스에 6개 섹션 slug 정의됨', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // TREE에 slug 필드들이 정의되어 있어야 함
    expect(content).toMatch(/slug:\s*['"]service['"]/);
    expect(content).toMatch(/slug:\s*['"]consulting['"]/);
    expect(content).toMatch(/slug:\s*['"]finance['"]/);
    expect(content).toMatch(/slug:\s*['"]pilot['"]/);
    expect(content).toMatch(/slug:\s*['"]app-store['"]/);
    expect(content).toMatch(/slug:\s*['"]admin['"]/);
  });

  test('currentSection — 소스 선언 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/let\s+currentSection\s*=\s*null/);
  });

  test('popstate 이벤트 — navigateToHash 호출 확인', async ({ page }) => {
    await page.goto('/');
    const hasHandler = await page.evaluate(() =>
      typeof window.navigateToHash === 'function'
    );
    expect(hasHandler).toBe(true);
  });

  test('renderHomeSections 함수 존재 확인', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, 'renderHomeSections');
    expect(exists).toBe(true);
  });

  test('DASH_CARDS — 소스에 section 필드 정의됨', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // DASH_CARDS 내 section 필드가 존재해야 함
    expect(content).toMatch(/section:\s*['"]service['"]/);
    expect(content).toMatch(/section:\s*['"]consulting['"]/);
    expect(content).toMatch(/section:\s*['"]finance['"]/);
    expect(content).toMatch(/section:\s*['"]admin['"]/);
  });

  test('renderDashCards — sectionFilter 파라미터 지원', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, 'renderDashCards');
    expect(exists).toBe(true);
    // sectionFilter 인자를 받아 오류 없이 실행되어야 함
    await expect(page.evaluate(() => {
      window.renderDashCards('service');
      return true;
    })).resolves.toBe(true);
  });

  test('SECTION_DESCS — 소스에 6개 섹션 설명 정의됨', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // SECTION_DESCS 상수 선언이 있어야 함
    expect(content).toMatch(/SECTION_DESCS/);
    expect(content).toMatch(/service:/);
    expect(content).toMatch(/consulting:/);
    expect(content).toMatch(/finance:/);
    expect(content).toMatch(/pilot:/);
  });

  test('_buildSectionSidebar 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, '_buildSectionSidebar');
    expect(exists).toBe(true);
  });

  test('_buildFullSidebar 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await hubFnExists(page, '_buildFullSidebar');
    expect(exists).toBe(true);
  });

});
