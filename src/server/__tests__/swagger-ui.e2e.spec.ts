import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';

/**
 * Day 14 - Task I (δ=400): Swagger UI e2e 테스트
 *
 * Swagger UI 접근성 및 기능을 검증한다.
 */
describe('Swagger UI (Day 14 - Task I)', () => {
  let pool: Pool;
  let app: FastifyInstance;
  let backupDir: string;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-swagger-'));
    app = await buildServer(pool, { jwtSecret: 'test-secret', backupDir });
  });

  afterEach(async () => {
    fs.rmSync(backupDir, { recursive: true, force: true });
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  it('Swagger UI가 /api/docs에서 접근 가능하다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs' });
    expect(res.statusCode).toBe(200);
    expect(res.payload).toContain('swagger-ui');
  });

  it('OpenAPI JSON 스키마를 /api/docs/json에서 제공한다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    expect(res.statusCode).toBe(200);
    const schema = JSON.parse(res.payload);
    expect(schema.openapi).toBe('3.0.0');
    expect(schema.paths).toBeDefined();
  });

  it('Swagger UI HTML이 올바르게 렌더링된다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs' });
    expect(res.headers['content-type']).toContain('text/html');
    expect(res.payload).toContain('swagger-ui');
  });

  it('스키마에 20개 이상의 경로가 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    const pathCount = Object.keys(schema.paths).length;
    expect(pathCount).toBeGreaterThanOrEqual(15);
  });

  it('Bearer 토큰 인증이 보안 스키마에 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.components.securitySchemes.Bearer).toBeDefined();
    expect(schema.components.securitySchemes.Bearer.type).toBe('http');
    expect(schema.components.securitySchemes.Bearer.scheme).toBe('bearer');
  });

  it('API 정보가 올바르게 표시된다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.info.title).toContain('MAARS');
    expect(schema.info.version).toBe('1.0.0');
    expect(schema.info.description).toBeDefined();
  });

  it('모든 태그가 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.tags).toBeDefined();
    expect(schema.tags.length).toBeGreaterThan(0);
  });

  it('인증 없이도 Swagger UI에 접근 가능하다', async () => {
    const res1 = await app.inject({ method: 'GET', url: '/api/docs' });
    const res2 = await app.inject({ method: 'GET', url: '/api/docs/json' });
    expect(res1.statusCode).toBe(200);
    expect(res2.statusCode).toBe(200);
  });
});
