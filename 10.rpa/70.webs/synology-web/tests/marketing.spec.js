/**
 * marketing.spec.js — 마케팅 자료 & 이메일 발송 테스트
 *
 * 실행: npx playwright test tests/marketing.spec.js
 * 대상: consulting/marketing/index.html
 */

const { test, expect } = require('./fixtures');
const path = require('path');
const fs   = require('fs');

const MAIL_WORKER  = 'send-mail.worksfree.workers.dev';
const BIZDB_WORKER = 'biz-db.worksfree.workers.dev';

// ── 공통 모킹 ────────────────────────────────────────────────────────
async function mockMailApis(page, opts = {}) {
  const {
    sent      = 5,
    limit     = 3000,
    remaining = 2995,
    period    = '2026-06',
    sendOk    = true,
    filtered  = [],
  } = opts;

  // GET / — 발송 현황
  await page.route(`https://${MAIL_WORKER}`, route => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ sent, limit, remaining, period }),
      });
    } else if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() || {};
      const count = (body.emails || []).length;
      route.fulfill({
        status: sendOk ? 200 : 400,
        contentType: 'application/json',
        body: JSON.stringify(sendOk
          ? { success: true, sent: count - filtered.length, filtered, totalSent: sent + count, remaining: remaining - count }
          : { error: '월 발송 한도 초과' }),
      });
    } else {
      route.continue();
    }
  });

  // BizDB — /sent-emails
  await page.route(`**/${BIZDB_WORKER}/sent-emails**`, route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ emails: [], count: 0 }),
    })
  );
}

// CSV 픽스처 생성 헬퍼
function makeCsvBlob(rows) {
  const bom = '﻿';
  const header = '기업명,이메일\n';
  const body   = rows.map(r => `"${r.name}","${r.email}"`).join('\n');
  return Buffer.from(bom + header + body, 'utf8');
}

// ════════════════════════════════════════════════════════════════════
// TEST SUITE 1: 페이지 로드
// ════════════════════════════════════════════════════════════════════
test.describe('Marketing: 페이지 로드', () => {

  test('헤더 타이틀이 표시된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await expect(page.locator('header .hdr-title')).toContainText('마케팅 자료');
  });

  test('전단지 그리드가 렌더된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    // 역할 없으면 로딩 상태 또는 섹션 중 하나가 표시됨
    await expect(page.locator('#section-loading, #section-ins, #section-mgmt')).toHaveCount(3);
  });

  test('탭 전환 — 단건/대량 발송', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await page.locator('.mail-tab[data-tab="bulk"]').click();
    await expect(page.locator('#panel-bulk')).toBeVisible();
    await expect(page.locator('#panel-single')).toBeHidden();
  });

});

// ════════════════════════════════════════════════════════════════════
// TEST SUITE 2: 발송 현황 (Quota)
// ════════════════════════════════════════════════════════════════════
test.describe('Marketing: 발송 현황', () => {

  test('발송 현황이 올바른 형식으로 표시된다', async ({ page }) => {
    await mockMailApis(page, { sent: 9, remaining: 2991, period: '2026-06' });
    await page.goto('/consulting/marketing/index.html');
    await page.waitForTimeout(500);
    const text = await page.locator('#quota-text').textContent();
    expect(text).toMatch(/2026-06.*9.*발송.*2,991.*남음/);
  });

  test('Worker 오프라인 시 안내 메시지가 표시된다', async ({ page }) => {
    await page.route(`https://${MAIL_WORKER}`, route => route.abort());
    await page.route(`**/${BIZDB_WORKER}/**`, route => route.abort());
    await page.goto('/consulting/marketing/index.html');
    await page.waitForTimeout(1000);
    const text = await page.locator('#quota-text').textContent();
    expect(text).toMatch(/미배포|연결 오류|오류/);
  });

  test('새로고침 버튼이 quota를 다시 로드한다', async ({ page }) => {
    let callCount = 0;
    await page.route(`https://${MAIL_WORKER}`, route => {
      if (route.request().method() === 'GET') {
        callCount++;
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sent: callCount, limit: 3000, remaining: 3000 - callCount, period: '2026-06' }) });
      } else route.continue();
    });
    await page.route(`**/${BIZDB_WORKER}/**`, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ emails: [], count: 0 }) }));
    await page.goto('/consulting/marketing/index.html');
    const prevCount = callCount;
    await page.locator('.mail-quota-refresh').click();
    await page.waitForTimeout(500);
    expect(callCount).toBeGreaterThan(prevCount);
  });

});

