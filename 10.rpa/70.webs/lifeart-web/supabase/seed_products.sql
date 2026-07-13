-- ================================================================
-- LifeArt — products 초기 데이터 (7일차: 실제 상품 연동)
-- 액자는 정찰가라 실제 주문이 가능하도록 시딩. 삽입식앨범/VIP앨범은
-- 맞춤 상담형이라 대표 옵션만 안내용으로 등록 (가격 0 = 상담 후 결정).
-- Supabase Dashboard → SQL Editor 에서 schema.sql 다음에 실행
-- ================================================================

INSERT INTO public.products (tenant_id, category, name, price, options, is_active) VALUES
-- 슬림 크리스탈
('lifeart','frame','슬림 크리스탈 6x8',7700,'{"series":"슬림 크리스탈","size":"6x8"}','true'),
('lifeart','frame','슬림 크리스탈 6x9',8800,'{"series":"슬림 크리스탈","size":"6x9"}','true'),
('lifeart','frame','슬림 크리스탈 8x8',8800,'{"series":"슬림 크리스탈","size":"8x8"}','true'),
('lifeart','frame','슬림 크리스탈 6x12',8800,'{"series":"슬림 크리스탈","size":"6x12"}','true'),
('lifeart','frame','슬림 크리스탈 8x10',9900,'{"series":"슬림 크리스탈","size":"8x10"}','true'),
('lifeart','frame','슬림 크리스탈 8x12',11000,'{"series":"슬림 크리스탈","size":"8x12"}','true'),
('lifeart','frame','슬림 크리스탈 10x10',11000,'{"series":"슬림 크리스탈","size":"10x10"}','true'),
('lifeart','frame','슬림 크리스탈 10x20',22000,'{"series":"슬림 크리스탈","size":"10x20"}','true'),
('lifeart','frame','슬림 크리스탈 11x14',15400,'{"series":"슬림 크리스탈","size":"11x14"}','true'),
('lifeart','frame','슬림 크리스탈 12x15',19800,'{"series":"슬림 크리스탈","size":"12x15"}','true'),
('lifeart','frame','슬림 크리스탈 12x16',19800,'{"series":"슬림 크리스탈","size":"12x16"}','true'),
('lifeart','frame','슬림 크리스탈 12x17',19800,'{"series":"슬림 크리스탈","size":"12x17"}','true'),
('lifeart','frame','슬림 크리스탈 14x14',19800,'{"series":"슬림 크리스탈","size":"14x14"}','true'),
('lifeart','frame','슬림 크리스탈 14x18',34100,'{"series":"슬림 크리스탈","size":"14x18"}','true'),
('lifeart','frame','슬림 크리스탈 16x16',27500,'{"series":"슬림 크리스탈","size":"16x16"}','true'),
('lifeart','frame','슬림 크리스탈 16x20',34100,'{"series":"슬림 크리스탈","size":"16x20"}','true'),
('lifeart','frame','슬림 크리스탈 16x24',38500,'{"series":"슬림 크리스탈","size":"16x24"}','true'),
('lifeart','frame','슬림 크리스탈 20x24',42900,'{"series":"슬림 크리스탈","size":"20x24"}','true'),
('lifeart','frame','슬림 크리스탈 20x28',49500,'{"series":"슬림 크리스탈","size":"20x28"}','true'),
('lifeart','frame','슬림 크리스탈 20x30',51700,'{"series":"슬림 크리스탈","size":"20x30"}','true'),
('lifeart','frame','슬림 크리스탈 24x30',61600,'{"series":"슬림 크리스탈","size":"24x30"}','true'),
('lifeart','frame','슬림 크리스탈 24x32',61600,'{"series":"슬림 크리스탈","size":"24x32"}','true'),
('lifeart','frame','슬림 크리스탈 24x36',67100,'{"series":"슬림 크리스탈","size":"24x36"}','true'),
('lifeart','frame','슬림 크리스탈 28x42',106700,'{"series":"슬림 크리스탈","size":"28x42"}','true'),
-- 티크목
('lifeart','frame','티크목 8x10 소프트코팅',10500,'{"series":"티크목","size":"8x10","finish":"소프트코팅"}','true'),
('lifeart','frame','티크목 11x14 소프트코팅',17200,'{"series":"티크목","size":"11x14","finish":"소프트코팅"}','true'),
('lifeart','frame','티크목 16x20 소프트코팅',28600,'{"series":"티크목","size":"16x20","finish":"소프트코팅"}','true'),
('lifeart','frame','티크목 20x24 소프트코팅',35200,'{"series":"티크목","size":"20x24","finish":"소프트코팅"}','true'),
('lifeart','frame','티크목 24x32 소프트코팅',58900,'{"series":"티크목","size":"24x32","finish":"소프트코팅"}','true'),
('lifeart','frame','티크목 8x10 아크릴',13700,'{"series":"티크목","size":"8x10","finish":"아크릴"}','true'),
('lifeart','frame','티크목 11x14 아크릴',21400,'{"series":"티크목","size":"11x14","finish":"아크릴"}','true'),
('lifeart','frame','티크목 16x20 아크릴',35700,'{"series":"티크목","size":"16x20","finish":"아크릴"}','true'),
('lifeart','frame','티크목 20x24 아크릴',47200,'{"series":"티크목","size":"20x24","finish":"아크릴"}','true'),
('lifeart','frame','티크목 24x32 아크릴',67000,'{"series":"티크목","size":"24x32","finish":"아크릴"}','true'),
('lifeart','frame','티크목 30x40 아크릴',106600,'{"series":"티크목","size":"30x40","finish":"아크릴"}','true'),
-- 삼각 소 다크
('lifeart','frame','삼각 소 다크 5x7',4400,'{"series":"삼각 소 다크","size":"5x7"}','true'),
('lifeart','frame','삼각 소 다크 8x10',7200,'{"series":"삼각 소 다크","size":"8x10"}','true'),
('lifeart','frame','삼각 소 다크 11x14',11600,'{"series":"삼각 소 다크","size":"11x14"}','true'),
('lifeart','frame','삼각 소 다크 12x17',13800,'{"series":"삼각 소 다크","size":"12x17"}','true'),
('lifeart','frame','삼각 소 다크 16x20',18700,'{"series":"삼각 소 다크","size":"16x20"}','true'),
('lifeart','frame','삼각 소 다크 16x24',22600,'{"series":"삼각 소 다크","size":"16x24"}','true'),
('lifeart','frame','삼각 소 다크 20x24',26400,'{"series":"삼각 소 다크","size":"20x24"}','true'),
('lifeart','frame','삼각 소 다크 20x30',33000,'{"series":"삼각 소 다크","size":"20x30"}','true'),
('lifeart','frame','삼각 소 다크 24x32',42900,'{"series":"삼각 소 다크","size":"24x32"}','true'),
-- 상담형 상품 (가격 0 = 상담 후 결정)
('lifeart','instant-album','삽입식 기념앨범 (상담형)',0,'{"note":"수량/커버 옵션에 따라 상담"}','true'),
('lifeart','vip-album','VIP 앨범 Tier A/B/C (상담형)',0,'{"note":"Tier 및 매수에 따라 상담"}','true');
