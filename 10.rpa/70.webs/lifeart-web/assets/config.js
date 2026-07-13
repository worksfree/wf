// LifeArt — Supabase 클라이언트 설정
// 기존 WorksFree Supabase 프로젝트를 재사용, tenant_id='lifeart'로 데이터 격리 (비용 절감)
const SUPABASE_URL  = 'https://rkycwfpkzorfpcxfvaqt.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJreWN3ZnBrem9yZnBjeGZ2YXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgzMDk4OTQsImV4cCI6MjA5Mzg4NTg5NH0.u1HC0KiArbdqFAPpkRWsfZmMYqfZ-euRTHeNtUr2NBs';

// LifeArt 테넌트 UUID — 공유 tenants 테이블의 lifeart.ai.kr 행 id.
// ★ 마이그레이션 03_tenants_hardening.sql 실행 후 나오는 실제 UUID로 교체 필요.
//   교체 전까지는 orders/inquiries insert 가 FK 위반으로 실패함(의도된 안전장치).
const TENANT_UUID = '81b84745-a87b-4a7e-8516-474d4bb5e1d5';
const TENANT_ID = 'lifeart';  // 사람이 읽는 라벨 (컬럼 값으로는 TENANT_UUID 사용)

// test-lifeart / pre-test-lifeart / production 환경 격리 (auction과 동일한 env 컬럼 패턴)
function getEnv() {
  const h = location.hostname;
  if (h.startsWith('test-lifeart.'))     return 'test';
  if (h.startsWith('pre-test-lifeart.')) return 'pre-test';
  if (h === 'localhost' || h === '127.0.0.1') return 'dev';
  return 'production';
}

const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON);

// 토스페이먼츠 — 현재는 토스 공용 테스트 키(누구나 즉시 테스트 가능한 샌드박스 키)
// 실 운영 전환 시 LifeArt 명의로 발급받은 라이브 키로 반드시 교체할 것.
const TOSS_CLIENT_KEY = 'test_ck_D5GePWvyJnrK0W0k6q45Qzldwmy1';
const TOSS_VERIFY_URL = 'https://lifeart-toss-verify.worksfree.workers.dev';
