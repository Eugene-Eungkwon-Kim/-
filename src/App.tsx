import { useState, FormEvent } from 'react';
import {
  applyForLoan,
  getLoanPortfolio,
  getLoanPortfolioSummary,
  LoanRecord,
  PortfolioSummary,
  registerUser,
  UserProfile
} from './webApiClient';

const todayIso = () => new Date().toISOString().slice(0, 10);

export default function App() {
  const [email, setEmail] = useState('demo@example.com');
  const [name, setName] = useState('데모 사용자');
  const [creditScore, setCreditScore] = useState(750);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [userError, setUserError] = useState<string | null>(null);

  const [loanAmount, setLoanAmount] = useState(300000000);
  const [interestRate, setInterestRate] = useState(3.2);
  const [termMonths, setTermMonths] = useState(240);
  const [loanError, setLoanError] = useState<string | null>(null);

  const [portfolio, setPortfolio] = useState<LoanRecord[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);

  async function handleRegister(event: FormEvent) {
    event.preventDefault();
    setUserError(null);
    const result = await registerUser({ email, name, creditProfile: { score: creditScore } });
    if (result.success) {
      setUser(result.data);
    } else {
      setUserError(result.error.message);
    }
  }

  async function refreshPortfolio(userId: string) {
    const [portfolioResult, summaryResult] = await Promise.all([getLoanPortfolio(userId), getLoanPortfolioSummary(userId)]);
    if (portfolioResult.success) setPortfolio(portfolioResult.data);
    if (summaryResult.success) setSummary(summaryResult.data);
  }

  async function handleApplyLoan(event: FormEvent) {
    event.preventDefault();
    setLoanError(null);
    if (!user) {
      setLoanError('먼저 사용자를 등록하세요.');
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
      <p style={{ color: '#666' }}>실제 SQLite 백엔드(Fastify + 서비스 계층)와 연동된 최소 데모입니다.</p>

      <section style={{ marginBottom: 32, padding: 16, border: '1px solid #ddd', borderRadius: 8 }}>
        <h2>1. 사용자 등록</h2>
        <form onSubmit={handleRegister}>
          <div>
            <label>
              이메일{' '}
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
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
          <button type="submit">등록</button>
        </form>
        {userError && <p style={{ color: 'crimson' }}>{userError}</p>}
        {user && (
          <p>
            ✅ 등록됨: <strong>{user.name}</strong> ({user.email}) — 신용등급 {user.creditProfile.grade ?? '-'}
          </p>
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
    </div>
  );
}
