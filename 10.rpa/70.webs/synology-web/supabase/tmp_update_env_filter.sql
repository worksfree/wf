-- ═══════════════════════════════════════════════════════════════════
-- update_env_filter.sql
-- admin_page_view_stats 함수에 env_filter 파라미터 추가
--
-- 변경 내용:
--   - 기존 admin_page_view_stats(days INT) → 삭제
--   - 신규 admin_page_view_stats(days INT, env_filter TEXT[]) 생성
--
-- 조회 환경 규칙 (프론트엔드 기준):
--   test.worksfree.kr   → env_filter = ['staging']
--   staging.worksfree.kr → env_filter = ['staging']
--   portal.worksfree.kr  → env_filter = ['portal']
--
-- 실행: Supabase Dashboard → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: 여러 번 실행해도 안전
-- ═══════════════════════════════════════════════════════════════════


-- ── STEP 1: 기존 단일 파라미터 버전 삭제 ──────────────────────────
DROP FUNCTION IF EXISTS public.admin_page_view_stats(INT);


-- ── STEP 2: env_filter 파라미터 추가 버전 생성 ───────────────────
--   env_filter = NULL → ARRAY['staging','portal'] 기본값 (하위 호환)
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(
  days        INT     DEFAULT 30,
  env_filter  TEXT[]  DEFAULT NULL
)
RETURNS TABLE (
  page         TEXT,
  views        BIGINT,
  unique_users BIGINT,
  avg_sec      NUMERIC,
  pct_with_dur NUMERIC
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  _r    TEXT;
  _envs TEXT[];
BEGIN
  -- 호출자가 admin 이어야만 결과 반환
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;

  -- NULL이면 staging+portal 기본값 (기존 동작 유지)
  _envs := COALESCE(env_filter, ARRAY['staging', 'portal']::TEXT[]);

  RETURN QUERY
    SELECT
      pv.page,
      COUNT(*)::BIGINT,
      COUNT(DISTINCT pv.user_id)::BIGINT,
      ROUND(AVG(pv.duration_s), 1),
      ROUND(100.0 * COUNT(pv.duration_s) / NULLIF(COUNT(*), 0), 1)
    FROM public.page_views pv
    WHERE pv.viewed_at > NOW() - (days || ' days')::INTERVAL
      AND pv.env = ANY(_envs)
    GROUP BY pv.page
    ORDER BY COUNT(*) DESC;
END;
$$;

REVOKE ALL    ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) TO anon, authenticated;


-- ── STEP 3: 확인 쿼리 ─────────────────────────────────────────────
SELECT '✅ admin_page_view_stats(INT, TEXT[]) 생성 완료' AS result,
       pg_get_function_arguments(p.oid) AS signature
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname = 'admin_page_view_stats';
