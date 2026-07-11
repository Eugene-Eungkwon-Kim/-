/**
 * Day 13 - Task G (δ=550): 감사 로깅 시스템
 *
 * 모든 주요 CRUD 작업에 대해 감사 로그를 기록한다.
 * 변경 이전/이후 상태, 작업자, 타임스탐프, 오류 정보를 추적한다.
 */

import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';

export enum AuditAction {
  CREATE = 'CREATE',
  READ = 'READ',
  UPDATE = 'UPDATE',
  DELETE = 'DELETE',
  PAYMENT = 'PAYMENT',
  LOAN_APPROVAL = 'LOAN_APPROVAL',
  LOGIN = 'LOGIN',
  LOGOUT = 'LOGOUT'
}

export interface AuditLogEntry {
  id: string;
  userId: string;
  action: AuditAction;
  resourceType: string;
  resourceId: string;
  changesBefore: Record<string, unknown> | null;
  changesAfter: Record<string, unknown> | null;
  metadataIp: string | null;
  status: 'success' | 'failure';
  errorMessage: string | null;
  createdAt: string;
}

export interface AuditFilterOptions {
  userId?: string;
  action?: AuditAction;
  resourceType?: string;
  resourceId?: string;
  fromDate?: string;
  toDate?: string;
  limit?: number;
  offset?: number;
}

export class AuditLogger {
  constructor(private readonly db: Database.Database) {}

  /**
   * 감사 로그를 기록한다.
   */
  log(entry: Omit<AuditLogEntry, 'id' | 'createdAt'>): string {
    const id = randomUUID();
    const createdAt = new Date().toISOString();

    this.db
      .prepare(
        `
        INSERT INTO audit_logs (
          id, user_id, action, resource_type, resource_id,
          changes_before, changes_after, metadata_ip,
          status, error_message, created_at
        ) VALUES (
          @id, @userId, @action, @resourceType, @resourceId,
          @changesBefore, @changesAfter, @metadataIp,
          @status, @errorMessage, @createdAt
        )
      `
      )
      .run({
        id,
        userId: entry.userId,
        action: entry.action,
        resourceType: entry.resourceType,
        resourceId: entry.resourceId,
        changesBefore: entry.changesBefore ? JSON.stringify(entry.changesBefore) : null,
        changesAfter: entry.changesAfter ? JSON.stringify(entry.changesAfter) : null,
        metadataIp: entry.metadataIp || null,
        status: entry.status,
        errorMessage: entry.errorMessage || null,
        createdAt
      });

    return id;
  }

  /**
   * 감사 로그를 필터링하여 조회한다.
   */
  query(options: AuditFilterOptions): AuditLogEntry[] {
    let sql = 'SELECT * FROM audit_logs WHERE 1=1';
    const params: Record<string, unknown> = {};

    if (options.userId) {
      sql += ' AND user_id = @userId';
      params.userId = options.userId;
    }

    if (options.action) {
      sql += ' AND action = @action';
      params.action = options.action;
    }

    if (options.resourceType) {
      sql += ' AND resource_type = @resourceType';
      params.resourceType = options.resourceType;
    }

    if (options.resourceId) {
      sql += ' AND resource_id = @resourceId';
      params.resourceId = options.resourceId;
    }

    if (options.fromDate) {
      sql += ' AND created_at >= @fromDate';
      params.fromDate = options.fromDate;
    }

    if (options.toDate) {
      sql += ' AND created_at <= @toDate';
      params.toDate = options.toDate;
    }

    sql += ' ORDER BY created_at DESC';

    if (options.limit) {
      sql += ' LIMIT @limit';
      params.limit = options.limit;
    }

    if (options.offset) {
      sql += ' OFFSET @offset';
      params.offset = options.offset;
    }

    const rows = this.db.prepare(sql).all(params) as {
      id: string;
      user_id: string;
      action: string;
      resource_type: string;
      resource_id: string;
      changes_before: string | null;
      changes_after: string | null;
      metadata_ip: string | null;
      status: string;
      error_message: string | null;
      created_at: string;
    }[];

    return rows.map((row) => ({
      id: row.id,
      userId: row.user_id,
      action: row.action as AuditAction,
      resourceType: row.resource_type,
      resourceId: row.resource_id,
      changesBefore: row.changes_before ? JSON.parse(row.changes_before) : null,
      changesAfter: row.changes_after ? JSON.parse(row.changes_after) : null,
      metadataIp: row.metadata_ip,
      status: row.status as 'success' | 'failure',
      errorMessage: row.error_message,
      createdAt: row.created_at
    }));
  }

  /**
   * 특정 사용자의 모든 감사 로그를 조회한다.
   */
  getByUser(userId: string, options?: { limit?: number; offset?: number }): AuditLogEntry[] {
    return this.query({
      userId,
      limit: options?.limit || 100,
      offset: options?.offset || 0
    });
  }

  /**
   * 특정 리소스의 모든 변경 이력을 조회한다.
   */
  getResourceHistory(resourceId: string): AuditLogEntry[] {
    return this.query({
      resourceId,
      limit: 1000
    });
  }

  /**
   * 특정 액션의 모든 로그를 조회한다.
   */
  getByAction(action: AuditAction, options?: { limit?: number; offset?: number }): AuditLogEntry[] {
    return this.query({
      action,
      limit: options?.limit || 100,
      offset: options?.offset || 0
    });
  }

  /**
   * 감사 로그 개수를 조회한다.
   */
  count(options?: Omit<AuditFilterOptions, 'limit' | 'offset'>): number {
    let sql = 'SELECT COUNT(*) as count FROM audit_logs WHERE 1=1';
    const params: Record<string, unknown> = {};

    if (options?.userId) {
      sql += ' AND user_id = @userId';
      params.userId = options.userId;
    }

    if (options?.action) {
      sql += ' AND action = @action';
      params.action = options.action;
    }

    if (options?.resourceType) {
      sql += ' AND resource_type = @resourceType';
      params.resourceType = options.resourceType;
    }

    const result = this.db.prepare(sql).get(params) as { count: number };
    return result.count;
  }
}
