'use client'

import React, { useState, useCallback } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingDown,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useWebSocket } from '@/lib/useWebSocket'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface HealthStatus {
  status: string
  latest_result?: any
  degradation?: any
  statistics?: any
  next_training?: any
  timestamp: string
}

interface DegradationAlert {
  detected: boolean
  type: string
  previous_r2: number
  latest_r2: number
  degradation_percentage: number
  threshold: number
  timestamp: string
}

export default function RealtimeMonitoring() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>({
    status: 'healthy',
    timestamp: new Date().toISOString(),
  })
  const [alerts, setAlerts] = useState<DegradationAlert[]>([])
  const [isMonitoring, setIsMonitoring] = useState(false)

  const handleWebSocketMessage = useCallback((message: any) => {
    if (message.type === 'system_health') {
      setHealthStatus(message.health_status || message)
      setIsMonitoring(true)
    } else if (message.type === 'degradation_alert') {
      // 새로운 알림 추가
      setAlerts((prev) => [
        {
          ...message.alert,
          timestamp: message.timestamp,
        },
        ...prev.slice(0, 4), // 최근 5개만 유지
      ])
    }
  }, [])

  const { isConnected, isReconnecting } = useWebSocket(
    `${API_BASE_URL}/ws/monitoring`,
    {
      onMessage: handleWebSocketMessage,
      onError: (error) => {
        console.error('Monitoring WebSocket error:', error)
      },
    }
  )

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'warning':
        return 'warning'
      case 'error':
        return 'error'
      default:
        return 'neutral'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'healthy':
        return '정상'
      case 'warning':
        return '경고'
      case 'error':
        return '오류'
      default:
        return '알 수 없음'
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h2 text-neutral-900 font-semibold">실시간 모니터링</h1>
          <p className="text-body text-neutral-600 mt-1">
            시스템 상태 및 성능 이상 감지
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-neutral-50 rounded-lg border border-neutral-200">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-success-500" />
              <span className="text-sm text-success-600 font-medium">모니터링 중</span>
            </>
          ) : isReconnecting ? (
            <>
              <WifiOff className="w-4 h-4 text-warning-500 animate-pulse" />
              <span className="text-sm text-warning-600 font-medium">재연결 중...</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-error-500" />
              <span className="text-sm text-error-600 font-medium">모니터링 대기</span>
            </>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
        <div className="mb-6">
          <h2 className="text-h4 text-neutral-900 font-semibold">
            시스템 상태
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Status Card */}
          <div className="p-6 rounded-lg border-2 border-neutral-200 bg-neutral-50">
            <div className="flex items-center gap-4">
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center bg-${getStatusColor(
                  healthStatus.status
                )}-100`}
              >
                {healthStatus.status === 'healthy' ? (
                  <CheckCircle className={`w-6 h-6 text-${getStatusColor(healthStatus.status)}-600`} />
                ) : (
                  <AlertTriangle
                    className={`w-6 h-6 text-${getStatusColor(healthStatus.status)}-600`}
                  />
                )}
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">전체 상태</p>
                <p className={`text-h4 font-semibold text-${getStatusColor(healthStatus.status)}-600`}>
                  {getStatusLabel(healthStatus.status)}
                </p>
              </div>
            </div>
          </div>

          {/* Latest Result Card */}
          {healthStatus.latest_result && (
            <div className="p-6 rounded-lg border-2 border-neutral-200 bg-neutral-50">
              <p className="text-sm text-neutral-600 mb-2">최신 결과</p>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-neutral-600">R² 점수:</span>
                  <span className="text-sm font-bold text-primary-600">
                    {healthStatus.latest_result.ensemble?.r2?.toFixed(4) || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-neutral-600">상태:</span>
                  <span
                    className={`text-sm font-bold text-${
                      healthStatus.latest_result.status === 'success'
                        ? 'success'
                        : 'warning'
                    }-600`}
                  >
                    {healthStatus.latest_result.status === 'success'
                      ? '성공'
                      : '경고'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Next Training */}
        {healthStatus.next_training && (
          <div className="mt-6 p-4 rounded-lg bg-info-50 border border-info-200">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-info-600" />
              <div>
                <p className="text-sm font-medium text-info-900">
                  다음 자동 학습
                </p>
                <p className="text-xs text-info-700 mt-1">
                  {healthStatus.next_training.schedule?.day} {healthStatus.next_training.schedule?.time} 예정
                  ({healthStatus.next_training.days_remaining}일 남음)
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
          <div className="mb-6">
            <h2 className="text-h4 text-neutral-900 font-semibold flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-warning-600" />
              최근 알림
            </h2>
          </div>

          <div className="space-y-3">
            {alerts.map((alert, index) => (
              <div
                key={index}
                className="p-4 rounded-lg border border-warning-200 bg-warning-50"
              >
                <div className="flex items-start gap-3">
                  <TrendingDown className="w-5 h-5 text-warning-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-warning-900">
                      성능 저하 감지
                    </p>
                    <div className="text-sm text-warning-700 mt-2 space-y-1">
                      <p>
                        이전 R²: {alert.previous_r2?.toFixed(4)} → 현재 R²:{' '}
                        {alert.latest_r2?.toFixed(4)}
                      </p>
                      <p>
                        저하율: {alert.degradation_percentage?.toFixed(2)}% (임계값:{' '}
                        {((1 - alert.threshold) * 100).toFixed(1)}%)
                      </p>
                      <p className="text-xs text-warning-600 mt-2">
                        {new Date(alert.timestamp).toLocaleString('ko-KR')}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Statistics */}
      {healthStatus.statistics && (
        <div className="bg-white rounded-lg shadow-sm border border-neutral-300 p-6">
          <div className="mb-6">
            <h2 className="text-h4 text-neutral-900 font-semibold">통계 정보</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border border-neutral-200 bg-neutral-50">
              <p className="text-sm text-neutral-600 mb-2">총 학습 횟수</p>
              <p className="text-h4 font-bold text-neutral-900">
                {healthStatus.statistics.total_trainings || 0}
              </p>
            </div>
            <div className="p-4 rounded-lg border border-neutral-200 bg-neutral-50">
              <p className="text-sm text-neutral-600 mb-2">성공률</p>
              <p className="text-h4 font-bold text-success-600">
                {healthStatus.statistics.success_rate?.toFixed(1) || 0}%
              </p>
            </div>
            <div className="p-4 rounded-lg border border-neutral-200 bg-neutral-50">
              <p className="text-sm text-neutral-600 mb-2">평균 R²</p>
              <p className="text-h4 font-bold text-primary-600">
                {healthStatus.statistics.average_r2?.toFixed(4) || 'N/A'}
              </p>
            </div>
            <div className="p-4 rounded-lg border border-neutral-200 bg-neutral-50">
              <p className="text-sm text-neutral-600 mb-2">최고 R²</p>
              <p className="text-h4 font-bold text-primary-600">
                {healthStatus.statistics.max_r2?.toFixed(4) || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      )}

      {!isMonitoring && (
        <div className="bg-info-50 border border-info-200 rounded-lg p-6">
          <p className="text-sm text-info-700">
            WebSocket 연결을 대기 중입니다. 연결되면 실시간 데이터가 표시됩니다.
          </p>
        </div>
      )}
    </div>
  )
}
