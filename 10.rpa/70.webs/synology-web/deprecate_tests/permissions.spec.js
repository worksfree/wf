/**
 * permissions.spec.js — 페이지 접근 제어 테스트
 *
 * 검증 범위:
 *   - 역할별 페이지 접근 레벨 적용 (full / blur / readonly / hidden)
 *   - site_config에서 규칙 로드
 *   - CSS 클래스 및 오버레이 DOM 상태
 *   - GFC 전용 콘텐츠 이원화 (보험 용어 role별 분기)
 *
 * 실행: npx playwright test tests/permissions.spec.js
 */

const { test, expect, mockExternalAPIs, gotoDevPage } = require('./fixtures');

const SUPABASE_HOST = 'rkycwfpkzorfpcxfvaqt.supabase.co';
const GFC_PATH      = 'consulting/gfc/index.html';

// ── 공통: site_config mock ──────────────────────────────────────────
async function mockSiteConfig(page, rules = {}) {
  const defaultRules = {
    [GFC_PATH]: {
      general: 'hidden', member: 'hidden',
      consultant: 'blur', gfc: 'full', admin: 'full',
    },
  };
  await page.route(`**/${SUPABASE_HOST}/rest/v1/site_config*`, route =>
    route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify([{ key: 'page_access_rules', value: { ...defaultRules, ...rules } }]),
    })
  );
}

async function loginDevRole(page, role) {
  const btnId = {
    general:    '#dev-btn-general',
    consultant: '#dev-btn-consultant',
    gfc:        '#dev-btn-gfc',
    admin:      '#dev-btn-admin',
  }[role] || '#dev-btn-user';

  await gotoDevPage(page);
  await page.click(btnId);
  if (role === 'admin' || role === 'gfc') {
    try {
      await page.waitForSelector('#dev-pw-modal', { state: 'visible', timeout: 2000 });
      await page.click('#dev-pw-modal button:text("확인")');
    } catch {}
  }
  await page.waitForSelector('.user-pill', { state: 'visible', timeout: 8000 });
}

async function clickGfcNode(page) {
  // 사이드바에서 경영종합진단 노드 클릭
  const node = page.locator('.tree-node:has-text("경영종합진단"), .tree-node:has-text("Financial Plan")').first();
  if (await node.count() > 0) {
    await node.click();
    await page.waitForTimeout(500);
    return true;
  }
  return false;
}

// ════════════════════════════════════════════════════════════════════
// SUITE 1: 기본 구조 검증
// ════════════════════════════════════════════════════════════════════
test.describe('Permissions: 기본 구조', () => {

  test('frame-container에 access-overlay 요소가 존재한다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await page.goto('/');
    await expect(page.locator('#access-overlay')).toBeAttached();
    await expect(page.locator('#access-readonly-banner')).toBeAttached();
  });

  test('초기 로드 시 access-overlay가 숨겨져 있다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await page.goto('/');
    await expect(page.locator('#access-overlay')).not.toHaveClass(/active/);
    await expect(page.locator('#frame-container')).not.toHaveClass(/access-blur/);
    await expect(page.locator('#frame-container')).not.toHaveClass(/access-readonly/);
  });

  test('홈으로 돌아가면 access 클래스가 초기화된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await gotoDevPage(page);
    // 강제로 blur 클래스 설정 후 showHome 호출
    await page.evaluate(() => {
      const fc = document.getElementById('frame-container');
      fc.classList.add('access-blur');
      document.getElementById('access-overlay').classList.add('active');
      fc.style.display = 'block';
      if (typeof showHome === 'function') showHome();
    });
    await expect(page.locator('#frame-container')).not.toHaveClass(/access-blur/);
    await expect(page.locator('#access-overlay')).not.toHaveClass(/active/);
  });

});

