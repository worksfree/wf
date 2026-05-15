/**
 * Real-DB 테스트 globalTeardown
 * - 테스트 전체 종료 후 1회 호출
 * - 테스트 계정 삭제 (credits/payments는 CASCADE로 자동 삭제)
 */

require('dotenv').config({ path: '.env.test' });
const { createClient } = require('@supabase/supabase-js');

const admin = createClient(
  process.env.TEST_SUPABASE_URL,
  process.env.TEST_SUPABASE_SERVICE_KEY,
  { auth: { autoRefreshToken: false, persistSession: false } }
);

module.exports = async function globalTeardown() {
  const emails = [
    'test-paid@worksfree-test.local',
    'test-admin@worksfree-test.local',
    'test-free@worksfree-test.local',
  ];

  console.log('\n[teardown] 테스트 계정 삭제 중…');

  const { data: list } = await admin.auth.admin.listUsers();
  const targets = (list?.users || []).filter(u => emails.includes(u.email));

  await Promise.all(targets.map(u => admin.auth.admin.deleteUser(u.id)));

  console.log(`[teardown] ${targets.length}개 계정 삭제 완료`);
};
