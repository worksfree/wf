-- ================================================================
--  site_config RLS 설정 (2026-07-11)
--  Hub는 인증 전 anon으로 site_config를 읽으므로 SELECT는 전체 허용.
--  WRITE는 admin 역할만 허용.
-- ================================================================

-- 테이블이 아직 없다면 생성 (이미 있으면 무시)
CREATE TABLE IF NOT EXISTS public.site_config (
  key        text PRIMARY KEY,
  value      text,
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.site_config ENABLE ROW LEVEL SECURITY;

-- 기존 정책 초기화 (멱등 실행 보장)
DROP POLICY IF EXISTS "sc_select_all"   ON public.site_config;
DROP POLICY IF EXISTS "sc_write_admin"  ON public.site_config;

-- SELECT: anon 포함 전체 허용 (Hub가 로그인 전에 읽어야 함)
CREATE POLICY "sc_select_all"
  ON public.site_config FOR SELECT
  USING (true);

-- INSERT / UPDATE / DELETE: admin만 허용
CREATE POLICY "sc_write_admin"
  ON public.site_config FOR ALL
  USING     (public.is_admin())
  WITH CHECK (public.is_admin());

-- 확인 쿼리 (실행 후 Results 패널에서 검증)
-- SELECT policyname, cmd, qual FROM pg_policies WHERE tablename = 'site_config';
