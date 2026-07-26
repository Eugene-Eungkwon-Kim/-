# 🎨 AVM 대시보드 Figma 프로토타입 구현 계획

**기반 스타일:** MAARS Loan4U Admin Dashboard  
**작성일:** 2026-06-19  
**버전:** v1.0  

---

## 📋 Figma 프로젝트 구조

```
AVM Dashboard
├─ 01_Design_System
│  ├─ Colors (색상 팔레트)
│  ├─ Typography (타이포그래피)
│  ├─ Components (재사용 가능한 컴포넌트)
│  └─ Icons (아이콘 모음)
│
├─ 02_Pages
│  ├─ Dashboard (메인 대시보드)
│  ├─ Model_Details (모델 상세)
│  ├─ Data_Analysis (데이터 분석)
│  ├─ Settings (설정)
│  └─ Login (로그인)
│
├─ 03_Components
│  ├─ Header
│  ├─ Sidebar
│  ├─ SummaryCard
│  ├─ StatisticCard
│  ├─ DataTable
│  ├─ Chart
│  ├─ Button
│  └─ Modal
│
└─ 04_Responsive
   ├─ Desktop (1920x1080)
   ├─ Tablet (768x1024)
   └─ Mobile (375x667)
```

---

## 🎨 색상 팔레트 (Figma 색상 스타일)

### Primary Colors

```
Create Color Styles:

┌─────────────────────────────────┐
│ Primary/Blue-900                │
│ HEX: #0D47A1                    │
│ RGB: 13, 71, 161               │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ Primary/Blue-700                │
│ HEX: #1565C0                    │
│ RGB: 21, 101, 192              │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ Primary/Blue-500                │
│ HEX: #2196F3                    │
│ RGB: 33, 150, 243              │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ Primary/Blue-300                │
│ HEX: #64B5F6                    │
│ RGB: 100, 181, 246             │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ Primary/Blue-100                │
│ HEX: #E3F2FD                    │
│ RGB: 227, 242, 253             │
└─────────────────────────────────┘
```

### Status Colors

```
Success/Green-500:
├─ HEX: #4CAF50
├─ RGB: 76, 175, 80
└─ Used: 긍정적 상태, 성공 메시지

Warning/Orange-500:
├─ HEX: #FFA726
├─ RGB: 255, 167, 38
└─ Used: 주의 필요, 진행중

Error/Red-500:
├─ HEX: #F44336
├─ RGB: 244, 67, 54
└─ Used: 오류, 실패, 위험한 액션

Info/Cyan-500:
├─ HEX: #29B6F6
├─ RGB: 41, 182, 246
└─ Used: 정보, 알림
```

### Neutral Colors

```
Text/Dark-900:
├─ HEX: #212121
└─ Used: 헤더, 강한 강조

Text/Dark-700:
├─ HEX: #424242
└─ Used: 본문 텍스트

Text/Dark-500:
├─ HEX: #757575
└─ Used: 라벨, 보조 텍스트

Background/White:
├─ HEX: #FFFFFF
└─ Used: 카드, 패널 배경

Background/Gray-50:
├─ HEX: #FAFAFA
└─ Used: 섹션 배경

Background/Gray-100:
├─ HEX: #F5F5F5
└─ Used: 페이지 배경

Border/Gray-200:
├─ HEX: #EEEEEE
└─ Used: 경계선
```

---

## 🧩 컴포넌트 디자인 (Figma)

### 1. SummaryCard 컴포넌트

**Figma 프레임 설정:**
```
프레임 이름: SummaryCard/Default
크기: 300 × 160px
배경: #FFFFFF
반각: 8px
그림자: 0 2px 8px rgba(0,0,0,0.12)

계층 구조:
├─ Background (배경 / 필 #FFFFFF)
├─ LeftBorder (좌측 테두리 / 너비 4px / 색상 #2196F3)
├─ Title (텍스트 / 폰트 14px / 색상 #757575)
├─ Value (텍스트 / 폰트 32px 볼드 / 색상 #2196F3)
├─ Unit (텍스트 / 폰트 14px / 색상 #757575)
├─ Trend (텍스트 / 폰트 12px / 색상 #4CAF50)
└─ Link (텍스트 / 폰트 12px / 색상 #2196F3)
```

**상태 변형:**
```
Default
├─ 배경 #FFFFFF
├─ 그림자 기본

Hover
├─ 배경 #FFFFFF (동일)
├─ 그림자 0 4px 12px rgba(0,0,0,0.15)
└─ Transform: Y -4px (위로 2px)

Active
├─ 배경 #E3F2FD (연한 파란색)
└─ 그림자 강화
```

### 2. StatisticCard 컴포넌트

