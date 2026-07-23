-- ================================================================
-- 21_lifeart_products_addons.sql — 옵션상품(추가구성상품) 지원
--
-- 08 이후 아무 때나 실행 가능(단순 ALTER + 시딩). 배경:
--  · 상품 상세/구매 페이지에 "추가구성상품"(케이스·각인·클리닝 키트 등)을
--    선택해 담을 수 있어야 함 — fomex.co.kr 류 쇼핑몰의 "추가구성상품" 패턴 참고.
--  · 새 테이블을 만들지 않고 기존 lifeart_products 를 재사용 — addon도 결국
--    "카테고리 안에서 팔리는 품목"이라 is_addon 플래그 하나로 충분하고,
--    admin/RLS/조회 쿼리를 전부 그대로 재사용할 수 있다(카테고리로 스코프).
-- ================================================================

ALTER TABLE public.lifeart_products
  ADD COLUMN IF NOT EXISTS is_addon BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_lifeart_products_addon
  ON public.lifeart_products (tenant_id, category, is_addon);

-- ── 액자(frame) 카테고리 데모 옵션상품 (재실행 안전: 이름 기준 삭제 후 삽입) ──
DELETE FROM public.lifeart_products
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
  AND category = 'frame' AND is_addon = TRUE;

INSERT INTO public.lifeart_products (tenant_id, category, name, price, options, is_active, is_addon)
SELECT (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr'),
       category, name, price, options::jsonb, true, true
FROM (VALUES
  ('frame','프리미엄 우드 스탠드',  8000, '{"note":"탁상 거치용 원목 스탠드 추가"}'),
  ('frame','선물 포장 (리본+박스)', 3000, '{"note":"선물용 박스 포장"}'),
  ('frame','액자 클리닝 키트',      5000, '{"note":"전용 극세사 천 + 클리너"}'),
  ('frame','각인 서비스 (문구 1줄)', 10000, '{"note":"액자 하단 금속 명패 각인"}')
) AS v(category, name, price, options);

-- ── 검증 ──
SELECT category, is_addon, COUNT(*) FROM public.lifeart_products
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
GROUP BY category, is_addon ORDER BY category, is_addon;
-- 기대: frame/false 44, frame/true 4, instant-album/false 1, vip-album/false 1
