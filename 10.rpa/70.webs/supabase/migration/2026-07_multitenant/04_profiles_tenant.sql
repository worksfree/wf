-- ================================================================
-- 04_profiles_tenant.sql — profiles.tenant_id + 관리자 승격 차단 (핵심 단계)
--
-- 반드시 03 실행 후에 실행하세요 (tenants 에 lifeart.ai.kr 행 필요).
--
-- 이 단계가 하는 일:
--  ① profiles 에 tenant_id(uuid FK) 추가, 기존 전 행을 worksfree.kr 로 백필
--  ② is_admin() 을 "worksfree 테넌트의 admin"으로 재정의
--  ③ admin_* RPC 6종의 인라인 role 체크를 is_admin() 호출로 교체
--     → 이거 없이는 LifeArt 관리자(role='admin')가 허브 관리자 RPC를
--       전부 쓸 수 있게 되는 권한 상승 구멍이 생김
--  ④ is_lifeart_admin() 생성 (LifeArt 테이블 RLS 에서 사용)
--
-- 기존 허브 관리자(wfadmin 등)는 전원 worksfree 로 백필되므로 동작 불변.
-- ================================================================

-- ① 컬럼 추가 + 백필
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);

UPDATE public.profiles
SET tenant_id = (SELECT id FROM public.tenants WHERE domain = 'worksfree.kr')
WHERE tenant_id IS NULL;

-- 백필 완료 확인 후 NOT NULL 강제 (아래 SELECT 가 0 이어야 함 — 0이 아니면 STOP)
SELECT COUNT(*) AS must_be_zero FROM public.profiles WHERE tenant_id IS NULL;

ALTER TABLE public.profiles ALTER COLUMN tenant_id SET NOT NULL;

-- 신규 가입 트리거(handle_new_user)가 tenant_id 를 넣지 않으므로 DEFAULT 필요.
-- 허브 가입이 대부분이므로 worksfree 를 DEFAULT 로, LifeArt 는 클라이언트가 명시 갱신.
DO $$
DECLARE wf_id uuid;
BEGIN
  SELECT id INTO wf_id FROM public.tenants WHERE domain = 'worksfree.kr';
  EXECUTE format('ALTER TABLE public.profiles ALTER COLUMN tenant_id SET DEFAULT %L', wf_id);
END $$;

-- ② is_admin() 재정의 — 허브(worksfree.kr) 테넌트의 admin 만 true
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
      AND role = 'admin'
      AND tenant_id = (SELECT id FROM public.tenants WHERE domain = 'worksfree.kr')
  );
$$;

-- ④ is_lifeart_admin() — LifeArt 테넌트의 admin 만 true
CREATE OR REPLACE FUNCTION public.is_lifeart_admin()
RETURNS BOOLEAN
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
      AND role = 'admin'
      AND tenant_id = (SELECT id FROM public.tenants WHERE domain = 'lifeart.ai.kr')
  );
$$;
GRANT EXECUTE ON FUNCTION public.is_lifeart_admin() TO authenticated, anon;

-- ③ admin RPC 6종 — 인라인 체크를 is_admin() 으로 교체 (본문 나머지는 원본 그대로)

-- admin_set_user_role
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_id UUID, new_role TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF NOT public.is_admin() THEN RETURN 'error: not_admin'; END IF;
  IF new_role NOT IN ('member', 'consultant', 'partner') THEN
    RETURN 'error: invalid_role';
  END IF;
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  UPDATE auth.users
  SET raw_app_meta_data = jsonb_set(
    COALESCE(raw_app_meta_data, '{}'),
    '{wf_role}',
    to_jsonb(new_role)
  )
  WHERE id = target_id;
  RETURN 'ok';
END;
$$;

-- admin_set_user_name
CREATE OR REPLACE FUNCTION public.admin_set_user_name(target_id UUID, new_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF NOT public.is_admin() THEN RETURN 'error: not_admin'; END IF;
  IF new_name IS NULL OR trim(new_name) = '' THEN RETURN 'error: empty_name'; END IF;
  UPDATE public.profiles SET name = trim(new_name) WHERE id = target_id;
  UPDATE auth.users
  SET raw_user_meta_data = jsonb_set(
    COALESCE(raw_user_meta_data, '{}'),
    '{full_name}',
    to_jsonb(trim(new_name))
  )
  WHERE id = target_id;
  RETURN 'ok';
END;
$$;

-- admin_get_all_profiles
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (
  id        UUID,
  email     TEXT,
  name      TEXT,
  role      TEXT,
  agreed_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF NOT public.is_admin() THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM   public.profiles p
    ORDER  BY p.agreed_at DESC NULLS LAST;
END;
$$;

-- admin_get_user_logins
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF NOT public.is_admin() THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM   auth.users au;
END;
$$;

-- admin_grant_credits
CREATE OR REPLACE FUNCTION public.admin_grant_credits(
  target_id UUID,
  amount    INT,
  env_name  TEXT DEFAULT 'portal'
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  IF NOT public.is_admin() THEN RETURN 'error: not_admin'; END IF;
  IF amount < 1 THEN RETURN 'error: invalid_amount'; END IF;
  INSERT INTO public.credits (user_id, delta, reason, note, env, created_at)
  VALUES (target_id, amount, 'admin_grant', '관리자 수동 지급', env_name, NOW());
  RETURN 'ok';
END;
$$;

-- admin_page_view_stats
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
  _envs TEXT[];
BEGIN
  IF NOT public.is_admin() THEN RETURN; END IF;
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

-- ── 검증 ──
-- (a) 백필 완료: 0 이어야 함
SELECT COUNT(*) AS must_be_zero FROM public.profiles WHERE tenant_id IS NULL;

-- (b) 테넌트별 분포: 전원 worksfree.kr 이어야 함 (LifeArt 행은 아직 0)
SELECT t.domain, COUNT(*)
FROM public.profiles p JOIN public.tenants t ON t.id = p.tenant_id
GROUP BY t.domain;

-- (c) 회귀: wfadmin@worksfree.kr 로 로그인한 브라우저에서 admin/users 페이지가
--     00 스냅샷과 동일하게 표시되는지 확인.

-- (d) 승격 차단 확인 (선택이지만 강력 추천):
--     임시로 아무 테스트 계정의 profiles 행을
--       role='admin', tenant_id=(SELECT id FROM tenants WHERE domain='lifeart.ai.kr')
--     로 바꾼 뒤 그 계정으로 admin_get_all_profiles() 호출 → 빈 결과여야 함.
--     확인 후 원복하세요.
