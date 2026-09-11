'use client'

import React, { useEffect, useState } from 'react'
import { XCircle } from 'lucide-react'
import StatisticCard from '@/components/ui/StatisticCard'
import { modelAPI, apiUtils } from '@/lib/api'

// 이 페이지는 "XGBoost v20260619_100000", R²=0.8420 등 모델 하나를 통째로
// 하드코딩해 어떤 모델을 보든 항상 같은 화면을 보여주고 있었다 —
// modelAPI가 lib/api.ts에 있었는데 호출된 적이 없었다. 실제로는
// backend/ml_models.py의 model_manager가 models/*.joblib 를 로드하고
// /models 가 그 목록을 돌려주므로(이번 세션에 연결), 목록에서 고른
// 모델의 실제 메타데이터·특성 중요도를 보여준다.

interface ModelSummary {
  id: string
  name: string
  type: string
  version: string
  loaded: boolean
  file: string
}

interface ModelDetail {
  id: string
  name: string
  type: string
  file: string
  version: string
  loaded_at: string
  is_demo: boolean
  is_real_data: boolean
  r2: number | null
  mae: number | null
  rmse: number | null
  mape: number | null
}

interface FeatureImportance {
  name: string
  importance: number
}

export default function ModelDetails() {
  const [models, setModels] = useState<ModelSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ModelDetail | null>(null)
  const [features, setFeatures] = useState<FeatureImportance[]>([])
  const [featureMessage, setFeatureMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    modelAPI
      .listModels()
      .then((res) => {
        if (cancelled) return
        const list: ModelSummary[] = res.data.data
        setModels(list)
        if (list.length > 0) setSelectedId(list[0].id)
        else setLoading(false)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(apiUtils.handleError(err))
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let cancelled = false
    setLoading(true)
    Promise.all([modelAPI.getModelDetails(selectedId), modelAPI.getFeatureImportance(selectedId)])
      .then(([detailRes, featureRes]) => {
        if (cancelled) return
        setDetail(detailRes.data)
        setFeatures(featureRes.data.data)
        setFeatureMessage(featureRes.data.message ?? null)
      })
      .catch((err) => {
        if (!cancelled) setError(apiUtils.handleError(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 p-4 bg-error-50 border border-error-200 rounded-lg">
          <XCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-error-900">모델 정보 조회 실패</p>
            <p className="text-sm text-error-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!loading && models.length === 0) {
    return (
      <div className="p-6">
        <h1 className="text-h2 text-neutral-900 font-semibold mb-4">모델 상세 정보</h1>
        <div className="p-6 bg-warning-50 border border-warning-200 rounded-lg text-sm text-warning-700">
          로드된 모델이 없습니다. <code className="bg-white px-1 rounded">models/*.joblib</code> 에
          모델 파일이 있어야 여기 표시됩니다.
        </div>
      </div>
    )
  }

  const fmt = (v: number | null, digits = 4) => (v != null ? v.toFixed(digits) : '—')
  const fmtWon = (v: number | null) => (v != null ? `${(v / 1_000_000).toFixed(1)}M` : '—')

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-h2 text-neutral-900 font-semibold">모델 상세 정보</h1>
          <p className="text-body text-neutral-600 mt-1">{detail?.name ?? '로드 중...'}</p>
        </div>
        <select
          className="input max-w-xs"
          value={selectedId ?? ''}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.version})
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-500" />
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-neutral-300 p-6 space-y-6">
          {detail?.is_demo && (
            <div className="p-3 bg-warning-50 border border-warning-200 rounded-lg text-sm text-warning-700">
              이 모델은 실학습 산출물이 없을 때 자동 생성되는 데모 모델입니다 — 실제 성능 지표가 아닙니다.
            </div>
          )}

          <div>
            <h3 className="text-h4 text-neutral-900 font-semibold mb-4">모델 정보</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoCell label="모델명" value={detail?.name ?? '—'} />
              <InfoCell label="모델 타입" value={detail?.type ?? '—'} />
              <InfoCell label="버전" value={detail?.version ?? '—'} />
              <InfoCell label="파일명" value={detail?.file ?? '—'} />
              <InfoCell label="로드 시각" value={detail?.loaded_at ?? '—'} />
              <InfoCell label="실거래 데이터 학습 여부" value={detail?.is_real_data ? '예' : '아니오 (합성 데이터)'} />
            </div>
          </div>

          <div>
            <h3 className="text-h4 text-neutral-900 font-semibold mb-4">성능 지표</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <StatisticCard label="R² 점수" value={fmt(detail?.r2 ?? null)} subtext="결정계수" icon="chart" />
              <StatisticCard label="MAE" value={fmtWon(detail?.mae ?? null)} subtext="절대 오차" icon="trending" />
              <StatisticCard label="RMSE" value={fmtWon(detail?.rmse ?? null)} subtext="제곱 평균" icon="up" />
              <StatisticCard
                label="MAPE"
                value={detail?.mape != null ? `${(detail.mape * 100).toFixed(1)}%` : '—'}
                subtext="백분율 오차"
                icon="activity"
              />
            </div>
            {detail?.r2 == null && (
              <p className="text-body-sm text-neutral-500 mt-3">
                성능 지표 없음 — logs/retrain_history.jsonl 에 이 모델 타입({detail?.type})의 학습 기록이 없습니다.
              </p>
            )}
          </div>

          <div>
            <h3 className="text-h4 text-neutral-900 font-semibold mb-4">특성 중요도 (Top 10)</h3>
            {features.length > 0 ? (
              <div className="space-y-4">
                {features.map((feature) => (
                  <div key={feature.name} className="flex items-center gap-4">
                    <div className="w-24 text-sm font-medium text-neutral-700 truncate">{feature.name}</div>
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
            ) : (
              <p className="text-body-sm text-neutral-500">{featureMessage ?? '특성 중요도 데이터가 없습니다.'}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-neutral-50 rounded-lg p-4">
      <p className="text-body-sm text-neutral-600">{label}</p>
      <p className="text-body-lg font-semibold text-neutral-900 mt-1">{value}</p>
    </div>
  )
}
