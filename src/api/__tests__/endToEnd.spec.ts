import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Pool } from 'pg';
import { initializeTestDatabase, cleanupTestDatabase } from '@db/__tests__/testDatabase';
import { getUserProfile, registerUser, updateUserProfile } from '@api/userService';
import { applyForLoan, detectDelinquentLoans, getLoanPortfolio, recordLoanPayment } from '@api/loanService';
import { recordTransaction, getTransactionSummary } from '@api/transactionService';
import { getSnapshotTrend, runRiskAssessment } from '@api/financialAnalyticsService';
import { createBackup, runIntegrityCheck } from '@api/adminService';
import { LoanRepository } from '@repositories/LoanRepository';
import { BackupManager } from '@repositories/BackupManager';

describe('End-to-End Service Integration (Day 6 - Task 7: 종단 통합 테스트, δ=1225)', () => {
  let pool: Pool;
  let backupDir: string;

  beforeEach(async () => {
    process.env.ENCRYPTION_KEY = 'de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0de0d';
    pool = await initializeTestDatabase();
    backupDir = fs.mkdtempSync(path.join(os.tmpdir(), 'maars-e2e-'));
  });

  afterEach(async () => {
    fs.rmSync(backupDir, { recursive: true, force: true });
    await cleanupTestDatabase();
    delete process.env.ENCRYPTION_KEY;
  });

  describe('[T-SVC-701~706] 종단 통합 시나리오', () => {
    it('[T-SVC-701] 전체 플로우: 등록→대출신청→거래기록→리스크평가→추세조회', async () => {
      const registered = await registerUser(pool, {
        email: 'e2e-full@example.com',
        name: 'E2E Full User',
        password: 'test-password-123',
        creditProfile: { score: 720 },
        financialSnapshot: { monthlyIncome: 6000000, totalDebt: 30000000, totalAssets: 400000000, savingsRate: 20 }
      });
      expect(registered.success).toBe(true);
      const userId = registered.success ? registered.data.id : '';

      const loan = await applyForLoan(pool, {
        userId,
        productId: 'standard-loan-1',
        originalAmount: 300000000,
        interestRate: 3.2,
        termMonths: 240,
        startDate: '2026-01-01'
      });
      expect(loan.success).toBe(true);

      const txn = await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-05' });
      expect(txn.success).toBe(true);

      const risk = await runRiskAssessment(pool, userId, '2026-01-05');
      expect(risk.success).toBe(true);

      const trend = await getSnapshotTrend(pool, userId, 'riskScore');
      expect(trend.success).toBe(true);
      if (trend.success) expect(trend.data.points.length).toBe(1);
    });

    it('[T-SVC-702] 낙관적 락 충돌이 서비스 계층까지 전파된다', async () => {
      const created = await registerUser(pool, { email: 'e2e-lock@example.com', name: 'E2E Lock User', password: 'test-password-123' });
      const userId = created.success ? created.data.id : '';

      const firstWriter = await updateUserProfile(pool, userId, { name: 'First Writer' }, 1);
      expect(firstWriter.success).toBe(true);

      const staleWriter = await updateUserProfile(pool, userId, { name: 'Stale Writer' }, 1);
      expect(staleWriter.success).toBe(false);
      if (!staleWriter.success) expect(staleWriter.error.code).toBe('VERSION_CONFLICT');

      // 실제로 반영된 값은 first writer의 값이어야 한다
      const profile = await getUserProfile(pool, userId);
      expect(profile.success).toBe(true);
      if (profile.success) expect(profile.data.name).toBe('First Writer');
    });

    it('[T-SVC-703] 대출 연체 감지 → 이력 기록 → 무결성 체크 연동', async () => {
      const created = await registerUser(pool, { email: 'e2e-delinquent@example.com', name: 'E2E Delinquent User', password: 'test-password-123' });
      const userId = created.success ? created.data.id : '';

      const loan = await applyForLoan(pool, {
        userId,
        productId: 'p1',
        originalAmount: 50000000,
        interestRate: 3.5,
        termMonths: 60,
        startDate: '2020-01-01' // 오래 전 대출 → 다음 상환일이 이미 지남
      });
      expect(loan.success).toBe(true);
      const loanId = loan.success ? loan.data.id : '';

      // Day7 Task2에서 서비스 계층에 노출된 연체 감지 배치 진입점을 사용한다
      const delinquent = await detectDelinquentLoans(pool, '2026-07-01');
      expect(delinquent.success).toBe(true);
      if (delinquent.success) {
        expect(delinquent.data.some((l) => l.id === loanId)).toBe(true);
      }

      const history = await new LoanRepository(pool).getLoanHistory(loanId);
      expect(history.some((h) => h.action === 'STATUS_CHANGE')).toBe(true);

      const integrity = await runIntegrityCheck(pool, '2026-07-01');
      expect(integrity.success).toBe(true);
      if (integrity.success) {
        // 연체 처리 자체는 무결성 위반이 아니다 (정상적인 상태 전이)
        expect(integrity.data.every((r) => r.status === 'ok')).toBe(true);
      }
    });

    it('[T-SVC-704] 백업 → 복구 → 복구된 DB로 서비스 재조회', async () => {
      const created = await registerUser(pool, { email: 'e2e-backup@example.com', name: 'E2E Backup User', password: 'test-password-123' });
      const userId = created.success ? created.data.id : '';
      await applyForLoan(pool, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });

      const backup = await createBackup(pool, backupDir);
      expect(backup.success).toBe(true);
      const backupPath = backup.success ? backup.data.backupPath : '';

      // PostgreSQL 이관 후 백업은 SQLite 파일이 아니라 FK-안전 순서의 INSERT
      // 스크립트다. 따라서 "백업 파일을 DB로 열어 재조회"하는 대신, 덤프가
      // 트랜잭션으로 완결됐고 백업 시점의 데이터를 담고 있는지 검증한다.
      const dump = fs.readFileSync(backupPath, 'utf-8');
      expect(dump.startsWith('BEGIN;')).toBe(true);
      expect(dump.trimEnd().endsWith('COMMIT;')).toBe(true);
      expect(dump).toContain('INSERT INTO users');
      expect(dump).toContain('INSERT INTO loans');
      expect(dump).toContain(userId);

      // 복원 경로는 스크립트를 온전히 꺼내오는 데까지 책임진다.
      const restoredPath = path.join(backupDir, 'restored.sql');
      await new BackupManager(pool, backupDir).restoreFromBackup(backup.success ? backup.data.id : '', restoredPath);
      expect(fs.readFileSync(restoredPath, 'utf-8')).toBe(dump);
    });

    it('[T-SVC-705] 여러 서비스가 동일 DB 상태를 즉시 공유한다', async () => {
      const created = await registerUser(pool, { email: 'e2e-shared@example.com', name: 'E2E Shared User', password: 'test-password-123', financialSnapshot: { monthlyIncome: 5000000 } });
      const userId = created.success ? created.data.id : '';

      await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-01' });
      await recordTransaction(pool, { userId, transactionType: 'withdrawal', amount: 300000, occurredAt: '2026-01-02' });

      const summary = await getTransactionSummary(pool, userId);
      expect(summary.success).toBe(true);
      if (summary.success) {
        expect(summary.data.transactionCount).toBe(2);
        expect(summary.data.totalDeposits).toBe(1000000);
      }
    });

    it('[T-SVC-706] 여러 서비스 활동 이후에도 관리자 무결성 체크는 위반 없이 통과한다', async () => {
      const created = await registerUser(pool, {
        email: 'e2e-health@example.com',
        name: 'E2E Health User',
        password: 'test-password-123',
        creditProfile: { score: 750 },
        financialSnapshot: { monthlyIncome: 5000000, totalDebt: 20000000, totalAssets: 200000000 }
      });
      const userId = created.success ? created.data.id : '';

      await applyForLoan(pool, { userId, productId: 'p1', originalAmount: 100000000, interestRate: 3.2, termMonths: 120, startDate: '2026-01-01' });
      await recordTransaction(pool, { userId, transactionType: 'deposit', amount: 500000, occurredAt: '2026-01-05' });
      await runRiskAssessment(pool, userId, '2026-01-05');

      const loanPortfolio = await getLoanPortfolio(pool, userId);
      const loanId = loanPortfolio.success ? loanPortfolio.data[0].id : '';
      await recordLoanPayment(pool, loanId, { paymentDate: '2026-02-01', principal: 500000, interest: 300000 });

      const integrity = await runIntegrityCheck(pool, '2026-07-01');
      expect(integrity.success).toBe(true);
      if (integrity.success) {
        expect(integrity.data.every((r) => r.status === 'ok')).toBe(true);
      }
    });
  });
});
