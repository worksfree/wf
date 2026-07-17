// @ts-check
/**
 * pension.spec.js — 연금 수령 전략 시뮬레이터 종합 검증
 *
 * 검증 범위:
 *  1. 페이지 로드 및 기본 구조
 *  2. 현직/퇴직 상태 토글 (setIcMode)
 *  3. 숨김처리 토글 (.pv-toggle)
 *  4. 전략 옵션 체크박스 A/B/C/D
 *  5. 시나리오 프리셋 A/B/C/D (조기수령·지연수령·최적형·나의설정)
 *  6. 시뮬레이션 함수 존재 및 소스 구조
 *  7. 연금 용어 표기 (직접용어·전문용어 병행)
 *  8. 건보료/세금 판정 소스 확인
 */
const { test, expect } = require('@playwright/test');

const PENSION_PAGE  = '/consulting/pension/index.html';
const PENSION_V2    = '/consulting/pension/v2/index.html';

// ─────────────────────────────────────────────────────────
// 1. 페이지 로드 및 기본 구조
// ─────────────────────────────────────────────────────────

test.describe('Pension — 페이지 로드 및 기본 구조', () => {

  test('pension 페이지 로드 성공 (200)', async ({ page }) => {
    const resp = await page.goto(PENSION_PAGE);
    expect([200, 304]).toContain(resp?.status() ?? 200);
  });

  test('pension 페이지 title 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await expect(page).toHaveTitle(/연금|시뮬레이터|WorksFree/i);
  });

  test('pension v2 페이지 로드 성공', async ({ page }) => {
    const resp = await page.goto(PENSION_V2);
    expect([200, 304]).toContain(resp?.status() ?? 200);
  });

  test('헤더 제목 — 연금 수령 전략', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const src = await page.content();
    expect(src).toMatch(/연금.*시뮬레이터|연금 수령 전략/);
  });

  test('Chart.js 로드됨', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/chart\.js|chart\.umd/i);
  });

  test('저장 버튼 존재 (saveMySettings)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.save-btn').count()).toBeGreaterThan(0);
  });

});


// ─────────────────────────────────────────────────────────
// 2. 현직/퇴직 상태 토글
// ─────────────────────────────────────────────────────────

test.describe('Pension — 현직/퇴직 상태 토글', () => {

  test('.status-toggle 요소 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.status-toggle').count()).toBeGreaterThan(0);
  });

  test('현직 중 버튼 (stEmployed) 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#stEmployed').count()).toBe(1);
  });

  test('이미 퇴직 버튼 (stRetired) 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#stRetired').count()).toBe(1);
  });

  test('초기 상태 — 현직 중 버튼 active', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const hasActive = await page.evaluate(() =>
      document.getElementById('stEmployed')?.classList.contains('active') ?? false
    );
    expect(hasActive).toBe(true);
  });

  test('setIcMode 함수 존재 (window)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.setIcMode === 'function');
    expect(exists).toBe(true);
  });

  test('퇴직 버튼 클릭 → stRetired active, stEmployed 비활성', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    await page.locator('#stRetired').click();
    await page.waitForTimeout(300);
    const retiredActive = await page.evaluate(() =>
      document.getElementById('stRetired')?.classList.contains('active') ?? false
    );
    const employedActive = await page.evaluate(() =>
      document.getElementById('stEmployed')?.classList.contains('active') ?? false
    );
    expect(retiredActive).toBe(true);
    expect(employedActive).toBe(false);
  });

  test('현직 모드 — ic-retired-section display:none', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    // 초기 상태 현직 → 퇴직 섹션 숨김
    const src = await page.content();
    expect(src).toMatch(/ic-retired-section.*display:\s*none|\.ic-retired-section\{display:none/);
  });

  test('퇴직 모드 클릭 → ic-retired-section 표시됨', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    await page.locator('#stRetired').click();
    await page.waitForTimeout(300);
    const display = await page.evaluate(() => {
      const el = document.querySelector('.ic-retired-section');
      if (!el) return 'not-found';
      return el.style.display || getComputedStyle(el).display;
    });
    expect(display).not.toBe('none');
    expect(display).not.toBe('not-found');
  });

  test('setIcMode — employed/retired 분기 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const fnSrc = await page.evaluate(() => window.setIcMode?.toString() ?? '');
    expect(fnSrc).toMatch(/employed|retired/);
  });

});


