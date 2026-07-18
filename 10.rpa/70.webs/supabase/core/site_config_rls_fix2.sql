-- ================================================================
--  site_config_rls_fix2.sql — sc_write_admin 정책 교체
--  문제: is_admin()이 tenant_id까지 체크하는데, profiles.tenant_id가
--        NULL이면 항상 false 반환 → "new row violates RLS" 오류
--  해결: is_admin() 대신 profiles.role = 'admin' 직접 체크
--  실행: Supabase Dashboard → SQL Editor (멱등, 여러 번 안전)
-- ================================================================

DROP POLICY IF EXISTS "sc_write_admin" ON public.site_config;

CREATE POLICY "sc_write_admin"
  ON public.site_config FOR ALL
  USING (
    auth.uid() IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    auth.uid() IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- 적용 확인
SELECT policyname, cmd, qual
FROM pg_policies
WHERE tablename = 'site_config';

-- 현재 로그인 사용자의 profiles 확인 (실행 시점에 세션 있어야 함)
-- SELECT id, role, tenant_id FROM public.profiles WHERE id = auth.uid();
