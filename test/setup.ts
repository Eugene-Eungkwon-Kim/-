import { vi, beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';

// MSW 서버 시작 (모든 테스트 전)
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

// 각 테스트 후 핸들러 초기화
afterEach(() => {
  server.resetHandlers();
});

// 테스트 스위트 완료 후 서버 종료
afterAll(() => {
  server.close();
});

// 전역 모킹 설정
global.fetch = vi.fn();

// localStorage 모킹
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  }
});

// 콘솔 경고 억제 (선택사항)
console.warn = vi.fn();
