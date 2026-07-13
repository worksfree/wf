-- ══════════════════════════════════════════════════════════════════════
-- admin_data_protection.sql
-- WorksFree Hub — profiles 데이터 보호 및 복구 도구
-- Supabase SQL Editor에서 필요한 STEP만 선택 실행하세요
-- ══════════════════════════════════════════════════════════════════════
--
-- STEP D1 : 현황 진단 (파괴 없음, 항상 먼저 실행)
-- STEP D2 : profiles 백업 테이블 생성 (profiles_backup_YYYYMMDD)
-- STEP D3 : auth.users에 있지만 profiles 없는 계정 목록 확인
-- STEP D4 : 누락 profiles 일괄 생성 (백필)
-- STEP D5 : 구형 역할명 → 신형 역할명 안전 변환
-- STEP D6 : 복구 후 최종 검증
-- ══════════════════════════════════════════════════════════════════════


-- ══════════════════════════════════════════════════════════════════════
-- STEP D1. 현황 진단 (파괴적 작업 없음 — 언제든 안전하게 실행)
-- ══════════════════════════════════════════════════════════════════════

-- [D1-A] 전체 사용자 수 비교
SELECT
  'auth.users'    AS 테이블,
  COUNT(*)        AS 총_계정수
FROM auth.users
UNION ALL
SELECT
  'profiles'      AS 테이블,
  COUNT(*)        AS 총_행수
FROM public.profiles;

-- [D1-B] profiles 역할 분포 (기대값: member/consultant/partner/admin)
SELECT
  COALESCE(role, '(NULL)') AS 역할,
  COUNT(*)                  AS 인원수
FROM public.profiles
GROUP BY role
ORDER BY 인원수 DESC;

-- [D1-C] auth.users 중 profiles 행이 없는 계정 (고아 계정 — 백필 대상)
SELECT
  u.email,
  u.id,
  u.created_at AS 가입일,
  u.last_sign_in_at AS 마지막로그인
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE p.id IS NULL
ORDER BY u.created_at;

-- [D1-D] admin 권한 확인 (조회가 되면 현재 접속 계정이 관리자)
SELECT
  p.email,
  p.role,
  p.agreed_at
FROM public.profiles p
WHERE p.id = auth.uid();


-- ══════════════════════════════════════════════════════════════════════
-- STEP D2. profiles 백업 (중요 작업 전 반드시 실행)
-- 실행할 때마다 새 백업 테이블 생성 — 멱등하지 않으므로 날짜 바꿔서 실행
-- ══════════════════════════════════════════════════════════════════════

-- 오늘 날짜를 테이블 이름에 포함 (예: profiles_backup_20260630)
-- ⚠ 이미 같은 이름의 테이블이 있으면 에러 발생 — 아래 DROP 주석 해제 후 실행
-- DROP TABLE IF EXISTS public.profiles_backup_20260630;

CREATE TABLE public.profiles_backup_20260630 AS
SELECT * FROM public.profiles;

-- 백업 확인
SELECT COUNT(*) AS 백업_행수, '백업 완료' AS 상태
FROM public.profiles_backup_20260630;


-- ══════════════════════════════════════════════════════════════════════
-- STEP D3. 고아 계정 확인 (profiles 없는 auth.users)
-- ══════════════════════════════════════════════════════════════════════

SELECT
  u.email,
  u.id,
  u.created_at                              AS 가입일,
  u.raw_user_meta_data->>'full_name'        AS 이름
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE p.id IS NULL
ORDER BY u.created_at;


-- ══════════════════════════════════════════════════════════════════════
-- STEP D4. 누락 profiles 일괄 생성 (백필)
-- ON CONFLICT → 기존 profiles 행은 절대 덮어쓰지 않음 (안전)
-- ══════════════════════════════════════════════════════════════════════

INSERT INTO public.profiles (id, email, name, role)
SELECT
  u.id,
  u.email,
  COALESCE(
    u.raw_user_meta_data->>'full_name',
    u.raw_user_meta_data->>'name'
  ),
  'member'   -- 기본 역할 (이후 D5에서 역할 조정 가능)
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE p.id IS NULL   -- profiles가 없는 계정만
ON CONFLICT (id) DO NOTHING;   -- 혹시 모를 경쟁 조건 방지

-- 백필 결과 확인
SELECT COUNT(*) AS 생성된_profiles_수
FROM public.profiles;


-- ══════════════════════════════════════════════════════════════════════
-- STEP D5. 구형 역할명 → 신형 역할명 변환 (안전 — UPDATE만 사용)
-- general → member, gfc → partner, ceo/staff → consultant
-- ══════════════════════════════════════════════════════════════════════

-- 변환 전 현황 확인
SELECT role, COUNT(*) AS 인원 FROM public.profiles GROUP BY role;

-- 실제 변환 (기존 CHECK 제약 없으면 오류 없이 실행됨)
UPDATE public.profiles SET role = 'member'     WHERE role = 'general';
UPDATE public.profiles SET role = 'partner'    WHERE role = 'gfc';
UPDATE public.profiles SET role = 'consultant' WHERE role IN ('ceo', 'staff');

-- 변환 후 현황 확인
SELECT role, COUNT(*) AS 인원 FROM public.profiles GROUP BY role;

-- CHECK 제약이 없으면 추가 (이미 있으면 무시)
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('member', 'consultant', 'partner', 'admin'));


-- ══════════════════════════════════════════════════════════════════════
-- STEP D6. 최종 검증 — O&M에서 보여야 할 데이터
-- ══════════════════════════════════════════════════════════════════════

SELECT
  u.email,
  p.role,
  p.name,
  p.agreed_at IS NOT NULL AS 동의완료,
  u.last_sign_in_at       AS 마지막로그인,
  CASE WHEN p.id IS NULL THEN '❌ profiles 없음' ELSE '✅ OK' END AS 상태
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
ORDER BY
  CASE WHEN p.role = 'admin' THEN 0
       WHEN p.role = 'partner' THEN 1
       WHEN p.role = 'consultant' THEN 2
       ELSE 3
  END,
  u.created_at;
