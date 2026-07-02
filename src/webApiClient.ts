/**
 * 브라우저에서 Fastify 서버(src/server)를 호출하는 최소 fetch 클라이언트.
 * 서버가 이미 ServiceResult<T> 형태로 응답하므로 여기서는 파싱만 한다.
 */
export type ServiceResult<T> = { success: true; data: T } | { success: false; error: { code: string; message: string } };

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  creditProfile: { score: number | null; grade: string | null };
}

const ACCESS_TOKEN_KEY = 'maars.accessToken';
const REFRESH_TOKEN_KEY = 'maars.refreshToken';
const USER_KEY = 'maars.user';

// Day 9 - Task 4 (δ=1090): 새로고침 시 로그아웃되던 문제를 localStorage 영속화로 해소.
// 모듈 로드 시 1회만 읽으므로, 테스트에서 "로드 시 복원"을 검증하려면
// vi.resetModules() + 동적 import로 이 모듈을 다시 로드해야 한다.
let authToken: string | null = localStorage.getItem(ACCESS_TOKEN_KEY);
let refreshTokenValue: string | null = localStorage.getItem(REFRESH_TOKEN_KEY);

export function setAuthToken(token: string | null): void {
  authToken = token;
  if (token) localStorage.setItem(ACCESS_TOKEN_KEY, token);
  else localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function setRefreshTokenValue(token: string | null): void {
  refreshTokenValue = token;
  if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): UserProfile | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as UserProfile) : null;
}

export function setStoredUser(user: UserProfile | null): void {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}

// --- 강제 로그아웃 구독 (상태 라이브러리 없이 최소 pub/sub) ---
const forcedLogoutListeners = new Set<() => void>();

export function onForcedLogout(callback: () => void): () => void {
  forcedLogoutListeners.add(callback);
  return () => forcedLogoutListeners.delete(callback);
}

function clearAuthState(): void {
  setAuthToken(null);
  setRefreshTokenValue(null);
  setStoredUser(null);
}

function notifyForcedLogout(): void {
  clearAuthState();
  forcedLogoutListeners.forEach((cb) => cb());
}

function authHeaders(): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

/** /api/auth/refresh를 raw fetch로만 호출한다 — request()를 거치면 401 재귀 위험이 생긴다 */
async function tryRefresh(): Promise<boolean> {
  if (!refreshTokenValue) return false;

  const res = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken: refreshTokenValue })
  });
  if (res.status !== 200) return false;

  const body = (await res.json()) as ServiceResult<{ token: string; refreshToken: string }>;
  if (!body.success) return false;

  setAuthToken(body.data.token);
  setRefreshTokenValue(body.data.refreshToken);
  return true;
}

/**
 * 401을 받으면 refresh를 한 번만 시도해 원 요청을 재시도한다. 재시도에서 온 401은
 * 다시 처리하지 않으므로(재귀 없음) 무한 루프 위험이 구조적으로 없다.
 */
async function request<T>(url: string, init: RequestInit): Promise<ServiceResult<T>> {
  const res = await fetch(url, { ...init, headers: { ...init.headers, ...authHeaders() } });

  if (res.status === 401 && authToken) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const retryRes = await fetch(url, { ...init, headers: { ...init.headers, ...authHeaders() } });
      return retryRes.json() as Promise<ServiceResult<T>>;
    }
    notifyForcedLogout();
  }

  return res.json() as Promise<ServiceResult<T>>;
}

async function postJson<T>(url: string, body: unknown): Promise<ServiceResult<T>> {
  return request<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}

async function getJson<T>(url: string): Promise<ServiceResult<T>> {
  return request<T>(url, {});
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

export function registerUser(input: { email: string; name: string; password: string; creditProfile?: { score: number } }) {
  return postJson<UserProfile>('/api/users', input);
}

export function login(email: string, password: string) {
  return postJson<{ token: string; refreshToken: string; user: UserProfile }>('/api/auth/login', { email, password });
}

export async function logout(): Promise<void> {
  if (refreshTokenValue) {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken: refreshTokenValue })
    }).catch(() => undefined); // 서버 호출이 실패해도 클라이언트 로그아웃은 항상 진행한다
  }
  clearAuthState();
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
