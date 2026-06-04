-- ═══════════════════════════════════════════════════════════════════
-- Phase 3 Fix 2: instance_id 보정
-- GoTrue는 instance_id가 없는 auth.users 행을 무시함
-- 기존 정상 사용자의 instance_id를 dev 사용자에게 복사
-- ═══════════════════════════════════════════════════════════════════

-- 1. 현재 instance_id 확인 (기존 정상 사용자 기준)
SELECT '=== 기존 사용자 instance_id ===' AS section;
SELECT id, email, instance_id
FROM auth.users
WHERE instance_id IS NOT NULL
LIMIT 3;

-- 2. dev 사용자에 instance_id 복사 적용
UPDATE auth.users
SET instance_id = (
  SELECT instance_id FROM auth.users
  WHERE instance_id IS NOT NULL
  LIMIT 1
)
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
AND instance_id IS NULL;

-- 3. 결과 확인
SELECT '=== dev 사용자 instance_id 적용 결과 ===' AS section;
SELECT id, email, instance_id
FROM auth.users
WHERE id IN (
  'd0000001-0000-4000-8000-000000000000'::uuid,
  'd0000002-0000-4000-8000-000000000000'::uuid,
  'd0000003-0000-4000-8000-000000000000'::uuid,
  'd0000004-0000-4000-8000-000000000000'::uuid
)
ORDER BY email;
