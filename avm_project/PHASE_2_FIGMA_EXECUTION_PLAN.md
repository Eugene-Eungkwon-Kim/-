# 🎨 Phase 2: Figma 대시보드 디자인 - 실행 계획서

**시작일:** 2026-06-19  
**기간:** 4주 (2026-06-19 ~ 2026-07-17)  
**목표:** 5개 페이지의 완전한 Figma 프로토타입 + React 컴포넌트 구조  
**기반:** MAARS Loan4U Admin Dashboard 스타일

---

## 📅 주간별 실행 계획

### 주차 1 (2026-06-19 ~ 2026-06-23): 디자인 시스템 & 기초

**목표:** Figma 프로젝트 세팅 + 디자인 시스템 완성

#### 1.1 Figma 프로젝트 생성 (1일)
```
Task: Create Figma Project
├─ Project 이름: "AVM Dashboard"
├─ Team Space: Private
├─ Pages 구조 생성
└─ 초대 멤버 설정
```

**실행 단계:**
1. Figma 로그인
2. "New File" → "AVM Dashboard" 생성
3. 페이지 구조 생성:
   - 01_Design_System
   - 02_Pages
   - 03_Components
   - 04_Responsive
   - 05_Interactions
4. 공유 링크 생성

---

#### 1.2 색상 팔레트 정의 (1일)

**Figma에서 색상 스타일 생성:**

```
Primary Colors:
├─ Blue-900: #0D47A1 (다크 배경)
├─ Blue-700: #1565C0 (강조)
├─ Blue-500: #2196F3 (주요 액션)
├─ Blue-300: #64B5F6 (호버)
└─ Blue-100: #E3F2FD (배경)

Status Colors:
├─ Success (Green): #4CAF50
├─ Warning (Orange): #FFA726
├─ Error (Red): #F44336
└─ Info (Cyan): #00BCD4

Neutral Colors:
├─ Gray-900: #212121 (텍스트)
├─ Gray-700: #424242 (보조 텍스트)
├─ Gray-500: #757575 (플레이스홀더)
├─ Gray-300: #E0E0E0 (보더)
└─ Gray-100: #F5F5F5 (배경)

Semantic Colors:
├─ Background: #FFFFFF
├─ Surface: #F8F9FA
├─ Border: #E0E0E0
└─ Shadow: rgba(0,0,0,0.1)
```

**작업 순서:**
1. Edit → Colors 탭 열기
2. + 버튼으로 새 색상 생성
3. 각 색상에 Group 이름 추가 (e.g., "Primary/Blue-500")
4. 모든 색상 스타일 정의

---

#### 1.3 타이포그래피 정의 (1일)

**Figma에서 텍스트 스타일 생성:**

```
Heading Styles:
├─ H1 (Display): 36px, Weight 700, Line-height 44px
├─ H2 (Large): 28px, Weight 600, Line-height 36px
├─ H3 (Medium): 24px, Weight 600, Line-height 32px
└─ H4 (Small): 20px, Weight 600, Line-height 28px

Body Styles:
├─ Body-Large: 16px, Weight 400, Line-height 24px
├─ Body-Regular: 14px, Weight 400, Line-height 20px
└─ Body-Small: 12px, Weight 400, Line-height 16px

Label Styles:
├─ Label-Bold: 12px, Weight 600, Line-height 16px
└─ Label-Regular: 11px, Weight 400, Line-height 16px

Code Styles:
└─ Monospace: 13px, Font: "SF Mono" or "Courier New"
```

**작업 순서:**
1. Assets 탭 → Text Styles
2. 각 스타일별로 텍스트 컴포넌트 생성
3. 폰트, 크기, 가중치, 줄 간격 설정
4. 색상 지정 (대부분 Gray-900)

**추천 폰트:**
- 한글: Noto Sans CJK KR (Google Fonts)
- 영문: Inter 또는 SF Pro Display

---

#### 1.4 기본 컴포넌트 생성 (2일)

**Figma 컴포넌트 라이브러리 구축:**