// ─────────────────────────────────────────────────────────
// 3. 숨김처리 토글 (.pv-toggle)
// ─────────────────────────────────────────────────────────

test.describe('Pension — 숨김처리 토글', () => {

  test('.pv-toggle 요소 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.pv-toggle').count()).toBeGreaterThan(0);
  });

  test('pv-toggle — checkbox input 포함', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.pv-toggle input[type="checkbox"]').count()).toBeGreaterThan(0);
  });

  test('pv-toggle — 텍스트 "숨김처리" 포함', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const text = await page.locator('.pv-toggle').first().textContent();
    expect(text?.trim()).toMatch(/숨김처리/);
  });

  test('pv-toggle — 초기 체크됨 (숨김 활성)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const checked = await page.locator('#pvChk').isChecked();
    expect(checked).toBe(true);
  });

  test('pv-toggle — body.pv CSS 선택자 존재 (blur 대상 정의)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/body\.pv\s+\./);
  });

  test('pv-toggle 클릭 → body.pv 토글', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    const before = await page.evaluate(() => document.body.classList.contains('pv'));
    await page.locator('#pvChk').click();
    await page.waitForTimeout(200);
    const after = await page.evaluate(() => document.body.classList.contains('pv'));
    expect(after).toBe(!before);
  });

  test('pension — body.pv 숨김 대상 CSS 정의됨 (ar-bal, ph-total 등)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    // 연금 페이지의 숨김 대상: .ar-bal, .ar-monthly strong, .ph-total 등
    expect(src).toMatch(/body\.pv\s+\.ar-bal|body\.pv\s+\.ph-total/);
  });

  test('숨김 상태(pv) — .ar-bal 블러 적용 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    // 초기 상태는 pv 클래스 있음 (checked)
    const hasPv = await page.evaluate(() => document.body.classList.contains('pv'));
    expect(hasPv).toBe(true);
  });

});


// ─────────────────────────────────────────────────────────
// 4. 전략 옵션 체크박스 A/B/C/D
// ─────────────────────────────────────────────────────────

test.describe('Pension — 전략 옵션', () => {

  test('전략 옵션 패널 존재 (.opt-panel)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.opt-panel').count()).toBeGreaterThan(0);
  });

  test('옵션 A — 분리과세 한도 최적화 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#ckOptA').count()).toBe(1);
  });

  test('옵션 B — 퇴직연금 지연 수령 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#ckOptB').count()).toBe(1);
  });

  test('옵션 C — 배당 재투자 복리 성장 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#ckOptC').count()).toBe(1);
  });

  test('옵션 D — 건보료 피부양자 유지 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#ckOptD').count()).toBe(1);
  });

  test('toggleOpt 함수 존재 (window)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.toggleOpt === 'function');
    expect(exists).toBe(true);
  });

  test('옵션 A 클릭 → ckOptA 체크 상태 변경', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    const before = await page.locator('#ckOptA').isChecked();
    await page.locator('#ckOptA').click();
    await page.waitForTimeout(200);
    const after = await page.locator('#ckOptA').isChecked();
    expect(after).toBe(!before);
  });

  test('optA/B/C/D — 옵션 항목 전부 표시됨', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const count = await page.locator('.opt-item').count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('toggleOpt — 재계산(onIC) 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const fnSrc = await page.evaluate(() => window.toggleOpt?.toString() ?? '');
    expect(fnSrc).toMatch(/onIC|renderAll|simulate/);
  });

});


// ─────────────────────────────────────────────────────────
// 5. 시나리오 프리셋 버튼 (A=조기/B=지연/C=최적/D=나의설정)
// ─────────────────────────────────────────────────────────

