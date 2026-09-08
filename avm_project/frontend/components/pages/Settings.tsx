'use client'

import React, { useEffect, useState } from 'react'
import { Save, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { settingsAPI, apiUtils } from '@/lib/api'

// 이 페이지는 저장 버튼을 눌러도 실제로는 아무것도 저장하지 않고 3초짜리
// 토스트만 보여줬다 — 새로고침하면 항상 기본값으로 돌아갔다. settingsAPI는
// lib/api.ts에 있었는데 호출된 적이 없었다. 실제로는
// config/schedule_config.json 을 retraining_monitor.py(성능 임계값)와
// weekly_retrain_scheduler.py(스케줄)가 이미 참조하고 있어서, 백엔드가
// 그 파일을 그대로 읽고 쓰도록 연결했다(이번 세션) — 이 페이지는 그
// 엔드포인트를 호출하기만 하면 된다.

interface SettingsData {
  performance_threshold: number
  email_alert: boolean
  email_address: string
  slack_alert: boolean
  log_level: string
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    settingsAPI
      .getSettings()
      .then((res) => {
        if (!cancelled) setSettings(res.data)
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
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    setError(null)
    try {
      const res = await settingsAPI.updateSettings(settings)
      setSettings(res.data.settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(apiUtils.handleError(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-500" />
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 p-4 bg-error-50 border border-error-200 rounded-lg">
          <XCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-error-700">{error ?? '설정을 불러오지 못했습니다.'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-h2 text-neutral-900 font-semibold">설정</h1>
        <p className="text-body text-neutral-600 mt-1">
          config/schedule_config.json 을 직접 읽고 씁니다 — 재학습 스케줄러가 참조하는 실제 설정 파일입니다.
        </p>
      </div>

      {saved && (
        <div className="flex items-start gap-3 p-4 bg-success-50 border border-success-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-success-900">저장 완료</p>
            <p className="text-sm text-success-700">설정이 파일에 저장되었습니다.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 p-4 bg-error-50 border border-error-200 rounded-lg">
          <XCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-error-700">{error}</p>
        </div>
      )}

      <div className="space-y-6">
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">모델 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                성능 임계값 (R²)
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={settings.performance_threshold}
                onChange={(e) =>
                  setSettings({ ...settings, performance_threshold: parseFloat(e.target.value) || 0 })
                }
                className="input"
              />
              <p className="text-body-sm text-neutral-500 mt-1">
                이 값 이하로 R²가 떨어지면 성능 저하 알림 (retraining_monitor.py 가 실제로 사용)
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">알림 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">이메일 알림</label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="email-alert"
                    checked={settings.email_alert}
                    onChange={() => setSettings({ ...settings, email_alert: true })}
                    className="w-4 h-4"
                  />
                  <span className="text-body text-neutral-700">활성화</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="email-alert"
                    checked={!settings.email_alert}
                    onChange={() => setSettings({ ...settings, email_alert: false })}
                    className="w-4 h-4"
                  />
                  <span className="text-body text-neutral-700">비활성화</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">이메일 주소</label>
              <input
                type="email"
                value={settings.email_address}
                onChange={(e) => setSettings({ ...settings, email_address: e.target.value })}
                className="input"
              />
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">Slack 알림</label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="slack-alert"
                    checked={settings.slack_alert}
                    onChange={() => setSettings({ ...settings, slack_alert: true })}
                    className="w-4 h-4"
                  />
                  <span className="text-body text-neutral-700">활성화</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="slack-alert"
                    checked={!settings.slack_alert}
                    onChange={() => setSettings({ ...settings, slack_alert: false })}
                    className="w-4 h-4"
                  />
                  <span className="text-body text-neutral-700">비활성화</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">시스템 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">로그 레벨</label>
              <select
                className="input"
                value={settings.log_level}
                onChange={(e) => setSettings({ ...settings, log_level: e.target.value })}
              >
                <option>INFO</option>
                <option>DEBUG</option>
                <option>WARNING</option>
                <option>ERROR</option>
              </select>
            </div>

            <div className="p-3 bg-info-50 border border-info-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-info-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-info-900">API 키 보안</p>
                <p className="text-sm text-info-700">
                  API 키는 이 설정 파일에 저장되지 않습니다 — 서버 환경변수(.env)로만 관리됩니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} disabled={saving} className="btn btn-primary gap-2 disabled:opacity-60">
          <Save className="w-4 h-4" />
          {saving ? '저장 중...' : '설정 저장'}
        </button>
      </div>
    </div>
  )
}
