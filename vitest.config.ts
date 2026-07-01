import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@services': path.resolve(__dirname, './src/services'),
      '@types': path.resolve(__dirname, './src/types'),
      '@fixtures': path.resolve(__dirname, './test/fixtures'),
      '@mocks': path.resolve(__dirname, './test/mocks'),
    }
  },

  test: {
    // 환경
    environment: 'happy-dom',
    globals: true,

    // 커버리지 임계치 (Phase 2: 40%)
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov', 'text-summary'],

      // 절대값 (%)
      lines: 40,
      functions: 40,
      branches: 35,
      statements: 40,

      // 파일별 요구사항
      perFile: true,

      exclude: [
        'node_modules/',
        'dist/',
        '**/*.spec.ts',
        '**/*.test.ts',
        '**/fixtures/',
        '**/mocks/',
        'src/main.ts',
        'src/index.html'
      ],

      // 상세 리포트
      all: true,
      skipFull: false,
    },

    // 테스트 파일 패턴
    include: ['src/**/*.{spec,test}.ts', 'test/**/*.{spec,test}.ts'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],

    // 세트업 파일
    setupFiles: ['./test/setup.ts'],

    // 병렬 실행
    threads: true,
    maxThreads: 4,
    minThreads: 1,

    // 타임아웃
    testTimeout: 10000,
    hookTimeout: 10000,

    // 로깅
    reporter: ['default', 'html'],
    outputFile: {
      html: './coverage/index.html',
    },

    // 변경 감지 모드
    watch: process.env.CI !== 'true',
  }
});