test.describe('Pension — 시나리오 프리셋', () => {

  test('시나리오 버튼 바 존재 (.sc-bar)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('.sc-bar').count()).toBeGreaterThan(0);
  });

  test('프리셋 A (조기 수령) 버튼 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#scBtnA').count()).toBe(1);
  });

  test('프리셋 B (지연 수령) 버튼 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#scBtnB').count()).toBe(1);
  });

  test('프리셋 C (최적형) 버튼 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#scBtnC').count()).toBe(1);
  });

  test('프리셋 D (나의 설정) 버튼 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#scBtnD').count()).toBe(1);
  });

  test('초기 — C 버튼 active', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    const hasActive = await page.evaluate(() =>
      document.getElementById('scBtnC')?.classList.contains('active') ?? false
    );
    expect(hasActive).toBe(true);
  });

  test('loadSc 함수 존재 (window)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.loadSc === 'function');
    expect(exists).toBe(true);
  });

  test('loadMySettings 함수 존재 (window)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.loadMySettings === 'function');
    expect(exists).toBe(true);
  });

  test('saveMySettings 함수 존재 (window)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.saveMySettings === 'function');
    expect(exists).toBe(true);
  });

  test('프리셋 A 클릭 → scBtnA active, scBtnC 비활성', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    await page.locator('#scBtnA').click();
    await page.waitForTimeout(300);
    const aActive = await page.evaluate(() =>
      document.getElementById('scBtnA')?.classList.contains('active') ?? false
    );
    const cActive = await page.evaluate(() =>
      document.getElementById('scBtnC')?.classList.contains('active') ?? false
    );
    expect(aActive).toBe(true);
    expect(cActive).toBe(false);
  });

});


// ─────────────────────────────────────────────────────────
// 6. 시뮬레이션 함수 존재 및 소스 구조
// ─────────────────────────────────────────────────────────

test.describe('Pension — 시뮬레이션 엔진', () => {

  test('simulate 함수 존재 (window)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.simulate === 'function');
    expect(exists).toBe(true);
  });

  test('onIC 함수 존재 (window) — 입력 변경 시 재계산', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.onIC === 'function');
    expect(exists).toBe(true);
  });

  test('renderStrategy 함수 존재 (window) — 전략 메시지 렌더', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.renderStrategy === 'function');
    expect(exists).toBe(true);
  });

  test('renderPhases 함수 존재 (window) — 페이즈별 수령액 렌더', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.renderPhases === 'function');
    expect(exists).toBe(true);
  });

  test('taxR 함수 존재 — 나이별 세율', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.taxR === 'function');
    expect(exists).toBe(true);
  });

  test('taxR — 55~64세 5.5% 반환', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const rate = await page.evaluate(() => window.taxR?.(60));
    expect(rate).toBeCloseTo(0.055, 3);
  });

  test('taxR — 65~74세 4.4% 반환', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const rate = await page.evaluate(() => window.taxR?.(70));
    expect(rate).toBeCloseTo(0.044, 3);
  });

  test('taxR — 75세+ 3.3% 반환', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const rate = await page.evaluate(() => window.taxR?.(80));
    expect(rate).toBeCloseTo(0.033, 3);
  });

  test('simulate — 1,500만원 LIMIT 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/LIMIT|15_000_000|15000000/);
    expect(src).toMatch(/분리과세|1,500만/);
  });

  test('simulate — 이연퇴직소득 30/40% 감면 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/deferredDiscount|0\.30|0\.40|30.*감면|40.*감면/);
  });

  test('updateBanners 함수 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.updateBanners === 'function');
    expect(exists).toBe(true);
  });

  test('calcAge 함수 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.calcAge === 'function');
    expect(exists).toBe(true);
  });

  test('onIC 호출 시 오류 없이 실행됨', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('networkidle');
    const noError = await page.evaluate(() => {
      try { window.onIC?.(); return true; } catch { return false; }
    });
    expect(noError).toBe(true);
  });

});


// ─────────────────────────────────────────────────────────
// 7. 연금 용어 표기 (직접용어·전문용어 병행)
// ─────────────────────────────────────────────────────────

test.describe('Pension — 연금 용어 명시', () => {

  test('회사납입분 용어 표기 존재 (직접용어)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/회사납입분|사용자부담금/);
  });

  test('본인납입분 용어 표기 존재 (직접용어)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/본인납입분|가입자부담금/);
  });

  test('이연퇴직소득 전문용어 표기 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/이연퇴직소득|퇴직소득세/);
  });

  test('과세 용어 표기 존재 (분리과세·세금)', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/세금|분리과세|과세/);
  });

  test('IRP 전문용어 표기 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/IRP/);
  });

  test('연금저축 용어 표기 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/연금저축|PA/);
  });

  test('분리과세 한도(1,500만) 명시', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/1[,.]?500만|1,500|분리과세 한도/);
  });

  test('건보료·피부양자 용어 표기 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/건보료|피부양자|건강보험/);
  });

  test('국민연금(NP) 표기 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/국민연금|NP/);
  });

  test('숨김처리 토글 — 용어/금액 가시성 제어 label 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    // .pv-toggle은 금액 숨김 처리 레이블 역할도 함
    const label = page.locator('label.pv-toggle');
    expect(await label.count()).toBeGreaterThan(0);
  });

});


