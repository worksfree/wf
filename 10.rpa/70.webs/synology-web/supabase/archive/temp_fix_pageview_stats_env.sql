-- ============================================================
-- fix_pageview_stats_env.sql
-- admin_page_view_stats 함수 개선
--
-- 문제: 기존 함수가 env NOT IN ('dev','test')를 하드코딩
--       → test 서버의 어드민 패널에서 test 환경 데이터가 통계에 잡히지 않음
--
-- 수정: env_filter 배열을 받아 해당 환경만 필터링
--       호출 예시: SELECT * FROM admin_page_view_stats(30, ARRAY['test','staging'])
--       기본값:   ARRAY['portal'] (기존 동작 유지)
-- ============================================================

CREATE OR REPLACE FUNCTION public.admin_page_view_stats(
  days       INT     DEFAULT 30,
  env_filter TEXT[]  DEFAULT ARRAY['portal']
)
RETURNS TABLE (
  page          TEXT,
  views         BIGINT,
  unique_users  BIGINT,
  avg_sec       NUMERIC,
  pct_with_dur  NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT
      pv.page,
      COUNT(*)::BIGINT,
      COUNT(DISTINCT pv.user_id)::BIGINT,
      ROUND(AVG(pv.duration_s), 1),
      ROUND(100.0 * COUNT(pv.duration_s) / NULLIF(COUNT(*), 0), 1)
    FROM public.page_views pv
    WHERE pv.viewed_at > NOW() - (days || ' days')::INTERVAL
      AND pv.env = ANY(env_filter)   -- 하드코딩 제거, 파라미터로 제어
    GROUP BY pv.page
    ORDER BY COUNT(*) DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) TO anon, authenticated;

-- 확인
SELECT 'admin_page_view_stats updated' AS result;
