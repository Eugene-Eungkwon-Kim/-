import Fastify, { FastifyReply, FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import type Database from 'better-sqlite3';
import { getUserProfile, registerUser } from '../api/userService';
import { applyForLoan, getLoanPortfolio, getLoanPortfolioSummary } from '../api/loanService';
import { ServiceResult } from '../api/errorMapping';

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
  INTERNAL_ERROR: 500
};

function respond<T>(reply: FastifyReply, result: ServiceResult<T>): void {
  if (result.success) {
    reply.send(result);
    return;
  }
  reply.code(STATUS_BY_ERROR_CODE[result.error.code] ?? 500).send(result);
}

export function buildServer(db: Database.Database): FastifyInstance {
  const app = Fastify({ logger: false });
  app.register(cors, { origin: true });

  app.post('/api/users', async (request, reply) => {
    respond(reply, registerUser(db, request.body as Parameters<typeof registerUser>[1]));
  });

  app.get('/api/users/:userId', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    respond(reply, getUserProfile(db, userId));
  });

  app.post('/api/loans', async (request, reply) => {
    const result = await applyForLoan(db, request.body as Parameters<typeof applyForLoan>[1]);
    respond(reply, result);
  });

  app.get('/api/users/:userId/loans', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    respond(reply, getLoanPortfolio(db, userId));
  });

  app.get('/api/users/:userId/loans/summary', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    respond(reply, getLoanPortfolioSummary(db, userId));
  });

  return app;
}
