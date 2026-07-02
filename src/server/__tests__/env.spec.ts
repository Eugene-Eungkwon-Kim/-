import { describe, it, expect, vi, afterEach } from 'vitest';
import { MissingJwtSecretError, resolveServerEnv } from '@/server/env';

describe('resolveServerEnv (Day 9 - Task 1: JWT_SECRET 필수화, δ=1270)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('production + 시크릿 있음: 그대로 반환한다', () => {
    const result = resolveServerEnv({ JWT_SECRET: 'real-secret', NODE_ENV: 'production' });
    expect(result).toEqual({ jwtSecret: 'real-secret', nodeEnv: 'production' });
  });

  it('production + 시크릿 없음: MissingJwtSecretError를 던진다 (fail-fast)', () => {
    expect(() => resolveServerEnv({ NODE_ENV: 'production' })).toThrow(MissingJwtSecretError);
  });

  it('development + 시크릿 없음: 폴백 시크릿을 반환하고 경고를 남긴다', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const result = resolveServerEnv({ NODE_ENV: 'development' });
    expect(result.jwtSecret).toBe('dev-secret-change-in-production');
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('NODE_ENV 미설정 시 development로 기본 처리된다', () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const result = resolveServerEnv({});
    expect(result.nodeEnv).toBe('development');
  });
});
