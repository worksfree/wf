-- ================================================================
--  lifeart_reset_testdata.sql — LifeArt 테스트/데모 데이터 초기화 + 재시딩
--  실행 위치: Supabase Dashboard → SQL Editor (postgres 권한으로 실행되어
--            lifeart_payments 의 "쓰기는 service_role 전용" RLS 를 우회함)
--
--  반복 실행 가능(재실행할 때마다 초기화 + 재시딩). 날짜는 모두 NOW() 기준
--  상대값이라 언제 실행해도 "최근 N일"로 현행화되어 보인다.
--
--  건드리는 것 : lifeart_orders / lifeart_payments / lifeart_inquiries(전체) /
--               lifeart_notices(제목에 '테스트' 포함된 것만) / lifeart_hero_slides
--  건드리지 않는 것 : lifeart_products(카탈로그), lifeart_faqs, lifeart_press,
--                    실제 오픈 공지("LifeArt 홈페이지가 새롭게 오픈했습니다"),
--                    다른 테넌트(worksfree 등) 데이터 — 전부 tenant_id 로 격리됨
--
--  전제: 아직 서비스 오픈 전이라 실결제 이력이 없음(사용자 확인 완료).
--        실결제가 발생한 뒤에는 이 스크립트를 그대로 재사용하지 말 것.
-- ================================================================

DO $$
BEGIN
  IF public.lifeart_tenant_id() IS NULL THEN
    RAISE EXCEPTION 'lifeart 테넌트를 찾을 수 없습니다 — 03 마이그레이션을 먼저 확인하세요';
  END IF;
END $$;

-- ── ① 삭제 (FK 순서: payments → orders) ──────────────────────────
DELETE FROM public.lifeart_payments  WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_orders    WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_inquiries WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_notices   WHERE tenant_id = public.lifeart_tenant_id() AND title ILIKE '%테스트%';
DELETE FROM public.lifeart_hero_slides WHERE tenant_id = public.lifeart_tenant_id();

-- ── ② 히어로 슬라이드 재시딩 (개편판 최적화 실사진 5장 — index.html 정적 목록과 동일) ──
INSERT INTO public.lifeart_hero_slides (tenant_id, image_url, sort_order, is_active)
SELECT public.lifeart_tenant_id(), v.url, v.ord, true FROM (VALUES
  ('/assets/img/albums/insert-collection-01.jpg', 1),
  ('/assets/img/albums/insert-dsme-03.jpg',        2),
  ('/assets/gallery/corp-01.jpg',                  3),
  ('/assets/img/albums/insert-dsme-01.jpg',        4),
  ('/assets/img/albums/insert-stx-01.jpg',         5)
) AS v(url, ord);

-- ── ③ 데모 주문 재시딩 (관리자 콘솔 검증용 — 실 고객 데이터 아님, 날짜는 NOW() 상대) ──
--   pending 상태는 결제 전이므로 의도적으로 payments 를 만들지 않는다(실제 흐름과 동일).
WITH prod AS (
  SELECT id, name FROM public.lifeart_products
),
seed AS (
  SELECT * FROM (VALUES
    ('VIP 앨범 Tier A/B/C (상담형)', 1, 0::bigint,     'done',     'delivered', 45),
    ('삽입식 기념앨범 (상담형)',       2, 0::bigint,     'shipping', 'shipping',  20),
    ('슬림 크리스탈 24x30',           1, 61600::bigint, 'done',     'delivered', 15),
    ('삼각 소 다크 8x10',             2, 14400::bigint, 'paid',     'ready',      7),
    ('삼각 소 다크 11x14',            1, 11600::bigint, 'paid',     'ready',      3),
    ('삼각 소 다크 20x30',            1, 33000::bigint, 'pending',  'ready',      1)
  ) AS v(prod_name, qty, amount, status, ship_status, days_ago)
),
new_orders AS (
  INSERT INTO public.lifeart_orders
    (tenant_id, user_id, product_id, quantity, amount, status, shipping_address, shipping_status, env, created_at, updated_at)
  SELECT
    public.lifeart_tenant_id(), NULL, p.id, s.qty, s.amount, s.status, 'DEMO', s.ship_status, 'pre-test',
    NOW() - (s.days_ago || ' days')::interval,
    NOW() - (s.days_ago || ' days')::interval
  FROM seed s JOIN prod p ON p.name = s.prod_name
  RETURNING id, status, amount, created_at
)
INSERT INTO public.lifeart_payments (tenant_id, order_id, pg_provider, pg_tid, amount, status, env, approved_at, created_at)
SELECT public.lifeart_tenant_id(), id, 'toss', 'DEMO_' || substr(id::text, 1, 8), amount, 'approved', 'pre-test', created_at, created_at
FROM new_orders
WHERE status IN ('paid', 'shipping', 'done');

-- ── ④ 데모 문의 1건 재시딩 (관리자 콘솔 답변 UI 확인용) ──
INSERT INTO public.lifeart_inquiries
  (tenant_id, type, env, user_id, name, phone, email, message, status, answer, answered_at, created_at)
SELECT
  public.lifeart_tenant_id(), 'estimate', 'pre-test', NULL,
  '홍길동', '010-1234-5678', 'demo@example.com',
  '기업 워크숍 50명 기념앨범 견적 부탁드립니다.',
  'answered',
  '문의 주셔서 감사합니다. 상세 견적은 이메일로 안내드렸습니다.',
  NOW() - interval '2 days',
  NOW() - interval '3 days';

-- ── 검증 ──
SELECT 'orders' AS t, COUNT(*) FROM public.lifeart_orders WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'payments',    COUNT(*) FROM public.lifeart_payments    WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'inquiries',   COUNT(*) FROM public.lifeart_inquiries   WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'notices',     COUNT(*) FROM public.lifeart_notices     WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'hero_slides', COUNT(*) FROM public.lifeart_hero_slides WHERE tenant_id = public.lifeart_tenant_id();

SELECT status, shipping_status, amount, created_at FROM public.lifeart_orders
WHERE tenant_id = public.lifeart_tenant_id() ORDER BY created_at DESC;
