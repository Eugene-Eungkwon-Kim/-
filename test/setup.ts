import { vi, beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';
import { initializeTestDatabase, cleanupTestDatabase, closeTestDatabase } from '../src/db/__tests__/testDatabase';

// 암호화 키 설정 (테스트용)
process.env.ENCRYPTION_KEY = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';

// PostgreSQL 테스트 데이터베이스 초기화
beforeAll(async () => {
  try {
    await initializeTestDatabase();
  } catch (error) {
    console.warn('PostgreSQL test database initialization failed (optional for non-DB tests):', error);
  }

  server.listen({ onUnhandledRequest: 'error' });
});

// 각 테스트 후 DB 정리 및 핸들러 초기화
afterEach(async () => {
  try {
    await cleanupTestDatabase();
  } catch (error) {
    // DB 정리 실패는 무시 (테스트에서 DB를 사용하지 않은 경우)
  }
  server.resetHandlers();
});

// 테스트 스위트 완료 후 DB 및 서버 종료
afterAll(async () => {
  server.close();
  try {
    await closeTestDatabase();
  } catch (error) {
    // DB 정리 실패는 무시
  }
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
