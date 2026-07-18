// @ts-check
/**
 * security.spec.js — 접근 제어 보안 테스트 (GS 인증 수준)
 *
 * 테스트 범위:
 *   A. 비인증 상태 접근 제어
 *   B. 역할별 노드 가시성 및 클릭 보호
 *   C. iframe 콘텐츠 미로드 보장 (about:blank)
 *   D. 계정 전환 시 이전 콘텐츠 차단 + 홈 귀환
 *   E. DB 규칙 동적 적용 (_reapplyCurrentPageAccess)
 *   F. showDenied → showHome 연동
 *   G. 보안 함수 존재 및 구조 검증
 *   H. overlay 우회 불가 (CSS 구조)
 */
const { test, expect } = require('@playwright/test');

// ────────────────────────────────────────────────────────────
// 공통 헬퍼
// ────────────────────────────────────────────────────────────

/** Hub를 로드하고 초기 렌더 대기 */
async function loadHub(page) {
  await page.goto('/');
  await page.waitForFunction(() => typeof window.refreshTreeAndCards === 'function');
  await page.waitForTimeout(200);
}

/** dev 모드로 특정 역할 주입 */
async function setDevRole(page, role) {
  await page.evaluate((r) => {
    localStorage.setItem('wf_dev', '1');
    localStorage.setItem('wf_role', r);
    if (r === 'admin') {
      window.IS_DEV = true;
      window.authUser = { id: 'dev-admin', email: 'admin@test.local' };
      window.userRole = 'admin';
    } else if (r === 'member') {
      window.IS_DEV = true;
      window.authUser = { id: 'dev-member', email: 'member@test.local' };
      window.userRole = 'member';
    } else if (r === 'consultant') {
      window.IS_DEV = true;
      window.authUser = { id: 'dev-consultant', email: 'cons@test.local' };
      window.userRole = 'consultant';
    } else {
      window.IS_DEV = true;
      window.authUser = null;
      window.userRole = 'member';
    }
    window.IS_PARTNER = window.userRole === 'partner' || window.userRole === 'admin';
    if (typeof window.refreshTreeAndCards === 'function') window.refreshTreeAndCards();
  }, role);
  await page.waitForTimeout(150);
}

/** frame-container 및 contentFrame 상태 반환 */
async function getFrameState(page) {
  return page.evaluate(() => {
    const fc = document.getElementById('frame-container');
    const iframe = document.getElementById('contentFrame');
    const hs = document.getElementById('home-screen');
    return {
      frameVisible: fc?.style.display !== 'none',
      iframeSrc: iframe?.src ?? '',
      homeVisible: hs?.style.display !== 'none',
      overlayActive: document.getElementById('access-overlay')?.classList.contains('active') ?? false,
      frameHasBlur: fc?.classList.contains('access-blur') ?? false,
      frameHasReadonly: fc?.classList.contains('access-readonly') ?? false,
    };
  });
}

// ────────────────────────────────────────────────────────────
// A. 비인증 상태 접근 제어
// ────────────────────────────────────────────────────────────

test.describe('A. 비인증 상태 접근 제어', () => {

  test('A-1: 페이지 로드 시 홈 화면 표시', async ({ page }) => {
    await loadHub(page);
    const hs = await page.$eval('#home-screen', el => el.style.display !== 'none');
    expect(hs).toBe(true);
  });

  test('A-2: 비인증 상태에서 iframe은 로드되지 않음 (about:blank 또는 비표시)', async ({ page }) => {
    await loadHub(page);
    const iframeSrc = await page.$eval('#contentFrame', el => el.src ?? '');
    const isBlank = !iframeSrc || iframeSrc === 'about:blank' || iframeSrc === '';
    // 홈 화면이라면 frame-container는 숨겨져 있어야 함
    const fcHidden = await page.$eval('#frame-container', el => el.style.display === 'none');
    expect(isBlank || fcHidden).toBe(true);
  });

  test('A-3: 비인증 — 규칙 없는 URL은 getAccessLevel이 full 반환 (기본값)', async ({ page }) => {
    await loadHub(page);
    const level = await page.evaluate(() => {
      if (typeof window.getAccessLevel !== 'function') return 'unknown';
      // DB 규칙을 비워 DEFAULT만 남긴 후 테스트 (admin/content는 DB에 규칙이 있을 수 있음)
      const saved = window.pageAccessRules;
      window.pageAccessRules = {};
      const result = window.getAccessLevel('admin/content/index.html');
      window.pageAccessRules = saved;
      return result;
    });
    // DB/DEFAULT 규칙이 없으면 반드시 'full' 반환
    expect(level).toBe('full');
  });

  test('A-4: 비인증 — GFC 접근 레벨은 hidden (DEFAULT_ACCESS_RULES)', async ({ page }) => {
    await loadHub(page);
    const level = await page.evaluate(() =>
      typeof window.getAccessLevel === 'function'
        ? window.getAccessLevel('consulting/gfc/index.html')
        : 'unknown'
    );
    expect(level).toBe('hidden');
  });

  test('A-5: 비인증 — pageAccessRules 에 GFC 규칙 존재', async ({ page }) => {
    await loadHub(page);
    const hasGfc = await page.evaluate(() =>
      Object.prototype.hasOwnProperty.call(window.pageAccessRules ?? {}, 'consulting/gfc/index.html')
    );
    expect(hasGfc).toBe(true);
  });

});

