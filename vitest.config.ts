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
      '@db': path.resolve(__dirname, './src/db'),
      '@repositories': path.resolve(__dirname, './src/repositories'),
      '@validation': path.resolve(__dirname, './src/validation'),
      '@api': path.resolve(__dirname, './src/api'),
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

      // Day 11 - Task 1 (δ=1275): include 없이 all:true를 쓰면 v8 provider가
      // 프로젝트 루트 전체(예: 이 저장소에 함께 존재하는 무관한 search_app/
      // 디렉터리)를 스캔해 이 앱과 무관한 파일까지 threshold 대상이 된다.
      // src/ 아래로 스캔 범위를 명시적으로 좁힌다.
      include: ['src/**/*.ts', 'src/**/*.tsx'],

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
        'src/main.tsx',
        'src/index.html',
        // 부트스트랩 진입점 — 분기 로직 없이 조립만 하며, 유닛테스트가 아니라
        // 실제 서버/CLI 실행으로 검증한다 (이 세션 전반의 curl/Playwright 검증 패턴)
        'src/server/index.ts',
        'src/db/migrate-cli.ts',
        // Day7에서 사용자가 명시적으로 선택한 "최소 데모" 범위의 UI 컴포넌트 —
        // 각 Day 완료 시 Playwright로 수동 검증되며, 별도 프론트엔드 테스트
        // 인프라(@testing-library 등)는 이 세션의 DB중심/유지보수 우선순위 밖
        'src/App.tsx',
        // 타입 전용 파일 — 런타임 코드가 없어 v8 provider가 0/0 statement를
        // 0%로 집계, perFile threshold를 항상 위반한다 (실제 로직 없음이 원인)
        'src/types/backup.ts',
        'src/types/credit.ts',
        'src/types/financialSnapshot.ts',
        'src/types/loan.ts',
        'src/types/loanPortfolio.ts',
        'src/types/transaction.ts',
        'src/types/user.ts',
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

    // 통합 테스트는 단일 PostgreSQL 데이터베이스(maars_test)를 공유하며
    // afterEach에서 모든 테이블을 TRUNCATE 한다. 파일을 병렬로 돌리면 한
    // 워커의 정리(TRUNCATE)가 다른 워커의 트랜잭션 도중 실행되어 FK 위반·
    // deadlock·"not found" 오류를 일으킨다(이 truncate 기반 정리 설계는
    // 직렬 실행을 전제로 한다). 따라서 단일 스레드로 직렬 실행한다.
    threads: true,
    maxThreads: 1,
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
