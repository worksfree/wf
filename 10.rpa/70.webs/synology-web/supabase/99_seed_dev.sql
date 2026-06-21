-- ═══════════════════════════════════════════════════════════════════
-- 99_seed_dev.sql
-- WorksFree Hub — [개발/테스트 전용] 테스트 계정 생성
--
-- ⚠ 프로덕션(portal) 환경에서는 절대 실행하지 마세요.
--
-- 사전 조건: 01_auth_profiles.sql 실행 완료
--
-- 생성 계정 (이메일 로그인):
--   test@worksfree.co.kr        일반회원    TestPassword123!
--   consultant@worksfree.co.kr  컨설턴트    TestPassword123!
--   partner@worksfree.co.kr     파트너      TestPassword123!
--   admin@worksfree.co.kr       관리자      AdminPassword123!
--
-- 멱등성: ON CONFLICT DO NOTHING → 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 테스트 사용자 4명
-- ══════════════════════════════════════════════════════════════════════

-- (1) 일반회원
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'test@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"테스트 회원"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'test@worksfree.co.kr', 'd0000001-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000001-0000-4000-8000-000000000000',
    'email','test@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'member', agreed_at = NOW()
WHERE id = 'd0000001-0000-4000-8000-000000000000'::UUID;


-- (2) 컨설턴트
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'consultant@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"컨설턴트 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'consultant@worksfree.co.kr', 'd0000002-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000002-0000-4000-8000-000000000000',
    'email','consultant@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'consultant', agreed_at = NOW()
WHERE id = 'd0000002-0000-4000-8000-000000000000'::UUID;


-- (3) 파트너
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'partner@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"파트너 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'partner@worksfree.co.kr', 'd0000003-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000003-0000-4000-8000-000000000000',
    'email','partner@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'partner', agreed_at = NOW()
WHERE id = 'd0000003-0000-4000-8000-000000000000'::UUID;


-- (4) 관리자
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000004-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'admin@worksfree.co.kr',
  crypt('AdminPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"관리자 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'admin@worksfree.co.kr', 'd0000004-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000004-0000-4000-8000-000000000000',
    'email','admin@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'admin', agreed_at = NOW()
WHERE id = 'd0000004-0000-4000-8000-000000000000'::UUID;


-- ── instance_id 보정 (GoTrue가 instance_id 없는 행은 로그인 불가) ──────
UPDATE auth.users
SET instance_id = (
  SELECT instance_id FROM auth.users WHERE instance_id IS NOT NULL LIMIT 1
)
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'd0000004-0000-4000-8000-000000000000'::UUID
) AND instance_id IS NULL;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT email, role FROM public.profiles
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'd0000004-0000-4000-8000-000000000000'::UUID
)
ORDER BY email;
