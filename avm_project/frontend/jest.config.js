const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  // tsconfig.json의 "@/*" -> "./*" 와 맞춘다. 이 프로젝트에는 src/ 디렉터리가
  // 없고 app/, components/, lib/ 가 전부 루트에 있다 — 예전 설정(<rootDir>/src/$1)
  // 은 "@/" 로 임포트하는 어떤 테스트도 모듈을 못 찾아 실패했을 것이다
  // (지금까지 테스트 파일 자체가 없어 드러나지 않았을 뿐).
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: ['**/__tests__/**/*.test.ts', '**/__tests__/**/*.test.tsx', '**/*.test.ts', '**/*.test.tsx'],
  collectCoverageFrom: [
    '{app,components,lib}/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/*.stories.{js,jsx,ts,tsx}',
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)
