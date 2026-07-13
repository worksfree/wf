-- ================================================================
-- 01_fix_role_default.sql — 신규 가입 500 에러 수정 (최우선, 독립 실행 가능)
--
-- 원인: profiles.role 라이브 DEFAULT가 'general'인데 체크 제약은
--       ('member','consultant','partner','admin')만 허용 → 모든 신규 가입 실패.
--       complete_db_setup.sql의 ADD COLUMN IF NOT EXISTS DEFAULT 'member'는
--       컬럼이 이미 존재해 무시(no-op)됐음. 명시적 ALTER COLUMN이 필요.
-- ================================================================

ALTER TABLE public.profiles ALTER COLUMN role SET DEFAULT 'member';

-- 잔존 구형 role 값 정리 (00 스냅샷 (2)에서 'general' 등이 보였을 때만 의미 있음, 없어도 무해)
UPDATE public.profiles SET role = 'member'     WHERE role = 'general';
UPDATE public.profiles SET role = 'partner'    WHERE role = 'gfc';
UPDATE public.profiles SET role = 'consultant' WHERE role IN ('ceo','staff');

-- ── 검증 ──
-- (a) 'member'::text 가 나와야 함
SELECT column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='profiles' AND column_name='role';

-- (b) 허용 외 role 0건이어야 함
SELECT COUNT(*) AS invalid_roles
FROM public.profiles
WHERE role NOT IN ('member','consultant','partner','admin');

-- (c) 실행 후 저에게 알려주시면 REST 가입 테스트로 500 해소를 확인하겠습니다.
