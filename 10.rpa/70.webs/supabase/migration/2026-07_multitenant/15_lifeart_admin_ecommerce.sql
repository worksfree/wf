-- ================================================================
-- 15_lifeart_admin_ecommerce.sql — LifeArt O&M 거래 중심 재설계 RPC
--
-- 14 이후 실행. 온라인 몰다운 운영관리를 위해:
--  · 14 의 lifeart_admin_get_users 버그 수정(반환 타입 ::text) + 구매 집계 추가
--  · 주문 목록에 주문자(회원)·결제상태 조인
--  · 회원별 주문 이력 drill-down
--  · 매출 요약(대시보드)
-- 모두 SECURITY DEFINER + is_lifeart_admin 게이트 + tenant='lifeart' 스코프.
-- 브라우저(anon)는 auth.users·타인 profiles 를 못 읽으므로 반드시 RPC 경유.
-- ================================================================

-- 결제 완료로 간주하는 주문 상태(매출 인식): paid/shipping/done
--   (pending/cancelled 은 매출 제외)

-- 14 에서 만든 get_users 는 반환 컬럼이 달라져 CREATE OR REPLACE 불가 → 먼저 DROP.
-- (재실행 안전을 위해 신규 함수들도 IF EXISTS 로 정리)
DROP FUNCTION IF EXISTS public.lifeart_admin_get_users();
DROP FUNCTION IF EXISTS public.lifeart_admin_get_orders();
DROP FUNCTION IF EXISTS public.lifeart_admin_get_member_orders(uuid);
DROP FUNCTION IF EXISTS public.lifeart_admin_sales_summary();

-- ── ① 회원 목록 + 구매 집계 (14 대체·수정) ──
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
DECLARE lifeart uuid := (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT u.id,
           u.email::text,
           COALESCE(u.raw_app_meta_data->>'provider', 'email')::text,
           p.name::text,
           p.role::text,
           u.created_at,
           COALESCE(o.cnt, 0)::bigint,
           COALESCE(o.paid, 0)::bigint,
           o.last_at
    FROM public.profiles p
    JOIN auth.users u ON u.id = p.id
    LEFT JOIN (
        SELECT user_id,
               COUNT(*)                                                        AS cnt,
               SUM(amount) FILTER (WHERE status IN ('paid','shipping','done')) AS paid,
               MAX(created_at)                                                 AS last_at
        FROM public.lifeart_orders
        WHERE tenant_id = lifeart
        GROUP BY user_id
    ) o ON o.user_id = p.id
    WHERE p.tenant_id = lifeart
    ORDER BY u.created_at DESC;
END;
$$;

-- ── ② 주문 목록 (주문자·상품·결제상태 조인) ──
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
DECLARE lifeart uuid := (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT o.id, o.created_at,
           p.name::text, u.email::text,
           pr.name::text, o.quantity, o.amount,
           o.status::text, o.shipping_status::text,
           pay.status::text, pay.pg_tid::text, o.shipping_address::text
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

-- ── ③ 특정 회원 주문 이력 (drill-down) ──
CREATE OR REPLACE FUNCTION public.lifeart_admin_get_member_orders(member_id uuid)
RETURNS TABLE (
    created_at   timestamptz,
    product_name text,
    quantity     integer,
    amount       bigint,
    status       text
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE lifeart uuid := (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT o.created_at, pr.name::text, o.quantity, o.amount, o.status::text
    FROM public.lifeart_orders o
    LEFT JOIN public.lifeart_products pr ON pr.id = o.product_id
    WHERE o.tenant_id = lifeart AND o.user_id = member_id
    ORDER BY o.created_at DESC;
END;
$$;

-- ── ④ 매출 요약 (대시보드) ──
CREATE OR REPLACE FUNCTION public.lifeart_admin_sales_summary()
RETURNS TABLE (
    total_sales  bigint,   -- 결제완료(paid/shipping/done) 매출 합
    paid_orders  bigint,   -- 결제완료 주문 수
    total_orders bigint,   -- 전체 주문 수(pending 포함)
    member_count bigint,   -- LifeArt 회원 수
    month_sales  bigint    -- 이번 달 결제완료 매출
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE lifeart uuid := (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr');
BEGIN
    IF NOT public.is_lifeart_admin() THEN RAISE EXCEPTION 'not_lifeart_admin'; END IF;
    RETURN QUERY
    SELECT
      COALESCE(SUM(o.amount) FILTER (WHERE o.status IN ('paid','shipping','done')), 0)::bigint,
      COUNT(*) FILTER (WHERE o.status IN ('paid','shipping','done'))::bigint,
      COUNT(*)::bigint,
      (SELECT COUNT(*) FROM public.profiles WHERE tenant_id = lifeart)::bigint,
      COALESCE(SUM(o.amount) FILTER (
        WHERE o.status IN ('paid','shipping','done')
          AND o.created_at >= date_trunc('month', now())), 0)::bigint
    FROM public.lifeart_orders o
    WHERE o.tenant_id = lifeart;
END;
$$;

GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_users()             TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_orders()            TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_member_orders(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_sales_summary()         TO authenticated;

-- ── 검증 ──
SELECT proname FROM pg_proc
WHERE proname IN ('lifeart_admin_get_users','lifeart_admin_get_orders',
                  'lifeart_admin_get_member_orders','lifeart_admin_sales_summary')
ORDER BY proname;