// ════════════════════════════════════════════════════════════════════
// TEST SUITE 3: 단건 발송
// ════════════════════════════════════════════════════════════════════
test.describe('Marketing: 단건 발송', () => {

  test('이메일 주소 없이 발송 시 에러가 표시된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await page.locator('#mail-subject').fill('테스트 제목');
    await page.locator('#panel-single .mail-send-btn').click();
    await expect(page.locator('#mail-status')).toContainText('이메일 주소');
  });

  test('이메일 주소 없이 발송 시 버튼이 다시 활성화된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await page.locator('#panel-single .mail-send-btn').click();
    await expect(page.locator('#panel-single .mail-send-btn')).toBeEnabled();
  });

  test('유효한 입력으로 발송 완료 메시지가 표시된다', async ({ page }) => {
    await mockMailApis(page, { sent: 1, remaining: 2999 });
    await page.goto('/consulting/marketing/index.html');
    await page.locator('#mail-subject').fill('테스트 제목');
    await page.locator('#mail-to').fill('test@company.co.kr');
    await page.locator('#panel-single .mail-send-btn').click();
    await expect(page.locator('#mail-status')).toContainText('완료', { timeout: 5000 });
  });

  test('발송 중 버튼이 비활성화된다', async ({ page }) => {
    // 응답 지연 시뮬레이션
    await page.route(`https://${MAIL_WORKER}`, async route => {
      if (route.request().method() === 'POST') {
        await new Promise(r => setTimeout(r, 500));
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, sent: 1, filtered: [], totalSent: 1, remaining: 2999 }) });
      } else route.continue();
    });
    await page.route(`**/${BIZDB_WORKER}/**`, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ emails: [], count: 0 }) }));
    await page.goto('/consulting/marketing/index.html');
    await page.locator('#mail-subject').fill('테스트');
    await page.locator('#mail-to').fill('test@company.co.kr');
    await page.locator('#panel-single .mail-send-btn').click();
    // 발송 중에는 disabled
    await expect(page.locator('#panel-single .mail-send-btn')).toBeDisabled();
    // 완료 후 다시 활성화
    await expect(page.locator('#panel-single .mail-send-btn')).toBeEnabled({ timeout: 3000 });
  });

});

