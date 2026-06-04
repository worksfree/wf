-- ═══════════════════════════════════════════════════════════════════
-- fix_profiles_name_sync.sql
-- profiles.name 컬럼 추가 + auth.users 업데이트 시 자동 동기화 트리거
-- Supabase Dashboard → SQL Editor 에서 실행
-- 멱등성 보장: 여러 번 실행해도 안전
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. profiles 테이블에 name, email 컬럼 추가 ─────────────────────
--    (이미 있으면 무시)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS name  TEXT,
  ADD COLUMN IF NOT EXISTS email TEXT;

-- ── 2. 기존 사용자 name/email 소급 동기화 ──────────────────────────
--    현재 auth.users.raw_user_meta_data 와 auth.users.email 값으로 채움
UPDATE public.profiles p
SET
  name  = COALESCE(
            u.raw_user_meta_data->>'full_name',
            u.raw_user_meta_data->>'name',
            p.name
          ),
  email = COALESCE(u.email, p.email)
FROM auth.users u
WHERE p.id = u.id;


-- ── 3. 신규 가입 트리거 갱신 ───────────────────────────────────────
--    handle_new_user: 가입 시 name, email 도 함께 삽입
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, name, email)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name'),
    NEW.email
  )
  ON CONFLICT (id) DO UPDATE
    SET name  = COALESCE(EXCLUDED.name,  profiles.name),
        email = COALESCE(EXCLUDED.email, profiles.email);
  RETURN NEW;
END;
$$;


-- ── 4. auth.users 업데이트 시 profiles.name 자동 동기화 트리거 ──────
--    saveProfileName() 이 auth.updateUser() 를 호출하면
--    이 트리거가 자동으로 profiles.name 을 업데이트함
--    → JS 에서 profiles.update() 를 별도로 호출하지 않아도 항상 동기화됨

CREATE OR REPLACE FUNCTION public.sync_profile_name()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
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
    name  = COALESCE(_new_name,  name),   -- null 이면 기존 값 유지
    email = COALESCE(_new_email, email)
  WHERE id = NEW.id;

  RETURN NEW;
END;
$$;

-- 트리거: auth.users 의 raw_user_meta_data 또는 email 변경 시 실행
DROP TRIGGER IF EXISTS on_auth_user_updated ON auth.users;
CREATE TRIGGER on_auth_user_updated
  AFTER UPDATE OF raw_user_meta_data, email ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_profile_name();


-- ── 5. 결과 확인 ────────────────────────────────────────────────────
SELECT '=== profiles 컬럼 ===' AS section;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'profiles'
ORDER BY ordinal_position;

SELECT '=== 트리거 목록 ===' AS section;
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_name IN ('on_auth_user_created', 'on_auth_user_updated');

SELECT '=== name 동기화 현황 ===' AS section;
SELECT
  COUNT(*)                                    AS total_users,
  COUNT(name)                                 AS has_name,
  COUNT(*) FILTER (WHERE name IS NULL)        AS missing_name,
  COUNT(email)                                AS has_email
FROM public.profiles;
