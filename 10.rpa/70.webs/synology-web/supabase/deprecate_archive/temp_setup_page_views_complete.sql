-- ═══════════════════════════════════════════════════════════════════
-- setup_page_views_complete.sql
-- page_views 테이블 + RLS 정책 완전 재설정 (진단 포함)
--
-- 실행: Supabase Dashboard → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: 여러 번 실행해도 안전
-- ═══════════════════════════════════════════════════════════════════

-- ── 0. 실행 전 진단 ───────────────────────────────────────────────
-- (이 SELECT 결과를 Claude에게 공유하면 원인 파악 가능)
SELECT
  current_user                                            AS "현재 유저",
  (SELECT COUNT(*) FROM information_schema.tables
   WHERE table_schema = 'public' AND table_name = 'page_views')  AS "테이블 존재(1=예)",
  COALESCE((
    SELECT relrowsecurity::text
    FROM   pg_class c
    JOIN   pg_namespace n ON n.oid = c.relnamespace
    WHERE  c.relname = 'page_views' AND n.nspname = 'public'
  ), 'table_missing')                                    AS "RLS 활성화",
  (SELECT COUNT(*) FROM pg_policies
   WHERE  schemaname = 'public' AND tablename = 'page_views')    AS "정책 수(실행 전)";


-- ── 1. 테이블 생성 (없으면) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.page_views (
  id         BIGSERIAL   PRIMARY KEY,
  user_id    UUID        REFERENCES public.profiles (id) ON DELETE SET NULL,
  page       TEXT        NOT NULL,
  duration_s INT,
  env        TEXT        DEFAULT 'portal',
  viewed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS page_views_page_viewed_at ON public.page_views (page, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_user_viewed_at ON public.page_views (user_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS page_views_viewed_at      ON public.page_views (viewed_at DESC);

-- ── 2. RLS 활성화 ────────────────────────────────────────────────
ALTER TABLE public.page_views ENABLE ROW LEVEL SECURITY;

-- ── 3. 기존 정책 전부 삭제 후 재생성 ─────────────────────────────
DROP POLICY IF EXISTS "pv_insert_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_select_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_update_own"   ON public.page_views;
DROP POLICY IF EXISTS "pv_admin_select" ON public.page_views;

-- 사용자: 자신의 행 INSERT
CREATE POLICY "pv_insert_own" ON public.page_views
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 사용자: 자신의 행 SELECT (INSERT ... RETURNING 포함)
CREATE POLICY "pv_select_own" ON public.page_views
  FOR SELECT USING (auth.uid() = user_id);

-- 사용자: 자신의 행 UPDATE (체류 시간 기록)
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

-- ── 4. 최종 확인 (4개 정책 + RLS 상태 한번에 표시) ────────────────
SELECT
  CASE WHEN pol_cnt = 4
    THEN '✅ 완료 — 4개 정책 생성됨, 트래킹 준비 완료'
    ELSE '❌ 이상: 정책 ' || pol_cnt || '개 (4개 필요). 위 단계에서 오류 발생한 것 같음'
  END                  AS "결과",
  rls_on::text         AS "RLS 활성화",
  pol_cnt::text        AS "정책 수",
  current_user         AS "실행 유저"
FROM (
  SELECT
    (SELECT COUNT(*) FROM pg_policies
     WHERE schemaname = 'public' AND tablename = 'page_views') AS pol_cnt,
    (SELECT relrowsecurity
     FROM   pg_class c
     JOIN   pg_namespace n ON n.oid = c.relnamespace
     WHERE  c.relname = 'page_views' AND n.nspname = 'public') AS rls_on
) sub;

-- 정책 목록도 함께 표시
SELECT policyname AS "정책명", cmd AS "명령"
FROM   pg_policies
WHERE  schemaname = 'public' AND tablename = 'page_views'
ORDER  BY cmd, policyname;
