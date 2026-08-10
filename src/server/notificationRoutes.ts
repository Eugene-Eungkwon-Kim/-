import { randomUUID } from 'node:crypto';
import type { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import type { Pool } from 'pg';
import type { CacheStore } from '../cache/cacheStore';
import type { NotificationHub } from '../notifications/notificationHub';
import { NotificationRepository } from '../repositories/NotificationRepository';
import { ServiceResult, toServiceResultAsync } from '../api/errorMapping';
import { routeSchemas } from './openapi-schemas';
import type { NotificationRecord } from '../types/notification';

/**
 * 알림 조회 + SSE 스트림 (Phase 15 - Section 2, B-6).
 */

/** 티켓 유효 시간. 발급 직후 스트림을 여는 정상 흐름에는 충분하고, 유출 창은 짧다. */
const TICKET_TTL_MS = 60_000;
const TICKET_PREFIX = 'sse:ticket:';

/** 대부분의 리버스 프록시 기본 유휴 타임아웃(30~60초)보다 짧게 잡는다. */
const HEARTBEAT_MS = 25_000;

/**
 * 브라우저 EventSource는 Authorization 헤더를 설정할 수 없다. JWT를 쿼리에 실으면
 * 1시간짜리 액세스 토큰이 프록시·액세스 로그에 남으므로, 60초 1회용 티켓을 대신 쓴다.
 *
 * 티켓 저장소로 CacheStore를 재사용한다 — 프로덕션(Redis)에서는 발급 인스턴스와
 * 스트림 인스턴스가 달라도 공유되고, 테스트(메모리)에서는 별도 준비가 필요 없다.
 */
export async function issueTicket(cache: CacheStore, userId: string): Promise<string> {
  const ticket = randomUUID();
  await cache.set(`${TICKET_PREFIX}${ticket}`, { userId }, TICKET_TTL_MS);
  return ticket;
}

/** 조회 즉시 삭제해 1회용을 보장한다. 유효하지 않으면 null. */
export async function consumeTicket(cache: CacheStore, ticket: string | undefined): Promise<string | null> {
  if (!ticket) return null;

  const key = `${TICKET_PREFIX}${ticket}`;
  const entry = await cache.get<{ userId: string }>(key);
  if (!entry) return null;

  await cache.delete(key);
  return entry.userId;
}

export interface NotificationRouteDeps {
  pool: Pool;
  cache: CacheStore;
  hub: NotificationHub;
  isOwner: (request: FastifyRequest, targetUserId: string) => boolean;
  forbidden: (reply: FastifyReply) => void;
  respond: <T>(reply: FastifyReply, result: ServiceResult<T>) => void;
}

export function registerNotificationRoutes(app: FastifyInstance, deps: NotificationRouteDeps): void {
  const { pool, cache, hub, isOwner, forbidden, respond } = deps;

  app.get('/api/users/:userId/notifications', { schema: routeSchemas.getNotifications }, async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);

    const { unreadOnly, limit } = request.query as { unreadOnly?: string; limit?: string };
    respond(
      reply,
      await toServiceResultAsync(async () =>
        new NotificationRepository(pool).list(userId, {
          unreadOnly: unreadOnly === 'true',
          limit: limit ? Number(limit) : undefined
        })
      )
    );
  });

  app.post('/api/users/:userId/notifications/:id/read', { schema: routeSchemas.postNotificationRead }, async (request, reply) => {
    const { userId, id } = request.params as { userId: string; id: string };
    if (!isOwner(request, userId)) return forbidden(reply);

    respond(reply, await toServiceResultAsync(async () => new NotificationRepository(pool).markRead(userId, id)));
  });

  app.post('/api/notifications/ticket', { schema: routeSchemas.postNotificationTicket }, async (request, reply) => {
    const authUser = request.user as { userId: string };
    const ticket = await issueTicket(cache, authUser.userId);
    reply.send({ success: true, data: { ticket, expiresInMs: TICKET_TTL_MS } });
  });

  /**
   * SSE 스트림. PUBLIC_ROUTES에 등록되어 JWT 훅을 거치지 않으며, 티켓으로 인증한다.
   */
  app.get('/api/notifications/stream', { schema: routeSchemas.getNotificationStream }, async (request, reply) => {
    const { ticket } = request.query as { ticket?: string };
    const userId = await consumeTicket(cache, ticket);
    if (!userId) {
      return reply
        .code(401)
        .send({ success: false, error: { code: 'UNAUTHORIZED', message: 'Missing, expired, or already used ticket' } });
    }

    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      // nginx 등 리버스 프록시의 응답 버퍼링을 끈다 — 켜져 있으면 이벤트가 모였다가 나간다.
      'X-Accel-Buffering': 'no'
    });
    // hijack()을 호출하지 않으면 Fastify가 응답을 종료시켜 스트림이 즉시 끊긴다.
    // 증상이 "연결은 되는데 아무것도 안 옴"이라 원인 파악이 오래 걸리는 함정이다.
    reply.hijack();

    const write = (chunk: string): void => {
      if (!reply.raw.writableEnded) reply.raw.write(chunk);
    };

    // 연결 직후 1프레임을 보내 클라이언트가 open을 확정할 수 있게 한다.
    write(`event: connected\ndata: ${JSON.stringify({ userId })}\n\n`);

    const send = (notification: NotificationRecord): void => {
      write(`event: notification\ndata: ${JSON.stringify(notification)}\n\n`);
    };

    const unsubscribe = hub.subscribe(userId, send);
    const heartbeat = setInterval(() => write(': ping\n\n'), HEARTBEAT_MS);
    // 하트비트가 이벤트 루프를 붙잡아 프로세스 종료를 막지 않게 한다.
    heartbeat.unref?.();

    let closed = false;
    const cleanup = (): void => {
      if (closed) return;
      closed = true;
      clearInterval(heartbeat);
      unsubscribe();
      if (!reply.raw.writableEnded) reply.raw.end();
    };

    request.raw.on('close', cleanup);
    request.raw.on('error', cleanup);
  });
}
