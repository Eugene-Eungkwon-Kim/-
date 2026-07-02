import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import bcrypt from 'bcryptjs';
import {
  AuditAction,
  AuditLogEntry,
  CreditGrade,
  CreditHistoryEntry,
  RegisterUserInput,
  UpdateUserInput,
  UserProfile
} from '../types/user';
import { DuplicateEmailError, OptimisticLockError, UserNotFoundError } from './errors';
import { validateRegisterUserInput, validateUpdateUserInput } from '../validation/userValidation';

const PASSWORD_SALT_ROUNDS = 10;

interface UserRow {
  id: string;
  email: string;
  name: string;
  password_hash: string | null;
  date_of_birth: string | null;
  employment_status: string | null;
  employment_industry: string | null;
  employment_tenure: number | null;
  employment_company: string | null;
  phone: string | null;
  address_street: string | null;
  address_city: string | null;
  address_zipcode: string | null;
  address_country: string | null;
  credit_score: number | null;
  credit_grade: string | null;
  credit_inquiries: number;
  credit_delinquency: number;
  income: number | null;
  expenses: number | null;
  assets: number | null;
  debt: number | null;
  savings_rate: number | null;
  version: number;
  status: string;
  role: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

type UserRowColumn = keyof UserRow;
type AuditDiff = Record<string, { from: unknown; to: unknown }>;

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * 신용점수 → 등급 매핑. Day 4 상품추천(δ=520)에서 사용한 800/700/600 경계를 그대로 따르되,
 * 사용자 프로필 명세(A/B/C/D/F)에 맞춰 D/F 구간을 추가한다.
 */
function computeCreditGrade(score: number | null | undefined): CreditGrade | null {
  if (score === null || score === undefined) return null;
  if (score >= 800) return 'A';
  if (score >= 700) return 'B';
  if (score >= 600) return 'C';
  if (score >= 500) return 'D';
  return 'F';
}

function mapRowToProfile(row: UserRow): UserProfile {
  return {
    id: row.id,
    email: row.email,
    name: row.name,
    dateOfBirth: row.date_of_birth,
    employment: {
      status: row.employment_status as UserProfile['employment']['status'],
      industry: row.employment_industry,
      tenure: row.employment_tenure,
      company: row.employment_company
    },
    contact: {
      phone: row.phone,
      address: {
        street: row.address_street,
        city: row.address_city,
        zipCode: row.address_zipcode,
        country: row.address_country
      }
    },
    creditProfile: {
      score: row.credit_score,
      grade: row.credit_grade as CreditGrade | null,
      inquiries: row.credit_inquiries,
      delinquency: row.credit_delinquency
    },
    financialSnapshot: {
      monthlyIncome: row.income,
      monthlyExpenses: row.expenses,
      totalAssets: row.assets,
      totalDebt: row.debt,
      savingsRate: row.savings_rate
    },
    metadata: {
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      lastLoginAt: row.last_login_at,
      status: row.status as UserProfile['metadata']['status'],
      role: row.role as UserProfile['metadata']['role'],
      version: row.version
    }
  };
}

/**
 * 사용자 프로필 & 계정 관리 리포지토리 (Day 5 - Task 1, δ=1635)
 *
 * 낙관적 동시성 제어(version 컬럼)와 감사 로그(users_audit)를 리포지토리 레벨에서
 * 강제하여, 호출자가 매번 동시성/추적 로직을 재구현하지 않도록 한다.
 * 입력 검증은 src/validation/userValidation.ts (Task 5, δ=1605)에 위임하며,
 * DB CHECK 제약은 애플리케이션 검증을 우회하는 경로에 대비한 최후 방어선이다.
 */
export class UserRepository {
  constructor(private readonly db: Database.Database) {}

