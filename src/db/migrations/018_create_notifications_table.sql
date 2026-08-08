-- UP
-- Phase 15 - Section 2 (B-1): 임계값 알림 영속화.
--
-- dedupe_key = '{userId}:{metric}:{severity}:{snapshotDate}'
-- UNIQUE 제약이 다중 인스턴스의 동시 평가 경합을 DB 층에서 차단한다 —
-- 애플리케이션 락이 필요 없다. 부작용으로 같은 날 warning → ok → warning 왕복 시
-- 두 번째 warning은 삽입되지 않는데, 이는 경계값 근처 플래핑을 흡수하는 의도된 동작이다.
--
-- 방언 주의: migrationRunner의 translateSqliteToPostgres()는 datetime('now')와
-- REAL 두 가지만 치환한다. 나머지는 SQLite/PostgreSQL 양쪽에서 그대로 유효해야 한다.
CREATE TABLE notifications (
  id            TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL REFERENCES users(id),
  metric        TEXT NOT NULL,
  severity      TEXT NOT NULL CHECK (severity IN ('warning', 'critical', 'resolved')),
  value         REAL NOT NULL,
  threshold     REAL NOT NULL,
  snapshot_date TEXT NOT NULL,
  dedupe_key    TEXT NOT NULL UNIQUE,
  read_at       TEXT,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at);
CREATE INDEX idx_notifications_user_metric ON notifications(user_id, metric, created_at);
CREATE INDEX idx_notifications_unread ON notifications(user_id, read_at);

-- DOWN
DROP INDEX IF EXISTS idx_notifications_unread;
DROP INDEX IF EXISTS idx_notifications_user_metric;
DROP INDEX IF EXISTS idx_notifications_user_created;
DROP TABLE IF EXISTS notifications;
