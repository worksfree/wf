-- ================================================================
-- 03_tenants_hardening.sql — 테넌트 레지스트리 정비 + LifeArt 등록
--
-- · tenants 는 멀티테넌트 마이그레이션에서 유일하게 RLS가 빠진 테이블
-- · SELECT 공개 정책 필수: consulting/asset 페이지가 로그인 전 anon 키로
--   domain→tenant_id 를 조회함 (site_config 의 sc_select_all 과 동일 선례)
-- · 쓰기 정책은 만들지 않음 → SQL Editor/service_role 만 등록 가능
-- ================================================================

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenants_select_public" ON public.tenants;
CREATE POLICY "tenants_select_public" ON public.tenants FOR SELECT USING (true);

INSERT INTO public.tenants (domain, name)
VALUES ('lifeart.ai.kr', 'LifeArt')
ON CONFLICT (domain) DO NOTHING;

-- ── 검증 ──
-- (a) 정확히 2행: worksfree.kr, lifeart.ai.kr — ★ lifeart.ai.kr 의 id(UUID)를
--     복사해서 저에게 알려주세요. 사이트 코드(TENANT_UUID)에 넣어야 합니다.
SELECT domain, name, id FROM public.tenants ORDER BY domain;

-- (b) RLS on + SELECT 정책 1개만
SELECT rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename='tenants';
SELECT policyname, cmd FROM pg_policies WHERE schemaname='public' AND tablename='tenants';
