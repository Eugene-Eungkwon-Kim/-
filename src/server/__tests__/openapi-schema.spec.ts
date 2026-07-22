import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { buildServer } from '@/server/app';
import type { FastifyInstance } from 'fastify';

/**
 * Day 14 - Task H (δ=400): OpenAPI 스키마 검증 테스트
 *
 * API 문서 생성 및 스키마 유효성을 검증한다.
 */
describe('OpenAPI Schema (Day 14 - Task H)', () => {
  let pool: Pool;
  let app: FastifyInstance;
  let backupDir: string;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-openapi-'));
    app = await buildServer(pool, { jwtSecret: 'test-secret', backupDir });
  });

  afterEach(async () => {
    fs.rmSync(backupDir, { recursive: true, force: true });
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  it('OpenAPI 스키마가 유효한 3.0 형식이다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    expect(res.statusCode).toBe(200);
    const schema = JSON.parse(res.payload);
    expect(schema.openapi).toBe('3.0.0');
    expect(schema.info.title).toBe('MAARS 금융 플랫폼 API');
    expect(schema.info.version).toBe('1.0.0');
  });

  it('API 스키마에 components 정의가 포함되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.components).toBeDefined();
    expect(schema.components.schemas).toBeDefined();
    expect(schema.components.securitySchemes).toBeDefined();
  });

  it('필수 도메인 모델이 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    const requiredSchemas = ['User', 'Loan', 'Transaction', 'AuditLog', 'CreditProfile'];
    for (const schemaName of requiredSchemas) {
      expect(schema.components.schemas[schemaName], `${schemaName} 스키마가 정의되어야 함`).toBeDefined();
    }
  });

  it('JWT Bearer 인증 스키마가 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.components.securitySchemes.Bearer).toBeDefined();
    expect(schema.components.securitySchemes.Bearer.type).toBe('http');
    expect(schema.components.securitySchemes.Bearer.scheme).toBe('bearer');
  });

  it('에러 응답 타입이 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    const errorTypes = ['ValidationError', 'NotFound', 'Unauthorized', 'Forbidden', 'DuplicateEmail'];
    for (const errorType of errorTypes) {
      expect(schema.components.schemas[errorType], `${errorType}가 정의되어야 함`).toBeDefined();
    }
  });

  it('태그가 7개 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.tags).toBeDefined();
    expect(schema.tags.length).toBeGreaterThanOrEqual(7);
    const tagNames = schema.tags.map((t: any) => t.name);
    expect(tagNames).toContain('Authentication');
    expect(tagNames).toContain('Users');
    expect(tagNames).toContain('Loans');
    expect(tagNames).toContain('Transactions');
    expect(tagNames).toContain('Analytics');
    expect(tagNames).toContain('Admin');
    expect(tagNames).toContain('Audit');
  });

  it('최소 20개 이상의 엔드포인트가 문서화되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    let endpointCount = 0;
    for (const path of Object.values(schema.paths)) {
      const pathObj = path as Record<string, any>;
      for (const method of ['get', 'post', 'patch', 'put', 'delete']) {
        if (pathObj[method]) {
          endpointCount++;
        }
      }
    }
    expect(endpointCount).toBeGreaterThanOrEqual(20);
  });

  it('주요 POST 엔드포인트가 requestBody를 정의한다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    const documented = ['/api/users', '/api/auth/login'];
    for (const path of documented) {
      const spec = schema.paths[path]?.post;
      expect(spec, `POST ${path} 스펙이 존재해야 함`).toBeDefined();
      expect(spec.requestBody, `POST ${path}는 requestBody를 정의해야 함`).toBeDefined();
    }
  });

  it('모든 엔드포인트가 응답 스키마를 정의한다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    for (const [path, pathItem] of Object.entries(schema.paths)) {
      const pathObj = pathItem as Record<string, any>;
      for (const method of ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']) {
        if (pathObj[method] && method !== 'parameters') {
          const spec = pathObj[method];
          expect(spec.responses, `${method.toUpperCase()} ${path}는 responses를 정의해야 함`).toBeDefined();
          expect(Object.keys(spec.responses).length).toBeGreaterThan(0);
        }
      }
    }
  });

  it('/api/users POST 엔드포인트가 스키마를 포함한다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    const usersPost = schema.paths['/api/users'].post;
    expect(usersPost).toBeDefined();
    expect(usersPost.description).toBeDefined();
    expect(usersPost.tags).toContain('Authentication');
    expect(usersPost.requestBody).toBeDefined();
    expect(usersPost.responses['200']).toBeDefined();
  });

  it('서버 URL이 정의되어 있다', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/docs/json' });
    const schema = JSON.parse(res.payload);
    expect(schema.servers).toBeDefined();
    expect(schema.servers.length).toBeGreaterThan(0);
    expect(schema.servers.map((s: any) => s.url)).toContain('http://localhost:3001');
  });
});
