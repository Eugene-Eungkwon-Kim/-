import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
import {
  AuditLogRecord,
  MonthlyTrendPoint,
  RecordTransactionInput,
  TransactionFilter,
  TransactionRecord,
  TransactionSummary
} from '../types/transaction';
import { UserNotFoundError, ValidationError } from './errors';
import { AuditLogger } from './AuditLogger';
import type { CacheStore } from '../cache/cacheStore';
import { createCacheStore } from '../cache/cacheFactory';

interface TransactionRow {
  id: string;
  user_id: string;
  transaction_type: string;
  amount: number;
  description: string | null;
  status: string;
  occurred_at: string;
  created_at: string;
}

const ANOMALY_INCOME_RATIO = 0.5;

export class TransactionNotFoundError extends Error {
  constructor(transactionId: string) {
    super(`Transaction not found: ${transactionId}`);
    this.name = 'TransactionNotFoundError';
  }
}

function mapRow(row: TransactionRow): TransactionRecord {
  return {
    id: row.id,
    userId: row.user_id,
    transactionType: row.transaction_type as TransactionRecord['transactionType'],
    amount: row.amount,
    description: row.description,
    status: row.status as TransactionRecord['status'],
    occurredAt: row.occurred_at,
    createdAt: row.created_at
  };
}

export class TransactionRepository {
  private readonly auditLogger: AuditLogger;
  private readonly cache: CacheStore;

  constructor(private readonly pool: Pool) {
    this.auditLogger = new AuditLogger(pool);
    this.cache = createCacheStore(pool);
  }

  private invalidateUserAggregates(userId: string): void {
    this.cache.deleteByPrefix(`txn:${userId}:`);
  }

  async recordTransaction(input: RecordTransactionInput): Promise<TransactionRecord> {
    if (input.amount <= 0) throw new ValidationError('amount must be greater than 0');

    const userResult = await this.pool.query('SELECT id, income FROM users WHERE id = $1', [input.userId]);
    const user = userResult.rows[0] as { id: string; income: number | null } | undefined;
    if (!user) throw new UserNotFoundError(input.userId);

    const isAnomalous = user.income !== null && input.amount > user.income * ANOMALY_INCOME_RATIO;
    const status = isAnomalous ? 'flagged' : 'completed';
    const id = randomUUID();

    await this.pool.query(
      'INSERT INTO transactions (id, user_id, transaction_type, amount, description, status, occurred_at) VALUES ($1, $2, $3, $4, $5, $6, $7)',
      [id, input.userId, input.transactionType, input.amount, input.description ?? null, status, input.occurredAt]
    );

    await this.auditLogger.record(
      'transaction',
      id,
      'CREATE',
      { transactionType: input.transactionType, amount: input.amount, status },
      input.userId,
      input.occurredAt
    );

    this.invalidateUserAggregates(input.userId);

    return this.getTransactionOrThrow(id);
  }

  async getTransaction(transactionId: string): Promise<TransactionRecord | null> {
    const result = await this.pool.query('SELECT * FROM transactions WHERE id = $1', [transactionId]);
    const row = result.rows[0] as TransactionRow | undefined;
    return row ? mapRow(row) : null;
  }

  async getTransactions(userId: string, filter: TransactionFilter = {}): Promise<TransactionRecord[]> {
    const conditions: string[] = ['user_id = $1'];
    const params: unknown[] = [userId];
    let paramIndex = 2;

    if (filter.status) {
      conditions.push(`status = $${paramIndex}`);
      params.push(filter.status);
      paramIndex++;
    }
    if (filter.from) {
      conditions.push(`date(occurred_at) >= date($${paramIndex})`);
      params.push(filter.from);
      paramIndex++;
    }
    if (filter.to) {
      conditions.push(`date(occurred_at) <= date($${paramIndex})`);
      params.push(filter.to);
      paramIndex++;
    }

    const result = await this.pool.query(
      `SELECT * FROM transactions WHERE ${conditions.join(' AND ')} ORDER BY occurred_at ASC`,
      params
    );

    return (result.rows as TransactionRow[]).map(mapRow);
  }

