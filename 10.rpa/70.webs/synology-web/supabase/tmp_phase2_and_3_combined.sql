-- ═══════════════════════════════════════════════════════════════════
-- WorksFree Hub — Phase 2 + Phase 3 합본
-- 실행: Supabase Dashboard → SQL Editor → Run (service_role 권한 필요)
-- 멱등성 보장: 여러 번 실행해도 안전
--
-- Phase 2: email_log + email_unsubscribes 테이블 생성
-- Phase 3: profiles 보강 + dev 테스트 사용자 4명 + O&M RLS
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ════════════════════════════════════════════════════════════════════
-- PHASE 2: 이메일 관리 테이블
-- ════════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 2-1. email_log — 발송 이력
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.email_log (
  id              bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sent_at         timestamptz  NOT NULL DEFAULT now(),
  recipient_email text         NOT NULL,
  sender_email    text,
  sender_name     text,
  flyer_src       text,
  flyer_name      text,
  subject         text,
  env             text         NOT NULL DEFAULT 'portal'
                  CHECK (env IN ('dev', 'test', 'staging', 'portal')),
  extra           jsonb        DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS email_log_recipient_idx ON public.email_log (recipient_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_sender_idx    ON public.email_log (sender_email, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_log_env_idx       ON public.email_log (env, sent_at DESC);

ALTER TABLE public.email_log ENABLE ROW LEVEL SECURITY;


-- ────────────────────────────────────────────────────────────────
-- 2-2. email_log — status 컬럼 추가 (sent | filtered)
--      테이블 생성 직후 추가하므로 항상 존재하게 됨
-- ────────────────────────────────────────────────────────────────

ALTER TABLE public.email_log
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'sent'
  CHECK (status IN ('sent', 'filtered'));

CREATE INDEX IF NOT EXISTS email_log_status_idx ON public.email_log (status, sent_at DESC);


-- ────────────────────────────────────────────────────────────────
-- 2-3. email_unsubscribes — 수신거부 목록
-- ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.email_unsubscribes (
  id               bigint       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email            text         NOT NULL UNIQUE,
  unsubscribed_at  timestamptz  NOT NULL DEFAULT now(),
  source           text         NOT NULL DEFAULT 'link'
                   CHECK (source IN ('link', 'manual')),
  note             text
);

CREATE INDEX IF NOT EXISTS email_unsubscribes_email_idx ON public.email_unsubscribes (email);

ALTER TABLE public.email_unsubscribes ENABLE ROW LEVEL SECURITY;


-- ────────────────────────────────────────────────────────────────
-- 2-4. 발송 이력 조회 헬퍼
-- ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION get_email_history(p_email text, p_limit int DEFAULT 10)
RETURNS TABLE (
  sent_at         timestamptz,
  flyer_name      text,
  sender_name     text,
  subject         text,
  env             text
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT sent_at, flyer_name, sender_name, subject, env
  FROM public.email_log
  WHERE recipient_email = lower(p_email)
  ORDER BY sent_at DESC
  LIMIT p_limit;
$$;


-- ════════════════════════════════════════════════════════════════════
-- PHASE 3: profiles 보강 + 관리자 RLS + dev 테스트 사용자
-- ════════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 3-1. profiles.role CHECK 제약 확장 — 'admin' 추가
--      기존 제약: general | consultant | gfc  →  + admin 추가
-- ────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_role_check;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('general', 'consultant', 'gfc', 'admin'));


-- ────────────────────────────────────────────────────────────────
-- 3-3. profiles 테이블 보강 — name, email 컬럼 추가
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
-- 3-4. handle_new_user 트리거 업데이트 — email/name 자동 캡처
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
-- 3-5. O&M 관리자 헬퍼 함수 (SECURITY DEFINER — RLS 순환 방지)
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
-- 3-6. RLS 정책 추가 — 관리자가 모든 데이터 열람 가능
-- ────────────────────────────────────────────────────────────────

-- profiles: 관리자는 전체 조회 가능
DROP POLICY IF EXISTS "profiles_admin_select_all" ON public.profiles;
CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());

-- email_log: 관리자 전체 조회
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;
CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());

-- email_unsubscribes: 관리자 전체 조회 + INSERT + DELETE
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;
CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK(is_admin());


-- ────────────────────────────────────────────────────────────────
-- 3-5. 개발 테스트 사용자 4명 생성
--      UUID: d0000001~4-0000-4000-8000-000000000000
--      비밀번호: TestPassword123! / AdminPassword123! (관리자)
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


-- ════════════════════════════════════════════════════════════════════
-- 최종 검증
-- ════════════════════════════════════════════════════════════════════

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

SELECT '=== is_admin() + RLS 정책 ===' AS section;
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('profiles','email_log','email_unsubscribes')
  AND policyname IN ('profiles_admin_select_all','email_log_admin_select','email_unsubscribes_admin')
ORDER BY tablename, policyname;
