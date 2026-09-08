'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { AlertCircle, CheckCircle, Wifi, WifiOff, XCircle } from 'lucide-react'
import SummaryCard from '@/components/ui/SummaryCard'
import StatisticCard from '@/components/ui/StatisticCard'
import LineChart from '@/components/ui/LineChart'
import PerformanceTable from '@/components/ui/PerformanceTable'
import { useWebSocket } from '@/lib/useWebSocket'
import { dashboardAPI, apiUtils } from '@/lib/api'

// 이 페이지는 하드코딩된 데모값(R²=0.8450, 10주 추세 등)을 항상 보여주고
// 있었다 — dashboardAPI가 lib/api.ts에 있었는데 아무도 호출하지 않았다.
// 백엔드의 /dashboard/* 도 같은 이유로 고정 예시값을 돌려주고 있었는데,
// logs/retrain_history.jsonl 을 실제로 읽는 monitor는 이미 있었다(웹소켓
// 브로드캐스트 루프만 그걸 썼다) — 이번에 REST 쪽도 같은 소스에 연결했다.

interface TrendPoint {
  week: string
  r2: number
}

interface Training {
  date: string
  status: string
  r2: number | null
  rmse: number | null
  duration: string | null
}

interface Statistics {
  highest_r2: number | null
  average_r2: number | null
  improvement: string | null
  training_count: number
}

interface DashboardState {
  status: string
  ensembleR2: number | null
  ensembleRmse: number | null
  ensembleMae: number | null
  changeRate: number | null
  trend: TrendPoint[]
  recentTrainings: Training[]
  statistics: Statistics | null
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const [data, setData] = useState<DashboardState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const handleWebSocketMessage = useCallback((message: any) => {
    if (message.type !== 'dashboard_update') return
    setData((prev) => {
      if (!prev) return prev
      const trend = (message.trend_data ?? []).map((item: any) => ({ week: item.week, r2: item.r2 }))
      const ensemble = message.latest_result?.ensemble
      return {
        ...prev,
        ensembleR2: ensemble?.r2 ?? prev.ensembleR2,
        ensembleRmse: ensemble?.rmse ?? prev.ensembleRmse,
        ensembleMae: ensemble?.mae ?? prev.ensembleMae,
        trend: trend.length > 0 ? trend : prev.trend,
      }
    })
  }, [])

