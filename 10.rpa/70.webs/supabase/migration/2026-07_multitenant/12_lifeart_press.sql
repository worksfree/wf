-- ================================================================
-- 12_lifeart_press.sql — LifeArt O&M 보도자료 관리
--
-- 11 이후 실행. 관리자 콘솔에서 보도자료·수상이력을 CRUD 하고,
-- 공개 /about/press/ 페이지가 게시된 항목을 읽는다.
-- 규약은 lifeart_notices 와 동일(테넌트 스코프 + is_lifeart_admin CRUD).
-- ================================================================

CREATE TABLE IF NOT EXISTS public.lifeart_press (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES public.tenants(id),
    title        TEXT        NOT NULL,
    outlet       TEXT        NOT NULL DEFAULT '',   -- 매체/출처 (예: 매일경제, KBS)
    summary      TEXT        NOT NULL DEFAULT '',   -- 요약/본문
    link_url     TEXT,                              -- 원문 링크 (선택)
    published_on DATE,                              -- 보도일 (선택)
    is_published BOOLEAN     NOT NULL DEFAULT TRUE,
    pinned       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.lifeart_press ENABLE ROW LEVEL SECURITY;

-- 게시된 것 공개 읽기, 관리자 전체 CRUD (테넌트 스코프)
-- (재실행 안전: 기존 정책 있으면 먼저 제거)
DROP POLICY IF EXISTS "lifeart_press_public" ON public.lifeart_press;
DROP POLICY IF EXISTS "lifeart_press_admin"  ON public.lifeart_press;
CREATE POLICY "lifeart_press_public" ON public.lifeart_press FOR SELECT
    USING (is_published = true AND tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_press_admin" ON public.lifeart_press FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

CREATE INDEX IF NOT EXISTS idx_lifeart_press_pub
    ON public.lifeart_press (tenant_id, is_published, pinned, published_on DESC);

-- 초기 시드 (정적 예시 — 실제 데이터로 교체 예정)
INSERT INTO public.lifeart_press (tenant_id, title, outlet, summary, published_on, pinned)
SELECT public.lifeart_tenant_id(),
       'LifeArt, 25년 포토 시스템 노하우로 프리미엄 앨범 서비스 확대',
       '보도자료',
       '한화오션 VIP 앨범 납품 등 25년간 축적한 포토 시스템 기술을 바탕으로 온라인 프리미엄 포토 서비스를 시작합니다.',
       CURRENT_DATE, true
WHERE NOT EXISTS (SELECT 1 FROM public.lifeart_press WHERE tenant_id = public.lifeart_tenant_id());

-- ── 검증 ──
SELECT 'press' AS t, COUNT(*) FROM public.lifeart_press;
SELECT policyname FROM pg_policies WHERE tablename = 'lifeart_press';
