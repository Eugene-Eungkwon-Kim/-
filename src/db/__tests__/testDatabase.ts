import { Pool, PoolClient } from 'pg';
import { applyMigrations } from '../migrationRunner';
import { MIGRATIONS_DIR } from '../connection';

/**
 * 테스트용 PostgreSQL 환경 설정
 * 각 테스트 케이스는 고립된 DB 커넥션을 받음
 */

let testPool: Pool | null = null;
let testDbName = '';

/**
 * 테스트용 PostgreSQL 커넥션 풀 생성
 * 환경변수가 없으면 localhost:5432의 기본값 사용
 */
export function createTestPool(): Pool {
  const pool = new Pool({
    host: process.env.PG_HOST || 'localhost',
    port: parseInt(process.env.PG_PORT || '5432'),
    database: process.env.PG_TEST_DATABASE || 'maars_test',
    user: process.env.PG_USER || 'postgres',
    password: process.env.PG_PASSWORD || '',
    max: 5,
  });
  return pool;
}

/**
 * 테스트 데이터베이스 초기화
 * - 커넥션 풀 생성
 * - 마이그레이션 실행
 * - 글로벌 풀 등록
 */
export async function initializeTestDatabase(): Promise<Pool> {
  testPool = createTestPool();

  const client = await testPool.connect();
  try {
    // 마이그레이션 실행
    await applyMigrations(client as any, MIGRATIONS_DIR);
  } finally {
    client.release();
  }

  return testPool;
}

/**
 * 테스트 후 데이터베이스 정리
 * 모든 테이블 데이터 삭제 (스키마는 유지)
 */
export async function cleanupTestDatabase(): Promise<void> {
  if (!testPool) return;

  const client = await testPool.connect();
  try {
    // 외래키 제약 비활성화
    await client.query('SET session_replication_role = REPLICA');

    // 모든 사용자 테이블 TRUNCATE (마이그레이션 테이블 제외)
    const tables = [
      'audit_logs',
      'credit_history',
      'transaction_anomalies',
      'transactions',
      'data_integrity_log',
      'financial_snapshots',
      'refresh_tokens',
      'loan_payments',
      'loans',
      'backup_records',
      'users',
    ];

    for (const table of tables) {
      await client.query(`TRUNCATE TABLE ${table} CASCADE`);
    }

    // 외래키 제약 재활성화
    await client.query('SET session_replication_role = DEFAULT');
  } finally {
    client.release();
  }
}

/**
 * 테스트 데이터베이스 완전 해제
 * 커넥션 풀 종료
 */
export async function closeTestDatabase(): Promise<void> {
  if (testPool) {
    await testPool.end();
    testPool = null;
  }
}

/**
 * 테스트용 트랜잭션 래퍼
 * 각 테스트는 독립적인 트랜잭션에서 실행되고 자동 롤백
 */
export async function withTestTransaction<T>(
  callback: (client: PoolClient) => Promise<T>
): Promise<T> {
  if (!testPool) {
    throw new Error('Test database not initialized. Call initializeTestDatabase first.');
  }

  const client = await testPool.connect();
  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('ROLLBACK');
    return result;
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
  }
}

/**
 * 테스트용 일반 쿼리 실행 (자동 정리 없음)
 */
export function getTestPool(): Pool {
  if (!testPool) {
    throw new Error('Test database not initialized. Call initializeTestDatabase first.');
  }
  return testPool;
}
