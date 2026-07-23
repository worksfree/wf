-- ================================================================
-- 22_lifeart_admin_orders_options.sql — 주문 관리에 옵션상품(addon) 내역 노출
--
-- 21(옵션상품) 이후 실행. 15가 만든 lifeart_admin_get_orders 는 반환 컬럼이
-- 고정돼 있어 CREATE OR REPLACE 로 컬럼을 늘릴 수 없음 → DROP 후 재생성.
-- (반환 타입 변경 시 Postgres 규칙 — 15 마이그레이션 파일 자체는 이미 실행된
--  것으로 간주하고 건드리지 않음. 항상 새 번호로 이어서 수정한다.)
-- ================================================================

DROP FUNCTION IF EXISTS public.lifeart_admin_get_orders();

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
    shipping_address text,
    options         jsonb
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE lifeart uuid := (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT o.id, o.created_at,
           p.name::text, u.email::text,
           pr.name::text, o.quantity, o.amount,
           o.status::text, o.shipping_status::text,
           pay.status::text, pay.pg_tid::text, o.shipping_address::text,
           o.options
    FROM public.lifeart_orders o
    LEFT JOIN auth.users u          ON u.id  = o.user_id
    LEFT JOIN public.profiles p     ON p.id  = o.user_id
    LEFT JOIN public.lifeart_products pr ON pr.id = o.product_id
    LEFT JOIN LATERAL (
        SELECT status, pg_tid FROM public.lifeart_payments
        WHERE order_id = o.id ORDER BY created_at DESC LIMIT 1
    ) pay ON true
    WHERE o.tenant_id = lifeart
    ORDER BY o.created_at DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_orders() TO authenticated;

-- ── 검증 ──
SELECT proname FROM pg_proc WHERE proname = 'lifeart_admin_get_orders';
