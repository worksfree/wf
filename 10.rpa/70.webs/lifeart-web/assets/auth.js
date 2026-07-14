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

/* ════════════════════════════════════════════════════════════════
   소셜 로그인/가입 (Supabase OAuth — 구글·카카오)  · 웍스프리 허브와 동일 패턴
   ────────────────────────────────────────────────────────────────
   OAuth 는 이메일 가입과 달리 signUp 시점에 tenant 메타데이터를 심을 수 없다.
   → 리다이렉트 전 localStorage 표식을 남기고, 복귀 후 claimOAuthProfile 로
     "방금 생성된 계정(신규)"만 LifeArt 테넌트로 클레임한다.
     이미 존재하는 타 테넌트(허브) 계정으로 로그인하면 명확히 거부.
   공유 Supabase 라 구글/카카오 공급자는 프로젝트 전역 설정을 재사용하며,
   운영자가 lifeart 도메인 redirect URL 을 Auth 허용목록에 추가해야 동작한다. */
async function _oauth(provider) {
  if (!stageAtLeast(1)) { alert('소셜 로그인은 곧 오픈됩니다.'); return; }
  localStorage.setItem('lifeart_oauth', '1');
  const { error } = await sb.auth.signInWithOAuth({
    provider,
    options: { redirectTo: location.origin + '/mypage/' },
  });
  if (error) { localStorage.removeItem('lifeart_oauth'); alert('소셜 로그인 실패: ' + error.message); }
}
function signInWithGoogle() { return _oauth('google'); }
function signInWithKakao()  { return _oauth('kakao'); }

async function claimOAuthProfile(user) {
  // created_at 이 최근(3분 내)이면 이번 OAuth 로 갓 생성된 신규 계정으로 간주.
  const isNew = (Date.now() - new Date(user.created_at).getTime()) < 180000;
  const { data: existing } = await sb.from('profiles')
    .select('id, tenant_id').eq('id', user.id).maybeSingle();

  if (existing && existing.tenant_id === TENANT_UUID) return;  // 이미 LifeArt
  if (existing && existing.tenant_id && existing.tenant_id !== TENANT_UUID && !isNew) {
    throw new Error('이 소셜 계정은 다른 서비스(WorksFree) 계정으로 이미 사용 중입니다. LifeArt는 다른 계정으로 가입해주세요.');
  }
  // 신규(또는 트리거가 만든 기본행) → LifeArt 로 클레임 + 이후 식별용 메타데이터 표식
  await sb.auth.updateUser({ data: { tenant: 'lifeart' } });
  const nm = user.user_metadata?.name || user.user_metadata?.full_name || user.user_metadata?.nickname || null;
  const payload = { tenant_id: TENANT_UUID, name: nm };
  if (existing) await sb.from('profiles').update(payload).eq('id', user.id);
  else          await sb.from('profiles').insert({ id: user.id, ...payload });
}

// OAuth 리다이렉트 복귀 처리: 표식이 있으면 세션 확인 후 클레임 → 마이페이지.
(async function handleOAuthReturn() {
  if (localStorage.getItem('lifeart_oauth') !== '1') return;
  const { data: { session } } = await sb.auth.getSession();
  if (!session) return;  // 아직 세션 미확립(취소 등) — 표식 유지, 다음 로드에서 재시도
  localStorage.removeItem('lifeart_oauth');
  try {
    await claimOAuthProfile(session.user);
    if (!location.pathname.startsWith('/mypage')) location.href = '/mypage/';
  } catch (e) {
    await sb.auth.signOut();
    alert(e.message);
    location.href = '/auth/login/';
  }
})();

// 헤더 인증 UI 갱신 (레이아웃 주입 완료 후 실행)
//  비로그인 : 카탈로그 · 회원가입 · 로그인
//  회원     : 카탈로그 · 마이페이지 · 로그아웃
//  관리자   : 카탈로그 · ⚙관리자 · 마이페이지 · 로그아웃
document.addEventListener('layout:ready', async () => {
  const actions = document.getElementById('nav-actions');
  const loginBtn  = document.getElementById('nav-login-btn');
  const signupBtn = document.getElementById('nav-signup-btn');
  if (!actions || !loginBtn) return;

  const { data: { session } } = await sb.auth.getSession();
  if (!session) return;  // 비로그인 → 회원가입/로그인 그대로

  // 로그인 상태: 회원가입 숨김, 로그인 → 마이페이지, 로그아웃 추가
  if (signupBtn) signupBtn.style.display = 'none';
  loginBtn.textContent = '마이페이지';
  loginBtn.href = '/mypage/';

  if (!document.getElementById('nav-logout-btn')) {
    const out = document.createElement('a');
    out.id = 'nav-logout-btn';
    out.href = '#';
    out.className = 'btn-outline';
    out.textContent = '로그아웃';
    out.addEventListener('click', (e) => { e.preventDefault(); lifeartLogout(); });
    actions.appendChild(out);
  }

  // 관리자면 마이페이지 앞에 ⚙관리자 링크
  const { data: profile } = await sb.from('profiles').select('role, tenant_id').eq('id', session.user.id).maybeSingle();
  if (profile?.role === 'admin' && profile?.tenant_id === TENANT_UUID) {
    if (!document.getElementById('nav-admin-btn')) {
      const a = document.createElement('a');
      a.id = 'nav-admin-btn';
      a.href = '/admin/';
      a.className = 'btn-outline';
      a.textContent = '⚙ 관리자';
      actions.insertBefore(a, loginBtn);
    }
  }
});
