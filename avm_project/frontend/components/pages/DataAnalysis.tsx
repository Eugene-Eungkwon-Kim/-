'use client'

import React from 'react'
import { BarChart3, PieChart, AlertCircle, CheckCircle } from 'lucide-react'
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
  Legend,
  ResponsiveContainer,
} from 'recharts'

export default function DataAnalysis() {
  const priceDistribution = [
    { range: '1-5억', count: 850 },
    { range: '5-10억', count: 1200 },
    { range: '10-15억', count: 1500 },
    { range: '15-20억', count: 900 },
    { range: '20억+', count: 550 },
  ]

  const regionDistribution = [
    { name: '강남구', value: 1200, color: '#2196F3' },
    { name: '서초구', value: 950, color: '#64B5F6' },
    { name: '송파구', value: 1100, color: '#1565C0' },
    { name: '강서구', value: 800, color: '#0D47A1' },
    { name: '기타', value: 950, color: '#E3F2FD' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-h2 text-neutral-900 font-semibold">데이터 분석</h1>
        <p className="text-body text-neutral-600 mt-1">데이터셋 품질 및 분포 분석</p>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-lg border border-neutral-300 p-4 flex flex-wrap gap-4">
        <select className="input flex-1 min-w-[200px]">
          <option>전체 데이터셋</option>
          <option>2026년 상반기</option>
          <option>서울 지역</option>
        </select>
        <select className="input flex-1 min-w-[200px]">
          <option>전체 기간</option>
          <option>2026-01 ~ 2026-06</option>
          <option>2026-01</option>
        </select>
        <button className="btn btn-secondary">필터 적용</button>
        <button className="btn btn-secondary">리셋</button>
      </div>

      {/* Data Quality Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">총 행</p>
          <p className="text-h3 font-bold text-neutral-900 mt-2">5,000</p>
          <p className="text-body-sm text-neutral-500 mt-2">부동산 거래 기록</p>
        </div>
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">결측치</p>
          <p className="text-h3 font-bold text-success-500 mt-2">15</p>
          <p className="text-body-sm text-neutral-500 mt-2">0.3% (우수)</p>
        </div>
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">아웃라이어</p>
          <p className="text-h3 font-bold text-warning-500 mt-2">125</p>
          <p className="text-body-sm text-neutral-500 mt-2">2.5% (정상)</p>
        </div>
        <div className="bg-white rounded-lg border border-neutral-300 p-4">
          <p className="text-body-sm text-neutral-600">데이터 품질</p>
          <p className="text-h3 font-bold text-success-500 mt-2">99.2%</p>
          <p className="text-body-sm text-neutral-500 mt-2">매우 우수</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Price Distribution */}
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h3 className="text-h4 text-neutral-900 font-semibold mb-4">거래금액 분포</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={priceDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="range" stroke="#757575" style={{ fontSize: '12px' }} />
              <YAxis stroke="#757575" style={{ fontSize: '12px' }} />
              <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', border: '1px solid #E0E0E0' }} />
              <Bar dataKey="count" fill="#2196F3" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Region Distribution */}
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h3 className="text-h4 text-neutral-900 font-semibold mb-4">지역별 분포</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RechartsPieChart>
              <Pie
                data={regionDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name} ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {regionDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </RechartsPieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Data Quality Details */}
      <div className="bg-white rounded-lg border border-neutral-300 p-6">
        <h3 className="text-h4 text-neutral-900 font-semibold mb-4">데이터 품질 상세</h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 bg-success-50 border border-success-200 rounded-lg">
            <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-success-900">데이터 범위</p>
              <p className="text-sm text-success-700">거래금액: 1억 ~ 50억 원 (정상 범위)</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-success-50 border border-success-200 rounded-lg">
            <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-success-900">시간 분포</p>
              <p className="text-sm text-success-700">2020-2026년 균형있는 분포 (시계열 OK)</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3 bg-warning-50 border border-warning-200 rounded-lg">
            <AlertCircle className="w-5 h-5 text-warning-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-warning-900">주유소 데이터</p>
              <p className="text-sm text-warning-700">Opinet 99.6% 수집 완료 (일부 외곽 지역 누락)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
