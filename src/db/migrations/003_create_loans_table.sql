-- UP
CREATE TABLE loans (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  product_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed', 'delinquent', 'defaulted')),

  original_amount INTEGER NOT NULL CHECK (original_amount > 0),
  current_balance INTEGER NOT NULL CHECK (current_balance >= 0),
  interest_rate REAL NOT NULL CHECK (interest_rate > 0),
  term_months INTEGER NOT NULL CHECK (term_months > 0),
  start_date TEXT NOT NULL,
  maturity_date TEXT NOT NULL,

  monthly_payment INTEGER NOT NULL CHECK (monthly_payment > 0),
  next_payment_date TEXT,
  total_paid INTEGER NOT NULL DEFAULT 0 CHECK (total_paid >= 0),
  total_interest_paid INTEGER NOT NULL DEFAULT 0 CHECK (total_interest_paid >= 0),

  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  closed_at TEXT,

  CHECK (current_balance <= original_amount),
  CHECK (maturity_date >= start_date)
);

CREATE INDEX idx_loans_user_status ON loans(user_id, status);
CREATE INDEX idx_loans_maturity ON loans(maturity_date);

-- DOWN
DROP INDEX IF EXISTS idx_loans_maturity;
DROP INDEX IF EXISTS idx_loans_user_status;
DROP TABLE IF EXISTS loans;
