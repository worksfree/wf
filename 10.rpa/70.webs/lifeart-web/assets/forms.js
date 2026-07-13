// 문의/견적/제휴 폼 공통 제출 로직 — public.lifeart_inquiries 테이블에 INSERT
async function submitInquiry(type, formEl, msgElId) {
  const msgEl = document.getElementById(msgElId);
  const { data: { session } } = await sb.auth.getSession();
  const data = {
    tenant_id: TENANT_UUID,
    type,
    env: getEnv(),
    user_id: session?.user?.id || null,
    name: formEl.querySelector('[name=name]').value.trim(),
    phone: formEl.querySelector('[name=phone]').value.trim(),
    email: formEl.querySelector('[name=email]')?.value.trim() || null,
    message: formEl.querySelector('[name=message]').value.trim(),
  };
  if (!data.name || !data.phone || !data.message) {
    msgEl.textContent = '이름, 연락처, 문의 내용을 모두 입력해주세요.';
    msgEl.className = 'form-msg error';
    return;
  }
  msgEl.textContent = '접수 중...';
  msgEl.className = 'form-msg';
  const { error } = await sb.from('lifeart_inquiries').insert(data);
  if (error) {
    msgEl.textContent = '접수에 실패했습니다. 잠시 후 다시 시도해주세요.';
    msgEl.className = 'form-msg error';
    console.error(error);
    return;
  }
  msgEl.textContent = '문의가 접수되었습니다. 빠르게 연락드리겠습니다.';
  msgEl.className = 'form-msg success';
  formEl.reset();
}
