-- ================================================================
-- add_sender_user_id.sql
-- email_log 테이블에 발송 회원 ID 컬럼 추가
--
-- 실행: Supabase Dashboard → SQL Editor → 전체 붙여넣기 → Run
-- 멱등성: 여러 번 실행해도 안전
-- ================================================================

ALTER TABLE public.email_log
  ADD COLUMN IF NOT EXISTS sender_user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS email_log_sender_user_idx
  ON public.email_log(sender_user_id);

-- 확인
SELECT column_name, data_type
FROM   information_schema.columns
WHERE  table_schema = 'public'
  AND  table_name   = 'email_log'
ORDER  BY ordinal_position;
