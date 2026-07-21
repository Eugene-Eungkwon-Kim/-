/**
 * Day 13 - Task G (δ=550): 감사 로깅 시스템
 *
 * 모든 주요 CRUD 작업에 대해 감사 로그를 기록한다.
 * 변경 이전/이후 상태, 작업자, 타임스탐프, 오류 정보를 추적한다.
 */

import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';

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
  constructor(private readonly pool: Pool) {}

  /**
   * 감사 로그를 기록한다.
   */
  async log(entry: Omit<AuditLogEntry, 'id' | 'createdAt'>): Promise<string> {
    const id = randomUUID();
    const createdAt = new Date().toISOString();

    await this.pool.query(
      `INSERT INTO audit_logs (
        id, user_id, action, resource_type, resource_id,
        changes_before, changes_after, metadata_ip,
        status, error_message, created_at
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
      )`,
      [
        id,
        entry.userId,
        entry.action,
        entry.resourceType,
        entry.resourceId,
        entry.changesBefore ? JSON.stringify(entry.changesBefore) : null,
        entry.changesAfter ? JSON.stringify(entry.changesAfter) : null,
        entry.metadataIp || null,
        entry.status,
        entry.errorMessage || null,
        createdAt
      ]
    );

    return id;
  }

  /**
   * 감사 로그를 필터링하여 조회한다.
   */
  async query(options: AuditFilterOptions): Promise<AuditLogEntry[]> {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let paramIndex = 1;

    if (options.userId) {
      conditions.push(`user_id = $${paramIndex}`);
      params.push(options.userId);
      paramIndex++;
    }

    if (options.action) {
      conditions.push(`action = $${paramIndex}`);
      params.push(options.action);
      paramIndex++;
    }

    if (options.resourceType) {
      conditions.push(`resource_type = $${paramIndex}`);
      params.push(options.resourceType);
      paramIndex++;
    }

    if (options.resourceId) {
      conditions.push(`resource_id = $${paramIndex}`);
      params.push(options.resourceId);
      paramIndex++;
    }

    if (options.fromDate) {
      conditions.push(`created_at >= $${paramIndex}`);
      params.push(options.fromDate);
      paramIndex++;
    }

    if (options.toDate) {
      conditions.push(`created_at <= $${paramIndex}`);
      params.push(options.toDate);
      paramIndex++;
    }

    let sql = `SELECT * FROM audit_logs WHERE ${conditions.length > 0 ? conditions.join(' AND ') : '1=1'} ORDER BY created_at DESC`;

    if (options.limit) {
      sql += ` LIMIT $${paramIndex}`;
      params.push(options.limit);
      paramIndex++;
    }

    if (options.offset) {
      sql += ` OFFSET $${paramIndex}`;
      params.push(options.offset);
    }

    const result = await this.pool.query(sql, params);
    const rows = result.rows as {
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
  async getByUser(userId: string, options?: { limit?: number; offset?: number }): Promise<AuditLogEntry[]> {
    return this.query({
      userId,
      limit: options?.limit || 100,
      offset: options?.offset || 0
    });
  }

  /**
   * 특정 리소스의 모든 변경 이력을 조회한다.
   */
  async getResourceHistory(resourceId: string): Promise<AuditLogEntry[]> {
    return this.query({
      resourceId,
      limit: 1000
    });
  }

  /**
   * 특정 액션의 모든 로그를 조회한다.
   */
  async getByAction(action: AuditAction, options?: { limit?: number; offset?: number }): Promise<AuditLogEntry[]> {
    return this.query({
      action,
      limit: options?.limit || 100,
      offset: options?.offset || 0
    });
  }

  /**
   * 감사 로그 개수를 조회한다.
   */
  async count(options?: Omit<AuditFilterOptions, 'limit' | 'offset'>): Promise<number> {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let paramIndex = 1;

    if (options?.userId) {
      conditions.push(`user_id = $${paramIndex}`);
      params.push(options.userId);
      paramIndex++;
    }

    if (options?.action) {
      conditions.push(`action = $${paramIndex}`);
      params.push(options.action);
      paramIndex++;
    }

    if (options?.resourceType) {
      conditions.push(`resource_type = $${paramIndex}`);
      params.push(options.resourceType);
    }

    const sql = `SELECT COUNT(*) as count FROM audit_logs WHERE ${conditions.length > 0 ? conditions.join(' AND ') : '1=1'}`;
    const result = await this.pool.query(sql, params);
    return parseInt((result.rows[0] as { count: string }).count, 10);
  }
}
