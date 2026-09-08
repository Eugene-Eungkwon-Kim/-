import type { Pool } from 'pg';
import { TransactionRepository } from '../repositories/TransactionRepository';
import {
  AuditLogRecord,
  MonthlyTrendPoint,
  RecordTransactionInput,
  TransactionFilter,
  TransactionRecord,
  TransactionSummary
} from '../types/transaction';
import { ServiceResult, toServiceResultAsync } from './errorMapping';
import { validateTransaction } from '../validation/requestValidation';

export async function recordTransaction(pool: Pool, input: RecordTransactionInput): Promise<ServiceResult<TransactionRecord>> {
  return toServiceResultAsync(async () => {
    validateTransaction(input);
    return new TransactionRepository(pool).recordTransaction(input);
  });
}

export async function getTransactionHistory(
  pool: Pool,
  userId: string,
  filter?: TransactionFilter
): Promise<ServiceResult<TransactionRecord[]>> {
  return toServiceResultAsync(async () => new TransactionRepository(pool).getTransactions(userId, filter));
}

export async function getTransactionSummary(pool: Pool, userId: string): Promise<ServiceResult<TransactionSummary>> {
  return toServiceResultAsync(async () => new TransactionRepository(pool).getSummary(userId));
}

export async function rescanAnomalies(pool: Pool, userId: string): Promise<ServiceResult<TransactionRecord[]>> {
  return toServiceResultAsync(async () => new TransactionRepository(pool).rescanForAnomalies(userId));
}

export async function getTransactionAuditLog(
  pool: Pool,
  transactionId?: string,
  options?: { from?: string; to?: string }
): Promise<ServiceResult<AuditLogRecord[]>> {
  return toServiceResultAsync(async () => new TransactionRepository(pool).getAuditLog(transactionId, options));
}

export async function getTransactionMonthlyTrend(pool: Pool, userId: string): Promise<ServiceResult<MonthlyTrendPoint[]>> {
  return toServiceResultAsync(async () => new TransactionRepository(pool).getMonthlyTrend(userId));
}
