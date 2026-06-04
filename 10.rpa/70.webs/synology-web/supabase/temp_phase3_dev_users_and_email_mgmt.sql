-- ═══════════════════════════════════════════════════════════════════
-- WorksFree Hub — Phase 3: 개발 테스트 사용자 + 이메일 관리 보강
-- 실행: Supabase Dashboard → SQL Editor → Run (service_role 권한 필요)
-- 멱등성 보장: 여러 번 실행해도 안전
--
-- 포함 내용:
--   1. profiles 테이블에 name, email 컬럼 추가 + 트리거 업데이트
--   2. email_log에 status 컬럼 추가 (sent | filtered)
--   3. O&M 관리자용 RLS 정책 추가 (is_admin() 함수 포함)
--   4. 개발 테스트 사용자 4명 등록 (auth.users + profiles)
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ────────────────────────────────────────────────────────────────
-- 1. profiles 테이블 보강 — name, email 컬럼 추가
-- ────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name  text,
  ADD COLUMN IF NOT EXISTS email text;

-- 기존 가입자 이메일 백필 (auth.users에서 복사)
UPDATE public.profiles p
SET email = u.email
FROM auth.users u
WHERE p.id = u.id AND p.email IS NULL;

-- 기존 가입자 이름 백필 (auth.users 메타데이터에서 복사)
UPDATE public.profiles p
SET name = u.raw_user_meta_data->>'full_name'
FROM auth.users u
WHERE p.id = u.id AND p.name IS NULL AND u.raw_user_meta_data->>'full_name' IS NOT NULL;


-- ────────────────────────────────────────────────────────────────
-- 2. handle_new_user 트리거 업데이트 — email/name 자동 캡처
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', NULL)
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name  = COALESCE(EXCLUDED.name, public.profiles.name);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();


-- ────────────────────────────────────────────────────────────────
-- 3. email_log — status 컬럼 추가 (sent | filtered)
-- ────────────────────────────────────────────────────────────────

ALTER TABLE public.email_log
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'sent'
  CHECK (status IN ('sent', 'filtered'));

CREATE INDEX IF NOT EXISTS email_log_status_idx ON public.email_log (status, sent_at DESC);


-- ────────────────────────────────────────────────────────────────
-- 4. O&M 관리자 공통 헬퍼 함수 (SECURITY DEFINER — RLS 순환 방지)
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

GRANT EXECUTE ON FUNCTION is_admin() TO authenticated, anon;


-- ────────────────────────────────────────────────────────────────
-- 5. RLS 정책 추가 — 관리자가 모든 데이터 열람 가능
-- ────────────────────────────────────────────────────────────────

-- 5-a. profiles: 관리자는 전체 조회 가능
DROP POLICY IF EXISTS "profiles_admin_select_all" ON public.profiles;
CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());

-- 5-b. email_log: 관리자 전체 조회
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;
CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());

-- 5-c. email_unsubscribes: 관리자 전체 조회 + INSERT + DELETE
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;
CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK(is_admin());


-- ────────────────────────────────────────────────────────────────
-- 6. 개발 테스트 사용자 4명 생성
--    UUID: d0000001~4-0000-4000-8000-000000000000
--    ※ 비밀번호: TestPassword123! (일반/컨설턴트/파트너) / AdminPassword123! (관리자)
--    ※ 이미 존재하면 ON CONFLICT DO NOTHING으로 무시
-- ────────────────────────────────────────────────────────────────

-- (1) 일반회원 테스터
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token,
  email_change, email_change_token_new
) VALUES (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'authenticated', 'authenticated',
  'test@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"테스트 회원"}'::jsonb,
  '{"provider":"email","providers":["email"]}'::jsonb,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

UPDATE public.profiles SET role = 'general'
WHERE id = 'd0000001-0000-4000-8000-000000000000'::uuid;


-- (2) 컨설턴트 테스터
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token,
  email_change, email_change_token_new
) VALUES (
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'authenticated', 'authenticated',
  'consultant@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"컨설턴트 테스터"}'::jsonb,
  '{"provider":"email","providers":["email"]}'::jsonb,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

UPDATE public.profiles SET role = 'consultant'
WHERE id = 'd0000002-0000-4000-8000-000000000000'::uuid;


-- (3) 파트너(GFC) 테스터
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token,
  email_change, email_change_token_new
) VALUES (
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'authenticated', 'authenticated',
  'gfc@worksfree.co.kr',
  crypt('TestPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"파트너 테스터"}'::jsonb,
  '{"provider":"email","providers":["email"]}'::jsonb,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

UPDATE public.profiles SET role = 'gfc'
WHERE id = 'd0000003-0000-4000-8000-000000000000'::uuid;


-- (4) 관리자 테스터
INSERT INTO auth.users (
  id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_user_meta_data, raw_app_meta_data,
  is_super_admin, is_sso_user,
  confirmation_token, recovery_token,
  email_change, email_change_token_new
) VALUES (
  'd0000004-0000-4000-8000-000000000000'::uuid,
  'authenticated', 'authenticated',
  'admin@worksfree.co.kr',
  crypt('AdminPassword123!', gen_salt('bf')),
  now(), now(), now(),
  '{"full_name":"관리자 테스터"}'::jsonb,
  '{"provider":"email","providers":["email"]}'::jsonb,
  false, false, '', '', '', ''
) ON CONFLICT (id) DO NOTHING;

UPDATE public.profiles SET role = 'admin'
WHERE id = 'd0000004-0000-4000-8000-000000000000'::uuid;


-- ────────────────────────────────────────────────────────────────
-- 7. 최종 검증
-- ────────────────────────────────────────────────────────────────

SELECT '=== 개발 테스트 사용자 profiles ===' AS section;
SELECT id, email, name, role, agreed_at, created_at
FROM public.profiles
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
ORDER BY id;

SELECT '=== email_log 컬럼 ===' AS section;
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'email_log'
ORDER BY ordinal_position;

SELECT '=== is_admin() 함수 ===' AS section;
SELECT routine_name, security_type
FROM information_schema.routines
WHERE routine_schema = 'public' AND routine_name = 'is_admin';

SELECT '=== RLS 정책 (Phase 3 추가분) ===' AS section;
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('profiles','email_log','email_unsubscribes')
  AND policyname IN ('profiles_admin_select_all','email_log_admin_select','email_unsubscribes_admin')
ORDER BY tablename, policyname;