  register(input: RegisterUserInput): UserProfile {
    validateRegisterUserInput(input, todayIso());

    const id = randomUUID();
    const grade = computeCreditGrade(input.creditProfile?.score);
    const passwordHash = input.password ? bcrypt.hashSync(input.password, PASSWORD_SALT_ROUNDS) : null;

    const insert = this.db.prepare(`
      INSERT INTO users (
        id, email, name, password_hash, date_of_birth,
        employment_status, employment_industry, employment_tenure, employment_company,
        phone, address_street, address_city, address_zipcode, address_country,
        credit_score, credit_grade, credit_inquiries, credit_delinquency,
        income, expenses, assets, debt, savings_rate
      ) VALUES (
        @id, @email, @name, @passwordHash, @dateOfBirth,
        @employmentStatus, @employmentIndustry, @employmentTenure, @employmentCompany,
        @phone, @addressStreet, @addressCity, @addressZipcode, @addressCountry,
        @creditScore, @creditGrade, @creditInquiries, @creditDelinquency,
        @income, @expenses, @assets, @debt, @savingsRate
      )
    `);

    try {
      insert.run({
        id,
        email: input.email,
        name: input.name,
        passwordHash,
        dateOfBirth: input.dateOfBirth ?? null,
        employmentStatus: input.employment?.status ?? null,
        employmentIndustry: input.employment?.industry ?? null,
        employmentTenure: input.employment?.tenure ?? null,
        employmentCompany: input.employment?.company ?? null,
        phone: input.contact?.phone ?? null,
        addressStreet: input.contact?.address?.street ?? null,
        addressCity: input.contact?.address?.city ?? null,
        addressZipcode: input.contact?.address?.zipCode ?? null,
        addressCountry: input.contact?.address?.country ?? null,
        creditScore: input.creditProfile?.score ?? null,
        creditGrade: grade,
        creditInquiries: input.creditProfile?.inquiries ?? 0,
        creditDelinquency: input.creditProfile?.delinquency ?? 0,
        income: input.financialSnapshot?.monthlyIncome ?? null,
        expenses: input.financialSnapshot?.monthlyExpenses ?? null,
        assets: input.financialSnapshot?.totalAssets ?? null,
        debt: input.financialSnapshot?.totalDebt ?? null,
        savingsRate: input.financialSnapshot?.savingsRate ?? null
      });
    } catch (error) {
      if (error instanceof Error && /UNIQUE constraint failed: users\.email/.test(error.message)) {
        throw new DuplicateEmailError(input.email);
      }
      throw error;
    }

    this.recordAudit(id, 'CREATE', {
      email: { from: null, to: input.email },
      name: { from: null, to: input.name }
    });

    return this.getProfileOrThrow(id);
  }

  getProfile(userId: string): UserProfile | null {
    const row = this.db.prepare('SELECT * FROM users WHERE id = ?').get(userId) as UserRow | undefined;
    return row ? mapRowToProfile(row) : null;
  }

  /**
   * 이메일+비밀번호를 검증한다. 비밀번호를 설정하지 않고 등록된 사용자(password_hash가 null)는
   * 어떤 입력으로도 로그인할 수 없다 — null과 일치하는 해시는 존재하지 않으므로 안전하다.
   */
  verifyPassword(email: string, plainPassword: string): UserProfile | null {
    const row = this.db.prepare('SELECT * FROM users WHERE email = ?').get(email) as UserRow | undefined;
    if (!row || !row.password_hash) return null;
    return bcrypt.compareSync(plainPassword, row.password_hash) ? mapRowToProfile(row) : null;
  }

