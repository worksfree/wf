-- ================================================================
-- 18_fix_admin_rpc_ambiguity.sql — 관리자 RPC "column reference id is ambiguous" 수정
--
-- 원인: 15의 lifeart_admin_get_orders LATERAL 서브쿼리 안에서 바깥 테이블
--   (orders/users/profiles/products)이 스코프에 들어와 미한정 컬럼(status·created_at 등)이
--   충돌 → 42702. 서브쿼리 테이블/컬럼을 전부 alias 로 한정해 해소.
--   추가로 #variable_conflict use_column 지시로 OUT 파라미터-컬럼 충돌도 방지.
-- 반환 타입 동일 → CREATE OR REPLACE 로 교체(재실행 안전).
-- ================================================================

CREATE OR REPLACE FUNCTION public.lifeart_admin_get_orders()
RETURNS TABLE (
    id              uuid,
    created_at      timestamptz,
    member_name     text,
    member_email    text,
    product_name    text,
    quantity        integer,
    amount          bigint,
    status          text,
    shipping_status text,
    pay_status      text,
    pg_tid          text,
    shipping_address text
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
#variable_conflict use_column
DECLARE lifeart uuid := (SELECT t.id FROM public.tenants t WHERE t.domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT o.id, o.created_at,
           p.name::text, u.email::text,
           pr.name::text, o.quantity, o.amount,
           o.status::text, o.shipping_status::text,
           pay.pstatus::text, pay.ptid::text, o.shipping_address::text
    FROM public.lifeart_orders o
    LEFT JOIN auth.users u               ON u.id  = o.user_id
    LEFT JOIN public.profiles p          ON p.id  = o.user_id
    LEFT JOIN public.lifeart_products pr ON pr.id = o.product_id
    LEFT JOIN LATERAL (
        SELECT lp.status AS pstatus, lp.pg_tid AS ptid
        FROM public.lifeart_payments lp
        WHERE lp.order_id = o.id
        ORDER BY lp.created_at DESC
        LIMIT 1
    ) pay ON true
    WHERE o.tenant_id = lifeart
    ORDER BY o.created_at DESC;
END;
$$;

-- 회원 목록: 집계 서브쿼리 컬럼 한정 + 지시 추가 (방어적)
CREATE OR REPLACE FUNCTION public.lifeart_admin_get_users()
RETURNS TABLE (
    id            uuid,
    email         text,
    provider      text,
    name          text,
    role          text,
    created_at    timestamptz,
    order_count   bigint,
    total_paid    bigint,
    last_order_at timestamptz
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
#variable_conflict use_column
DECLARE lifeart uuid := (SELECT t.id FROM public.tenants t WHERE t.domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT u.id,
           u.email::text,
           COALESCE(u.raw_app_meta_data->>'provider', 'email')::text,
           p.name::text,
           p.role::text,
           u.created_at,
           COALESCE(agg.cnt, 0)::bigint,
           COALESCE(agg.paid, 0)::bigint,
           agg.last_at
    FROM public.profiles p
    JOIN auth.users u ON u.id = p.id
    LEFT JOIN (
        SELECT lo.user_id AS uid,
               COUNT(*)                                                           AS cnt,
               SUM(lo.amount) FILTER (WHERE lo.status IN ('paid','shipping','done')) AS paid,
               MAX(lo.created_at)                                                 AS last_at
        FROM public.lifeart_orders lo
        WHERE lo.tenant_id = lifeart
        GROUP BY lo.user_id
    ) agg ON agg.uid = p.id
    WHERE p.tenant_id = lifeart
    ORDER BY u.created_at DESC;
END;
$$;

-- ── 검증 ── (LifeArt 관리자 세션 브라우저에서 확인; SQL Editor 는 not_lifeart_admin 예외 정상)
SELECT 'reload PostgREST 스키마 캐시' AS note;
NOTIFY pgrst, 'reload schema';
SELECT proname FROM pg_proc WHERE proname IN ('lifeart_admin_get_orders','lifeart_admin_get_users');