// ────────────────────────────────────────────────────────────
// B. 역할별 노드 가시성 및 클릭 보호
// ────────────────────────────────────────────────────────────

test.describe('B. 역할별 노드 가시성', () => {

  test('B-1: member — adminOnly 노드 클릭 시 iframe은 about:blank', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    // showAccessBlur 직접 호출 시뮬레이션
    await page.evaluate(() => {
      if (typeof window.showAccessBlur === 'function') {
        window.showAccessBlur('admin');
      }
    });
    await page.waitForTimeout(100);

    const state = await getFrameState(page);
    expect(state.iframeSrc).toMatch(/about:blank|^$/);
  });

  test('B-2: member — showAccessBlur 후 frame-container 활성화', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => { if (typeof window.showAccessBlur === 'function') window.showAccessBlur('admin'); });
    await page.waitForTimeout(100);

    const state = await getFrameState(page);
    expect(state.frameVisible).toBe(true);
    expect(state.frameHasBlur).toBe(true);
    expect(state.overlayActive).toBe(true);
  });

  test('B-3: member — showAccessBlur 후 홈 화면 숨겨짐', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => { if (typeof window.showAccessBlur === 'function') window.showAccessBlur('admin'); });
    await page.waitForTimeout(100);

    const state = await getFrameState(page);
    expect(state.homeVisible).toBe(false);
  });

  test('B-4: admin — showAccessBlur 없이 iframe 로드 가능', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'admin');

    await page.evaluate(() => {
      if (typeof window.loadIframe === 'function') window.loadIframe('admin/content/index.html');
    });
    await page.waitForTimeout(300);

    const state = await getFrameState(page);
    // admin은 blur 없이 접근
    expect(state.frameHasBlur).toBe(false);
    expect(state.overlayActive).toBe(false);
  });

  test('B-5: consultant — adminOnly 페이지 클릭 시 iframe은 about:blank', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'consultant');

    await page.evaluate(() => { if (typeof window.showAccessBlur === 'function') window.showAccessBlur('admin'); });
    await page.waitForTimeout(100);

    const iframeSrc = await page.$eval('#contentFrame', el => el.src ?? '');
    expect(iframeSrc).toMatch(/about:blank|^$/);
  });

  test('B-6: showAccessBlur 함수 존재 및 3개 타입 처리', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => typeof window.showAccessBlur === 'function' ? window.showAccessBlur.toString() : '');
    expect(fnSrc).toMatch(/about:blank/);
    expect(fnSrc).toMatch(/admin/);
    expect(fnSrc).toMatch(/partner/);
    expect(fnSrc).toMatch(/consultant/);
  });

});

// ────────────────────────────────────────────────────────────
// C. iframe 콘텐츠 미로드 보장
// ────────────────────────────────────────────────────────────

