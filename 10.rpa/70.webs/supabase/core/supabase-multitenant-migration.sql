-- ================================================================
--  WorksFree 멀티테넌트 마이그레이션
--  실행 위치: Supabase Dashboard → SQL Editor
--  순서대로 실행하세요.
-- ================================================================

-- ① tenants 테이블 (도메인별 테넌트)
CREATE TABLE IF NOT EXISTS public.tenants (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain     text UNIQUE NOT NULL,     -- 'worksfree.kr', 'client1.com' 등 루트 도메인
  name       text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- WorksFree 기본 테넌트 등록
INSERT INTO public.tenants (domain, name)
VALUES ('worksfree.kr', 'WorksFree')
ON CONFLICT (domain) DO NOTHING;

-- ② portfolios 테이블에 tenant_id 추가 (이미 있으면 무시)
ALTER TABLE public.portfolios ADD COLUMN IF NOT EXISTS
  tenant_id uuid REFERENCES public.tenants(id);

-- 기존 행 → WorksFree 테넌트로 백필
UPDATE public.portfolios
SET tenant_id = (SELECT id FROM public.tenants WHERE domain = 'worksfree.kr')
WHERE tenant_id IS NULL;

-- (선택) UNIQUE 제약: 테넌트 내 user당 1개
ALTER TABLE public.portfolios DROP CONSTRAINT IF EXISTS portfolios_user_id_key;
ALTER TABLE public.portfolios DROP CONSTRAINT IF EXISTS portfolios_tenant_user_key;
ALTER TABLE public.portfolios ADD CONSTRAINT portfolios_tenant_user_key
  UNIQUE (tenant_id, user_id);

-- ③ 종목별 일별 시세 스냅샷
CREATE TABLE IF NOT EXISTS public.stock_snapshots (
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  date      date NOT NULL,
  code      text NOT NULL,
  price     numeric NOT NULL,
  PRIMARY KEY (tenant_id, date, code)
);

-- ④ 포트폴리오 일별 총평가액 (구성 변경 시 왜곡 방지용)
CREATE TABLE IF NOT EXISTS public.portfolio_daily (
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  user_id   uuid NOT NULL,
  date      date NOT NULL,
  total     numeric NOT NULL,
  PRIMARY KEY (tenant_id, user_id, date)
);

-- ⑤ 분배금 이력 (per 종목, JSONB로 payments 배열 저장)
CREATE TABLE IF NOT EXISTS public.dividends (
  tenant_id   uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL,
  code        text NOT NULL,
  payments    jsonb NOT NULL DEFAULT '[]',
  last_synced date,
  updated_at  timestamptz DEFAULT now(),
  PRIMARY KEY (tenant_id, user_id, code)
);

-- ================================================================
--  RLS — Supabase Auth 토큰 사용 확인 (2026-07-11 활성화)
--  consulting/asset/index.html 은 sbHeaders()로 Bearer 토큰을 포함하므로
--  인증된 사용자의 접근은 그대로 허용됨.
-- ================================================================
ALTER TABLE public.stock_snapshots  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_daily  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dividends        ENABLE ROW LEVEL SECURITY;

-- stock_snapshots: 시세 데이터 (PII 없음) — 인증 사용자 전체 접근 허용
DROP POLICY IF EXISTS "snap_authenticated" ON public.stock_snapshots;
CREATE POLICY "snap_authenticated"
  ON public.stock_snapshots FOR ALL
  USING     (auth.uid() IS NOT NULL)
  WITH CHECK (auth.uid() IS NOT NULL);

-- portfolio_daily: 일별 총평가액 — 본인 데이터만
DROP POLICY IF EXISTS "본인 테넌트만" ON public.portfolio_daily;
DROP POLICY IF EXISTS "daily_own"    ON public.portfolio_daily;
CREATE POLICY "daily_own"
  ON public.portfolio_daily FOR ALL
  USING     (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- dividends: 분배금 이력 — 본인 데이터만
DROP POLICY IF EXISTS "본인 테넌트만" ON public.dividends;
DROP POLICY IF EXISTS "div_own"      ON public.dividends;
CREATE POLICY "div_own"
  ON public.dividends FOR ALL
  USING     (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
