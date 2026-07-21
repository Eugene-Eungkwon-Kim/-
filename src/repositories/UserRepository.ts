import { randomUUID } from 'node:crypto';
import type { Pool } from 'pg';
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
import { encrypt, decrypt } from '../utils/encryption';

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
  encrypted_email: string | null;
  encrypted_phone: string | null;
  encryption_version: number;
}

type UserRowColumn = keyof UserRow;
type AuditDiff = Record<string, { from: unknown; to: unknown }>;

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function computeCreditGrade(score: number | null | undefined): CreditGrade | null {
  if (score === null || score === undefined) return null;
  if (score >= 800) return 'A';
  if (score >= 700) return 'B';
  if (score >= 600) return 'C';
  if (score >= 500) return 'D';
  return 'F';
}

function mapRowToProfile(row: UserRow): UserProfile {
  const email = row.encrypted_email ? decrypt(row.encrypted_email) : row.email;
  const phone = row.encrypted_phone ? decrypt(row.encrypted_phone) : row.phone;

  return {
    id: row.id,
    email,
    name: row.name,
    dateOfBirth: row.date_of_birth,
    employment: {
      status: row.employment_status as UserProfile['employment']['status'],
      industry: row.employment_industry,
      tenure: row.employment_tenure,
      company: row.employment_company
    },
    contact: {
      phone,
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

export class UserRepository {
  constructor(private readonly pool: Pool) {}

  async register(input: RegisterUserInput): Promise<UserProfile> {
    validateRegisterUserInput(input, todayIso());

    const id = randomUUID();
    const grade = computeCreditGrade(input.creditProfile?.score);
    const passwordHash = input.password ? bcrypt.hashSync(input.password, PASSWORD_SALT_ROUNDS) : null;

    const encryptedEmail = encrypt(input.email);
    const encryptedPhone = input.contact?.phone ? encrypt(input.contact.phone) : null;

    try {
      await this.pool.query(
        `INSERT INTO users (
          id, email, name, password_hash, date_of_birth,
          employment_status, employment_industry, employment_tenure, employment_company,
          phone, address_street, address_city, address_zipcode, address_country,
          credit_score, credit_grade, credit_inquiries, credit_delinquency,
          income, expenses, assets, debt, savings_rate,
          encrypted_email, encrypted_phone, encryption_version
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
          $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26
        )`,
        [
          id,
          input.email,
          input.name,
          passwordHash,
          input.dateOfBirth ?? null,
          input.employment?.status ?? null,
          input.employment?.industry ?? null,
          input.employment?.tenure ?? null,
          input.employment?.company ?? null,
          input.contact?.phone ?? null,
          input.contact?.address?.street ?? null,
          input.contact?.address?.city ?? null,
          input.contact?.address?.zipCode ?? null,
          input.contact?.address?.country ?? null,
          input.creditProfile?.score ?? null,
          grade,
          input.creditProfile?.inquiries ?? 0,
          input.creditProfile?.delinquency ?? 0,
          input.financialSnapshot?.monthlyIncome ?? null,
          input.financialSnapshot?.monthlyExpenses ?? null,
          input.financialSnapshot?.totalAssets ?? null,
          input.financialSnapshot?.totalDebt ?? null,
          input.financialSnapshot?.savingsRate ?? null,
          encryptedEmail,
          encryptedPhone,
          1
        ]
      );
    } catch (error) {
      if (error instanceof Error && /duplicate key value violates unique constraint "users_email_key"/.test(error.message)) {
        throw new DuplicateEmailError(input.email);
      }
      throw error;
    }

    await this.recordAudit(id, 'CREATE', {
      email: { from: null, to: input.email },
      name: { from: null, to: input.name }
    });

    return this.getProfileOrThrow(id);
  }

  async getProfile(userId: string): Promise<UserProfile | null> {
    const result = await this.pool.query('SELECT * FROM users WHERE id = $1', [userId]);
    const row = result.rows[0] as UserRow | undefined;
    return row ? mapRowToProfile(row) : null;
  }

  async verifyPassword(email: string, plainPassword: string): Promise<UserProfile | null> {
    const result = await this.pool.query('SELECT * FROM users WHERE email = $1', [email]);
    const row = result.rows[0] as UserRow | undefined;
    if (!row || !row.password_hash) return null;
    return bcrypt.compareSync(plainPassword, row.password_hash) ? mapRowToProfile(row) : null;
  }

  async updateProfile(userId: string, updates: UpdateUserInput, expectedVersion: number): Promise<UserProfile> {
    validateUpdateUserInput(updates, todayIso());

    const currentResult = await this.pool.query('SELECT * FROM users WHERE id = $1', [userId]);
    const currentRow = currentResult.rows[0] as UserRow | undefined;
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

    if (updates.contact?.phone !== undefined) {
      const encryptedPhone = updates.contact.phone ? encrypt(updates.contact.phone) : null;
      columnUpdates['encrypted_phone'] = encryptedPhone;
      diff['encrypted_phone'] = { from: currentRow.encrypted_phone, to: encryptedPhone };
    }

    if (Object.keys(columnUpdates).length === 0) {
      return mapRowToProfile(currentRow);
    }

    const entries = Object.entries(columnUpdates);
    const setClauses = entries
      .map((_, i) => `${entries[i][0]} = $${i + 1}`)
      .concat(['updated_at = CURRENT_TIMESTAMP', 'version = version + 1'])
      .join(', ');

    const values = [...entries.map(([, v]) => v), userId, expectedVersion];
    const updateResult = await this.pool.query(
      `UPDATE users SET ${setClauses} WHERE id = $${entries.length + 1} AND version = $${entries.length + 2}`,
      values
    );

    if (updateResult.rowCount === 0) {
      const latest = await this.pool.query('SELECT version FROM users WHERE id = $1', [userId]);
      const latestRow = latest.rows[0] as { version: number } | undefined;
      throw new OptimisticLockError(userId, expectedVersion, latestRow?.version ?? -1);
    }

    await this.recordAudit(userId, 'UPDATE', diff);

    return this.getProfileOrThrow(userId);
  }

  async getCreditHistory(userId: string): Promise<CreditHistoryEntry[]> {
    const result = await this.pool.query(
      `SELECT changed_at,
              (changed_fields->'credit_score'->>'from')::numeric as from_value,
              (changed_fields->'credit_score'->>'to')::numeric as to_value
       FROM users_audit
       WHERE user_id = $1 AND action = 'UPDATE' AND changed_fields ? 'credit_score'
       ORDER BY changed_at ASC`,
      [userId]
    );

    return result.rows.map((row) => ({
      changedAt: row.changed_at,
      from: row.from_value,
      to: row.to_value
    }));
  }

  async getAuditLog(userId: string): Promise<AuditLogEntry[]> {
    const result = await this.pool.query(
      'SELECT * FROM users_audit WHERE user_id = $1 ORDER BY changed_at ASC',
      [userId]
    );

    return result.rows.map((row) => ({
      id: row.id,
      userId: row.user_id,
      action: row.action as AuditAction,
      changedFields: typeof row.changed_fields === 'string' ? JSON.parse(row.changed_fields) : row.changed_fields,
      changedBy: row.changed_by,
      changedAt: row.changed_at
    }));
  }

  private async getProfileOrThrow(userId: string): Promise<UserProfile> {
    const profile = await this.getProfile(userId);
    if (!profile) throw new UserNotFoundError(userId);
    return profile;
  }

  private async recordAudit(userId: string, action: AuditAction, diff: AuditDiff): Promise<void> {
    await this.pool.query(
      'INSERT INTO users_audit (id, user_id, action, changed_fields) VALUES ($1, $2, $3, $4)',
      [randomUUID(), userId, action, JSON.stringify(diff)]
    );
  }
}
