/**
 * 브라우저에서 Fastify 서버(src/server)를 호출하는 최소 fetch 클라이언트.
 * 서버가 이미 ServiceResult<T> 형태로 응답하므로 여기서는 파싱만 한다.
 */
export type ServiceResult<T> = { success: true; data: T } | { success: false; error: { code: string; message: string } };

async function postJson<T>(url: string, body: unknown): Promise<ServiceResult<T>> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res.json() as Promise<ServiceResult<T>>;
}

async function getJson<T>(url: string): Promise<ServiceResult<T>> {
  const res = await fetch(url);
  return res.json() as Promise<ServiceResult<T>>;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  creditProfile: { score: number | null; grade: string | null };
}

export interface LoanRecord {
  id: string;
  productId: string;
  originalAmount: number;
  currentBalance: number;
  status: string;
  monthlyPayment: number;
}

export interface PortfolioSummary {
  loanCount: number;
  totalOriginalAmount: number;
  totalCurrentBalance: number;
}

export function registerUser(input: { email: string; name: string; creditProfile?: { score: number } }) {
  return postJson<UserProfile>('/api/users', input);
}

export function getUserProfile(userId: string) {
  return getJson<UserProfile>(`/api/users/${userId}`);
}

export function applyForLoan(input: {
  userId: string;
  productId: string;
  originalAmount: number;
  interestRate: number;
  termMonths: number;
  startDate: string;
}) {
  return postJson<LoanRecord>('/api/loans', input);
}

export function getLoanPortfolio(userId: string) {
  return getJson<LoanRecord[]>(`/api/users/${userId}/loans`);
}

export function getLoanPortfolioSummary(userId: string) {
  return getJson<PortfolioSummary>(`/api/users/${userId}/loans/summary`);
}
