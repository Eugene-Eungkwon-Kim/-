-- UP
CREATE TABLE backup_history (
  id TEXT PRIMARY KEY,
  backup_type TEXT NOT NULL CHECK (backup_type IN ('full')),
  backup_path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed')),
  verified INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_backup_history_created_at ON backup_history(created_at);

-- DOWN
DROP INDEX IF EXISTS idx_backup_history_created_at;
DROP TABLE IF EXISTS backup_history;
