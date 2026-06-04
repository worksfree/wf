-- ═══════════════════════════════════════════════════════════════════
-- 30_triggers.sql
-- WorksFree Hub — [3단계] 트리거 함수 + 트리거 등록
--
-- 실행 순서: 3/7  (20_security_rls.sql 이후)
-- 다음 단계: 40_functions.sql
--
-- 포함 내용:
--   - handle_new_user     : auth.users INSERT → profiles 행 자동 생성
--   - sync_profile_name   : auth.users UPDATE → profiles.name·email 동기화
--   - 기존 사용자 소급 보완 : 트리거 없던 시절 가입자의 profiles 행 생성
-- ═══════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════
-- 1. handle_new_user — 신규 가입 시 profiles 행 자동 생성
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
-- 2. sync_profile_name — auth 업데이트 시 profiles 자동 동기화
--    JS에서 auth.updateUser() 호출 → 트리거 → profiles.name·email 갱신
--    (프론트엔드에서 profiles.update() 별도 호출 불필요)
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
-- 3. 기존 사용자 소급 동기화 (트리거 없던 시절 가입자 보완)
-- ══════════════════════════════════════════════════════════════════════

-- profiles 행 없는 사용자 생성
INSERT INTO public.profiles (id)
SELECT id FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- name·email 백필
UPDATE public.profiles p
SET
  name  = COALESCE(u.raw_user_meta_data->>'full_name',
                   u.raw_user_meta_data->>'name', p.name),
  email = COALESCE(u.email, p.email)
FROM auth.users u
WHERE p.id = u.id
  AND (p.name IS NULL OR p.email IS NULL);


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT trigger_name, event_manipulation, event_object_table, action_timing
FROM   information_schema.triggers
WHERE  trigger_name IN ('on_auth_user_created', 'on_auth_user_updated')
ORDER  BY trigger_name;
