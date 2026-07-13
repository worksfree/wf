-- ================================================================
-- LifeArt 독립 배포용 스키마 (standalone)
--
-- 용도: 고객사가 공유 DB를 떠나 자기 소유의 새 Supabase 프로젝트로
--       LifeArt를 독립 운영할 때, 빈 프로젝트에서 이 파일 하나만 실행하면
--       LifeArt에 필요한 테이블/정책/함수가 전부 생성됩니다.
--
-- 공유본과의 차이 (단일 테넌트라 단순화):
--   · tenant_id 컬럼 / tenants FK 제거 (테넌트가 하나뿐이므로 불필요)
--   · is_lifeart_admin() → profiles.role='admin' 만 확인 (테넌트 조건 제거)
--   · profiles 는 이 프로젝트 전용이므로 여기서 생성 (공유본에선 허브 소유라 안 만듦)
--
-- 회원 데이터는 export_lifeart_data.sql 로 별도 이관.
-- ================================================================

-- profiles (이 독립 프로젝트에선 LifeArt 전용)
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT,
    phone       TEXT,
    email       TEXT,
    role        TEXT        NOT NULL DEFAULT 'member' CHECK (role IN ('member','admin')),
    agreed_at   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "profiles_own" ON public.profiles
    USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin');
$$;

-- 신규 가입 시 profiles 자동 생성 (독립 프로젝트라 전역 트리거 안전)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name, phone)
  VALUES (NEW.id, NEW.email,
          NEW.raw_user_meta_data->>'name',
          NEW.raw_user_meta_data->>'phone')
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END; $$;
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- products
CREATE TABLE IF NOT EXISTS public.lifeart_products (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    category    TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    description TEXT,
    price       BIGINT      NOT NULL DEFAULT 0,
    options     JSONB       DEFAULT '{}'::jsonb,
    images      JSONB       DEFAULT '[]'::jsonb,
    is_active   BOOLEAN     DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- orders
CREATE TABLE IF NOT EXISTS public.lifeart_orders (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES auth.users(id),
    product_id        UUID        REFERENCES public.lifeart_products(id),
    options           JSONB       DEFAULT '{}'::jsonb,
    quantity          INTEGER     NOT NULL DEFAULT 1,
    amount            BIGINT      NOT NULL,
    status            TEXT        NOT NULL DEFAULT 'pending',
    shipping_address  TEXT,
    shipping_status   TEXT        DEFAULT 'ready',
    env               TEXT        NOT NULL DEFAULT 'production',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- payments
CREATE TABLE IF NOT EXISTS public.lifeart_payments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID        REFERENCES public.lifeart_orders(id),
    pg_provider  TEXT        NOT NULL DEFAULT 'toss',
    pg_tid       TEXT,
    amount       BIGINT      NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'requested',
    env          TEXT        NOT NULL DEFAULT 'production',
    approved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- inquiries
CREATE TABLE IF NOT EXISTS public.lifeart_inquiries (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    type        TEXT        NOT NULL,
    env         TEXT        NOT NULL DEFAULT 'production',
    user_id     UUID        REFERENCES auth.users(id),
    name        TEXT        NOT NULL,
    phone       TEXT,
    email       TEXT,
    message     TEXT,
    status      TEXT        DEFAULT 'new',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.lifeart_products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_orders    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_payments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_inquiries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "products_public" ON public.lifeart_products FOR SELECT USING (is_active = true);
CREATE POLICY "products_admin"  ON public.lifeart_products FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY "orders_own" ON public.lifeart_orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "orders_insert_own" ON public.lifeart_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id AND status = 'pending');
CREATE POLICY "orders_admin" ON public.lifeart_orders FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE POLICY "payments_own" ON public.lifeart_payments FOR SELECT
    USING (order_id IN (SELECT id FROM public.lifeart_orders WHERE user_id = auth.uid()));
CREATE POLICY "payments_admin" ON public.lifeart_payments FOR SELECT USING (public.is_admin());
-- payments INSERT/UPDATE 정책 없음 → service_role(Worker)만 기록

CREATE POLICY "inq_insert" ON public.lifeart_inquiries FOR INSERT WITH CHECK (true);
CREATE POLICY "inq_own" ON public.lifeart_inquiries FOR SELECT
    USING (user_id IS NOT NULL AND user_id = auth.uid());
CREATE POLICY "inq_admin" ON public.lifeart_inquiries FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

CREATE INDEX IF NOT EXISTS idx_la_products_cat  ON public.lifeart_products (category);
CREATE INDEX IF NOT EXISTS idx_la_orders_user   ON public.lifeart_orders (user_id);
CREATE INDEX IF NOT EXISTS idx_la_payments_ord  ON public.lifeart_payments (order_id);
CREATE INDEX IF NOT EXISTS idx_la_inq_user      ON public.lifeart_inquiries (user_id);
