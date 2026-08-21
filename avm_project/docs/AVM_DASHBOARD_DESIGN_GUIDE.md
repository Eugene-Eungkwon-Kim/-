# 🎨 AVM 대시보드 디자인 가이드

## MAARS Loan4U 스타일 기반 부동산 자동감정 모델 대시보드

**작성일:** 2026-06-19  
**버전:** v1.0  
**기반 스타일:** MAARS Loan4U Admin Dashboard  

---

## 📋 목차

1. [디자인 철학](#디자인-철학)
2. [색상 팔레트](#색상-팔레트)
3. [레이아웃 구조](#레이아웃-구조)
4. [핵심 컴포넌트](#핵심-컴포넌트)
5. [페이지별 디자인](#페이지별-디자인)
6. [구현 가이드](#구현-가이드)

---

## 🎨 디자인 철학

### 목표

```
✨ 복잡한 부동산 데이터를 직관적이고 아름답게 표현
✨ 사용자 친화적인 인터페이스로 의사결정 촉진
✨ 전문성과 신뢰성을 시각적으로 전달
✨ 모든 수준의 사용자가 쉽게 이해할 수 있도록 설계
```

### 원칙

```
1️⃣ 명확성 (Clarity)
   └─ 정보 계층 구조가 명확함
   └─ 혼란 없는 시각적 흐름
   └─ 의도가 명확한 CTA 버튼

2️⃣ 일관성 (Consistency)
   └─ 전체 대시보드에서 일관된 스타일
   └─ 동일한 유형의 데이터는 동일한 표현
   └─ 재사용 가능한 컴포넌트 시스템

3️⃣ 효율성 (Efficiency)
   └─ 필요한 정보를 빠르게 찾을 수 있음
   └─ 최소한의 클릭으로 액션 수행
   └─ 반응성 좋은 UI/UX

4️⃣ 미적 완성도 (Aesthetics)
   └─ 현대적이고 세련된 디자인
   └─ 프로페셔널한 이미지 전달
   └─ 사용 기쁨 (Delight)
```

---

## 🎨 색상 팔레트

### Primary Colors (주요 색상)

```
파란색 (Primary Blue)
├─ #1565C0 (Dark)    - 버튼, 선택된 항목
├─ #2196F3 (Main)    - 주요 요소, 헤더
├─ #64B5F6 (Light)   - 호버 상태
└─ #E3F2FD (Very Light) - 배경 하이라이트

사용처:
├─ 헤더 배경
├─ 활성 탭
├─ 주요 버튼
├─ 링크
└─ 강조 텍스트
```

### Status Colors (상태 색상)

```
성공 (Success - Green)
├─ #4CAF50 (Main)
├─ #66BB6A (Light)
└─ #C8E6C9 (Very Light)
└─ 사용처: 긍정적 수치, 승인 상태, 완료

경고 (Warning - Orange)
├─ #FFA726 (Main)
├─ #FFB74D (Light)
└─ #FFE0B2 (Very Light)
└─ 사용처: 주의 필요, 진행중, 업데이트

오류 (Error - Red)
├─ #F44336 (Main)
├─ #EF5350 (Light)
└─ #FFCDD2 (Very Light)
└─ 사용처: 오류, 부정적 수치, 거절

정보 (Info - Cyan)
├─ #29B6F6 (Main)
├─ #4FC3F7 (Light)
└─ #B3E5FC (Very Light)
└─ 사용처: 정보 알림, 추가 정보
```

### Neutral Colors (중립 색상)

```
밝은 배경
├─ #FFFFFF (White)       - 카드, 패널 배경
├─ #FAFAFA (Off-White)   - 섹션 배경
├─ #F5F5F5 (Light Gray)  - 페이지 배경
└─ #EEEEEE (Lighter Gray) - 비활성 상태

어두운 텍스트
├─ #212121 (Almost Black) - 헤더 텍스트
├─ #424242 (Dark Gray)   - 본문 텍스트
├─ #757575 (Medium Gray) - 라벨, 보조 텍스트
└─ #BDBDBD (Light Gray)  - 비활성 텍스트
```

### Color Usage Example

```
차트 색상 (시계열 데이터):
├─ Line 1: #2196F3 (파란색)
├─ Line 2: #4CAF50 (녹색)
├─ Line 3: #FFA726 (주황색)
└─ Line 4: #F44336 (빨간색)

바 차트 (카테고리별 비교):
├─ 긍정: #4CAF50
├─ 중립: #2196F3
└─ 부정: #F44336
```

---

## 📐 레이아웃 구조

### 전체 레이아웃

```
┌────────────────────────────────────────────────────────────┐
│  LOGO    메뉴 1  메뉴 2  메뉴 3              검색  사용자  설정  │ 헤더 (56px)
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ 사이드   │                                                  │
│ 바       │          메인 콘텐츠 영역                         │
│ (170px)  │                                                  │
│          │                                                  │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### 사이드바 (Sidebar)

```
구조:
├─ 로고/브랜드 (48px)
├─ 네비게이션 메뉴
│  ├─ 아이콘 (24px)
│  ├─ 텍스트 (14px)
│  └─ 활성 표시 (좌측 테두리)
├─ 구분선
└─ 추가 메뉴 (설정, 로그아웃 등)

스타일:
├─ 배경: #FFFFFF (흰색)
├─ 경계: 1px #E0E0E0 (밝은 회색)
├─ 텍스트: #424242 (어두운 회색)
└─ 호버: #F5F5F5 (밝은 배경)
└─ 활성: #2196F3 (파란색 테두리)
```

### 헤더 (Header)

```
구조:
├─ 좌측: 로고
├─ 중앙: 검색바
└─ 우측: 알림, 사용자 정보, 설정

스타일:
├─ 배경: #2196F3 (파란색)
├─ 텍스트: #FFFFFF (흰색)
├─ 높이: 56px
├─ 그림자: 0 2px 4px rgba(0,0,0,0.1)
└─ 고정 상단
```

### 메인 콘텐츠 (Main Content)

```
기본 마진/패딩:
├─ 페이지 패딩: 24px
├─ 섹션 간격: 24px
├─ 컴포넌트 간격: 16px
└─ 카드 패딩: 20px

반응형 그리드:
├─ 데스크톱 (> 1200px): 3-4 컬럼
├─ 태블릿 (768px ~ 1200px): 2 컬럼
└─ 모바일 (< 768px): 1 컬럼
```

---

## 🧩 핵심 컴포넌트

### 1. 요약 카드 (Summary Card)

**용도:** 주요 KPI 표시

```
┌─────────────────────────────────┐
│  모델 성능 (헤더)                │
├─────────────────────────────────┤
│                                 │
│   R² Score: 0.8520             │
│   (큰 숫자, 파란색)              │
│                                 │
│   RMSE: 51.2M원                │
│   MAE: 39.8M원                 │
│                                 │
│  [자세히 보기] (링크)            │
└─────────────────────────────────┘

스타일:
├─ 배경: #FFFFFF (흰색)
├─ 경계: 1px #E0E0E0
├─ 반경: 8px (둥근 모서리)
├─ 그림자: 0 1px 3px rgba(0,0,0,0.12)
├─ 패딩: 20px
├─ 호버: 그림자 증가, 약간 상승
└─ 헤더: 파란색 좌측 테두리 (4px)
```

### 2. 통계 카드 (Statistic Card)

**용도:** 숫자와 아이콘으로 통계 표시

```
┌─────────────────────────────────┐
│        특성 중요도               │
│                                 │
│        📊  면적                 │
│        38.2%                   │
│        (녹색으로 강조)           │
│                                 │
│        추세: ↑ 2.1% (초록색)   │
└─────────────────────────────────┘

스타일:
├─ 아이콘: 48px, 파란색
├─ 숫자: 32px 볼드
├─ 라벨: 14px 그레이
├─ 배경: 흰색 또는 연한 파란색
├─ 레이아웃: 플렉스 (아이콘 좌, 텍스트 우)
└─ 추세: 초록색(↑) 또는 빨간색(↓)
```

### 3. 테이블 (Data Table)

**용도:** 상세 데이터 표시

```
┌─────────────────────────────────────────┐
│ 특성  │  중요도  │  영향도  │  상태      │
├─────────────────────────────────────────┤
│ 면적  │  38.2%   │ 매우높음 │ ✅        │
│ 지역  │  29.5%   │ 매우높음 │ ✅        │
│ 거래일│  16.3%   │ 높음    │ ✅        │
└─────────────────────────────────────────┘

스타일:
├─ 헤더: #2196F3 배경, 흰색 텍스트
├─ 행: 교대로 #FFFFFF, #FAFAFA
├─ 호버: #F5F5F5
├─ 경계: 1px #E0E0E0 (행 구분)
├─ 패딩: 12px 16px
├─ 정렬: 좌측 텍스트, 우측 숫자
└─ 스크롤: 수평 스크롤 가능
```

### 4. 차트 (Chart)

**용도:** 데이터 시각화

```
성능 추이 (Line Chart):
├─ X축: 날짜/기간
├─ Y축: R² Score
├─ 라인: #2196F3 (파란색)
├─ 배경: 연한 파란색 (#E3F2FD)
└─ 포인트: 호버 시 값 표시

바 차트 (Bar Chart):
├─ X축: 모델명
├─ Y축: 성능 점수
├─ 컬러: 각 모델별 구분색
└─ 범례: 우측 또는 하단

파이 차트 (Pie Chart):
├─ 각도: 데이터 비율
├─ 색상: 색상 팔레트 순서
├─ 범례: 인쇄
└─ 라벨: 퍼센트 및 값 표시

공통:
├─ 배경: #FFFFFF
├─ 그림자: 약한 그림자
├─ 인터랙션: 호버 시 정보 표시
└─ 반응형: 화면 크기에 따라 리사이징
```

### 5. 버튼 (Button)

```
Primary Button:
├─ 배경: #2196F3 (파란색)
├─ 텍스트: #FFFFFF (흰색)
├─ 패딩: 10px 24px
├─ 반경: 4px
├─ 호버: #1565C0 (어두운 파란색)
├─ 활성: #0D47A1 (더 어두운 파란색)
└─ 사용: 주요 액션 (저장, 확인 등)

Secondary Button:
├─ 배경: #F5F5F5 (밝은 회색)
├─ 텍스트: #424242 (어두운 회색)
├─ 경계: 1px #E0E0E0
├─ 호버: #EEEEEE
└─ 사용: 보조 액션 (취소, 돌아가기 등)

Danger Button:
├─ 배경: #F44336 (빨간색)
├─ 텍스트: #FFFFFF (흰색)
├─ 호버: #D32F2F (어두운 빨강)
└─ 사용: 삭제, 리셋 등 위험한 액션
```

### 6. 모달/팝업 (Modal)

```
┌─────────────────────────────────┐
│  제목                       ✕  │
├─────────────────────────────────┤
│                                 │
│  모달 콘텐츠                     │
│                                 │
├─────────────────────────────────┤
│             [취소]  [확인]       │
└─────────────────────────────────┘

스타일:
├─ 백드롭: rgba(0,0,0,0.5) (반투명)
├─ 배경: #FFFFFF (흰색)
├─ 경계: 1px #E0E0E0
├─ 반각: 8px
├─ 그림자: 0 5px 25px rgba(0,0,0,0.2)
├─ 최대 너비: 600px
├─ Z-index: 1000
└─ 중앙 정렬: 화면 중앙
```

---

## 📄 페이지별 디자인

### 1. 대시보드 메인 페이지

**구성:**
```
┌──────────────────────────────────────────────────┐
│ 페이지 제목: 모델 성능 대시보드                    │
├──────────────────────────────────────────────────┤
│                                                  │
│ 상단 요약 (3개 카드)                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│ │ R² Score    │ │ RMSE        │ │ MAE         ││
│ │  0.8520     │ │ 51.2M원     │ │ 39.8M원     ││
│ └─────────────┘ └─────────────┘ └─────────────┘│
│                                                  │
│ 성능 추이 (차트)                                 │
│ ┌────────────────────────────────────────────┐ │
│ │                                            │ │
│ │      R² Score 추이 (Line Chart)           │ │
│ │                                            │ │
│ └────────────────────────────────────────────┘ │
│                                                  │
│ 특성 중요도 (2개 섹션)                          │
│ ┌─────────────────────────────────────────┐   │
│ │ 특성 중요도         │ 모델 성능 비교     │   │
│ │ • 면적 38.2%       │ • Random Forest   │   │
│ │ • 지역 29.5%       │ • GB: 0.8312      │   │
│ │ • 거래일 16.3%     │ • XGBoost: 0.8156│   │
│ └─────────────────────────────────────────┘   │
│                                                  │
│ 데이터 품질 (테이블)                            │
│ ┌──────────────────────────────────────────┐  │
│ │ 항목        │ 현황      │ 상태           │  │
│ │ 데이터 행수 │ 85,000개  │ ✅ 양호        │  │
│ │ 결측치율    │ 1.2%     │ ✅ 양호        │  │
│ │ 이상치     │ 2.1%     │ ⚠️ 주의        │  │
│ └──────────────────────────────────────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 2. 모델 상세 페이지

**구성:**
```
모델 선택 탭: [ Linear ] [ Tree ] [Forest] [GB] [XGB] [LGB]

선택된 모델: Gradient Boosting

성능 메트릭:
┌────────────────────────────────────┐
│ R² Score: 0.8312 ✅               │
│ RMSE: 58.1M원                      │
│ MAE: 46.3M원                       │
│ 학습 시간: 45초                    │
│ 최종 업데이트: 2026-06-19          │
└────────────────────────────────────┘

하이퍼파라미터:
┌────────────────────────────────────┐
│ n_estimators: 300                  │
│ learning_rate: 0.1                 │
│ max_depth: 7                       │
│ subsample: 0.8                     │
│ ...                                │
└────────────────────────────────────┘

Confusion Matrix / Feature Importance 차트
```

### 3. 데이터 분석 페이지

**구성:**
```
데이터 소스 선택:
[ D-드라이브 ] [ Vworld ] [ Opinet ] [ 실시간 ]

선택: Vworld

통계 요약:
┌────────────────────────────────────┐
│ 총 데이터: 85,000행                │
│ 위도/경도: 84,230개 ✅            │
│ 성공률: 99.6%                      │
│ 마지막 업데이트: 2025-06-19        │
└────────────────────────────────────┘

상세 분석:
- 지역별 데이터 분포
- 좌표 정확도 분석
- 이상치 탐지 결과
- 시계열 분석
```

### 4. 설정 페이지

**구성:**
```
설정 카테고리:
[ API 설정 ] [ 모델 설정 ] [ 알림 설정 ] [ 사용자 ]

API 설정:
┌────────────────────────────────────┐
│ Vworld API 키: [****]              │
│ □ Vworld 강화 활성화               │
│                                    │
│ Opinet API 키: [****]              │
│ □ Opinet 강화 활성화               │
│                                    │
│ [저장] [테스트]                    │
└────────────────────────────────────┘

모델 설정:
┌────────────────────────────────────┐
│ □ 자동 재학습 (주간)               │
│ □ 자동 업데이트                    │
│ 알림 메일: user@example.com        │
│ [저장]                             │
└────────────────────────────────────┘
```

---

## 💻 구현 가이드

### 기술 스택

```
프론트엔드:
├─ React.js 18+
├─ Next.js 13+ (SSR/SSG)
├─ Tailwind CSS (스타일링)
├─ Recharts 또는 Chart.js (차트)
├─ React Query (데이터 페칭)
└─ Zustand 또는 Redux (상태관리)

백엔드:
├─ FastAPI (Python)
├─ Uvicorn (서버)
└─ WebSocket (실시간 데이터)

호스팅:
├─ Vercel 또는 Netlify (프론트엔드)
└─ Google Cloud Run (백엔드)
```

### 폴더 구조

```
frontend/
├─ components/
│  ├─ Header.tsx
│  ├─ Sidebar.tsx
│  ├─ SummaryCard.tsx
│  ├─ StatisticCard.tsx
│  ├─ DataTable.tsx
│  ├─ Chart/
│  │  ├─ LineChart.tsx
│  │  ├─ BarChart.tsx
│  │  └─ PieChart.tsx
│  └─ Modal.tsx
│
├─ pages/
│  ├─ dashboard.tsx
│  ├─ models.tsx
│  ├─ data-analysis.tsx
│  └─ settings.tsx
│
├─ styles/
│  ├─ globals.css
│  ├─ colors.css
│  └─ components.css
│
└─ utils/
   ├─ api.ts
   └─ constants.ts
```

### CSS/Tailwind 예제

```css
/* 요약 카드 */
.summary-card {
  @apply bg-white rounded-lg shadow p-5 
         border-l-4 border-blue-500 
         hover:shadow-md transition-shadow;
}

/* 버튼 */
.btn-primary {
  @apply bg-blue-500 text-white px-6 py-2 rounded
         hover:bg-blue-700 active:bg-blue-900
         transition-colors;
}

/* 테이블 */
.data-table thead {
  @apply bg-blue-500 text-white;
}

.data-table tbody tr:hover {
  @apply bg-gray-100;
}

/* 차트 컨테이너 */
.chart-container {
  @apply bg-white rounded-lg shadow p-5
         w-full h-80;
}
```

### React 컴포넌트 예제

```typescript
// SummaryCard.tsx
import React from 'react';

interface SummaryCardProps {
  title: string;
  value: number | string;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: number;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  value,
  unit,
  trend,
  trendValue
}) => {
  const trendColor = 
    trend === 'up' ? 'text-green-500' :
    trend === 'down' ? 'text-red-500' :
    'text-gray-500';

  return (
    <div className="summary-card">
      <h3 className="text-gray-600 text-sm font-medium mb-4">
        {title}
      </h3>
      
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-3xl font-bold text-blue-600">
          {value}
        </span>
        {unit && <span className="text-gray-500">{unit}</span>}
      </div>

      {trend && trendValue && (
        <div className={`text-sm ${trendColor}`}>
          {trend === 'up' ? '↑' : '↓'} {trendValue}%
        </div>
      )}

      <a href="#" className="text-blue-500 text-sm mt-4 block">
        자세히 보기 →
      </a>
    </div>
  );
};
```

---

## 🎬 애니메이션 & 인터랙션

### 페이드 인

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 0.3s ease-in;
}
```

### 슬라이드 업

```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-up {
  animation: slideUp 0.4s ease-out;
}
```

### 호버 효과

```css
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}
```

---

## 📱 반응형 디자인

### 미디어 쿼리

```css
/* 모바일 (< 640px) */
@media (max-width: 640px) {
  .sidebar {
    width: 100%;
    height: 56px;
    flex-direction: row;
  }
  
  .main-content {
    grid-template-columns: 1fr;
  }
}

/* 태블릿 (640px ~ 1024px) */
@media (min-width: 640px) and (max-width: 1024px) {
  .main-content {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 데스크톱 (> 1024px) */
@media (min-width: 1024px) {
  .main-content {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## ♿ 접근성 (Accessibility)

### WCAG 2.1 준수

```
✅ 색상만으로 정보 전달 금지
   └─ 텍스트 라벨도 함께 제공

✅ 충분한 색상 대비
   └─ 텍스트: 4.5:1 이상

✅ 키보드 네비게이션
   └─ Tab 키로 모든 요소 접근 가능

✅ 스크린 리더 지원
   └─ ARIA 라벨 추가

✅ 포커스 표시
   └─ 명확한 포커스 아웃라인
```

---

## 🎨 브랜드 가이드라인

### 로고

```
┌─────────────────────┐
│  AVM DASHBOARD      │
│  (로고)              │
└─────────────────────┘

사이즈: 최소 48px × 48px
명시 공간: 로고 주변 16px
색상: 원본 컬러 또는 단색 (흰색/파란색)
```

### 타이포그래피

```
폰트 패밀리:
├─ 메인: 'Segoe UI', 'Noto Sans KR', sans-serif
├─ 코드: 'Monaco', 'Courier New', monospace
└─ 폴백: -apple-system, BlinkMacSystemFont

사이즈 스케일:
├─ H1: 32px (페이지 제목)
├─ H2: 24px (섹션 제목)
├─ H3: 18px (서브 제목)
├─ Body: 14px (본문)
└─ Caption: 12px (설명)

가중치:
├─ 300: Light (사용 최소화)
├─ 400: Regular (기본)
├─ 500: Medium (강조)
├─ 600: SemiBold (제목)
└─ 700: Bold (매우 강조)

줄 높이:
├─ 제목: 1.2
├─ 본문: 1.5
└─ 코드: 1.6
```

---

## 🚀 배포 체크리스트

```
디자인 검증:
[ ] 모든 페이지 반응형 테스트
[ ] 색상 대비 검증 (WCAG 준수)
[ ] 폰트 로딩 성능 확인
[ ] 이미지 최적화 (WebP)

성능:
[ ] Lighthouse 점수 90+
[ ] First Contentful Paint < 1.5s
[ ] Cumulative Layout Shift < 0.1

호환성:
[ ] Chrome 최신 버전
[ ] Firefox 최신 버전
[ ] Safari 최신 버전
[ ] Edge 최신 버전

보안:
[ ] HTTPS 적용
[ ] CSP 헤더 설정
[ ] XSS 방지 대책
[ ] CSRF 토큰 적용
```

---

## 📚 참고 자료

### 디자인 시스템
- Material Design: https://material.io
- Tailwind CSS: https://tailwindcss.com
- Ant Design: https://ant.design

### 차트 라이브러리
- Recharts: https://recharts.org
- Chart.js: https://www.chartjs.org
- Apache ECharts: https://echarts.apache.org

### 아이콘
- Feather Icons: https://feathericons.com
- Material Icons: https://fonts.google.com/icons
- Heroicons: https://heroicons.com

---

**작성자:** AI Development Team  
**최종 수정:** 2026-06-19  
**라이선스:** MIT

**상태:** ✅ 설계 가이드 완성