  updateProfile(userId: string, updates: UpdateUserInput, expectedVersion: number): UserProfile {
    validateUpdateUserInput(updates, todayIso());

    const currentRow = this.db.prepare('SELECT * FROM users WHERE id = ?').get(userId) as UserRow | undefined;
    if (!currentRow) throw new UserNotFoundError(userId);
    if (currentRow.version !== expectedVersion) {
      throw new OptimisticLockError(userId, expectedVersion, currentRow.version);
    }

    const columnUpdates: Partial<Record<UserRowColumn, unknown>> = {};
    const diff: AuditDiff = {};

    const setIfChanged = (column: UserRowColumn, nextValue: unknown): void => {
      if (nextValue === undefined) return;
      const currentValue = currentRow[column];
      if (currentValue !== nextValue) {
        columnUpdates[column] = nextValue;
        diff[column] = { from: currentValue, to: nextValue };
      }
    };

    setIfChanged('name', updates.name);
    setIfChanged('date_of_birth', updates.dateOfBirth);
    setIfChanged('employment_status', updates.employment?.status);
    setIfChanged('employment_industry', updates.employment?.industry);
    setIfChanged('employment_tenure', updates.employment?.tenure);
    setIfChanged('employment_company', updates.employment?.company);
    setIfChanged('phone', updates.contact?.phone);
    setIfChanged('address_street', updates.contact?.address?.street);
    setIfChanged('address_city', updates.contact?.address?.city);
    setIfChanged('address_zipcode', updates.contact?.address?.zipCode);
    setIfChanged('address_country', updates.contact?.address?.country);
    setIfChanged('credit_inquiries', updates.creditProfile?.inquiries);
    setIfChanged('credit_delinquency', updates.creditProfile?.delinquency);
    setIfChanged('income', updates.financialSnapshot?.monthlyIncome);
    setIfChanged('expenses', updates.financialSnapshot?.monthlyExpenses);
    setIfChanged('assets', updates.financialSnapshot?.totalAssets);
    setIfChanged('debt', updates.financialSnapshot?.totalDebt);
    setIfChanged('savings_rate', updates.financialSnapshot?.savingsRate);
    setIfChanged('status', updates.status);

    if (updates.creditProfile?.score !== undefined) {
      setIfChanged('credit_score', updates.creditProfile.score);
      setIfChanged('credit_grade', computeCreditGrade(updates.creditProfile.score));
    }

    if (Object.keys(columnUpdates).length === 0) {
      return mapRowToProfile(currentRow);
    }

    const setClauses = Object.keys(columnUpdates)
      .map((column) => `${column} = @${column}`)
      .concat(["updated_at = datetime('now')", 'version = version + 1'])
      .join(', ');

    const update = this.db.prepare(`UPDATE users SET ${setClauses} WHERE id = @id AND version = @expectedVersion`);
    const result = update.run({ ...columnUpdates, id: userId, expectedVersion });

    if (result.changes === 0) {
      const latest = this.db.prepare('SELECT version FROM users WHERE id = ?').get(userId) as
        | { version: number }
        | undefined;
      throw new OptimisticLockError(userId, expectedVersion, latest?.version ?? -1);
    }

    this.recordAudit(userId, 'UPDATE', diff);

    return this.getProfileOrThrow(userId);
  }

  getCreditHistory(userId: string): CreditHistoryEntry[] {
    const rows = this.db
      .prepare(
        `
        SELECT changed_at,
               json_extract(changed_fields, '$.credit_score.from') as from_value,
               json_extract(changed_fields, '$.credit_score.to') as to_value
        FROM users_audit
        WHERE user_id = ? AND action = 'UPDATE' AND json_extract(changed_fields, '$.credit_score') IS NOT NULL
        ORDER BY changed_at ASC
      `
      )
      .all(userId) as { changed_at: string; from_value: number | null; to_value: number | null }[];

    return rows.map((row) => ({
      changedAt: row.changed_at,
      from: row.from_value,
      to: row.to_value
    }));
  }

  getAuditLog(userId: string): AuditLogEntry[] {
    const rows = this.db
      .prepare('SELECT * FROM users_audit WHERE user_id = ? ORDER BY changed_at ASC')
      .all(userId) as {
      id: string;
      user_id: string;
      action: string;
      changed_fields: string;
      changed_by: string;
      changed_at: string;
    }[];

    return rows.map((row) => ({
      id: row.id,
      userId: row.user_id,
      action: row.action as AuditAction,
      changedFields: JSON.parse(row.changed_fields) as AuditDiff,
      changedBy: row.changed_by,
      changedAt: row.changed_at
    }));
  }

  private getProfileOrThrow(userId: string): UserProfile {
    const profile = this.getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);
    return profile;
  }

  private recordAudit(userId: string, action: AuditAction, diff: AuditDiff): void {
    this.db
      .prepare('INSERT INTO users_audit (id, user_id, action, changed_fields) VALUES (?, ?, ?, ?)')
      .run(randomUUID(), userId, action, JSON.stringify(diff));
  }
}
