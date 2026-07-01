/**
 * 사용자 프로필 & 계정 관리 관련 타입 정의
 * Day 5 - Task 1: User Profile Management (δ=1635)
 */

export type EmploymentStatus = 'employed' | 'self-employed' | 'unemployed';
export type CreditGrade = 'A' | 'B' | 'C' | 'D' | 'F';
export type UserStatus = 'active' | 'inactive' | 'suspended';
export type AuditAction = 'CREATE' | 'UPDATE' | 'DELETE';

export interface EmploymentInfo {
  status: EmploymentStatus | null;
  industry: string | null;
  tenure: number | null; // months
  company: string | null;
}

export interface AddressInfo {
  street: string | null;
  city: string | null;
  zipCode: string | null;
  country: string | null;
}

export interface ContactInfo {
  phone: string | null;
  address: AddressInfo;
}

export interface CreditProfile {
  score: number | null; // 0-999
  grade: CreditGrade | null;
  inquiries: number;
  delinquency: number;
}

export interface FinancialSnapshot {
  monthlyIncome: number | null;
  monthlyExpenses: number | null;
  totalAssets: number | null;
  totalDebt: number | null;
  savingsRate: number | null; // %
}

export interface UserMetadata {
  createdAt: string;
  updatedAt: string;
  lastLoginAt: string | null;
  status: UserStatus;
  version: number; // optimistic locking
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  dateOfBirth: string | null;
  employment: EmploymentInfo;
  contact: ContactInfo;
  creditProfile: CreditProfile;
  financialSnapshot: FinancialSnapshot;
  metadata: UserMetadata;
}

export interface EmploymentInput {
  status?: EmploymentStatus;
  industry?: string;
  tenure?: number;
  company?: string;
}

export interface AddressInput {
  street?: string;
  city?: string;
  zipCode?: string;
  country?: string;
}

export interface ContactInput {
  phone?: string;
  address?: AddressInput;
}

export interface CreditProfileInput {
  score?: number;
  inquiries?: number;
  delinquency?: number;
}

export interface FinancialSnapshotInput {
  monthlyIncome?: number;
  monthlyExpenses?: number;
  totalAssets?: number;
  totalDebt?: number;
  savingsRate?: number;
}

export interface RegisterUserInput {
  email: string;
  name: string;
  dateOfBirth?: string;
  employment?: EmploymentInput;
  contact?: ContactInput;
  creditProfile?: CreditProfileInput;
  financialSnapshot?: FinancialSnapshotInput;
}

export interface UpdateUserInput {
  name?: string;
  dateOfBirth?: string;
  employment?: EmploymentInput;
  contact?: ContactInput;
  creditProfile?: CreditProfileInput;
  financialSnapshot?: FinancialSnapshotInput;
  status?: UserStatus;
}

export interface AuditLogEntry {
  id: string;
  userId: string;
  action: AuditAction;
  changedFields: Record<string, { from: unknown; to: unknown }>;
  changedBy: string;
  changedAt: string;
}

export interface CreditHistoryEntry {
  changedAt: string;
  from: number | null;
  to: number | null;
}
