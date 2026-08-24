/**
 * 고급 리스크 분석 (Day 4 - Task 7 로직을 실제 재사용 가능한 모듈로 추출)
 *
 * src/services/creditSimulation.ts와 동일한 이유로 여기로 옮겼다. 계산 로직은
 * 변경하지 않았다 (Day4에서 이미 검증된 5개 테스트가 그대로 통과해야 한다).
 */
export async function assessRisk(input: any): Promise<any> {
  const creditScore = input.creditScore || 700;
  const income = input.income || 4000000;
  const debt = input.debt || 0;
  const loanAmount = input.loanAmount || 300000000;
  const loanTerm = input.loanTerm || 240;
  const employmentStability = input.employmentStability || 'stable';

  let creditRiskScore = 50;
  if (creditScore >= 800) creditRiskScore = 10;
  else if (creditScore >= 700) creditRiskScore = 25;
  else if (creditScore >= 650) creditRiskScore = 40;
  else creditRiskScore = 70;

  let incomeRiskScore = 30;
  if (employmentStability === 'stable') incomeRiskScore = 15;
  else if (employmentStability === 'moderate') incomeRiskScore = 40;
  else incomeRiskScore = 70;

  const monthlyRate = 3.2 / 12 / 100;
  const monthlyPayment = (loanAmount * (monthlyRate * Math.pow(1 + monthlyRate, loanTerm))) / (Math.pow(1 + monthlyRate, loanTerm) - 1);
  const paymentRatio = (monthlyPayment / income) * 100;
  const repaymentRiskScore = paymentRatio > 50 ? 70 : paymentRatio > 40 ? 50 : 30;

  const systemRiskScore = 25;

  const savingsRate = input.savingsRate || 15;
  const behavioralRiskScore = savingsRate < 10 ? 60 : savingsRate < 20 ? 40 : 20;

  const overallRiskScore = Math.round(
    creditRiskScore * 0.3 + incomeRiskScore * 0.25 + repaymentRiskScore * 0.25 + systemRiskScore * 0.1 + behavioralRiskScore * 0.1
  );

  const basePD = creditScore >= 800 ? 0.5 : creditScore >= 700 ? 1.5 : creditScore >= 650 ? 3.5 : 8.0;
  const pdAdjustment = (overallRiskScore / 100) * 5;
  const probabilityOfDefault = Math.min(100, basePD + pdAdjustment);

  let riskLevel: string;
  if (overallRiskScore < 20) riskLevel = 'very-low';
  else if (overallRiskScore < 35) riskLevel = 'low';
  else if (overallRiskScore < 55) riskLevel = 'medium';
  else if (overallRiskScore < 75) riskLevel = 'high';
  else riskLevel = 'very-high';

  const mitigations = {
    immediate: [] as string[],
    shortTerm: [] as string[],
    mediumTerm: [] as string[]
  };

  if (paymentRatio > 40) {
    mitigations.immediate.push('월상환액 감소 검토 (기간 연장)');
  }
  if (debt > income * 0.3) {
    mitigations.immediate.push('기존 부채 정리');
  }
  if (creditScore < 700) {
    mitigations.shortTerm.push('신용점수 개선 노력');
    mitigations.shortTerm.push('정시 결제 습관 형성');
  }
  if (savingsRate < 15) {
    mitigations.mediumTerm.push('월 저축률 15% 이상 목표 설정');
  }

  return {
    userId: input.userId,
    overallRiskLevel: riskLevel,
    probabilityOfDefault: Math.round(probabilityOfDefault * 100) / 100,
    riskScore: overallRiskScore,
    riskComponents: {
      creditRisk: {
        score: creditRiskScore,
        assessment: creditScore >= 800 ? 'Excellent' : creditScore >= 700 ? 'Good' : 'Poor',
        factors: [`Credit Score: ${creditScore}`]
      },
      incomeRisk: {
        score: incomeRiskScore,
        stabilityIndex: employmentStability === 'stable' ? 0.9 : 0.5,
        factorsOfConcern: []
      },
      repaymentRisk: {
        score: repaymentRiskScore,
        paymentRatio,
        affordabilityIndex: paymentRatio <= 40 ? 0.8 : 0.4
      },
      systemRisk: {
        score: systemRiskScore,
        macroFactors: ['경제 성장률', '금리 환경'],
        industryFactors: [input.industry || '금융']
      },
      behavioralRisk: {
        score: behavioralRiskScore,
        savingsRate,
        creditDiscipline: savingsRate > 20 ? 'Excellent' : 'Moderate'
      }
    },
    scenarioAnalysis: {
      bestCase: {
        description: '신용도 개선 + 수입 증가 시나리오',
        probabilityOfDefault: Math.max(0, probabilityOfDefault * 0.5)
      },
      baseCase: {
        description: '현재 추세 유지',
        probabilityOfDefault
      },
      worstCase: {
        description: '경제 악화 + 실직 시나리오',
        probabilityOfDefault: Math.min(100, probabilityOfDefault * 2)
      }
    },
    mitigationStrategies: mitigations,
    loanDecision: {
      recommendation: riskLevel === 'very-low' || riskLevel === 'low' ? 'approve' : riskLevel === 'medium' ? 'approve-with-conditions' : 'decline',
      reasoning: riskLevel === 'very-low' ? 'Excellent credit profile' : riskLevel === 'low' ? 'Good credit profile' : 'High risk factors',
      conditions:
        riskLevel === 'medium'
          ? {
              requiredCollateral: Math.round(loanAmount * 0.3),
              coApplicantRequired: true,
              rateAdjustment: 1.5,
              maxLoanAmount: loanAmount
            }
          : undefined
    },
    monitoringPlan: {
      checkpoints: [
        {
          period: 6,
          metrics: ['Credit Score', 'Payment Status'],
          triggers: ['Score drop > 50점', 'Payment delay']
        }
      ]
    }
  };
}