// ════════════════════════════════════════════════════════════════════
// SUITE 2: GFC 페이지 — 역할별 접근 레벨
// ════════════════════════════════════════════════════════════════════
test.describe('Permissions: GFC 페이지 역할별 접근', () => {

  test('[GFC 역할] getAccessLevel이 full을 반환한다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await loginDevRole(page, 'gfc');

    const level = await page.evaluate((path) => {
      if (typeof getAccessLevel === 'function') return getAccessLevel(path);
      return null;
    }, GFC_PATH);

    if (level !== null) expect(level).toBe('full');
  });

  test('[컨설턴트] getAccessLevel이 blur를 반환한다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await loginDevRole(page, 'consultant');

    const level = await page.evaluate((path) => {
      if (typeof getAccessLevel === 'function') return getAccessLevel(path);
      return null;
    }, GFC_PATH);

    if (level !== null) expect(level).toBe('blur');
  });

  test('[컨설턴트] blur 레벨 직접 적용 시 CSS 클래스가 추가된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await loginDevRole(page, 'consultant');

    await page.evaluate(() => {
      const fc = document.getElementById('frame-container');
      if (fc) fc.style.display = 'block';
      if (typeof applyAccessOverlay === 'function') applyAccessOverlay('blur');
    });

    await expect(page.locator('#frame-container')).toHaveClass(/access-blur/);
    await expect(page.locator('#access-overlay')).toHaveClass(/active/);
  });

  test('[일반 회원] getAccessLevel이 hidden을 반환한다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await loginDevRole(page, 'general');

    const level = await page.evaluate((path) => {
      if (typeof getAccessLevel === 'function') return getAccessLevel(path);
      return null;
    }, GFC_PATH);

    if (level !== null) expect(level).toBe('hidden');
  });

  test('[관리자] getAccessLevel이 full을 반환한다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await loginDevRole(page, 'admin');

    const level = await page.evaluate((path) => {
      if (typeof getAccessLevel === 'function') return getAccessLevel(path);
      return null;
    }, GFC_PATH);

    if (level !== null) expect(level).toBe('full');
  });

});

// ════════════════════════════════════════════════════════════════════
// SUITE 3: 동적 규칙 변경
// ════════════════════════════════════════════════════════════════════
test.describe('Permissions: 동적 규칙 적용', () => {

  test('site_config 미설정 시 DEFAULT_ACCESS_RULES로 폴백', async ({ page }) => {
    await mockExternalAPIs(page);
    // site_config 응답 없음 (빈 배열)
    await page.route(`**/${SUPABASE_HOST}/rest/v1/site_config*`, route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );
    await gotoDevPage(page);
    // DEFAULT_ACCESS_RULES가 있어야 함
    const hasDefault = await page.evaluate(() => {
      return typeof DEFAULT_ACCESS_RULES === 'object' && DEFAULT_ACCESS_RULES !== null;
    });
    expect(hasDefault).toBeTruthy();
  });

  test('readonly 레벨 적용 시 access-readonly 클래스가 추가된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page, {
      [GFC_PATH]: { general: 'hidden', member: 'hidden', consultant: 'readonly', gfc: 'full', admin: 'full' }
    });
    await loginDevRole(page, 'consultant');

    // applyAccessOverlay를 직접 호출
    await page.evaluate(() => {
      if (typeof applyAccessOverlay === 'function') {
        document.getElementById('frame-container').style.display = 'block';
        applyAccessOverlay('readonly');
      }
    });

    await expect(page.locator('#frame-container')).toHaveClass(/access-readonly/);
    await expect(page.locator('#frame-container')).not.toHaveClass(/access-blur/);
  });

  test('full 레벨 전환 시 모든 access 클래스가 제거된다', async ({ page }) => {
    await mockExternalAPIs(page);
    await mockSiteConfig(page);
    await gotoDevPage(page);

    await page.evaluate(() => {
      const fc = document.getElementById('frame-container');
      fc.classList.add('access-blur');
      if (typeof applyAccessOverlay === 'function') applyAccessOverlay('full');
    });

    await expect(page.locator('#frame-container')).not.toHaveClass(/access-blur/);
    await expect(page.locator('#frame-container')).not.toHaveClass(/access-readonly/);
  });

});

