-- MAARS PostgreSQL 통합 스키마
-- SQLite 마이그레이션에서 자동 생성됨 — 직접 수정하지 말 것
-- 원본 마이그레이션: 17개 (001 ~ 017)


-- ===== 001_create_users_table.sql =====
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  date_of_birth TEXT,
  employment_status TEXT CHECK (employment_status IS NULL OR employment_status IN ('employed', 'self-employed', 'unemployed')),
  employment_industry TEXT,
  employment_tenure INTEGER CHECK (employment_tenure IS NULL OR employment_tenure >= 0),
  employment_company TEXT,
  phone TEXT,
  address_street TEXT,
  address_city TEXT,
  address_zipcode TEXT,
  address_country TEXT,
  credit_score INTEGER CHECK (credit_score IS NULL OR (credit_score >= 0 AND credit_score <= 999)),
  credit_grade TEXT CHECK (credit_grade IS NULL OR credit_grade IN ('A', 'B', 'C', 'D', 'F')),
  credit_inquiries INTEGER NOT NULL DEFAULT 0 CHECK (credit_inquiries >= 0),
  credit_delinquency INTEGER NOT NULL DEFAULT 0 CHECK (credit_delinquency >= 0),
  income INTEGER CHECK (income IS NULL OR income >= 0),
  expenses INTEGER CHECK (expenses IS NULL OR expenses >= 0),
  assets INTEGER CHECK (assets IS NULL OR assets >= 0),
  debt INTEGER CHECK (debt IS NULL OR debt >= 0),
  savings_rate DOUBLE PRECISION CHECK (savings_rate IS NULL OR (savings_rate >= 0 AND savings_rate <= 100)),
  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')),
  updated_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')),
  last_login_at TEXT
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_credit_score ON users(credit_score);
CREATE INDEX idx_users_status ON users(status);