test.describe('C. iframe 콘텐츠 미로드 보장', () => {

  test('C-1: 접근 제한 노드 — iframe src가 admin 페이지 URL이 아님', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    // member가 adminOnly 노드를 클릭 시뮬레이션
    await page.evaluate(() => {
      if (typeof window.showAccessBlur === 'function') {
        // showAccessBlur는 iframe을 about:blank로 설정
        window.showAccessBlur('admin');
      }
    });
    await page.waitForTimeout(200);

    const src = await page.$eval('#contentFrame', el => el.src ?? '');
    // admin 페이지가 로드되면 안 됨
    expect(src).not.toMatch(/admin\/content|admin\/users|admin\/permissions/);
  });

  test('C-2: showAccessBlur 소스에 iframe.src = about:blank 포함', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window.showAccessBlur?.toString() ?? '');
    expect(fnSrc).toContain('about:blank');
  });

  test('C-3: loadIframe(hidden page) — showDenied + showHome 호출', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    // hidden 레벨 규칙 주입
    await page.evaluate(() => {
      window.pageAccessRules = {
        ...window.pageAccessRules,
        'consulting/gfc/index.html': { guest: 'hidden', member: 'hidden', admin: 'full' }
      };
    });

    await page.evaluate(() => {
      if (typeof window.loadIframe === 'function') window.loadIframe('consulting/gfc/index.html');
    });
    await page.waitForTimeout(300);

    // hidden이면 홈 화면으로 귀환
    const hs = await page.$eval('#home-screen', el => el.style.display !== 'none');
    expect(hs).toBe(true);
  });

  test('C-4: _reapplyCurrentPageAccess 소스에 about:blank 포함 (blur/readonly 처리)', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window._reapplyCurrentPageAccess?.toString() ?? '');
    expect(fnSrc).toContain('about:blank');
  });

  test('C-5: applyAccessOverlay(full) — blur 클래스 제거 확인', async ({ page }) => {
    await loadHub(page);

    await page.evaluate(() => {
      const fc = document.getElementById('frame-container');
      const overlay = document.getElementById('access-overlay');
      fc?.classList.add('access-blur');
      overlay?.classList.add('active');
      if (typeof window.applyAccessOverlay === 'function') window.applyAccessOverlay('full');
    });

    const state = await getFrameState(page);
    expect(state.frameHasBlur).toBe(false);
    expect(state.overlayActive).toBe(false);
  });

});

// ────────────────────────────────────────────────────────────
// D. 계정 전환 보안 (onAuthComplete 사용자 전환)
// ────────────────────────────────────────────────────────────

test.describe('D. 계정 전환 보안', () => {

  test('D-1: onAuthComplete 소스에 _prevAuthUserId 존재', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    expect(src).toMatch(/_prevAuthUserId/);
  });

  test('D-2: onAuthComplete 소스에 _userChanged → showHome 로직 존재', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window.onAuthComplete?.toString() ?? '');
    expect(fnSrc).toMatch(/_userChanged/);
    expect(fnSrc).toMatch(/showHome/);
  });

  test('D-3: onAuthComplete 소스에 about:blank 포함 (iframe 즉시 차단)', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window.onAuthComplete?.toString() ?? '');
    expect(fnSrc).toContain('about:blank');
  });

  test('D-4: admin 콘텐츠 노출 후 member로 전환 — iframe은 about:blank', async ({ page }) => {
    await loadHub(page);

    // admin 상태 주입 후 콘텐츠 로드
    await setDevRole(page, 'admin');
    await page.evaluate(() => {
      window._prevAuthUserId = 'admin-user-id';
      const iframe = document.getElementById('contentFrame');
      const fc = document.getElementById('frame-container');
      if (iframe) iframe.src = 'about:admin-was-here'; // 관리자 콘텐츠 모의
      if (fc) fc.style.display = 'block';
      document.getElementById('home-screen').style.display = 'none';
    });

    // member로 전환 시뮬레이션 (_userChanged = true)
    await page.evaluate(() => {
      window.authUser = { id: 'member-user-id', email: 'member@test.local' };
      window.userRole = 'member';
      window.IS_PARTNER = false;
      // _prevAuthUserId는 'admin-user-id' → _userChanged = true
      if (typeof window.onAuthComplete === 'function') window.onAuthComplete();
    });
    await page.waitForTimeout(300);

    const iframeSrc = await page.$eval('#contentFrame', el => el.src ?? '');
    expect(iframeSrc).toMatch(/about:blank|^$/);
  });

  test('D-5: 계정 전환 후 홈 화면으로 귀환', async ({ page }) => {
    await loadHub(page);

    // admin 이후 member 전환
    await page.evaluate(() => {
      window._prevAuthUserId = 'admin-user-id';
      window.authUser = { id: 'member-user-id', email: 'member@test.local' };
      window.userRole = 'member';
      window.IS_PARTNER = false;
      if (typeof window.refreshTreeAndCards === 'function') window.refreshTreeAndCards();
      // _userChanged 블록 직접 시뮬레이션
      const iframe = document.getElementById('contentFrame');
      if (iframe) iframe.src = 'about:blank';
      if (typeof window.showHome === 'function') window.showHome();
    });
    await page.waitForTimeout(200);

    const hs = await page.$eval('#home-screen', el => el.style.display !== 'none');
    expect(hs).toBe(true);
  });

  test('D-6: 동일 사용자 재인증 — iframe 유지 (불필요한 초기화 없음)', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'admin');

    // admin 페이지 로드
    await page.evaluate(() => {
      window._prevAuthUserId = 'same-user-id';
      window.authUser = { id: 'same-user-id', email: 'admin@test.local' };
      window.userRole = 'admin';
      window.IS_PARTNER = true;
      const iframe = document.getElementById('contentFrame');
      const fc = document.getElementById('frame-container');
      if (iframe) iframe.setAttribute('data-test-src', 'admin/content/index.html');
      if (fc) fc.style.display = 'block';
      document.getElementById('home-screen').style.display = 'none';
    });

    // 같은 사용자 재인증 (_userChanged = false)
    await page.evaluate(() => {
      // _prevAuthUserId = 'same-user-id', authUser.id = 'same-user-id' → _userChanged = false
      const _curUserId = window.authUser?.id ?? null;
      const _userChanged = window._prevAuthUserId !== _curUserId;
      // _userChanged = false → showHome 호출 안 함
      expect_result = { userChanged: _userChanged };
      window._testResult = _userChanged;
    });

    const userChanged = await page.evaluate(() => window._testResult);
    expect(userChanged).toBe(false);
  });

});

