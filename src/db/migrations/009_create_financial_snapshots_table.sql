-- UP
CREATE TABLE financial_snapshots (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  snapshot_date TEXT NOT NULL,

  credit_score INTEGER NOT NULL CHECK (credit_score >= 0 AND credit_score <= 999),
  financial_health_score INTEGER NOT NULL CHECK (financial_health_score >= 0 AND financial_health_score <= 100),
  health_grade TEXT NOT NULL,
  debt_to_income_ratio REAL NOT NULL CHECK (debt_to_income_ratio >= 0),
  asset_to_debt_ratio REAL NOT NULL CHECK (asset_to_debt_ratio >= 0),
  monthly_surplus INTEGER NOT NULL,
  risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
  risk_level TEXT NOT NULL,
  probability_of_default REAL NOT NULL CHECK (probability_of_default >= 0 AND probability_of_default <= 100),

  created_at TEXT NOT NULL DEFAULT (datetime('now')),

  UNIQUE (user_id, snapshot_date)
);

CREATE INDEX idx_financial_snapshots_user_date ON financial_snapshots(user_id, snapshot_date);

-- DOWN
DROP INDEX IF EXISTS idx_financial_snapshots_user_date;
DROP TABLE IF EXISTS financial_snapshots;
