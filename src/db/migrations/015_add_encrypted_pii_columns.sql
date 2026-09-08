-- UP
ALTER TABLE users ADD COLUMN encrypted_email TEXT;
ALTER TABLE users ADD COLUMN encrypted_phone TEXT;
ALTER TABLE users ADD COLUMN encryption_version INTEGER DEFAULT 1;

-- DOWN
ALTER TABLE users DROP COLUMN encryption_version;
ALTER TABLE users DROP COLUMN encrypted_phone;
ALTER TABLE users DROP COLUMN encrypted_email;
