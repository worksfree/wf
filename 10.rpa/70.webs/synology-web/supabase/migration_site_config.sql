-- ═══════════════════════════════════════════════════════════════════
-- migration_site_config.sql
-- WorksFree Hub — 사이트 설정 테이블 (페이지 권한 관리 등)
--
-- 실행: Supabase 대시보드 → SQL Editor → 전체 붙여넣기 → Run
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS site_config (
  key        TEXT        PRIMARY KEY,
  value      JSONB       NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 기본 페이지 권한 규칙 삽입 (관리자 페이지에서 변경 가능)
INSERT INTO site_config (key, value) VALUES (
  'page_access_rules',
  '{
    "consulting/gfc/index.html": {
      "general":    "hidden",
      "member":     "hidden",
      "consultant": "blur",
      "gfc":        "full",
      "admin":      "full"
    }
  }'::jsonb
) ON CONFLICT (key) DO NOTHING;

-- Worker service_role 키로 RLS 우회
ALTER TABLE site_config ENABLE ROW LEVEL SECURITY;

-- 읽기: 모든 로그인 사용자 (anon 포함 — Hub가 읽어야 함)
CREATE POLICY "site_config_read_all"
  ON site_config FOR SELECT
  USING (true);

-- 쓰기: 관리자만 (service_role via RLS 우회 or admin 프로파일)
-- Hub admin 페이지는 anon key로 접근하므로 profiles 확인
CREATE POLICY "site_config_write_admin"
  ON site_config FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
        AND profiles.role = 'admin'
    )
  );

-- 검증
SELECT key, jsonb_pretty(value) FROM site_config;
