'use client'

import React, { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle, HelpCircle, XCircle } from 'lucide-react'
import {
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { dataAPI, apiUtils } from '@/lib/api'

// 이 페이지는 /data/comparable-sales/* (실측 — scripts/collect_all_transactions.py
// 가 적재한 실제 행 수) 를 그린다. 이전 버전은 5,000/850/1200 같은 하드코딩된
// 데모값을 항상 보여줘 "실제로 수집된 게 있는지"를 알 수 없었다.

interface SummaryResponse {
  total_rows: number
  by_property_type: { name: string; count: number }[]
  by_region: { name: string; count: number }[]
}

interface PriceDistributionResponse {
  data: { range: string; count: number }[]
}

interface RegionDistributionResponse {
  data: { name: string; value: number }[]
}

type QualityStatus = 'no_data' | 'excellent' | 'good' | 'needs_review'

interface QualityResponse {
  total_rows: number
  missing_values: number
  missing_percentage: number
  outliers: number
  outlier_percentage: number
  quality_score: number
  status: QualityStatus
}

const PIE_COLORS = ['#2196F3', '#64B5F6', '#1565C0', '#0D47A1', '#90CAF9', '#42A5F5']

const STATUS_LABEL: Record<QualityStatus, string> = {
  no_data: '데이터 없음',
  excellent: '매우 우수',
  good: '양호',
  needs_review: '확인 필요',
}

export default function DataAnalysis() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null)
  const [priceDist, setPriceDist] = useState<PriceDistributionResponse | null>(null)
  const [regionDist, setRegionDist] = useState<RegionDistributionResponse | null>(null)
  const [quality, setQuality] = useState<QualityResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [summaryRes, priceRes, regionRes, qualityRes] = await Promise.all([
          dataAPI.getDataSummary(),
          dataAPI.getPriceDistribution(),
          dataAPI.getRegionDistribution(),
          dataAPI.getDataQuality(),
        ])
        if (cancelled) return
        setSummary(summaryRes.data)
        setPriceDist(priceRes.data)
        setRegionDist(regionRes.data)
        setQuality(qualityRes.data)
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
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-500 mx-auto mb-4" />
          <p className="text-neutral-600">수집 데이터 조회 중...</p>
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
            <p className="font-medium text-error-900">데이터 조회 실패</p>
            <p className="text-sm text-error-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  const totalRows = summary?.total_rows ?? 0

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-h2 text-neutral-900 font-semibold">데이터 분석</h1>
        <p className="text-body text-neutral-600 mt-1">
          수집 파이프라인(scripts/collect_all_transactions.py)이 적재한 실거래 현황
        </p>
      </div>

      {totalRows === 0 && (
        <div className="flex items-start gap-3 p-4 bg-warning-50 border border-warning-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-warning-900">수집된 실거래 없음</p>
            <p className="text-sm text-warning-700 mt-1">
              <code className="bg-white px-1 rounded">python scripts/collect_all_transactions.py --sgg 11680 --year 2025 --month 12</code>
              {' '}실행 후 새로고침하면 아래가 채워집니다.
            </p>
          </div>
        </div>
      )}

      {/* Data Quality Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">총 행</p>
          <p className="text-h3 font-bold text-neutral-900 mt-2">{totalRows.toLocaleString()}</p>
          <p className="text-body-sm text-neutral-500 mt-2">비교사례(comparable_sales)</p>
        </div>
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">결측치</p>
          <p className="text-h3 font-bold text-neutral-900 mt-2">{quality?.missing_values ?? 0}</p>
          <p className="text-body-sm text-neutral-500 mt-2">
            {(quality?.missing_percentage ?? 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">아웃라이어</p>
          <p className="text-h3 font-bold text-neutral-900 mt-2">{quality?.outliers ?? 0}</p>
          <p className="text-body-sm text-neutral-500 mt-2">
            {(quality?.outlier_percentage ?? 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">데이터 품질</p>
          <p className="text-h3 font-bold text-neutral-900 mt-2">
            {quality ? `${(quality.quality_score * 100).toFixed(1)}%` : '—'}
          </p>
          <p className="text-body-sm text-neutral-500 mt-2">
            {quality ? STATUS_LABEL[quality.status] : '데이터 없음'}
          </p>
        </div>
      </div>

      {/* Property type breakdown */}
      {summary && summary.by_property_type.length > 0 && (
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <h3 className="text-h4 text-neutral-900 font-semibold mb-3">자산유형별 건수</h3>
          <div className="flex flex-wrap gap-3">
            {summary.by_property_type.map((row) => (
              <span
                key={row.name}
                className="px-3 py-1.5 rounded-full bg-primary-50 text-primary-700 text-sm font-medium border border-primary-200"
              >
                {row.name} {row.count.toLocaleString()}건
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h3 className="text-h4 text-neutral-900 font-semibold mb-4">거래금액 분포</h3>
          {priceDist && priceDist.data.some((d) => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={priceDist.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="range" stroke="#757575" style={{ fontSize: '12px' }} />
                <YAxis stroke="#757575" style={{ fontSize: '12px' }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', border: '1px solid #E0E0E0' }} />
                <Bar dataKey="count" fill="#2196F3" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </div>

        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h3 className="text-h4 text-neutral-900 font-semibold mb-4">시군구별 분포</h3>
          {regionDist && regionDist.data.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <RechartsPieChart>
                <Pie
                  data={regionDist.data}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name} ${value}`}
                  outerRadius={80}
                  dataKey="value"
                >
                  {regionDist.data.map((entry, index) => (
                    <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </div>
      </div>

      {/* Data Quality Details */}
      <div className="bg-white rounded-lg border border-neutral-300 p-6">
        <h3 className="text-h4 text-neutral-900 font-semibold mb-4">데이터 품질 상세</h3>
        <QualityDetail quality={quality} />
      </div>
    </div>
  )
}

function EmptyChart() {
  return (
    <div className="h-[300px] flex items-center justify-center text-neutral-400 text-sm">
      표시할 데이터가 없습니다
    </div>
  )
}

function QualityDetail({ quality }: { quality: QualityResponse | null }) {
  if (!quality || quality.status === 'no_data') {
    return (
      <div className="flex items-start gap-3 p-3 bg-neutral-50 border border-neutral-200 rounded-lg">
        <HelpCircle className="w-5 h-5 text-neutral-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium text-neutral-700">평가할 데이터 없음</p>
          <p className="text-sm text-neutral-500">실거래를 먼저 수집해야 품질 지표가 계산됩니다.</p>
        </div>
      </div>
    )
  }

  const rows = [
    {
      ok: quality.missing_percentage < 5,
      title: '결측치',
      detail: `${quality.missing_values}건 (${quality.missing_percentage.toFixed(1)}%) — 면적·거래금액 누락`,
    },
    {
      ok: quality.outlier_percentage < 5,
      title: '이상치',
      detail: `${quality.outliers}건 (${quality.outlier_percentage.toFixed(1)}%) — ㎡당 단가가 상식 범위(1만~5억 원) 밖`,
    },
  ]

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div
          key={row.title}
          className={`flex items-start gap-3 p-3 rounded-lg border ${
            row.ok ? 'bg-success-50 border-success-200' : 'bg-warning-50 border-warning-200'
          }`}
        >
          {row.ok ? (
            <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className={`font-medium ${row.ok ? 'text-success-900' : 'text-warning-900'}`}>{row.title}</p>
            <p className={`text-sm ${row.ok ? 'text-success-700' : 'text-warning-700'}`}>{row.detail}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
