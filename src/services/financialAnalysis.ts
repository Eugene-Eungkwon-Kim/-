/**
 * 재정 분석 & 계획 (Day 4 - Task 5 로직을 실제 재사용 가능한 모듈로 추출)
 *
 * src/services/creditSimulation.ts, riskAssessment.ts와 동일한 이유로 여기로
 * 옮겼다 (Day6에서 이 둘만 추출하고 financialAnalysis는 남겨뒀던 것을 Day7에서 마저 처리).
 * 계산 로직은 변경하지 않았다 (Day4에서 이미 검증된 5개 테스트가 그대로 통과해야 한다).
 */
export async function analyzeFinancials(input: any): Promise<any> {
  const monthlyIncome = input.monthlyIncome || 4000000;
  const monthlyExpenses = input.monthlyExpenses || 1500000;
  const totalDebt = input.totalDebt || 100000000;
  const totalAssets = input.totalAssets || 500000000;

  const monthlyLoanPayments = totalDebt / 240;
  const monthlySurplus = monthlyIncome - monthlyExpenses - monthlyLoanPayments;
  const debtToIncomeRatio = totalDebt / (monthlyIncome * 12);
  const assetToDebtRatio = totalAssets / totalDebt;
  const netWorth = totalAssets - totalDebt;

  const healthScore = Math.round(Math.max(0, 100 - debtToIncomeRatio * 50));
  const healthGrade = healthScore >= 80 ? 'A' : healthScore >= 60 ? 'B' : healthScore >= 40 ? 'C' : 'F';

  return {
    userId: input.userId,
    currentStatus: {
      monthlyIncome,
      monthlyExpenses,
      monthlyLoanPayments: Math.round(monthlyLoanPayments),
      monthlySurplus: Math.round(monthlySurplus),
      totalDebt,
      totalAssets,
      netWorth,
      debtToIncomeRatio: Math.round(debtToIncomeRatio * 1000) / 1000,
      assetToDebtRatio: Math.round(assetToDebtRatio * 100) / 100
    },
    financialHealthScore: healthScore,
    healthGrade,
    healthBreakdown: {
      debtRatioScore: Math.max(0, 100 - debtToIncomeRatio * 100),
      surplusCashScore: Math.min(100, (monthlySurplus / monthlyIncome) * 300),
      assetScore: Math.min(100, assetToDebtRatio * 20),
      creditScore: Math.min(100, 100 - debtToIncomeRatio * 50)
    },
    savingsAnalysis: {
      currentMonthlySavings: Math.round(Math.max(0, monthlySurplus)),
      projectedSavings12Months: Math.round(Math.max(0, monthlySurplus) * 12),
      savingsGoal: 100000000,
      savingsGoalMonths: Math.max(0, monthlySurplus) > 0 ? Math.ceil(100000000 / Math.max(0, monthlySurplus)) : 999,
      monthlyRequiredSavings: Math.round(100000000 / 36),
      achievable: Math.max(0, monthlySurplus) >= 100000000 / 36
    },
    debtRepaymentPlan: {
      totalDebt,
      quickestPayoffMonths: Math.ceil(totalDebt / (monthlyIncome * 0.5)),
      balancedPayoffMonths: Math.ceil(totalDebt / (monthlyIncome * 0.2)),
      debtFreeDate: new Date(Date.now() + Math.ceil(totalDebt / (monthlyIncome * 0.2)) * 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0],
      estimatedInterestSavings: Math.round(monthlyIncome * 0.1 * Math.ceil(totalDebt / (monthlyIncome * 0.2)) * 0.3)
    },
    recommendations: [healthScore > 70 ? '현재 추세 유지' : '재정 개선 필요']
  };
}
