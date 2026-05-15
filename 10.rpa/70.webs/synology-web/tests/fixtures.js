/**
 * 공통 픽스처 — 네트워크 모킹 + 로그인 헬퍼
 *
 * 외부 의존성(Supabase, Toss, Stripe)을 모두 인터셉트하여
 * 테스트가 인터넷 연결 없이도 안정적으로 동작하도록 합니다.
 */

const { test: base, expect } = require('@playwright/test');

// ── 모킹할 URL 패턴 ────────────────────────────────────────
const SUPABASE_HOST  = 'rkycwfpkzorfpcxfvaqt.supabase.co';
const TOSS_WORKER    = 'toss-verify.worksfree.workers.dev';
const STRIPE_WORKER  = 'stripe-session.worksfree.workers.dev';

// Supabase profiles 응답: dev 유저들은 이미 동의 완료 상태
const MOCK_PROFILES = {
  'dev-test-user-001': { id: 'dev-test-user-001', agreed_at: '2024-01-01T00:00:00Z', role: 'general' },
  'dev-test-user-gfc': { id: 'dev-test-user-gfc', agreed_at: '2024-01-01T00:00:00Z', role: 'gfc'     },
  // role 값: general(기본) | gfc | ceo | staff | consultant  ('member'/'admin' 없음)
};

/**
 * 모든 외부 API 요청 인터셉트.
 * 단일 핸들러로 작성 — Playwright는 마지막 등록 라우트가 우선 매칭되므로
 * 여러 패턴을 등록하면 순서 문제가 발생. 하나의 catch-all에서 URL 분기 처리.
 */
async function mockExternalAPIs(page) {
  // ── Supabase 전체 (인증 + REST) ──────────────────────────────
  await page.route(`**/${SUPABASE_HOST}/**`, route => {
    const url    = route.request().url();
    const method = route.request().method();

    // Auth 엔드포인트 — 세션 없음으로 응답 (초기 비로그인 상태)
    if (url.includes('/auth/')) {
      if (method === 'DELETE') {
        // signOut — 성공 응답
        route.fulfill({ status: 204, body: '' });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ user: null, session: null }),
        });
      }
      return;
    }

    // REST /credit_balance 뷰 — 잔액 500 목업
    if (url.includes('/rest/v1/credit_balance')) {
      const idMatch = url.match(/user_id=eq\.([^&]+)/);
      const userId  = idMatch ? decodeURIComponent(idMatch[1]) : null;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(userId ? [{ user_id: userId, balance: 500, total_charged: 500, total_used: 0 }] : []),
      });
      return;
    }

    // REST /profiles — dev 유저 동의 완료 상태 반환
    if (url.includes('/rest/v1/profiles')) {
      const idMatch = url.match(/id=eq\.([^&]+)/);
      const userId  = idMatch ? decodeURIComponent(idMatch[1]) : null;
      const profile = userId ? MOCK_PROFILES[userId] : null;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(profile ? [profile] : []),
      });
      return;
    }

    // REST 기타 테이블 (payments, credits 등) — 쓰기 성공, 읽기 빈 배열
    if (url.includes('/rest/')) {
      if (method === 'POST' || method === 'PATCH' || method === 'PUT') {
        route.fulfill({ status: 201, contentType: 'application/json', body: '{}' });
      } else {
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      }
      return;
    }

    // 그 외 Supabase 요청 (realtime 등) — 통과
    route.continue();
  });

  // ── Toss Payments 결제 검증 Worker ──────────────────────────
  await page.route(`**/${TOSS_WORKER}/**`, route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, payment: { totalAmount: 14000, status: 'DONE' } }),
    });
  });

  // ── Stripe 세션 Worker ───────────────────────────────────────
  await page.route(`**/${STRIPE_WORKER}/**`, route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        url:       'https://checkout.stripe.com/c/pay/test_session',
        sessionId: 'cs_test_mock',
        success:   true,
        amountUsd: 12.99,
      }),
    });
  });
}

/**
 * 페이지를 dev 모드로 로드하고 Supabase 초기화를 기다림
 */
async function gotoDevPage(page, query = '') {
  await mockExternalAPIs(page);
  await page.goto(`/?dev=1${query}`);
  // Dev toolbar가 show 상태가 될 때까지 대기
  await page.waitForSelector('#dev-toolbar.show', { timeout: 8000 });
}

/**
 * Dev 모드 — 일반 사용자 로그인
 * .user-pill까지 기다려야 드롭다운 테스트가 안정적으로 동작
 */
async function loginAsUser(page) {
  await gotoDevPage(page);
  await page.click('#dev-btn-user');
  // updateAuthUI()가 .user-pill을 렌더하면 로그인 완료
  await page.waitForSelector('.user-pill', { state: 'visible', timeout: 8000 });
}

/**
 * Dev 모드 — 관리자(GFC) 로그인
 * 비밀번호가 자동 입력되어 있으므로 확인 버튼만 클릭
 */
async function loginAsAdmin(page) {
  await gotoDevPage(page);
  await page.click('#dev-btn-admin');
  await page.waitForSelector('#dev-pw-modal', { state: 'visible', timeout: 3000 });
  await page.click('#dev-pw-modal button:text("확인")');
  await page.waitForSelector('.user-pill', { state: 'visible', timeout: 8000 });
}

// ── 커스텀 픽스처 export ────────────────────────────────────
const test = base.extend({
  // 각 테스트에서 helpers에 바로 접근 가능
  helpers: async ({ page }, use) => {
    await use({
      mockExternalAPIs: () => mockExternalAPIs(page),
      gotoDevPage:      (q)  => gotoDevPage(page, q),
      loginAsUser:      ()   => loginAsUser(page),
      loginAsAdmin:     ()   => loginAsAdmin(page),
    });
  },
});

module.exports = { test, expect, mockExternalAPIs, gotoDevPage, loginAsUser, loginAsAdmin };
