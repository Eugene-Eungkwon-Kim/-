-- UP
CREATE TABLE loan_payments (
  id TEXT PRIMARY KEY,
  loan_id TEXT NOT NULL REFERENCES loans(id),
  payment_date TEXT NOT NULL,
  principal INTEGER NOT NULL CHECK (principal >= 0),
  interest INTEGER NOT NULL CHECK (interest >= 0),
  fees INTEGER NOT NULL DEFAULT 0 CHECK (fees >= 0),
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed', 'pending')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),

  CHECK (principal + interest + fees > 0)
);

CREATE INDEX idx_loan_payments_loan_date ON loan_payments(loan_id, payment_date);

-- DOWN
DROP INDEX IF EXISTS idx_loan_payments_loan_date;
DROP TABLE IF EXISTS loan_payments;