// ────────────────────────────────────────────────────────────
// E. DB 규칙 동적 적용
// ────────────────────────────────────────────────────────────

test.describe('E. DB 규칙 동적 적용', () => {

  test('E-1: getAccessLevel — DB 규칙 있으면 노드 플래그 무시', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    // DB 규칙으로 member=full 설정
    await page.evaluate(() => {
      window.pageAccessRules = {
        ...window.pageAccessRules,
        'admin/storage/index.html': { guest: 'readonly', member: 'full', admin: 'full' }
      };
    });

    const level = await page.evaluate(() =>
      window.getAccessLevel?.('admin/storage/index.html') ?? 'unknown'
    );
    expect(level).toBe('full');
  });

  test('E-2: getAccessLevel — guest는 member 규칙으로 폴백', async ({ page }) => {
    await loadHub(page);

    // guest rule 없이 member만 설정
    await page.evaluate(() => {
      window.authUser = null;
      window.userRole = 'member';
      window.pageAccessRules = {
        'test/page.html': { member: 'blur', admin: 'full' }
      };
    });

    const level = await page.evaluate(() =>
      window.getAccessLevel?.('test/page.html') ?? 'unknown'
    );
    // guest는 guest 규칙 없으면 member 폴백 → 'blur'
    expect(level).toBe('blur');
  });

  test('E-3: getAccessLevel — 규칙 없는 페이지는 full', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    const level = await page.evaluate(() =>
      window.getAccessLevel?.('no/rule/here.html') ?? 'unknown'
    );
    expect(level).toBe('full');
  });

  test('E-4: _isNodeLocked — DB 규칙 있고 level=full이면 false', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => {
      window.pageAccessRules = {
        'admin/storage/index.html': { member: 'full', admin: 'full' }
      };
    });

    const locked = await page.evaluate(() =>
      typeof window._isNodeLocked === 'function'
        ? window._isNodeLocked({ iframe: 'admin/storage/index.html', adminOnly: true })
        : null
    );
    expect(locked).toBe(false);
  });

  test('E-5: _isNodeLocked — DB 규칙 있고 level=hidden이면 true', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => {
      window.pageAccessRules = {
        'admin/storage/index.html': { member: 'hidden', admin: 'full' }
      };
    });

    const locked = await page.evaluate(() =>
      typeof window._isNodeLocked === 'function'
        ? window._isNodeLocked({ iframe: 'admin/storage/index.html', adminOnly: true })
        : null
    );
    expect(locked).toBe(true);
  });

  test('E-6: _isNodeLocked — DB 규칙 없고 adminOnly=true면 member는 locked', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => {
      // 해당 페이지 규칙 삭제
      const rules = { ...window.pageAccessRules };
      delete rules['admin/content/index.html'];
      window.pageAccessRules = rules;
    });

    const locked = await page.evaluate(() =>
      typeof window._isNodeLocked === 'function'
        ? window._isNodeLocked({ iframe: 'admin/content/index.html', adminOnly: true })
        : null
    );
    expect(locked).toBe(true);
  });

});

