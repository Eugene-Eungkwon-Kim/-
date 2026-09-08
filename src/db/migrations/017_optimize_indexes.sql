-- UP
-- Day 15 - Task J: 실제 쿼리 패턴 기반 인덱스 최적화
--
-- audit_logs: AuditLogger.query()는 항상 ORDER BY created_at DESC를 동반하므로
-- 단일 컬럼 인덱스(user_id / resource_id)로는 필터 후 별도 정렬이 필요하다.
-- (필터 컬럼, created_at) 복합 인덱스로 교체해 필터+정렬을 한 번에 처리한다.
-- 복합 인덱스가 선행 컬럼 단독 조회도 커버하므로 기존 단일 인덱스는 제거해
-- 쓰기 오버헤드를 줄인다.
DROP INDEX IF EXISTS idx_audit_logs_user_id;
DROP INDEX IF EXISTS idx_audit_logs_resource_id;
CREATE INDEX idx_audit_logs_user_created ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_logs_resource_created ON audit_logs(resource_id, created_at);

-- transactions: rescanAnomalies의 "user_id = ? AND status = 'completed' AND amount > ?"
-- 조회는 기존 idx_transactions_user_time(user_id, occurred_at)으로는 user_id 프리픽스만
-- 활용 가능하다. 세 조건을 모두 커버하는 전용 복합 인덱스를 추가한다.
CREATE INDEX idx_transactions_user_status_amount ON transactions(user_id, status, amount);

-- DOWN
DROP INDEX IF EXISTS idx_transactions_user_status_amount;
DROP INDEX IF EXISTS idx_audit_logs_resource_created;
DROP INDEX IF EXISTS idx_audit_logs_user_created;
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