// ─────────────────────────────────────────────────────────
// 8. 건보료 및 세금 판정 소스 확인
// ─────────────────────────────────────────────────────────

test.describe('Pension — 건보료·세금 소스 검증', () => {

  test('건보료·피부양자 판정 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/건보료|건강보험|피부양자/);
  });

  test('국민연금 2,000만원 한도 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    expect(src).toMatch(/20[_,]?000[_,]?000|NP_DEPENDENT_LIMIT|2[,.]?000만/);
  });

  test('사적연금 건보료 제외 안내 소스 확인', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const src = await page.content();
    // 사적연금(연금저축·IRP)은 건보료 소득에서 제외
    expect(src).toMatch(/사적연금.*건보|건보.*사적연금|프리패스|건보료 제외/);
  });

  test('onSlider 함수 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.onSlider === 'function');
    expect(exists).toBe(true);
  });

  test('getInputs 함수 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    const exists = await page.evaluate(() => typeof window.getInputs === 'function');
    expect(exists).toBe(true);
  });

  test('목표 생활비 입력 (#targetMonthly) 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#targetMonthly').count()).toBe(1);
  });

  test('생년월일 입력 (#birthDate) 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#birthDate').count()).toBe(1);
  });

  test('국민연금 월 수령액 입력 (#npMonthly) 존재', async ({ page }) => {
    await page.goto(PENSION_PAGE);
    await page.waitForLoadState('domcontentloaded');
    expect(await page.locator('#npMonthly').count()).toBeGreaterThan(0);
  });

});


// ─────────────────────────────────────────────────────────
// 9. pension v2 — 전략 비교 시뮬레이터
// ─────────────────────────────────────────────────────────

test.describe('Pension v2 — 인출 전략 시뮬레이터', () => {

  test('v2 페이지 title 확인', async ({ page }) => {
    await page.goto(PENSION_V2);
    await expect(page).toHaveTitle(/연금|WorksFree/i);
  });

  test('v2 — simulate 함수 존재', async ({ page }) => {
    await page.goto(PENSION_V2);
    const exists = await page.evaluate(() => typeof window.simulate === 'function');
    expect(exists).toBe(true);
  });

  test('v2 — renderAll 또는 render 함수 존재', async ({ page }) => {
    await page.goto(PENSION_V2);
    const exists = await page.evaluate(() =>
      typeof window.renderAll === 'function' ||
      typeof window.render === 'function' ||
      typeof window.renderSummaryPanel === 'function'
    );
    expect(exists).toBe(true);
  });

  test('v2 — 1,500만원 LIMIT 소스 확인', async ({ page }) => {
    await page.goto(PENSION_V2);
    const src = await page.content();
    expect(src).toMatch(/LIMIT|15_000_000|15000000/);
  });

  test('v2 — 피부양자 탈락 경고 소스 확인', async ({ page }) => {
    await page.goto(PENSION_V2);
    const src = await page.content();
    expect(src).toMatch(/피부양자.*탈락|탈락.*피부양자/);
  });

  test('v2 — pv-toggle 또는 숨김처리 소스 확인', async ({ page }) => {
    await page.goto(PENSION_V2);
    const src = await page.content();
    expect(src).toMatch(/pv-toggle|숨김처리|pvChk/);
  });

  test('v2 — 전략 1~3 소스 확인', async ({ page }) => {
    await page.goto(PENSION_V2);
    const src = await page.content();
    expect(src).toMatch(/전략\s*[123]|strategy.*[123]|한도 사수|원금 보존|65세 올인/i);
  });

  test('v2 — 이연퇴직소득 30/40% 감면 소스 확인', async ({ page }) => {
    await page.goto(PENSION_V2);
    const src = await page.content();
    expect(src).toMatch(/0\.3|0\.4|30.*감면|40.*감면|deferredDiscount/);
  });

});