  const { isConnected, isReconnecting } = useWebSocket(`${API_BASE_URL}/ws/dashboard`, {
    onMessage: handleWebSocketMessage,
    onError: (err) => console.error('WebSocket error:', err),
  })

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [summaryRes, trendRes, trainingsRes, statsRes] = await Promise.all([
          dashboardAPI.getSummary(),
          dashboardAPI.getTrendData(10),
          dashboardAPI.getRecentTrainings(10),
          dashboardAPI.getStatistics(),
        ])
        if (cancelled) return
        const s = summaryRes.data
        setData({
          status: s.status,
          ensembleR2: s.ensemble_r2,
          ensembleRmse: s.ensemble_rmse,
          ensembleMae: s.ensemble_mae,
          changeRate: s.change_rate,
          trend: trendRes.data.data,
          recentTrainings: trainingsRes.data.data,
          statistics: statsRes.data,
        })
      } catch (err) {
        if (!cancelled) setError(apiUtils.handleError(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <p className="text-neutral-600">데이터 로드 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 p-4 bg-error-50 border border-error-200 rounded-lg">
          <XCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-error-900">대시보드 데이터 조회 실패</p>
            <p className="text-sm text-error-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  const noData = !data || data.status === 'no_data'
  const fmtR2 = (v: number | null) => (v != null ? v.toFixed(4) : '—')
  const fmtWon = (v: number | null) => (v != null ? `${Math.round(v).toLocaleString()}원` : '—')

  return (
    <div className="p-6 space-y-6">
      {/* Connection Status Indicator */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-h2 text-neutral-900 font-semibold">대시보드</h1>
          <p className="text-body text-neutral-600 mt-1">모델 성능 모니터링 및 분석</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-neutral-50 rounded-lg border border-neutral-200">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-success-500" />
              <span className="text-sm text-success-600 font-medium">실시간 연결</span>
            </>
          ) : isReconnecting ? (
            <>
              <WifiOff className="w-4 h-4 text-warning-500 animate-pulse" />
              <span className="text-sm text-warning-600 font-medium">재연결 중...</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-error-500" />
              <span className="text-sm text-error-600 font-medium">연결 대기</span>
            </>
          )}
        </div>
      </div>

      {noData && (
        <div className="flex items-start gap-3 p-4 bg-warning-50 border border-warning-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-warning-900">재학습 이력 없음</p>
            <p className="text-sm text-warning-700 mt-1">
              <code className="bg-white px-1 rounded">scripts/weekly_retrain_scheduler.py</code>
              {' '}실행 후 <code className="bg-white px-1 rounded">logs/retrain_history.jsonl</code>에
              기록이 쌓이면 아래가 채워집니다.
            </p>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <SummaryCard
          title="앙상블 R² 점수"
          value={fmtR2(data?.ensembleR2 ?? null)}
          change={data?.changeRate ?? null}
          icon="chart"
          color="blue"
        />
        <SummaryCard
          title="평균 오차 (RMSE)"
          value={fmtWon(data?.ensembleRmse ?? null)}
          icon="trending"
          color="green"
        />
        <SummaryCard
          title="평균 절대 오차 (MAE)"
          value={fmtWon(data?.ensembleMae ?? null)}
          icon="target"
          color="purple"
        />
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
        <div className="mb-6">
          <h2 className="text-h4 text-neutral-900 font-semibold">R² 추세 (최근 10회)</h2>
          <p className="text-body-sm text-neutral-600 mt-1">재학습 이력 기준 앙상블 모델 성능 변화</p>
        </div>
        {data && data.trend.length > 0 ? (
          <LineChart data={data.trend} />
        ) : (
          <div className="h-[300px] flex items-center justify-center text-neutral-400 text-sm">
            표시할 추세 데이터가 없습니다
          </div>
        )}
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatisticCard
          label="최고 성능"
          value={fmtR2(data?.statistics?.highest_r2 ?? null)}
          subtext="전체 이력 기준"
          icon="trending"
        />
        <StatisticCard
          label="평균 성능"
          value={fmtR2(data?.statistics?.average_r2 ?? null)}
          subtext="전체 이력 기준"
          icon="chart"
        />
        <StatisticCard
          label="성공률"
          value={data?.statistics?.improvement ?? '—'}
          subtext="전체 재학습 대비"
          icon="up"
        />
        <StatisticCard
          label="학습 횟수"
          value={String(data?.statistics?.training_count ?? 0)}
          subtext="누적"
          icon="activity"
        />
      </div>

      {/* Recent Trainings Table */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
        <div className="mb-6">
          <h2 className="text-h4 text-neutral-900 font-semibold">최근 학습 기록</h2>
          <p className="text-body-sm text-neutral-600 mt-1">가장 최근 재학습 이력부터 표시</p>
        </div>
        {data && data.recentTrainings.length > 0 ? (
          <PerformanceTable data={data.recentTrainings} />
        ) : (
          <p className="text-sm text-neutral-400 py-8 text-center">학습 기록이 없습니다</p>
        )}
      </div>

      {/* Alerts Section */}
      {data && data.status === 'failed' && (
        <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
          <div className="flex items-start gap-3 p-3 bg-error-50 border border-error-200 rounded-lg">
            <AlertCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-error-900">최근 재학습 실패</p>
              <p className="text-sm text-error-700">로그를 확인하세요: logs/weekly_retrain.log</p>
            </div>
          </div>
        </div>
      )}
      {data && data.status === 'success' && (
        <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
          <div className="flex items-start gap-3 p-3 bg-success-50 border border-success-200 rounded-lg">
            <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-success-900">최근 재학습 성공</p>
              <p className="text-sm text-success-700">R² {fmtR2(data.ensembleR2)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
