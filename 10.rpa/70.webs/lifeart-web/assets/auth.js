// LifeArt 회원 인증 공통 로직 (Supabase Auth, 이메일/비밀번호)

// 로그인/가입 성공 직후 공유 profiles 행을 LifeArt 테넌트로 보정.
//
// 허브 신규가입 트리거(handle_new_user)가 profiles 행을 tenant_id=worksfree DEFAULT 로
// 먼저 만든다. 그래서 tenant_id 만으로는 "허브 계정"과 "방금 만든 LifeArt 계정"을 구분할 수 없다.
// → LifeArt 가입 시 auth 메타데이터에 tenant:'lifeart' 를 심어(lifeartSignUp),
//   그 표식이 있는 계정만 LifeArt 로 클레임한다. 표식 없는 기존 허브 계정으로
//   LifeArt 에 로그인하면 조용히 덮어쓰지 않고 명확히 거부한다.
async function ensureProfile(user, extra = {}) {
  const isLifeArtAccount = user.user_metadata?.tenant === 'lifeart';
  const { data: existing } = await sb.from('profiles')
    .select('id, tenant_id').eq('id', user.id).maybeSingle();

  if (existing && existing.tenant_id === TENANT_UUID) return;  // 이미 LifeArt

  if (existing && !isLifeArtAccount) {
    // 표식 없는 기존 계정(허브 등)으로 LifeArt 로그인 시도 → 거부
    throw new Error('이 이메일은 다른 서비스(WorksFree) 계정으로 사용 중입니다. LifeArt는 다른 이메일로 가입해주세요.');
  }

  const payload = {
    tenant_id: TENANT_UUID,
    name: extra.name || user.user_metadata?.name || null,
    phone: extra.phone || user.user_metadata?.phone || null,
  };
  if (existing) {
    // 트리거가 만든 worksfree DEFAULT 행을 LifeArt 로 보정
    await sb.from('profiles').update(payload).eq('id', user.id);
  } else {
    await sb.from('profiles').insert({ id: user.id, ...payload });
  }
}

async function lifeartSignUp(name, phone, email, password, msgEl) {
  msgEl.textContent = '가입 처리 중...'; msgEl.className = 'form-msg';
  const { data, error } = await sb.auth.signUp({
    email, password,
    options: { data: { name, phone, tenant: 'lifeart' } },
  });
  if (error) {
    msgEl.textContent = error.message.includes('already registered')
      ? '이미 가입된 이메일입니다.' : '가입에 실패했습니다: ' + error.message;
    msgEl.className = 'form-msg error';
    return;
  }
  try {
    if (data.user) await ensureProfile(data.user, { name, phone });
  } catch (e) {
    msgEl.textContent = e.message; msgEl.className = 'form-msg error'; return;
  }
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
  try {
    if (data.user) await ensureProfile(data.user);
  } catch (e) {
    await sb.auth.signOut();
    msgEl.textContent = e.message; msgEl.className = 'form-msg error'; return;
  }
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
