import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  InvalidEncryptionKeyError,
  MissingEncryptionKeyError,
  MissingJwtSecretError,
  resolveServerEnv
} from '@/server/env';

const VALID_KEY = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';

describe('resolveServerEnv (Day 9 - Task 1: JWT_SECRET 필수화, δ=1270)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('production + 시크릿/키 있음: 그대로 반환한다', () => {
    const result = resolveServerEnv({
      JWT_SECRET: 'real-secret',
      ENCRYPTION_KEY: VALID_KEY,
      NODE_ENV: 'production'
    });
    expect(result).toEqual({ jwtSecret: 'real-secret', encryptionKey: VALID_KEY, nodeEnv: 'production' });
  });

  it('production + JWT 시크릿 없음: MissingJwtSecretError를 던진다 (fail-fast)', () => {
    expect(() => resolveServerEnv({ ENCRYPTION_KEY: VALID_KEY, NODE_ENV: 'production' })).toThrow(
      MissingJwtSecretError
    );
  });

  it('development + 시크릿 없음: 폴백 시크릿을 반환하고 경고를 남긴다', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const result = resolveServerEnv({ ENCRYPTION_KEY: VALID_KEY, NODE_ENV: 'development' });
    expect(result.jwtSecret).toBe('dev-secret-change-in-production');
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('NODE_ENV 미설정 시 development로 기본 처리된다', () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const result = resolveServerEnv({});
    expect(result.nodeEnv).toBe('development');
  });
});

describe('resolveServerEnv — ENCRYPTION_KEY 검증 (디버깅 세션)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('production + 키 없음: MissingEncryptionKeyError를 던진다 (fail-fast)', () => {
    expect(() => resolveServerEnv({ JWT_SECRET: 's', NODE_ENV: 'production' })).toThrow(
      MissingEncryptionKeyError
    );
  });

  it('development + 키 없음: 결정적 폴백 키를 반환하고 경고를 남긴다', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const first = resolveServerEnv({ JWT_SECRET: 's', NODE_ENV: 'development' });
    const second = resolveServerEnv({ JWT_SECRET: 's', NODE_ENV: 'development' });
    // 재시작 간에도 같은 키여야 이전에 암호화된 개발 데이터를 읽을 수 있다
    expect(first.encryptionKey).toBe(second.encryptionKey);
    expect(first.encryptionKey).toMatch(/^[0-9a-f]{64}$/i);
    expect(warnSpy).toHaveBeenCalled();
  });

  it('형식이 잘못된 키는 환경을 불문하고 InvalidEncryptionKeyError를 던진다', () => {
    // 잘못된 키로 조용히 폴백하면 기존 암호문을 영영 못 읽게 되므로 dev에서도 실패해야 한다
    expect(() =>
      resolveServerEnv({ JWT_SECRET: 's', ENCRYPTION_KEY: 'too-short', NODE_ENV: 'development' })
    ).toThrow(InvalidEncryptionKeyError);
    expect(() =>
      resolveServerEnv({ JWT_SECRET: 's', ENCRYPTION_KEY: 'g'.repeat(64), NODE_ENV: 'production' })
    ).toThrow(InvalidEncryptionKeyError);
  });

  it('유효한 키는 development에서도 그대로 반환한다', () => {
    const result = resolveServerEnv({ JWT_SECRET: 's', ENCRYPTION_KEY: VALID_KEY, NODE_ENV: 'development' });
    expect(result.encryptionKey).toBe(VALID_KEY);
  });
});
