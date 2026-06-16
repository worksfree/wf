-- ═══════════════════════════════════════════════════════════════════
-- 04_admin_analytics.sql
-- WorksFree Hub — [Stage 4] 관리자 · 페이지뷰 분석 (선택)
--
-- 사전 조건: 01_auth_profiles.sql 실행 완료
-- (이 스테이지는 독립 선택 사항 — 관리자 대시보드를 구축할 때만 실행)
--
-- 포함 내용:
--   - public.page_views       (페이지 조회 추적)
--   - page_views RLS 정책
--   - page_view_stats 뷰      (페이지별 통계 요약)
--   - admin_page_view_stats   (관리자 통계 조회 함수)
--
-- 멱등성: 반복 실행 안전
-- ═══════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- 1. page_views — 페이지 조회 추적 (체류시간 포함)
-- ══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.page_views (
  id         BIGSERIAL   PRIMARY KEY,
  user_id    UUID        REFERENCES public.profiles(id) ON DELETE SET NULL,
  page       TEXT        NOT NULL,
  duration_s INT,
  env        TEXT        DEFAULT 'portal',
  viewed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS page_views_page_viewed_at ON public.page_views (page, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_user_viewed_at ON public.page_views (user_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_viewed_at      ON public.page_views (viewed_at DESC);

ALTER TABLE public.page_views ENABLE ROW LEVEL SECURITY;


-- ══════════════════════════════════════════════════════════════════════
-- 2. page_views RLS 정책
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
-- 3. page_view_stats 뷰 — 페이지별 통계 요약
-- ══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW public.page_view_stats AS
SELECT
  page,
  COUNT(*)                                                          AS total_views,
  COUNT(DISTINCT user_id)                                           AS unique_users,
  ROUND(AVG(duration_s))                                            AS avg_duration_s,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '7 days')    AS views_7d,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '30 days')   AS views_30d,
  MAX(viewed_at)                                                    AS last_viewed
FROM public.page_views
GROUP BY page
ORDER BY total_views DESC;


-- ══════════════════════════════════════════════════════════════════════
-- 4. admin_page_view_stats — 관리자 통계 조회 함수
--    env_filter = NULL → ['staging','portal'] 기본값
-- ══════════════════════════════════════════════════════════════════════
DROP FUNCTION IF EXISTS public.admin_page_view_stats(INT);
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(
  days        INT    DEFAULT 30,
  env_filter  TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  page         TEXT,
  views        BIGINT,
  unique_users BIGINT,
  avg_sec      NUMERIC,
  pct_with_dur NUMERIC
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  _r    TEXT;
  _envs TEXT[];
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
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


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name
FROM   information_schema.tables
WHERE  table_schema = 'public'
  AND  table_name = 'page_views';

SELECT table_name AS view_name
FROM   information_schema.views
WHERE  table_schema = 'public'
  AND  table_name   = 'page_view_stats';
