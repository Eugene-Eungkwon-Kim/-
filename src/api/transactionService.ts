import type Database from 'better-sqlite3';
import { TransactionRepository } from '../repositories/TransactionRepository';
import {
  AuditLogRecord,
  MonthlyTrendPoint,
  RecordTransactionInput,
  TransactionFilter,
  TransactionRecord,
  TransactionSummary
} from '../types/transaction';
import { ServiceResult, toServiceResult } from './errorMapping';
import { validateTransaction } from '../validation/requestValidation';

/** 거래/감사 서비스 계층 (Day 6 - Task 4, δ=1410) */
export function recordTransaction(db: Database.Database, input: RecordTransactionInput): ServiceResult<TransactionRecord> {
  return toServiceResult(() => {
    validateTransaction(input);
    return new TransactionRepository(db).recordTransaction(input);
  });
}

export function getTransactionHistory(
  db: Database.Database,
  userId: string,
  filter?: TransactionFilter
): ServiceResult<TransactionRecord[]> {
  return toServiceResult(() => new TransactionRepository(db).getTransactions(userId, filter));
}

export function getTransactionSummary(db: Database.Database, userId: string): ServiceResult<TransactionSummary> {
  return toServiceResult(() => new TransactionRepository(db).getSummary(userId));
}

export function rescanAnomalies(db: Database.Database, userId: string): ServiceResult<TransactionRecord[]> {
  return toServiceResult(() => new TransactionRepository(db).rescanForAnomalies(userId));
}

export function getTransactionAuditLog(
  db: Database.Database,
  transactionId?: string,
  options?: { from?: string; to?: string }
): ServiceResult<AuditLogRecord[]> {
  return toServiceResult(() => new TransactionRepository(db).getAuditLog(transactionId, options));
}

export function getTransactionMonthlyTrend(db: Database.Database, userId: string): ServiceResult<MonthlyTrendPoint[]> {
  return toServiceResult(() => new TransactionRepository(db).getMonthlyTrend(userId));
}
