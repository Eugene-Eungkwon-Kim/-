-- UP
CREATE TABLE data_integrity_log (
  id TEXT PRIMARY KEY,
  check_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok', 'violation', 'repaired')),
  findings TEXT NOT NULL,
  checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_data_integrity_log_check_type ON data_integrity_log(check_type, checked_at);

-- DOWN
DROP INDEX IF EXISTS idx_data_integrity_log_check_type;
DROP TABLE IF EXISTS data_integrity_log;
