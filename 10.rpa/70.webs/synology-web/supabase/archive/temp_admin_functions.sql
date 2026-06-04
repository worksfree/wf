-- ═══════════════════════════════════════════════════════════════════
-- 관리자 전용 SECURITY DEFINER 함수
-- 목적: RLS(auth.uid()=id) 정책을 우회해 관리자가 다른 사용자의
--       프로필 역할을 변경하고 크레딧을 지급할 수 있도록 함.
-- 실행: Supabase Dashboard → SQL Editor 에서 실행
-- ═══════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────
-- 1. admin_set_user_role
--    관리자가 특정 사용자의 역할을 변경한다.
-- ─────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(
  target_id UUID,
  new_role  TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _caller_role TEXT;
BEGIN
  -- 호출자가 admin인지 확인
  SELECT role INTO _caller_role
  FROM public.profiles
  WHERE id = auth.uid();

  IF _caller_role IS DISTINCT FROM 'admin' THEN
    RETURN 'error: not_admin';
  END IF;

  -- 허용 역할 검증
  IF new_role NOT IN ('general', 'consultant', 'gfc', 'ceo', 'staff') THEN
    RETURN 'error: invalid_role';
  END IF;

  UPDATE public.profiles
  SET role = new_role
  WHERE id = target_id;

  RETURN 'ok';
END;
$$;

-- anon/authenticated 모두 호출 가능 (내부에서 admin 여부 검증)
REVOKE ALL ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ─────────────────────────────────────────────
-- 2. admin_grant_credits
--    관리자가 특정 사용자에게 크레딧을 지급한다.
-- ─────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INT, TEXT);
CREATE OR REPLACE FUNCTION public.admin_grant_credits(
  target_id UUID,
  amount    INT,
  env_name  TEXT DEFAULT 'portal'
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role
  FROM public.profiles
  WHERE id = auth.uid();

  IF _caller_role IS DISTINCT FROM 'admin' THEN
    RETURN 'error: not_admin';
  END IF;

  IF amount < 1 THEN
    RETURN 'error: invalid_amount';
  END IF;

  INSERT INTO public.credits(user_id, delta, reason, note, env, created_at)
  VALUES (target_id, amount, 'admin_grant', '관리자 수동 지급', env_name, NOW());

  RETURN 'ok';
END;
$$;

REVOKE ALL ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) TO anon, authenticated;


-- ─────────────────────────────────────────────
-- 3. admin_set_user_name
--    관리자가 특정 사용자의 이름을 변경한다.
--    profiles.name 을 직접 수정하며, DB 트리거가
--    없으므로 auth.users.user_metadata 는 별도 동기화 필요.
-- ─────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(
  target_id UUID,
  new_name  TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN
    RETURN 'error: not_admin';
  END IF;

  IF new_name IS NULL OR trim(new_name) = '' THEN
    RETURN 'error: empty_name';
  END IF;

  UPDATE public.profiles
  SET name = trim(new_name)
  WHERE id = target_id;

  RETURN 'ok';
END;
$$;

REVOKE ALL ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ─────────────────────────────────────────────
-- 확인 쿼리
-- ─────────────────────────────────────────────
SELECT routine_name, routine_type, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('admin_set_user_role', 'admin_grant_credits', 'admin_set_user_name');
