/**
 * 신용도 시뮬레이션 (Day 4 - Task 2 로직을 실제 재사용 가능한 모듈로 추출)
 *
 * 원래 src/services/__tests__/handlers.spec.ts 안에 테스트 전용 함수로 갇혀 있던
 * 로직이다. Day 6 financialAnalyticsService가 이 함수를 실제 DB 상태(현재
 * 신용점수)와 연결해 호출할 수 있도록 여기로 옮겼다. 계산 로직 자체는
 * 변경하지 않았다 (Day4에서 이미 검증된 5개 테스트가 그대로 통과해야 한다).
 */
export async function simulateCreditScore(input: any): Promise<any> {
  const userId = input.userId || 'user-001';
  const currentScore = input.currentScore || 750;
  const scenario = input.scenarios?.scenario || 'normal';
  const duration = input.scenarios?.duration || 12;
  const params = input.parameters || {};

  const scenarioDefaults = {
    ideal: { paymentSuccess: 100, debtChangeRate: -1 },
    normal: { paymentSuccess: 90, debtChangeRate: -0.5 },
    risky: { paymentSuccess: 70, debtChangeRate: 0.5 },
    crisis: { paymentSuccess: 50, debtChangeRate: 1.5 }
  };

  const defaults = scenarioDefaults[scenario as keyof typeof scenarioDefaults] || scenarioDefaults.normal;
  const paymentSuccess = params.paymentSuccess ?? defaults.paymentSuccess;
  const debtChangeRate = params.debtChangeRate ?? defaults.debtChangeRate;
  const inquiryFrequency = params.inquiryFrequency ?? 2;

  const getGrade = (score: number): string => {
    if (score >= 900) return 'A+';
    if (score >= 800) return 'A';
    if (score >= 700) return 'B+';
    if (score >= 600) return 'B';
    if (score >= 500) return 'C';
    if (score >= 400) return 'D';
    return 'F';
  };

  const results: any[] = [];
  let score = currentScore;
  const scores: number[] = [score];

  for (let month = 1; month <= duration; month++) {
    let monthScore = score;
    const events: string[] = [];
    let scoreChange = 0;
    let debtChange = debtChangeRate;

    const paymentSuccess_ = scenario === 'ideal' ? true : scenario === 'crisis' ? false : Math.random() * 100 < paymentSuccess;
    if (paymentSuccess_) {
      monthScore += 5;
      events.push('결제 성공');
      debtChange -= 1;
    } else {
      monthScore -= 20;
      events.push('연체 발생');
      debtChange += 0.5;
    }

    let inquiries = 0;
    if (scenario === 'ideal') inquiries = 0;
    else if (scenario === 'crisis') inquiries = 4;
    else inquiries = Math.floor(inquiryFrequency * (Math.random() + 0.5));

    if (inquiries > 0) {
      monthScore -= inquiries * 2;
      events.push(`신용조회 ${inquiries}회`);
    }

    const volatility = scenario === 'ideal' || scenario === 'crisis' ? 0 : (Math.random() - 0.5) * 10;
    monthScore += volatility;

    monthScore = Math.max(300, Math.min(999, Math.round(monthScore)));
    scoreChange = monthScore - score;
    score = monthScore;
    scores.push(score);

    results.push({
      month,
      score: monthScore,
      grade: getGrade(monthScore),
      debtChange: Math.round(debtChange * 10) / 10,
      events,
      scoreChange
    });
  }

  const bestMonth = results.reduce((best: any, r: any) => (r.score > best.score ? r : best), results[0]);
  const worstMonth = results.reduce((worst: any, r: any) => (r.score < worst.score ? r : worst), results[0]);
  const averageScore = Math.round(scores.reduce((a: number, b: number) => a + b) / scores.length);
  const finalScoreChange = score - currentScore;

  let trend = 'stable';
  if (finalScoreChange > 30) trend = 'improving';
  else if (finalScoreChange < -30) trend = 'declining';

  const riskLevel = score < 500 ? 'high' : score < 700 ? 'medium' : 'low';

  const recommendations = [
    trend === 'declining' ? '신용도 회복에 집중하세요' : '현재 추세를 유지하세요',
    riskLevel === 'high' ? '우발적 부채 발생 자제' : '신용도 관리 지속',
    score < 700 ? '정기적인 신용보험료 검토' : '우수 고객 혜택 활용'
  ];

  return {
    userId,
    currentScore,
    simulationPeriod: duration,
    scenario,
    results,
    summary: {
      finalScore: score,
      finalGrade: getGrade(score),
      scoreChange: finalScoreChange,
      bestMonth,
      worstMonth,
      averageScore,
      trend,
      riskLevel
    },
    recommendations
  };
}
