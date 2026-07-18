import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { encrypt, decrypt, generateEncryptionKey, hashData, getEncryptionKey } from '../encryption';

/**
 * Day 13 - Task F (δ=650): 암호화 유틸리티 테스트
 *
 * AES-256-GCM 암호화/복호화 기능과 엣지 케이스를 검증한다.
 */
describe('encryption.ts', () => {
  const testKey = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';

  beforeEach(() => {
    process.env.ENCRYPTION_KEY = testKey;
  });

  afterEach(() => {
    delete process.env.ENCRYPTION_KEY;
  });

  describe('getEncryptionKey', () => {
    it('환경변수에서 암호화 키를 로드한다', () => {
      const key = getEncryptionKey();
      expect(key).toBeInstanceOf(Buffer);
      expect(key.length).toBe(32); // 256 bits
    });

    it('ENCRYPTION_KEY가 없으면 에러를 던진다', () => {
      delete process.env.ENCRYPTION_KEY;
      expect(() => getEncryptionKey()).toThrow('ENCRYPTION_KEY environment variable is not set');
    });

    it('64자가 아닌 hex 문자열이면 에러를 던진다', () => {
      process.env.ENCRYPTION_KEY = '0123456789abcdef'; // 16자만
      expect(() => getEncryptionKey()).toThrow('ENCRYPTION_KEY must be a 64-character hex string');
    });

    it('유효하지 않은 hex 문자열이면 에러를 던진다', () => {
      process.env.ENCRYPTION_KEY = 'g'.repeat(64); // 'g'는 hex가 아님
      expect(() => getEncryptionKey()).toThrow('ENCRYPTION_KEY must be a 64-character hex string');
    });
  });

  describe('encrypt & decrypt', () => {
    it('기본 암호화와 복호화', () => {
      const plaintext = 'hello@example.com';
      const encrypted = encrypt(plaintext);
      const decrypted = decrypt(encrypted);
      expect(decrypted).toBe(plaintext);
    });

    it('빈 문자열은 암호화하지 않는다', () => {
      const empty = '';
      expect(encrypt(empty)).toBe(empty);
      expect(decrypt(empty)).toBe(empty);
    });

    it('특수문자와 이모지를 암호화할 수 있다', () => {
      const plaintext = 'test@example.com 🎉 한글 텍스트 !@#$%^&*()';
      const encrypted = encrypt(plaintext);
      const decrypted = decrypt(encrypted);
      expect(decrypted).toBe(plaintext);
    });

    it('긴 문자열을 암호화할 수 있다', () => {
      const plaintext = 'a'.repeat(1000);
      const encrypted = encrypt(plaintext);
      const decrypted = decrypt(encrypted);
      expect(decrypted).toBe(plaintext);
    });

    it('매번 암호화할 때마다 다른 결과를 생성한다 (IV가 다르기 때문)', () => {
      const plaintext = 'same text';
      const encrypted1 = encrypt(plaintext);
      const encrypted2 = encrypt(plaintext);
      expect(encrypted1).not.toBe(encrypted2);
      expect(decrypt(encrypted1)).toBe(plaintext);
      expect(decrypt(encrypted2)).toBe(plaintext);
    });

    it('암호화된 데이터가 손상되면 복호화 실패', () => {
      const plaintext = 'test';
      const encrypted = encrypt(plaintext);
      const tampered = Buffer.from(encrypted, 'base64');
      tampered[0] ^= 0xff; // 첫 바이트를 변조
      const tamperedEncrypted = tampered.toString('base64');

      expect(() => decrypt(tamperedEncrypted)).toThrow();
    });

    it('잘못된 형식의 암호화 데이터는 복호화 실패', () => {
      expect(() => decrypt('invalid-base64-data')).toThrow();
      expect(() => decrypt('aW52YWxpZA==')).toThrow(); // 올바른 base64이지만 잘못된 포맷
    });

    it('다른 키로 복호화하면 실패한다', () => {
      const plaintext = 'secret';
      const encrypted = encrypt(plaintext);

      const otherKey = '1111111111111111111111111111111111111111111111111111111111111111';
      process.env.ENCRYPTION_KEY = otherKey;

      expect(() => decrypt(encrypted)).toThrow();
    });
  });

  describe('generateEncryptionKey', () => {
    it('32바이트의 랜덤 hex 문자열을 생성한다', () => {
      const key = generateEncryptionKey();
      expect(typeof key).toBe('string');
      expect(key.length).toBe(64); // 32 bytes = 64 hex chars
      expect(/^[0-9a-f]{64}$/.test(key)).toBe(true);
    });

    it('매번 다른 키를 생성한다', () => {
      const key1 = generateEncryptionKey();
      const key2 = generateEncryptionKey();
      expect(key1).not.toBe(key2);
    });
  });

  describe('hashData', () => {
    it('데이터의 SHA256 해시를 생성한다', () => {
      const data = 'test';
      const hash = hashData(data);
      expect(typeof hash).toBe('string');
      expect(hash.length).toBe(64); // SHA256 = 32 bytes = 64 hex chars
      expect(/^[0-9a-f]{64}$/.test(hash)).toBe(true);
    });

    it('같은 데이터는 같은 해시를 생성한다', () => {
      const data = 'same data';
      const hash1 = hashData(data);
      const hash2 = hashData(data);
      expect(hash1).toBe(hash2);
    });

    it('다른 데이터는 다른 해시를 생성한다', () => {
      const hash1 = hashData('data1');
      const hash2 = hashData('data2');
      expect(hash1).not.toBe(hash2);
    });
  });

  describe('성능', () => {
    it('암호화는 10ms 이내에 완료된다', () => {
      const plaintext = 'test@example.com';
      const start = performance.now();
      for (let i = 0; i < 100; i++) {
        encrypt(plaintext);
      }
      const duration = performance.now() - start;
      expect(duration).toBeLessThan(1000); // 100 iterations < 1000ms = 10ms avg
    });

    it('복호화는 10ms 이내에 완료된다', () => {
      const plaintext = 'test@example.com';
      const encrypted = encrypt(plaintext);
      const start = performance.now();
      for (let i = 0; i < 100; i++) {
        decrypt(encrypted);
      }
      const duration = performance.now() - start;
      expect(duration).toBeLessThan(1000); // 100 iterations < 1000ms = 10ms avg
    });
  });
});
