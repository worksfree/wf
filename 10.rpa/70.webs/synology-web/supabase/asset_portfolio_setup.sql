-- ══════════════════════════════════════════════════════════════
-- portfolios 테이블 — 자산 통합 관리 (consulting/asset)
-- Supabase → SQL Editor에서 1회 실행
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS portfolios (
  user_id     uuid        REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  holdings    jsonb       NOT NULL DEFAULT '[]',
  nw_assets   jsonb       NOT NULL DEFAULT '[]',
  nw_liabs    jsonb       NOT NULL DEFAULT '[]',
  instruments jsonb       NOT NULL DEFAULT '{}',
  updated_at  timestamptz DEFAULT now()
);

-- RLS: 본인 데이터만 접근 가능
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own portfolio only"
  ON portfolios FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- updated_at 자동 갱신 트리거 (선택사항)
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

CREATE TRIGGER portfolios_updated_at
  BEFORE UPDATE ON portfolios
  FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
