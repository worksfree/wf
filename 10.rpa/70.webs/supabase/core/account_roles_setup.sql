-- ══════════════════════════════════════════════════════════════════════
-- WorksFree 계정 역할 설정 및 포트폴리오 데이터 이전
-- Supabase SQL Editor에서 실행하세요
-- ══════════════════════════════════════════════════════════════════════
--
-- 계정 역할 매핑:
--   wfadmin@worksfree.kr      → admin       (자산통합관리 실데이터 접근)
--   partner@worksfree.kr      → partner
--   consultant@worksfree.kr   → consultant
--   member@worksfree.kr       → member      (기본값)
--
-- 실행 순서:
--   STEP 1: 계정 존재 여부 확인
--   STEP 2: profiles 역할 설정
--   STEP 3: 포트폴리오 데이터 이전 (구 관리자 → 신 관리자)
-- ══════════════════════════════════════════════════════════════════════


-- ── STEP 1. 계정 존재 여부 확인 ──────────────────────────────────────
-- 아래 쿼리를 먼저 실행해서 4개 계정이 모두 있는지 확인하세요.
-- 없는 계정은 Supabase Authentication > Users 에서 직접 생성해야 합니다.

SELECT
  email,
  id,
  created_at,
  CASE
    WHEN email = 'wfadmin@worksfree.kr'     THEN '→ 관리자 (admin) 로 설정 예정'
    WHEN email = 'partner@worksfree.kr'     THEN '→ 파트너 (partner) 로 설정 예정'
    WHEN email = 'consultant@worksfree.kr'  THEN '→ 컨설턴트 (consultant) 로 설정 예정'
    WHEN email = 'member@worksfree.kr'      THEN '→ 일반회원 (member) 로 설정 예정'
    WHEN email = 'consultant@worksfree.co.kr' THEN '→ 구 관리자 (포트폴리오 이전 대상)'
    ELSE '기타'
  END AS 처리내용
FROM auth.users
WHERE email IN (
  'wfadmin@worksfree.kr',
  'partner@worksfree.kr',
  'consultant@worksfree.kr',
  'member@worksfree.kr',
  'consultant@worksfree.co.kr'  -- 구 관리자 계정 (데이터 이전 후 역할 제거)
)
ORDER BY email;


-- ── STEP 1-B. 구형 역할명 → 신형 역할명 변환 (기존 사용자 대상) ───────
-- general → member, gfc → partner (ceo/staff → consultant 또는 member 로 변환)
-- 신규 CHECK 제약(member/consultant/partner/admin)에 맞게 정리

UPDATE public.profiles SET role = 'member'     WHERE role = 'general';
UPDATE public.profiles SET role = 'partner'    WHERE role = 'gfc';
UPDATE public.profiles SET role = 'consultant' WHERE role IN ('ceo', 'staff');

-- 변환 결과 확인
SELECT role, COUNT(*) AS 인원수
FROM public.profiles
GROUP BY role
ORDER BY role;


-- ── STEP 2. profiles 역할 설정 ───────────────────────────────────────
-- 계정이 존재하는 것을 확인한 후 실행하세요.
-- ON CONFLICT: profiles 행이 이미 있으면 role만 업데이트, 없으면 새로 삽입

-- 관리자 설정
INSERT INTO public.profiles (id, email, role)
SELECT id, email, 'admin'
FROM auth.users
WHERE email = 'wfadmin@worksfree.kr'
ON CONFLICT (id) DO UPDATE SET role = 'admin';

-- 파트너 설정
INSERT INTO public.profiles (id, email, role)
SELECT id, email, 'partner'
FROM auth.users
WHERE email = 'partner@worksfree.kr'
ON CONFLICT (id) DO UPDATE SET role = 'partner';

-- 컨설턴트 설정
INSERT INTO public.profiles (id, email, role)
SELECT id, email, 'consultant'
FROM auth.users
WHERE email = 'consultant@worksfree.kr'
ON CONFLICT (id) DO UPDATE SET role = 'consultant';