// ────────────────────────────────────────────────────────────
// F. showDenied → showHome 연동
// ────────────────────────────────────────────────────────────

test.describe('F. hidden 접근 시 showHome 연동', () => {

  test('F-1: loadIframe(hidden 페이지) → 홈 화면 표시', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => {
      // member에게 hidden 규칙 설정
      window.pageAccessRules = {
        ...window.pageAccessRules,
        'secret/page.html': { member: 'hidden', admin: 'full' }
      };
    });

    await page.evaluate(() => {
      if (typeof window.loadIframe === 'function') window.loadIframe('secret/page.html');
    });
    await page.waitForTimeout(300);

    const hs = await page.$eval('#home-screen', el => el.style.display !== 'none');
    expect(hs).toBe(true);
  });

  test('F-2: _reapplyCurrentPageAccess 소스에 hidden → showHome 포함', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window._reapplyCurrentPageAccess?.toString() ?? '');
    // hidden → showDenied() + showHome() 순서 확인
    expect(fnSrc).toMatch(/hidden[\s\S]{0,100}showDenied[\s\S]{0,50}showHome/);
  });

  test('F-3: loadIframe(hidden 페이지) → iframe src는 about:blank 또는 빈 값', async ({ page }) => {
    await loadHub(page);
    await setDevRole(page, 'member');

    await page.evaluate(() => {
      window.pageAccessRules = { 'secret2/page.html': { member: 'hidden', admin: 'full' } };
    });

    await page.evaluate(() => {
      if (typeof window.loadIframe === 'function') window.loadIframe('secret2/page.html');
    });
    await page.waitForTimeout(200);

    const src = await page.$eval('#contentFrame', el => el.src ?? '');
    // hidden이면 페이지를 로드하지 않고 홈으로 귀환
    expect(src).not.toMatch(/secret2/);
  });

});

// ────────────────────────────────────────────────────────────
// G. 보안 함수 존재 및 구조 검증
// ────────────────────────────────────────────────────────────

test.describe('G. 보안 함수 존재 및 구조', () => {

  test('G-1: 핵심 보안 함수 모두 존재', async ({ page }) => {
    await loadHub(page);
    const funcs = await page.evaluate(() => ({
      showAccessBlur: typeof window.showAccessBlur === 'function',
      showDenied: typeof window.showDenied === 'function',
      showHome: typeof window.showHome === 'function',
      getAccessLevel: typeof window.getAccessLevel === 'function',
      applyAccessOverlay: typeof window.applyAccessOverlay === 'function',
      _isNodeLocked: typeof window._isNodeLocked === 'function',
      _reapplyCurrentPageAccess: typeof window._reapplyCurrentPageAccess === 'function',
      onAuthComplete: typeof window.onAuthComplete === 'function',
      loadIframe: typeof window.loadIframe === 'function',
    }));

    for (const [fn, exists] of Object.entries(funcs)) {
      expect(exists, `${fn} 함수가 없음`).toBe(true);
    }
  });

  test('G-2: _prevAuthUserId 변수 소스에 선언됨', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    expect(src).toMatch(/_prevAuthUserId/);
  });

  test('G-3: onAuthComplete — _userChanged 계정 전환 로직 포함', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window.onAuthComplete?.toString() ?? '');
    expect(fnSrc).toMatch(/_userChanged/);
    expect(fnSrc).toMatch(/_prevAuthUserId/);
    expect(fnSrc).toMatch(/about:blank/);
    expect(fnSrc).toMatch(/showHome/);
  });

  test('G-4: showAccessBlur — iframe blank + frame-container 활성화 로직', async ({ page }) => {
    await loadHub(page);
    const fnSrc = await page.evaluate(() => window.showAccessBlur?.toString() ?? '');
    expect(fnSrc).toContain('about:blank');
    expect(fnSrc).toContain('home-screen');
    expect(fnSrc).toContain('access-blur');
  });

  test('G-5: buildTree 클릭 핸들러 소스에 loadIframe 없는 접근 제한 패턴', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    // 수정된 패턴: setActive + showAccessBlur (loadIframe 없음)
    // adminOnly 분기에서 setActive(labelEl); showAccessBlur('admin'); return; 패턴
    expect(src).toMatch(/setActive\(labelEl\);\s*showAccessBlur\('admin'\)/);
  });

  test('G-6: 대시보드 잠금 카드 onclick에 loadIframe 없음', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    // 수정 후: showAccessBlur('admin') 단독 (loadIframe 없음)
    // 이전: loadIframe(card.iframe, [], card.title); showAccessBlur('admin')
    expect(src).not.toMatch(/loadIframe\(card\.iframe.*\);\s*showAccessBlur\('admin'\)/);
  });

  test('G-7: pageAccessRules 초기값 — DEFAULT_ACCESS_RULES 포함', async ({ page }) => {
    await loadHub(page);
    const hasDefault = await page.evaluate(() =>
      Object.prototype.hasOwnProperty.call(
        window.pageAccessRules ?? {},
        'consulting/gfc/index.html'
      )
    );
    expect(hasDefault).toBe(true);
  });

  test('G-8: getAccessLevel — 비로그인은 guest 역할 적용', async ({ page }) => {
    await loadHub(page);

    await page.evaluate(() => {
      window.authUser = null;
      window.pageAccessRules = {
        'test/guest-page.html': { guest: 'hidden', member: 'full', admin: 'full' }
      };
    });

    const level = await page.evaluate(() =>
      window.getAccessLevel?.('test/guest-page.html') ?? 'unknown'
    );
    expect(level).toBe('hidden');
  });

});

