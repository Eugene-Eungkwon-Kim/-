import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
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

/** 'YYYY-MM-DD' 문자열에 개월 수를 더한 'YYYY-MM-DD'를 반환 (UTC 기준, TZ 영향 없음) */
function addMonths(dateStr: string, months: number): string {
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1 + months, day));
  return date.toISOString().slice(0, 10);
}

/**
 * 대출 포트폴리오 관리 리포지토리 (Day 5 - Task 2, δ=1570)
 *
 * 월상환액 계산은 src/services/interest-calculator.ts 의 기존 상각 공식을 재사용한다
 * (Day3/4 MSW mock에서 동일 공식을 여러 번 복제했던 것과 달리, 실제 저장 계층에서는
 * 단일 출처를 유지해 공식이 어긋날 여지를 없앤다).
 */
export class LoanRepository {
  constructor(private readonly db: Database.Database) {}

  async registerLoan(input: RegisterLoanInput): Promise<LoanRecord> {
    validateRegisterLoanInput(input);

    const userExists = this.db.prepare('SELECT 1 FROM users WHERE id = ?').get(input.userId);
    if (!userExists) throw new UserNotFoundError(input.userId);

    const { monthlyPayment } = await calculateLoanPayment({
      principal: input.originalAmount,
      rate: input.interestRate,
      term: input.termMonths
    });

    const id = randomUUID();
    const maturityDate = addMonths(input.startDate, input.termMonths);
    const nextPaymentDate = addMonths(input.startDate, 1);

    this.db
      .prepare(
        `
        INSERT INTO loans (
          id, user_id, product_id, original_amount, current_balance,
          interest_rate, term_months, start_date, maturity_date,
          monthly_payment, next_payment_date
        ) VALUES (
          @id, @userId, @productId, @originalAmount, @originalAmount,
          @interestRate, @termMonths, @startDate, @maturityDate,
          @monthlyPayment, @nextPaymentDate
        )
      `
      )
      .run({
        id,
        userId: input.userId,
        productId: input.productId,
        originalAmount: input.originalAmount,
        interestRate: input.interestRate,
        termMonths: input.termMonths,
        startDate: input.startDate,
        maturityDate,
        monthlyPayment,
        nextPaymentDate
      });

    this.recordHistory(id, 'CREATED', 0, input.originalAmount);

    return this.getLoanOrThrow(id);
  }

  getLoan(loanId: string): LoanRecord | null {
    const row = this.db.prepare('SELECT * FROM loans WHERE id = ?').get(loanId) as LoanRow | undefined;
    return row ? mapRowToLoan(row) : null;
  }

  getPortfolio(userId: string): LoanRecord[] {
    const rows = this.db
      .prepare('SELECT * FROM loans WHERE user_id = ? ORDER BY created_at ASC')
      .all(userId) as LoanRow[];
    return rows.map(mapRowToLoan);
  }

  recordPayment(loanId: string, input: RecordPaymentInput): LoanRecord {
    const row = this.db.prepare('SELECT * FROM loans WHERE id = ?').get(loanId) as LoanRow | undefined;
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

    const recordPaymentStmt = this.db.transaction(() => {
      this.db
        .prepare(
          'INSERT INTO loan_payments (id, loan_id, payment_date, principal, interest, fees, status) VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        .run(randomUUID(), loanId, input.paymentDate, input.principal, input.interest, fees, input.status ?? 'completed');

      this.db
        .prepare(
          `
          UPDATE loans SET
            current_balance = @newBalance,
            total_paid = total_paid + @totalPayment,
            total_interest_paid = total_interest_paid + @interest,
            next_payment_date = @nextPaymentDate,
            status = @status,
            closed_at = @closedAt,
            updated_at = datetime('now')
          WHERE id = @id
        `
        )
        .run({
          id: loanId,
          newBalance,
          totalPayment: input.principal + input.interest + fees,
          interest: input.interest,
          nextPaymentDate: isPaidOff ? null : addMonths(input.paymentDate, 1),
          status: isPaidOff ? 'closed' : row.status,
          closedAt: isPaidOff ? new Date().toISOString() : null
        });

      this.recordHistory(loanId, 'PAYMENT', row.current_balance, newBalance);
    });
    recordPaymentStmt();

    return this.getLoanOrThrow(loanId);
  }

  updateLoanStatus(loanId: string, status: LoanStatus): LoanRecord {
    const row = this.db.prepare('SELECT * FROM loans WHERE id = ?').get(loanId) as LoanRow | undefined;
    if (!row) throw new LoanNotFoundError(loanId);
    if (row.status === status) return mapRowToLoan(row);

    this.db
      .prepare("UPDATE loans SET status = ?, updated_at = datetime('now') WHERE id = ?")
      .run(status, loanId);

    this.recordHistory(loanId, 'STATUS_CHANGE', row.current_balance, row.current_balance);

    return this.getLoanOrThrow(loanId);
  }

  /** next_payment_date가 오늘보다 과거인 active 대출을 delinquent로 전환한다 */
  detectDelinquentLoans(asOfDate: string): LoanRecord[] {
    const overdue = this.db
      .prepare("SELECT * FROM loans WHERE status = 'active' AND next_payment_date < ? ORDER BY next_payment_date ASC")
      .all(asOfDate) as LoanRow[];

    // updateLoanStatus를 건별로 호출하면 N개의 개별 트랜잭션이 생긴다. 배치 전체를
    // 하나의 트랜잭션으로 묶어 원자성을 보장하고(중간 실패 시 부분 반영 방지) 커밋 횟수를 줄인다.
    const flagBatch = this.db.transaction(() => {
      for (const row of overdue) {
        this.updateLoanStatus(row.id, 'delinquent');
      }
    });
    flagBatch();

    return overdue.map((row) => this.getLoanOrThrow(row.id));
  }

  getLoanHistory(loanId: string): LoanHistoryEntry[] {
    const rows = this.db
      .prepare('SELECT * FROM loan_history WHERE loan_id = ? ORDER BY action_date ASC')
      .all(loanId) as {
      id: string;
      loan_id: string;
      action: string;
      previous_balance: number;
      new_balance: number;
      action_date: string;
    }[];

    return rows.map((row) => ({
      id: row.id,
      loanId: row.loan_id,
      action: row.action as LoanHistoryAction,
      previousBalance: row.previous_balance,
      newBalance: row.new_balance,
      actionDate: row.action_date
    }));
  }

  getPortfolioSummary(userId: string): PortfolioSummary {
    const loans = this.getPortfolio(userId);
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

  private getLoanOrThrow(loanId: string): LoanRecord {
    const loan = this.getLoan(loanId);
    if (!loan) throw new LoanNotFoundError(loanId);
    return loan;
  }

  private recordHistory(loanId: string, action: LoanHistoryAction, previousBalance: number, newBalance: number): void {
    this.db
      .prepare(
        'INSERT INTO loan_history (id, loan_id, action, previous_balance, new_balance) VALUES (?, ?, ?, ?, ?)'
      )
      .run(randomUUID(), loanId, action, previousBalance, newBalance);
  }
}