**Figma 프레임 설정:**
```
프레임 이름: StatisticCard/Default
크기: 180 × 140px
배경: #FFFFFF 또는 #E3F2FD
반각: 8px

계층 구조:
├─ Background
├─ Icon (크기 48×48px / 색상 #2196F3)
├─ Value (텍스트 / 28px 볼드)
├─ Label (텍스트 / 12px / 색상 #757575)
└─ Trend (텍스트 / 11px / 색상 #4CAF50 또는 #F44336)
```

### 3. DataTable 컴포넌트

**Figma 테이블 행 설정:**
```
프레임 이름: DataTable/Row
높이: 48px
배경: #FFFFFF (일반), #FAFAFA (대체)

셀 구성:
├─ Checkbox (20×20px)
├─ Column1 (텍스트)
├─ Column2 (텍스트, 우측 정렬)
├─ Column3 (텍스트 + 아이콘)
└─ Column4 (액션 버튼)

호버 상태:
└─ 배경: #F5F5F5
```

**테이블 헤더:**
```
프레임 이름: DataTable/Header
높이: 56px
배경: #2196F3
색상: #FFFFFF
폰트: 12px 볼드
```

### 4. 차트 컴포넌트

**Line Chart 프레임:**
```
프레임 이름: Chart/LineChart
크기: 600 × 300px
배경: #FFFFFF
그림자: 약함

요소:
├─ Title (텍스트 / 16px 볼드)
├─ ChartArea (배경 #F5F5F5)
├─ Lines (3개 라인)
│  ├─ Line1: #2196F3 (R² Score)
│  ├─ Line2: #4CAF50 (RMSE 추이)
│  └─ Line3: #FFA726 (비교 모델)
├─ XAxis (날짜)
├─ YAxis (수치)
└─ Legend (범례)
```

### 5. 버튼 컴포넌트

**Primary Button:**
```
프레임 이름: Button/Primary/Default
크기: 120 × 40px
배경: #2196F3
테두리: 없음
반경: 4px
텍스트: "확인" / 14px 볼드 / #FFFFFF
패딩: 10px 24px

상태:
├─ Default: 배경 #2196F3
├─ Hover: 배경 #1565C0
├─ Active: 배경 #0D47A1
└─ Disabled: 배경 #BDBDBD / 텍스트 #FFFFFF
```

**Secondary Button:**
```
프레임 이름: Button/Secondary/Default
배경: #F5F5F5
테두리: 1px #E0E0E0
텍스트: #424242

상태:
├─ Default: 배경 #F5F5F5
├─ Hover: 배경 #EEEEEE
└─ Active: 배경 #E0E0E0
```

---

## 📄 페이지 설계

### Dashboard (메인 대시보드) 페이지

**캔버스 크기:** 1920 × 1080px

```
┌─────────────────────────────────────────┐
│ Header (높이: 56px)                     │
│ [로고] [검색] [알림] [사용자]            │
├──────────┬──────────────────────────────┤
│ Sidebar  │ 페이지 제목                   │
│ (170px)  │ 모델 성능 대시보드            │
│          │                              │
│          │ 요약 카드 (3개)               │
│          │ ┌──────┐ ┌──────┐ ┌──────┐  │
│          │ │R²    │ │RMSE  │ │MAE   │  │
│          │ └──────┘ └──────┘ └──────┘  │
│          │                              │
│          │ R² Score 추이 (Chart)        │
│          │ ┌─────────────────────────┐ │
│          │ │                         │ │
│          │ │   Line Chart            │ │
│          │ │                         │ │
│          │ └─────────────────────────┘ │
│          │                              │
│          │ 특성 중요도 & 모델 비교      │
│          │ ┌──────────┐ ┌──────────┐  │
│          │ │ Pie      │ │ Bar      │  │
│          │ │ Chart    │ │ Chart    │  │
│          │ └──────────┘ └──────────┘  │
│          │                              │
│          │ 데이터 품질 테이블           │
│          │ ┌─────────────────────────┐ │
│          │ │ 결과 테이블             │ │
│          │ └─────────────────────────┘ │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Figma 작성 단계:**

1. **프레임 생성**
   - 메인 프레임 (1920×1080)
   - 헤더, 사이드바, 콘텐츠 프레임 각각

2. **레이아웃 그리드 설정**
   - 마진: 16px
   - 컬럼: 12개
   - 행: 자동

3. **컴포넌트 배치**
   - SummaryCard ×3
   - Chart ×2
   - DataTable ×1
   - Button ×2-3

4. **인터랙션 추가**
   - 호버 상태
   - 클릭 상태
   - 로딩 상태

---

## 📐 반응형 레이아웃

### Desktop View (1920px)

```
3-컬럼 레이아웃:
┌─────────────────────────────┐
│ SummaryCard │ SummaryCard │ SummaryCard
├─────────────────────────────┤
│ LineChart (전체 너비)        │
├─────────────────────────────┤
│ PieChart    │ BarChart    │ (각 50%)
├─────────────────────────────┤
│ DataTable (전체 너비)        │
└─────────────────────────────┘
```

### Tablet View (768px)

```
2-컬럼 레이아웃:
┌──────────────┐
│ SummaryCard  │
├──────────────┤
│ SummaryCard  │
├──────────────┤
│ SummaryCard  │
├──────────────┤
│ LineChart    │
├──────────────┤
│ PieChart     │
├──────────────┤
│ BarChart     │
├──────────────┤
│ DataTable    │
└──────────────┘
```

### Mobile View (375px)

```
1-컬럼 레이아웃:
┌──────┐
│Card1 │
├──────┤
│Card2 │
├──────┤
│Card3 │
├──────┤
│Chart │
├──────┤
│Table │
└──────┘
```

---

## 🎬 프로토타입 인터랙션

### Figma Prototype 설정

**페이지 네비게이션:**
```
Dashboard 페이지의 Sidebar 메뉴 항목
├─ "모델 상세" 클릭 → Model Details 페이지로 이동
├─ "데이터 분석" 클릭 → Data Analysis 페이지로 이동
└─ "설정" 클릭 → Settings 페이지로 이동

