'use client'

import React, { useState } from 'react'
import { AlertCircle, Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // 백엔드 로그인 API 호출 (추후 구현)
      console.log('Login attempt:', { email, password })

      // 임시: 로컬 스토리지에 토큰 저장
      localStorage.setItem('auth_token', 'demo_token_12345')
      localStorage.setItem('user_email', email)

      // 대시보드로 리다이렉트
      window.location.href = '/dashboard'
    } catch (err) {
      setError('로그인에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-900 via-primary-700 to-primary-500 flex items-center justify-center p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl"></div>
      </div>

      {/* Login Card */}
      <div className="relative w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl p-8 space-y-6">
          {/* Logo Section */}
          <div className="text-center space-y-3">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl shadow-lg">
              <span className="text-white font-bold text-2xl">AVM</span>
            </div>
            <div>
              <h1 className="text-h2 text-neutral-900 font-bold">AVM Dashboard</h1>
              <p className="text-body-sm text-neutral-600 mt-1">
                부동산 자동감정 모델 대시보드
              </p>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Input */}
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                이메일
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@avm.com"
                className="input"
                required
              />
            </div>

            {/* Password Input */}
            <div>
              <label className="block text-body-sm font-medium text-neutral-900 mb-2">
                비밀번호
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input pr-10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-start gap-3 p-3 bg-error-50 border border-error-200 rounded-lg">
                <AlertCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-error-700">{error}</p>
              </div>
            )}

            {/* Remember Me */}
            <div className="flex items-center">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded" defaultChecked />
                <span className="text-body-sm text-neutral-700">로그인 상태 유지</span>
              </label>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn btn-primary text-body-lg font-semibold py-3"
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-neutral-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-neutral-600">또는</span>
            </div>
          </div>

          {/* Demo Login */}
          <button
            type="button"
            onClick={() => {
              setEmail('admin@avm.com')
              setPassword('demo123')
            }}
            className="w-full btn btn-secondary text-body font-medium py-2"
          >
            데모 계정으로 로그인
          </button>

          {/* Footer */}
          <div className="text-center space-y-2">
            <button className="text-primary-500 hover:text-primary-700 font-medium text-body-sm">
              비밀번호를 잊으셨나요?
            </button>
            <p className="text-body-sm text-neutral-600">
              계정이 없으신가요?{' '}
              <button className="text-primary-500 hover:text-primary-700 font-medium">
                관리자에게 문의
              </button>
            </p>
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-white bg-opacity-10 rounded-lg backdrop-blur-sm border border-white border-opacity-20">
          <p className="text-white text-center text-body-sm">
            <strong>테스트:</strong> admin@avm.com / demo123
          </p>
        </div>
      </div>
    </div>
  )
}
