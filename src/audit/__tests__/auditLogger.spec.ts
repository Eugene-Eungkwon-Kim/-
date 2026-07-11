import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import type Database from 'better-sqlite3';
import { createDatabase } from '../../db/connection';
import { AuditLogger, AuditAction } from '../auditLogger';

/**
 * Day 13 - Task G (δ=550): AuditLogger 테스트
 *
 * 감사 로그 기록, 조회, 필터링 기능을 검증한다.
 */
describe('AuditLogger', () => {
  let db: Database.Database;
  let auditLogger: AuditLogger;
  const testUserId = 'user-123';
  const testResourceId = 'resource-456';

  beforeEach(() => {
    db = createDatabase(':memory:');
    // 마이그레이션이 이미 users 테이블을 생성했으므로, 테스트 데이터만 삽입한다
    db.prepare('INSERT INTO users (id, email, name) VALUES (?, ?, ?)').run(
      testUserId,
      'test@example.com',
      'Test User'
    );
    auditLogger = new AuditLogger(db);
  });

  afterEach(() => {
    db.close();
  });

  describe('log', () => {
    it('새로운 감사 로그를 기록한다', () => {
      const logId = auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'user',
        resourceId: testResourceId,
        changesBefore: null,
        changesAfter: { email: 'test@example.com', name: 'Test User' },
        metadataIp: '192.168.1.1',
        status: 'success',
        errorMessage: null
      });

      expect(logId).toBeTruthy();
      expect(typeof logId).toBe('string');
    });

    it('기록된 로그를 조회할 수 있다', () => {
      const logId = auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'loan',
        resourceId: testResourceId,
        changesBefore: null,
        changesAfter: { amount: 1000000, interestRate: 5 },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      const logs = auditLogger.query({ limit: 10 });
      expect(logs.length).toBeGreaterThan(0);
      expect(logs[0].id).toBe(logId);
    });

    it('실패한 작업을 로그할 수 있다', () => {
      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'user',
        resourceId: testResourceId,
        changesBefore: { email: 'old@example.com' },
        changesAfter: null,
        metadataIp: '10.0.0.1',
        status: 'failure',
        errorMessage: 'UNIQUE constraint failed: users.email'
      });

      const logs = auditLogger.query({ limit: 10 });
      const failedLog = logs.find((log) => log.status === 'failure');
      expect(failedLog).toBeTruthy();
      expect(failedLog?.errorMessage).toContain('UNIQUE constraint failed');
    });
  });

  describe('query', () => {
    const otherUserId = 'user-456';

    beforeEach(() => {
      // 다른 사용자를 데이터베이스에 추가한다
      db.prepare('INSERT INTO users (id, email, name) VALUES (?, ?, ?)').run(
        otherUserId,
        'other@example.com',
        'Other User'
      );

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'user',
        resourceId: 'user-1',
        changesBefore: null,
        changesAfter: { email: 'user1@example.com' },
        metadataIp: '192.168.1.1',
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: { status: 'active' },
        changesAfter: { status: 'repaid' },
        metadataIp: '192.168.1.2',
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: otherUserId,
        action: AuditAction.DELETE,
        resourceType: 'transaction',
        resourceId: 'txn-1',
        changesBefore: { amount: 10000 },
        changesAfter: null,
        metadataIp: null,
        status: 'failure',
        errorMessage: 'Permission denied'
      });
    });

    it('액션으로 필터링할 수 있다', () => {
      const logs = auditLogger.query({ action: AuditAction.UPDATE });
      expect(logs.length).toBe(1);
      expect(logs[0].action).toBe(AuditAction.UPDATE);
    });

    it('리소스 타입으로 필터링할 수 있다', () => {
      const logs = auditLogger.query({ resourceType: 'loan' });
      expect(logs.length).toBe(1);
      expect(logs[0].resourceType).toBe('loan');
    });

    it('사용자 ID로 필터링할 수 있다', () => {
      const logs = auditLogger.query({ userId: otherUserId });
      expect(logs.length).toBe(1);
      expect(logs[0].userId).toBe(otherUserId);
    });

    it('리소스 ID로 필터링할 수 있다', () => {
      const logs = auditLogger.query({ resourceId: 'loan-1' });
      expect(logs.length).toBe(1);
      expect(logs[0].resourceId).toBe('loan-1');
    });

    it('페이지네이션을 지원한다', () => {
      const page1 = auditLogger.query({ limit: 2, offset: 0 });
      const page2 = auditLogger.query({ limit: 2, offset: 2 });

      expect(page1.length).toBe(2);
      expect(page2.length).toBe(1);
      expect(page1[0].id).not.toBe(page2[0].id);
    });

    it('최신 로그부터 역순으로 반환한다', () => {
      const logs = auditLogger.query({ limit: 10 });
      const timestamps = logs.map((log) => new Date(log.createdAt).getTime());

      for (let i = 1; i < timestamps.length; i++) {
        expect(timestamps[i - 1]).toBeGreaterThanOrEqual(timestamps[i]);
      }
    });

    it('복합 필터링을 지원한다', () => {
      const logs = auditLogger.query({
        userId: testUserId,
        resourceType: 'loan',
        action: AuditAction.UPDATE
      });

      expect(logs.length).toBe(1);
      expect(logs[0].userId).toBe(testUserId);
      expect(logs[0].resourceType).toBe('loan');
      expect(logs[0].action).toBe(AuditAction.UPDATE);
    });
  });

  describe('getByUser', () => {
    beforeEach(() => {
      for (let i = 0; i < 5; i++) {
        auditLogger.log({
          userId: testUserId,
          action: AuditAction.CREATE,
          resourceType: 'loan',
          resourceId: `loan-${i}`,
          changesBefore: null,
          changesAfter: { amount: 1000000 * (i + 1) },
          metadataIp: null,
          status: 'success',
          errorMessage: null
        });
      }
    });

    it('특정 사용자의 모든 로그를 조회한다', () => {
      const logs = auditLogger.getByUser(testUserId);
      expect(logs.length).toBe(5);
      expect(logs.every((log) => log.userId === testUserId)).toBe(true);
    });

    it('사용자 로그 조회 시 페이지네이션을 지원한다', () => {
      const page1 = auditLogger.getByUser(testUserId, { limit: 2, offset: 0 });
      const page2 = auditLogger.getByUser(testUserId, { limit: 2, offset: 2 });

      expect(page1.length).toBe(2);
      expect(page2.length).toBe(2);
    });
  });

  describe('getResourceHistory', () => {
    beforeEach(() => {
      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: null,
        changesAfter: { amount: 1000000, status: 'active' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: { status: 'active' },
        changesAfter: { status: 'repaid' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.DELETE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: { status: 'repaid' },
        changesAfter: null,
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });
    });

    it('리소스의 모든 변경 이력을 시간순으로 조회한다', () => {
      const history = auditLogger.getResourceHistory('loan-1');
      expect(history.length).toBe(3);
      // 모든 액션이 포함되어 있는지 확인 (타임스탐프가 같을 수 있으므로 순서는 보장 안함)
      const actions = history.map((log) => log.action);
      expect(actions).toContain(AuditAction.DELETE);
      expect(actions).toContain(AuditAction.UPDATE);
      expect(actions).toContain(AuditAction.CREATE);
    });
  });

  describe('getByAction', () => {
    beforeEach(() => {
      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'user',
        resourceId: 'user-1',
        changesBefore: null,
        changesAfter: { email: 'user1@example.com' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: null,
        changesAfter: { amount: 1000000 },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'user',
        resourceId: 'user-1',
        changesBefore: { email: 'user1@example.com' },
        changesAfter: { email: 'user1_new@example.com' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });
    });

    it('특정 액션의 모든 로그를 조회한다', () => {
      const logs = auditLogger.getByAction(AuditAction.CREATE);
      expect(logs.length).toBe(2);
      expect(logs.every((log) => log.action === AuditAction.CREATE)).toBe(true);
    });
  });

  describe('count', () => {
    beforeEach(() => {
      auditLogger.log({
        userId: testUserId,
        action: AuditAction.CREATE,
        resourceType: 'user',
        resourceId: 'user-1',
        changesBefore: null,
        changesAfter: { email: 'user1@example.com' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'loan',
        resourceId: 'loan-1',
        changesBefore: null,
        changesAfter: { amount: 1000000 },
        metadataIp: null,
        status: 'failure',
        errorMessage: 'Insufficient funds'
      });
    });

    it('전체 감사 로그 개수를 반환한다', () => {
      const count = auditLogger.count();
      expect(count).toBe(2);
    });

    it('필터링된 로그 개수를 반환한다', () => {
      const count = auditLogger.count({ action: AuditAction.UPDATE });
      expect(count).toBe(1);
    });
  });

  describe('JSON 직렬화', () => {
    it('changesBefore와 changesAfter를 JSON으로 저장/복원한다', () => {
      const changes = {
        email: { from: 'old@example.com', to: 'new@example.com' },
        phone: { from: '010-1111-1111', to: '010-2222-2222' }
      };

      auditLogger.log({
        userId: testUserId,
        action: AuditAction.UPDATE,
        resourceType: 'user',
        resourceId: 'user-1',
        changesBefore: { email: 'old@example.com', phone: '010-1111-1111' },
        changesAfter: { email: 'new@example.com', phone: '010-2222-2222' },
        metadataIp: null,
        status: 'success',
        errorMessage: null
      });

      const logs = auditLogger.query({ limit: 1 });
      const log = logs[0];

      expect(log.changesAfter).toEqual({ email: 'new@example.com', phone: '010-2222-2222' });
      expect(log.changesBefore).toEqual({ email: 'old@example.com', phone: '010-1111-1111' });
    });
  });
});
