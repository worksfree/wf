/**
 * Real-DB 테스트 globalSetup
 * - 테스트 실행 전 1회 호출
 * - Supabase Admin API로 테스트 계정 생성 + 크레딧 시딩
 * - 생성된 UUID를 process.env에 저장 → 각 테스트에서 참조 가능
 *
 * 실행 전 필수: .env.test 파일에 TEST_SUPABASE_* 환경변수 설정
 */

require('dotenv').config({ path: '.env.test' });
const { createClient } = require('@supabase/supabase-js');

const {
  TEST_SUPABASE_URL,
  TEST_SUPABASE_SERVICE_KEY,
  TEST_USER_PASSWORD  = 'TestPassword123!',
  TEST_ADMIN_PASSWORD = 'AdminPassword123!',
} = process.env;

// service_role 클라이언트 — RLS 우회, 관리자 작업용
const admin = createClient(TEST_SUPABASE_URL, TEST_SUPABASE_SERVICE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
});

async function createTestUser(email, password, role, initialCredits, creditNote) {
  // 기존 사용자가 있으면 재사용 (이전 테스트 실패로 잔류한 경우)
  const { data: list } = await admin.auth.admin.listUsers();
  const existing = list?.users?.find(u => u.email === email);
  if (existing) {
    await admin.auth.admin.deleteUser(existing.id);
  }

  const { data, error } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,   // 이메일 인증 건너뜀
  });
  if (error) throw new Error(`createUser(${email}): ${error.message}`);

  const userId = data.user.id;

  // profiles 행 생성 + 역할 + 동의 완료 처리
  await admin.from('profiles').upsert({
    id:               userId,
    role,
    agreed_at:        new Date().toISOString(),
    marketing_agreed: false,
  });

  // 크레딧 시딩 (헬퍼 함수 호출)
  if (initialCredits > 0) {
    await admin.rpc('admin_grant_credits', {
      p_user_id: userId,
      p_amount:  initialCredits,
      p_note:    creditNote,
    });
  }

  return userId;
}

module.exports = async function globalSetup() {
  if (!TEST_SUPABASE_URL || !TEST_SUPABASE_SERVICE_KEY) {
    throw new Error(
      '.env.test 파일에 TEST_SUPABASE_URL, TEST_SUPABASE_SERVICE_KEY가 없습니다.\n' +
      '.env.test.example을 참고하여 .env.test를 생성하세요.'
    );
  }

  console.log('\n[setup] 테스트 계정 생성 중…');

  // role 값: general(기본) | gfc | ceo | staff | consultant
  const [userId, adminId, freeId] = await Promise.all([
    createTestUser(
      'test-paid@worksfree-test.local',
      TEST_USER_PASSWORD,
      'general', 500, '유료 테스트 계정 초기 지급'
    ),
    createTestUser(
      'test-admin@worksfree-test.local',
      TEST_ADMIN_PASSWORD,
      'gfc', 9999, '관리자 테스트 계정'
    ),
    createTestUser(
      'test-free@worksfree-test.local',
      TEST_USER_PASSWORD,
      'general', 0, ''
    ),
  ]);

  // 환경변수로 노출 — 테스트 파일에서 process.env.TEST_USER_ID 등으로 참조
  process.env.TEST_USER_ID  = userId;
  process.env.TEST_ADMIN_ID = adminId;
  process.env.TEST_FREE_ID  = freeId;
  process.env.TEST_USER_EMAIL  = 'test-paid@worksfree-test.local';
  process.env.TEST_ADMIN_EMAIL = 'test-admin@worksfree-test.local';
  process.env.TEST_FREE_EMAIL  = 'test-free@worksfree-test.local';

  console.log(`[setup] 완료 — paid:${userId.slice(0,8)} admin:${adminId.slice(0,8)} free:${freeId.slice(0,8)}`);
};