  async rescanForAnomalies(userId: string): Promise<TransactionRecord[]> {
    const userResult = await this.pool.query('SELECT income FROM users WHERE id = $1', [userId]);
    const user = userResult.rows[0] as { income: number | null } | undefined;
    if (!user || user.income === null) return [];

    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      const threshold = user.income * ANOMALY_INCOME_RATIO;
      const candidatesResult = await client.query(
        "SELECT * FROM transactions WHERE user_id = $1 AND status = 'completed' AND amount > $2",
        [userId, threshold]
      );
      const candidates = candidatesResult.rows as TransactionRow[];

      for (const row of candidates) {
        await client.query("UPDATE transactions SET status = 'flagged' WHERE id = $1", [row.id]);
        await this.auditLogger.record(
          'transaction',
          row.id,
          'FLAGGED',
          { reason: 'income_threshold_rescan', threshold },
          userId
        );
      }

      await client.query('COMMIT');

      if (candidates.length > 0) this.invalidateUserAggregates(userId);

      return Promise.all(candidates.map((row) => this.getTransactionOrThrow(row.id)));
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getAuditLog(transactionId?: string, options: { from?: string; to?: string } = {}): Promise<AuditLogRecord[]> {
    return this.auditLogger.query('transaction', { entityId: transactionId, ...options });
  }

  private async computeSummary(userId: string): Promise<TransactionSummary> {
    const rows = await this.getTransactions(userId);
    const totalDeposits = rows.filter((r) => r.transactionType === 'deposit').reduce((sum, r) => sum + r.amount, 0);
    const totalWithdrawals = rows
      .filter((r) => r.transactionType === 'withdrawal')
      .reduce((sum, r) => sum + r.amount, 0);

    return {
      userId,
      transactionCount: rows.length,
      totalDeposits,
      totalWithdrawals,
      flaggedCount: rows.filter((r) => r.status === 'flagged').length,
      lastTransactionAt: rows.length > 0 ? rows[rows.length - 1].occurredAt : null
    };
  }

  async getSummary(userId: string): Promise<TransactionSummary> {
    try {
      return await this.cache.getOrCompute(`txn:${userId}:summary`, () => this.computeSummary(userId));
    } catch (cacheError) {
      // If cache layer fails (e.g., Redis connection error), fall back to direct computation
      return this.computeSummary(userId);
    }
  }

  private async computeMonthlyTrend(userId: string): Promise<MonthlyTrendPoint[]> {
    const result = await this.pool.query(
      `SELECT to_char(occurred_at::timestamp, 'YYYY-MM') as month,
              CAST(SUM(amount) AS INTEGER) as total_amount,
              CAST(COUNT(*) AS INTEGER) as transaction_count
       FROM transactions
       WHERE user_id = $1
       GROUP BY to_char(occurred_at::timestamp, 'YYYY-MM')
       ORDER BY month ASC`,
      [userId]
    );

    return result.rows.map((row) => ({
      month: row.month,
      totalAmount: Number(row.total_amount),
      transactionCount: Number(row.transaction_count)
    }));
  }

  async getMonthlyTrend(userId: string): Promise<MonthlyTrendPoint[]> {
    try {
      return await this.cache.getOrCompute(`txn:${userId}:trend`, () => this.computeMonthlyTrend(userId));
    } catch (cacheError) {
      // If cache layer fails (e.g., Redis connection error), fall back to direct computation
      return this.computeMonthlyTrend(userId);
    }
  }

  private async getTransactionOrThrow(transactionId: string): Promise<TransactionRecord> {
    const record = await this.getTransaction(transactionId);
    if (!record) throw new TransactionNotFoundError(transactionId);
    return record;
  }
}
