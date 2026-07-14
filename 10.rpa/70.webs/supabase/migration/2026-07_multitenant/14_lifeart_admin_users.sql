-- ================================================================
-- 14_lifeart_admin_users.sql — LifeArt O&M 회원 관리 (테넌트 스코프)
--
-- 브라우저(anon/authenticated)는 auth.users(이메일 등)를 직접 못 읽으므로,
-- SECURITY DEFINER RPC 로 "LifeArt 테넌트 회원만" 조회/역할변경을 제공한다.
-- 반드시 04(is_lifeart_admin) 이후 실행.
-- ================================================================

-- ── 회원 목록 조회 (LifeArt 테넌트 한정) ──
CREATE OR REPLACE FUNCTION public.lifeart_admin_get_users()
RETURNS TABLE (
    id         uuid,
    email      text,
    provider   text,
    name       text,
    role       text,
    created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT public.is_lifeart_admin() THEN
        RAISE EXCEPTION 'not_lifeart_admin';
    END IF;

    RETURN QUERY
    SELECT u.id,
           u.email::text,
           COALESCE(u.raw_app_meta_data->>'provider', 'email') AS provider,
           p.name,
           p.role,
           u.created_at
    FROM public.profiles p
    JOIN auth.users u ON u.id = p.id
    WHERE p.tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
    ORDER BY u.created_at DESC;
END;
$$;

-- ── 회원 역할 변경 (LifeArt 테넌트 내부에서만, member/admin 만 허용) ──
--    타 테넌트 사용자에게는 절대 영향 없음(WHERE tenant_id 스코프).
CREATE OR REPLACE FUNCTION public.lifeart_admin_set_role(target_id uuid, new_role text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    lifeart uuid := (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');
    updated int;
BEGIN
    IF NOT public.is_lifeart_admin() THEN
        RETURN 'error: not_lifeart_admin';
    END IF;
    IF new_role NOT IN ('member', 'admin') THEN
        RETURN 'error: invalid_role';
    END IF;

    UPDATE public.profiles
    SET role = new_role
    WHERE id = target_id AND tenant_id = lifeart;   -- 테넌트 스코프 필수
    GET DIAGNOSTICS updated = ROW_COUNT;

    IF updated = 0 THEN
        RETURN 'error: not_in_tenant';   -- LifeArt 회원이 아니면 거부
    END IF;
    RETURN 'ok';
END;
$$;

GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_users() TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_set_role(uuid, text) TO authenticated;

-- ── 검증 ──
-- (LifeArt 관리자 세션에서 실행해야 결과가 나옴. 그 외 세션은 예외/거부)
-- SELECT * FROM public.lifeart_admin_get_users();
SELECT proname FROM pg_proc WHERE proname IN ('lifeart_admin_get_users','lifeart_admin_set_role');
