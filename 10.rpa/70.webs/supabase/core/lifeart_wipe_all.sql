-- ================================================================
--  lifeart_wipe_all.sql — LifeArt 테스트/데모 데이터 전체 삭제
--  실행 위치: Supabase Dashboard → SQL Editor
--
--  삭제 대상 (전부 tenant_id = lifeart 로 격리된 것만, 다른 테넌트 무관):
--    lifeart_payments · lifeart_orders · lifeart_inquiries ·
--    lifeart_notices · lifeart_faqs · lifeart_press (전부)
--    + 테스트 회원 계정 2개(lifeart.tester@worksfree.kr, lifeart.admin.tester@worksfree.kr)
--      → auth.users 삭제 시 public.profiles 는 ON DELETE CASCADE 로 자동 삭제됨
--
--  건드리지 않는 것:
--    lifeart_products(카탈로그, 46건) — 실제 가격표라 보존
--    lifeart_hero_slides(첫화면) — 사용자 지시대로 제외, 큐레이션된 실사진 유지
--
--  전제: 실결제 이력 없음(사용자 확인 완료). 실결제 발생 후에는 재사용 금지.
--  재시딩은 lifeart_seed_testdata.sql 을 별도로, 원할 때 실행하세요.
-- ================================================================

DO $$
BEGIN
  IF public.lifeart_tenant_id() IS NULL THEN
    RAISE EXCEPTION 'lifeart 테넌트를 찾을 수 없습니다 — 03 마이그레이션을 먼저 확인하세요';
  END IF;
END $$;

-- ── FK 순서: payments → orders/inquiries(테넌트 회원 참조) → auth.users ──
DELETE FROM public.lifeart_payments  WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_orders    WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_inquiries WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_notices   WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_faqs      WHERE tenant_id = public.lifeart_tenant_id();
DELETE FROM public.lifeart_press     WHERE tenant_id = public.lifeart_tenant_id();

-- 테스트 회원 계정 삭제 (profiles 는 ON DELETE CASCADE 로 자동 정리됨)
DELETE FROM auth.users
WHERE email IN ('lifeart.tester@worksfree.kr', 'lifeart.admin.tester@worksfree.kr');

-- ── 검증 (전부 0 이어야 함, hero_slides 만 유지되어 5 여야 함) ──
SELECT 'orders' AS t, COUNT(*) FROM public.lifeart_orders WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'payments',    COUNT(*) FROM public.lifeart_payments    WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'inquiries',   COUNT(*) FROM public.lifeart_inquiries   WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'notices',     COUNT(*) FROM public.lifeart_notices     WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'faqs',        COUNT(*) FROM public.lifeart_faqs        WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'press',       COUNT(*) FROM public.lifeart_press       WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'hero_slides(유지되어야함)', COUNT(*) FROM public.lifeart_hero_slides WHERE tenant_id = public.lifeart_tenant_id()
UNION ALL SELECT 'members', COUNT(*) FROM auth.users WHERE email IN ('lifeart.tester@worksfree.kr','lifeart.admin.tester@worksfree.kr');
