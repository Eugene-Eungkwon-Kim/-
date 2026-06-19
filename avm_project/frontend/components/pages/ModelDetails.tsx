'use client'

import React, { useState } from 'react'
import { Download, Share2, Trash2, ChevronRight } from 'lucide-react'
import StatisticCard from '@/components/ui/StatisticCard'

export default function ModelDetails() {
  const [activeTab, setActiveTab] = useState('overview')

  const tabs = [
    { id: 'overview', label: '개요' },
    { id: 'metrics', label: '지표' },
    { id: 'features', label: '특성' },
    { id: 'validation', label: '검증' },
    { id: 'logs', label: '로그' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-h2 text-neutral-900 font-semibold">모델 상세 정보</h1>
        <p className="text-body text-neutral-600 mt-1">XGBoost 모델 - v20260619_100000</p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg border border-neutral-300">
        <div className="flex border-b border-neutral-300">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? 'text-primary-500 border-primary-500'
                  : 'text-neutral-600 border-transparent hover:text-neutral-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Model Information */}
              <div>
                <h3 className="text-h4 text-neutral-900 font-semibold mb-4">모델 정보</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-neutral-50 rounded-lg p-4">
                    <p className="text-body-sm text-neutral-600">모델명</p>
                    <p className="text-body-lg font-semibold text-neutral-900 mt-1">XGBoost v20260619_100000</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-4">
                    <p className="text-body-sm text-neutral-600">모델 타입</p>
                    <p className="text-body-lg font-semibold text-neutral-900 mt-1">Gradient Boosting (Regression)</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-4">
                    <p className="text-body-sm text-neutral-600">생성 날짜</p>
                    <p className="text-body-lg font-semibold text-neutral-900 mt-1">2026-06-19 10:00:00</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-4">
                    <p className="text-body-sm text-neutral-600">마지막 학습</p>
                    <p className="text-body-lg font-semibold text-neutral-900 mt-1">2026-06-19 10:15:00</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-4">
                    <p className="text-body-sm text-neutral-600">데이터 크기</p>
                    <p className="text-body-lg font-semibold text-neutral-900 mt-1">5,000 행</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-4">
                    <p className="text-body-sm text-neutral-600">특성 수</p>
                    <p className="text-body-lg font-semibold text-neutral-900 mt-1">17개</p>
                  </div>
                </div>
              </div>

              {/* Performance Metrics */}
              <div>
                <h3 className="text-h4 text-neutral-900 font-semibold mb-4">성능 지표</h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <StatisticCard label="R² 점수" value="0.8420" subtext="vs prev: -0.15%" icon="chart" />
                  <StatisticCard label="MAE" value="42.5M" subtext="절대 오차" icon="trending" />
                  <StatisticCard label="RMSE" value="55.8M" subtext="제곱 평균" icon="up" />
                  <StatisticCard label="MAPE" value="5.2%" subtext="백분율 오차" icon="activity" />
                </div>
              </div>

              {/* Action Buttons */}
              <div>
                <h3 className="text-h4 text-neutral-900 font-semibold mb-4">액션</h3>
                <div className="flex flex-wrap gap-3">
                  <button className="btn btn-primary gap-2">
                    <Download className="w-4 h-4" />
                    모델 다운로드
                  </button>
                  <button className="btn btn-secondary gap-2">
                    <Share2 className="w-4 h-4" />
                    프로덕션 배포
                  </button>
                  <button className="btn btn-danger gap-2">
                    <Trash2 className="w-4 h-4" />
                    삭제
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="text-center py-12">
              <p className="text-neutral-600">상세 성능 지표 - 개발 중</p>
            </div>
          )}

          {activeTab === 'features' && (
            <div className="space-y-4">
              <h3 className="text-h4 text-neutral-900 font-semibold">특성 중요도 (Top 10)</h3>
              {[
                { name: '면적', importance: 38.2 },
                { name: '지역', importance: 28.5 },
                { name: '거래일', importance: 15.8 },
                { name: '위도', importance: 8.0 },
                { name: '경도', importance: 4.7 },
                { name: '주변_주유소', importance: 3.2 },
                { name: '건축년도', importance: 2.5 },
                { name: '평균_가격', importance: 0.8 },
                { name: '층수', importance: 0.3 },
                { name: '주차장', importance: 0.1 },
              ].map((feature, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-20 text-sm font-medium text-neutral-700">{feature.name}</div>
                  <div className="flex-1 bg-neutral-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary-400 to-primary-500 transition-all"
                      style={{ width: `${feature.importance}%` }}
                    />
                  </div>
                  <div className="w-12 text-right text-sm font-semibold text-neutral-900">
                    {feature.importance.toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'validation' && (
            <div className="text-center py-12">
              <p className="text-neutral-600">검증 결과 - 개발 중</p>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="text-center py-12">
              <p className="text-neutral-600">학습 로그 - 개발 중</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
