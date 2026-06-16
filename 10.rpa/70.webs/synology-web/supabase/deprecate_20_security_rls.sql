-- ═══════════════════════════════════════════════════════════════════
-- 20_security_rls.sql
-- WorksFree Hub — [2단계] 보안 헬퍼 함수 + 전체 RLS 정책
--
-- 실행 순서: 2/7  (10_extensions_tables.sql 이후)
-- 다음 단계: 30_triggers.sql
--
-- 포함 내용:
--   - is_admin()  헬퍼 함수 (RLS 정책이 참조 → 정책보다 먼저 생성)
--   - profiles    RLS: 본인 전체 · 관리자 SELECT
--   - credits     RLS: 본인 SELECT · purchase INSERT
--   - payments    RLS: 본인 SELECT · INSERT
--   - email_log   RLS: 관리자 SELECT (INSERT는 Worker service_role 우회)
--   - email_unsubscribes RLS: 관리자 ALL
--   - page_views  RLS: 본인 INSERT/SELECT/UPDATE · 관리자 SELECT
--
-- 멱등성: DROP POLICY IF EXISTS → CREATE POLICY
-- ═══════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════
-- 1. is_admin() — RLS 정책 내 순환 참조 방지 (SECURITY DEFINER)
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, anon;


-- ══════════════════════════════════════════════════════════════════════
-- 2. profiles RLS
-- ══════════════════════════════════════════════════════════════════════
-- 기존 정책 전부 삭제 (이름 불일치 방지)
DO $$ DECLARE r RECORD;
BEGIN
  FOR r IN SELECT policyname FROM pg_policies
           WHERE schemaname = 'public' AND tablename = 'profiles' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.profiles', r.policyname);
  END LOOP;
END $$;

-- 본인 행: 모든 작업 허용
CREATE POLICY "profiles_self"
  ON public.profiles FOR ALL
  USING     (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 관리자: 전체 SELECT
CREATE POLICY "profiles_admin_select_all"
  ON public.profiles FOR SELECT
  USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 3. credits RLS
-- ══════════════════════════════════════════════════════════════════════
DROP POLICY IF EXISTS "credits_select_own"      ON public.credits;
DROP POLICY IF EXISTS "credits_insert_purchase" ON public.credits;

-- 본인 크레딧 이력 조회
CREATE POLICY "credits_select_own"
  ON public.credits FOR SELECT
  USING (auth.uid() = user_id);

-- 충전(purchase)만 직접 INSERT 허용 — 차감은 deduct_credits() SECURITY DEFINER 경유
CREATE POLICY "credits_insert_purchase"
  ON public.credits FOR INSERT
  WITH CHECK (auth.uid() = user_id AND delta > 0 AND reason = 'purchase');


-- ══════════════════════════════════════════════════════════════════════
-- 4. payments RLS
-- ══════════════════════════════════════════════════════════════════════
DROP POLICY IF EXISTS "payments_select_own" ON public.payments;
DROP POLICY IF EXISTS "payments_insert_own" ON public.payments;

CREATE POLICY "payments_select_own"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "payments_insert_own"
  ON public.payments FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- ══════════════════════════════════════════════════════════════════════
-- 5. email_log RLS
--    INSERT: Cloudflare Worker(service_role)가 RLS 우회하여 직접 삽입
-- ══════════════════════════════════════════════════════════════════════
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select" ON public.email_log;

CREATE POLICY "email_log_admin_select"
  ON public.email_log FOR SELECT
  USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 6. email_unsubscribes RLS
-- ══════════════════════════════════════════════════════════════════════
DROP POLICY IF EXISTS "eu_admin_all"             ON public.email_unsubscribes;
DROP POLICY IF EXISTS "email_unsubscribes_admin" ON public.email_unsubscribes;

CREATE POLICY "email_unsubscribes_admin"
  ON public.email_unsubscribes FOR ALL
  USING     (is_admin())
  WITH CHECK (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 7. page_views RLS
-- ══════════════════════════════════════════════════════════════════════
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_select_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

CREATE POLICY "pv_insert_own"   ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "pv_select_own"   ON public.page_views
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "pv_update_own"   ON public.page_views
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "pv_admin_select" ON public.page_views
  FOR SELECT USING (is_admin());


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT tablename, policyname, cmd
FROM   pg_policies
WHERE  schemaname = 'public'
  AND  tablename  IN ('profiles','credits','payments',
                      'email_log','email_unsubscribes','page_views')
ORDER  BY tablename, policyname;
