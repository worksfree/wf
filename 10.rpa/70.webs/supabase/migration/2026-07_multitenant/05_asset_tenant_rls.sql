-- ================================================================
-- 05_asset_tenant_rls.sql — 자산관리(ETF) 테넌트 격리 강화
--
-- 반드시 04 실행 후 (profiles.tenant_id 필요).
-- 유일한 클라이언트 = consulting/asset/index.html (anon 키 + 사용자 JWT).
-- 모든 쓰기에 tenant_id 명시 전달, 관리자만 스냅샷 쓰기 → 아래 정책과 정합.
--
-- 기존 사용자/행이 전부 worksfree 이므로 조건 추가해도 동작 불변.
-- ================================================================

-- portfolios: tenant_id 컬럼 없으면 추가 + 백필 (multitenant-migration 이 이미 넣었을 수 있음)
ALTER TABLE public.portfolios ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
UPDATE public.portfolios
SET tenant_id = (SELECT id FROM public.tenants WHERE domain='worksfree.kr')
WHERE tenant_id IS NULL;

-- portfolios: 본인 + 본인 테넌트
DROP POLICY IF EXISTS "own portfolio only" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_own_tenant" ON public.portfolios;
CREATE POLICY "portfolios_own_tenant" ON public.portfolios FOR ALL
  USING (auth.uid() = user_id
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()))
  WITH CHECK (auth.uid() = user_id
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));

-- portfolio_daily: 본인 + 본인 테넌트
DROP POLICY IF EXISTS "본인 테넌트만" ON public.portfolio_daily;
DROP POLICY IF EXISTS "daily_own"     ON public.portfolio_daily;
DROP POLICY IF EXISTS "daily_own_tenant" ON public.portfolio_daily;
CREATE POLICY "daily_own_tenant" ON public.portfolio_daily FOR ALL
  USING (auth.uid() = user_id
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()))
  WITH CHECK (auth.uid() = user_id
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));

-- dividends: 본인 + 본인 테넌트
DROP POLICY IF EXISTS "본인 테넌트만" ON public.dividends;
DROP POLICY IF EXISTS "div_own"       ON public.dividends;
DROP POLICY IF EXISTS "div_own_tenant" ON public.dividends;
CREATE POLICY "div_own_tenant" ON public.dividends FOR ALL
  USING (auth.uid() = user_id
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()))
  WITH CHECK (auth.uid() = user_id
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));

-- stock_snapshots: 읽기는 인증 사용자 전체(시세, PII 없음) 유지,
--   쓰기는 관리자 + 관리자 테넌트로 제한 (현 클라이언트가 sbIsAdmin 게이트로 upsert 하므로 정합)
DROP POLICY IF EXISTS "snap_authenticated" ON public.stock_snapshots;
DROP POLICY IF EXISTS "snap_read"  ON public.stock_snapshots;
DROP POLICY IF EXISTS "snap_write" ON public.stock_snapshots;
CREATE POLICY "snap_read" ON public.stock_snapshots FOR SELECT
  USING (auth.uid() IS NOT NULL);
CREATE POLICY "snap_write" ON public.stock_snapshots FOR ALL
  USING (public.is_admin()
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()))
  WITH CHECK (public.is_admin()
         AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));

-- 참고: portfolios PK 가 (user_id) 단독이라 테넌트당 1행 제약이 남아있음.
--       현재 단일 테넌트라 문제 없음. 복합 PK 재설계는 별도 승인 후 진행(문서화만).

-- ── 검증 ──
SELECT COUNT(*) AS portfolios_null_tenant FROM public.portfolios WHERE tenant_id IS NULL; -- 0
SELECT tablename, policyname, cmd FROM pg_policies
WHERE schemaname='public'
  AND tablename IN ('portfolios','portfolio_daily','dividends','stock_snapshots')
ORDER BY tablename, cmd;
-- 회귀: consulting/asset 페이지 로그인 후 포트폴리오 로드/저장/스냅샷/배당 정상 동작 확인.
