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
    user_id     UUID        REFERENCES auth.users(id),  -- 비회원 문의는 NULL, 마이페이지 조회용
    name        TEXT        NOT NULL,
    phone       TEXT,
    email       TEXT,
    message     TEXT,
    status      TEXT        DEFAULT 'new',   -- new / answered / closed
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 주의: auth.users는 이 Supabase 프로젝트를 공유하는 모든 테넌트(WorksFree 본사이트,
-- auction 등)가 함께 쓰는 전역 테이블이다. 여기에 전역 트리거를 걸면 다른 테넌트의
-- 가입 시에도 lifeart profiles 행이 잘못 생성된다. 그래서 트리거 대신 클라이언트에서
-- 로그인/가입 성공 시 upsert로 profiles를 생성한다 (assets/auth.js의 ensureProfile 참고).

-- RLS 활성화
ALTER TABLE public.profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inquiries ENABLE ROW LEVEL SECURITY;

-- profiles: 본인 행만
CREATE POLICY "profiles_own_row" ON public.profiles
    USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- lifeart 관리자 여부 확인 (profiles.role = 'admin')
CREATE OR REPLACE FUNCTION public.is_lifeart_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND tenant_id = 'lifeart' AND role = 'admin'
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- products: 공개 읽기, 관리자는 전체 CRUD
CREATE POLICY "products_select_public" ON public.products FOR SELECT USING (is_active = true);
CREATE POLICY "products_admin_all" ON public.products FOR ALL
    USING (public.is_lifeart_admin()) WITH CHECK (public.is_lifeart_admin());

-- orders: 본인 주문만 조회/생성, 관리자는 전체 조회+수정(배송상태 등)
CREATE POLICY "orders_own_row" ON public.orders
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "orders_admin_all" ON public.orders FOR ALL
    USING (public.is_lifeart_admin()) WITH CHECK (public.is_lifeart_admin());

-- payments: 본인 주문에 연결된 결제만 조회 (쓰기는 서버에서 service_role로만 처리), 관리자는 전체 조회
CREATE POLICY "payments_select_own" ON public.payments FOR SELECT
    USING (order_id IN (SELECT id FROM public.orders WHERE user_id = auth.uid()));
CREATE POLICY "payments_admin_select" ON public.payments FOR SELECT
    USING (public.is_lifeart_admin());

-- inquiries: 누구나 생성 가능(비회원 문의 포함)
CREATE POLICY "inquiries_insert_public" ON public.inquiries FOR INSERT WITH CHECK (true);
-- inquiries: 로그인한 회원은 본인이 남긴 문의만 마이페이지에서 조회, 관리자는 전체 조회+답변상태 변경
CREATE POLICY "inquiries_select_own" ON public.inquiries FOR SELECT
    USING (user_id IS NOT NULL AND user_id = auth.uid());
CREATE POLICY "inquiries_admin_all" ON public.inquiries FOR ALL
    USING (public.is_lifeart_admin()) WITH CHECK (public.is_lifeart_admin());

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_products_category ON public.products (tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_orders_user        ON public.orders   (tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_orders_env         ON public.orders   (tenant_id, env);
CREATE INDEX IF NOT EXISTS idx_payments_order     ON public.payments (order_id);
