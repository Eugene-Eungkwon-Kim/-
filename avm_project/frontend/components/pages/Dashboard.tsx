'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { TrendingUp, AlertCircle, CheckCircle, Wifi, WifiOff } from 'lucide-react'
import SummaryCard from '@/components/ui/SummaryCard'
import StatisticCard from '@/components/ui/StatisticCard'
import LineChart from '@/components/ui/LineChart'
import PerformanceTable from '@/components/ui/PerformanceTable'
import { useWebSocket } from '@/lib/useWebSocket'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface DashboardData {
  ensemble_r2: number
  ensemble_rmse: number
  ensemble_mae: number
  trend: any[]
  recent_trainings: any[]
  statistics?: any
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData>({
    ensemble_r2: 0.8450,
    ensemble_rmse: 55200000,
    ensemble_mae: 42300000,
    trend: [],
    recent_trainings: [],
  })
  const [loading, setLoading] = useState(true)

  const handleWebSocketMessage = useCallback((message: any) => {
    if (message.type === 'dashboard_update') {
      // WebSocket에서 수신한 데이터로 업데이트
      if (message.trend_data && message.trend_data.length > 0) {
        const trend = message.trend_data.map((item: any) => ({
          week: item.week,
          r2: item.r2,
        }))

        if (message.latest_result) {
          setData((prev) => ({
            ...prev,
            ensemble_r2: message.latest_result.ensemble?.r2 || prev.ensemble_r2,
            ensemble_rmse: message.latest_result.ensemble?.rmse || prev.ensemble_rmse,
            ensemble_mae: message.latest_result.ensemble?.mae || prev.ensemble_mae,
            trend: trend,
          }))
        } else {
          setData((prev) => ({
            ...prev,
            trend: trend,
          }))
        }
      }
      setLoading(false)
    }
  }, [])

  const { isConnected, isReconnecting, send } = useWebSocket(
    `${API_BASE_URL}/ws/dashboard`,
    {
      onMessage: handleWebSocketMessage,
      onError: (error) => {
        console.error('WebSocket error:', error)
        setLoading(false)
      },
      onClose: () => {
        console.log('WebSocket connection closed')
      },
    }
  )

  // 초기 데이터 로드
  useEffect(() => {
    // 데모 데이터 설정
    const demoData: DashboardData = {
      ensemble_r2: 0.8450,
      ensemble_rmse: 55200000,
      ensemble_mae: 42300000,
      trend: [
        { week: '1주', r2: 0.8200 },
        { week: '2주', r2: 0.8220 },
        { week: '3주', r2: 0.8250 },
        { week: '4주', r2: 0.8280 },
        { week: '5주', r2: 0.8310 },
        { week: '6주', r2: 0.8340 },
        { week: '7주', r2: 0.8360 },
        { week: '8주', r2: 0.8380 },
        { week: '9주', r2: 0.8410 },
        { week: '10주', r2: 0.8450 },
      ],
      recent_trainings: [
        { date: '2026-06-19', status: 'success', r2: 0.8450, rmse: 55200000, duration: '12분' },
        { date: '2026-06-12', status: 'success', r2: 0.8420, rmse: 55800000, duration: '11분' },
        { date: '2026-06-05', status: 'success', r2: 0.8380, rmse: 56500000, duration: '13분' },
        { date: '2026-05-29', status: 'warning', r2: 0.8340, rmse: 57200000, duration: '12분' },
        { date: '2026-05-22', status: 'success', r2: 0.8310, rmse: 57500000, duration: '11분' },
      ],
    }
    setData(demoData)
    setLoading(false)
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

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <SummaryCard
          title="앙상블 R² 점수"
          value={data?.ensemble_r2.toFixed(4) || '0.0000'}
          change={0.12}
          icon="chart"
          color="blue"
        />
        <SummaryCard
          title="평균 오차 (RMSE)"
          value={`${Math.round(data?.ensemble_rmse || 0).toLocaleString()}원`}
          change={-2.6}
          icon="trending"
          color="green"
        />
        <SummaryCard
          title="평균 절대 오차 (MAE)"
          value={`${Math.round(data?.ensemble_mae || 0).toLocaleString()}원`}
          change={-1.8}
          icon="target"
          color="purple"
        />
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
        <div className="mb-6">
          <h2 className="text-h4 text-neutral-900 font-semibold">R² 추세 (10주)</h2>
          <p className="text-body-sm text-neutral-600 mt-1">주간별 앙상블 모델 성능 변화</p>
        </div>
        <LineChart data={data?.trend || []} />
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatisticCard
          label="최고 성능"
          value="0.8450"
          subtext="2주 전 대비 +0.63%"
          icon="trending"
        />
        <StatisticCard
          label="평균 성능"
          value="0.8325"
          subtext="전체 기간"
          icon="chart"
        />
        <StatisticCard
          label="개선도"
          value="2.7%"
          subtext="1개월 기준"
          icon="up"
        />
        <StatisticCard
          label="학습 횟수"
          value="52"
          subtext="1년 누적"
          icon="activity"
        />
      </div>

      {/* Recent Trainings Table */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
        <div className="mb-6">
          <h2 className="text-h4 text-neutral-900 font-semibold">최근 학습 기록</h2>
          <p className="text-body-sm text-neutral-600 mt-1">지난 10주간의 재학습 이력</p>
        </div>
        <PerformanceTable data={data?.recent_trainings || []} />
      </div>

      {/* Alerts Section */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
        <div className="mb-6">
          <h2 className="text-h4 text-neutral-900 font-semibold">알림 및 권장사항</h2>
        </div>
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 bg-success-50 border border-success-200 rounded-lg">
            <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-success-900">성능 정상</p>
              <p className="text-sm text-success-700">R² 0.8450은 목표값(0.95) 대비 양호한 성능입니다.</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-warning-50 border border-warning-200 rounded-lg">
            <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-warning-900">데이터 품질</p>
              <p className="text-sm text-warning-700">주유소 데이터 (Opinet) 99.6% 수집 완료</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
