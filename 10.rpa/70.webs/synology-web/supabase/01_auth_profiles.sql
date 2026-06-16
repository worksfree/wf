-- ═══════════════════════════════════════════════════════════════════
-- 01_auth_profiles.sql
-- WorksFree Hub — [Stage 1] 회원 인증 · 프로필
--
-- 책 참조: 7장(Supabase 인증), 8장(DB 구축)
--
-- 포함 내용:
--   - pgcrypto 확장
--   - public.profiles        (사용자 프로필 · 역할)
--   - is_admin()             (RLS 헬퍼 함수 — 전 스테이지 공통)
--   - profiles RLS 정책
--   - handle_new_user        (신규 가입 → profiles 행 자동 생성)
--   - sync_profile_name      (auth 업데이트 → name·email 동기화)
--   - 기존 사용자 소급 보완
--
-- 실행 환경: Supabase SQL Editor → 전체 선택 → Run
-- 멱등성: 반복 실행 안전 (CREATE ... IF NOT EXISTS, OR REPLACE)
-- ═══════════════════════════════════════════════════════════════════


-- ── 0. 확장 ──────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ══════════════════════════════════════════════════════════════════════
-- 1. profiles — 사용자 프로필 · 역할
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.profiles (
  id               UUID        REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  name             TEXT,
  email            TEXT,
  agreed_at        TIMESTAMPTZ,
  marketing_agreed BOOLEAN     DEFAULT false,
  role             TEXT        DEFAULT 'general',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 기존 테이블에 누락 컬럼 보완 (멱등성)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name             TEXT,
  ADD COLUMN IF NOT EXISTS email            TEXT,
  ADD COLUMN IF NOT EXISTS agreed_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS marketing_agreed BOOLEAN     DEFAULT false,
  ADD COLUMN IF NOT EXISTS role             TEXT        DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS created_at       TIMESTAMPTZ DEFAULT NOW();

-- role 값 제약 (admin은 DB 직접 수정만 허용)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('general', 'consultant', 'gfc', 'ceo', 'staff', 'admin'));

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 2. is_admin() — RLS 정책 내 순환 참조 방지용 헬퍼 (전 스테이지 공통)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 3. profiles RLS 정책
-- ══════════════════════════════════════════════════════════════════════
-- 기존 정책 전부 삭제 (이름 불일치 방지)
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies
           WHERE schemaname = 'public' AND tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles', r.policyname);
  END LOOP;
END $$;

-- 본인 행: 모든 작업 허용
CREATE POLICY "profiles_self"
  ON public.profiles FOR ALL
  USING     (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 관리자: 전체 SELECT
CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 4. handle_new_user — 신규 가입 시 profiles 행 자동 생성
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name')
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
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ══════════════════════════════════════════════════════════════════════
-- 5. sync_profile_name — auth 업데이트 시 profiles 자동 동기화
--    JS에서 auth.updateUser() 호출 → 트리거 → profiles.name·email 갱신
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.sync_profile_name()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  _new_name  TEXT;
  _new_email TEXT;
BEGIN
  _new_name  := COALESCE(
                  NEW.raw_user_meta_data->>'full_name',
                  NEW.raw_user_meta_data->>'name'
                );
  _new_email := NEW.email;
  UPDATE public.profiles
  SET
    name  = COALESCE(_new_name,  name),
    email = COALESCE(_new_email, email)
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE OF raw_user_meta_data, email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_profile_name();


-- ══════════════════════════════════════════════════════════════════════
-- 6. 기존 사용자 소급 동기화 (트리거 없던 시절 가입자 보완)
-- ══════════════════════════════════════════════════════════════════════
INSERT INTO public.profiles (id)
SELECT id FROM auth.users
ON CONFLICT (id) DO NOTHING;

UPDATE public.profiles p
SET
  name  = COALESCE(u.raw_user_meta_data->>'full_name',
                   u.raw_user_meta_data->>'name', p.name),
  email = COALESCE(u.email, p.email)
FROM auth.users u
WHERE p.id = u.id
  AND (p.name IS NULL OR p.email IS NULL);


-- ══════════════════════════════════════════════════════════════════════
-- 7. 관리자 전용 함수 — 역할·이름 변경, 전체 프로필 조회
-- ══════════════════════════════════════════════════════════════════════

-- ── admin_set_user_role ───────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_id UUID, new_role TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_role NOT IN ('general', 'consultant', 'gfc', 'ceo', 'staff') THEN
    RETURN 'error: invalid_role';
  END IF;
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ── admin_set_user_name ────────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(target_id UUID, new_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_name IS NULL OR trim(new_name) = '' THEN RETURN 'error: empty_name'; END IF;
  UPDATE public.profiles SET name = trim(new_name) WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ── admin_get_all_profiles ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (
  id        UUID,
  email     TEXT,
  name      TEXT,
  role      TEXT,
  agreed_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM   public.profiles p
    ORDER  BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;


-- ── admin_get_user_logins ──────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM   auth.users au;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT 'profiles' AS item, COUNT(*) AS count FROM public.profiles
UNION ALL
SELECT 'triggers', COUNT(*) FROM information_schema.triggers
  WHERE trigger_name IN ('on_auth_user_created', 'on_auth_user_updated');
