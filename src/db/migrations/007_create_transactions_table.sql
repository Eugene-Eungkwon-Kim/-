-- UP
CREATE TABLE transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal', 'loan_payment', 'fee', 'adjustment')),
  amount INTEGER NOT NULL CHECK (amount > 0),
  description TEXT,
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'flagged', 'reversed')),
  occurred_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_transactions_user_time ON transactions(user_id, occurred_at);
CREATE INDEX idx_transactions_status ON transactions(status);

-- DOWN
DROP INDEX IF EXISTS idx_transactions_status;
DROP INDEX IF EXISTS idx_transactions_user_time;
DROP TABLE IF EXISTS transactions;