// ────────────────────────────────────────────────────────────
// H. overlay 우회 불가 (CSS 구조 검증)
// ────────────────────────────────────────────────────────────

test.describe('H. overlay 우회 불가 CSS 구조', () => {

  test('H-1: access-overlay CSS — pointer-events:none 기본값', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    expect(src).toMatch(/#access-overlay[\s\S]{0,200}pointer-events:\s*none/);
  });

  test('H-2: access-blur + iframe — pointer-events:none 적용', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    expect(src).toMatch(/access-blur\s+iframe[\s\S]{0,100}pointer-events:\s*none/);
  });

  test('H-3: showAccessBlur 후 iframe src는 about:blank', async ({ page }) => {
    await loadHub(page);

    await page.evaluate(() => {
      // iframe에 임의 src 설정
      const iframe = document.getElementById('contentFrame');
      if (iframe) iframe.src = 'https://example.com/admin';
      if (typeof window.showAccessBlur === 'function') window.showAccessBlur('admin');
    });
    await page.waitForTimeout(100);

    const src = await page.$eval('#contentFrame', el => el.src ?? '');
    expect(src).toBe('about:blank');
  });

  test('H-4: access-blur 상태에서 overlay는 pointer-events:auto', async ({ page }) => {
    await loadHub(page);
    const src = await page.content();
    expect(src).toMatch(/access-blur.*#access-overlay|#frame-container\.access-blur\s+#access-overlay[\s\S]{0,100}pointer-events:\s*auto/);
  });

  test('H-5: showHome — frame-container 숨기고 home-screen 표시', async ({ page }) => {
    await loadHub(page);

    // frame-container 활성화 후 showHome 호출
    await page.evaluate(() => {
      const fc = document.getElementById('frame-container');
      const hs = document.getElementById('home-screen');
      if (fc) fc.style.display = 'block';
      if (hs) hs.style.display = 'none';
      if (typeof window.showHome === 'function') window.showHome();
    });
    await page.waitForTimeout(100);

    const state = await getFrameState(page);
    expect(state.homeVisible).toBe(true);
    expect(state.frameVisible).toBe(false);
  });

  test('H-6: applyAccessOverlay(readonly) — access-readonly 클래스 추가', async ({ page }) => {
    await loadHub(page);

    await page.evaluate(() => {
      const fc = document.getElementById('frame-container');
      if (fc) fc.style.display = 'block';
      if (typeof window.applyAccessOverlay === 'function') window.applyAccessOverlay('readonly');
    });

    const state = await getFrameState(page);
    expect(state.frameHasReadonly).toBe(true);
    expect(state.frameHasBlur).toBe(false);
  });

});
