-- ================================================================
-- 11_lifeart_om.sql — LifeArt O&M(운영관리) 확장
--
-- 08 이후 실행. LifeArt 관리자 콘솔에서 공지/FAQ 관리 + 모든 문의
-- (1:1·견적·제휴) 상세/답변/이메일 회신을 위한 스키마.
-- ================================================================

-- 공지사항
CREATE TABLE IF NOT EXISTS public.lifeart_notices (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES public.tenants(id),
    title        TEXT        NOT NULL,
    body         TEXT        NOT NULL DEFAULT '',
    is_published BOOLEAN     NOT NULL DEFAULT TRUE,
    pinned       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 자주 묻는 질문
CREATE TABLE IF NOT EXISTS public.lifeart_faqs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES public.tenants(id),
    question     TEXT        NOT NULL,
    answer       TEXT        NOT NULL DEFAULT '',
    sort_order   INTEGER     NOT NULL DEFAULT 0,
    is_published BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 문의(1:1·견적·제휴 공통)에 답변 컬럼 추가
ALTER TABLE public.lifeart_inquiries
    ADD COLUMN IF NOT EXISTS answer        TEXT,
    ADD COLUMN IF NOT EXISTS answered_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS answered_by   UUID REFERENCES auth.users(id),
    ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMPTZ;

-- RLS
ALTER TABLE public.lifeart_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lifeart_faqs    ENABLE ROW LEVEL SECURITY;

-- 공지: 게시된 것 공개 읽기, 관리자 전체 CRUD
CREATE POLICY "lifeart_notices_public" ON public.lifeart_notices FOR SELECT
    USING (is_published = true AND tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_notices_admin" ON public.lifeart_notices FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

-- FAQ: 게시된 것 공개 읽기, 관리자 전체 CRUD
CREATE POLICY "lifeart_faqs_public" ON public.lifeart_faqs FOR SELECT
    USING (is_published = true AND tenant_id = public.lifeart_tenant_id());
CREATE POLICY "lifeart_faqs_admin" ON public.lifeart_faqs FOR ALL
    USING (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id())
    WITH CHECK (public.is_lifeart_admin() AND tenant_id = public.lifeart_tenant_id());

-- (lifeart_inquiries 의 admin 정책은 08 에서 이미 부여됨 — 답변 UPDATE 포함)

CREATE INDEX IF NOT EXISTS idx_lifeart_notices_pub ON public.lifeart_notices (tenant_id, is_published, pinned, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lifeart_faqs_sort    ON public.lifeart_faqs (tenant_id, is_published, sort_order);

-- 초기 공지/FAQ 시드 (기존 정적 콘텐츠 이전)
INSERT INTO public.lifeart_notices (tenant_id, title, body, pinned)
SELECT public.lifeart_tenant_id(), 'LifeArt 홈페이지가 새롭게 오픈했습니다', 'LifeArt 온라인 서비스를 시작합니다. 포토북·삽입식앨범·VIP앨범·액자를 온라인에서 만나보세요.', true
WHERE NOT EXISTS (SELECT 1 FROM public.lifeart_notices WHERE tenant_id = public.lifeart_tenant_id());

INSERT INTO public.lifeart_faqs (tenant_id, question, answer, sort_order)
SELECT public.lifeart_tenant_id(), q, a, o FROM (VALUES
  ('주문 후 제작 기간은 얼마나 걸리나요?', '상품 종류와 수량에 따라 다르며, 삽입식 앨범은 현장 즉석 제작도 가능합니다. 정확한 기간은 견적 문의 시 안내드립니다.', 1),
  ('대량 주문 시 할인이 있나요?', '액자 등 일부 상품은 수량에 따라 할인이 적용됩니다. 견적 문의를 통해 안내드립니다.', 2),
  ('기업 단체 행사도 진행하나요?', '네, 25년간 다양한 기업 행사(진수식, 워크숍, 해외 출장 등)의 VIP 앨범과 삽입식 앨범을 제작해왔습니다.', 3)
) AS v(q,a,o)
WHERE NOT EXISTS (SELECT 1 FROM public.lifeart_faqs WHERE tenant_id = public.lifeart_tenant_id());

-- ── 검증 ──
SELECT 'notices' AS t, COUNT(*) FROM public.lifeart_notices
UNION ALL SELECT 'faqs', COUNT(*) FROM public.lifeart_faqs;
SELECT column_name FROM information_schema.columns
WHERE table_name='lifeart_inquiries' AND column_name IN ('answer','answered_at','answered_by','email_sent_at');
