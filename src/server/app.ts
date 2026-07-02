import Fastify, { FastifyReply, FastifyRequest, FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import rateLimit from '@fastify/rate-limit';
import helmet from '@fastify/helmet';
import type Database from 'better-sqlite3';
import { getUserProfile, registerUser } from '../api/userService';
import { applyForLoan, getLoanPortfolio, getLoanPortfolioSummary } from '../api/loanService';
import { issueRefreshToken, revokeRefreshToken, verifyCredentials, verifyRefreshToken } from '../api/authService';
import { ServiceResult } from '../api/errorMapping';
import { resolveServerEnv } from './env';

export interface BuildServerOptions {
  jwtSecret?: string;
}

/**
 * 인증 없이 접근 가능한 (method, path) 목록. /api/auth/refresh와 /api/auth/logout도
 * 여기 포함된다 — 이 두 엔드포인트는 (이미 만료됐을 수 있는) 액세스 JWT가 아니라
 * 리프레시 토큰 자체를 자격증명으로 사용하기 때문이다.
 */
const PUBLIC_ROUTES: Array<[string, string]> = [
  ['POST', '/api/auth/login'],
  ['POST', '/api/auth/refresh'],
  ['POST', '/api/auth/logout'],
  ['POST', '/api/users']
];

/**
 * 프론트엔드 연동을 위한 최소 HTTP 서버 (Fastify).
 *
 * src/api/*Service.ts가 이미 ServiceResult<T>({success, data} | {success, error})
 * 형태로 실패를 값으로 표현하므로, 이 레이어는 그 결과를 HTTP 상태 코드에
 * 매핑하는 얇은 어댑터일 뿐이다 — 비즈니스 로직은 전혀 추가하지 않는다.
 */
const STATUS_BY_ERROR_CODE: Record<string, number> = {
  VALIDATION_ERROR: 400,
  DUPLICATE_EMAIL: 409,
  VERSION_CONFLICT: 409,
  USER_NOT_FOUND: 404,
  LOAN_NOT_FOUND: 404,
  TRANSACTION_NOT_FOUND: 404,
  BACKUP_NOT_FOUND: 404,
  OVERPAYMENT: 400,
  INVALID_CREDENTIALS: 401,
  INVALID_REFRESH_TOKEN: 401,
  INTERNAL_ERROR: 500
};

function respond<T>(reply: FastifyReply, result: ServiceResult<T>): void {
  if (result.success) {
    reply.send(result);
    return;
  }
  reply.code(STATUS_BY_ERROR_CODE[result.error.code] ?? 500).send(result);
}

/**
 * 권한 검사 (Day 8 - Task 3, δ=1360): 요청자(JWT의 userId)와 대상 리소스의
 * 소유자가 다르면 403. 존재 여부보다 소유권을 먼저 확인해, 타인의 리소스에
 * 대해서는 "존재하지 않음"과 "내 것이 아님"을 구분해 노출하지 않는다.
 */
function isOwner(request: FastifyRequest, targetUserId: string): boolean {
  const authUser = request.user as { userId: string };
  return authUser.userId === targetUserId;
}

function forbidden(reply: FastifyReply): void {
  reply.code(403).send({ success: false, error: { code: 'FORBIDDEN', message: 'You do not have access to this resource' } });
}

export async function buildServer(db: Database.Database, options: BuildServerOptions = {}): Promise<FastifyInstance> {
  // Day 9 - Task 1 (δ=1270): JWT_SECRET을 여기서 조용히 폴백시키지 않는다.
  // 실제 기동 경로(src/server/index.ts)는 resolveServerEnv()를 직접 호출해
  // production에서 시크릿 누락 시 서버가 뜨기도 전에 실패하도록 하고, 그 결과를
  // options.jwtSecret으로 주입한다. 이 폴백은 index.ts를 거치지 않는 임시
  // buildServer() 호출(테스트 등)을 위한 안전망일 뿐이다.
  const jwtSecret = options.jwtSecret ?? resolveServerEnv().jwtSecret;

  const app = Fastify({ logger: false });
  await app.register(cors, { origin: true });
  // Day 9 - Task 5 (δ=1015): CSP는 이 서버가 HTML/스크립트를 서빙하지 않는
  // 순수 JSON API라 적용 대상이 아니므로 끈다. crossOriginResourcePolicy는
  // helmet 기본값(same-origin)이 @fastify/cors의 origin:true 의도(교차 출처
  // 배포 허용)와 충돌할 수 있어 cross-origin으로 완화한다.
  await app.register(helmet, { contentSecurityPolicy: false, crossOriginResourcePolicy: { policy: 'cross-origin' } });
  await app.register(jwt, { secret: jwtSecret });
  // Day 9 - Task 2 (δ=1230): @fastify/rate-limit는 라우트 등록 시점에
  // config.rateLimit을 가로채는 onRoute 훅을 심는다. register()를 await하지
  // 않고 바로 라우트를 정의하면(다른 플러그인과 달리) 이 훅이 아직 준비되지
  // 않아 라우트별 제한이 조용히 무시된다 — 실제로 겪은 문제라 반드시 await 필요.
  await app.register(rateLimit, { global: false });

  // 인증 훅 (Day 8 - Task 4, δ=1360): 공개 라우트를 제외한 모든 요청은 유효한
  // JWT가 있어야 통과한다. 성공 시 request.user에 { userId }가 채워진다.
  app.addHook('onRequest', async (request, reply) => {
    const path = request.url.split('?')[0];
    const isPublic = PUBLIC_ROUTES.some(([method, url]) => request.method === method && path === url);
    if (isPublic) return;

    try {
      await request.jwtVerify();
    } catch {
      reply.code(401).send({ success: false, error: { code: 'UNAUTHORIZED', message: 'Missing or invalid authorization token' } });
    }
  });

  app.post('/api/users', async (request, reply) => {
    respond(reply, registerUser(db, request.body as Parameters<typeof registerUser>[1]));
  });

  app.post(
    '/api/auth/login',
    {
      config: {
        rateLimit: {
          max: 5,
          timeWindow: '1 minute',
          errorResponseBuilder: (_request: FastifyRequest, context: { after: string }) => ({
            statusCode: 429,
            success: false,
            error: { code: 'RATE_LIMITED', message: `Too many login attempts, retry in ${context.after}` }
          })
        }
      }
    },
    async (request, reply) => {
      const { email, password } = request.body as { email: string; password: string };
      const result = verifyCredentials(db, email, password);
      if (!result.success) {
        respond(reply, result);
        return;
      }
      const refreshResult = issueRefreshToken(db, result.data.id);
      if (!refreshResult.success) {
        respond(reply, refreshResult);
        return;
      }
      const token = await reply.jwtSign({ userId: result.data.id }, { expiresIn: '1h' });
      reply.send({ success: true, data: { token, refreshToken: refreshResult.data.token, user: result.data } });
    }
  );

  app.post('/api/auth/refresh', async (request, reply) => {
    const { refreshToken } = request.body as { refreshToken: string };
    const verified = verifyRefreshToken(db, refreshToken);
    if (!verified.success) {
      respond(reply, verified);
      return;
    }

    // 회전(rotation): 제시된 리프레시 토큰은 즉시 무효화하고 새 토큰을 발급한다.
    // 탈취된 리프레시 토큰이 갱신 이후에도 재사용될 여지를 없앤다.
    revokeRefreshToken(db, refreshToken);
    const rotated = issueRefreshToken(db, verified.data.userId);
    if (!rotated.success) {
      respond(reply, rotated);
      return;
    }

    const token = await reply.jwtSign({ userId: verified.data.userId }, { expiresIn: '1h' });
    reply.send({ success: true, data: { token, refreshToken: rotated.data.token } });
  });

  app.post('/api/auth/logout', async (request, reply) => {
    const { refreshToken } = request.body as { refreshToken: string };
    respond(reply, revokeRefreshToken(db, refreshToken));
  });

  app.get('/api/users/:userId', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, getUserProfile(db, userId));
  });

  app.post('/api/loans', async (request, reply) => {
    const body = request.body as Parameters<typeof applyForLoan>[1];
    if (!isOwner(request, body.userId)) return forbidden(reply);
    const result = await applyForLoan(db, body);
    respond(reply, result);
  });

  app.get('/api/users/:userId/loans', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, getLoanPortfolio(db, userId));
  });

  app.get('/api/users/:userId/loans/summary', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, getLoanPortfolioSummary(db, userId));
  });

  return app;
}
