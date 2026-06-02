-- ═══════════════════════════════════════════════════════════════════
-- fix_dev_profiles_roles.sql  (v2 — UPSERT 방식으로 교체)
--
-- 문제: 기존 UPDATE는 profiles 행이 없으면 아무것도 안 함
--       dev 계정 로그인 시 role이 null/general로 반환 → 메뉴 권한 오작동
--
-- 수정: INSERT ... ON CONFLICT DO UPDATE 로 행 없어도 안전하게 설정
-- ═══════════════════════════════════════════════════════════════════

-- 1. 현재 상태 확인 (실행 전)
SELECT '=== 보정 전 dev 사용자 profiles ===' AS section;
SELECT
  u.email,
  p.id,
  p.role,
  p.agreed_at,
  p.name
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE u.id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
ORDER BY u.email;

-- 2. UPSERT — 행이 없어도 INSERT, 있으면 UPDATE
INSERT INTO public.profiles (id, role, agreed_at, marketing_agreed, name, email)
VALUES
  ('d0000001-0000-4000-8000-000000000000'::uuid, 'general',    NOW(), false, '테스트 회원',       'test@worksfree.co.kr'),
  ('d0000002-0000-4000-8000-000000000000'::uuid, 'consultant', NOW(), false, '컨설턴트 테스터',   'consultant@worksfree.co.kr'),
  ('d0000003-0000-4000-8000-000000000000'::uuid, 'gfc',        NOW(), false, '파트너(GFC) 테스터','gfc@worksfree.co.kr'),
  ('d0000004-0000-4000-8000-000000000000'::uuid, 'admin',      NOW(), false, '관리자 테스터',     'admin@worksfree.co.kr')
ON CONFLICT (id) DO UPDATE SET
  role       = EXCLUDED.role,
  agreed_at  = COALESCE(public.profiles.agreed_at, EXCLUDED.agreed_at),
  name       = EXCLUDED.name,
  email      = EXCLUDED.email;

-- 3. 결과 확인
SELECT '=== 보정 후 dev 사용자 profiles ===' AS section;
SELECT
  u.email,
  p.role,
  p.agreed_at IS NOT NULL AS has_agreed,
  p.name
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE u.id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
ORDER BY u.email;
