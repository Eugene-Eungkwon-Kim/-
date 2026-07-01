import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
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
    changes: JSON.parse(row.changes) as Record<string, unknown>,
    occurredAt: row.occurred_at
  };
}

/**
 * 범용 감사 로그 (Day 5 - Task 3, δ=1415)
 *
 * users_audit(Task1)/loan_history(Task2)는 각각 자기 엔티티 전용 스키마로
 * 강타입 이력을 남기지만, 이 클래스는 entity_type/entity_id 패턴으로 어떤
 * 엔티티에도 재사용 가능한 범용 감사 트레일을 제공한다 (여기서는 거래 기록에 사용).
 */
export class AuditLogger {
  constructor(private readonly db: Database.Database) {}

  /**
   * occurredAt을 생략하면 DB 기본값(datetime('now'), 로그를 남긴 실제 시각)이 쓰인다.
   * 거래처럼 "업무상 발생일"과 "로그가 남겨진 시각"이 다를 수 있는 엔티티는
   * occurredAt에 업무일자를 명시해야 날짜 필터가 의미대로 동작한다.
   */
  record(
    entityType: string,
    entityId: string,
    action: string,
    changes: Record<string, unknown>,
    actorId?: string,
    occurredAt?: string
  ): void {
    if (occurredAt) {
      this.db
        .prepare(
          'INSERT INTO audit_log (id, entity_type, entity_id, action, actor_id, changes, occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        .run(randomUUID(), entityType, entityId, action, actorId ?? null, JSON.stringify(changes), occurredAt);
      return;
    }

    this.db
      .prepare('INSERT INTO audit_log (id, entity_type, entity_id, action, actor_id, changes) VALUES (?, ?, ?, ?, ?, ?)')
      .run(randomUUID(), entityType, entityId, action, actorId ?? null, JSON.stringify(changes));
  }

  query(entityType: string, filter: AuditLogFilter = {}): AuditLogRecord[] {
    const conditions: string[] = ['entity_type = @entityType'];
    const params: Record<string, unknown> = { entityType };

    if (filter.entityId) {
      conditions.push('entity_id = @entityId');
      params.entityId = filter.entityId;
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
      .prepare(`SELECT * FROM audit_log WHERE ${conditions.join(' AND ')} ORDER BY occurred_at ASC`)
      .all(params) as AuditLogRow[];

    return rows.map(mapRow);
  }
}
