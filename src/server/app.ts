import path from 'node:path';
import Fastify, { FastifyReply, FastifyRequest, FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import rateLimit from '@fastify/rate-limit';
import helmet from '@fastify/helmet';
import swagger from '@fastify/swagger';
import swaggerUI from '@fastify/swagger-ui';
import type { Pool } from 'pg';
import { LoanRepository } from '../repositories/LoanRepository';
import { getUserProfile, registerUser } from '../api/userService';
import { applyForLoan, detectDelinquentLoans, getLoanPortfolio, getLoanPortfolioSummary, recordLoanPayment } from '../api/loanService';
import { issueRefreshToken, revokeRefreshToken, verifyCredentials, verifyRefreshToken } from '../api/authService';
import {
  CreditSimulationRequest,
  compareSnapshotPerformance,
  getSnapshotTrend,
  runCreditSimulation,
  runFinancialAnalysis,
  runRiskAssessment
} from '../api/financialAnalyticsService';
import {
  getTransactionAuditLog,
  getTransactionHistory,
  getTransactionMonthlyTrend,
  getTransactionSummary,
  recordTransaction,
  rescanAnomalies
} from '../api/transactionService';
import { getDashboard } from '../api/dashboardService';
import { createNotificationHub, type NotificationHub } from '../notifications/notificationHub';
import { registerNotificationRoutes } from './notificationRoutes';
import { createStreamRegistry, type StreamRegistry } from '../notifications/streamRegistry';
import { createCacheStore } from '../cache/cacheFactory';
import {
  checkBackupDue,
  createBackup,
  listBackups,
  pruneOldBackups,
  pruneOldNotifications,
  runIntegrityCheck,
  verifyBackup
} from '../api/adminService';
import { ServiceResult } from '../api/errorMapping';
import { TrendMetric } from '../types/financialSnapshot';
import { RecordPaymentInput } from '../types/loanPortfolio';
import { RecordTransactionInput, TransactionFilter } from '../types/transaction';
import { resolveServerEnv } from './env';
import { AuditLogger } from '../audit/auditLogger';
import { openAPISchemas, routeSchemas } from './openapi-schemas';

export interface BuildServerOptions {
  jwtSecret?: string;
  backupDir?: string;
  /** 미지정 시 REDIS_URL 유무로 결정된다. 테스트는 메모리 허브를 주입해 격리한다. */
  notificationHub?: NotificationHub;
  /** 미지정 시 REDIS_URL 유무로 결정된다. Redis면 상한이 인스턴스 전체에 걸린다. */
  streamRegistry?: StreamRegistry;
  /** SSE 스트림 최대 수명(ms). 미지정 시 notificationRoutes의 기본값(50분)을 쓴다. */
  streamLifetimeMs?: number;
}

const DEFAULT_BACKUP_DIR = path.join(process.cwd(), 'data', 'backups');

/**
 * 인증 없이 접근 가능한 (method, path) 목록. /api/auth/refresh와 /api/auth/logout도
 * 여기 포함된다 — 이 두 엔드포인트는 (이미 만료됐을 수 있는) 액세스 JWT가 아니라
 * 리프레시 토큰 자체를 자격증명으로 사용하기 때문이다.
 */
const PUBLIC_ROUTES: Array<[string, string]> = [
  ['GET', '/health'],
  ['POST', '/api/auth/login'],
  ['POST', '/api/auth/refresh'],
  ['POST', '/api/auth/logout'],
  ['POST', '/api/users'],
  // SSE 스트림은 EventSource가 Authorization 헤더를 못 붙이므로 JWT 대신
  // 1회용 티켓으로 인증한다. 인증 훅이 쿼리스트링을 제거한 뒤 비교하므로
  // ?ticket=... 이 붙어도 이 항목과 정확히 매칭된다.
  ['GET', '/api/notifications/stream']
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
  SNAPSHOT_NOT_FOUND: 404,
  NOTIFICATION_NOT_FOUND: 404,
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

/**
 * 관리자 권한 검사 (Day 10 - Task 3, δ=1065). role은 로그인/리프레시 시점에
 * JWT payload에 실려오므로 요청마다 DB를 다시 조회할 필요가 없다. role 변경
 * API는 범위 밖 — 운영에서는 DB에 직접 SQL로 승격한다(시드 스크립트 등).
 */
function isAdmin(request: FastifyRequest): boolean {
  const authUser = request.user as { role?: string };
  return authUser.role === 'admin';
}

function forbidden(reply: FastifyReply): void {
  reply.code(403).send({ success: false, error: { code: 'FORBIDDEN', message: 'You do not have access to this resource' } });
}

export async function buildServer(pool: Pool, options: BuildServerOptions = {}): Promise<FastifyInstance> {
  // Day 9 - Task 1 (δ=1270): JWT_SECRET을 여기서 조용히 폴백시키지 않는다.
  // 실제 기동 경로(src/server/index.ts)는 resolveServerEnv()를 직접 호출해
  // production에서 시크릿 누락 시 서버가 뜨기도 전에 실패하도록 하고, 그 결과를
  // options.jwtSecret으로 주입한다. 이 폴백은 index.ts를 거치지 않는 임시
  // buildServer() 호출(테스트 등)을 위한 안전망일 뿐이다.
  const jwtSecret = options.jwtSecret ?? resolveServerEnv().jwtSecret;
  const backupDir = options.backupDir ?? DEFAULT_BACKUP_DIR;

  // Phase 15 - Section 2: 알림 팬아웃 허브와 SSE 티켓 저장소.
  // 티켓을 프로세스 메모리에 두면 발급 인스턴스와 스트림 인스턴스가 달라질 때
  // 실패하므로, 0b에서 안정화한 CacheStore(프로덕션=Redis)를 그대로 쓴다.
  const notificationHub = options.notificationHub ?? createNotificationHub();
  const streamRegistry = options.streamRegistry ?? createStreamRegistry();
  const cache = createCacheStore(pool);

  // Day 11 - Task 3 (δ=915): 구조화된 로깅 활성화 (pino 기반)
  // Fastify의 내장 pino 통합: true면 기본 pino, 객체면 pino 옵션으로 간주
  // 프로덕션(NODE_ENV=production)에서는 JSON, 개발에서는 pino-pretty 포맷
  const isProduction = process.env.NODE_ENV === 'production';
  const loggerConfig = isProduction
    ? true // 프로덕션: 기본 pino (JSON)
    : {
        level: process.env.LOG_LEVEL ?? 'debug',
        transport: {
          target: 'pino-pretty',
          options: {
            colorize: true,
            singleLine: false,
            translateTime: 'SYS:standard',
            ignore: 'pid,hostname'
          }
        }
      };

  const app = Fastify({ logger: loggerConfig });
  await app.register(cors, { origin: true });
  // Day 9 - Task 5 (δ=1015): CSP는 이 서버가 HTML/스크립트를 서빙하지 않는
  // 순수 JSON API라 적용 대상이 아니므로 끈다. crossOriginResourcePolicy는
  // helmet 기본값(same-origin)이 @fastify/cors의 origin:true 의도(교차 출처
  // 배포 허용)와 충돌할 수 있어 cross-origin으로 완화한다.
  await app.register(helmet, { contentSecurityPolicy: false, crossOriginResourcePolicy: { policy: 'cross-origin' } });

  // Day 11 - Task 5 (δ=780): OpenAPI 자동 문서생성 (swagger + swagger-ui)
  // Day 14 - Task H (δ=400): OpenAPI 스키마 확장
  // openAPISchemas의 JSON 스키마 리터럴이 @fastify/swagger의 OpenAPIV3 타입과
  // 구조적으로 호환되지만 타입 추론이 실패하므로 옵션 객체를 한 번 캐스팅한다.
  await app.register(swagger, {
    openapi: {
      openapi: '3.0.0',
      info: {
        title: 'MAARS 금융 플랫폼 API',
        version: '1.0.0',
        description: 'Multi-Agent AI Risk & Loan Service API',
        contact: {
          name: 'API Support',
          email: 'support@maars.example.com'
        },
        license: {
          name: 'MIT'
        }
      },
      servers: [
        { url: 'http://localhost:3001', description: 'Development' },
        { url: 'https://api.maars.example.com', description: 'Production' }
      ],
      components: {
        schemas: openAPISchemas,
        securitySchemes: {
          Bearer: {
            type: 'http',
            scheme: 'bearer',
            bearerFormat: 'JWT',
            description: 'JWT Access Token (유효 기간: 1시간)'
          }
        },
        responses: {
          ValidationError: {
            description: '입력 검증 오류',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/ValidationError' }
              }
            }
          },
          DuplicateEmail: {
            description: '이메일 중복',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/DuplicateEmail' }
              }
            }
          },
          NotFound: {
            description: '리소스를 찾을 수 없음',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/NotFound' }
              }
            }
          },
          Unauthorized: {
            description: '인증 실패',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/Unauthorized' }
              }
            }
          },
          Forbidden: {
            description: '권한 없음',
            content: {
              'application/json': {
                schema: { $ref: '#/components/schemas/Forbidden' }
              }
            }
          }
        }
      },
      security: [{ Bearer: [] }],
      tags: [
        { name: 'Authentication', description: '인증 관련 엔드포인트' },
        { name: 'Users', description: '사용자 프로필 관리' },
        { name: 'Loans', description: '대출 신청 및 관리' },
        { name: 'Transactions', description: '거래 기록 및 조회' },
        { name: 'Analytics', description: '금융 분석 및 시뮬레이션' },
        { name: 'Notifications', description: '임계값 알림 조회 및 SSE 실시간 스트림' },
        { name: 'Admin', description: '관리자 전용 기능' },
        { name: 'Audit', description: '감사 로그 조회' }
      ]
    }
  } as Parameters<typeof app.register>[1]);
  await app.register(swaggerUI, {
    routePrefix: '/api/docs',
    uiConfig: {
      docExpansion: 'full',
      deepLinking: true
    }
  });

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

    // Day 14 - Task I (δ=400): API 문서(Swagger UI)는 인증 없이 접근 가능
    if (request.method === 'GET' && (path === '/api/docs' || path.startsWith('/api/docs/'))) return;

    try {
      await request.jwtVerify();
    } catch {
      reply.code(401).send({ success: false, error: { code: 'UNAUTHORIZED', message: 'Missing or invalid authorization token' } });
    }
  });

  // Day 11 - Task 4 (δ=865): 헬스체크 엔드포인트 (인증 불필요)
  app.get(
    '/health',
    {
      schema: {
        response: {
          200: {
            type: 'object',
            properties: {
              status: { type: 'string', enum: ['ok', 'error'] },
              db: { type: 'string', enum: ['connected', 'disconnected'] }
            }
          },
          503: {
            type: 'object',
            properties: {
              status: { type: 'string', enum: ['ok', 'error'] },
              db: { type: 'string', enum: ['connected', 'disconnected'] }
            }
          }
        }
      }
    },
    async (_request, reply) => {
      try {
        await pool.query('SELECT 1');
        reply.send({ status: 'ok', db: 'connected' });
      } catch (error) {
        reply.code(503).send({ status: 'error', db: 'disconnected' });
      }
    }
  );

  app.post('/api/users', { schema: routeSchemas.postUsers }, async (request, reply) => {
    respond(reply, await registerUser(pool, request.body as Parameters<typeof registerUser>[1]));
  });

  app.post(
    '/api/auth/login',
    {
      schema: {
        body: {
          type: 'object',
          properties: {
            email: { type: 'string', format: 'email' },
            password: { type: 'string' }
          },
          required: ['email', 'password']
        },
        response: {
          200: {
            type: 'object',
            properties: {
              success: { type: 'boolean', const: true },
              data: {
                type: 'object',
                properties: {
                  token: { type: 'string' },
                  refreshToken: { type: 'string' },
                  user: {
                    type: 'object',
                    properties: {
                      id: { type: 'string' },
                      email: { type: 'string' },
                      name: { type: 'string' },
                      creditProfile: {
                        type: 'object',
                        properties: {
                          score: { type: ['number', 'null'] },
                          grade: { type: ['string', 'null'] }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      },
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
      const result = await verifyCredentials(pool, email, password);
      if (!result.success) {
        respond(reply, result);
        return;
      }
      const refreshResult = await issueRefreshToken(pool, result.data.id);
      if (!refreshResult.success) {
        respond(reply, refreshResult);
        return;
      }
      const token = await reply.jwtSign({ userId: result.data.id, role: result.data.metadata.role }, { expiresIn: '1h' });
      reply.send({ success: true, data: { token, refreshToken: refreshResult.data.token, user: result.data } });
    }
  );

  app.post('/api/auth/refresh', async (request, reply) => {
    const { refreshToken } = request.body as { refreshToken: string };
    const verified = await verifyRefreshToken(pool, refreshToken);
    if (!verified.success) {
      respond(reply, verified);
      return;
    }

    // 회전(rotation): 제시된 리프레시 토큰은 즉시 무효화하고 새 토큰을 발급한다.
    // 탈취된 리프레시 토큰이 갱신 이후에도 재사용될 여지를 없앤다.
    await revokeRefreshToken(pool, refreshToken);
    const rotated = await issueRefreshToken(pool, verified.data.userId);
    if (!rotated.success) {
      respond(reply, rotated);
      return;
    }

    // role은 로그인 이후 바뀌었을 수 있으므로(관리자 승격 등) 리프레시 토큰이
    // 아니라 최신 프로필에서 다시 읽어 새 액세스 토큰에 반영한다.
    const profile = await getUserProfile(pool, verified.data.userId);
    const role = profile.success ? profile.data.metadata.role : 'user';

    const token = await reply.jwtSign({ userId: verified.data.userId, role }, { expiresIn: '1h' });
    reply.send({ success: true, data: { token, refreshToken: rotated.data.token } });
  });

  app.post('/api/auth/logout', async (request, reply) => {
    const { refreshToken } = request.body as { refreshToken: string };
    const result = await revokeRefreshToken(pool, refreshToken);

    // 열린 SSE 스트림은 티켓 1회로만 인증돼 이후 재인증되지 않는다. 서버가 끊지
    // 않으면 로그아웃한 사용자의 브라우저로 알림이 계속 흐른다.
    if (result.success && result.data.userId) {
      await notificationHub.revoke(result.data.userId);
    }

    respond(reply, result);
  });

  app.get('/api/users/:userId', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getUserProfile(pool, userId));
  });

  app.post('/api/loans', async (request, reply) => {
    const body = request.body as Parameters<typeof applyForLoan>[1];
    if (!isOwner(request, body.userId)) return forbidden(reply);
    const result = await applyForLoan(pool, body);
    respond(reply, result);
  });

  app.get('/api/users/:userId/loans', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getLoanPortfolio(pool, userId));
  });

  app.get('/api/users/:userId/loans/summary', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getLoanPortfolioSummary(pool, userId));
  });

  // Day 10 - Task 1 (δ=1270): 금융분석 서비스(Day6/7에서 이미 구현·테스트됨)를
  // 처음으로 HTTP에 노출한다. Day6이 "리포지토리는 있는데 아무도 호출 안 함"을
  // 해결했던 것과 같은 종류의 갭을 서비스→HTTP 경계에서 마저 해소.
  app.post('/api/analytics/credit-simulation', async (request, reply) => {
    const body = request.body as { userId: string } & CreditSimulationRequest;
    if (!isOwner(request, body.userId)) return forbidden(reply);
    const result = await runCreditSimulation(pool, body.userId, { scenario: body.scenario, duration: body.duration });
    respond(reply, result);
  });

  app.post('/api/analytics/risk-assessment', async (request, reply) => {
    const body = request.body as { userId: string; snapshotDate: string };
    if (!isOwner(request, body.userId)) return forbidden(reply);
    const result = await runRiskAssessment(pool, body.userId, body.snapshotDate, notificationHub);
    respond(reply, result);
  });

  app.post('/api/analytics/financial-analysis', async (request, reply) => {
    const body = request.body as { userId: string; snapshotDate: string };
    if (!isOwner(request, body.userId)) return forbidden(reply);
    const result = await runFinancialAnalysis(pool, body.userId, body.snapshotDate, notificationHub);
    respond(reply, result);
  });

  app.get('/api/users/:userId/snapshots/trend/:metric', async (request, reply) => {
    const { userId, metric } = request.params as { userId: string; metric: TrendMetric };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getSnapshotTrend(pool, userId, metric));
  });

  // Day 10 - Task 2 (δ=1220): transactionService.ts(Day6에서 구현·테스트됨)도
  // 동일하게 HTTP로 노출한다.
  app.post('/api/transactions', async (request, reply) => {
    const body = request.body as RecordTransactionInput;
    if (!isOwner(request, body.userId)) return forbidden(reply);
    respond(reply, await recordTransaction(pool, body));
  });

  app.get('/api/users/:userId/transactions', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    const filter = request.query as TransactionFilter;
    respond(reply, await getTransactionHistory(pool, userId, filter));
  });

  app.get('/api/users/:userId/transactions/summary', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getTransactionSummary(pool, userId));
  });

  app.post('/api/users/:userId/transactions/rescan', async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await rescanAnomalies(pool, userId));
  });

  // Phase 15 - Section 3 (A-3): 이미 구현·테스트됐지만 라우트가 없어 외부에서
  // 호출할 수 없던 서비스 3종을 노출한다. 신규 비즈니스 로직은 없다.
  app.get('/api/users/:userId/transactions/trend', { schema: routeSchemas.getTransactionTrend }, async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getTransactionMonthlyTrend(pool, userId));
  });

  app.post('/api/users/:userId/snapshots/compare', { schema: routeSchemas.postSnapshotCompare }, async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    const { fromDate, toDate } = request.body as { fromDate: string; toDate: string };
    respond(reply, await compareSnapshotPerformance(pool, userId, fromDate, toDate));
  });

  // 감사 로그는 transactionId가 선택 인자라 생략하면 전체 거래가 반환된다.
  // 소유권 개념이 성립하지 않으므로 기존 /api/admin/audit-logs 계열과 같이 isAdmin.
  app.get('/api/admin/transactions/audit-log', { schema: routeSchemas.getTransactionAuditLog }, async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { transactionId, from, to } = request.query as { transactionId?: string; from?: string; to?: string };
    respond(reply, await getTransactionAuditLog(pool, transactionId, { from, to }));
  });

  // Phase 15 - Section 3 (A-4): 대시보드 초기 로드를 1회 요청으로 묶는다.
  app.get('/api/users/:userId/dashboard', { schema: routeSchemas.getDashboard }, async (request, reply) => {
    const { userId } = request.params as { userId: string };
    if (!isOwner(request, userId)) return forbidden(reply);
    respond(reply, await getDashboard(pool, userId));
  });

  // Phase 15 - Section 2 (B-6): 알림 조회 + SSE 스트림
  registerNotificationRoutes(app, {
    pool,
    cache,
    hub: notificationHub,
    streams: streamRegistry,
    isOwner,
    forbidden,
    respond,
    streamLifetimeMs: options.streamLifetimeMs
  });

  // 허브가 Redis 연결을 들고 있으므로 서버 종료 시 반드시 닫는다 —
  // 닫지 않으면 열린 핸들이 남아 vitest가 종료되지 않는다.
  app.addHook('onClose', async () => {
    await notificationHub.close();
    await streamRegistry.close();
  });

  // Day 10 - Task 4 (δ=1065): adminService.ts도 HTTP로 노출한다. isOwner가 아니라
  // isAdmin으로 검사한다 — 이 라우트들은 특정 사용자가 아니라 시스템 전체(무결성
  // 검사, 백업)에 대한 작업이라 "본인 소유"라는 개념 자체가 성립하지 않는다.
  app.post('/api/admin/integrity-check', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { asOfDate } = request.body as { asOfDate: string };
    respond(reply, await runIntegrityCheck(pool, asOfDate));
  });

  app.post('/api/admin/backups', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    respond(reply, await createBackup(pool, backupDir));
  });

  app.get('/api/admin/backups', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    respond(reply, await listBackups(pool, backupDir));
  });

  app.post('/api/admin/backups/:id/verify', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { id } = request.params as { id: string };
    respond(reply, await verifyBackup(pool, backupDir, id));
  });

  // Day 11 - Task 2 (δ=1080): 남아있던 4개 라우트를 노출한다.
  // 1. 대출금 상환 기록
  app.post('/api/loans/:loanId/payments', async (request, reply) => {
    const { loanId } = request.params as { loanId: string };
    const input = request.body as RecordPaymentInput;
    const loan = await new LoanRepository(pool).getLoan(loanId);
    if (!loan) {
      return reply.code(404).send({ success: false, error: { code: 'LOAN_NOT_FOUND', message: `Loan ${loanId} not found` } });
    }
    const authUser = request.user as { userId: string };
    if (loan.userId !== authUser.userId) {
      return forbidden(reply);
    }
    respond(reply, await recordLoanPayment(pool, loanId, input));
  });

  // 2. 연체 대출 감지 (관리자 전용 배치)
  app.post('/api/admin/delinquency-check', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { asOfDate } = request.body as { asOfDate: string };
    respond(reply, await detectDelinquentLoans(pool, asOfDate));
  });

  // 3. 백업 필요 여부 확인
  app.get('/api/admin/backups/due', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const query = request.query as { intervalHours?: string; now?: string };
    const intervalHours = parseInt(query.intervalHours ?? '24', 10);
    const now = query.now ?? new Date().toISOString().slice(0, 10);
    respond(reply, await checkBackupDue(pool, backupDir, intervalHours, now));
  });

  // 4. 보존기간 초과 백압 정리
  app.post('/api/admin/backups/prune', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { retentionDays, now } = request.body as { retentionDays: number; now: string };
    respond(reply, await pruneOldBackups(pool, backupDir, retentionDays, now));
  });

  // Phase 15 - B-3: 보존기간 초과 알림 정리 (읽음 처리된 것만)
  app.post('/api/admin/notifications/prune', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { retentionDays, now } = request.body as { retentionDays: number; now: string };
    respond(reply, await pruneOldNotifications(pool, retentionDays, now));
  });

  // Day 13 - Task G (δ=550): 감사 로그 조회 엔드포인트
  const auditLogger = new AuditLogger(pool);

  // 1. 모든 감사 로그 조회 (페이지네이션 지원)
  app.get('/api/admin/audit-logs', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const query = request.query as { limit?: string; offset?: string; action?: string; resourceType?: string };
    const limit = parseInt(query.limit ?? '100', 10);
    const offset = parseInt(query.offset ?? '0', 10);
    const logs = await auditLogger.query({ limit, offset, action: query.action as any, resourceType: query.resourceType });
    const count = await auditLogger.count();
    reply.send({ success: true, data: { logs, total: count, limit, offset } });
  });

  // 2. 특정 사용자의 감사 로그 조회
  app.get('/api/admin/audit-logs/user/:userId', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { userId } = request.params as { userId: string };
    const query = request.query as { limit?: string; offset?: string };
    const limit = parseInt(query.limit ?? '100', 10);
    const offset = parseInt(query.offset ?? '0', 10);
    const logs = await auditLogger.getByUser(userId, { limit, offset });
    const count = await auditLogger.count({ userId });
    reply.send({ success: true, data: { logs, total: count, limit, offset } });
  });

  // 3. 특정 리소스의 변경 이력 조회
  app.get('/api/admin/audit-logs/resource/:resourceId', async (request, reply) => {
    if (!isAdmin(request)) return forbidden(reply);
    const { resourceId } = request.params as { resourceId: string };
    const logs = await auditLogger.getResourceHistory(resourceId);
    reply.send({ success: true, data: logs });
  });

  return app;
}
