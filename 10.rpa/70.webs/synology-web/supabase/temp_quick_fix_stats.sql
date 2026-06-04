-- ═══════════════════════════════════════════════════════════════════
-- quick_fix_stats.sql
-- 이메일 내역 + 페이지뷰 통계 안 나오는 문제 즉시 수정
--
-- 실행: Supabase Dashboard → SQL Editor → 이 파일 내용 붙여넣기 → Run
-- 멱등성: 여러 번 실행해도 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- A. 이메일 내역 수정
--    원인: phase2_email_management.sql 이 status 컬럼 없이 생성
--          + admin SELECT 정책 없음 → 프론트 직접 조회 불가
-- ══════════════════════════════════════════════════════════════════════

-- A-1. status 컬럼 추가
ALTER TABLE public.email_log
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'sent';

-- A-2. admin SELECT 정책 재설정 (기존 이름 다른 것 포함 정리)
DROP POLICY IF EXISTS "el_admin_select"        ON public.email_log;
DROP POLICY IF EXISTS "email_log_admin_select"  ON public.email_log;

CREATE POLICY "email_log_admin_select" ON public.email_log
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );


-- ══════════════════════════════════════════════════════════════════════
-- B. 페이지뷰 트래킹
--    원인: tracking_tables.sql 이 아직 실행 안 됨
--          → page_views 테이블 없음 + admin_page_view_stats 함수 없음
-- ══════════════════════════════════════════════════════════════════════

-- B-1. page_views 테이블
CREATE TABLE IF NOT EXISTS public.page_views (
  id         BIGSERIAL   PRIMARY KEY,
  user_id    UUID        REFERENCES public.profiles (id) ON DELETE SET NULL,
  page       TEXT        NOT NULL,
  duration_s INT,
  env        TEXT        DEFAULT 'portal',  -- 'portal' | 'staging' | 'test' | 'dev'
  viewed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS page_views_page_viewed_at ON public.page_views (page, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_user_viewed_at ON public.page_views (user_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_viewed_at      ON public.page_views (viewed_at DESC);

ALTER TABLE public.page_views ENABLE ROW LEVEL SECURITY;

-- B-2. page_views RLS 정책
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

-- 사용자: 자신의 행만 INSERT (페이지 방문 기록)
CREATE POLICY "pv_insert_own" ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 사용자: 자신의 행만 UPDATE (체류 시간 기록)
CREATE POLICY "pv_update_own" ON public.page_views
  FOR UPDATE USING (auth.uid() = user_id);

-- 관리자: 전체 SELECT
CREATE POLICY "pv_admin_select" ON public.page_views
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- B-3. admin_page_view_stats 함수
--   staging + portal 데이터만 집계 (test/dev 제외)
--   SECURITY DEFINER → RLS 우회해서 전체 집계 가능
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(days INT DEFAULT 30)
RETURNS TABLE (
  page         TEXT,
  views        BIGINT,
  unique_users BIGINT,
  avg_sec      NUMERIC,
  pct_with_dur NUMERIC
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE _r TEXT;
BEGIN
  -- 호출자가 admin 이어야만 결과 반환
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;

  RETURN QUERY
    SELECT
      pv.page,
      COUNT(*)::BIGINT,
      COUNT(DISTINCT pv.user_id)::BIGINT,
      ROUND(AVG(pv.duration_s), 1),
      ROUND(100.0 * COUNT(pv.duration_s) / NULLIF(COUNT(*), 0), 1)
    FROM public.page_views pv
    WHERE pv.viewed_at > NOW() - (days || ' days')::INTERVAL
      AND pv.env IN ('staging', 'portal')   -- test/dev 제외
    GROUP BY pv.page
    ORDER BY COUNT(*) DESC;
END;
$$;

REVOKE ALL   ON FUNCTION public.admin_page_view_stats(INT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT) TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════
-- Z. 확인 쿼리 — Run 후 결과 패널에서 확인
-- ══════════════════════════════════════════════════════════════════════

SELECT '① email_log.status 컬럼' AS check_item,
       CASE WHEN COUNT(*) > 0 THEN '✅ 있음 — 이메일 내역 조회 가능'
                               ELSE '❌ 없음' END AS result
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name   = 'email_log'
  AND column_name  = 'status';

SELECT '② email_log RLS 정책' AS check_item,
       policyname, cmd
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'email_log';

SELECT '③ page_views 테이블 행 수' AS check_item,
       COUNT(*)::TEXT AS result
FROM public.page_views;

SELECT '④ page_views RLS 정책' AS check_item,
       policyname, cmd
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'page_views';

SELECT '⑤ admin_page_view_stats 함수' AS check_item,
       CASE WHEN COUNT(*) > 0 THEN '✅ 있음 — 페이지 통계 사용 가능'
                               ELSE '❌ 없음' END AS result
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name   = 'admin_page_view_stats';


-- ══════════════════════════════════════════════════════════════════════
-- C. 로그인 이력 조회 함수 (사용자 관리 페이지용)
--    auth.users.last_sign_in_at 을 SECURITY DEFINER 로 안전하게 노출
--    → 관리자만 호출 가능, 일반 사용자는 빈 결과 반환
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM auth.users au;
END;
$$;
REVOKE ALL   ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;

SELECT '⑥ admin_get_user_logins 함수' AS check_item,
       CASE WHEN COUNT(*) > 0 THEN '✅ 있음 — 로그인 이력 조회 가능'
                               ELSE '❌ 없음' END AS result
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name   = 'admin_get_user_logins';


-- ══════════════════════════════════════════════════════════════════════
-- D. 사용자 목록 조회 함수 (사용자 관리 페이지용)
--    profiles 테이블을 SECURITY DEFINER 로 전체 조회
--    → RLS 정책 상태와 무관하게 관리자가 모든 프로필 조회 가능
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (
  id          UUID,
  email       TEXT,
  name        TEXT,
  role        TEXT,
  agreed_at   TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM public.profiles p
    ORDER BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;

SELECT '⑦ admin_get_all_profiles 함수' AS check_item,
       CASE WHEN COUNT(*) > 0 THEN '✅ 있음 — 사용자 목록 조회 가능'
                               ELSE '❌ 없음' END AS result
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name   = 'admin_get_all_profiles';
