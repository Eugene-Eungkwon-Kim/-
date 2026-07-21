import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
import { AuditLogFilter, AuditLogRecord } from '../types/transaction';

interface AuditLogRow {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: string | null;
  changes: string;
  occurred_at: string;
}

function mapRow(row: AuditLogRow): AuditLogRecord {
  return {
    id: row.id,
    entityType: row.entity_type,
    entityId: row.entity_id,
    action: row.action,
    actorId: row.actor_id,
    changes: typeof row.changes === 'string' ? JSON.parse(row.changes) : row.changes,
    occurredAt: row.occurred_at
  };
}

export class AuditLogger {
  constructor(private readonly pool: Pool) {}

  async record(
    entityType: string,
    entityId: string,
    action: string,
    changes: Record<string, unknown>,
    actorId?: string,
    occurredAt?: string
  ): Promise<void> {
    if (occurredAt) {
      await this.pool.query(
        'INSERT INTO audit_log (id, entity_type, entity_id, action, actor_id, changes, occurred_at) VALUES ($1, $2, $3, $4, $5, $6, $7)',
        [randomUUID(), entityType, entityId, action, actorId ?? null, JSON.stringify(changes), occurredAt]
      );
      return;
    }

    await this.pool.query(
      'INSERT INTO audit_log (id, entity_type, entity_id, action, actor_id, changes) VALUES ($1, $2, $3, $4, $5, $6)',
      [randomUUID(), entityType, entityId, action, actorId ?? null, JSON.stringify(changes)]
    );
  }

  async query(entityType: string, filter: AuditLogFilter = {}): Promise<AuditLogRecord[]> {
    const conditions: string[] = ['entity_type = $1'];
    const params: unknown[] = [entityType];
    let paramIndex = 2;

    if (filter.entityId) {
      conditions.push(`entity_id = $${paramIndex}`);
      params.push(filter.entityId);
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
      `SELECT * FROM audit_log WHERE ${conditions.join(' AND ')} ORDER BY occurred_at ASC`,
      params
    );

    return result.rows.map(mapRow);
  }
}
