import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createConnection, type Socket } from 'node:net';
import type { Pool } from 'pg';
import type { FastifyInstance } from 'fastify';
import { cleanupTestDatabase, initializeTestDatabase } from '@db/__tests__/testDatabase';
import { buildServer } from '@/server/app';
import { MemoryNotificationHub } from '@/notifications/notificationHub';
import { FinancialSnapshotRepository } from '@repositories/FinancialSnapshotRepository';

/**
 * Phase 15 - Section 2 (B-6, B-7): 알림 조회 · 티켓 인증 · SSE 스트림.
 */
describe('알림 API와 SSE 스트림', () => {
  let pool: Pool;
  let app: FastifyInstance;
  let hub: MemoryNotificationHub;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    hub = new MemoryNotificationHub();
    app = await buildServer(pool, { jwtSecret: 'test-secret', notificationHub: hub });
  });

  afterEach(async () => {
    await app.close();
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  async function registerAndLogin(email: string, creditScore?: number): Promise<{ userId: string; token: string }> {
    const registerRes = await app.inject({
      method: 'POST',
      url: '/api/users',
      payload: {
        email,
        name: 'Alert User',
        password: 'correct-horse',
        ...(creditScore !== undefined ? { creditProfile: { score: creditScore } } : {})
      }
    });
    const userId = registerRes.json().data.id;

    const loginRes = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { email, password: 'correct-horse' } });
    return { userId, token: loginRes.json().data.token };
  }

  function auth(token: string) {
    return { authorization: `Bearer ${token}` };
  }

  /** 신용점수를 지정해 임계값을 위반시키는 스냅샷 */
  async function recordSnapshot(userId: string, creditScore: number, snapshotDate: string): Promise<void> {
    await new FinancialSnapshotRepository(pool).recordSnapshot({
      userId,
      snapshotDate,
      creditScore,
      financialHealthScore: 80,
      healthGrade: 'A',
      debtToIncomeRatio: 0.2,
      assetToDebtRatio: 3,
      monthlySurplus: 1_000_000,
      riskScore: 20,
      riskLevel: 'low',
      probabilityOfDefault: 0.01
    });
  }

  /**
   * inject()는 응답을 완결시켜 끊기지 않는 스트림 검증에 부적합하다. 그렇다고
   * fetch를 쓸 수도 없다 — test/setup.ts가 global.fetch를 목으로 바꾸고 MSW가
   * onUnhandledRequest:'error'로 가로채기 때문이다. raw TCP 소켓으로 직접
   * HTTP를 말하면 가로채기 계층을 전부 우회하면서 SSE 와이어 포맷을 그대로 검증할 수 있다.
   */
  class StreamClient {
    private buffer = '';
    private readonly socket: Socket;

    private constructor(socket: Socket) {
      this.socket = socket;
      socket.setEncoding('utf-8');
      socket.on('data', (chunk: string) => {
        this.buffer += chunk;
      });
    }

    static async connect(port: number, path: string): Promise<StreamClient> {
      const socket = await new Promise<Socket>((resolve, reject) => {
        const s = createConnection({ port, host: '127.0.0.1' }, () => resolve(s));
        s.once('error', reject);
      });

      const client = new StreamClient(socket);
      socket.write(`GET ${path} HTTP/1.1\r\nHost: 127.0.0.1:${port}\r\nAccept: text/event-stream\r\n\r\n`);
      return client;
    }

    /** 주어진 문자열이 나타날 때까지 기다렸다가 그 시점까지의 버퍼를 돌려준다. */
    async waitFor(needle: string, timeoutMs = 5000): Promise<string> {
      const start = Date.now();
      while (!this.buffer.includes(needle)) {
        if (Date.now() - start > timeoutMs) {
          throw new Error(`timed out waiting for "${needle}". buffer so far:\n${this.buffer}`);
        }
        await new Promise((resolve) => setTimeout(resolve, 20));
      }
      return this.buffer;
    }

    close(): void {
      this.socket.destroy();
    }
  }

  async function listen(): Promise<number> {
    await app.listen({ port: 0, host: '127.0.0.1' });
    const address = app.server.address();
    if (!address || typeof address === 'string') throw new Error('server did not bind a TCP port');
    return address.port;
  }

  async function issueTicketFor(token: string): Promise<string> {
    const res = await app.inject({ method: 'POST', url: '/api/notifications/ticket', headers: auth(token) });
    return res.json().data.ticket;
  }

  /** 조건이 참이 될 때까지 기다린다 (소켓 종료가 서버에 반영되는 시차 흡수용). */
  async function waitUntil(predicate: () => boolean, timeoutMs = 3000): Promise<void> {
    const start = Date.now();
    while (!predicate()) {
      if (Date.now() - start > timeoutMs) throw new Error('timed out waiting for condition');
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
  }

  describe('알림 조회', () => {
    it('위험 평가 실행 후 알림이 기록된다', async () => {
      const { userId, token } = await registerAndLogin('n1@example.com');
      await recordSnapshot(userId, 480, '2026-01-01');

      // risk-assessment는 프로필 기반으로 스냅샷을 덮어쓰므로, 알림 판정은
      // financial-analysis 경로로 확인한다 (둘 다 동일한 트리거를 쓴다).
      const res = await app.inject({
        method: 'POST',
        url: '/api/analytics/financial-analysis',
        headers: auth(token),
        payload: { userId, snapshotDate: '2026-01-02' }
      });
      expect(res.statusCode).toBe(200);

      const listRes = await app.inject({ method: 'GET', url: `/api/users/${userId}/notifications`, headers: auth(token) });
      expect(listRes.statusCode).toBe(200);
      expect(listRes.json().data.length).toBeGreaterThan(0);
    });

    it('같은 분석을 반복해도 알림 수가 늘지 않는다', async () => {
      const { userId, token } = await registerAndLogin('n2@example.com');

      const analyze = () =>
        app.inject({
          method: 'POST',
          url: '/api/analytics/financial-analysis',
          headers: auth(token),
          payload: { userId, snapshotDate: '2026-01-02' }
        });

      await analyze();
      const first = (await app.inject({ method: 'GET', url: `/api/users/${userId}/notifications`, headers: auth(token) })).json()
        .data.length;

      await analyze();
      const second = (await app.inject({ method: 'GET', url: `/api/users/${userId}/notifications`, headers: auth(token) })).json()
        .data.length;

      expect(second).toBe(first);
    });

    it('타인의 알림 목록은 403이다', async () => {
      const owner = await registerAndLogin('owner@example.com');
      const other = await registerAndLogin('other@example.com');

      const res = await app.inject({
        method: 'GET',
        url: `/api/users/${owner.userId}/notifications`,
        headers: auth(other.token)
      });
      expect(res.statusCode).toBe(403);
    });

    it('타인의 알림 읽음 처리는 403이다', async () => {
      const owner = await registerAndLogin('owner2@example.com');
      const other = await registerAndLogin('other2@example.com');

      const res = await app.inject({
        method: 'POST',
        url: `/api/users/${owner.userId}/notifications/some-id/read`,
        headers: auth(other.token)
      });
      expect(res.statusCode).toBe(403);
    });

    it('없는 알림을 읽음 처리하면 404다', async () => {
      const { userId, token } = await registerAndLogin('n3@example.com');

      const res = await app.inject({
        method: 'POST',
        url: `/api/users/${userId}/notifications/00000000-0000-0000-0000-000000000000/read`,
        headers: auth(token)
      });
      expect(res.statusCode).toBe(404);
      expect(res.json().error.code).toBe('NOTIFICATION_NOT_FOUND');
    });
  });

  describe('티켓 인증', () => {
    it('인증된 사용자는 티켓을 발급받는다', async () => {
      const { token } = await registerAndLogin('t1@example.com');

      const res = await app.inject({ method: 'POST', url: '/api/notifications/ticket', headers: auth(token) });
      expect(res.statusCode).toBe(200);
      expect(typeof res.json().data.ticket).toBe('string');
    });

    it('JWT 없이 티켓을 요청하면 401이다', async () => {
      const res = await app.inject({ method: 'POST', url: '/api/notifications/ticket' });
      expect(res.statusCode).toBe(401);
    });

    it('티켓 없이 스트림에 접속하면 401이다', async () => {
      const res = await app.inject({ method: 'GET', url: '/api/notifications/stream' });
      expect(res.statusCode).toBe(401);
    });

    it('위조 티켓으로 접속하면 401이다', async () => {
      const res = await app.inject({ method: 'GET', url: '/api/notifications/stream?ticket=not-a-real-ticket' });
      expect(res.statusCode).toBe(401);
    });
  });

  describe('SSE 스트림', () => {
    it('유효한 티켓으로 접속하면 SSE 헤더와 connected 프레임을 받는다', async () => {
      const { token } = await registerAndLogin('s1@example.com');
      const ticket = await issueTicketFor(token);
      const port = await listen();

      const client = await StreamClient.connect(port, `/api/notifications/stream?ticket=${ticket}`);
      try {
        const received = await client.waitFor('event: connected');
        expect(received).toContain('HTTP/1.1 200');
        expect(received.toLowerCase()).toContain('content-type: text/event-stream');
        expect(received).toContain('event: connected');
      } finally {
        client.close();
      }
    });

    it('스트림 연결 중 발생한 알림이 notification 프레임으로 전달된다', async () => {
      // 분석이 기록하는 스냅샷의 creditScore는 프로필 값을 쓴다. 낮은 점수를 부여해야
      // creditScore 지표가 실제로 임계값을 위반한다.
      const { userId, token } = await registerAndLogin('s2@example.com', 480);
      const ticket = await issueTicketFor(token);
      const port = await listen();

      const client = await StreamClient.connect(port, `/api/notifications/stream?ticket=${ticket}`);
      try {
        // connected 프레임을 기다려 구독 등록을 확정한 뒤에 알림을 유발한다.
        await client.waitFor('event: connected');

        await recordSnapshot(userId, 480, '2026-01-01');
        await app.inject({
          method: 'POST',
          url: '/api/analytics/financial-analysis',
          headers: auth(token),
          payload: { userId, snapshotDate: '2026-01-02' }
        });

        const received = await client.waitFor('event: notification');
        expect(received).toContain('creditScore');
      } finally {
        client.close();
      }
    });

    it('티켓은 1회용이라 재사용하면 401이다', async () => {
      const { token } = await registerAndLogin('s3@example.com');
      const ticket = await issueTicketFor(token);
      const port = await listen();

      const client = await StreamClient.connect(port, `/api/notifications/stream?ticket=${ticket}`);
      await client.waitFor('event: connected');
      client.close();

      const reuse = await app.inject({ method: 'GET', url: `/api/notifications/stream?ticket=${ticket}` });
      expect(reuse.statusCode).toBe(401);
    });
  });

  /**
   * 티켓은 1회용 60초 만료라 EventSource의 기본 자동 재연결이 반드시 실패한다.
   * 클라이언트가 백오프 없이 재발급을 반복하면 발급이 폭주하므로 한도를 둔다.
   */
  describe('남용 방지', () => {
    it('티켓 발급이 분당 한도를 넘으면 429다', async () => {
      const { token } = await registerAndLogin('rl@example.com');

      const codes: number[] = [];
      for (let i = 0; i < 22; i++) {
        const res = await app.inject({ method: 'POST', url: '/api/notifications/ticket', headers: auth(token) });
        codes.push(res.statusCode);
      }

      expect(codes.filter((c) => c === 200)).toHaveLength(20);
      expect(codes.filter((c) => c === 429)).toHaveLength(2);
      expect(codes[20]).toBe(429);
    });

    it('한도는 사용자별로 분리된다', async () => {
      const first = await registerAndLogin('rl-a@example.com');
      const second = await registerAndLogin('rl-b@example.com');

      for (let i = 0; i < 20; i++) {
        await app.inject({ method: 'POST', url: '/api/notifications/ticket', headers: auth(first.token) });
      }
      const exhausted = await app.inject({ method: 'POST', url: '/api/notifications/ticket', headers: auth(first.token) });
      const other = await app.inject({ method: 'POST', url: '/api/notifications/ticket', headers: auth(second.token) });

      expect(exhausted.statusCode).toBe(429);
      expect(other.statusCode).toBe(200);
    });

    it('동시 스트림이 상한을 넘으면 429이고, 닫으면 자리가 반환된다', async () => {
      const { userId, token } = await registerAndLogin('cap@example.com');
      const port = await listen();
      const clients: StreamClient[] = [];

      try {
        for (let i = 0; i < 5; i++) {
          const client = await StreamClient.connect(port, `/api/notifications/stream?ticket=${await issueTicketFor(token)}`);
          await client.waitFor('event: connected');
          clients.push(client);
        }

        const overflow = await app.inject({
          method: 'GET',
          url: `/api/notifications/stream?ticket=${await issueTicketFor(token)}`
        });
        expect(overflow.statusCode).toBe(429);
        expect(overflow.json().error.code).toBe('TOO_MANY_STREAMS');

        // 하나를 닫으면 자리가 비어 다시 열 수 있어야 한다.
        clients.pop()!.close();
        await waitUntil(() => hub.subscriberCount(userId) === 4);

        const reopened = await StreamClient.connect(
          port,
          `/api/notifications/stream?ticket=${await issueTicketFor(token)}`
        );
        clients.push(reopened);
        expect(await reopened.waitFor('event: connected')).toContain('HTTP/1.1 200');
      } finally {
        for (const client of clients) client.close();
      }
    });
  });
});
