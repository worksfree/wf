-- ================================================================
-- tracking_tables.sql
-- 페이지뷰 & 세션 트래킹 테이블
-- Supabase Dashboard > SQL Editor 에서 실행
-- ================================================================

-- ── 1. page_views ────────────────────────────────────────────────
--    어떤 페이지를 언제, 얼마나 봤는지 기록
CREATE TABLE IF NOT EXISTS public.page_views (
  id          BIGSERIAL PRIMARY KEY,
  user_id     UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  page        TEXT        NOT NULL,         -- iframe src (e.g. 'service/qr/index.html')
  duration_s  INT,                          -- 체류 시간(초) — visibilitychange 시 UPDATE
  env         TEXT        DEFAULT 'portal', -- 'portal' | 'staging' | 'test' | 'dev'
  viewed_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 인기 페이지 집계, 사용자별 이력 조회에 필요한 인덱스
CREATE INDEX IF NOT EXISTS page_views_page_viewed_at  ON public.page_views(page, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_user_viewed_at  ON public.page_views(user_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_viewed_at       ON public.page_views(viewed_at DESC);

-- RLS: 관리자는 전체 읽기, 사용자는 자신의 행만 INSERT/UPDATE
ALTER TABLE public.page_views ENABLE ROW LEVEL SECURITY;

-- 재실행 안전: 기존 정책 삭제 후 재생성
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

CREATE POLICY "pv_insert_own" ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "pv_update_own" ON public.page_views
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "pv_admin_select" ON public.page_views
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );


-- ── 2. page_views 요약 뷰 (집계용) ──────────────────────────────
CREATE OR REPLACE VIEW public.page_view_stats AS
SELECT
  page,
  COUNT(*)                                    AS total_views,
  COUNT(DISTINCT user_id)                     AS unique_users,
  ROUND(AVG(duration_s))                      AS avg_duration_s,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '7 days')  AS views_7d,
  COUNT(*) FILTER (WHERE viewed_at > NOW() - INTERVAL '30 days') AS views_30d,
  MAX(viewed_at)                              AS last_viewed
FROM public.page_views
GROUP BY page
ORDER BY total_views DESC;

-- RLS 적용 (뷰는 정책 상속 안 되므로 SECURITY DEFINER 함수로 래핑)
-- 간단하게 admin 전용 함수로 제공
CREATE OR REPLACE FUNCTION public.admin_page_view_stats(days INT DEFAULT 30)
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
      AND pv.env NOT IN ('dev','test')
    GROUP BY pv.page
    ORDER BY COUNT(*) DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT) TO anon, authenticated;


-- ── 3. 확인 쿼리 ─────────────────────────────────────────────────
SELECT 'page_views table' AS object, COUNT(*) AS rows FROM public.page_views;
