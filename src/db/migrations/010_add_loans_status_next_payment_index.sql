-- UP
-- detectDelinquentLoans의 "status='active' AND next_payment_date < ?" 조회는
-- 기존 idx_loans_user_status(user_id, status)로는 인덱스를 탈 수 없어
-- (선행 컬럼 user_id가 조건에 없음) 전용 복합 인덱스를 추가한다.
CREATE INDEX idx_loans_status_next_payment ON loans(status, next_payment_date);

-- DOWN
DROP INDEX IF EXISTS idx_loans_status_next_payment;
