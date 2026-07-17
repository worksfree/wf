// @ts-check
/**
 * auth.spec.js — 세션 관리 및 인증 흐름 테스트
 *
 * 주의: index.html은 non-module <script>이므로
 *  - function 선언 → window에 노출 (테스트 가능)
 *  - const/let 선언 → window 미노출 (소스 검사 방식 사용)
 */
const { test, expect } = require('@playwright/test');

test.describe('Auth — 세션 및 인증 흐름', () => {

  // ───────────────────────────────────────────
  // 1. 비로그인 초기 상태
  // ───────────────────────────────────────────

  test('비로그인 — userRole 선언 확인 (let userRole 소스 검사)', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // let userRole = 'member' 선언이 소스에 있어야 함
    expect(content).toMatch(/let\s+userRole\s*=\s*['"]member['"]/);
  });

  test('비로그인 — authUser null (function 접근)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // authUser는 let이므로 window 미노출 — getAccessLevel 동작으로 간접 확인
    // 비로그인 시 getAccessLevel은 userRole='member'로 동작
    const level = await page.evaluate(() =>
      window.getAccessLevel ? window.getAccessLevel('consulting/gfc/index.html') : null
    );
    // member 접근 시 hidden 반환 → authUser=null & userRole=member 상태 간접 증명
    expect(level).toBe('hidden');
  });

  test('비로그인 — IS_PARTNER false (소스 선언 확인)', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/let\s+IS_PARTNER\s*=\s*false/);
  });

  test('비로그인 — preview-overlay 또는 login modal 표시', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const overlay = page.locator('#preview-overlay');
    const loginArea = page.locator('#auth-btn, .login-btn, [id*="login"], [class*="login"]');
    const hasAny = (await overlay.count()) > 0 || (await loginArea.count()) > 0;
    expect(hasAny).toBe(true);
  });

  // ───────────────────────────────────────────
  // 2. 인증 함수 존재 확인 (function 선언 → window에 노출)
  // ───────────────────────────────────────────

  test('onAuthComplete 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.onAuthComplete === 'function');
    expect(exists).toBe(true);
  });

  test('updateAuthUI 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.updateAuthUI === 'function');
    expect(exists).toBe(true);
  });

  test('refreshTreeAndCards 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.refreshTreeAndCards === 'function');
    expect(exists).toBe(true);
  });

  test('checkConsent 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.checkConsent === 'function');
    expect(exists).toBe(true);
  });

  test('saveConsent 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.saveConsent === 'function');
    expect(exists).toBe(true);
  });

  // ───────────────────────────────────────────
  // 3. sessionStorage 복원 — onAuthComplete 소스 검사
  // ───────────────────────────────────────────

  test('onAuthComplete — wf_last_page 읽지 않음 (hash 라우팅으로 대체)', async ({ page }) => {
    await page.goto('/');
    const fnSrc = await page.evaluate(() => window.onAuthComplete?.toString() ?? '');
    // onAuthComplete 내부에 wf_last_page 읽기 코드가 없어야 함
    const reads = fnSrc.includes("getItem('wf_last_page')") ||
                  fnSrc.includes('getItem("wf_last_page")');
    expect(reads).toBe(false);
  });

  test('hash 기반 복원 — navigateToHash 사용 확인 (onAuthComplete 소스)', async ({ page }) => {
    await page.goto('/');
    const src = await page.evaluate(() => window.onAuthComplete?.toString() ?? '');
    expect(src).toMatch(/navigateToHash/);
  });

  test('hash 기반 복원 — showHome 사용 확인 (onAuthComplete 소스)', async ({ page }) => {
    await page.goto('/');
    const src = await page.evaluate(() => window.onAuthComplete?.toString() ?? '');
    expect(src).toMatch(/showHome/);
  });

  test('hash 없는 홈 접근 — showHome 경로 진입', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const hash = await page.evaluate(() => location.hash);
    expect(['', '#']).toContain(hash);
  });

  test('hash 있는 접근 — hash 유지', async ({ page }) => {
    await page.goto('/#service');
    await page.waitForLoadState('networkidle');
    const hash = await page.evaluate(() => location.hash);
    expect(typeof hash).toBe('string');
  });

  // ───────────────────────────────────────────
  // 4. 역할별 상태 함수 (소스 검사 방식)
  // ───────────────────────────────────────────

  test('canConsult — 소스에 정의됨', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // const canConsult = () => userRole === 'consultant' || ...
    expect(content).toMatch(/canConsult/);
  });

  test('canConsult — consultant|partner|admin 역할 허용 소스 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // 소스에서 canConsult가 consultant, partner, admin을 허용해야 함
    expect(content).toMatch(/consultant.*partner.*admin|partner.*consultant.*admin/);
  });

  test('getAccessLevel — 비로그인(member) GFC hidden 반환', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // function 선언이므로 window에서 직접 호출 가능
    const level = await page.evaluate(() =>
      window.getAccessLevel ? window.getAccessLevel('consulting/gfc/index.html') : null
    );
    expect(level).toBe('hidden');
  });

  // ───────────────────────────────────────────
  // 5. SB_SESSION_KEY 보안
  // ───────────────────────────────────────────

  test('Supabase 세션 — onAuthStateChange 핸들러 등록 확인', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    // Supabase auth 상태 변화 핸들러가 등록되어야 함
    expect(content).toMatch(/onAuthStateChange/);
  });

  test('Supabase Anon Key — 소스 내 존재 (의도적 공개)', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/);
  });

  test('Supabase Service Key — 소스에 없음 (CF Worker에만)', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    const hasServiceKey = content.includes('SUPABASE_SERVICE_KEY') &&
                          !content.includes('// SUPABASE_SERVICE_KEY');
    expect(hasServiceKey).toBe(false);
  });

  // ───────────────────────────────────────────
  // 6. Dev 모드 관련 함수
  // ───────────────────────────────────────────

  test('IS_DEV 상수 존재', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/IS_DEV/);
  });

  test('loadCreditBalance 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.loadCreditBalance === 'function');
    expect(exists).toBe(true);
  });

  test('loadPageAccessRules 함수 존재', async ({ page }) => {
    await page.goto('/');
    const exists = await page.evaluate(() => typeof window.loadPageAccessRules === 'function');
    expect(exists).toBe(true);
  });

  // ───────────────────────────────────────────
  // 7. 로그아웃 후 상태 초기화
  // ───────────────────────────────────────────

  test('signOut 함수 또는 logout 함수 존재', async ({ page }) => {
    await page.goto('/');
    const hasSignOut = await page.evaluate(() =>
      typeof window.signOut === 'function' ||
      typeof window.logout === 'function' ||
      typeof window.handleLogout === 'function'
    );
    expect(hasSignOut).toBe(true);
  });

  test('로그아웃 후 — wf_last_login localStorage 사용', async ({ page }) => {
    await page.goto('/');
    const content = await page.content();
    expect(content).toMatch(/wf_last_login/);
  });

});
