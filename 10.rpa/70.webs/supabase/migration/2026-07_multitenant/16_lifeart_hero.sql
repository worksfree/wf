-- ================================================================
-- 16_lifeart_hero.sql — LifeArt 첫 화면(히어로) 슬라이드 관리
--
-- 관리자 콘솔에서 첫 화면 로테이션 이미지를 교체/추가/정렬한다.
-- 공개 홈은 활성 슬라이드를 읽어 렌더(없으면 기본 이미지로 폴백).
-- 규약은 lifeart_notices 와 동일(테넌트 스코프 + is_lifeart_admin CRUD).
-- ================================================================

CREATE TABLE IF NOT EXISTS public.lifeart_hero_slides (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID        NOT NULL REFERENCES public.tenants(id),
    image_url  TEXT        NOT NULL,
    caption    TEXT,                          -- (선택) 접근성/설명
    sort_order INTEGER     NOT NULL DEFAULT 0,
    is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.lifeart_hero_slides ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "lifeart_hero_public" ON public.lifeart_hero_slides;
DROP POLICY IF EXISTS "lifeart_hero_admin"  ON public.lifeart_hero_slides;
CREATE POLICY "lifeart_hero_public" ON public.lifeart_hero_slides FOR SELECT
    USING (is_active = true AND tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_hero_admin" ON public.lifeart_hero_slides FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

CREATE INDEX IF NOT EXISTS idx_lifeart_hero_order
    ON public.lifeart_hero_slides (tenant_id, is_active, sort_order);

-- 현재 하드코딩된 기본 5장 시드 (관리자가 이후 교체)
INSERT INTO public.lifeart_hero_slides (tenant_id, image_url, sort_order)
SELECT public.lifeart_tenant_id(), v.url, v.ord
FROM (VALUES
  ('/assets/gallery/prod-01.png', 1),
  ('/assets/gallery/event-01.jpg', 2),
  ('/assets/gallery/corp-01.jpg', 3),
  ('/assets/img/hero-vip.png', 4),
  ('/assets/gallery/prod-02.png', 5)
) AS v(url, ord)
WHERE NOT EXISTS (SELECT 1 FROM public.lifeart_hero_slides WHERE tenant_id = public.lifeart_tenant_id());

-- ── 검증 ──
SELECT sort_order, image_url, is_active FROM public.lifeart_hero_slides
WHERE tenant_id = public.lifeart_tenant_id() ORDER BY sort_order;
SELECT policyname FROM pg_policies WHERE tablename = 'lifeart_hero_slides';
