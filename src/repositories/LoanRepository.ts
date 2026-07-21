import { randomUUID } from 'node:crypto';
import type { Pool, PoolClient } from 'pg';
import { calculateLoanPayment } from '../services/interest-calculator';
import {
  LoanHistoryAction,
  LoanHistoryEntry,
  LoanRecord,
  LoanStatus,
  PortfolioSummary,
  RecordPaymentInput,
  RegisterLoanInput
} from '../types/loanPortfolio';
import { UserNotFoundError, ValidationError } from './errors';
import { validateRegisterLoanInput } from '../validation/loanValidation';

interface LoanRow {
  id: string;
  user_id: string;
  product_id: string;
  status: string;
  original_amount: number;
  current_balance: number;
  interest_rate: number;
  term_months: number;
  start_date: string;
  maturity_date: string;
  monthly_payment: number;
  next_payment_date: string | null;
  total_paid: number;
  total_interest_paid: number;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export class LoanNotFoundError extends Error {
  constructor(loanId: string) {
    super(`Loan not found: ${loanId}`);
    this.name = 'LoanNotFoundError';
  }
}

export class OverpaymentError extends Error {
  constructor(loanId: string, principal: number, balance: number) {
    super(`Payment principal (${principal}) exceeds current balance (${balance}) for loan ${loanId}`);
    this.name = 'OverpaymentError';
  }
}

function mapRowToLoan(row: LoanRow): LoanRecord {
  return {
    id: row.id,
    userId: row.user_id,
    productId: row.product_id,
    status: row.status as LoanStatus,
    originalAmount: row.original_amount,
    currentBalance: row.current_balance,
    interestRate: row.interest_rate,
    termMonths: row.term_months,
    startDate: row.start_date,
    maturityDate: row.maturity_date,
    monthlyPayment: row.monthly_payment,
    nextPaymentDate: row.next_payment_date,
    totalPaid: row.total_paid,
    totalInterestPaid: row.total_interest_paid,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    closedAt: row.closed_at
  };
}

function addMonths(dateStr: string, months: number): string {
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1 + months, day));
  return date.toISOString().slice(0, 10);
}

export class LoanRepository {
  constructor(private readonly pool: Pool) {}

  async registerLoan(input: RegisterLoanInput): Promise<LoanRecord> {
    validateRegisterLoanInput(input);

    const userResult = await this.pool.query('SELECT 1 FROM users WHERE id = $1', [input.userId]);
    if (!userResult.rows.length) throw new UserNotFoundError(input.userId);

    const { monthlyPayment } = await calculateLoanPayment({
      principal: input.originalAmount,
      rate: input.interestRate,
      term: input.termMonths
    });

    const id = randomUUID();
    const maturityDate = addMonths(input.startDate, input.termMonths);
    const nextPaymentDate = addMonths(input.startDate, 1);

    await this.pool.query(
      `INSERT INTO loans (
        id, user_id, product_id, original_amount, current_balance,
        interest_rate, term_months, start_date, maturity_date,
        monthly_payment, next_payment_date
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
      )`,
      [
        id,
        input.userId,
        input.productId,
        input.originalAmount,
        input.originalAmount,
        input.interestRate,
        input.termMonths,
        input.startDate,
        maturityDate,
        monthlyPayment,
        nextPaymentDate
      ]
    );

    await this.recordHistory(id, 'CREATED', 0, input.originalAmount);

    return this.getLoanOrThrow(id);
  }

  async getLoan(loanId: string): Promise<LoanRecord | null> {
    const result = await this.pool.query('SELECT * FROM loans WHERE id = $1', [loanId]);
    const row = result.rows[0] as LoanRow | undefined;
    return row ? mapRowToLoan(row) : null;
  }

  async getPortfolio(userId: string): Promise<LoanRecord[]> {
    const result = await this.pool.query('SELECT * FROM loans WHERE user_id = $1 ORDER BY created_at ASC', [userId]);
    return (result.rows as LoanRow[]).map(mapRowToLoan);
  }

  async recordPayment(loanId: string, input: RecordPaymentInput): Promise<LoanRecord> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      const rowResult = await client.query('SELECT * FROM loans WHERE id = $1', [loanId]);
      const row = rowResult.rows[0] as LoanRow | undefined;
      if (!row) throw new LoanNotFoundError(loanId);

      const fees = input.fees ?? 0;
      if (input.principal + input.interest + fees <= 0) {
        throw new ValidationError('Payment amount (principal + interest + fees) must be greater than 0');
      }
      if (input.principal > row.current_balance) {
        throw new OverpaymentError(loanId, input.principal, row.current_balance);
      }

      const newBalance = row.current_balance - input.principal;
      const isPaidOff = newBalance === 0;

