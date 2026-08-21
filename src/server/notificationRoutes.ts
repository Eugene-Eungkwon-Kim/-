import { randomUUID } from 'node:crypto';
import type { StreamRegistry } from '../notifications/streamRegistry';
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
 * 티켓 발급 한도 (분당). 재연결마다 티켓이 1장 필요하므로 로그인(5회)보다는
 * 넉넉해야 하지만, 백오프 없는 재연결 루프는 이 선에서 막힌다.
 */
const TICKET_RATE_LIMIT = 20;

/**
 * 사용자당 동시 SSE 연결 상한. 정상 사용은 탭 몇 개 수준이라 5면 충분하다.
 * StreamRegistry가 Redis 기반이면 인스턴스 전체에 걸쳐 적용된다.
 */
const MAX_STREAMS_PER_USER = 5;

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
  streams: StreamRegistry;
  isOwner: (request: FastifyRequest, targetUserId: string) => boolean;
  forbidden: (reply: FastifyReply) => void;
  respond: <T>(reply: FastifyReply, result: ServiceResult<T>) => void;
}

export function registerNotificationRoutes(app: FastifyInstance, deps: NotificationRouteDeps): void {
  const { pool, cache, hub, streams, isOwner, forbidden, respond } = deps;

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

  app.get('/api/users/:userId/notifications/unread-count', { schema: routeSchemas.getUnreadCount }, async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);

    respond(
      reply,
      await toServiceResultAsync(async () => ({ count: await new NotificationRepository(pool).countUnread(userId) }))
    );
  });

  app.post('/api/users/:userId/notifications/:id/read', { schema: routeSchemas.postNotificationRead }, async (request, reply) => {
    const { userId, id } = request.params as { userId: string; id: string };
    if (!isOwner(request, userId)) return forbidden(reply);

    respond(reply, await toServiceResultAsync(async () => new NotificationRepository(pool).markRead(userId, id)));
  });

  app.post(
    '/api/notifications/ticket',
    {
      schema: routeSchemas.postNotificationTicket,
      config: {
        rateLimit: {
          max: TICKET_RATE_LIMIT,
          timeWindow: '1 minute',
          // 기본 키는 IP다. 이 라우트는 JWT 검증을 이미 통과했으므로 사용자별로
          // 센다 — NAT 뒤의 여러 사용자가 서로의 한도를 잡아먹지 않게 한다.
          keyGenerator: (request: FastifyRequest) => (request.user as { userId?: string })?.userId ?? request.ip,
          errorResponseBuilder: (_request: FastifyRequest, context: { after: string }) => ({
            statusCode: 429,
            success: false,
            error: { code: 'RATE_LIMITED', message: `Too many ticket requests, retry in ${context.after}` }
          })
        }
      }
    },
    async (request, reply) => {
      const authUser = request.user as { userId: string };
      const ticket = await issueTicket(cache, authUser.userId);
      reply.send({ success: true, data: { ticket, expiresInMs: TICKET_TTL_MS } });
    }
  );

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

    // 먼저 등록하고 결과 개수로 판단한다. 세고 나서 등록하면 두 인스턴스가 동시에
    // 같은 빈자리를 보고 둘 다 통과한다. 상한 검사는 헤더를 쓰기 전에 끝나야 한다 —
    // writeHead 이후에는 상태 코드를 바꿀 수 없어 429를 돌려줄 방법이 없다.
    const streamId = randomUUID();
    const openStreams = await streams.registerAndCount(userId, streamId, Date.now());
    if (openStreams > MAX_STREAMS_PER_USER) {
      await streams.unregister(userId, streamId);
      return reply.code(429).send({
        success: false,
        error: {
          code: 'TOO_MANY_STREAMS',
          message: `At most ${MAX_STREAMS_PER_USER} concurrent notification streams are allowed`
        }
      });
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
    const heartbeat = setInterval(() => {
      write(': ping\n\n');
      // 레지스트리 항목을 갱신해 두지 않으면 STALE_AFTER_MS 뒤 살아 있는 스트림이
      // 죽은 것으로 걷힌다.
      void streams.heartbeat(userId, streamId, Date.now()).catch(() => undefined);
    }, HEARTBEAT_MS);
    // 하트비트가 이벤트 루프를 붙잡아 프로세스 종료를 막지 않게 한다.
    heartbeat.unref?.();

    let closed = false;
    let unsubscribeRevoke = (): void => {};

    const cleanup = (): void => {
      if (closed) return;
      closed = true;
      clearInterval(heartbeat);
      unsubscribe();
      unsubscribeRevoke();
      void streams.unregister(userId, streamId).catch(() => undefined);
      if (!reply.raw.writableEnded) reply.raw.end();
    };

    // 로그아웃 등으로 서버가 이 사용자의 스트림을 끊을 때 호출된다. 스트림은
    // 티켓 1회로만 인증되고 이후 재인증되지 않으므로, 클라이언트가 닫아주기를
    // 기대하지 않고 서버가 직접 끊는다. 끊기 전에 이유를 한 프레임 보내
    // 클라이언트가 재연결 루프에 빠지지 않고 로그아웃으로 처리하게 한다.
    unsubscribeRevoke = hub.onRevoke(userId, () => {
      write(`event: revoked\ndata: ${JSON.stringify({ reason: 'session_ended' })}\n\n`);
      cleanup();
    });

    request.raw.on('close', cleanup);
    request.raw.on('error', cleanup);
  });
}
