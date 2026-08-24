-- UP
CREATE TABLE users_audit (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE')),
  changed_fields TEXT NOT NULL,
  changed_by TEXT NOT NULL DEFAULT 'system',
  changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_users_audit_user_id ON users_audit(user_id, changed_at);

-- DOWN
DROP INDEX IF EXISTS idx_users_audit_user_id;
DROP TABLE IF EXISTS users_audit;
