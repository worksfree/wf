-- ================================================================
-- WorksFree 경매정보 — Supabase 테이블 설정
-- Supabase Dashboard → SQL Editor 에서 실행
-- ================================================================

-- auction_items: 경매 물건 정보 (KV data:{tenant} 대체)
CREATE TABLE IF NOT EXISTS public.auction_items (
    id           TEXT             NOT NULL,
    tenant_id    TEXT             NOT NULL DEFAULT 'worksfree',
    case_number  TEXT,
    court        TEXT,
    type         TEXT,                        -- apartment / house / commercial / land / other
    sido         TEXT,
    gu           TEXT,
    dong         TEXT,
    address      TEXT,
    area         NUMERIC,
    app          BIGINT,                      -- 감정가
    min_p        BIGINT,                      -- 최저입찰가
    avg_t        BIGINT,                      -- 예상낙찰가
    fc           INTEGER          DEFAULT 0,  -- 유찰횟수
    bid_date     DATE,
    pred         INTEGER,                     -- 예측 낙찰가율 (%)
    detail_url   TEXT,
    lat          DOUBLE PRECISION,
    lng          DOUBLE PRECISION,
    geocoded_at  TIMESTAMPTZ,
    is_real      BOOLEAN          DEFAULT TRUE,
    created_at   TIMESTAMPTZ      DEFAULT NOW(),
    updated_at   TIMESTAMPTZ      DEFAULT NOW(),
    PRIMARY KEY (id, tenant_id)
);

-- auction_meta: 크롤링 상태 (KV meta:{tenant} 대체)
CREATE TABLE IF NOT EXISTS public.auction_meta (
    tenant_id       TEXT        PRIMARY KEY,
    status          TEXT        DEFAULT 'idle',
    next_page       INTEGER     DEFAULT 1,
    count           INTEGER     DEFAULT 0,
    total_available INTEGER     DEFAULT 0,
    has_more        BOOLEAN     DEFAULT FALSE,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    generated_at    TIMESTAMPTZ,
    error           TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 활성화
ALTER TABLE public.auction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auction_meta  ENABLE ROW LEVEL SECURITY;

-- anon 키: SELECT 허용 (공개 경매 데이터)
CREATE POLICY "auction_items_select_public"
    ON public.auction_items FOR SELECT USING (true);

CREATE POLICY "auction_meta_select_public"
    ON public.auction_meta FOR SELECT USING (true);

-- service_role 키는 RLS bypass — 별도 정책 불필요

-- 인덱스 (필터/정렬 최적화)
CREATE INDEX IF NOT EXISTS idx_auction_items_tenant
    ON public.auction_items (tenant_id);
CREATE INDEX IF NOT EXISTS idx_auction_items_bid_date
    ON public.auction_items (tenant_id, bid_date);
CREATE INDEX IF NOT EXISTS idx_auction_items_type
    ON public.auction_items (tenant_id, type);
CREATE INDEX IF NOT EXISTS idx_auction_items_sido
    ON public.auction_items (tenant_id, sido);
CREATE INDEX IF NOT EXISTS idx_auction_items_geo
    ON public.auction_items (tenant_id, lat, lng)
    WHERE lat IS NOT NULL AND lng IS NOT NULL;
