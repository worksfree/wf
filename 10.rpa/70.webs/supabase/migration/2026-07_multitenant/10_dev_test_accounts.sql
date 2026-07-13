-- ================================================================
-- 10_dev_test_accounts.sql — dev 툴킷용 테스트 계정 보정 (pre-test 전용)
--
-- 전제: 아래 두 계정이 이미 가입되어 있어야 함(사이트 또는 REST 가입).
--   lifeart.tester@worksfree.kr     / LifeArt!test2026   (회원)
--   lifeart.admin.test@worksfree.kr / LifeArt!admin2026  (관리자)
--
-- 하는 일:
--   ① 이메일 인증 강제 완료 (테스트 계정이라 즉시 로그인 가능하게)
--   ② profiles.tenant_id 를 LifeArt 로 보정 (트리거가 worksfree 기본값으로 넣었음)
--   ③ 관리자 계정 role='admin'
--
-- ※ 이 계정들은 pre-test 검수용 throwaway. 운영 오픈 전 삭제 권장.
-- ================================================================

-- ① 이메일 인증 완료
UPDATE auth.users
SET email_confirmed_at = COALESCE(email_confirmed_at, NOW())
WHERE email IN ('lifeart.tester@worksfree.kr', 'lifeart.admin.test@worksfree.kr');

-- ② + ③ 프로필 테넌트/역할 보정
UPDATE public.profiles p
SET tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr'),
    role = CASE
             WHEN au.email = 'lifeart.admin.test@worksfree.kr' THEN 'admin'
             ELSE 'member'
           END
FROM auth.users au
WHERE au.id = p.id
  AND au.email IN ('lifeart.tester@worksfree.kr', 'lifeart.admin.test@worksfree.kr');

-- ── 검증 ──
SELECT au.email, p.role, t.domain AS tenant, au.email_confirmed_at IS NOT NULL AS confirmed
FROM auth.users au
JOIN public.profiles p ON p.id = au.id
LEFT JOIN public.tenants t ON t.id = p.tenant_id
WHERE au.email IN ('lifeart.tester@worksfree.kr', 'lifeart.admin.test@worksfree.kr');
-- 기대:
--   lifeart.tester...     | member | lifeart.ai.kr | true
--   lifeart.admin.test... | admin  | lifeart.ai.kr | true