-- 일반회원 설정 (기본값이지만 명시적으로 설정)
INSERT INTO public.profiles (id, email, role)
SELECT id, email, 'member'
FROM auth.users
WHERE email = 'member@worksfree.kr'
ON CONFLICT (id) DO UPDATE SET role = 'member';

-- 구 관리자 역할 제거 (consultant@worksfree.co.kr → member 강등)
UPDATE public.profiles
SET role = 'member'
WHERE id = (SELECT id FROM auth.users WHERE email = 'consultant@worksfree.co.kr' LIMIT 1);


-- ── STEP 3. portfolios 데이터 이전 ──────────────────────────────────
-- 구 관리자(consultant@worksfree.co.kr)의 포트폴리오를
-- 신 관리자(wfadmin@worksfree.kr)로 이전합니다.
--
-- 전제조건:
--   - wfadmin@worksfree.kr 계정이 존재해야 함 (STEP 1에서 확인)
--   - consultant@worksfree.co.kr 계정에 portfolios 데이터가 있어야 함

DO $$
DECLARE
  old_id uuid;
  new_id uuid;
  row_count int;
BEGIN
  -- 구 관리자 UUID 조회
  SELECT id INTO old_id
  FROM auth.users
  WHERE email = 'consultant@worksfree.co.kr'
  LIMIT 1;

  -- 신 관리자 UUID 조회
  SELECT id INTO new_id
  FROM auth.users
  WHERE email = 'wfadmin@worksfree.kr'
  LIMIT 1;

  -- 구 관리자 계정 없음
  IF old_id IS NULL THEN
    RAISE NOTICE '[SKIP] 구 관리자 계정(consultant@worksfree.co.kr)이 없습니다. 이전할 데이터 없음.';
    RETURN;
  END IF;

  -- 구 관리자 portfolios 존재 여부 확인
  SELECT COUNT(*) INTO row_count FROM public.portfolios WHERE user_id = old_id;
  IF row_count = 0 THEN
    RAISE NOTICE '[SKIP] 구 관리자의 portfolios 데이터가 없습니다.';
    RETURN;
  END IF;

  -- 신 관리자 계정 없음
  IF new_id IS NULL THEN
    RAISE EXCEPTION '[ERROR] 신 관리자 계정(wfadmin@worksfree.kr)이 없습니다. Authentication > Users에서 먼저 계정을 생성하세요.';
  END IF;

  -- 신 관리자에 이미 portfolios 행이 있으면 삭제 (PK 충돌 방지)
  DELETE FROM public.portfolios WHERE user_id = new_id;

  -- portfolios 이전: user_id를 구 → 신 관리자로 변경
  UPDATE public.portfolios
  SET user_id = new_id
  WHERE user_id = old_id;

  GET DIAGNOSTICS row_count = ROW_COUNT;
  RAISE NOTICE '[OK] portfolios 이전 완료: % 행 이전됨 (% → %)', row_count, old_id, new_id;
END $$;


-- ── STEP 4. 결과 검증 ────────────────────────────────────────────────
-- 위 스텝 실행 후 아래 쿼리로 최종 상태를 확인하세요.

SELECT
  u.email,
  p.role,
  CASE WHEN po.user_id IS NOT NULL THEN '있음' ELSE '없음' END AS 포트폴리오,
  p.agreed_at IS NOT NULL AS 동의완료
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
LEFT JOIN public.portfolios po ON po.user_id = u.id
WHERE u.email IN (
  'wfadmin@worksfree.kr',
  'partner@worksfree.kr',
  'consultant@worksfree.kr',
  'member@worksfree.kr',
  'consultant@worksfree.co.kr'
)
ORDER BY
  CASE p.role
    WHEN 'admin' THEN 1
    WHEN 'partner' THEN 2
    WHEN 'consultant' THEN 3
    WHEN 'member' THEN 4
    ELSE 5
  END;
