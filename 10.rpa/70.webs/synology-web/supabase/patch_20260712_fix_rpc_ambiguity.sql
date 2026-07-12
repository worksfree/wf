-- ============================================================
--  패치: admin RPC 함수 컬럼 ambiguity 수정
--  실행: Supabase SQL Editor에서 전체 선택 → RUN
--  날짜: 2026-07-12
-- ============================================================

-- 문제: RETURNS TABLE에 선언된 컬럼명(role, id)이
--       함수 내부 SELECT의 비한정 컬럼명과 충돌
--       → "column reference 'role' is ambiguous" 400 오류
-- 수정: 내부 SELECT에 p2 alias 추가하여 명시적으로 한정

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
  SELECT p2.role INTO _r FROM public.profiles p2 WHERE p2.id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM   public.profiles p
    ORDER  BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;


CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT p2.role INTO _r FROM public.profiles p2 WHERE p2.id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM   auth.users au;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;