모든 페이지:
└─ "뒤로 가기" 버튼 → 이전 페이지로 이동
```

**컴포넌트 인터랙션:**
```
SummaryCard:
└─ Hover → 그림자 강화, Y 위치 -4px
└─ Click → 상세 모달 열기

DataTable 행:
└─ Hover → 배경색 #F5F5F5로 변경
└─ Click → 상세 페이지로 이동

버튼:
└─ Hover → 배경색 변경
└─ Click → 액션 수행 (모달 열기 등)
```

---

## 🎨 개발 전략

### Phase 1: Design System (1주)

```
Week 1:
├─ Day 1-2: 색상, 타이포그래피 스타일 생성
├─ Day 3-4: 기본 컴포넌트 디자인 (Button, Input, Card)
└─ Day 5-7: 고급 컴포넌트 (Table, Chart, Modal)
```

### Phase 2: Pages (2주)

```
Week 2-3:
├─ Week 2: Dashboard, Model Details 페이지
└─ Week 3: Data Analysis, Settings, Login 페이지
```

### Phase 3: Prototype & Documentation (1주)

```
Week 4:
├─ Day 1-3: 프로토타입 인터랙션 설정
├─ Day 4-5: 문서화 (Figma Specs 생성)
└─ Day 6-7: QA 및 최종 검토
```

---

## 📊 Figma에서 Handoff

### 개발자를 위한 Specs 생성

```
1. Figma Inspect 활성화
   └─ 색상, 글꼴, 간격 자동 추출

2. Design Tokens 내보내기
   └─ JSON 형식으로 색상, 타이포그래피 내보내기

3. Component Library 공개
   └─ 개발팀이 Figma에서 컴포넌트 검토 가능

4. Prototype Link 공유
   └─ 인터랙션 검증 및 피드백
```

### 개발 스택 연동

```
Figma Plugins:
├─ Figma to React: 컴포넌트 코드 생성
├─ Tailwind CSS: CSS 코드 추출
└─ Tokens Studio: 디자인 토큰 관리

자동화:
└─ GitHub Actions로 Figma에서 코드 동기화
```

---

## 📋 Figma 파일 체크리스트

```
Design System:
[ ] 색상 스타일 (15개+)
[ ] 타이포그래피 스타일 (10개+)
[ ] 그리드 시스템
[ ] 아이콘 라이브러리

Components:
[ ] Button (3개 상태)
[ ] Input (4개 상태)
[ ] Card (3개 변형)
[ ] Table (헤더, 행, 바닥글)
[ ] Chart (Line, Bar, Pie)
[ ] Modal
[ ] Sidebar
[ ] Header

Pages:
[ ] Dashboard
[ ] Model Details
[ ] Data Analysis
[ ] Settings
[ ] Login
[ ] 404 Not Found

Responsive:
[ ] Desktop 프레임
[ ] Tablet 프레임
[ ] Mobile 프레임

Prototype:
[ ] 페이지 링크
[ ] 컴포넌트 인터랙션
[ ] 전환 효과 정의
```

---

## 🚀 구현 타임라인

```
2026-06-21: Figma 디자인 시작
├─ 1주: Design System 완성
├─ 2주: 모든 페이지 디자인
├─ 3주: 프로토타입 완성
└─ 4주: 개발팀 Handoff

2026-07-19: 프론트엔드 개발 시작
├─ 2주: 기본 페이지 구현
├─ 2주: 상세 기능 구현
└─ 1주: 반응형 테스트 및 최적화

2026-08-20: 백엔드 통합
├─ 1주: API 연동
├─ 1주: 실시간 데이터 스트리밍
└─ 1주: 배포 준비
```

---

**작성자:** Design Team  
**협력:** Development Team  
**최종 수정:** 2026-06-19