##### Button Component
```
States:
├─ Primary
│  ├─ Default (Blue-500 배경, White 텍스트)
│  ├─ Hover (Blue-700, 약간 축소)
│  ├─ Active (Blue-900)
│  └─ Disabled (Gray-300)
├─ Secondary
│  ├─ Default (Blue-100 배경, Blue-700 텍스트)
│  ├─ Hover (Blue-300)
│  ├─ Active (Blue-500)
│  └─ Disabled (Gray-100)
└─ Danger
   ├─ Default (Red-500 배경)
   ├─ Hover (Red-700)
   ├─ Active (Red-900)
   └─ Disabled (Gray-300)

Sizes:
├─ Large: 44px 높이, 16px 패딩
├─ Medium: 36px 높이, 12px 패딩
└─ Small: 28px 높이, 8px 패딩

Content:
├─ Text only
├─ Icon + Text
└─ Icon only
```

**Figma에서 구현:**
1. Frame 생성 (e.g., "Button/Primary/Default")
2. 배경 Rectangle (반경 4px)
3. 텍스트 추가 (Body-Regular)
4. 아이콘 추가 (좌측 8px 마진)
5. Constraints 설정 (Hug contents)
6. Component로 변환
7. Variants 생성 (State, Size, Content)

##### Input Field Component
```
States:
├─ Default (Gray-100 배경, Gray-300 보더)
├─ Focused (Blue-100 배경, Blue-500 보더, 2px)
├─ Filled (값 입력됨)
├─ Error (Red-500 보더, Red-100 배경)
└─ Disabled (Gray-50 배경)

Size:
├─ Large: 44px
├─ Medium: 36px
└─ Small: 28px

Content:
├─ Label (위쪽)
├─ Placeholder text
├─ Helper text (아래)
└─ Error message
```

##### Card Component
```
Structure:
├─ Padding: 16px
├─ 배경: White
├─ 보더: 1px Gray-300
├─ 반경: 8px
└─ Shadow: 0 2px 8px rgba(0,0,0,0.1)

Variants:
├─ Default (기본)
├─ Elevated (Shadow 더 진함)
└─ Outlined (보더만)
```

---

### 주차 2 (2026-06-26 ~ 2026-06-30): 페이지 프로토타입 (1/2)

**목표:** Dashboard & Model Details 페이지 완성

#### 2.1 Dashboard 페이지 (2.5일)

**레이아웃:**
```
Desktop (1920x1080):
┌─────────────────────────────────────────────────┐
│ Header (56px)                                    │
├──────┬──────────────────────────────────────────┤
│      │                                           │
│ 170px│ Main Content Area                        │
│ Side │                                           │
│ bar  ├─────────────────────────────────────────┤
│      │ Dashboard / Performance Summary           │
│      ├─────────────────────────────────────────┤
│      │                                           │
│      │ [SummaryCard] [SummaryCard] [SummaryCard]│
│      │                                           │
│      ├─────────────────────────────────────────┤
│      │ Model Performance Chart                  │
│      │ ┌───────────────────────────────────────┐│
│      │ │ Line Chart: R² Trend (10주)           ││
│      │ └───────────────────────────────────────┘│
│      │                                           │
│      ├─────────────────────────────────────────┤
│      │ Recent Trainings                        │
│      │ ┌───────────────────────────────────────┐│
│      │ │ Table: Date|Model|R²|Status          ││
│      │ └───────────────────────────────────────┘│
└──────┴──────────────────────────────────────────┘
```

**Figma 구현 단계:**

1. **Frame 생성**
   ```
   Frame: "Dashboard_Desktop"
   Size: 1920x1080
   Background: Gray-100
   ```

2. **Header 추가**
   ```
   Component: Header
   ├─ Logo (좌측)
   ├─ Navigation (중앙)
   ├─ User Menu (우측)
   └─ Height: 56px
   ```

3. **Sidebar 추가**
   ```
   Component: Sidebar
   ├─ Width: 170px
   ├─ Navigation Items:
   │  ├─ Dashboard (활성)
   │  ├─ Model Details
   │  ├─ Data Analysis
   │  ├─ Settings
   │  └─ Logout
   └─ Position: 좌측
   ```

