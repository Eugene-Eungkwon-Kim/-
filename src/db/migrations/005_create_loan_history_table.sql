-- UP
CREATE TABLE loan_history (
  id TEXT PRIMARY KEY,
  loan_id TEXT NOT NULL REFERENCES loans(id),
  action TEXT NOT NULL CHECK (action IN ('CREATED', 'PAYMENT', 'STATUS_CHANGE', 'CLOSED')),
  previous_balance INTEGER NOT NULL CHECK (previous_balance >= 0),
  new_balance INTEGER NOT NULL CHECK (new_balance >= 0),
  action_date TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_loan_history_loan_date ON loan_history(loan_id, action_date);

-- DOWN
DROP INDEX IF EXISTS idx_loan_history_loan_date;
DROP TABLE IF EXISTS loan_history;
