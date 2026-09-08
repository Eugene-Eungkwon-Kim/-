import axios, { AxiosInstance } from 'axios'

// API 기본 설정
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Axios 인스턴스 생성
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 요청 인터셉터 (토큰 추가)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 응답 인터셉터 (에러 처리)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ============================================
// 인증 API
// ============================================
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
}

// ============================================
// 대시보드 API
// ============================================
export const dashboardAPI = {
  getSummary: () => api.get('/dashboard/summary'),
  getTrendData: (weeks: number = 10) =>
    api.get(`/dashboard/trend?weeks=${weeks}`),
  getRecentTrainings: (limit: number = 10) =>
    api.get(`/dashboard/recent-trainings?limit=${limit}`),
  getStatistics: () => api.get('/dashboard/statistics'),
}

// ============================================
// 모델 API
// ============================================
export const modelAPI = {
  getModelDetails: (modelId: string) =>
    api.get(`/models/${modelId}`),
  listModels: () => api.get('/models'),
  getFeatureImportance: (modelId: string) =>
    api.get(`/models/${modelId}/feature-importance`),
  downloadModel: (modelId: string) =>
    api.get(`/models/${modelId}/download`, { responseType: 'blob' }),
  deployModel: (modelId: string) =>
    api.post(`/models/${modelId}/deploy`),
  deleteModel: (modelId: string) =>
    api.delete(`/models/${modelId}`),
}

// ============================================
// 데이터 분석 API
// ============================================
// /data/quality, /data/price-distribution, /data/region-distribution 은 고정
// 예시값을 돌려주는 deprecated 엔드포인트다 — 수집 파이프라인이 적재한 실측값을
// 같은 응답 모양으로 주는 /data/comparable-sales/* 를 쓴다.
export const dataAPI = {
  getDataQuality: () => api.get('/data/comparable-sales/quality'),
  getPriceDistribution: () => api.get('/data/comparable-sales/price-distribution'),
  getRegionDistribution: () => api.get('/data/comparable-sales/region-distribution'),
  getDataSummary: () => api.get('/data/comparable-sales/summary'),
}

// ============================================
// 모니터링 API
// ============================================
export const monitoringAPI = {
  getPerformanceMetrics: () => api.get('/monitoring/metrics'),
  getAlerts: () => api.get('/monitoring/alerts'),
  getHealthStatus: () => api.get('/health'),
}

// ============================================
// 설정 API
// ============================================
export const settingsAPI = {
  getSettings: () => api.get('/settings'),
  updateSettings: (settings: Record<string, any>) =>
    api.put('/settings', settings),
  testEmailNotification: (email: string) =>
    api.post('/settings/test-email', { email }),
  testSlackNotification: () =>
    api.post('/settings/test-slack'),
}

// ============================================
// 재학습 API
// ============================================
export const retrainingAPI = {
  startRetraining: () => api.post('/retraining/start'),
  getRetrainingStatus: () => api.get('/retraining/status'),
  getRetrainingHistory: (limit: number = 50) =>
    api.get(`/retraining/history?limit=${limit}`),
  cancelRetraining: () => api.post('/retraining/cancel'),
}

// ============================================
// 유틸리티 함수
// ============================================
export const apiUtils = {
  handleError: (error: any): string => {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    }
    if (error.response?.data?.message) {
      return error.response.data.message
    }
    if (error.message) {
      return error.message
    }
    return '알 수 없는 오류가 발생했습니다.'
  },

  isAxiosError: (error: any): error is any => {
    return error.config !== undefined
  },
}

export default api
