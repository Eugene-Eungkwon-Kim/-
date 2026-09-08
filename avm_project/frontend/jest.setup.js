// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// jsdom에는 ResizeObserver가 없다 — recharts의 ResponsiveContainer가 마운트
// 시 바로 이걸 찾아 쓰므로, recharts를 쓰는 어떤 컴포넌트든(Dashboard,
// DataAnalysis, RealtimeMonitoring) 이 폴리필 없이는 렌더 자체가 실패한다.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
