-- ================================================================
-- LifeArt — Supabase 스키마 (1일차 기획 및 설계 산출물)
-- 기존 Supabase 프로젝트를 그대로 사용, tenant_id + RLS로 격리
-- (WorksFree auction 프로젝트와 동일한 멀티테넌시 패턴)
-- Supabase Dashboard → SQL Editor 에서 실행
-- ================================================================

-- profiles: 회원 정보 (auth.users 확장)
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id   TEXT        NOT NULL DEFAULT 'lifeart',
    name        TEXT,
    phone       TEXT,
    role        TEXT        NOT NULL DEFAULT 'member',   -- member / admin
    agreed_at   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- products: 상품 (포토북 / 삽입식앨범 / VIP앨범 / 액자)
CREATE TABLE IF NOT EXISTS public.products (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT        NOT NULL DEFAULT 'lifeart',
    category    TEXT        NOT NULL,   -- photobook / instant-album / vip-album / frame
    name        TEXT        NOT NULL,
    description TEXT,
    price       BIGINT      NOT NULL DEFAULT 0,
    options     JSONB       DEFAULT '{}'::jsonb,   -- 사이즈/재질/커버 등
    images      JSONB       DEFAULT '[]'::jsonb,
    is_active   BOOLEAN     DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- orders: 주문
CREATE TABLE IF NOT EXISTS public.orders (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         TEXT        NOT NULL DEFAULT 'lifeart',
    user_id           UUID        REFERENCES auth.users(id),
    product_id        UUID        REFERENCES public.products(id),
    options           JSONB       DEFAULT '{}'::jsonb,
    quantity          INTEGER     NOT NULL DEFAULT 1,
    amount            BIGINT      NOT NULL,
    status            TEXT        NOT NULL DEFAULT 'pending',  -- pending / paid / shipping / done / cancelled
    shipping_address  TEXT,
    shipping_status   TEXT        DEFAULT 'ready',             -- ready / shipping / delivered
    env               TEXT        NOT NULL DEFAULT 'production', -- test-lifeart / production 환경 격리
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- payments: 결제 (토스페이먼츠 연동)
CREATE TABLE IF NOT EXISTS public.payments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    TEXT        NOT NULL DEFAULT 'lifeart',
    order_id     UUID        REFERENCES public.orders(id),
    pg_provider  TEXT        NOT NULL DEFAULT 'toss',
    pg_tid       TEXT,                          -- 토스 paymentKey
    amount       BIGINT      NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'requested',  -- requested / approved / cancelled / failed
    env          TEXT        NOT NULL DEFAULT 'production',
    approved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- inquiries: 1:1 문의 / 견적 문의
CREATE TABLE IF NOT EXISTS public.inquiries (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT        NOT NULL DEFAULT 'lifeart',
    type        TEXT        NOT NULL,   -- estimate / qna / partnership
    env         TEXT        NOT NULL DEFAULT 'production',
    name        TEXT        NOT NULL,
    phone       TEXT,
    email       TEXT,
    message     TEXT,
    status      TEXT        DEFAULT 'new',   -- new / answered / closed
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 활성화
ALTER TABLE public.profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inquiries ENABLE ROW LEVEL SECURITY;

-- profiles: 본인 행만
CREATE POLICY "profiles_own_row" ON public.profiles
    USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- products: 공개 읽기, 쓰기는 service_role(관리자 API)만
CREATE POLICY "products_select_public" ON public.products FOR SELECT USING (is_active = true);

-- orders: 본인 주문만 조회/생성
CREATE POLICY "orders_own_row" ON public.orders
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- payments: 본인 주문에 연결된 결제만 조회 (쓰기는 서버에서 service_role로만 처리)
CREATE POLICY "payments_select_own" ON public.payments FOR SELECT
    USING (order_id IN (SELECT id FROM public.orders WHERE user_id = auth.uid()));

-- inquiries: 누구나 생성 가능(비회원 문의), 조회는 관리자만 — service_role로 관리자 페이지에서 처리
CREATE POLICY "inquiries_insert_public" ON public.inquiries FOR INSERT WITH CHECK (true);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_products_category ON public.products (tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_orders_user        ON public.orders   (tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_orders_env         ON public.orders   (tenant_id, env);
CREATE INDEX IF NOT EXISTS idx_payments_order     ON public.payments (order_id);
