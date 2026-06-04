-- ═══════════════════════════════════════════════════════════════════
-- Phase 3 Fix: auth.identities 누락 보정
-- auth.users만 INSERT하면 이메일/비밀번호 로그인 불가 — identities 필요
-- 멱등성: ON CONFLICT DO NOTHING
-- ═══════════════════════════════════════════════════════════════════

-- (1) 일반회원 테스터
INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'test@worksfree.co.kr',
  'd0000001-0000-4000-8000-000000000000'::uuid,
  jsonb_build_object(
    'sub',            'd0000001-0000-4000-8000-000000000000',
    'email',          'test@worksfree.co.kr',
    'email_verified', true,
    'phone_verified', false
  ),
  'email',
  now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

-- (2) 컨설턴트 테스터
INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'consultant@worksfree.co.kr',
  'd0000002-0000-4000-8000-000000000000'::uuid,
  jsonb_build_object(
    'sub',            'd0000002-0000-4000-8000-000000000000',
    'email',          'consultant@worksfree.co.kr',
    'email_verified', true,
    'phone_verified', false
  ),
  'email',
  now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

-- (3) 파트너(GFC) 테스터
INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'gfc@worksfree.co.kr',
  'd0000003-0000-4000-8000-000000000000'::uuid,
  jsonb_build_object(
    'sub',            'd0000003-0000-4000-8000-000000000000',
    'email',          'gfc@worksfree.co.kr',
    'email_verified', true,
    'phone_verified', false
  ),
  'email',
  now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;

-- (4) 관리자 테스터
INSERT INTO auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
VALUES (
  'admin@worksfree.co.kr',
  'd0000004-0000-4000-8000-000000000000'::uuid,
  jsonb_build_object(
    'sub',            'd0000004-0000-4000-8000-000000000000',
    'email',          'admin@worksfree.co.kr',
    'email_verified', true,
    'phone_verified', false
  ),
  'email',
  now(), now(), now()
) ON CONFLICT (provider_id, provider) DO NOTHING;


-- ── 검증 ────────────────────────────────────────────────────────
SELECT u.email, i.provider, i.provider_id, i.created_at
FROM auth.identities i
JOIN auth.users u ON u.id = i.user_id
WHERE u.email LIKE '%worksfree.co.kr'
ORDER BY u.email;