-- ===== 002_create_users_audit_table.sql =====
CREATE TABLE users_audit (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE')),
  changed_fields TEXT NOT NULL,
  changed_by TEXT NOT NULL DEFAULT 'system',
  changed_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_users_audit_user_id ON users_audit(user_id, changed_at);

-- ===== 003_create_loans_table.sql =====
CREATE TABLE loans (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  product_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed', 'delinquent', 'defaulted')),

  original_amount INTEGER NOT NULL CHECK (original_amount > 0),
  current_balance INTEGER NOT NULL CHECK (current_balance >= 0),
  interest_rate DOUBLE PRECISION NOT NULL CHECK (interest_rate > 0),
  term_months INTEGER NOT NULL CHECK (term_months > 0),
  start_date TEXT NOT NULL,
  maturity_date TEXT NOT NULL,

  monthly_payment INTEGER NOT NULL CHECK (monthly_payment > 0),
  next_payment_date TEXT,
  total_paid INTEGER NOT NULL DEFAULT 0 CHECK (total_paid >= 0),
  total_interest_paid INTEGER NOT NULL DEFAULT 0 CHECK (total_interest_paid >= 0),

  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')),
  updated_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')),
  closed_at TEXT,

  CHECK (current_balance <= original_amount),
  CHECK (maturity_date >= start_date)
);

CREATE INDEX idx_loans_user_status ON loans(user_id, status);
CREATE INDEX idx_loans_maturity ON loans(maturity_date);

-- ===== 004_create_loan_payments_table.sql =====
CREATE TABLE loan_payments (
  id TEXT PRIMARY KEY,
  loan_id TEXT NOT NULL REFERENCES loans(id),
  payment_date TEXT NOT NULL,
  principal INTEGER NOT NULL CHECK (principal >= 0),
  interest INTEGER NOT NULL CHECK (interest >= 0),
  fees INTEGER NOT NULL DEFAULT 0 CHECK (fees >= 0),
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed', 'pending')),
  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')),

  CHECK (principal + interest + fees > 0)
);

CREATE INDEX idx_loan_payments_loan_date ON loan_payments(loan_id, payment_date);

-- ===== 005_create_loan_history_table.sql =====
CREATE TABLE loan_history (
  id TEXT PRIMARY KEY,
  loan_id TEXT NOT NULL REFERENCES loans(id),
  action TEXT NOT NULL CHECK (action IN ('CREATED', 'PAYMENT', 'STATUS_CHANGE', 'CLOSED')),
  previous_balance INTEGER NOT NULL CHECK (previous_balance >= 0),
  new_balance INTEGER NOT NULL CHECK (new_balance >= 0),
  action_date TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_loan_history_loan_date ON loan_history(loan_id, action_date);

-- ===== 006_create_data_integrity_log_table.sql =====
CREATE TABLE data_integrity_log (
  id TEXT PRIMARY KEY,
  check_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok', 'violation', 'repaired')),
  findings TEXT NOT NULL,
  checked_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_data_integrity_log_check_type ON data_integrity_log(check_type, checked_at);

-- ===== 007_create_transactions_table.sql =====
CREATE TABLE transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal', 'loan_payment', 'fee', 'adjustment')),
  amount INTEGER NOT NULL CHECK (amount > 0),
  description TEXT,
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'flagged', 'reversed')),
  occurred_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_transactions_user_time ON transactions(user_id, occurred_at);
CREATE INDEX idx_transactions_status ON transactions(status);

-- ===== 008_create_audit_log_table.sql =====
CREATE TABLE audit_log (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  actor_id TEXT,
  changes TEXT NOT NULL,
  occurred_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id, occurred_at);

-- ===== 009_create_financial_snapshots_table.sql =====
CREATE TABLE financial_snapshots (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  snapshot_date TEXT NOT NULL,

  credit_score INTEGER NOT NULL CHECK (credit_score >= 0 AND credit_score <= 999),
  financial_health_score INTEGER NOT NULL CHECK (financial_health_score >= 0 AND financial_health_score <= 100),
  health_grade TEXT NOT NULL,
  debt_to_income_ratio DOUBLE PRECISION NOT NULL CHECK (debt_to_income_ratio >= 0),
  asset_to_debt_ratio DOUBLE PRECISION NOT NULL CHECK (asset_to_debt_ratio >= 0),
  monthly_surplus INTEGER NOT NULL,
  risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
  risk_level TEXT NOT NULL,
  probability_of_default DOUBLE PRECISION NOT NULL CHECK (probability_of_default >= 0 AND probability_of_default <= 100),

  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')),

  UNIQUE (user_id, snapshot_date)
);

CREATE INDEX idx_financial_snapshots_user_date ON financial_snapshots(user_id, snapshot_date);

-- ===== 010_add_loans_status_next_payment_index.sql =====
-- detectDelinquentLoans의 "status='active' AND next_payment_date < ?" 조회는
-- 기존 idx_loans_user_status(user_id, status)로는 인덱스를 탈 수 없어
-- (선행 컬럼 user_id가 조건에 없음) 전용 복합 인덱스를 추가한다.
CREATE INDEX idx_loans_status_next_payment ON loans(status, next_payment_date);

-- ===== 011_create_backup_history_table.sql =====
CREATE TABLE backup_history (
  id TEXT PRIMARY KEY,
  backup_type TEXT NOT NULL CHECK (backup_type IN ('full')),
  backup_path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed')),
  verified INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_backup_history_created_at ON backup_history(created_at);

-- ===== 012_add_password_hash_to_users.sql =====
ALTER TABLE users ADD COLUMN password_hash TEXT;

-- ===== 013_create_refresh_tokens_table.sql =====
CREATE TABLE refresh_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);

-- ===== 014_add_role_to_users.sql =====
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin'));

-- ===== 015_add_encrypted_pii_columns.sql =====
ALTER TABLE users ADD COLUMN encrypted_email TEXT;
ALTER TABLE users ADD COLUMN encrypted_phone TEXT;
ALTER TABLE users ADD COLUMN encryption_version INTEGER DEFAULT 1;

-- ===== 016_create_audit_logs_table.sql =====
CREATE TABLE audit_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  changes_before TEXT,
  changes_after TEXT,
  metadata_ip TEXT,
  status TEXT NOT NULL CHECK (status IN ('success', 'failure')),
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- ===== 017_optimize_indexes.sql =====
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



-- ===== schema_migrations (마이그레이션 러너 상태) =====

CREATE TABLE schema_migrations (
  version TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  applied_at TEXT NOT NULL DEFAULT (to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS'))
);

INSERT INTO schema_migrations (version, filename) VALUES ('001', '001_create_users_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('002', '002_create_users_audit_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('003', '003_create_loans_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('004', '004_create_loan_payments_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('005', '005_create_loan_history_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('006', '006_create_data_integrity_log_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('007', '007_create_transactions_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('008', '008_create_audit_log_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('009', '009_create_financial_snapshots_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('010', '010_add_loans_status_next_payment_index.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('011', '011_create_backup_history_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('012', '012_add_password_hash_to_users.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('013', '013_create_refresh_tokens_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('014', '014_add_role_to_users.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('015', '015_add_encrypted_pii_columns.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('016', '016_create_audit_logs_table.sql');
INSERT INTO schema_migrations (version, filename) VALUES ('017', '017_optimize_indexes.sql');

