/**
 * Real-DB 크레딧 테스트
 * 실행: PLAYWRIGHT_PROJECT=realdb npx playwright test --project=realdb
 * 전제: .env.test 설정 + global-setup.js 에서 테스트 계정 생성됨
 *
 * 테스트 범위:
 * - credit_balance 뷰 잔액 조회
 * - RLS: 본인 내역만 조회
 * - 크레딧 충전 INSERT (purchase)
 * - RLS: 차감 직접 INSERT 차단
 * - deduct_credits() 함수 동작
 * - 잔액 부족 시 예외
 */

require('dotenv').config({ path: '.env.test' });
const { test, expect } = require('@playwright/test');
const { createClient } = require('@supabase/supabase-js');

const SB_URL  = process.env.TEST_SUPABASE_URL;
const SB_ANON = process.env.TEST_SUPABASE_ANON;
const SB_SVC  = process.env.TEST_SUPABASE_SERVICE_KEY;

// service_role 클라이언트 (테스트 보조용)
const adminClient = createClient(SB_URL, SB_SVC, {
  auth: { autoRefreshToken: false, persistSession: false },
});

// 테스트 계정으로 anon 클라이언트 로그인 헬퍼
async function loginClient(email, password) {
  const client = createClient(SB_URL, SB_ANON);
  const { error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw new Error(`로그인 실패(${email}): ${error.message}`);
  return client;
}

test.describe('credit_balance 뷰', () => {

  test('유료 사용자 초기 잔액이 500이다', async () => {
    const client = await loginClient(
      process.env.TEST_USER_EMAIL,
      process.env.TEST_USER_PASSWORD
    );
    const { data, error } = await client
      .from('credit_balance')
      .select('balance')
      .eq('user_id', process.env.TEST_USER_ID)
      .maybeSingle();
    expect(error).toBeNull();
    expect(data?.balance).toBe(500);
  });

  test('무료 사용자 잔액이 0이다', async () => {
    const client = await loginClient(
      process.env.TEST_FREE_EMAIL,
      process.env.TEST_USER_PASSWORD
    );
    const { data } = await client
      .from('credit_balance')
      .select('balance')
      .eq('user_id', process.env.TEST_FREE_ID)
      .maybeSingle();
    // 잔액 0이면 뷰에 행이 없음 → null
    expect(data?.balance ?? 0).toBe(0);
  });

  test('다른 사용자 잔액은 RLS로 조회 불가', async () => {
    const client = await loginClient(
      process.env.TEST_USER_EMAIL,
      process.env.TEST_USER_PASSWORD
    );
    const { data } = await client
      .from('credit_balance')
      .select('balance')
      .eq('user_id', process.env.TEST_ADMIN_ID)
      .maybeSingle();
    // RLS에 의해 행이 없어야 함
    expect(data).toBeNull();
  });

});

test.describe('credits 테이블 RLS', () => {

  test('purchase 사유로 양수 delta INSERT가 허용된다', async () => {
    const client = await loginClient(
      process.env.TEST_USER_EMAIL,
      process.env.TEST_USER_PASSWORD
    );
    const { error } = await client.from('credits').insert({
      user_id:      process.env.TEST_USER_ID,
      delta:        50,
      reason:       'purchase',
      ref_order_id: 'test_order_' + Date.now(),
    });
    expect(error).toBeNull();

    // 잔액이 550이 되어야 함
    const { data } = await client
      .from('credit_balance').select('balance')
      .eq('user_id', process.env.TEST_USER_ID).maybeSingle();
    expect(data?.balance).toBe(550);

    // 테스트 후 정리 (service_role로 삭제)
    await adminClient.from('credits')
      .delete()
      .eq('user_id', process.env.TEST_USER_ID)
      .eq('ref_order_id', 'test_order_' + Date.now());
  });

  test('use_app 사유로 음수 delta INSERT가 차단된다 (RLS)', async () => {
    const client = await loginClient(
      process.env.TEST_USER_EMAIL,
      process.env.TEST_USER_PASSWORD
    );
    const { error } = await client.from('credits').insert({
      user_id: process.env.TEST_USER_ID,
      delta:   -100,
      reason:  'use_app',
      app_id:  'bom_exporter',
    });
    // RLS WITH CHECK 위반 → 오류 발생해야 함
    expect(error).not.toBeNull();
  });

  test('타인 user_id로 INSERT가 차단된다 (RLS)', async () => {
    const client = await loginClient(
      process.env.TEST_USER_EMAIL,
      process.env.TEST_USER_PASSWORD
    );
    const { error } = await client.from('credits').insert({
      user_id: process.env.TEST_ADMIN_ID,  // 다른 사람 ID
      delta:   100,
      reason:  'purchase',
    });
    expect(error).not.toBeNull();
  });

});

test.describe('deduct_credits() 함수', () => {

  test('service_role로 크레딧 차감 후 잔액이 줄어든다', async () => {
    const before = await adminClient.rpc('get_user_credit_balance', {
      p_user_id: process.env.TEST_USER_ID,
    });
    const balanceBefore = before.data;

    await adminClient.rpc('deduct_credits', {
      p_user_id: process.env.TEST_USER_ID,
      p_amount:  100,
      p_app_id:  'bom_exporter',
      p_note:    '테스트 차감',
    });

    const after = await adminClient.rpc('get_user_credit_balance', {
      p_user_id: process.env.TEST_USER_ID,
    });
    expect(after.data).toBe(balanceBefore - 100);
  });

  test('잔액 부족 시 deduct_credits()가 예외를 던진다', async () => {
    const { error } = await adminClient.rpc('deduct_credits', {
      p_user_id: process.env.TEST_FREE_ID,
      p_amount:  100,   // 잔액 0
      p_app_id:  'bom_exporter',
    });
    expect(error).not.toBeNull();
    expect(error.message).toMatch(/insufficient_credits/);
  });

});