// ════════════════════════════════════════════════════════════════════
// TEST SUITE 4: 대량 발송 CSV
// ════════════════════════════════════════════════════════════════════
test.describe('Marketing: 대량 발송 CSV', () => {

  test('CSV 업로드 시 미리보기가 표시된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await page.locator('.mail-tab[data-tab="bulk"]').click();

    // 파일 업로드
    const csv = makeCsvBlob([
      { name: '삼성전자', email: 'ir@samsung.com' },
      { name: 'LG전자',  email: 'contact@lg.com' },
    ]);
    const [fileChooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('#mail-csv').click(),
    ]);
    await fileChooser.setFiles({ name: 'test.csv', mimeType: 'text/csv', buffer: csv });

    await expect(page.locator('#csv-preview')).toContainText('2건 로드됨');
    await expect(page.locator('#bulk-send-btn')).toBeEnabled();
  });

  test('CSV 2건 발송 시 관리자 사본 포함 3건이 전송된다', async ({ page }) => {
    let sentPayload = null;
    await page.route(`https://${MAIL_WORKER}`, async route => {
      if (route.request().method() === 'POST') {
        sentPayload = route.request().postDataJSON();
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, sent: (sentPayload?.emails?.length || 0), filtered: [], totalSent: 3, remaining: 2997 }) });
      } else {
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sent: 0, limit: 3000, remaining: 3000, period: '2026-06' }) });
      }
    });
    await page.route(`**/${BIZDB_WORKER}/**`, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ emails: [], count: 0 }) }));
    await page.goto('/consulting/marketing/index.html');

    await page.locator('.mail-tab[data-tab="bulk"]').click();
    await page.locator('#mail-subject').fill('테스트 대량발송');

    const csv = makeCsvBlob([
      { name: '삼성전자', email: 'ir@samsung.com' },
      { name: 'LG전자',  email: 'contact@lg.com' },
    ]);
    const [fc] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('#mail-csv').click(),
    ]);
    await fc.setFiles({ name: 'bulk.csv', mimeType: 'text/csv', buffer: csv });
    await page.locator('#bulk-send-btn').click();

    await expect(page.locator('#mail-status')).toContainText('완료', { timeout: 5000 });
    // 관리자 사본 포함 3건 (owner + 2 recipients)
    expect(sentPayload?.emails?.length).toBe(3);
  });

  test('관리자 사본의 제목에 건수가 포함된다', async ({ page }) => {
    let firstEmailSubject = '';
    await page.route(`https://${MAIL_WORKER}`, async route => {
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON();
        firstEmailSubject = body?.emails?.[0]?.subject || '';
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, sent: 3, filtered: [], totalSent: 3, remaining: 2997 }) });
      } else {
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sent: 0, limit: 3000, remaining: 3000, period: '2026-06' }) });
      }
    });
    await page.route(`**/${BIZDB_WORKER}/**`, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ emails: [], count: 0 }) }));
    await page.goto('/consulting/marketing/index.html');

    await page.locator('.mail-tab[data-tab="bulk"]').click();
    await page.locator('#mail-subject').fill('법인세 절세 전략');

    const csv = makeCsvBlob([{ name: '테스트', email: 'test@corp.co.kr' }]);
    const [fc] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('#mail-csv').click(),
    ]);
    await fc.setFiles({ name: 'test.csv', mimeType: 'text/csv', buffer: csv });
    await page.locator('#bulk-send-btn').click();
    await page.waitForTimeout(500);

    // 첫 번째 이메일(owner 사본)은 "[발송 확인 N건]" 포함
    expect(firstEmailSubject).toMatch(/발송 확인.*건/);
    expect(firstEmailSubject).toContain('법인세 절세 전략');
  });

  test('3001건 CSV 업로드 시 에러가 표시된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await page.locator('.mail-tab[data-tab="bulk"]').click();

    // 3001행 생성
    const rows = Array.from({ length: 3001 }, (_, i) => ({ name: `회사${i}`, email: `corp${i}@test.com` }));
    const csv  = makeCsvBlob(rows);
    const [fc] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('#mail-csv').click(),
    ]);
    await fc.setFiles({ name: 'big.csv', mimeType: 'text/csv', buffer: csv });
    await page.locator('#bulk-send-btn').click();
    await expect(page.locator('#mail-status')).toContainText('한도');
  });

  test('수신거부 필터링 결과가 표시된다', async ({ page }) => {
    await mockMailApis(page, {
      sent: 1,
      filtered: [{ email: 'unsub@company.com', reason: '수신거부' }],
    });
    await page.goto('/consulting/marketing/index.html');
    await page.locator('.mail-tab[data-tab="bulk"]').click();
    await page.locator('#mail-subject').fill('테스트');

    const csv = makeCsvBlob([
      { name: '정상기업',   email: 'ok@company.com' },
      { name: '수신거부기업', email: 'unsub@company.com' },
    ]);
    const [fc] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('#mail-csv').click(),
    ]);
    await fc.setFiles({ name: 'test.csv', mimeType: 'text/csv', buffer: csv });
    await page.locator('#bulk-send-btn').click();
    await expect(page.locator('#filter-result')).toBeVisible({ timeout: 5000 });
  });

});

// ════════════════════════════════════════════════════════════════════
// TEST SUITE 5: 법적 필수 항목
// ════════════════════════════════════════════════════════════════════
test.describe('Marketing: 법적 필수 항목', () => {

  test('(광고) 접두어 체크박스가 항상 체크되고 비활성화 상태이다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    const checkbox = page.locator('#ad-prefix-check');
    await expect(checkbox).toBeChecked();
    await expect(checkbox).toBeDisabled();
  });

  test('발신자 이메일 필드가 기본값을 가진다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    const val = await page.locator('#ad-sender-email').inputValue();
    expect(val).toMatch(/@/);
  });

  test('수신거부 DB 자동 관리 안내 문구가 표시된다', async ({ page }) => {
    await mockMailApis(page);
    await page.goto('/consulting/marketing/index.html');
    await expect(page.locator('.legal-card')).toContainText('수신거부');
  });

});
