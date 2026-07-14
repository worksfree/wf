-- ================================================================
-- 17_lifeart_seed_demo.sql — 관리자 콘솔 검증용 가상 주문/결제 데이터 (pre-test 전용)
--
-- 매출 현황·주문 관리·회원 관리(구매 집계)를 실제로 확인하기 위한 데모 데이터.
-- 회원 주문은 10_dev_test_accounts.sql 의 테스트 계정을 참조하므로 10 을 먼저 실행 권장
-- (안 했으면 해당 주문은 '비회원'으로 들어감).
--
-- ★ 재실행 안전 + 정리 가능: 데모 주문은 shipping_address='DEMO' 로 표식.
--   재실행하면 기존 데모를 지우고 다시 넣는다. 운영 오픈 전 아래 [정리]로 삭제.
-- ================================================================

DO $$
DECLARE
  la   uuid := public.lifeart_tenant_id();
  u1   uuid := (SELECT id FROM auth.users WHERE email = 'lifeart.tester@worksfree.kr');
  u2   uuid := (SELECT id FROM auth.users WHERE email = 'lifeart.admin.test@worksfree.kr');
  rec  record;
  oid  uuid;
  prod uuid;
  prc  bigint;
BEGIN
  -- 기존 데모 제거 (결제 → 주문 순)
  DELETE FROM public.lifeart_payments
   WHERE order_id IN (SELECT id FROM public.lifeart_orders WHERE tenant_id = la AND shipping_address = 'DEMO');
  DELETE FROM public.lifeart_orders WHERE tenant_id = la AND shipping_address = 'DEMO';

  FOR rec IN
    SELECT * FROM (VALUES
      -- 회원키, 카테고리, 이름패턴, 수량, 상태, N일전
      ('u1',   'vip-album',     NULL,        1, 'done',      42),
      ('u1',   'frame',         '%8x10%',    2, 'paid',       6),
      ('u2',   'instant-album', NULL,        3, 'shipping',  15),
      ('guest','frame',         '%11x14%',   1, 'paid',       3),
      ('u1',   'frame',         '%16x20%',   1, 'pending',    1),
      ('u2',   'vip-album',     NULL,        2, 'done',      22),
      ('guest','instant-album', NULL,        1, 'cancelled', 10),
      ('u1',   'frame',         '%20x30%',   1, 'paid',       0),
      ('u2',   'frame',         '%24x30%',   1, 'done',       9),
      ('guest','vip-album',     NULL,        1, 'paid',       4)
    ) AS v(ukey, cat, nlike, qty, st, dago)
  LOOP
    -- 상품 선택 (카테고리/이름패턴 → 없으면 아무 활성상품)
    SELECT id, price INTO prod, prc FROM public.lifeart_products
      WHERE tenant_id = la AND category = rec.cat
        AND (rec.nlike IS NULL OR name LIKE rec.nlike)
      ORDER BY price LIMIT 1;
    IF prod IS NULL THEN
      SELECT id, price INTO prod, prc FROM public.lifeart_products
        WHERE tenant_id = la AND is_active LIMIT 1;
    END IF;
    prc := COALESCE(prc, 10000);

    INSERT INTO public.lifeart_orders
      (tenant_id, user_id, product_id, quantity, amount, status, shipping_status, shipping_address, created_at, env)
    VALUES
      (la,
       CASE rec.ukey WHEN 'u1' THEN u1 WHEN 'u2' THEN u2 ELSE NULL END,
       prod, rec.qty, rec.qty * prc, rec.st,
       CASE rec.st WHEN 'done' THEN 'delivered' WHEN 'shipping' THEN 'shipping' ELSE 'ready' END,
       'DEMO',
       now() - (rec.dago || ' days')::interval,
       'pre-test')
    RETURNING id INTO oid;

    -- 결제완료 계열이면 승인 결제 기록
    IF rec.st IN ('paid','shipping','done') THEN
      INSERT INTO public.lifeart_payments
        (tenant_id, order_id, pg_provider, pg_tid, amount, status, approved_at, created_at, env)
      VALUES
        (la, oid, 'toss', 'DEMO_' || substr(oid::text, 1, 8),
         rec.qty * prc, 'approved',
         now() - (rec.dago || ' days')::interval,
         now() - (rec.dago || ' days')::interval, 'pre-test');
    END IF;
  END LOOP;
END $$;

-- ── 검증 ──
SELECT status, COUNT(*), SUM(amount) FROM public.lifeart_orders
WHERE tenant_id = public.lifeart_tenant_id() AND shipping_address = 'DEMO'
GROUP BY status ORDER BY status;

-- ── [정리] 운영 오픈 전 데모 삭제 (필요 시 개별 실행) ──
-- DELETE FROM public.lifeart_payments WHERE order_id IN
--   (SELECT id FROM public.lifeart_orders WHERE tenant_id=public.lifeart_tenant_id() AND shipping_address='DEMO');
-- DELETE FROM public.lifeart_orders WHERE tenant_id=public.lifeart_tenant_id() AND shipping_address='DEMO';
