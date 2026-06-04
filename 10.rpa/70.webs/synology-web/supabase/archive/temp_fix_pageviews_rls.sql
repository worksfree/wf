-- ═══════════════════════════════════════════════════════════════════
-- fix_pageviews_rls.sql
-- page_views 테이블 SELECT 정책 추가
--
-- 문제:
--   INSERT ... RETURNING id 실행 시 PostgreSQL은 INSERT 정책 + SELECT 정책을 함께 검사.
--   pv_select_own 이 없으면 RETURNING 이 빈 결과 반환 → row ID 못 얻음
--   → duration 업데이트 불가, 일부 DB 버전에서 INSERT 자체 롤백
--
-- 실행: Supabase Dashboard → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: 여러 번 실행해도 안전
-- ═══════════════════════════════════════════════════════════════════

-- 사용자: 자신의 page_views SELECT 허용 (INSERT ... RETURNING id 포함)
DROP POLICY IF EXISTS "pv_select_own" ON public.page_views;
CREATE POLICY "pv_select_own" ON public.page_views
  FOR SELECT USING (auth.uid() = user_id);

-- 확인
SELECT policyname, cmd, qual
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'page_views'
ORDER BY cmd, policyname;
