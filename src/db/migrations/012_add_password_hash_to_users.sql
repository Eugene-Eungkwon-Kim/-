-- UP
ALTER TABLE users ADD COLUMN password_hash TEXT;

-- DOWN
ALTER TABLE users DROP COLUMN password_hash;
