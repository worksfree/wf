/**
 * DART 대량 조회 (Bulk CSV) — mock 테스트
 *
 * dart-api-worker.worksfree.workers.dev 를 인터셉트하여
 * 인터넷 없이 벌크 조회 흐름 전체를 검증한다.
 *
 * 실행: npx playwright test tests/dart-bulk.spec.js
 */

const { test, expect } = require('@playwright/test');
const path             = require('path');

const DART_WORKER = 'dart-api-worker.worksfree.workers.dev';
const DART_PAGE   = '/consulting/dart/index.html';

// ── 4개 종목코드만 "알려진" 기업으로 처리 ───────────────────────────────
const MOCK_CORPS = {
  '005930': { corp_name: '삼성전자',   corp_code: '00126380', corp_cls: 'Y', ceo_nm: '한종희', induty_code: 'C26', stock_code: '005930', adres: '경기도 수원시' },
  '000660': { corp_name: 'SK하이닉스', corp_code: '00234990', corp_cls: 'Y', ceo_nm: '곽노정', induty_code: 'C26', stock_code: '000660', adres: '경기도 이천시' },
  '035420': { corp_name: 'NAVER',      corp_code: '00264549', corp_cls: 'Y', ceo_nm: '최수연', induty_code: 'J63', stock_code: '035420', adres: '경기도 성남시' },
  '035720': { corp_name: '카카오',     corp_code: '00266961', corp_cls: 'Y', ceo_nm: '정신아', induty_code: 'J63', stock_code: '035720', adres: '제주 제주시' },
};

/**
 * DART Worker URL 전체를 인터셉트.
 * ep=corp_info.json → 종목코드/회사명으로 목업 반환
 * ep=company.json   → 단건 검색 결과 목업
 */
async function mockDartWorker(page) {
  await page.route(`**/${DART_WORKER}**`, route => {
    const url      = new URL(route.request().url());
    const ep       = url.searchParams.get('ep');
    const stock    = url.searchParams.get('stock_code');
    const corpName = url.searchParams.get('corp_name');

    if (ep === 'corp_info.json') {
      const hit = stock
        ? MOCK_CORPS[stock]
        : Object.values(MOCK_CORPS).find(c => corpName && c.corp_name.includes(corpName));

      if (hit) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: '000', ...hit }),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: '013', message: '조회된 데이터가 없습니다.' }),
        });
      }
      return;
    }

    if (ep === 'company.json') {
      const list = corpName
        ? Object.values(MOCK_CORPS).filter(c => c.corp_name.includes(corpName))
        : [];
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: '000', total_count: String(list.length), list }),
      });
      return;
    }

    route.fulfill({ status: 404, body: 'not found' });
  });
}

/** 처리 완료 대기 — .btn-dl-csv 버튼이 나타나면 done=true */
async function waitForBulkDone(page, timeout = 15000) {
  await expect(page.locator('.btn-dl-csv')).toBeVisible({ timeout });
}

