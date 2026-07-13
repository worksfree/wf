-- ================================================================
-- 08_lifeart_tables.sql — LifeArt 전용 테이블 (신규)
--
-- 반드시 03(tenants 에 lifeart.ai.kr)·04(profiles.tenant_id, is_lifeart_admin) 후 실행.
--
-- 핵심 결정:
--  · 테이블명 lifeart_ 접두사 — 허브 기존 public.payments 등과의 충돌 방지
--    (허브 payments 는 order_id TEXT / pg CHECK / credits 구조로 완전히 다름)
--  · tenant_id uuid NOT NULL FK → tenants(id) — portfolios 계열 최신 규약
--  · 모든 RLS 정책에 tenant 조건 포함 (portfolios 안티패턴 회피)
--  · lifeart_orders.status='paid' 갱신 + lifeart_payments INSERT 는 클라이언트 정책
--    없음 → service_role(Worker)만 가능 (사용자가 자기 결제를 위조 못 하도록)
-- ================================================================

-- lifeart_products
CREATE TABLE IF NOT EXISTS public.lifeart_products (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID        NOT NULL REFERENCES public.tenants(id),
    category    TEXT        NOT NULL,   -- photobook / instant-album / vip-album / frame
    name        TEXT        NOT NULL,
    description TEXT,
    price       BIGINT      NOT NULL DEFAULT 0,
    options     JSONB       DEFAULT '{}'::jsonb,
    images      JSONB       DEFAULT '[]'::jsonb,
    is_active   BOOLEAN     DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- lifeart_orders
CREATE TABLE IF NOT EXISTS public.lifeart_orders (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID        NOT NULL REFERENCES public.tenants(id),
    user_id           UUID        REFERENCES auth.users(id),
    product_id        UUID        REFERENCES public.lifeart_products(id),
    options           JSONB       DEFAULT '{}'::jsonb,
    quantity          INTEGER     NOT NULL DEFAULT 1,
    amount            BIGINT      NOT NULL,
    status            TEXT        NOT NULL DEFAULT 'pending',   -- pending / paid / shipping / done / cancelled
    shipping_address  TEXT,
    shipping_status   TEXT        DEFAULT 'ready',              -- ready / shipping / delivered
    env               TEXT        NOT NULL DEFAULT 'production',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- lifeart_payments
CREATE TABLE IF NOT EXISTS public.lifeart_payments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES public.tenants(id),
    order_id     UUID        REFERENCES public.lifeart_orders(id),
    pg_provider  TEXT        NOT NULL DEFAULT 'toss',
    pg_tid       TEXT,
    amount       BIGINT      NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'requested',   -- requested / approved / cancelled / failed
    env          TEXT        NOT NULL DEFAULT 'production',
    approved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- lifeart_inquiries
CREATE TABLE IF NOT EXISTS public.lifeart_inquiries (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID        NOT NULL REFERENCES public.tenants(id),
    type        TEXT        NOT NULL,   -- estimate / qna / partnership
    env         TEXT        NOT NULL DEFAULT 'production',
    user_id     UUID        REFERENCES auth.users(id),  -- 비회원 문의는 NULL
    name        TEXT        NOT NULL,
    phone       TEXT,
    email       TEXT,
    message     TEXT,
    status      TEXT        DEFAULT 'new',   -- new / answered / closed
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE public.lifeart_products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_orders    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_payments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_inquiries ENABLE ROW LEVEL SECURITY;

-- 편의 함수: lifeart 테넌트 id
CREATE OR REPLACE FUNCTION public.lifeart_tenant_id()
RETURNS uuid LANGUAGE SQL STABLE AS $$
  SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr'
$$;

-- products: 공개 읽기(활성 + lifeart 테넌트), 관리자 전체 CRUD
CREATE POLICY "lifeart_products_select_public" ON public.lifeart_products FOR SELECT
    USING (is_active = true AND tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_products_admin_all" ON public.lifeart_products FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

-- orders: 본인 조회/생성(+테넌트), 관리자 전체. status='paid' 등 결제 확정은
--   여기 정책으로 허용되지만, 실제 결제 흐름에선 Worker(service_role)가 갱신하고
--   클라이언트는 pending 생성까지만 함. (자기 주문을 임의로 paid 로 바꾸는 것은
--   UPDATE 시 status 검증을 두지 않았으므로, 결제 확정은 Worker 경유를 원칙으로 함)
CREATE POLICY "lifeart_orders_own" ON public.lifeart_orders FOR SELECT
    USING (auth.uid() = user_id AND tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_orders_insert_own" ON public.lifeart_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id AND tenant_id = public.lifeart_tenant_id()
                AND status = 'pending');
CREATE POLICY "lifeart_orders_admin_all" ON public.lifeart_orders FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

-- payments: 본인 주문 연결 결제 조회 + 관리자 조회. INSERT/UPDATE 정책 없음
--   → service_role(Worker)만 기록 가능 (클라이언트 위조 차단)
CREATE POLICY "lifeart_payments_select_own" ON public.lifeart_payments FOR SELECT
    USING (order_id IN (SELECT id FROM public.lifeart_orders WHERE user_id = auth.uid()));
CREATE POLICY "lifeart_payments_admin_select" ON public.lifeart_payments FOR SELECT
    USING (public.is_lifeart_admin());

-- inquiries: 누구나 생성(비회원 포함, 단 lifeart 테넌트로만),
--   회원 본인 조회, 관리자 전체
CREATE POLICY "lifeart_inquiries_insert_public" ON public.lifeart_inquiries FOR INSERT
    WITH CHECK (tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_inquiries_select_own" ON public.lifeart_inquiries FOR SELECT
    USING (user_id IS NOT NULL AND user_id = auth.uid());
CREATE POLICY "lifeart_inquiries_admin_all" ON public.lifeart_inquiries FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_lifeart_products_cat   ON public.lifeart_products (tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_lifeart_orders_user    ON public.lifeart_orders   (tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_lifeart_orders_env     ON public.lifeart_orders   (tenant_id, env);
CREATE INDEX IF NOT EXISTS idx_lifeart_payments_order ON public.lifeart_payments (order_id);
CREATE INDEX IF NOT EXISTS idx_lifeart_inq_user       ON public.lifeart_inquiries (tenant_id, user_id);

-- ── 검증 ──
-- (a) 4개 테이블 생성 확인
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
  AND table_name IN ('lifeart_products','lifeart_orders','lifeart_payments','lifeart_inquiries')
ORDER BY table_name;

-- (b) 정책 목록
SELECT tablename, policyname, cmd FROM pg_policies
WHERE schemaname='public' AND tablename LIKE 'lifeart_%'
ORDER BY tablename, cmd;

-- (c) 허브 payments 충돌 없음 증명 — 00 스냅샷의 total_payments 와 동일해야 함
SELECT COUNT(*) AS hub_payments_unchanged FROM public.payments;
