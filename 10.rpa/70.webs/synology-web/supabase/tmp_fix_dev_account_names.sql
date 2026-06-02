-- ============================================================
-- fix_dev_account_names.sql
-- dev 테스트 계정 이름 강제 업데이트
--
-- 문제: phase3_dev_users_and_email_mgmt.sql 의 INSERT 가
--       ON CONFLICT DO NOTHING 이라 기존 계정 이름이 안 바뀜.
--       결과적으로 gfc / admin 계정이 같은 이름으로 보임.
--
-- 실행: Supabase Dashboard → SQL Editor → Run
-- ============================================================

-- 1. 현재 상태 확인
SELECT
  u.id,
  u.email,
  u.raw_user_meta_data->>'full_name' AS auth_full_name,
  p.name                             AS profile_name,
  p.role
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE u.id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
ORDER BY u.email;

-- 2. auth.users.raw_user_meta_data 이름 강제 업데이트
UPDATE auth.users
SET raw_user_meta_data = jsonb_set(COALESCE(raw_user_meta_data, '{}'), '{full_name}', '"테스트 회원"')
WHERE id = 'd0000001-0000-4000-8000-000000000000'::uuid;

UPDATE auth.users
SET raw_user_meta_data = jsonb_set(COALESCE(raw_user_meta_data, '{}'), '{full_name}', '"컨설턴트 테스터"')
WHERE id = 'd0000002-0000-4000-8000-000000000000'::uuid;

UPDATE auth.users
SET raw_user_meta_data = jsonb_set(COALESCE(raw_user_meta_data, '{}'), '{full_name}', '"파트너(GFC) 테스터"')
WHERE id = 'd0000003-0000-4000-8000-000000000000'::uuid;

UPDATE auth.users
SET raw_user_meta_data = jsonb_set(COALESCE(raw_user_meta_data, '{}'), '{full_name}', '"관리자 테스터"')
WHERE id = 'd0000004-0000-4000-8000-000000000000'::uuid;

-- 3. profiles.name 도 동기화
UPDATE public.profiles SET name = '테스트 회원'       WHERE id = 'd0000001-0000-4000-8000-000000000000'::uuid;
UPDATE public.profiles SET name = '컨설턴트 테스터'   WHERE id = 'd0000002-0000-4000-8000-000000000000'::uuid;
UPDATE public.profiles SET name = '파트너(GFC) 테스터' WHERE id = 'd0000003-0000-4000-8000-000000000000'::uuid;
UPDATE public.profiles SET name = '관리자 테스터'     WHERE id = 'd0000004-0000-4000-8000-000000000000'::uuid;

-- 4. 결과 확인
SELECT
  u.id,
  u.email,
  u.raw_user_meta_data->>'full_name' AS auth_full_name,
  p.name                             AS profile_name,
  p.role
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE u.id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
ORDER BY u.email;