// ════════════════════════════════════════════════════════════════
test.describe('DART 대량 조회 (Bulk CSV)', () => {

  // ── 1. 탭 전환 ─────────────────────────────────────────────
  test('벌크 탭 전환 — mode-bulk 표시', async ({ page }) => {
    await page.goto(DART_PAGE);
    await expect(page.locator('#mode-bulk')).toBeHidden();

    await page.click('#tab-bulk');

    await expect(page.locator('#mode-bulk')).toBeVisible();
    await expect(page.locator('#mode-single')).toBeHidden();
  });

  // ── 2. 텍스트 직접 입력 → 조회 → ok/err ────────────────────
  test('텍스트 입력 → 대량 조회 → ok 2건 + err 1건', async ({ page }) => {
    await mockDartWorker(page);
    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    // 알려진 코드 2개 + 없는 코드 1개
    await page.fill('#bulk-textarea', '005930\n000660\n999999');
    await expect(page.locator('#bulk-count')).toContainText('3건');

    await page.click('#btn-start');
    await waitForBulkDone(page);

    await expect(page.locator('#bulk-results .bs-ok')).toHaveCount(2);
    await expect(page.locator('#bulk-results .bs-err')).toHaveCount(1);
  });

  // ── 3. CSV 파일 업로드 → 조회 ──────────────────────────────
  test('dart_valid_test.csv 업로드 → 4 ok + 4 err', async ({ page }) => {
    await mockDartWorker(page);
    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    const fixture = path.join(__dirname, 'fixtures', 'dart_valid_test.csv');
    await page.setInputFiles('#csv-file', fixture);

    // FileReader 비동기 완료 후 카운터 갱신 대기
    await expect(page.locator('#bulk-count')).toContainText('8건', { timeout: 3000 });

    await page.click('#btn-start');
    await waitForBulkDone(page);

    // 005930, 000660, 035420, 035720 → ok (4개)
    // 005380, 066570, 068270, 006400 → 목업 없음 → err (4개)
    await expect(page.locator('#bulk-results .bs-ok')).toHaveCount(4);
    await expect(page.locator('#bulk-results .bs-err')).toHaveCount(4);
  });

  // ── 4. 에러 전용 CSV ────────────────────────────────────────
  test('dart_error_test.csv → 전체 6건 모두 err', async ({ page }) => {
    await mockDartWorker(page);
    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    const fixture = path.join(__dirname, 'fixtures', 'dart_error_test.csv');
    await page.setInputFiles('#csv-file', fixture);

    await expect(page.locator('#bulk-count')).toContainText('6건', { timeout: 3000 });

    await page.click('#btn-start');
    await waitForBulkDone(page);

    // 없는 종목코드·회사명 → 전부 err (miss 포함)
    const failed = page.locator('#bulk-results .bs-err, #bulk-results .bs-miss');
    await expect(failed).toHaveCount(6);
  });

  // ── 5. 행 수 카운터 ─────────────────────────────────────────
  test('textarea 입력 시 행 수 카운터 업데이트', async ({ page }) => {
    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    await page.fill('#bulk-textarea', '삼성전자\n카카오\nNAVER');
    await expect(page.locator('#bulk-count')).toContainText('3건');

    await page.fill('#bulk-textarea', '');
    await expect(page.locator('#bulk-count')).toHaveText('');
  });

  // ── 6. 템플릿 다운로드 ─────────────────────────────────────
  test('템플릿 다운로드 — dart_bulk_template.csv', async ({ page }) => {
    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#btn-tmpl'),
    ]);
    expect(download.suggestedFilename()).toBe('dart_bulk_template.csv');
  });

  // ── 7. 결과 CSV 다운로드 ────────────────────────────────────
  test('조회 완료 후 결과 CSV 다운로드', async ({ page }) => {
    await mockDartWorker(page);
    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    await page.fill('#bulk-textarea', '005930\n000660');
    await page.click('#btn-start');
    await waitForBulkDone(page);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('.btn-dl-csv'),
    ]);
    expect(download.suggestedFilename()).toMatch(/^dart_bulk_\d{4}-\d{2}-\d{2}\.csv$/);
  });

  // ── 8. 중지 버튼 ────────────────────────────────────────────
  test('처리 중 Stop 버튼 → 중지 후 Start 재활성화', async ({ page }) => {
    // 응답 지연(300ms)으로 처리 중 상태를 만든다
    await page.route(`**/${DART_WORKER}**`, async route => {
      await new Promise(r => setTimeout(r, 300));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: '000', corp_code: '00126380', corp_name: '삼성전자', corp_cls: 'Y' }),
      });
    });

    await page.goto(DART_PAGE);
    await page.click('#tab-bulk');

    // 15행 → CHUNK=5 기준 3회전, 총 4.5초 이상 → 첫 청크 완료 전에 중지 가능
    await page.fill('#bulk-textarea', Array(15).fill('005930').join('\n'));

    await page.click('#btn-start');
    await expect(page.locator('#btn-stop')).toBeVisible({ timeout: 3000 });

    await page.click('#btn-stop');
    await expect(page.locator('#btn-stop')).toBeHidden();
    await expect(page.locator('#btn-start')).toBeEnabled();
  });

});
