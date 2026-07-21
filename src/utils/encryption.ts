/**
 * Day 13 - Task F (δ=650): 데이터 암호화 (AES-256-GCM)
 *
 * PII(개인식별정보) 데이터를 AES-256-GCM으로 암호화하여 저장한다.
 * 암호화 키는 환경변수(ENCRYPTION_KEY)에서 로드되며, 데이터베이스에
 * 저장될 때 자동으로 암호화되고 로드될 때 자동으로 복호화된다.
 */

import { randomBytes, createCipheriv, createDecipheriv, createHash } from 'node:crypto';

const ALGORITHM = 'aes-256-gcm';
const KEY_LENGTH = 32; // 256 bits
const IV_LENGTH = 16;  // 128 bits

/**
 * 환경변수에서 암호화 키를 로드한다.
 * 프로덕션 환경에서는 반드시 설정되어야 한다.
 */
export function getEncryptionKey(): Buffer {
  const keyEnv = process.env.ENCRYPTION_KEY;
  if (!keyEnv) {
    throw new Error('ENCRYPTION_KEY environment variable is not set');
  }

  // hex 형식의 키를 Buffer로 변환
  if (!/^[0-9a-f]{64}$/i.test(keyEnv)) {
    throw new Error('ENCRYPTION_KEY must be a 64-character hex string (256 bits)');
  }

  return Buffer.from(keyEnv, 'hex');
}

/**
 * 평문을 AES-256-GCM으로 암호화한다.
 * 반환 형식: 'iv:ciphertext:authTag' (모두 base64)
 */
export function encrypt(plaintext: string): string {
  if (!plaintext) return plaintext;

  const key = getEncryptionKey();
  const iv = randomBytes(IV_LENGTH);

  const cipher = createCipheriv(ALGORITHM, key, iv);
  let ciphertext = cipher.update(plaintext, 'utf-8', 'hex');
  ciphertext += cipher.final('hex');
  const authTag = cipher.getAuthTag();

  // iv:ciphertext:authTag를 base64로 인코딩
  const encoded = `${iv.toString('hex')}:${ciphertext}:${authTag.toString('hex')}`;
  return Buffer.from(encoded).toString('base64');
}

/**
 * 암호화된 데이터를 복호화한다.
 * 입력 형식: base64로 인코딩된 'iv:ciphertext:authTag'
 */
export function decrypt(encrypted: string): string {
  if (!encrypted) return encrypted;

  try {
    const key = getEncryptionKey();
    const decoded = Buffer.from(encrypted, 'base64').toString('utf-8');
    const [ivHex, ciphertextHex, authTagHex] = decoded.split(':');

    if (!ivHex || !ciphertextHex || !authTagHex) {
      throw new Error('Invalid encrypted data format');
    }

    const iv = Buffer.from(ivHex, 'hex');
    const ciphertext = Buffer.from(ciphertextHex, 'hex');
    const authTag = Buffer.from(authTagHex, 'hex');

    const decipher = createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    return Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf-8');
  } catch (error) {
    throw new Error(`Decryption failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * 암호화 키를 생성한다 (개발/테스트용).
 * 프로덕션 환경에서는 안전한 키 관리 시스템을 사용해야 한다.
 */
export function generateEncryptionKey(): string {
  return randomBytes(KEY_LENGTH).toString('hex');
}

/**
 * 데이터의 SHA256 해시를 생성한다 (무결성 검증용).
 */
export function hashData(data: string): string {
  return createHash('sha256').update(data).digest('hex');
}

/**
 * 현재 ENCRYPTION_KEY가 DB에 이미 저장된 암호문과 일치하는지 부팅 시점에 검증한다.
 *
 * 키가 교체된 채 기동되면 서버는 정상으로 보이지만 암호화 컬럼을 읽는 모든
 * 요청(로그인, 프로필 조회)이 사용자별로 산발적인 500을 낸다 — 원인 추적이
 * 어려운 장애라 부팅 단계에서 명확한 메시지로 즉시 실패시키는 편이 낫다.
 *
 * @returns 'ok' 검증 통과 | 'no-data' 검증할 암호문 없음 (신규 DB)
 * @throws 저장된 암호문을 현재 키로 복호화할 수 없을 때
 */
export async function verifyEncryptionKeyAgainstDb(pool: {
  query: (text: string, values?: any[]) => Promise<{ rows: any[] }>;
}): Promise<'ok' | 'no-data'> {
  const result = await pool.query(
    'SELECT encrypted_email FROM users WHERE encrypted_email IS NOT NULL LIMIT 1'
  );

  if (!result.rows.length) return 'no-data';

  const row = result.rows[0] as { encrypted_email: string };

  try {
    decrypt(row.encrypted_email);
    return 'ok';
  } catch {
    throw new Error(
      'ENCRYPTION_KEY does not match existing encrypted data in the database. ' +
        'The key may have been rotated or mistyped — refusing to start with undecryptable data.'
    );
  }
}