4. **콘텐츠 영역 구성**
   ```
   Main Content:
   ├─ 패딩: 20px
   ├─ 제목: "대시보드 - 모델 성능 모니터링"
   └─ 콘텐츠:
      ├─ Summary Cards (3개 행)
      ├─ Performance Chart
      ├─ Recent Trainings Table
      └─ Quick Actions
   ```

5. **SummaryCard 레이아웃**
   ```
   For each card (3개):
   Card {
     ├─ Title: "앙상블 R² 점수"
     ├─ Value: "0.8450"
     ├─ Change: "↑ 0.12%" (Green)
     ├─ Icon: Chart icon (Blue)
     └─ Background: White
   }
   ```

6. **Performance Chart**
   ```
   Chart Container {
     ├─ Title: "R² 추세 (10주)"
     ├─ Legend: 각 모델별 색상
     ├─ Y-Axis: 0.80 ~ 0.85
     ├─ X-Axis: 주 번호
     ├─ Data Points: 10개
     └─ Grid Lines: 옅은 Gray
   }
   ```

7. **Recent Trainings Table**
   ```
   Table {
     Header: [날짜 | 상태 | R² | RMSE | 액션]
     Rows (5개):
       ├─ 2026-06-19 | ✅ 성공 | 0.8450 | 55.2M | [보기]
       ├─ 2026-06-12 | ✅ 성공 | 0.8420 | 55.8M | [보기]
       └─ ...
   }
   ```

---

#### 2.2 Model Details 페이지 (2.5일)

**레이아웃:**
```
Desktop:
┌─────────────────────────────────────────────────┐
│ Header                                           │
├──────┬──────────────────────────────────────────┤
│      │ Model Details / [Model Name]             │
│      ├────────────────────────────────────────┤
│      │ Tabs: Overview | Metrics | Features | ...│
│      ├────────────────────────────────────────┤
│Sidebar│                                        │
│      │ ┌─ Model Information                   │
│      │ │ ├─ Name: XGBoost                    │
│      │ │ ├─ Type: Regression                │
│      │ │ ├─ R²: 0.8420                      │
│      │ │ └─ Last Updated: 2026-06-19       │
│      │ │                                    │
│      │ ├─ Performance Metrics               │
│      │ │ ├─ MAE: 42.5M                     │
│      │ │ ├─ RMSE: 55.8M                    │
│      │ │ └─ MAPE: 5.2%                     │
│      │ │                                    │
│      │ └─ Actions                           │
│      │   ├─ [Download Model]               │
│      │   ├─ [Deploy]                       │
│      │   └─ [Delete]                       │
│      │                                        │
│      │ ┌─ Feature Importance (Chart)       │
│      │ │ Top 10 Features                    │
│      │ └─ Horizontal Bar Chart             │
└──────┴────────────────────────────────────────┘
```

**Figma 구현:**

1. **탭 네비게이션**
   ```
   Tabs Component:
   ├─ Overview (활성)
   ├─ Metrics
   ├─ Features
   ├─ Validation
   └─ Logs
   
   Active Tab: Blue-500 아래선, 텍스트 Bold
   Inactive Tab: Gray-500 텍스트
   ```

2. **모델 정보 패널**
   ```
   Panel {
     Title: "모델 정보"
     Fields:
     ├─ [라벨] [값]
     ├─ Name: XGBoost v20260619_100000
     ├─ Type: Gradient Boosting
     ├─ Created: 2026-06-19 10:00
     ├─ Last Training: 2026-06-19 10:15
     ├─ Data Size: 5,000 rows
     └─ Features: 17
   }
   ```

3. **성능 메트릭**
   ```
   Metrics Grid (2x2):
   ├─ [R²: 0.8420] [MAE: 42.5M]
   └─ [RMSE: 55.8M] [MAPE: 5.2%]
   
   각 메트릭:
   ├─ Label (Gray-700, Small)
   ├─ Value (Blue-900, Large, Bold)
   └─ Comparison (Gray-500, Small, e.g., "vs prev: -0.15%")
   ```

4. **Feature Importance Chart**
   ```
   Horizontal Bar Chart:
   ├─ Top 10 Features
   ├─ X-axis: 0-40%
   ├─ Colors: Gradient Blue
   └─ Labels: 특성명 및 %
   
   Example:
   면적        ▓▓▓▓▓▓▓▓░░ 38.2%
   지역        ▓▓▓▓▓▓░░░░ 28.5%
   거래일      ▓▓▓▓░░░░░░ 15.8%
   ```