      await client.query(
        'INSERT INTO loan_payments (id, loan_id, payment_date, principal, interest, fees, status) VALUES ($1, $2, $3, $4, $5, $6, $7)',
        [randomUUID(), loanId, input.paymentDate, input.principal, input.interest, fees, input.status ?? 'completed']
      );

      await client.query(
        `UPDATE loans SET
          current_balance = $1,
          total_paid = total_paid + $2,
          total_interest_paid = total_interest_paid + $3,
          next_payment_date = $4,
          status = $5,
          closed_at = $6,
          updated_at = CURRENT_TIMESTAMP
        WHERE id = $7`,
        [
          newBalance,
          input.principal + input.interest + fees,
          input.interest,
          isPaidOff ? null : addMonths(input.paymentDate, 1),
          isPaidOff ? 'closed' : row.status,
          isPaidOff ? new Date().toISOString() : null,
          loanId
        ]
      );

      await this.recordHistory(loanId, 'PAYMENT', row.current_balance, newBalance, client);

      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }

    return this.getLoanOrThrow(loanId);
  }

  async updateLoanStatus(loanId: string, status: LoanStatus): Promise<LoanRecord> {
    const rowResult = await this.pool.query('SELECT * FROM loans WHERE id = $1', [loanId]);
    const row = rowResult.rows[0] as LoanRow | undefined;
    if (!row) throw new LoanNotFoundError(loanId);
    if (row.status === status) return mapRowToLoan(row);

    await this.pool.query('UPDATE loans SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2', [status, loanId]);

    await this.recordHistory(loanId, 'STATUS_CHANGE', row.current_balance, row.current_balance);

    return this.getLoanOrThrow(loanId);
  }

  async detectDelinquentLoans(asOfDate: string): Promise<LoanRecord[]> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      const overdueResult = await client.query(
        "SELECT * FROM loans WHERE status = 'active' AND next_payment_date < $1 ORDER BY next_payment_date ASC",
        [asOfDate]
      );
      const overdue = overdueResult.rows as LoanRow[];

      for (const row of overdue) {
        await client.query('UPDATE loans SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2', [
          'delinquent',
          row.id
        ]);
        await this.recordHistory(row.id, 'STATUS_CHANGE', row.current_balance, row.current_balance, client);
      }

      await client.query('COMMIT');
      return overdue.map(mapRowToLoan);
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getLoanHistory(loanId: string): Promise<LoanHistoryEntry[]> {
    const result = await this.pool.query('SELECT * FROM loan_history WHERE loan_id = $1 ORDER BY action_date ASC', [
      loanId
    ]);

    return result.rows.map((row) => ({
      id: row.id,
      loanId: row.loan_id,
      action: row.action as LoanHistoryAction,
      previousBalance: row.previous_balance,
      newBalance: row.new_balance,
      actionDate: row.action_date
    }));
  }

  async getPortfolioSummary(userId: string): Promise<PortfolioSummary> {
    const loans = await this.getPortfolio(userId);
    const activeLoans = loans.filter((l) => l.status === 'active' || l.status === 'delinquent');

    const totalOriginalAmount = loans.reduce((sum, l) => sum + l.originalAmount, 0);
    const totalCurrentBalance = activeLoans.reduce((sum, l) => sum + l.currentBalance, 0);
    const totalMonthlyPayment = activeLoans.reduce((sum, l) => sum + l.monthlyPayment, 0);
    const averageInterestRate =
      activeLoans.length > 0
        ? Math.round((activeLoans.reduce((sum, l) => sum + l.interestRate, 0) / activeLoans.length) * 100) / 100
        : 0;

    return {
      userId,
      loanCount: loans.length,
      activeLoanCount: activeLoans.length,
      delinquentLoanCount: loans.filter((l) => l.status === 'delinquent').length,
      totalOriginalAmount,
      totalCurrentBalance,
      totalMonthlyPayment,
      averageInterestRate
    };
  }

  private async getLoanOrThrow(loanId: string): Promise<LoanRecord> {
    const loan = await this.getLoan(loanId);
    if (!loan) throw new LoanNotFoundError(loanId);
    return loan;
  }

  private async recordHistory(
    loanId: string,
    action: LoanHistoryAction,
    previousBalance: number,
    newBalance: number,
    client?: PoolClient
  ): Promise<void> {
    const query =
      'INSERT INTO loan_history (id, loan_id, action, previous_balance, new_balance) VALUES ($1, $2, $3, $4, $5)';
    const values = [randomUUID(), loanId, action, previousBalance, newBalance];

    if (client) {
      await client.query(query, values);
    } else {
      await this.pool.query(query, values);
    }
  }
}
