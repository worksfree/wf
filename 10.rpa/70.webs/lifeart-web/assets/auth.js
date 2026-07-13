// LifeArt 회원 인증 공통 로직 (Supabase Auth, 이메일/비밀번호)

// 로그인/가입 성공 직후 profiles 행이 없으면 생성 (전역 트리거 대신 클라이언트에서 처리 — schema.sql 주석 참고)
async function ensureProfile(user, extra = {}) {
  const { data: existing } = await sb.from('profiles').select('id').eq('id', user.id).maybeSingle();
  if (existing) return;
  await sb.from('profiles').insert({
    id: user.id,
    tenant_id: TENANT_ID,
    name: extra.name || user.user_metadata?.name || null,
    phone: extra.phone || user.user_metadata?.phone || null,
  });
}

async function lifeartSignUp(name, phone, email, password, msgEl) {
  msgEl.textContent = '가입 처리 중...'; msgEl.className = 'form-msg';
  const { data, error } = await sb.auth.signUp({
    email, password,
    options: { data: { name, phone } },
  });
  if (error) {
    msgEl.textContent = error.message.includes('already registered')
      ? '이미 가입된 이메일입니다.' : '가입에 실패했습니다: ' + error.message;
    msgEl.className = 'form-msg error';
    return;
  }
  if (data.user) await ensureProfile(data.user, { name, phone });
  if (data.session) {
    location.href = '/mypage/';
  } else {
    msgEl.textContent = '가입 완료! 이메일 인증 후 로그인해주세요.';
    msgEl.className = 'form-msg success';
  }
}

async function lifeartLogin(email, password, msgEl) {
  msgEl.textContent = '로그인 중...'; msgEl.className = 'form-msg';
  const { data, error } = await sb.auth.signInWithPassword({ email, password });
  if (error) {
    msgEl.textContent = '이메일 또는 비밀번호가 올바르지 않습니다.';
    msgEl.className = 'form-msg error';
    return;
  }
  if (data.user) await ensureProfile(data.user);
  location.href = '/mypage/';
}

async function lifeartLogout() {
  await sb.auth.signOut();
  location.href = '/';
}

// 헤더 로그인 버튼 상태 갱신 (레이아웃 주입 완료 후 실행)
document.addEventListener('layout:ready', async () => {
  const { data: { session } } = await sb.auth.getSession();
  const btn = document.getElementById('nav-login-btn');
  if (!btn) return;
  if (session) {
    btn.textContent = '마이페이지';
    btn.href = '/mypage/';
  }
});
