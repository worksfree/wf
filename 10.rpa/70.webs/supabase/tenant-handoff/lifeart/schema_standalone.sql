-- ================================================================
-- LifeArt 독립 배포용 스키마 (standalone) — v2 (2026-07-22 전면 재작성)
--
-- 용도: 고객사가 공유 DB를 떠나 자기 소유의 새 Supabase 프로젝트로
--       LifeArt를 독립 운영할 때, 빈 프로젝트에서 이 파일 하나만 실행하면
--       현재 운영 중인 모든 기능(쇼핑몰 프론트 + 관리자 콘솔)이 그대로 동작합니다.
--
-- v1(구버전) 대비 변경: 당시 관리자 콘솔이 아직 초기 버전이라
--   lifeart_notices/faqs/press/hero_slides 4개 테이블과 관리자 RPC 5종이
--   전부 누락돼 있었음. 이번에 실제 운영 스키마(마이그레이션 08~20)와
--   1:1 대조해 빠짐없이 반영함.
--
-- 공유본과의 차이 (단일 테넌트라 단순화):
--   · tenant_id 컬럼 / tenants FK 전부 제거 (테넌트가 하나뿐이므로 불필요)
--   · is_lifeart_admin() → is_admin() 하나로 통합 (profiles.role='admin'만 확인)
--   · lifeart_tenant_id() 함수 불필요 (테넌트 개념 자체가 없음)
--   · profiles 는 이 프로젝트 전용이므로 여기서 생성 (공유본에선 허브 소유라 안 만듦)
--
-- 회원 데이터(auth.users)는 export_lifeart_data.sql → import_lifeart_data.sql 로 별도 이관.
-- 실행 순서: ① 이 파일 실행(빈 스키마 생성) → ② import_lifeart_data.sql 로 데이터 주입.
-- ================================================================

-- ── profiles (이 독립 프로젝트 전용) ──────────────────────────────
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
-- ★ 운영 중인 공유 DB(complete_db_setup.sql)의 실제 정책을 그대로 복제 — 즉흥적으로
--   더 엄격한 정책을 새로 짜지 않음("이관은 현재 동작의 완전 복제"가 원칙).
--   참고(별도 보안 검토 대상, 이번 이관 범위 밖): 이 정책은 role 컬럼도 본인이 직접
--   UPDATE 가능하게 열려있음 — 클라이언트가 role='admin' 으로 자가 승격을 시도할 수
--   있는 이론적 여지가 있으나, 이는 원본 운영 시스템에도 동일하게 존재하는 특성이라
--   이관 스크립트에서 임의로 바꾸지 않음.
DROP POLICY IF EXISTS "profiles_own" ON public.profiles;
CREATE POLICY "profiles_own" ON public.profiles
    FOR ALL USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin');
$$;
GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;

-- 관리자는 모든 프로필 조회 가능(회원 관리 화면용)
DROP POLICY IF EXISTS "profiles_admin_select" ON public.profiles;
CREATE POLICY "profiles_admin_select" ON public.profiles
    FOR SELECT USING (public.is_admin());

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

