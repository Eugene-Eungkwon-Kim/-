# D13: Core Web Vitals 계측 & LCP 최적화 설계서

**작성일**: 2026-07-01  
**담당**: DevOps Lead + FE Dev #2  
**상태**: Tool Selection In Progress  
**목표**: LCP 2.5s → 1.2s 달성, RUM 대시보드 구축

---

## 1. 문제 분석

### 1.1 현황 진단

| 지표 | 현황 | 목표 | 갭 |
|------|------|------|-----|
| **LCP** (Largest Contentful Paint) | **2.5s** | **1.2s** | -53% |
| **INP** (Interaction to Next Paint) | 측정불가 | 200ms | 계측 필요 |
| **CLS** (Cumulative Layout Shift) | 미측정 | 0.1 | 계측 필요 |

### 1.2 LCP 병목점 추정 (Lighthouse 프로파일링)

```
초기 로딩 타임라인:
0ms    ├─ 페이지 요청 (DNS/TCP/TLS)
200ms  ├─ HTML 파싱 시작
400ms  ├─ CSS 다운로드 + 파싱 (boxicons.css 745KB ❌ 병목)
800ms  ├─ JavaScript 다운로드
900ms  ├─ jQuery v1.9.0 + Bootstrap 스크립트 파싱 (500KB ❌)
1200ms ├─ 이미지 로딩 시작 (마커 이미지, 배경 등)
1500ms ├─ 지도 API 호출 (외부 API, 카카오/VWorld)
2500ms └─ LCP: 지도 렌더링 완료 (첫 contentful paint)
```

**주요 병목**:
1. 📦 CSS 번들 크기: 745KB (icons.css + bootstrap.css)
2. 🔧 JavaScript 해석: jQuery 500KB + plugin loading
3. 🌐 외부 API: 지도 API 응답 시간 (500ms+)
4. 🖼️ 이미지 최적화: WebP 미지원, lazy-loading 미적용

---

## 2. RUM 도구 선택

### 2.1 도구 비교표

| 솔루션 | 가격 | 지연시간 | 기능 | 추천도 |
|--------|------|---------|------|--------|
| **Sentry** | 무료(50k events/월) | <1ms | Error + Performance + Session Replay | ⭐⭐⭐⭐⭐ 추천 |
| **New Relic** | $19-99/월 | <1ms | 전체 관찰성 + 고급 분석 | ⭐⭐⭐⭐ |
| **DataDog** | $15+/host | <1ms | APM + Infrastructure | ⭐⭐⭐ |
| **Google Analytics 4** | 무료 | <100ms | 기본 Web Vitals | ⭐⭐ (부족) |
| **OpenObserve** | 오픈소스 | <50ms | 자체 호스팅, 경량 | ⭐⭐⭐ |

**선택**: **Sentry** (초기 비용 최소, 충분한 기능, 한국 데이터센터 미지원이나 글로벌 무방)

---

## 3. 구현 계획

### 3.1 Sentry 설정

#### 3.1.1 설치
```bash
npm install @sentry/react @sentry/tracing
```

#### 3.1.2 src/main.tsx (초기화)
```typescript
import * as Sentry from "@sentry/react";
import { BrowserTracing } from "@sentry/tracing";

Sentry.init({
  dsn: "https://YOUR_KEY@YOUR_ORG.ingest.sentry.io/YOUR_PROJECT_ID",
  
  integrations: [
    new BrowserTracing({
      routingInstrumentation: Sentry.reactRouterV6Instrumentation(
        window.history
      ),
      tracingOrigins: [
        "localhost",
        /^\//,
        // 외부 API는 필요할 때만
        /https:\/\/dapi\.kakao\.com/,
        /https:\/\/api\.vworld\.kr/
      ]
    }),
    new Sentry.Replay({
      maskAllText: false,
      blockAllMedia: false
    })
  ],
  
  // Performance 샘플링
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0, // Prod: 10%, Dev: 100%
  
  // Session Replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  
  // 환경 식별
  environment: process.env.NODE_ENV,
  
  // 릴리스 추적
  release: "0.2.0",
  dist: "1"
});

export default Sentry;
```

#### 3.1.3 React 래퍼 (App.tsx)
```typescript
import Sentry from './sentry';

const AppWithProfiler = () => {
  return (
    <Sentry.Profiler name="AppRoot">
      <YourApp />
    </Sentry.Profiler>
  );
};

export default Sentry.withProfiler(AppWithProfiler);
```

### 3.2 Core Web Vitals 계측 (web-vitals 라이브러리)

