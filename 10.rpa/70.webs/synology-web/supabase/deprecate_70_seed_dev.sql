-- ═══════════════════════════════════════════════════════════════════
-- 70_seed_dev.sql
-- WorksFree Hub — [7단계] 개발 테스트 사용자 + 최종 검증
--
-- 실행 순서: 7/7  (60_external_dbs.sql 이후)
-- ⚠ 주의: 개발·테스트 환경 전용. 프로덕션(portal)에서는 실행하지 마세요.
--
-- 포함 내용:
--   - 개발 테스트 사용자 4명
--       test@worksfree.co.kr       일반회원   TestPassword123!
--       consultant@worksfree.co.kr 컨설턴트   TestPassword123!
--       gfc@worksfree.co.kr        GFC파트너  TestPassword123!
--       admin@worksfree.co.kr      관리자     AdminPassword123!
--   - instance_id 보정 (GoTrue 로그인 정상화)
--   - 최종 검증 쿼리 (전체 스키마 현황 출력)
--
-- 멱등성: ON CONFLICT DO NOTHING → 이미 존재해도 안전
-- ═══════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════
-- 개발 테스트 사용자 4명
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

UPDATE public.profiles SET role = 'general', agreed_at = NOW()
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


-- (3) GFC 파트너
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token, email_change, email_change_token_new
) VALUES (
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'authenticated', 'authenticated', 'gfc@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"GFC 파트너 테스터"}'::JSONB,
  '{"provider":"email","providers":["email"]}'::JSONB,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'gfc@worksfree.co.kr', 'd0000003-0000-4000-8000-000000000000'::UUID,
  jsonb_build_object('sub','d0000003-0000-4000-8000-000000000000',
    'email','gfc@worksfree.co.kr','email_verified',true,'phone_verified',false),
  'email', now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

UPDATE public.profiles SET role = 'gfc', agreed_at = NOW()
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
-- 최종 검증 — 전체 스키마 현황
-- ══════════════════════════════════════════════════════════════════════

SELECT '=== [1] 테이블 목록 ===' AS section;
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name   IN ('profiles','credits','payments',
                        'email_log','email_unsubscribes','page_views',
                        'biz_contacts','biz_send_log','jobkorea_proposals')
ORDER  BY table_name;

SELECT '=== [2] RLS 정책 ===' AS section;
SELECT tablename, policyname, cmd
FROM   pg_policies
WHERE  schemaname = 'public'
  AND  tablename  IN ('profiles','credits','payments',
                      'email_log','email_unsubscribes','page_views')
ORDER  BY tablename, policyname;

SELECT '=== [3] 트리거 ===' AS section;
SELECT trigger_name, event_object_table
FROM   information_schema.triggers
WHERE  trigger_name IN ('on_auth_user_created', 'on_auth_user_updated')
ORDER  BY trigger_name;

SELECT '=== [4] 함수 목록 ===' AS section;
SELECT routine_name
FROM   information_schema.routines
WHERE  routine_schema = 'public'
  AND  routine_name   IN (
    'is_admin', 'handle_new_user', 'sync_profile_name',
    'admin_set_user_role', 'admin_grant_credits', 'admin_set_user_name',
    'admin_get_all_profiles', 'admin_get_user_logins', 'admin_page_view_stats',
    'get_user_credit_balance', 'deduct_credits', 'get_email_history'
  )
ORDER  BY routine_name;

SELECT '=== [5] 뷰 ===' AS section;
SELECT table_name AS view_name
FROM   information_schema.views
WHERE  table_schema = 'public'
  AND  table_name   IN ('credit_balance', 'page_view_stats')
ORDER  BY table_name;

SELECT '=== [6] 개발 테스트 사용자 ===' AS section;
SELECT id, email, name, role, agreed_at IS NOT NULL AS has_agreed
FROM   public.profiles
WHERE  id IN (
  'd0000001-0000-4000-8000-000000000000'::UUID,
  'd0000002-0000-4000-8000-000000000000'::UUID,
  'd0000003-0000-4000-8000-000000000000'::UUID,
  'd0000004-0000-4000-8000-000000000000'::UUID
)
ORDER  BY id;
