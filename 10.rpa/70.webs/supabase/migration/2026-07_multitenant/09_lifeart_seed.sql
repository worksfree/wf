-- ================================================================
-- 09_lifeart_seed.sql — lifeart_products 초기 데이터 (액자 44종 + 상담형 2종)
--
-- 반드시 08 실행 후. tenant_id 는 서브쿼리로 lifeart.ai.kr 을 조회해 채움.
-- 재실행 안전: 이미 시딩됐으면 중복 방지 위해 먼저 삭제 후 삽입.
-- ================================================================

DELETE FROM public.lifeart_products
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
  AND category IN ('frame','instant-album','vip-album');

INSERT INTO public.lifeart_products (tenant_id, category, name, price, options, is_active)
SELECT (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr'),
       category, name, price, options::jsonb, true
FROM (VALUES
  -- 슬림 크리스탈
  ('frame','슬림 크리스탈 6x8',7700,'{"series":"슬림 크리스탈","size":"6x8"}'),
  ('frame','슬림 크리스탈 6x9',8800,'{"series":"슬림 크리스탈","size":"6x9"}'),
  ('frame','슬림 크리스탈 8x8',8800,'{"series":"슬림 크리스탈","size":"8x8"}'),
  ('frame','슬림 크리스탈 6x12',8800,'{"series":"슬림 크리스탈","size":"6x12"}'),
  ('frame','슬림 크리스탈 8x10',9900,'{"series":"슬림 크리스탈","size":"8x10"}'),
  ('frame','슬림 크리스탈 8x12',11000,'{"series":"슬림 크리스탈","size":"8x12"}'),
  ('frame','슬림 크리스탈 10x10',11000,'{"series":"슬림 크리스탈","size":"10x10"}'),
  ('frame','슬림 크리스탈 10x20',22000,'{"series":"슬림 크리스탈","size":"10x20"}'),
  ('frame','슬림 크리스탈 11x14',15400,'{"series":"슬림 크리스탈","size":"11x14"}'),
  ('frame','슬림 크리스탈 12x15',19800,'{"series":"슬림 크리스탈","size":"12x15"}'),
  ('frame','슬림 크리스탈 12x16',19800,'{"series":"슬림 크리스탈","size":"12x16"}'),
  ('frame','슬림 크리스탈 12x17',19800,'{"series":"슬림 크리스탈","size":"12x17"}'),
  ('frame','슬림 크리스탈 14x14',19800,'{"series":"슬림 크리스탈","size":"14x14"}'),
  ('frame','슬림 크리스탈 14x18',34100,'{"series":"슬림 크리스탈","size":"14x18"}'),
  ('frame','슬림 크리스탈 16x16',27500,'{"series":"슬림 크리스탈","size":"16x16"}'),
  ('frame','슬림 크리스탈 16x20',34100,'{"series":"슬림 크리스탈","size":"16x20"}'),
  ('frame','슬림 크리스탈 16x24',38500,'{"series":"슬림 크리스탈","size":"16x24"}'),
  ('frame','슬림 크리스탈 20x24',42900,'{"series":"슬림 크리스탈","size":"20x24"}'),
  ('frame','슬림 크리스탈 20x28',49500,'{"series":"슬림 크리스탈","size":"20x28"}'),
  ('frame','슬림 크리스탈 20x30',51700,'{"series":"슬림 크리스탈","size":"20x30"}'),
  ('frame','슬림 크리스탈 24x30',61600,'{"series":"슬림 크리스탈","size":"24x30"}'),
  ('frame','슬림 크리스탈 24x32',61600,'{"series":"슬림 크리스탈","size":"24x32"}'),
  ('frame','슬림 크리스탈 24x36',67100,'{"series":"슬림 크리스탈","size":"24x36"}'),
  ('frame','슬림 크리스탈 28x42',106700,'{"series":"슬림 크리스탈","size":"28x42"}'),
  -- 티크목
  ('frame','티크목 8x10 소프트코팅',10500,'{"series":"티크목","size":"8x10","finish":"소프트코팅"}'),
  ('frame','티크목 11x14 소프트코팅',17200,'{"series":"티크목","size":"11x14","finish":"소프트코팅"}'),
  ('frame','티크목 16x20 소프트코팅',28600,'{"series":"티크목","size":"16x20","finish":"소프트코팅"}'),
  ('frame','티크목 20x24 소프트코팅',35200,'{"series":"티크목","size":"20x24","finish":"소프트코팅"}'),
  ('frame','티크목 24x32 소프트코팅',58900,'{"series":"티크목","size":"24x32","finish":"소프트코팅"}'),
  ('frame','티크목 8x10 아크릴',13700,'{"series":"티크목","size":"8x10","finish":"아크릴"}'),
  ('frame','티크목 11x14 아크릴',21400,'{"series":"티크목","size":"11x14","finish":"아크릴"}'),
  ('frame','티크목 16x20 아크릴',35700,'{"series":"티크목","size":"16x20","finish":"아크릴"}'),
  ('frame','티크목 20x24 아크릴',47200,'{"series":"티크목","size":"20x24","finish":"아크릴"}'),
  ('frame','티크목 24x32 아크릴',67000,'{"series":"티크목","size":"24x32","finish":"아크릴"}'),
  ('frame','티크목 30x40 아크릴',106600,'{"series":"티크목","size":"30x40","finish":"아크릴"}'),
  -- 삼각 소 다크
  ('frame','삼각 소 다크 5x7',4400,'{"series":"삼각 소 다크","size":"5x7"}'),
  ('frame','삼각 소 다크 8x10',7200,'{"series":"삼각 소 다크","size":"8x10"}'),
  ('frame','삼각 소 다크 11x14',11600,'{"series":"삼각 소 다크","size":"11x14"}'),
  ('frame','삼각 소 다크 12x17',13800,'{"series":"삼각 소 다크","size":"12x17"}'),
  ('frame','삼각 소 다크 16x20',18700,'{"series":"삼각 소 다크","size":"16x20"}'),
  ('frame','삼각 소 다크 16x24',22600,'{"series":"삼각 소 다크","size":"16x24"}'),
  ('frame','삼각 소 다크 20x24',26400,'{"series":"삼각 소 다크","size":"20x24"}'),
  ('frame','삼각 소 다크 20x30',33000,'{"series":"삼각 소 다크","size":"20x30"}'),
  ('frame','삼각 소 다크 24x32',42900,'{"series":"삼각 소 다크","size":"24x32"}'),
  -- 상담형 (가격 0 = 상담 후 결정)
  ('instant-album','삽입식 기념앨범 (상담형)',0,'{"note":"수량/커버 옵션에 따라 상담"}'),
  ('vip-album','VIP 앨범 Tier A/B/C (상담형)',0,'{"note":"Tier 및 매수에 따라 상담"}')
) AS v(category, name, price, options);

-- ── 검증 ──
SELECT category, COUNT(*) FROM public.lifeart_products
WHERE tenant_id = (SELECT id FROM public.tenants WHERE domain='lifeart.ai.kr')
GROUP BY category ORDER BY category;
-- 기대: frame 44, instant-album 1, vip-album 1
