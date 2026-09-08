import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
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

export class IntegrityChecker {
  constructor(private readonly pool: Pool) {}

  async checkOrphanedLoans(): Promise<IntegrityCheckResult> {
    const result = await this.pool.query(`
      SELECT l.id as loan_id
      FROM loans l
      LEFT JOIN users u ON l.user_id = u.id
      WHERE u.id IS NULL
    `);
    const orphans = result.rows as { loan_id: string }[];

    const findings: IntegrityFinding[] = orphans.map((o) => ({
      entityId: o.loan_id,
      description: `Loan ${o.loan_id} references a non-existent user`
    }));

    return this.logResult('orphaned_loan', findings);
  }

  async checkAgeConsistency(asOfDate: string): Promise<IntegrityCheckResult> {
    const result = await this.pool.query('SELECT id, date_of_birth FROM users WHERE date_of_birth IS NOT NULL');
    const users = result.rows as { id: string; date_of_birth: string }[];

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
    const result = await this.pool.query(
      "SELECT id, original_amount, interest_rate, term_months, monthly_payment FROM loans WHERE status != 'closed'"
    );
    const loans = result.rows as {
      id: string;
      original_amount: number;
      interest_rate: number;
      term_months: number;
      monthly_payment: number;
    }[];

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
    return [
      await this.checkOrphanedLoans(),
      await this.checkAgeConsistency(asOfDate),
      await this.checkMonthlyPaymentConsistency()
    ];
  }

  async repairMonthlyPaymentDrift(loanId: string): Promise<IntegrityCheckResult> {
    const loanResult = await this.pool.query(
      'SELECT id, original_amount, interest_rate, term_months FROM loans WHERE id = $1',
      [loanId]
    );
    const loan = loanResult.rows[0] as {
      id: string;
      original_amount: number;
      interest_rate: number;
      term_months: number;
    } | undefined;

    if (!loan) throw new LoanNotFoundError(loanId);

    const { monthlyPayment: correctValue } = await calculateLoanPayment({
      principal: loan.original_amount,
      rate: loan.interest_rate,
      term: loan.term_months
    });

    await this.pool.query(
      'UPDATE loans SET monthly_payment = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2',
      [correctValue, loanId]
    );

    return this.logResult(
      'monthly_payment_drift',
      [{ entityId: loanId, description: `Repaired monthly_payment to recomputed value ${correctValue}` }],
      'repaired'
    );
  }

  async getIntegrityLog(checkType?: string): Promise<IntegrityLogEntry[]> {
    const result = checkType
      ? await this.pool.query('SELECT * FROM data_integrity_log WHERE check_type = $1 ORDER BY checked_at ASC', [checkType])
      : await this.pool.query('SELECT * FROM data_integrity_log ORDER BY checked_at ASC');

    return result.rows.map((row) => ({
      id: row.id,
      checkType: row.check_type,
      status: row.status as IntegrityStatus,
      findings: typeof row.findings === 'string' ? JSON.parse(row.findings) : row.findings,
      checkedAt: row.checked_at
    }));
  }

  private async logResult(
    checkType: string,
    findings: IntegrityFinding[],
    forcedStatus?: IntegrityStatus
  ): Promise<IntegrityCheckResult> {
    const status: IntegrityStatus = forcedStatus ?? (findings.length === 0 ? 'ok' : 'violation');
    await this.pool.query(
      'INSERT INTO data_integrity_log (id, check_type, status, findings) VALUES ($1, $2, $3, $4)',
      [randomUUID(), checkType, status, JSON.stringify(findings)]
    );
    return { checkType, status, findings };
  }
}
