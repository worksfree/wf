-- ═══════════════════════════════════════════════════════════════════
-- 40_functions.sql
-- WorksFree Hub — [4단계] 관리자 함수 + 일반 함수
--
-- 실행 순서: 4/7  (30_triggers.sql 이후)
-- 다음 단계: 50_views.sql
--
-- 포함 내용:
-- [관리자 전용 — SECURITY DEFINER, 관리자만 결과 반환]
--   - admin_set_user_role    : 역할 변경 (admin 제외)
--   - admin_grant_credits    : 크레딧 수동 지급
--   - admin_set_user_name    : 이름 변경
--   - admin_get_all_profiles : 전체 회원 목록 조회
--   - admin_get_user_logins  : 마지막 로그인 시각 조회
--   - admin_page_view_stats  : 페이지뷰 통계 (env 필터 포함)
-- [일반 함수]
--   - get_user_credit_balance : 크레딧 잔액 조회
--   - deduct_credits           : 크레딧 차감 (서버 측 전용)
--   - get_email_history        : 수신자별 발송 이력 조회
-- ═══════════════════════════════════════════════════════════════════

-- ══════════════════════════════════════════════════════════════════════
-- 관리자 전용 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── admin_set_user_role ───────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_role(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_role(target_id UUID, new_role TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  -- 'admin' 역할은 DB 직접 수정만 허용
  IF new_role NOT IN ('general', 'consultant', 'gfc', 'ceo', 'staff') THEN
    RETURN 'error: invalid_role';
  END IF;
  UPDATE public.profiles SET role = new_role WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_role(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(UUID, TEXT) TO anon, authenticated;


-- ── admin_grant_credits ────────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INT, TEXT);
DROP FUNCTION IF EXISTS public.admin_grant_credits(UUID, INTEGER, TEXT);
CREATE OR REPLACE FUNCTION public.admin_grant_credits(
  target_id UUID,
  amount    INT,
  env_name  TEXT DEFAULT 'portal'
)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF amount < 1 THEN RETURN 'error: invalid_amount'; END IF;
  INSERT INTO public.credits (user_id, delta, reason, note, env, created_at)
  VALUES (target_id, amount, 'admin_grant', '관리자 수동 지급', env_name, NOW());
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_grant_credits(UUID, INT, TEXT) TO anon, authenticated;


-- ── admin_set_user_name ────────────────────────────────────────────────
DROP FUNCTION IF EXISTS public.admin_set_user_name(UUID, TEXT);
CREATE OR REPLACE FUNCTION public.admin_set_user_name(target_id UUID, new_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _caller_role TEXT;
BEGIN
  SELECT role INTO _caller_role FROM public.profiles WHERE id = auth.uid();
  IF _caller_role IS DISTINCT FROM 'admin' THEN RETURN 'error: not_admin'; END IF;
  IF new_name IS NULL OR trim(new_name) = '' THEN RETURN 'error: empty_name'; END IF;
  UPDATE public.profiles SET name = trim(new_name) WHERE id = target_id;
  RETURN 'ok';
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_set_user_name(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_name(UUID, TEXT) TO anon, authenticated;


-- ── admin_get_all_profiles ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (
  id        UUID,
  email     TEXT,
  name      TEXT,
  role      TEXT,
  agreed_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT p.id, p.email, p.name, p.role, p.agreed_at
    FROM   public.profiles p
    ORDER  BY p.agreed_at DESC NULLS LAST;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_all_profiles() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles() TO anon, authenticated;


-- ── admin_get_user_logins ──────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_user_logins()
RETURNS TABLE (
  id              UUID,
  last_sign_in_at TIMESTAMPTZ
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _r TEXT;
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
  RETURN QUERY
    SELECT au.id::UUID, au.last_sign_in_at
    FROM   auth.users au;
END;
$$;
REVOKE ALL    ON FUNCTION public.admin_get_user_logins() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_get_user_logins() TO anon, authenticated;


-- ── admin_page_view_stats ──────────────────────────────────────────────
--   env_filter = NULL → ['staging','portal'] 기본값
DROP FUNCTION IF EXISTS public.admin_page_view_stats(INT);
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
  _r    TEXT;
  _envs TEXT[];
BEGIN
  SELECT role INTO _r FROM public.profiles WHERE id = auth.uid();
  IF _r IS DISTINCT FROM 'admin' THEN RETURN; END IF;
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
REVOKE ALL    ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_page_view_stats(INT, TEXT[]) TO anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════
-- 일반 함수
-- ══════════════════════════════════════════════════════════════════════

-- ── get_user_credit_balance ────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.get_user_credit_balance(p_user_id UUID)
RETURNS INTEGER
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COALESCE(SUM(delta), 0)::INT FROM public.credits WHERE user_id = p_user_id;
$$;


-- ── deduct_credits — 앱 사용 크레딧 차감 (서버 측 전용) ───────────────
CREATE OR REPLACE FUNCTION public.deduct_credits(
  p_user_id UUID,
  p_amount  INTEGER,
  p_app_id  TEXT,
  p_note    TEXT DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_balance INTEGER;
BEGIN
  SELECT get_user_credit_balance(p_user_id) INTO v_balance;
  IF v_balance < p_amount THEN
    RAISE EXCEPTION 'insufficient_credits: balance=%, required=%', v_balance, p_amount;
  END IF;
  INSERT INTO public.credits (user_id, delta, reason, app_id, note)
  VALUES (p_user_id, -p_amount, 'use_app', p_app_id, p_note);
  RETURN v_balance - p_amount;
END;
$$;


-- ── get_email_history — 수신자별 발송 이력 조회 ────────────────────────
CREATE OR REPLACE FUNCTION public.get_email_history(
  p_email TEXT,
  p_limit INT DEFAULT 10
)
RETURNS TABLE (
  sent_at     TIMESTAMPTZ,
  flyer_name  TEXT,
  sender_name TEXT,
  subject     TEXT,
  env         TEXT
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT sent_at, flyer_name, sender_name, subject, env
  FROM   public.email_log
  WHERE  recipient_email = lower(p_email)
  ORDER  BY sent_at DESC
  LIMIT  p_limit;
$$;


-- ══════════════════════════════════════════════════════════════════════
-- 검증
-- ══════════════════════════════════════════════════════════════════════
SELECT routine_name
FROM   information_schema.routines
WHERE  routine_schema = 'public'
  AND  routine_name IN (
    'is_admin', 'admin_set_user_role', 'admin_grant_credits', 'admin_set_user_name',
    'admin_get_all_profiles', 'admin_get_user_logins', 'admin_page_view_stats',
    'get_user_credit_balance', 'deduct_credits', 'get_email_history'
  )
ORDER  BY routine_name;
