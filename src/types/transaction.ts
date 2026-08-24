/**
 * 거래 기록 & 감시 로깅 관련 타입 정의
 * Day 5 - Task 3: Transaction History & Audit Logging (δ=1415)
 */

export type TransactionType = 'deposit' | 'withdrawal' | 'loan_payment' | 'fee' | 'adjustment';
export type TransactionStatus = 'completed' | 'flagged' | 'reversed';

export interface TransactionRecord {
  id: string;
  userId: string;
  transactionType: TransactionType;
  amount: number;
  description: string | null;
  status: TransactionStatus;
  occurredAt: string; // YYYY-MM-DD
  createdAt: string;
}

export interface RecordTransactionInput {
  userId: string;
  transactionType: TransactionType;
  amount: number;
  description?: string;
  occurredAt: string; // YYYY-MM-DD
}

export interface TransactionFilter {
  status?: TransactionStatus;
  from?: string; // YYYY-MM-DD, inclusive
  to?: string; // YYYY-MM-DD, inclusive
}

export interface TransactionSummary {
  userId: string;
  transactionCount: number;
  totalDeposits: number;
  totalWithdrawals: number;
  flaggedCount: number;
  lastTransactionAt: string | null;
}

export interface MonthlyTrendPoint {
  month: string; // YYYY-MM
  totalAmount: number;
  transactionCount: number;
}

export interface AuditLogRecord {
  id: string;
  entityType: string;
  entityId: string;
  action: string;
  actorId: string | null;
  changes: Record<string, unknown>;
  occurredAt: string;
}

export interface AuditLogFilter {
  entityId?: string;
  from?: string;
  to?: string;
}