5. **액션 버튼**
   ```
   Button Group (세로):
   ├─ [Primary] Download Model (아이콘)
   ├─ [Primary] Deploy to Production
   ├─ [Secondary] View Logs
   └─ [Danger] Delete Model
   
   각 버튼: 전체 너비, 아이콘 좌측
   ```

---

### 주차 3 (2026-07-03 ~ 2026-07-07): 페이지 프로토타입 (2/2)

**목표:** Data Analysis, Settings, Login 페이지 완성

#### 3.1 Data Analysis 페이지 (2일)

**레이아웃:**
```
Main Content:
├─ 필터 바 (상단)
│  └─ [데이터셋] [기간] [상태] [리셋]
├─ 데이터 분포 (2개 차트)
│  ├─ 가격 분포 (히스토그램)
│  └─ 지역별 분포 (원형 차트)
├─ 데이터 품질 메트릭
│  ├─ 총 행: 5,000
│  ├─ 결측치: 15 (0.3%)
│  ├─ 아웃라이어: 125 (2.5%)
│  └─ 데이터 품질: 99.2%
└─ 데이터 테이블 (상세)
   └─ 스크롤 가능, 정렬 가능
```

#### 3.2 Settings 페이지 (1.5일)

**섹션:**
```
Settings {
  ├─ 1. Model Settings
  │  ├─ Auto-retrain 활성화
  │  ├─ Retrain Schedule
  │  └─ Performance Threshold
  │
  ├─ 2. Data Settings
  │  ├─ 데이터 경로
  │  ├─ 전처리 옵션
  │  └─ Feature Engineering
  │
  ├─ 3. Notification Settings
  │  ├─ Email 알림
  │  ├─ Slack 알림
  │  └─ 알림 조건
  │
  └─ 4. System Settings
     ├─ API Key 관리
     ├─ 로그 레벨
     └─ 백업 설정
}
```

#### 3.3 Login 페이지 (0.5일)

**레이아웃:**
```
Center Card {
  ├─ Logo (상단)
  ├─ 제목: "AVM Dashboard"
  ├─ 부제목: "부동산 자동감정 모델 대시보드"
  │
  ├─ Input Fields:
  │  ├─ Email
  │  └─ Password
  │
  ├─ Buttons:
  │  ├─ [Login] (Primary)
  │  └─ Remember me (Checkbox)
  │
  └─ Footer:
     └─ "Forgot password?" (Link)
}
```

---

### 주차 4 (2026-07-10 ~ 2026-07-17): 반응형 & 상호작용

**목표:** 반응형 레이아웃 + 프로토타입 상호작용 + 최종 검수

#### 4.1 반응형 레이아웃 (2일)

**3가지 브레이크포인트 구현:**

```
Breakpoint 1: Desktop (1920x1080)
├─ Sidebar: 170px (고정)
├─ Header: 56px
└─ Content: 자유롭게 확장

Breakpoint 2: Tablet (768x1024)
├─ Sidebar: 120px (축소)
├─ Header: 48px
├─ Content: 제한된 너비
└─ 2열 레이아웃

Breakpoint 3: Mobile (375x667)
├─ Sidebar: 숨김 (햄버거 메뉴)
├─ Header: 44px
├─ Content: 전체 너비
└─ 1열 레이아웃
```

**Figma 구현:**
1. 각 해상도별로 별도 Frame 생성
2. 컴포넌트 반복 사용 (Auto-layout)
3. 반응형 제약 설정

#### 4.2 프로토타입 상호작용 (1.5일)

**Figma Prototype 상호작용:**
```
1. 네비게이션
   ├─ Dashboard → Dashboard 페이지
   ├─ Model Details → Model Details 페이지
   └─ Settings → Settings 페이지

2. 탭 전환
   ├─ Overview 탭 클릭
   └─ Metrics 탭으로 전환

3. 모달 열기
   ├─ Delete 버튼 → 확인 모달
   └─ Confirm 버튼 → Close

4. 드롭다운
   ├─ 모델 선택 드롭다운
   └─ 필터 선택
```

