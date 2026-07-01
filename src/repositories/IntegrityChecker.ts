import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import { calculateLoanPayment } from '../services/interest-calculator';
import { calculateAge, MAX_AGE, MIN_AGE } from '../validation/userValidation';
import { LoanNotFoundError } from './LoanRepository';

export interface IntegrityFinding {
  entityId: string;
  description: string;
}

export type IntegrityStatus = 'ok' | 'violation' | 'repaired';

export interface IntegrityCheckResult {
  checkType: string;
  status: IntegrityStatus;
  findings: IntegrityFinding[];
}

export interface IntegrityLogEntry {
  id: string;
  checkType: string;
  status: IntegrityStatus;
  findings: IntegrityFinding[];
  checkedAt: string;
}

/**
 * DB 무결성 자동 검사 (Day 5 - Task 5, δ=1605)
 *
 * DB 제약(CHECK/UNIQUE/FK)은 "쓰기 시점"의 위반만 막는다. 시간에 따라 조건이
 * 바뀌는 값(나이 등)이나, 두 컬럼이 서로 다른 시점에 각각 정상적으로 쓰였지만
 * 상호 불일치가 발생한 경우(월상환액 재계산 결과와 저장값의 드리프트 등)는
 * 주기적 스캔으로만 잡아낼 수 있다. 모든 검사 결과는 data_integrity_log에 남는다.
 */
export class IntegrityChecker {
  constructor(private readonly db: Database.Database) {}

  checkOrphanedLoans(): IntegrityCheckResult {
    const orphans = this.db
      .prepare(
        `
        SELECT l.id as loan_id
        FROM loans l
        LEFT JOIN users u ON l.user_id = u.id
        WHERE u.id IS NULL
      `
      )
      .all() as { loan_id: string }[];

    const findings: IntegrityFinding[] = orphans.map((o) => ({
      entityId: o.loan_id,
      description: `Loan ${o.loan_id} references a non-existent user`
    }));

    return this.logResult('orphaned_loan', findings);
  }

  checkAgeConsistency(asOfDate: string): IntegrityCheckResult {
    const users = this.db
      .prepare('SELECT id, date_of_birth FROM users WHERE date_of_birth IS NOT NULL')
      .all() as { id: string; date_of_birth: string }[];

    const findings: IntegrityFinding[] = [];
    for (const user of users) {
      const age = calculateAge(user.date_of_birth, asOfDate);
      if (age < MIN_AGE || age > MAX_AGE) {
        findings.push({
          entityId: user.id,
          description: `User ${user.id} age ${age} is outside the allowed ${MIN_AGE}-${MAX_AGE} range`
        });
      }
    }

    return this.logResult('age_out_of_range', findings);
  }

  async checkMonthlyPaymentConsistency(): Promise<IntegrityCheckResult> {
    const loans = this.db
      .prepare("SELECT id, original_amount, interest_rate, term_months, monthly_payment FROM loans WHERE status != 'closed'")
      .all() as { id: string; original_amount: number; interest_rate: number; term_months: number; monthly_payment: number }[];

    const findings: IntegrityFinding[] = [];
    for (const loan of loans) {
      const { monthlyPayment: expected } = await calculateLoanPayment({
        principal: loan.original_amount,
        rate: loan.interest_rate,
        term: loan.term_months
      });
      if (expected !== loan.monthly_payment) {
        findings.push({
          entityId: loan.id,
          description: `Loan ${loan.id} stored monthly_payment ${loan.monthly_payment} does not match recomputed value ${expected}`
        });
      }
    }

    return this.logResult('monthly_payment_drift', findings);
  }

  async runFullCheck(asOfDate: string): Promise<IntegrityCheckResult[]> {
    return [this.checkOrphanedLoans(), this.checkAgeConsistency(asOfDate), await this.checkMonthlyPaymentConsistency()];
  }

  /** monthly_payment 드리프트를 재계산값으로 고치고 'repaired' 상태로 기록한다 */
  async repairMonthlyPaymentDrift(loanId: string): Promise<IntegrityCheckResult> {
    const loan = this.db
      .prepare('SELECT id, original_amount, interest_rate, term_months FROM loans WHERE id = ?')
      .get(loanId) as { id: string; original_amount: number; interest_rate: number; term_months: number } | undefined;

    if (!loan) throw new LoanNotFoundError(loanId);

    const { monthlyPayment: correctValue } = await calculateLoanPayment({
      principal: loan.original_amount,
      rate: loan.interest_rate,
      term: loan.term_months
    });

    this.db
      .prepare("UPDATE loans SET monthly_payment = ?, updated_at = datetime('now') WHERE id = ?")
      .run(correctValue, loanId);

    return this.logResult(
      'monthly_payment_drift',
      [{ entityId: loanId, description: `Repaired monthly_payment to recomputed value ${correctValue}` }],
      'repaired'
    );
  }

  getIntegrityLog(checkType?: string): IntegrityLogEntry[] {
    const rows = (
      checkType
        ? this.db
            .prepare('SELECT * FROM data_integrity_log WHERE check_type = ? ORDER BY checked_at ASC')
            .all(checkType)
        : this.db.prepare('SELECT * FROM data_integrity_log ORDER BY checked_at ASC').all()
    ) as { id: string; check_type: string; status: string; findings: string; checked_at: string }[];

    return rows.map((row) => ({
      id: row.id,
      checkType: row.check_type,
      status: row.status as IntegrityStatus,
      findings: JSON.parse(row.findings) as IntegrityFinding[],
      checkedAt: row.checked_at
    }));
  }

  private logResult(
    checkType: string,
    findings: IntegrityFinding[],
    forcedStatus?: IntegrityStatus
  ): IntegrityCheckResult {
    const status: IntegrityStatus = forcedStatus ?? (findings.length === 0 ? 'ok' : 'violation');
    this.db
      .prepare('INSERT INTO data_integrity_log (id, check_type, status, findings) VALUES (?, ?, ?, ?)')
      .run(randomUUID(), checkType, status, JSON.stringify(findings));
    return { checkType, status, findings };
  }
}
