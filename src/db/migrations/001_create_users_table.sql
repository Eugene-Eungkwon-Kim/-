-- UP
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
  savings_rate REAL CHECK (savings_rate IS NULL OR (savings_rate >= 0 AND savings_rate <= 100)),
  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_login_at TEXT
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_credit_score ON users(credit_score);
CREATE INDEX idx_users_status ON users(status);

-- DOWN
DROP INDEX IF EXISTS idx_users_status;
DROP INDEX IF EXISTS idx_users_credit_score;
DROP INDEX IF EXISTS idx_users_email;
DROP TABLE IF EXISTS users;