#### 4.3 최종 검수 (0.5일)

```
Checklist:
[ ] 모든 페이지 완성
[ ] 색상 일관성 확인
[ ] 타이포그래피 일관성
[ ] 컴포넌트 재사용 확인
[ ] 반응형 레이아웃 테스트
[ ] 프로토타입 상호작용 테스트
[ ] 성능 (Figma 프레임 수) 최적화
[ ] 공유 링크 생성
```

---

## 📦 Figma에서 내보내기 (Phase 3 준비)

### 4단계: 디자인 → 개발 파일 변환

#### 1. 색상 팔레트 추출
```
Figma → CSS Variables
├─ :root {
│   --primary-900: #0D47A1;
│   --primary-700: #1565C0;
│   --primary-500: #2196F3;
│   --success-500: #4CAF50;
│   ...
│ }
└─ tailwind.config.js에 통합
```

#### 2. 컴포넌트 스펙 추출
```
For each component:
├─ 이름: Button
├─ 프롭스: 
│  ├─ variant: "primary" | "secondary" | "danger"
│  ├─ size: "large" | "medium" | "small"
│  ├─ icon?: React.ReactNode
│  └─ disabled?: boolean
├─ 상태: default, hover, active, disabled
├─ 크기: width, height, padding
└─ 스타일: 색상, 보더, 그림자
```

#### 3. React 컴포넌트 구조
```
src/components/
├─ ui/
│  ├─ Button.tsx
│  ├─ Input.tsx
│  ├─ Card.tsx
│  ├─ Modal.tsx
│  └─ Table.tsx
├─ layout/
│  ├─ Header.tsx
│  ├─ Sidebar.tsx
│  └─ MainLayout.tsx
├─ pages/
│  ├─ Dashboard.tsx
│  ├─ ModelDetails.tsx
│  ├─ DataAnalysis.tsx
│  ├─ Settings.tsx
│  └─ Login.tsx
└─ hooks/
   ├─ useTheme.ts
   └─ useNavigation.ts
```

#### 4. Tailwind CSS 설정
```
tailwind.config.js:
├─ colors: Figma 색상 팔레트
├─ spacing: 4px, 8px, 12px, 16px, 20px, ...
├─ fontSize: H1, H2, Body, Label, ...
├─ borderRadius: 4px, 8px, ...
└─ boxShadow: Light, Medium, Large, ...
```

---

## 🎯 성과 지표

### 주차별 완성도
```
주차 1: 디자인 시스템 완성
├─ 색상 팔레트: 12개
├─ 타이포그래피: 8개 스타일
├─ 기본 컴포넌트: 5개
└─ 완성도: 100%

주차 2: Dashboard + Model Details
├─ 페이지: 2개
├─ 컴포넌트 사용: 15개+
└─ 완성도: 100%

주차 3: Data Analysis + Settings + Login
├─ 페이지: 3개
├─ 차트: 4개
└─ 완성도: 100%

주차 4: 반응형 + 상호작용 + 최적화
├─ 브레이크포인트: 3개
├─ 상호작용: 10개+
└─ 완성도: 100%
```

### 최종 산출물
```
✅ Figma 파일 (링크 공유)
✅ 5개 페이지 (모든 상태)
✅ 3개 반응형 레이아웃
✅ 10+ 프로토타입 상호작용
✅ 색상/타이포그래피/컴포넌트 완전 정의
✅ React 컴포넌트 구조 가이드
✅ Tailwind CSS 설정 예제
```

---

## 🚀 다음 단계 (Phase 3)

### Phase 3: React 구현 (4주)
```
├─ Next.js 프로젝트 세팅
├─ Tailwind CSS 통합
├─ 재사용 가능한 컴포넌트 개발
├─ 페이지 구현
├─ API 연동 (FastAPI 백엔드)
├─ 상태 관리 (Redux/Context)
└─ 배포 (Google Cloud Run)
```

---

**시작일:** 2026-06-19  
**예상 완료일:** 2026-07-17  
**담당자:** AI Development Team  
**상태:** ✅ 준비 완료

