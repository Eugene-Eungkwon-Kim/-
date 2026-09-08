-- UP
CREATE TABLE audit_log (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  actor_id TEXT,
  changes TEXT NOT NULL,
  occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id, occurred_at);

-- DOWN
DROP INDEX IF EXISTS idx_audit_log_entity;
DROP TABLE IF EXISTS audit_log;
