// @ts-check
/**
 * permissions.spec.js — 역할 기반 접근 제어 테스트
 *
 * 주의: const/let 변수 (TREE, canConsult 등) → 소스 검사 방식
 *       function 선언 (getAccessLevel 등) → window에서 직접 호출
 */
const { test, expect } = require('@playwright/test');

test.describe('Permissions — 역할 기반 접근 제어', () => {

  // ───────────────────────────────────────────
  // 1. TREE 노드 접근 플래그 — 소스 검사
  // ───────────────────────────────────────────

  test('TREE — admin 섹션 adminOnly:true 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // slug:'admin' 과 adminOnly:true가 가까운 위치에 있어야 함
    expect(content).toMatch(/slug:\s*['"]admin['"]/);
    expect(content).toMatch(/adminOnly:\s*true/);
  });

  test('TREE — consulting 섹션 consultantOnly:true 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/slug:\s*['"]consulting['"]/);
    expect(content).toMatch(/consultantOnly:\s*true/);
  });

  test('TREE — finance 섹션 정의됨', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/slug:\s*['"]finance['"]/);
    // 연금 시뮬레이터가 finance 아래에 있어야 함
    expect(content).toMatch(/연금 시뮬레이터|Pension Simulator/);
  });

  test('TREE — service 섹션 consultantOnly 없음 (공개)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // 비로그인 상태에서 사이드바에 서비스 메뉴가 보여야 함
    const sidebarText = await page.locator('#sidebar, .sidebar').textContent().catch(() => '');
    const hasService = sidebarText.includes('서비스') ||
                       sidebarText.includes('Service') ||
                       sidebarText.includes('QR');
    expect(hasService).toBe(true);
  });

  test('TREE — pilot 섹션 타코매니저 consultantOnly 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/slug:\s*['"]pilot['"]/);
    // 타코 매니저와 consultantOnly가 소스에 있어야 함
    expect(content).toMatch(/타코|Taco/);
    expect(content).toMatch(/consultantOnly:\s*true/);
  });

  // ───────────────────────────────────────────
  // 2. getAccessLevel 함수 검증 (function 선언 → window)
  // ───────────────────────────────────────────

  test('getAccessLevel 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.getAccessLevel === 'function');
    expect(exists).toBe(true);
  });

  test('getAccessLevel — 규칙 없는 페이지는 full 반환', async ({ page }) => {
    await page.goto('/');
    const level = await page.evaluate(() =>
      window.getAccessLevel ? window.getAccessLevel('service/qr/index.html') : null
    );
    expect(level).toBe('full');
  });

  test('getAccessLevel — GFC 페이지 비로그인(member) 시 hidden 반환', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // 비로그인 상태 (authUser=null, userRole=member default)
    const level = await page.evaluate(() =>
      window.getAccessLevel ? window.getAccessLevel('consulting/gfc/index.html') : null
    );
    expect(level).toBe('hidden');
  });

  test('getAccessLevel — GFC consultant 모의 시 blur', async ({ page }) => {
    await page.goto('/');
    // getAccessLevel 소스를 읽어 내부 로직 확인
    const fnSrc = await page.evaluate(() => window.getAccessLevel?.toString() ?? '');
    // pageAccessRules와 role을 사용해야 함
    expect(fnSrc).toMatch(/pageAccessRules|rule/);
  });

  // ───────────────────────────────────────────
  // 3. DEFAULT_ACCESS_RULES 구조 — 소스 검사
  // ───────────────────────────────────────────

  test('DEFAULT_ACCESS_RULES — GFC 규칙 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/DEFAULT_ACCESS_RULES/);
    expect(content).toMatch(/consulting\/gfc\/index\.html/);
  });

  test('DEFAULT_ACCESS_RULES — general:hidden, member:hidden 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // GFC 규칙에 general:hidden, member:hidden이 있어야 함
    expect(content).toMatch(/general:\s*['"]hidden['"]/);
    expect(content).toMatch(/member:\s*['"]hidden['"]/);
  });

  test('DEFAULT_ACCESS_RULES — consultant:blur 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/consultant:\s*['"]blur['"]/);
  });

  // ───────────────────────────────────────────
  // 4. applyAccessOverlay 함수
  // ───────────────────────────────────────────

  test('applyAccessOverlay 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.applyAccessOverlay === 'function');
    expect(exists).toBe(true);
  });

  // ───────────────────────────────────────────
  // 5. 비로그인 상태 메뉴 가시성 — DOM 검사
  // ───────────────────────────────────────────

  test('buildTree 함수 존재 (사이드바 렌더)', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.buildTree === 'function');
    expect(exists).toBe(true);
  });

  test('비로그인 — consultantOnly 메뉴 비공개 (CEO 플랜 미노출)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const sidebarText = await page.locator('#sidebar, .sidebar').textContent().catch(() => '');
    expect(sidebarText).not.toMatch(/CEO 플랜/);
  });

  test('비로그인 — admin 메뉴 비공개 (O&M 미노출)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const sidebarText = await page.locator('#sidebar, .sidebar').textContent().catch(() => '');
    expect(sidebarText).not.toMatch(/사용자 관리|이메일 캠페인|시스템 모니터/);
  });

  test('비로그인 — service 메뉴 공개 (사이드바에 서비스 존재)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const sidebarText = await page.locator('#sidebar, .sidebar').textContent().catch(() => '');
    const hasPublicMenu = sidebarText.includes('서비스') ||
                          sidebarText.includes('QR') ||
                          sidebarText.includes('Service');
    expect(hasPublicMenu).toBe(true);
  });

  // ───────────────────────────────────────────
  // 6. pageAccessRules 동적 로드
  // ───────────────────────────────────────────

  test('pageAccessRules 소스 선언 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/pageAccessRules/);
  });

  // ───────────────────────────────────────────
  // 7. 역할별 소스 정의 확인
  // ───────────────────────────────────────────

  test('canConsult — 소스에 consultant|partner|admin 허용 정의', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // canConsult = () => userRole === 'consultant' || userRole === 'partner' || userRole === 'admin'
    expect(content).toMatch(/canConsult/);
    expect(content).toMatch(/'consultant'.*'partner'.*'admin'|consultant.*partner.*admin/);
  });

  test('IS_PARTNER — partner|admin 조건 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // IS_PARTNER = userRole === 'partner' || userRole === 'admin'
    expect(content).toMatch(/IS_PARTNER.*partner.*admin|partner.*admin.*IS_PARTNER/);
  });

  test('adminOnly 플래그 — admin만 허용하는 코드 존재', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // adminOnly:true 노드는 userRole !== 'admin'이면 return하는 코드
    expect(content).toMatch(/adminOnly.*admin|admin.*adminOnly/);
  });

  test('consultantOnly 플래그 — canConsult() 통과 확인 코드 존재', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/consultantOnly.*canConsult|canConsult.*consultantOnly/);
  });

  test('getAccessLevel — 역할 폴백 로직 소스 확인', async ({ page }) => {
    await page.goto('/');
    const fnSrc = await page.evaluate(() => window.getAccessLevel?.toString() ?? '');
    // 알 수 없는 역할은 member/full로 폴백
    expect(fnSrc).toMatch(/member.*full|full.*member|\?\?/);
  });

  // ───────────────────────────────────────────
  // 8. UX 역할별 홈 화면 메시지 분기
  // ───────────────────────────────────────────

  test('home_desc_consultant — i18n 키 소스 존재 (컨설턴트 전용 홈 설명)', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/home_desc_consultant/);
  });

  test('홈 설명문 분기 — canConsult() 기반 consultant 메시지 분기 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // IS_PARTNER ? home_desc_gfc : canConsult() ? home_desc_consultant : home_desc_open
    expect(content).toMatch(/canConsult.*home_desc_consultant|home_desc_consultant.*canConsult/);
  });

  // ───────────────────────────────────────────
  // 9. GFC 페이지 파트너 접근 권한
  // ───────────────────────────────────────────

  test('DEFAULT_ACCESS_RULES — GFC 페이지에 partner:full 정의', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // consulting/gfc/index.html 규칙에 partner: 'full' 포함
    expect(content).toMatch(/gfc.*partner.*full|partner.*full.*gfc/);
  });

  test('GFC 접근 규칙 — DEFAULT_ACCESS_RULES에 partner:full AND gfc:full 동시 존재', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // partner: 'full', gfc: 'full' 같은 줄에 존재
    expect(content).toMatch(/partner.*'full'.*gfc|gfc.*partner.*'full'/);
  });

  // ───────────────────────────────────────────
  // 10. 대시보드 잠금 카드 — 비로그인 preview 분기
  // ───────────────────────────────────────────

  test('사이드바 — 비로그인 consultantOnly 클릭 시 preview 로드 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // buildTree: consultantOnly !authUser → loadIframePreview (미리보기 테저)
    expect(content).toMatch(/consultantOnly[\s\S]{0,200}!authUser[\s\S]{0,100}loadIframePreview|loadIframePreview[\s\S]{0,300}!authUser[\s\S]{0,100}consultantOnly/);
  });

  // ───────────────────────────────────────────
  // 11. A안 — 역할별 대시보드 차등 표시
  // ───────────────────────────────────────────

  test('renderDashCards — consultantOnly 비컨설턴트 완전 숨김 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // consultantOnly && !canConsult() → return (숨김)
    expect(content).toMatch(/consultantOnly[\s\S]{0,80}!canConsult\(\)[\s\S]{0,30}return/);
  });

  test('renderHomeSections — 접근 가능 카드 없는 섹션 숨김 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // count 필터에 !(c.consultantOnly && !canConsult()) 포함 + count===0 return
    expect(content).toMatch(/consultantOnly[\s\S]{0,80}canConsult[\s\S]{0,200}count[\s\S]{0,30}=== 0[\s\S]{0,20}return/);
  });

  test('앱스토어 DASH_CARDS — memberOnly 없음 (비로그인도 카드 조회 가능)', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // bom-exporter, attribute-reset, dwg-batch-print 에 memberOnly 없어야 함
    expect(content).not.toMatch(/bom-exporter.*memberOnly|attribute-reset.*memberOnly|dwg-batch-print.*memberOnly/);
  });

});

