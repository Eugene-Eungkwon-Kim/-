-- UP
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin'));

-- DOWN
ALTER TABLE users DROP COLUMN role;
