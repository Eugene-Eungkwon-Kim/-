'use client'

import React, { useState } from 'react'
import { Save, AlertCircle, CheckCircle } from 'lucide-react'

export default function Settings() {
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-h2 text-neutral-900 font-semibold">설정</h1>
        <p className="text-body text-neutral-600 mt-1">AVM 모델 및 시스템 설정</p>
      </div>

      {/* Success Message */}
      {saved && (
        <div className="flex items-start gap-3 p-4 bg-success-50 border border-success-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-success-900">저장 완료</p>
            <p className="text-sm text-success-700">설정이 저장되었습니다.</p>
          </div>
        </div>
      )}

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Section 1: Model Settings */}
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">모델 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                자동 재학습 활성화
              </label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="auto-retrain" value="yes" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">예</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="auto-retrain" value="no" className="w-4 h-4" />
                  <span className="text-body text-neutral-700">아니오</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                재학습 스케줄
              </label>
              <select className="input">
                <option>매주 목요일 10:00 AM</option>
                <option>매일 01:00 AM</option>
                <option>매월 첫날 09:00 AM</option>
                <option>수동 실행</option>
              </select>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                성능 임계값 (R²)
              </label>
              <input type="number" min="0" max="1" step="0.01" defaultValue="0.95" className="input" />
              <p className="text-body-sm text-neutral-500 mt-1">이 값 이하로 떨어지면 알림</p>
            </div>
          </div>
        </div>

        {/* Section 2: Data Settings */}
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">데이터 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                데이터 경로
              </label>
              <input
                type="text"
                defaultValue="/data/raw/real_estate_2024.csv"
                className="input"
              />
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                전처리 옵션
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">결측치 처리</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">아웃라이어 제거</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">정규화</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                Feature Engineering
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">Vworld 좌표 추가</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">Opinet 주유소 정보 추가</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Notification Settings */}
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">알림 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                이메일 알림
              </label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="email-alert" value="yes" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">활성화</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="email-alert" value="no" className="w-4 h-4" />
                  <span className="text-body text-neutral-700">비활성화</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                이메일 주소
              </label>
              <input
                type="email"
                defaultValue="admin@avm.com"
                className="input"
              />
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                Slack 알림
              </label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="slack-alert" value="yes" className="w-4 h-4" />
                  <span className="text-body text-neutral-700">활성화</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="slack-alert" value="no" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">비활성화</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                알림 조건
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">성능 저하 시 알림</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-body text-neutral-700">학습 실패 시 알림</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" className="w-4 h-4" />
                  <span className="text-body text-neutral-700">학습 완료 시 알림</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: System Settings */}
        <div className="bg-white rounded-lg border border-neutral-300 p-6">
          <h2 className="text-h4 text-neutral-900 font-semibold mb-4">시스템 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                로그 레벨
              </label>
              <select className="input">
                <option>INFO</option>
                <option>DEBUG</option>
                <option>WARNING</option>
                <option>ERROR</option>
              </select>
            </div>

            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                백업 주기
              </label>
              <select className="input">
                <option>매일</option>
                <option>매주</option>
                <option>매월</option>
              </select>
            </div>

            <div className="p-3 bg-info-50 border border-info-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-info-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-info-900">API 키 보안</p>
                <p className="text-sm text-info-700">API 키는 암호화되어 저장됩니다.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button onClick={handleSave} className="btn btn-primary gap-2">
          <Save className="w-4 h-4" />
          설정 저장
        </button>
      </div>
    </div>
  )
}