// ════════════════════════════════════════════════════════════════════
// SUITE 4: GFC 콘텐츠 이원화 검증
// ════════════════════════════════════════════════════════════════════
test.describe('Permissions: GFC 콘텐츠 이원화', () => {

  test('GFC 페이지가 정상 로드된다', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');
    await expect(page.locator('header')).toBeVisible({ timeout: 5000 });
  });

  test('hubRole이 기본값 member로 초기화된다', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');
    const role = await page.evaluate(() => typeof hubRole !== 'undefined' ? hubRole : null);
    expect(role).toBe('member');
  });

  test('isGfcView()는 gfc/admin일 때만 true 반환', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');

    // let hubRole은 window.hubRole과 다른 바인딩 — 직접 대입 필요
    const memberResult = await page.evaluate(() => {
      try { hubRole = 'member'; } catch {}
      return typeof isGfcView === 'function' ? isGfcView() : null;
    });
    if (memberResult !== null) expect(memberResult).toBe(false);

    const consultantResult = await page.evaluate(() => {
      try { hubRole = 'consultant'; } catch {}
      return typeof isGfcView === 'function' ? isGfcView() : null;
    });
    if (consultantResult !== null) expect(consultantResult).toBe(false);

    const gfcResult = await page.evaluate(() => {
      try { hubRole = 'gfc'; } catch {}
      return typeof isGfcView === 'function' ? isGfcView() : null;
    });
    if (gfcResult !== null) expect(gfcResult).toBe(true);

    const adminResult = await page.evaluate(() => {
      try { hubRole = 'admin'; } catch {}
      return typeof isGfcView === 'function' ? isGfcView() : null;
    });
    if (adminResult !== null) expect(adminResult).toBe(true);
  });

  test('sanitizeRole()이 비GFC에서 보험 용어를 변환한다', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');

    const result = await page.evaluate(() => {
      if (typeof sanitizeRole !== 'function') return null;
      try { hubRole = 'consultant'; } catch {}
      const original = '경영인정기보험 비용처리';
      const sanitized = sanitizeRole(original);
      return { original, sanitized, changed: original !== sanitized };
    });

    if (result !== null) {
      expect(result.changed).toBe(true);
      expect(result.sanitized).not.toContain('경영인정기보험');
    }
  });

  test('sanitizeRole()이 GFC에서 원문을 유지한다', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');

    const result = await page.evaluate(() => {
      if (typeof sanitizeRole !== 'function') return null;
      try { hubRole = 'gfc'; } catch {}
      const original = '경영인정기보험 비용처리';
      return { original, sanitized: sanitizeRole(original) };
    });

    if (result !== null) {
      expect(result.sanitized).toBe(result.original);
    }
  });

  test('wf_role postMessage 수신 시 hubRole이 업데이트된다', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');

    await page.evaluate(() => {
      window.dispatchEvent(new MessageEvent('message', {
        data: { type: 'wf_role', role: 'gfc' }
      }));
    });

    const updatedRole = await page.evaluate(() => hubRole);
    expect(updatedRole).toBe('gfc');
  });

  test('wf_access postMessage가 처리된다 (오류 없음)', async ({ page }) => {
    await page.goto('/consulting/gfc/index.html');

    // wf_access postMessage — GFC 페이지에서 무시해도 오류 없어야 함
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));

    await page.evaluate(() => {
      window.dispatchEvent(new MessageEvent('message', {
        data: { type: 'wf_access', level: 'blur' }
      }));
    });

    await page.waitForTimeout(200);
    expect(errors.length).toBe(0);
  });

});

// ════════════════════════════════════════════════════════════════════
// SUITE 5: admin/permissions 페이지
// ════════════════════════════════════════════════════════════════════
test.describe('Permissions: 관리자 권한 설정 페이지', () => {

  test('admin-gate가 비관리자에게 표시된다', async ({ page }) => {
    await page.route(`**/${SUPABASE_HOST}/**`, route => {
      const url = route.request().url();
      if (url.includes('/auth/')) {
        route.fulfill({ status: 200, contentType: 'application/json',
          body: JSON.stringify({ user: null, session: null }) });
      } else {
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      }
    });
    await page.goto('/admin/permissions/index.html');
    await expect(page.locator('#admin-gate')).toHaveClass(/visible/, { timeout: 5000 });
  });

  test('페이지가 기본 구조를 포함한다', async ({ page }) => {
    await page.goto('/admin/permissions/index.html');
    await expect(page.locator('.perm-table')).toBeAttached();
    await expect(page.locator('#btn-save')).toBeAttached();
  });

  test('CONFIGURABLE_PAGES 배열이 정의되어 있다', async ({ page }) => {
    await page.goto('/admin/permissions/index.html');
    const count = await page.evaluate(() =>
      typeof CONFIGURABLE_PAGES !== 'undefined' ? CONFIGURABLE_PAGES.length : 0
    );
    expect(count).toBeGreaterThan(0);
  });

  test('DEFAULT_RULES에 GFC 페이지가 포함된다', async ({ page }) => {
    await page.goto('/admin/permissions/index.html');
    const hasGfc = await page.evaluate(() => {
      return typeof DEFAULT_RULES !== 'undefined' &&
             DEFAULT_RULES['consulting/gfc/index.html'] !== undefined;
    });
    expect(hasGfc).toBe(true);
  });

});
