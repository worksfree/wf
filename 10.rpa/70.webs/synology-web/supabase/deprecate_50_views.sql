-- ═══════════════════════════════════════════════════════════════════
-- 50_views.sql
-- WorksFree Hub — [5단계] 뷰 생성
--
-- 실행 순서: 5/7  (40_functions.sql 이후)
-- 다음 단계: 60_external_dbs.sql
--
-- 포함 내용:
--   - credit_balance   : 사용자별 크레딧 잔액 요약
--   - page_view_stats  : 페이지별 조회 통계 요약
-- ═══════════════════════════════════════════════════════════════════

-- ── credit_balance — 사용자별 크레딧 잔액 요약 ────────────────────────
CREATE OR REPLACE VIEW public.credit_balance
  WITH (security_invoker = true) AS
SELECT
  user_id,
  COALESCE(SUM(delta), 0)::INT                             AS balance,
  COALESCE(SUM(delta)  FILTER (WHERE delta > 0), 0)::INT   AS total_charged,
  COALESCE(SUM(-delta) FILTER (WHERE delta < 0), 0)::INT   AS total_used
FROM public.credits
GROUP BY user_id;


-- ── page_view_stats — 페이지별 조회 통계 요약 ─────────────────────────
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
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT table_name AS view_name
FROM   information_schema.views
WHERE  table_schema = 'public'
  AND  table_name   IN ('credit_balance', 'page_view_stats')
ORDER  BY table_name;