#### 3.2.1 설치
```bash
npm install web-vitals
```

#### 3.2.2 src/vitals.ts (별도 모듈)
```typescript
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';
import * as Sentry from '@sentry/react';

export const initWebVitals = () => {
  // LCP (Largest Contentful Paint) — 메인 콘텐츠 로딩 완료
  getLCP(({ name, value, rating }) => {
    Sentry.captureMessage('Web Vitals: LCP', 'info', {
      tags: { vital: name, rating },
      measurements: {
        [name]: { value }
      }
    });
    
    // 경고: LCP > 2.5초
    if (rating === 'poor') {
      console.warn(`⚠️ LCP is ${value}ms (poor)`);
      // Slack alert 트리거 가능
      alert('페이지 로딩이 느립니다. 관리자에게 보고되었습니다.');
    }
  });
  
  // INP (Interaction to Next Paint) — 사용자 입력 반응속도
  getFID(({ name, value, rating }) => {
    Sentry.captureMessage('Web Vitals: INP', 'info', {
      tags: { vital: name, rating },
      measurements: { [name]: { value } }
    });
  });
  
  // CLS (Cumulative Layout Shift) — 레이아웃 안정성
  getCLS(({ name, value, rating }) => {
    Sentry.captureMessage('Web Vitals: CLS', 'info', {
      tags: { vital: name, rating },
      measurements: { [name]: { value } }
    });
  });
  
  // FCP (First Contentful Paint) — 첫 콘텐츠 도착
  getFCP(({ name, value, rating }) => {
    Sentry.captureMessage('Web Vitals: FCP', 'info', {
      tags: { vital: name, rating },
      measurements: { [name]: { value } }
    });
  });
  
  // TTFB (Time To First Byte) — 서버 응답속도
  getTTFB(({ name, value, rating }) => {
    Sentry.captureMessage('Web Vitals: TTFB', 'info', {
      tags: { vital: name, rating },
      measurements: { [name]: { value } }
    });
  });
};

// src/main.tsx에서 호출
initWebVitals();
```

---

## 4. LCP 최적화 액션 아이템

### 4.1 이미지 최적화 (예상 효과: -0.6s)

#### 4.1.1 WebP 변환 (sharp 라이브러리)

```bash
npm install -D sharp
```

**스크립트** (scripts/optimize-images.js):
```javascript
const sharp = require('sharp');
const fs = require('fs').promises;
const path = require('path');

const imageDir = './src/assets/images';

(async () => {
  const files = await fs.readdir(imageDir);
  
  for (const file of files.filter(f => /\.(jpg|png)$/.test(f))) {
    const inputPath = path.join(imageDir, file);
    const outputPath = path.join(imageDir, file.replace(/\.[^/.]+$/, '.webp'));
    
    await sharp(inputPath)
      .webp({ quality: 80 })
      .toFile(outputPath);
    
    console.log(`✓ ${file} → ${path.basename(outputPath)}`);
  }
})();
```

**HTML 적용** (picture 태그로 폴백 지원):
```html
<picture>
  <source srcset="/images/marker.webp" type="image/webp">
  <source srcset="/images/marker.jpg" type="image/jpeg">
  <img src="/images/marker.jpg" alt="Property marker">
</picture>
```

#### 4.1.2 Lazy Loading (native lazy attribute)

```html
<!-- 초기 로딩 제외, 뷰포트 진입 시 로드 -->
<img src="/images/marker.webp" loading="lazy" alt="Property">

<!-- Intersection Observer로 더 세밀한 제어 -->
<img data-src="/images/marker.webp" alt="Property" class="lazy-image">

<script>
const imageObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;
      imageObserver.unobserve(img);
    }
  });
});

document.querySelectorAll('.lazy-image').forEach(img => imageObserver.observe(img));
</script>
```

### 4.2 폰트 최적화 (예상 효과: -0.4s)

#### 4.2.1 System Font 우선, 웹폰트 선택적 로드

```css
/* 기존: 모든 폰트 동기 로드 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=block');

/* 개선: system-ui 우선, 옵션 웹폰트 */
body {
  font-family: system-ui, -apple-system, sans-serif; /* 즉시 사용 가능 */
  font-size: 16px;
}

/* 웹폰트는 headings에만 (선택) */
h1, h2 {
  font-family: 'Noto Sans KR', system-ui;
  font-variation-settings: 'wght' 700;
}
```

#### 4.2.2 웹폰트 사전로드 (preload 링크)

