import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
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

/**
 * 거래 기록 & 감시 로깅 (Day 5 - Task 3, δ=1415)
 *
 * 사용자 소득 대비 과도한 거래는 기록 시점에 즉시 플래깅한다. 다만 소득은
 * 거래 이후에도 바뀔 수 있으므로(UserRepository.updateProfile), rescanForAnomalies로
 * 기존 'completed' 거래를 현재 소득 기준으로 재평가할 수 있게 한다
 * (IntegrityChecker의 "쓰기 시점 검증만으론 부족하다"는 설계와 동일한 원칙).
 */
export class TransactionRepository {
  private readonly auditLogger: AuditLogger;

  constructor(private readonly db: Database.Database) {
    this.auditLogger = new AuditLogger(db);
  }

  recordTransaction(input: RecordTransactionInput): TransactionRecord {
    if (input.amount <= 0) throw new ValidationError('amount must be greater than 0');

    const user = this.db.prepare('SELECT id, income FROM users WHERE id = ?').get(input.userId) as
      | { id: string; income: number | null }
      | undefined;
    if (!user) throw new UserNotFoundError(input.userId);

    const isAnomalous = user.income !== null && input.amount > user.income * ANOMALY_INCOME_RATIO;
    const status = isAnomalous ? 'flagged' : 'completed';
    const id = randomUUID();

    this.db
      .prepare(
        'INSERT INTO transactions (id, user_id, transaction_type, amount, description, status, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
      )
      .run(id, input.userId, input.transactionType, input.amount, input.description ?? null, status, input.occurredAt);

    this.auditLogger.record(
      'transaction',
      id,
      'CREATE',
      { transactionType: input.transactionType, amount: input.amount, status },
      input.userId,
      input.occurredAt
    );

    return this.getTransactionOrThrow(id);
  }

  getTransaction(transactionId: string): TransactionRecord | null {
    const row = this.db.prepare('SELECT * FROM transactions WHERE id = ?').get(transactionId) as
      | TransactionRow
      | undefined;
    return row ? mapRow(row) : null;
  }

  getTransactions(userId: string, filter: TransactionFilter = {}): TransactionRecord[] {
    const conditions: string[] = ['user_id = @userId'];
    const params: Record<string, unknown> = { userId };

    if (filter.status) {
      conditions.push('status = @status');
      params.status = filter.status;
    }
    if (filter.from) {
      conditions.push('date(occurred_at) >= date(@from)');
      params.from = filter.from;
    }
    if (filter.to) {
      conditions.push('date(occurred_at) <= date(@to)');
      params.to = filter.to;
    }

    const rows = this.db
      .prepare(`SELECT * FROM transactions WHERE ${conditions.join(' AND ')} ORDER BY occurred_at ASC`)
      .all(params) as TransactionRow[];

    return rows.map(mapRow);
  }

  /** 소득 변경 이후에도 과거 'completed' 거래를 현재 기준으로 재평가해 드리프트를 감지한다 */
  rescanForAnomalies(userId: string): TransactionRecord[] {
    const user = this.db.prepare('SELECT income FROM users WHERE id = ?').get(userId) as
      | { income: number | null }
      | undefined;
    if (!user || user.income === null) return [];

    const threshold = user.income * ANOMALY_INCOME_RATIO;
    const candidates = this.db
      .prepare("SELECT * FROM transactions WHERE user_id = ? AND status = 'completed' AND amount > ?")
      .all(userId, threshold) as TransactionRow[];

    for (const row of candidates) {
      this.db.prepare("UPDATE transactions SET status = 'flagged' WHERE id = ?").run(row.id);
      this.auditLogger.record(
        'transaction',
        row.id,
        'FLAGGED',
        { reason: 'income_threshold_rescan', threshold },
        userId
      );
    }

    return candidates.map((row) => this.getTransactionOrThrow(row.id));
  }

  getAuditLog(transactionId?: string, options: { from?: string; to?: string } = {}): AuditLogRecord[] {
    return this.auditLogger.query('transaction', { entityId: transactionId, ...options });
  }

  getSummary(userId: string): TransactionSummary {
    const rows = this.getTransactions(userId);
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

  getMonthlyTrend(userId: string): MonthlyTrendPoint[] {
    const rows = this.db
      .prepare(
        `
        SELECT substr(occurred_at, 1, 7) as month, SUM(amount) as total_amount, COUNT(*) as transaction_count
        FROM transactions
        WHERE user_id = ?
        GROUP BY month
        ORDER BY month ASC
      `
      )
      .all(userId) as { month: string; total_amount: number; transaction_count: number }[];

    return rows.map((row) => ({
      month: row.month,
      totalAmount: row.total_amount,
      transactionCount: row.transaction_count
    }));
  }

  private getTransactionOrThrow(transactionId: string): TransactionRecord {
    const record = this.getTransaction(transactionId);
    if (!record) throw new TransactionNotFoundError(transactionId);
    return record;
  }
}
