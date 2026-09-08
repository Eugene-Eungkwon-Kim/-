/**
 * 마이그레이션 리허설용 원본 SQLite DB 생성 스크립트.
 * 실제 리포지토리 경로(암호화, 감사 로그, 대출 상환)를 거쳐
 * 운영과 동일한 형태의 데이터를 만든다.
 */

import Database from 'better-sqlite3';
import fs from 'node:fs';
import { createDatabase } from '../src/db/connection';
import { UserRepository } from '../src/repositories/UserRepository';
import { LoanRepository } from '../src/repositories/LoanRepository';
import { TransactionRepository } from '../src/repositories/TransactionRepository';
import { AuditLogger, AuditAction } from '../src/audit/auditLogger';

const dbPath = process.argv[2];
if (!dbPath) {
  console.error('사용법: vite-node scripts/seed-migration-source.ts <sqlite-path>');
  process.exit(1);
}
if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);

const db: Database.Database = createDatabase(dbPath);
const users = new UserRepository(db);
const loans = new LoanRepository(db);
const txns = new TransactionRepository(db);
const audit = new AuditLogger(db);

// 특수문자(작은따옴표)를 포함한 사용자 — 이스케이프 검증용
const alice = users.register({
  email: "alice.o'brien@example.com",
  name: "Alice O'Brien",
  password: 'alice-password-123',
  dateOfBirth: '1990-05-15',
  contact: { phone: '010-1111-2222', address: { city: 'Seoul', country: 'KR' } },
  creditProfile: { score: 780 },
  financialSnapshot: { monthlyIncome: 6000000 }
});

const bob = users.register({
  email: 'bob@example.com',
  name: 'Bob Kim',
  password: 'bob-password-123',
  contact: { phone: '010-3333-4444', address: {} },
  creditProfile: { score: 650 },
  financialSnapshot: { monthlyIncome: 4000000 }
});

const loan = await loans.registerLoan({
  userId: alice.id,
  productId: 'standard-loan-1',
  originalAmount: 10000000,
  interestRate: 4.5,
  termMonths: 60,
  startDate: '2026-01-01'
});
loans.recordPayment(loan.id, { paymentDate: '2026-02-01', principal: 150000, interest: 37500 });
loans.recordPayment(loan.id, { paymentDate: '2026-03-01', principal: 150000, interest: 36900 });

txns.recordTransaction({ userId: alice.id, transactionType: 'deposit', amount: 1000000, occurredAt: '2026-01-10' });
txns.recordTransaction({ userId: alice.id, transactionType: 'withdrawal', amount: 200000, occurredAt: '2026-02-05' });
// bob 소득(400만)의 50% 초과 → flagged 경로
txns.recordTransaction({ userId: bob.id, transactionType: 'deposit', amount: 3000000, occurredAt: '2026-03-01' });

audit.log({
  userId: alice.id,
  action: AuditAction.LOGIN,
  resourceType: 'session',
  resourceId: alice.id,
  changesBefore: null,
  changesAfter: null,
  metadataIp: '203.0.113.7',
  status: 'success',
  errorMessage: null
});

console.log(`원본 DB 생성 완료: ${dbPath}`);
db.close();
