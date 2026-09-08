import { useEffect, useState, FormEvent } from 'react';
import NotificationBell from './components/NotificationBell';
import { useNotificationStream } from './hooks/useNotificationStream';
import {
  applyForLoan,
  getLoanPortfolio,
  getLoanPortfolioSummary,
  getStoredUser,
  getTransactionHistory,
  login,
  logout,
  LoanRecord,
  onForcedLogout,
  PortfolioSummary,
  recordTransaction,
  registerUser,
  setAuthToken,
  setRefreshTokenValue,
  setStoredUser,
  TransactionRecord,
  UserProfile
} from './webApiClient';

const todayIso = () => new Date().toISOString().slice(0, 10);

export default function App() {
  const [email, setEmail] = useState('demo@example.com');
  const [password, setPassword] = useState('demo-password-1234');
  const [name, setName] = useState('데모 사용자');
  const [creditScore, setCreditScore] = useState(750);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const [loanAmount, setLoanAmount] = useState(300000000);
  const [interestRate, setInterestRate] = useState(3.2);
  const [termMonths, setTermMonths] = useState(240);
  const [loanError, setLoanError] = useState<string | null>(null);

  const [portfolio, setPortfolio] = useState<LoanRecord[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);

  const [txnType, setTxnType] = useState<TransactionRecord['transactionType']>('deposit');
  const [txnAmount, setTxnAmount] = useState(1000000);
  const [txnError, setTxnError] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);

  // 로그아웃하면 user가 null이 되고, 훅이 스트림을 닫는다.
  const { notifications, unreadCount, status: streamStatus, markRead } = useNotificationStream(user?.id ?? null);

  // Day 9 - Task 4 (δ=1090): 새로고침 시 로그인 상태를 복원하고, 액세스+리프레시
  // 토큰이 모두 만료/무효화되어 webApiClient가 강제 로그아웃을 통지하면 화면에도 반영한다.
  useEffect(() => {
    const stored = getStoredUser();
    if (stored) setUser(stored);

    const unsubscribe = onForcedLogout(() => {
      setUser(null);
      setPortfolio([]);
      setSummary(null);
      setAuthError('세션이 만료되어 로그아웃되었습니다. 다시 로그인해주세요.');
    });
    return unsubscribe;
  }, []);

  function handleLoggedIn(token: string, refreshToken: string, profile: UserProfile) {
    setAuthToken(token);
    setRefreshTokenValue(refreshToken);
    setStoredUser(profile);
    setUser(profile);
  }

  async function handleRegister(event: FormEvent) {
    event.preventDefault();
    setAuthError(null);
    const registerResult = await registerUser({ email, name, password, creditProfile: { score: creditScore } });
    if (!registerResult.success) {
      setAuthError(registerResult.error.message);
      return;
    }
    // 회원가입 직후 같은 자격증명으로 자동 로그인해 토큰을 발급받는다
    const loginResult = await login(email, password);
    if (loginResult.success) {
      handleLoggedIn(loginResult.data.token, loginResult.data.refreshToken, loginResult.data.user);
    } else {
      setAuthError(loginResult.error.message);
    }
  }

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setAuthError(null);
    const result = await login(email, password);
    if (result.success) {
      handleLoggedIn(result.data.token, result.data.refreshToken, result.data.user);
    } else {
      setAuthError(result.error.message);
    }
  }

  async function handleLogout() {
    await logout();
    setUser(null);
    setPortfolio([]);
    setSummary(null);
  }

  async function refreshPortfolio(userId: string) {
    const [portfolioResult, summaryResult] = await Promise.all([getLoanPortfolio(userId), getLoanPortfolioSummary(userId)]);
    if (portfolioResult.success) setPortfolio(portfolioResult.data);
    if (summaryResult.success) setSummary(summaryResult.data);
  }

  async function refreshTransactions(userId: string) {
    const result = await getTransactionHistory(userId);
    if (result.success) setTransactions(result.data);
  }

  async function handleRecordTransaction(event: FormEvent) {
    event.preventDefault();
    setTxnError(null);
    if (!user) {
      setTxnError('먼저 로그인하세요.');
      return;
    }
    const result = await recordTransaction({ userId: user.id, transactionType: txnType, amount: txnAmount, occurredAt: todayIso() });
    if (result.success) {
      await refreshTransactions(user.id);
    } else {
      setTxnError(result.error.message);
    }
  }

  async function handleApplyLoan(event: FormEvent) {
    event.preventDefault();
    setLoanError(null);
    if (!user) {
      setLoanError('먼저 로그인하세요.');
      return;
    }
    const result = await applyForLoan({
      userId: user.id,
      productId: 'standard-loan-1',
      originalAmount: loanAmount,
      interestRate,
      termMonths,
      startDate: todayIso()
    });
    if (result.success) {
      await refreshPortfolio(user.id);
    } else {
      setLoanError(result.error.message);
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: '40px auto', fontFamily: 'sans-serif', lineHeight: 1.6 }}>
      <h1>MAARS 데모</h1>
      <p style={{ color: '#666' }}>실제 SQLite 백엔드(Fastify + 서비스 계층, JWT 인증)와 연동된 최소 데모입니다.</p>

      <section style={{ marginBottom: 32, padding: 16, border: '1px solid #ddd', borderRadius: 8 }}>
        <h2>1. 회원가입 / 로그인</h2>
        {user ? (
          <p>
            ✅ 로그인됨: <strong>{user.name}</strong> ({user.email}) — 신용등급 {user.creditProfile.grade ?? '-'}{' '}
            <button onClick={handleLogout}>로그아웃</button>
          </p>
        ) : (
          <>
            <form onSubmit={handleRegister}>
              <div>
                <label>
                  이메일{' '}
                  <input value={email} onChange={(e) => setEmail(e.target.value)} />
                </label>
              </div>
              <div>
                <label>
                  비밀번호{' '}
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                </label>
              </div>
              <div>
                <label>
                  이름{' '}
                  <input value={name} onChange={(e) => setName(e.target.value)} />
                </label>
              </div>
              <div>
                <label>
                  신용점수{' '}
                  <input type="number" value={creditScore} onChange={(e) => setCreditScore(Number(e.target.value))} />
                </label>
              </div>
              <button type="submit">회원가입 (자동 로그인)</button>
              <button type="button" onClick={handleLogin} style={{ marginLeft: 8 }}>
                이미 계정이 있다면 로그인
              </button>
            </form>
            {authError && <p style={{ color: 'crimson' }}>{authError}</p>}
          </>
        )}
      </section>

      <section style={{ marginBottom: 32, padding: 16, border: '1px solid #ddd', borderRadius: 8 }}>
        <h2>2. 대출 신청</h2>
        <form onSubmit={handleApplyLoan}>
          <div>
            <label>
              대출금액{' '}
              <input type="number" value={loanAmount} onChange={(e) => setLoanAmount(Number(e.target.value))} />
            </label>
          </div>
          <div>
            <label>
              금리(%){' '}
              <input type="number" step="0.1" value={interestRate} onChange={(e) => setInterestRate(Number(e.target.value))} />
            </label>
          </div>
          <div>
            <label>
              기간(개월){' '}
              <input type="number" value={termMonths} onChange={(e) => setTermMonths(Number(e.target.value))} />
            </label>
          </div>
          <button type="submit" disabled={!user}>
            신청
          </button>
        </form>
        {loanError && <p style={{ color: 'crimson' }}>{loanError}</p>}
      </section>

      <section style={{ padding: 16, border: '1px solid #ddd', borderRadius: 8 }}>
        <h2>3. 대출 포트폴리오</h2>
        <button onClick={() => user && refreshPortfolio(user.id)} disabled={!user}>
          새로고침
        </button>
        {summary && (
          <p>
            총 {summary.loanCount}건 · 원금 합계 {summary.totalOriginalAmount.toLocaleString()}원 · 잔액 합계{' '}
            {summary.totalCurrentBalance.toLocaleString()}원
          </p>
        )}
        <ul>
          {portfolio.map((loan) => (
            <li key={loan.id}>
              {loan.productId}: 잔액 {loan.currentBalance.toLocaleString()}원 / 월상환액{' '}
              {loan.monthlyPayment.toLocaleString()}원 ({loan.status})
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: 32, padding: 16, border: '1px solid #ddd', borderRadius: 8 }}>
        <h2>4. 거래 내역</h2>
        <form onSubmit={handleRecordTransaction}>
          <div>
            <label>
              유형{' '}
              <select value={txnType} onChange={(e) => setTxnType(e.target.value as TransactionRecord['transactionType'])}>
                <option value="deposit">입금</option>
                <option value="withdrawal">출금</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              금액{' '}
              <input type="number" value={txnAmount} onChange={(e) => setTxnAmount(Number(e.target.value))} />
            </label>
          </div>
          <button type="submit" disabled={!user}>
            기록
          </button>
          <button type="button" onClick={() => user && refreshTransactions(user.id)} disabled={!user} style={{ marginLeft: 8 }}>
            새로고침
          </button>
        </form>
        {txnError && <p style={{ color: 'crimson' }}>{txnError}</p>}
        <ul>
          {transactions.map((txn) => (
            <li key={txn.id}>
              [{txn.occurredAt}] {txn.transactionType === 'deposit' ? '입금' : txn.transactionType}: {txn.amount.toLocaleString()}원 (
              {txn.status})
            </li>
          ))}
        </ul>
      </section>

      {user && (
        <NotificationBell
          notifications={notifications}
          unreadCount={unreadCount}
          status={streamStatus}
          onMarkRead={(id) => void markRead(id)}
        />
      )}
    </div>
  );
}
