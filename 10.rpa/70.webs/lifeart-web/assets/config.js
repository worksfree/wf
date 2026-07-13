// LifeArt — Supabase 클라이언트 설정
// 기존 WorksFree Supabase 프로젝트를 재사용, tenant_id='lifeart'로 데이터 격리 (비용 절감)
const SUPABASE_URL  = 'https://rkycwfpkzorfpcxfvaqt.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJreWN3ZnBrem9yZnBjeGZ2YXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgzMDk4OTQsImV4cCI6MjA5Mzg4NTg5NH0.u1HC0KiArbdqFAPpkRWsfZmMYqfZ-euRTHeNtUr2NBs';
const TENANT_ID = 'lifeart';

// test-lifeart / pre-test-lifeart / production 환경 격리 (auction과 동일한 env 컬럼 패턴)
function getEnv() {
  const h = location.hostname;
  if (h.startsWith('test-lifeart.'))     return 'test';
  if (h.startsWith('pre-test-lifeart.')) return 'pre-test';
  if (h === 'localhost' || h === '127.0.0.1') return 'dev';
  return 'production';
}

const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON);
