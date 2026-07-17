-- ================================================================
-- 19_hub_node_tenant_consistency.sql
--   허브 노드 tenant_id 일관성 정리 — "공유 DB에 행을 쓰는 모든 테이블은
--   tenant_id uuid REFERENCES tenants(id) 를 가진다"는 표준(→ CLAUDE.md)에 맞춰
--   누락돼 있던 3개 테이블을 정비한다.
--
--   반드시 03(tenants)·04(profiles.tenant_id/is_admin) 실행 후.
--
--   대상 (실측 근거):
--    · esg_reports        — 사용자별 진단 데이터(user_id). 인증 클라이언트가 insert.
--                           → 소유자+테넌트 RLS (asset/portfolios 와 동일 패턴)
--    · jobkorea_proposals — 아웃리치 로그. 외부/Worker(service_role) 기록, 관리자 조회.
--    · jobkorea_stats     — 집계. 위와 동일.
--                           → 쓰기 클라이언트 정책 없음(service_role 전용), 읽기는 관리자+테넌트
--    · page_views         — 분석 로그(env 로 표면 구분). tenant_id 추가로 테넌트별 분석 가능.
--
--   규약: tenant_id uuid NOT NULL REFERENCES tenants(id).
--         DEFAULT 는 worksfree.kr 테넌트(기존 데이터/기존 호출부 무변경 보장).
--         DEFAULT 에 서브쿼리를 못 쓰므로 worksfree UUID 를 명시(03 검증에서 확인된 값).
-- ================================================================

-- 안전장치: worksfree 테넌트 UUID 가 기대값과 일치하는지 먼저 확인(다르면 즉시 중단)
DO $$
DECLARE wf uuid;
BEGIN
  SELECT id INTO wf FROM public.tenants WHERE domain = 'worksfree.kr';
  IF wf IS NULL THEN
    RAISE EXCEPTION '19: worksfree.kr 테넌트가 없음 — 03 을 먼저 실행하세요';
  END IF;
  IF wf <> '91aadb9a-2bca-4f34-8125-4f33c00fc636' THEN
    RAISE EXCEPTION '19: worksfree UUID 불일치(%). 아래 DEFAULT 상수를 실제 값으로 바꿔 다시 실행', wf;
  END IF;
END $$;

-- ── ① esg_reports — 사용자별 데이터 (소유자+테넌트 RLS) ──────────────
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='esg_reports') THEN
    ALTER TABLE public.esg_reports
      ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
    UPDATE public.esg_reports
      SET tenant_id = (SELECT id FROM public.tenants WHERE domain='worksfree.kr')
      WHERE tenant_id IS NULL;
    ALTER TABLE public.esg_reports
      ALTER COLUMN tenant_id SET DEFAULT '91aadb9a-2bca-4f34-8125-4f33c00fc636'::uuid;
    ALTER TABLE public.esg_reports ALTER COLUMN tenant_id SET NOT NULL;
    ALTER TABLE public.esg_reports ENABLE ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS "esg_own_tenant"    ON public.esg_reports;
    DROP POLICY IF EXISTS "esg_admin_tenant"  ON public.esg_reports;
    -- 본인 + 본인 테넌트만 (읽기/쓰기)
    CREATE POLICY "esg_own_tenant" ON public.esg_reports FOR ALL
      USING (auth.uid() = user_id
             AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()))
      WITH CHECK (auth.uid() = user_id
             AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));
    -- 같은 테넌트 관리자는 조회 가능(대시보드용)
    CREATE POLICY "esg_admin_tenant" ON public.esg_reports FOR SELECT
      USING (public.is_admin()
             AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));
  END IF;
END $$;

-- ── ② jobkorea_proposals / jobkorea_stats — Worker 기록 · 관리자 조회 ──
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['jobkorea_proposals','jobkorea_stats'] LOOP
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=t) THEN
      EXECUTE format('ALTER TABLE public.%I ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id)', t);
      EXECUTE format('UPDATE public.%I SET tenant_id=(SELECT id FROM public.tenants WHERE domain=''worksfree.kr'') WHERE tenant_id IS NULL', t);
      EXECUTE format('ALTER TABLE public.%I ALTER COLUMN tenant_id SET DEFAULT ''91aadb9a-2bca-4f34-8125-4f33c00fc636''::uuid', t);
      EXECUTE format('ALTER TABLE public.%I ALTER COLUMN tenant_id SET NOT NULL', t);
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
      EXECUTE format('DROP POLICY IF EXISTS "jk_admin_tenant" ON public.%I', t);
      -- 읽기: 같은 테넌트 관리자만. 쓰기: 정책 없음 → service_role(Worker) 전용
      EXECUTE format($f$CREATE POLICY "jk_admin_tenant" ON public.%I FOR SELECT
        USING (public.is_admin()
               AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()))$f$, t);
    END IF;
  END LOOP;
END $$;

-- ── ③ page_views — 분석 로그. tenant_id 추가(테넌트별 분석 가능) ───────
--   env(표면 구분: portal/asset…)는 유지. 클라이언트 insert 는 tenant_id 미지정 →
--   DEFAULT(worksfree)로 채워져 기존 호출부 무변경. (테넌트별 태깅은 코드 후속)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='page_views') THEN
    ALTER TABLE public.page_views
      ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
    UPDATE public.page_views
      SET tenant_id = (SELECT id FROM public.tenants WHERE domain='worksfree.kr')
      WHERE tenant_id IS NULL;
    ALTER TABLE public.page_views
      ALTER COLUMN tenant_id SET DEFAULT '91aadb9a-2bca-4f34-8125-4f33c00fc636'::uuid;
    ALTER TABLE public.page_views ALTER COLUMN tenant_id SET NOT NULL;
    -- 관리자 조회를 테넌트 스코프로 강화(기존 pv_admin_select 대체)
    DROP POLICY IF EXISTS "pv_admin_select"        ON public.page_views;
    DROP POLICY IF EXISTS "pv_admin_select_tenant" ON public.page_views;
    CREATE POLICY "pv_admin_select_tenant" ON public.page_views FOR SELECT
      USING (public.is_admin()
             AND tenant_id = (SELECT tenant_id FROM public.profiles WHERE id = auth.uid()));
  END IF;
END $$;

-- ── 검증 ──
-- (a) 세 계열 tenant_id NULL 0건 + NOT NULL 여부
SELECT table_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public' AND column_name='tenant_id'
  AND table_name IN ('esg_reports','jobkorea_proposals','jobkorea_stats','page_views')
ORDER BY table_name;

-- (b) 정책 목록
SELECT tablename, policyname, cmd FROM pg_policies
WHERE schemaname='public'
  AND tablename IN ('esg_reports','jobkorea_proposals','jobkorea_stats','page_views')
ORDER BY tablename, cmd;

-- (c) 회귀: esg 진단 저장 → esg_reports 에 tenant_id 붙어 저장되는지 /
--     jobkorea 관리자 페이지 목록 표시 / 분석(page_views) 기록 정상.