-- ── ① products ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_products (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    category    TEXT        NOT NULL,   -- photobook / instant-album / vip-album / frame
    name        TEXT        NOT NULL,
    description TEXT,
    price       BIGINT      NOT NULL DEFAULT 0,
    options     JSONB       DEFAULT '{}'::jsonb,
    images      JSONB       DEFAULT '[]'::jsonb,
    is_active   BOOLEAN     DEFAULT TRUE,
    is_addon    BOOLEAN     NOT NULL DEFAULT FALSE,   -- 옵션상품(추가구성상품) 여부 — category 안에서 스코프
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── ② orders ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_orders (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES auth.users(id),
    product_id        UUID        REFERENCES public.lifeart_products(id),
    options           JSONB       DEFAULT '{}'::jsonb,
    quantity          INTEGER     NOT NULL DEFAULT 1,
    amount            BIGINT      NOT NULL,
    status            TEXT        NOT NULL DEFAULT 'pending',   -- pending/paid/shipping/done/cancelled
    shipping_address  TEXT,
    shipping_status   TEXT        DEFAULT 'ready',              -- ready/shipping/delivered
    env               TEXT        NOT NULL DEFAULT 'production',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── ③ payments ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_payments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID        REFERENCES public.lifeart_orders(id),
    pg_provider  TEXT        NOT NULL DEFAULT 'toss',
    pg_tid       TEXT,
    amount       BIGINT      NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'requested',   -- requested/approved/cancelled/failed
    env          TEXT        NOT NULL DEFAULT 'production',
    approved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── ④ inquiries (문의 + 관리자 답변, 11_lifeart_om.sql 반영) ──────
CREATE TABLE IF NOT EXISTS public.lifeart_inquiries (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    type           TEXT        NOT NULL,   -- estimate / qna / partnership
    env            TEXT        NOT NULL DEFAULT 'production',
    user_id        UUID        REFERENCES auth.users(id),  -- 비회원 문의는 NULL
    name           TEXT        NOT NULL,
    phone          TEXT,
    email          TEXT,
    message        TEXT,
    status         TEXT        DEFAULT 'new',   -- new / answered / closed
    answer         TEXT,
    answered_at    TIMESTAMPTZ,
    answered_by    UUID        REFERENCES auth.users(id),
    email_sent_at  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── ⑤ notices (11_lifeart_om.sql) ────────────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_notices (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title        TEXT        NOT NULL,
    body         TEXT        NOT NULL DEFAULT '',
    is_published BOOLEAN     NOT NULL DEFAULT TRUE,
    pinned       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── ⑥ faqs (11_lifeart_om.sql) ───────────────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_faqs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    question     TEXT        NOT NULL,
    answer       TEXT        NOT NULL DEFAULT '',
    sort_order   INTEGER     NOT NULL DEFAULT 0,
    is_published BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── ⑦ press (12_lifeart_press.sql) ───────────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_press (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title        TEXT        NOT NULL,
    outlet       TEXT        NOT NULL DEFAULT '',
    summary      TEXT        NOT NULL DEFAULT '',
    link_url     TEXT,
    published_on DATE,
    is_published BOOLEAN     NOT NULL DEFAULT TRUE,
    pinned       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── ⑧ hero_slides (16_lifeart_hero.sql) ──────────────────────
CREATE TABLE IF NOT EXISTS public.lifeart_hero_slides (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    image_url  TEXT        NOT NULL,
    caption    TEXT,
    sort_order INTEGER     NOT NULL DEFAULT 0,
    is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── RLS 활성화 (8개 전 테이블) ────────────────────────────────
ALTER TABLE public.lifeart_products     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_orders       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_payments     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_inquiries    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_notices      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_faqs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_press        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_hero_slides  ENABLE ROW LEVEL SECURITY;

-- products
CREATE POLICY "products_public" ON public.lifeart_products FOR SELECT USING (is_active = true);
CREATE POLICY "products_admin"  ON public.lifeart_products FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- orders (결제 확정 UPDATE 는 정책 없음 → service_role/Worker 전용, 12_lifeart_om.sql과 동일 원칙)
CREATE POLICY "orders_own" ON public.lifeart_orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "orders_insert_own" ON public.lifeart_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id AND status = 'pending');
CREATE POLICY "orders_admin" ON public.lifeart_orders FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- payments (INSERT/UPDATE 정책 없음 → service_role(Worker) 전용, 클라이언트 위조 차단)
CREATE POLICY "payments_own" ON public.lifeart_payments FOR SELECT
    USING (order_id IN (SELECT id FROM public.lifeart_orders WHERE user_id = auth.uid()));
CREATE POLICY "payments_admin" ON public.lifeart_payments FOR SELECT USING (public.is_admin());

-- inquiries (누구나 생성 가능·본인 조회·관리자 전체, 11_lifeart_om.sql과 동일)
CREATE POLICY "inq_insert" ON public.lifeart_inquiries FOR INSERT WITH CHECK (true);
CREATE POLICY "inq_own" ON public.lifeart_inquiries FOR SELECT
    USING (user_id IS NOT NULL AND user_id = auth.uid());
CREATE POLICY "inq_admin" ON public.lifeart_inquiries FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- notices (공개 읽기 + 관리자 CRUD)
CREATE POLICY "notices_public" ON public.lifeart_notices FOR SELECT USING (is_published = true);
CREATE POLICY "notices_admin"  ON public.lifeart_notices FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- faqs (공개 읽기 + 관리자 CRUD)
CREATE POLICY "faqs_public" ON public.lifeart_faqs FOR SELECT USING (is_published = true);
CREATE POLICY "faqs_admin"  ON public.lifeart_faqs FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- press (공개 읽기 + 관리자 CRUD)
CREATE POLICY "press_public" ON public.lifeart_press FOR SELECT USING (is_published = true);
CREATE POLICY "press_admin"  ON public.lifeart_press FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- hero_slides (공개 읽기[활성만] + 관리자 CRUD)
CREATE POLICY "hero_public" ON public.lifeart_hero_slides FOR SELECT USING (is_active = true);
CREATE POLICY "hero_admin"  ON public.lifeart_hero_slides FOR ALL
    USING (public.is_admin()) WITH CHECK (public.is_admin());

-- ── 인덱스 ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_la_products_cat   ON public.lifeart_products (category);
CREATE INDEX IF NOT EXISTS idx_la_orders_user    ON public.lifeart_orders (user_id);
CREATE INDEX IF NOT EXISTS idx_la_payments_ord   ON public.lifeart_payments (order_id);
CREATE INDEX IF NOT EXISTS idx_la_inq_user       ON public.lifeart_inquiries (user_id);
CREATE INDEX IF NOT EXISTS idx_la_notices_pub    ON public.lifeart_notices (is_published, pinned, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_la_faqs_sort      ON public.lifeart_faqs (is_published, sort_order);
CREATE INDEX IF NOT EXISTS idx_la_press_pub      ON public.lifeart_press (is_published, pinned, published_on DESC);
CREATE INDEX IF NOT EXISTS idx_la_hero_order     ON public.lifeart_hero_slides (is_active, sort_order);

-- ── 관리자 콘솔 RPC 5종 (14/15/18 마이그레이션의 최종본을 단일 테넌트로 단순화) ──
-- 브라우저(anon/authenticated)는 auth.users 를 직접 못 읽으므로 SECURITY DEFINER RPC 경유.

-- ① 회원 목록 + 구매 집계
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
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
#variable_conflict use_column
BEGIN
    IF NOT public.is_admin() THEN RAISE EXCEPTION 'not_admin'; END IF;
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
               COUNT(*)                                                             AS cnt,
               SUM(lo.amount) FILTER (WHERE lo.status IN ('paid','shipping','done')) AS paid,
               MAX(lo.created_at)                                                    AS last_at
        FROM public.lifeart_orders lo
        GROUP BY lo.user_id
    ) agg ON agg.uid = p.id
    ORDER BY u.created_at DESC;
END;
$$;

-- ② 주문 목록 (주문자·상품·결제상태 조인)
CREATE OR REPLACE FUNCTION public.lifeart_admin_get_orders()
RETURNS TABLE (
    id                uuid,
    created_at        timestamptz,
    member_name       text,
    member_email      text,
    product_name      text,
    quantity          integer,
    amount            bigint,
    status            text,
    shipping_status   text,
    pay_status        text,
    pg_tid            text,
    shipping_address  text
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
#variable_conflict use_column
BEGIN
    IF NOT public.is_admin() THEN RAISE EXCEPTION 'not_admin'; END IF;
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
    ORDER BY o.created_at DESC;
END;
$$;

-- ③ 특정 회원 주문 이력 (drill-down)
CREATE OR REPLACE FUNCTION public.lifeart_admin_get_member_orders(member_id uuid)
RETURNS TABLE (
    created_at   timestamptz,
    product_name text,
    quantity     integer,
    amount       bigint,
    status       text
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    IF NOT public.is_admin() THEN RAISE EXCEPTION 'not_admin'; END IF;
    RETURN QUERY
    SELECT o.created_at, pr.name::text, o.quantity, o.amount, o.status::text
    FROM public.lifeart_orders o
    LEFT JOIN public.lifeart_products pr ON pr.id = o.product_id
    WHERE o.user_id = member_id
    ORDER BY o.created_at DESC;
END;
$$;

-- ④ 매출 요약 (대시보드)
CREATE OR REPLACE FUNCTION public.lifeart_admin_sales_summary()
RETURNS TABLE (
    total_sales  bigint,
    paid_orders  bigint,
    total_orders bigint,
    member_count bigint,
    month_sales  bigint
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    IF NOT public.is_admin() THEN RAISE EXCEPTION 'not_admin'; END IF;
    RETURN QUERY
    SELECT
      COALESCE(SUM(o.amount) FILTER (WHERE o.status IN ('paid','shipping','done')), 0)::bigint,
      COUNT(*) FILTER (WHERE o.status IN ('paid','shipping','done'))::bigint,
      COUNT(*)::bigint,
      (SELECT COUNT(*) FROM public.profiles)::bigint,
      COALESCE(SUM(o.amount) FILTER (
        WHERE o.status IN ('paid','shipping','done')
          AND o.created_at >= date_trunc('month', now())), 0)::bigint
    FROM public.lifeart_orders o;
END;
$$;

-- ⑤ 회원 역할 변경 (member/admin 만 허용)
CREATE OR REPLACE FUNCTION public.lifeart_admin_set_role(target_id uuid, new_role text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE updated int;
BEGIN
    IF NOT public.is_admin() THEN RETURN 'error: not_admin'; END IF;
    IF new_role NOT IN ('member', 'admin') THEN RETURN 'error: invalid_role'; END IF;
    UPDATE public.profiles SET role = new_role WHERE id = target_id;
    GET DIAGNOSTICS updated = ROW_COUNT;
    IF updated = 0 THEN RETURN 'error: user_not_found'; END IF;
    RETURN 'ok';
END;
$$;

GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_users()             TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_orders()            TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_get_member_orders(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_sales_summary()         TO authenticated;
GRANT EXECUTE ON FUNCTION public.lifeart_admin_set_role(uuid, text)    TO authenticated;

-- ── 검증 ──
-- (a) 테이블 8종 전부 생성됐는지
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'lifeart_%'
ORDER BY table_name;
-- 기대: lifeart_faqs, lifeart_hero_slides, lifeart_inquiries, lifeart_notices,
--       lifeart_orders, lifeart_payments, lifeart_press, lifeart_products  (8행)

-- (b) RPC 5종 전부 생성됐는지
SELECT proname FROM pg_proc
WHERE proname IN ('lifeart_admin_get_users','lifeart_admin_get_orders',
                   'lifeart_admin_get_member_orders','lifeart_admin_sales_summary',
                   'lifeart_admin_set_role')
ORDER BY proname;
-- 기대: 5행

-- (c) RLS 정책 전체 목록 (테이블당 최소 1개 이상이어야 함)
SELECT tablename, COUNT(*) AS policy_count FROM pg_policies
WHERE tablename LIKE 'lifeart_%' OR tablename = 'profiles'
GROUP BY tablename ORDER BY tablename;
