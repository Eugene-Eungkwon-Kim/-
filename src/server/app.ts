import Fastify, { FastifyReply, FastifyRequest, FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import type Database from 'better-sqlite3';
import { getUserProfile, registerUser } from '../api/userService';
import { applyForLoan, getLoanPortfolio, getLoanPortfolioSummary } from '../api/loanService';
import { verifyCredentials } from '../api/authService';
import { ServiceResult } from '../api/errorMapping';

const JWT_SECRET = process.env.JWT_SECRET ?? 'dev-secret-change-in-production';

/** 인증 없이 접근 가능한 (method, path) 목록 — 회원가입과 로그인만 예외 */
const PUBLIC_ROUTES: Array<[string, string]> = [
  ['POST', '/api/auth/login'],
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

export function buildServer(db: Database.Database): FastifyInstance {
  const app = Fastify({ logger: false });
  app.register(cors, { origin: true });
  app.register(jwt, { secret: JWT_SECRET });

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

  app.post('/api/auth/login', async (request, reply) => {
    const { email, password } = request.body as { email: string; password: string };
    const result = verifyCredentials(db, email, password);
    if (!result.success) {
      respond(reply, result);
      return;
    }
    const token = await reply.jwtSign({ userId: result.data.id }, { expiresIn: '1h' });
    reply.send({ success: true, data: { token, user: result.data } });
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