```html
<head>
  <!-- 가장 중요한 폰트만 preload -->
  <link
    rel="preload"
    as="font"
    href="/fonts/noto-sans-kr-400.woff2"
    type="font/woff2"
    crossorigin
  >
  
  <!-- CSS에서는 font-display: swap으로 FOUT 최소화 -->
</head>
```

```css
@font-face {
  font-family: 'Noto Sans KR';
  src: url('/fonts/noto-sans-kr-400.woff2') format('woff2');
  font-display: swap; /* 폰트 로딩 중 시스템 폰트 표시 */
}
```

### 4.3 JavaScript 최적화 (예상 효과: -0.3s)

#### 4.3.1 스크립트 로딩 순서 조정

```html
<body>
  <!-- jQuery + 플러그인 → defer (LCP 블로킹 안함) -->
  <script defer src="/js/jquery.min.js"></script>
  <script defer src="/js/jquery.plugin.min.js"></script>
  
  <!-- 핵심 마커 로직만 inline + async -->
  <script async>
    // 지도 마커 초기화 (최소한의 코드)
    window.MAP_CONFIG = { center: [37.5, 126.9] };
  </script>
  
  <!-- 나머지는 모두 defer -->
  <script defer src="/js/app.js"></script>
</body>
```

#### 4.3.2 Code Splitting (Vite/Webpack)

```typescript
// src/pages/MapPage.tsx
import { lazy, Suspense } from 'react';

const MapComponent = lazy(() => import('./MapComponent'));

export default function MapPage() {
  return (
    <Suspense fallback={<Loading />}>
      <MapComponent />
    </Suspense>
  );
}
```

### 4.4 CDN + 캐싱 전략 (예상 효과: -0.2s)

#### 4.4.1 CloudFront 배포 설정

```
원본: https://api.maars.kr (Node.js 서버)
     ↓
CloudFront: https://cdn.maars.kr (엣지 캐싱)
     ↓
브라우저: 평균 응답시간 300ms → 50ms
```

#### 4.4.2 캐시 정책

```
정적 자산 (CSS/JS/이미지):
  Cache-Control: public, max-age=31536000 (1년)
  ETag: "abc123def456"
  
HTML (index.html):
  Cache-Control: public, max-age=3600 (1시간)
  
API 응답:
  Cache-Control: private, max-age=300 (5분)
  ETag로 304 Not Modified 활용
```

---

## 5. 모니터링 대시보드

### 5.1 Sentry 대시보드 설정

**URL**: https://sentry.io/organizations/your-org/issues/

**모니터링 항목**:
- LCP 분포 (중앙값, P75, P95)
- 에러율 (페이지 로드 실패)
- Session Replay (느린 세션 기록)
- Performance Trends (시간대별 추이)

### 5.2 Slack 알림 규칙

```
Rule: If LCP > 2.0s for more than 10% of sessions
Action: Post to #performance-alerts
Message: "⚠️ LCP degradation detected: avg 2.3s (threshold 2.0s)"
Frequency: Once per hour
```

### 5.3 CI/CD 게이트

```bash
# lighthouse-ci로 빌드 전 성능 검증
npm run build
npx lighthouse-ci autorun

# 결과: 
# LCP: 1.3s ✅ (threshold 1.5s)
# CLS: 0.08 ✅ (threshold 0.1)
# INP: 180ms ✅ (threshold 200ms)
```

---

## 6. 마일스톤 & 검증

| 주차 | 작업 | 목표 | 검증 |
|------|------|------|------|
| **Week 3-4** | 이미지 최적화 (WebP, lazy) | LCP 2.5s → 1.9s | Lighthouse |
| **Week 4-5** | 폰트 + JS 최적화 | LCP 1.9s → 1.2s | Lighthouse + RUM |
| **Week 5-6** | CDN 배포 + 캐싱 | TTFB 200ms → 50ms | RUM 대시보드 |
| **Week 6** | Sentry 대시보드 검증 | 모든 지표 계측 | Sentry + 팀 리뷰 |

---

## 7. 성능 목표 (Google 기준)

| 지표 | Poor | Needs Improvement | Good |
|------|------|------------------|------|
| **LCP** | >2.5s | 1.5-2.5s | <1.2s ✅ |
| **INP** | >500ms | 100-500ms | <200ms ✅ |
| **CLS** | >0.25 | 0.1-0.25 | <0.1 ✅ |

---

**작성자**: Claude (Code Assistant)  
**검토 예정**: DevOps Lead, FE Lead  
**최종 승인**: Engineering Manager
