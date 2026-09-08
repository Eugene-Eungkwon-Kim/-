# 🗺️ Phase 14.4 & Phase 15 상세 개발 로드맵

**작성일**: 2026-08-03  
**프로젝트명**: Loan4U Automatic Valuation Model (AVM)  
**범위**: Phase 14.4 (앱 스토어 제출) + Phase 15 (모델 최적화 & 확장)  
**버전**: 1.0

---

## 📑 목차

1. [Phase 14.4: App Store/Play Store 제출](#phase-144-app-storeplay-store-제출)
2. [Phase 14.5: 배포 후 모니터링](#phase-145-배포-후-모니터링)
3. [Phase 15: 모델 최적화 & 글로벌 확장](#phase-15-모델-최적화--글로벌-확장)
4. [Phase 16: 고급 기능 & 통합](#phase-16-고급-기능--통합)
5. [프로젝트 일정 & 자원 계획](#프로젝트-일정--자원-계획)

---

## Phase 14.4: App Store/Play Store 제출

### 목표
- ✅ iOS 앱 App Store 심사 제출
- ✅ Android 앱 Google Play Store 업로드
- ✅ 앱 검수 통과 및 라이브 배포
- ✅ 초기 사용자 확보 및 피드백 수집

### 일정: 2026-08-10 ~ 2026-08-20 (11일)

---

### 4.1 iOS App Store 제출 (3-5일)

#### **Step 1: App Store Connect 계정 및 앱 레코드 생성** (Day 1, 4시간)

**필수 정보**:
```
1. Apple Developer Account (연 $99)
   - 이미 보유 시 Skip

2. App Record 생성
   ├─ Bundle ID: com.loan4u.app (또는 변경)
   ├─ App Name: Loan4U (또는 국문: 론포유)
   ├─ Subtitle: 부동산 자동감정 서비스
   ├─ Category: Finance (또는 Real Estate)
   ├─ Primary Language: Korean
   └─ Version: 1.0.0

3. Rights & Pricing
   ├─ Free (무료)
   ├─ 가용 국가: 한국 (우선), 추후 확대
   └─ 나이 제한: 4+ (모든 연령)
```

**작업 스텝**:
```
1. App Store Connect 로그인
   https://appstoreconnect.apple.com

2. "My Apps" 클릭 → "+" → "New App"

3. 다음 정보 입력:
   ├─ Platform: iOS
   ├─ Name: Loan4U
   ├─ Bundle ID: com.loan4u.app (from Xcode)
   ├─ SKU: LOAN4U_KR_001 (고유 ID)
   └─ User Access: Full Access

4. 저장 후 앱 페이지 활성화 대기 (5-10분)

5. 검증: App Store Connect 대시보드에서 앱 확인
```

**검증 체크리스트**:
```
☐ App record 생성됨
☐ Bundle ID 일치 (Xcode와)
☐ Version 1.0.0 설정됨
☐ 모든 필수 정보 입력됨
```

---

#### **Step 2: 앱 정보 & 메타데이터 입력** (Day 1, 6시간)

**2.1 기본 정보**:
```
App Information:
├─ 한국어 설명
│  └─ "AI 기반 부동산 자동감정 서비스. 
│       지역, 면적, 건축연도만 입력하면
│       시세 예측과 신뢰도를 제공합니다."
│
├─ 키워드 (5개)
│  └─ 부동산감정, 부동산시세, 주택가격,
│      자동감정, 부동산평가
│
├─ 지원 URL
│  └─ https://loan4u.example.com (준비 필요)
│
├─ 개인정보 보호정책
│  └─ https://loan4u.example.com/privacy (준비 필요)
│
└─ 지원 이메일
   └─ support@loan4u.example.com
```

**2.2 버전 정보**:
```
Version 1.0.0 Release Notes:
└─ "론포유 첫 출시 버전
   - AI 기반 부동산 자동감정
   - 6개 지역 지원 (서울, 부산, 경기, 대구, 인천, 전국)
   - 실시간 가격 예측
   - 24시간 캐싱으로 빠른 응답
   - 오프라인 모드 지원"
```

**2.3 스크린샷 (필수)**:
```
iPhone 6.7" Display (최대 5개 이미지)

Screenshot 1: Feature Input Screen
  └─ "지역 선택, 면적 입력, 예측 버튼"
  └─ 텍스트: "간단한 입력으로 시세 확인"

Screenshot 2: Price Prediction Result
  └─ "예측 가격 표시, 신뢰도 바"
  └─ 텍스트: "AI가 분석한 정확한 평가가"

Screenshot 3: Regional Comparison
  └─ "6개 지역 가격 비교"
  └─ 텍스트: "지역별로 다른 가격 한눈에"

Screenshot 4: Cache Speed
  └─ "빠른 응답 시간"
  └─ 텍스트: "초 단위의 빠른 응답"

Screenshot 5: Offline Support
  └─ "오프라인에서도 작동"
  └─ 텍스트: "인터넷 없이도 가능"
```

**2.4 프리뷰 이미지**:
```
App Preview (6초 비디오, 또는 정적 이미지)
├─ 해상도: 1920x1080 또는 1242x2208
├─ 콘텐츠: 주요 기능 3-4개 시연
└─ 자막: 한국어 (선택사항)
```

**작업 스텝**:
```bash
# 스크린샷 준비
1. iOS Simulator에서 각 화면 캡처
   Simulator → File → Save Screen Shot

2. 각 스크린샷에 텍스트 오버레이 추가 (이미지 편집기)
   - 한글 텍스트 추가
   - 배경 위에 명확하게 표시

3. App Store Connect에 업로드
   ├─ 이미지 크기: 1242x2208px (iPhone 6.7")
   ├─ 형식: PNG 또는 JPG
   └─ 5개 이미지 모두 업로드

4. Preview 비디오 (선택)
   - 또는 정적 이미지 사용 가능
```

**검증 체크리스트**:
```
☐ 설명 입력됨 (한국어)
☐ 키워드 5개 입력됨
☐ 지원 URL 설정됨
☐ 개인정보 보호정책 URL 설정됨
☐ 지원 이메일 설정됨
☐ 스크린샷 5개 업로드됨 (크기 1242x2208)
☐ 미리보기 이미지/비디오 업로드됨
☐ 릴리스 노트 입력됨
```

---

#### **Step 3: 앱 아이콘 & 이미지 자산** (Day 1, 3시간)

**3.1 앱 아이콘**:
```
필수 크기 (App Store):
├─ 1024x1024px (App Store 디스플레이)
│  └─ 모든 크기의 기반
├─ 다른 크기들 (자동 생성 또는 제공)
│  └─ Xcode에서 자동으로 축소
└─ 요구사항:
   ├─ PNG 또는 JPG
   ├─ 투명도 없음 (배경 필요)
   ├─ 모서리 반올림 없음 (OS에서 처리)
   └─ 240dpi 이상 권장

설계 가이드:
├─ 한국식 미니멀리즘
├─ 부동산 관련 심볼 (집, 코인 등)
├─ 신뢰감 있는 색상 (파랑, 녹색)
├─ 명확한 인식성
└─ 작은 크기에서도 구별 가능
```

**3.2 마켓팅 이미지**:
```
App Store Product Page Image (선택):
├─ 크기: 1200x628px 또는 1242x2208px
├─ 콘텐츠: 앱 핵심 가치 전달
├─ 예: "AI가 제시하는 정확한 부동산 감정"
└─ 형식: PNG, JPG, TIFF
```

**작업 스텝**:
```bash
# 아이콘 생성
1. 디자인 도구 사용 (Figma, Adobe XD, Sketch)
   - 1024x1024px 마스터 디자인
   - 여유 공간 (Safe area) 20% 확보

2. Xcode로 변환
   - Assets.xcassets > AppIcon 선택
   - 1024x1024px 이미지 드래그
   - Xcode가 자동 생성

3. App Store Connect 업로드
   - 1024x1024px PNG 업로드
```

**검증 체크리스트**:
```
☐ 앱 아이콘 1024x1024 준비됨
☐ 투명도 없음 (배경 있음)
☐ 마켓팅 이미지 준비됨 (선택사항)
☐ Xcode에 자산 추가됨
☐ Build 시 아이콘 포함 확인됨
```

---

#### **Step 4: 빌드 업로드 및 테스트** (Day 2, 8시간)

**4.1 빌드 준비**:
```bash
# Xcode에서 빌드 및 아카이브
cd ios_app/Loan4U_iOS

# 1단계: 코드 서명 설정
Xcode > Project > Build Settings
├─ Code Sign Identity: "iPhone Distribution"
├─ Team ID: YOUR_TEAM_ID
├─ Provisioning Profile: "Automatic"
└─ Bundle ID: com.loan4u.app

# 2단계: 아카이브 생성
xcodebuild \
  -workspace Loan4U_iOS.xcworkspace \
  -scheme Loan4U_iOS \
  -configuration Release \
  clean archive \
  -archivePath build/Loan4U_iOS.xcarchive

# 3단계: App Store Connect에 업로드
xcodebuild \
  -exportArchive \
  -archivePath build/Loan4U_iOS.xcarchive \
  -exportOptionsPlist exportOptions.plist \
  -exportPath build/Distribution
```

**4.2 TestFlight 베타 테스트 (선택사항)**:
```
1. TestFlight 초대
   App Store Connect > TestFlight > Builds > Add

2. 내부 테스터 추가 (최대 25명)
   - Apple Developer Team 멤버
   - 즉시 테스트 가능

3. 외부 테스터 추가 (최대 1000명)
   - 심사 필요 (24-48시간)
   - 공개 링크 공유 가능

4. 테스트 피드백 수집
   - TestFlight 앱에서 버그 보고
   - 스크린샷 및 로그 첨부 가능
```

**4.3 자동 심사 시스템**:
```
Xcode Cloud (선택, 유료):
├─ 자동 빌드 (코밋 시마다)
├─ 자동 테스트 실행
├─ 결과 리포트 생성
└─ App Store Connect 연동
```

**검증 체크리스트**:
```
☐ 서명 인증서 설정됨
☐ Provisioning Profile 설정됨
☐ 아카이브 생성 성공
☐ Distribution 빌드 생성됨
☐ TestFlight 업로드 성공
☐ 내부 테스터 테스트 완료
```

---

#### **Step 5: App Store 심사 제출** (Day 3, 2시간)

**5.1 최종 검수 체크리스트**:
```
앱 기능:
  ☐ 모든 기능 정상 작동
  ☐ 오프라인 모드 검증
  ☐ 캐싱 동작 확인
  ☐ 오류 처리 검증
  ☐ 메모리 누수 없음
  ☐ 배터리 소비 정상

법률:
  ☐ 개인정보 보호정책 한국어
  ☐ 이용약관 한국어
  ☐ 라이선스 표기 (ONNX Runtime)
  ☐ 저작권 표기

콘텐츠:
  ☐ 부적절한 콘텐츠 없음
  ☐ 광고 없음
  ☐ 외부 링크 안전 (HTTPS)

기술:
  ☐ iOS 14.0 이상 지원
  ☐ iPhone SE 이상 호환
  ☐ 다국어 입력 지원 (필요시)
  ☐ 접근성 (VoiceOver) 기본 지원
```

**5.2 제출 프로세스**:
```
1. App Store Connect 로그인
2. Builds 섹션 → 방금 업로드한 빌드 선택
3. Build 승인 (필요시)
4. 제출 버튼 클릭
5. 심사 대기
   - 평균: 24-48시간
   - 최장: 1주일
```

**5.3 심사 기준** (Apple 검수 가이드):
```
성능:
├─ 앱이 자주 크래시하면 거절
├─ 응답성 부족하면 거절
└─ 배터리 드레인 심하면 거절

보안:
├─ 개인정보 무단 수집 거절
├─ 암호화되지 않은 통신 거절
└─ 백그라운드에서 과도한 활동 거절

콘텐츠:
├─ 음란물, 폭력 거절
├─ 도박 관련 거절
└─ 금융사기 관련 거절

정확성:
├─ 거짓 정보 거절
├─ 오해소지 설명 거절
└─ 허위 기능 표시 거절
```

**거절 시 대응**:
```
1. 거절 사유 확인
   - 이메일로 받음 (영문)
   - "Resolution Center"에서 확인 가능

2. 원인 파악
   - 기술적 문제
   - 콘텐츠 이슈
   - 정책 위반

3. 수정 및 재제출
   - 코드 수정 필요시: 빌드 재생성
   - 설명 수정시: 메타데이터 수정
   - 재제출 즉시 가능

4. 최악의 경우
   - App Store 앱 거절 (드물음)
   - 대체 플랫폼 검토 (웹 앱 등)
```

**검증 체크리스트**:
```
☐ 최종 검수 완료
☐ TestFlight 테스트 통과
☐ 법률 문서 준비됨
☐ 메타데이터 완성
☐ 빌드 선택됨
☐ 제출 버튼 클릭
☐ 심사 상태 모니터링 시작
```

---

#### **Step 6: 심사 완료 & 출시** (Day 4-5, 1-7일)

**6.1 심사 상태 모니터링**:
```bash
# App Store Connect 로그인
# Version History 섹션에서 상태 확인

가능한 상태:
├─ Preparing for Submission: 초기 상태
├─ Waiting for Review: 심사 대기 (보통 1-2일)
├─ In Review: 심사 중
├─ Pending Developer Release: 통과, 대기 중
├─ Approved: 심사 완료, 배포 가능
└─ Rejected: 거절 (재제출 필요)
```

**6.2 출시 방식**:
```
Option 1: 수동 출시 (권장)
├─ 심사 완료 후 "Release this Version" 클릭
├─ 즉시 또는 예약 출시 선택
└─ 24시간 이내 App Store에 표시

Option 2: 자동 출시
├─ "Automatically release this version" 체크
├─ 심사 완료 시 자동 배포
└─ 릴리스 시간 제어 불가
```

**6.3 출시 후 모니터링**:
```
1시간 이내:
  ☐ App Store 검색에 표시 확인
  ☐ 다운로드 링크 작동 확인
  ☐ 스크린샷/설명 올바르게 표시

24시간:
  ☐ 초기 사용자 다운로드 확인
  ☐ 크래시 리포트 모니터링
  ☐ 사용자 리뷰 모니터링

1주일:
  ☐ 누적 다운로드 분석
  ☐ 평점 및 리뷰 분석
  ☐ 버그 리포트 수집 & 분류
```

**검증 체크리스트**:
```
☐ 심사 완료 알림 받음
☐ App Store에 표시됨 (검색 가능)
☐ 다운로드 가능 확인
☐ 초기 사용자 반응 모니터링
☐ Crash 없음 확인
```

---

### 4.2 Android Google Play Store 제출 (2-3일)

#### **Step 1: Google Play Console 계정 설정** (Day 1, 2시간)

**1.1 계정 생성**:
```
1. Google Play Console 접속
   https://play.google.com/console

2. 개발자 계정 생성 (일회성 $25)
   - Google 계정 필요
   - 신용카드 결제

3. 개발자 정보 입력
   ├─ 개발사명: Loan4U
   ├─ 이메일: support@loan4u.example.com
   ├─ 주소: 한국 (위도/경도)
   ├─ 전화번호: +82-10-XXXX-XXXX
   └─ 개발사 웹사이트: https://loan4u.example.com
```

**1.2 앱 생성**:
```
Google Play Console > Create app
├─ App name: Loan4U
├─ Default language: Korean
├─ App category: Finance
├─ App type: Free
└─ Declaration
   ├─ 함유된 콘텐츠: Financial information
   ├─ 대상 연령: All ages (4+)
   └─ 유통 국가: 한국 (우선)
```

**1.3 서명 키 설정**:
```
Play Console > Release > Setup > App signing
├─ Google Play에서 서명 관리 (권장)
│  └─ Google이 자동으로 키 생성 및 관리
│
└─ 또는 기존 서명 키 사용
   └─ app.jks 파일 업로드
```

**검증 체크리스트**:
```
☐ 개발자 계정 생성됨
☐ $25 결제 완료
☐ 앱 레코드 생성됨
☐ 서명 키 설정됨
```

---

#### **Step 2: 앱 정보 & 메타데이터** (Day 1, 4시간)

**2.1 기본 정보**:
```
App details:
├─ App name: Loan4U
├─ Short description (50자)
│  └─ "AI 기반 부동산 자동감정 앱"
│
├─ Full description (4000자)
│  └─ "지역, 면적, 건축연도를 입력하면
│       AI가 현재 시세를 예측해줍니다.
│       6개 지역 지원, 오프라인 지원..."
│
├─ 언어: Korean
├─ 카테고리: Finance
├─ 콘텐츠 등급: Everyone
└─ 문의 URL: https://loan4u.example.com/contact
```

**2.2 스크린샷 (필수)**:
```
최소 2개, 최대 8개 권장
디바이스별:
├─ Phone: 1080x1920px (또는 9:16)
├─ 7-inch tablet: 1200x1920px
└─ Wear OS: 320x320px (선택)

콘텐츠:
├─ Screenshot 1: Feature input screen
├─ Screenshot 2: Price prediction
├─ Screenshot 3: Regional comparison
├─ Screenshot 4: Caching speed
└─ Screenshot 5: Offline support
```

**2.3 Feature Graphic**:
```
앱 스토어 배너 이미지 (필수)
├─ 크기: 1024x500px
├─ 콘텐츠: 앱 핵심 가치 전달
├─ 텍스트: "AI가 제시하는 정확한 부동산 감정"
└─ 형식: PNG, JPG
```

**2.4 아이콘**:
```
Google Play 앱 아이콘
├─ 크기: 512x512px (마스터)
├─ 투명도: 있음 (배경 제거)
├─ 형식: PNG
└─ 배경: 투명 또는 단색
```

**2.5 비디오**:
```
앱 미리보기 비디오 (선택)
├─ 길이: 15-30초
├─ 해상도: 1080p 이상
├─ 콘텐츠: 주요 기능 시연
└─ 업로드: YouTube 링크 또는 파일
```

**검증 체크리스트**:
```
☐ 앱 이름 설정됨
☐ 설명 입력됨 (4000자)
☐ 스크린샷 5-8개 업로드
☐ Feature Graphic 업로드
☐ 아이콘 512x512 업로드
☐ 비디오 (선택)
☐ 모든 항목 한국어
```

---

#### **Step 3: 개인정보 보호 및 콘텐츠 등급** (Day 2, 3시간)

**3.1 개인정보 보호 정책**:
```
Privacy section:
├─ 개인정보 보호정책 URL
│  └─ https://loan4u.example.com/privacy
│
├─ 수집 데이터
│  └─ "버전: 기본값 (위치 정보 없음)"
│
└─ 광고
   └─ "광고 없음"
```

**3.2 콘텐츠 등급**:
```
Content rating questionnaire:
├─ Violence: None
├─ Sexual Content: None
├─ Profanity: None
├─ Alcohol/Tobacco: None
├─ Gambling: None
└─ Financial Information: Yes (부동산 정보)

결과: Everyone (모든 연령)
```

**3.3 타겟 연령 범위**:
```
Target audience:
├─ 연령: 13세 이상
├─ 이유: 금융 정보 (필수)
└─ 제한사항: 없음
```

**검증 체크리스트**:
```
☐ 개인정보 보호정책 URL 입력
☐ 콘텐츠 등급 설정
☐ 타겟 연령 설정
☐ 모든 선언 완료
```

---

#### **Step 4: 빌드 업로드** (Day 2, 4시간)

**4.1 서명된 Release AAB 준비**:
```bash
cd android_app/Loan4U_Android

# 1단계: Release AAB 빌드
./gradlew bundleRelease

# 검증
ls -lh app/build/outputs/bundle/release/
# app-release.aab 파일 확인 (22-28MB)

# 2단계: 서명 확인
jarsigner -verify -verbose -certs \
  app/build/outputs/bundle/release/app-release.aab
# "jar verified" 출력 확인
```

**4.2 Play Console에 업로드**:
```
Production > Releases > Create new release
├─ Release status: In production
├─ Build:
│  └─ app-release.aab 파일 드래그
├─ Release notes (한국어)
│  └─ "론포유 첫 출시
│       - AI 기반 부동산 평가
│       - 6개 지역 지원
│       - 오프라인 지원"
└─ Release date: 즉시 또는 예약
```

**4.3 롤아웃 전략**:
```
Phased rollout (점진적 배포, 권장):
├─ Week 1: 5% 사용자에게 배포
├─ Week 2: 25% 사용자
├─ Week 3: 50% 사용자
└─ Week 4: 100% 사용자

이점:
├─ 문제 발생 시 즉시 중단 가능
├─ 사용자 피드백 수집 가능
└─ 리뷰 및 평점 안정화
```

**검증 체크리스트**:
```
☐ Release AAB 빌드됨
☐ 파일 크기 정상 (22-28MB)
☐ 서명 확인됨
☐ Play Console에 업로드됨
☐ 릴리스 노트 입력됨
☐ 롤아웃 전략 선택됨
```

---

#### **Step 5: Play Store 심사 및 배포** (Day 3, 1-7시간)

**5.1 자동 심사**:
```
Google Play 심사 프로세스:
├─ 자동 심사 (기계 학습)
│  └─ 보통 1-2시간
│
├─ 수동 심사 (필요시)
│  └─ 평균 24-48시간
│
└─ 거절 사유 (드물음)
   ├─ 크래시/ANR (Application Not Responding)
   ├─ 금융사기 관련
   └─ 개인정보 보호 위반

거절 시 대응:
├─ 원인 확인
├─ 코드/메타데이터 수정
└─ 재제출 (즉시 가능)
```

**5.2 배포**:
```
Release > Production
├─ "Review release" 클릭
├─ 최종 확인
├─ "Start rollout" 클릭
└─ 배포 시작

예상 시간:
├─ 5% 롤아웃: 즉시
├─ 25% 단계: 며칠 후
├─ 최종 100%: 2-4주
```

**5.3 배포 후 모니터링**:
```
Play Console 대시보드:
├─ Real-time metrics
│  └─ 설치 수, 제거 수, 충돌률
│
├─ ANR rate
│  └─ 목표: <1%
│
├─ Crash rate
│  └─ 목표: <0.5%
│
├─ Rating
│  └─ 초기 목표: 4.0+ ⭐
│
└─ Reviews
   └─ 사용자 피드백 분석
```

**검증 체크리스트**:
```
☐ 심사 완료
☐ 배포 시작 (rollout)
☐ Play Store에 표시됨
☐ 다운로드 가능
☐ 초기 모니터링 (24시간)
```

---

### 4.3 출시 후 즉시 조치 (Day 1-7)

**4.3.1 모니터링 대시보드 설정**:
```
iOS (App Store Connect):
├─ App Analytics
│  ├─ Sessions: 목표 500+ (첫주)
│  ├─ Unique Users: 목표 300+
│  └─ Downloads: 목표 500+
│
├─ Crashes
│  └─ 목표: 0 또는 <1%
│
└─ Reviews & Ratings
   └─ 초기 평점 추적

Android (Google Play Console):
├─ Acquisition
│  ├─ Installs: 목표 300+ (첫주)
│  ├─ Uninstalls: 추적
│  └─ Rating: 목표 4.0+
│
├─ Vitals
│  ├─ Crash rate: 목표 <0.5%
│  ├─ ANR rate: 목표 <1%
│  └─ Frozen frames: 추적
│
└─ Reviews
   └─ 사용자 피드백 분석
```

**4.3.2 사용자 피드백 수집**:
```
1단계: 초기 리뷰 분석 (24-72시간)
  └─ 부정적 리뷰 우선 읽기
     ├─ 크래시 이슈?
     ├─ 성능 이슈?
     └─ 기능 이해도 부족?

2단계: 패턴 인식
  └─ 자주 나오는 불만
     ├─ 공통 메시지 있는가?
     ├─ 특정 기기에서만?
     └─ 특정 지역에서만?

3단계: 대응
  └─ 긴급 수정 필요 여부 판단
     ├─ 크래시: 긴급 패치
     ├─ 성능: 우선순위 높음
     └─ UX: 다음 버전에 반영
```

**4.3.3 긴급 패치 프로세스**:
```
Critical Issue 발견 시:

iOS:
1. 버그 수정 (30분)
2. 테스트 (1시간)
3. 빌드 생성 (15분)
4. TestFlight 배포 (내부 테스터)
5. 검증 (2시간)
6. App Store 제출 (15분)
7. 심사 (4-24시간)

Android:
1. 버그 수정 (30분)
2. 테스트 (1시간)
3. Release AAB 빌드 (30분)
4. Play Store 업로드 (15분)
5. 롤아웃 전략 (5% 먼저)
6. 모니터링 (2-4시간)
7. 확대 배포 (자동 또는 수동)
```

**검증 체크리스트**:
```
☐ 모니터링 대시보드 설정
☐ 초기 사용자 반응 확인
☐ 크래시 리포트 모니터링
☐ 리뷰 긍정/부정 분석
☐ 긴급 패치 프로세스 준비
☐ 개발팀 대기 상태 유지
```

---

### 4.4 Phase 14.4 완료 기준

**성공 기준**:
```
✅ iOS
  ├─ App Store에 라이브 (검색 가능)
  ├─ 다운로드 가능
  ├─ 초기 평점 3.5+ ⭐
  └─ 크래시율 <1%

✅ Android
  ├─ Google Play에 라이브 (검색 가능)
  ├─ 다운로드 가능
  ├─ 초기 평점 4.0+ ⭐
  └─ 크래시율 <0.5%

✅ 전체
  ├─ 누적 다운로드 500+
  ├─ 일일 활성 사용자 100+
  ├─ 긍정 리뷰 >80%
  └─ 사용자 피드백 정리
```

**일정**: 2026-08-10 ~ 2026-08-20 (11일)

---

## Phase 14.5: 배포 후 모니터링

### 목표
- ✅ 실시간 앱 성능 모니터링
- ✅ 사용자 피드백 분석 및 대응
- ✅ 초기 버그 수정 및 패치
- ✅ 사용자 성장 추적

### 일정: 2026-08-21 ~ 2026-09-03 (2주)

---

### 5.1 모니터링 체계 구축

**5.1.1 Analytics 연동**:
```
Firebase Analytics (권장):
├─ iOS: 
│   └─ Firebase SDK + GoogleService-Info.plist
│
├─ Android:
│   └─ Firebase SDK + google-services.json
│
└─ 추적 이벤트:
   ├─ predict_button_tapped
   ├─ prediction_result_viewed
   ├─ cache_hit
   ├─ model_load_time
   └─ app_crash
```

**5.1.2 Crash Reporting**:
```
Firebase Crashlytics:
├─ 자동 크래시 감지
├─ 스택 트레이스 분석
├─ 영향받은 사용자 수
├─ 심각도 등급
└─ 자동 알림

또는 Sentry (오픈소스):
├─ 더 상세한 성능 분석
├─ 커스텀 모니터링
└─ 자체 호스팅 가능
```

**5.1.3 성능 모니터링**:
```
Firebase Performance Monitoring:
├─ 앱 시작 시간 (Cold/Warm)
│  └─ 목표: <3초
│
├─ 모델 로드 시간
│  └─ 목표: <2초
│
├─ 추론 지연시간
│  └─ 목표: <150ms
│
├─ 메모리 사용
│  └─ 목표: <120MB
│
└─ 배터리 소비
   └─ 추적
```

**설정 코드**:
```swift
// iOS
import FirebaseAnalytics
import FirebaseCrashlytics
import FirebasePerformance

// App 시작 시
FirebaseApp.configure()

// 커스텀 이벤트
Analytics.logEvent("predict_button_tapped", parameters: [
    "region": "Seoul",
    "area_m2": 84.0,
    "year_built": 2015
])

// 성능 측정
let trace = Performance.startTrace(name: "model_inference")
// ... 추론 코드 ...
trace?.stop()
```

---

### 5.2 주간 모니터링 리포트

**주간 보고서 템플릿** (매주 월요일):
```
Week N Monitoring Report (2026-08-21 ~ 08-27)

## 주요 지표
┌─────────────────────┬──────┬──────┬────────┐
│ 지표                │ 이번│ 저번│ 변화  │
├─────────────────────┼──────┼──────┼────────┤
│ Installs/Downloads  │ 542 │ 0   │ +542  │
│ Daily Active Users  │ 127 │ 0   │ +127  │
│ Session per User    │ 2.3 │ -   │ 목표   │
│ Avg Session (min)   │ 1.2 │ -   │ >2분  │
│ Crash Rate          │ 0.2%│ -   │ <1%   │
│ Rating              │ 4.1 │ -   │ >4.0  │
└─────────────────────┴──────┴──────┴────────┘

## 주요 피드백 (긍정)
1. "매우 정확한 감정가" (15건)
2. "빠른 응답 속도" (8건)
3. "쉬운 사용법" (6건)

## 주요 피드백 (부정)
1. "서울 지역만 지원" (3건) → Phase 15에서 확장 예정
2. "앱 아이콘 크기 작음" (2건) → 고려 중
3. "더 많은 지역 지원 바람" (5건) → Phase 15 로드맵

## 기술 이슈
❌ Issue #1: iOS에서 특정 모델 느린 성능
   └─ 상태: 조사 중
   └─ 예상 해결: 1.0.1 패치

✅ Issue #2: Android 캐시 버그 (2명 영향)
   └─ 해결 완료
   └─ 1.0.1 릴리스 예정

## 다음주 계획
- [ ] 1.0.1 패치 배포
  └─ iOS 성능 개선
  └─ Android 캐시 버그 수정
- [ ] Marketing 추진
  └─ SNS 홍보
  └─ 언론 보도
- [ ] 사용자 피드백 분류
  └─ Phase 15 기능 개발 입력
```

---

### 5.3 사용자 피드백 분류 & 우선순위

**피드백 카테고리**:
```
1. 버그 리포트 (긴급)
   ├─ 크래시
   ├─ 기능 미작동
   └─ 데이터 오류

2. 성능 이슈 (높음)
   ├─ 느린 응답
   ├─ 배터리 소비
   └─ 메모리 부족

3. 기능 요청 (중간)
   ├─ 추가 지역
   ├─ 새로운 기능
   └─ UI 개선

4. 사소한 피드백 (낮음)
   ├─ 타이포
   ├─ UI 미세 조정
   └─ 텍스트 변경
```

**우선순위 메트릭**:
```
점수 = (영향도 × 심각도 × 발생빈도) / 해결비용

예:
- 크래시: (3 × 3 × 5) / 1 = 45 (매우 높음)
- 느린 성능: (3 × 2 × 4) / 2 = 12 (높음)
- 지역 추가: (2 × 2 × 2) / 3 = 2.67 (낮음)
```

---

### 5.4 초기 버그 수정 & 패치

**버그 수정 사이클**:
```
Version 1.0.0 → 1.0.1 → 1.0.2 ...

1.0.1 패치 (2주 후):
├─ iOS 성능 개선
├─ Android 캐시 버그 수정
└─ 데이터 정확성 미세 조정

1.0.2 패치 (4주 후):
├─ 추가 지역 지원 (경기)
├─ UI 개선
└─ 사용자 피드백 반영

1.1.0 메이저 버전 (8주 후):
├─ 추가 지역 3개 (부산, 대구, 인천 완전 지원)
├─ 신기능: 가격 변동 예측
└─ 성능: GPU 최적화
```

**패치 배포 프로세스**:
```
1. 버그 수정 (개발팀)
2. 단위 테스트 추가 (테스터)
3. TestFlight/Beta 테스트 (1주)
4. App Store/Play Store 제출 (1일)
5. 심사 (1-3일)
6. 배포 (rollout)
7. 모니터링 (1주)
```

---

### 5.5 사용자 성장 추적

**성장 메트릭**:
```
주간 추적:
├─ DAU (Daily Active Users): +50~100
├─ MAU (Monthly Active Users): +300~500
├─ Retention Rate
│  ├─ Day 1: 목표 >60%
│  ├─ Day 7: 목표 >30%
│  └─ Day 30: 목표 >15%
└─ Churn Rate: 모니터링

지역별 사용자 분포:
├─ Seoul: 40-50%
├─ Gyeonggi: 15-20%
├─ Busan: 10-15%
├─ Daegu: 5-10%
├─ Incheon: 5-10%
└─ Others: 5%
```

**성장 저해 요인 분석**:
```
만약 DAU 증가 정체:
  └─ 원인 분석
     ├─ 마케팅 부족?
     ├─ 앱 품질?
     ├─ 경쟁 출현?
     └─ 마켓팅 피로도?

만약 Retention 낮음 (<30%):
  └─ UX 문제?
  └─ 기능 부족?
  └─ 정확성 문제?

대응:
  ├─ 사용자 인터뷰 (10-20명)
  ├─ A/B 테스트 (다음 버전)
  └─ 기능 개선 (Phase 15)
```

---

## Phase 15: 모델 최적화 & 글로벌 확장

### 목표
- ✅ 추가 지역 모델 개발 (3개: 부산, 대구, 인천 완전 지원)
- ✅ 국제 시장 진출 (6개국: SG, JP, UK, DE, AU, CA)
- ✅ 모델 성능 최적화 (GPU/NPU)
- ✅ 앱 기능 고도화

### 일정: 2026-09-04 ~ 2026-10-31 (8주)

---

### 15.1 추가 지역 모델 개발

#### **15.1.1 Busan Model** (Week 1-2)

**데이터 준비**:
```
부산 부동산 거래 데이터:
├─ 최소 5,000 거래 이상
├─ 특성:
│  ├─ 주거 중심 (서울 비해 상대적으로)
│  ├─ 해수욕장 접근성 프리미엄
│  ├─ 신도시 개발 영향
│  └─ 중국과의 거리 프리미엄
│
└─ 데이터 소스:
   ├─ 국토교통부 API
   ├─ 부동산 중개소 협회
   └─ 공개 부동산 플랫폼
```

**모델 학습**:
```
Feature 엔지니어링:
├─ 부산 특화 특징 추가
│  ├─ 해수욕장 거리
│  ├─ 신항만 접근성
│  └─ 주민 이동성
│
└─ 기존 22개 특징 유지
   └─ 일관된 인터페이스

모델 선택:
├─ LightGBM (GPU 지원)
├─ 성능 목표: R² >0.85, MAPE <9%
└─ 학습 시간: GPU로 <5분

검증:
├─ Hold-out test: 20% 데이터
├─ Cross-validation: 5-fold
└─ 실제 시세와 비교
```

**ONNX 변환 & 배포**:
```
1. LightGBM → ONNX 변환
2. ONNX 검증 (shape, precision)
3. iOS/Android 번들에 추가
4. 버전: 1.1.0
5. 배포: A/B 테스트 (10% → 100%)
```

---

#### **15.1.2 Daegu & Incheon Models** (Week 3-4)

**동일 프로세스 반복**:
```
Daegu:
├─ 특화 특징: 산업 도시 특성, 구역 개발
├─ 목표: R² >0.84, MAPE <10.5%
└─ 학습 시간: <5분 (GPU)

Incheon:
├─ 특화 특징: 공항 접근, 인천국제공항
├─ 특화 특징: 신도시 개발, 교통 접근성
├─ 목표: R² >0.84, MAPE <10%
└─ 학습 시간: <5분 (GPU)

결과:
├─ 3개 모델 완성
├─ 총 6개 지역 모델 (Seoul + Busan + Gyeonggi + Daegu + Incheon + Nationwide)
├─ 앱 번들 크기: +150KB (모델)
└─ 배포: Version 1.1.0
```

---

### 15.2 국제 시장 진출 (6개국)

#### **15.2.1 Singapore (SG)** (Week 5)

**시장 분석**:
```
싱가포르 부동산 특성:
├─ 소유권: 99년 리스홀드 (국가 소유)
├─ 가격 변동: 안정적 (+2-3% 연간)
├─ 주요 유형: HDB (공공주택), 콘도
├─ 특징:
│  ├─ 높은 인구밀도
│  ├─ 다문화 사회
│  ├─ 첨단 기술 인프라
│  └─ 개방적 시장
│
└─ 데이터 가용성:
   ├─ Urban Redevelopment Authority (URA) 공개 데이터
   ├─ PropertyShark 등 부동산 포털
   └─ 거래량: 충분 (연간 100K+ 거래)
```

**모델 개발**:
```
데이터:
├─ 최소 3,000 거래 (싱가포르 소규모 시장)
└─ 특징: 리스홀드 잔여 기간, 지역별 프리미엄

학습:
├─ LightGBM with GPU
├─ 성능 목표: R² >0.82, MAPE <8%
└─ 학습 시간: <5분

배포:
├─ Version 1.2.0-SG
├─ 언어: English (싱가포르 영어)
└─ 통화: SGD (싱가포르 달러)
```

**앱 지역화**:
```
UI 변경사항:
├─ 언어: 영어 (+간체자 선택)
├─ 통화: SGD
├─ 단위: ㎡ (또는 sqft로 선택)
└─ 텍스트: 위에서 설명
```

---

#### **15.2.2 Japan (JP)** (Week 6)

**시장 분석**:
```
일본 부동산 특성:
├─ 가격 추세: 장기 디플레이션 (-1% 연간)
├─ 주요 유형: 아파트, 단독주택, 토지
├─ 특징:
│  ├─ 높은 기술 인프라
│  ├─ 인구 감소 영향
│  ├─ 지진 리스크 프리미엄
│  └─ 지역별 편차 큼
│
└─ 데이터 가용성:
   ├─ 부동산유통기구 공개 데이터
   ├─ Suumo, Homes 등 포털
   └─ 거래량: 매우 충분 (연간 1M+ 거래)
```

**복잡도**:
```
일본 특화 사항:
├─ 46개 도도부현 (prefecture)
│  └─ 각 지역 가격 편차 큼
├─ 도쿄, 오사카 등 메가시티 특별 취급
├─ 지진/재해 리스크 요소
└─ 건물 나이에 따른 급격한 감가

전략:
├─ Phase 15: 도쿄, 오사카 2개 지역만
├─ Phase 16: 추가 도시 확장 (20개)
└─ Phase 17: 전국 커버
```

---

#### **15.2.3 UK** (Week 7)

**시장 분석**:
```
영국 부동산 특성:
├─ 가격 추세: 상승 (+4-5% 연간)
├─ 주요 유형: Terraced, Semi-detached, Detached, Flat
├─ 특징:
│  ├─ London 중심의 가격 편차
│  ├─ 학군 영향력 높음
│  ├─ 거래세 (Stamp Duty) 영향
│  └─ 유럽 경제 상황 민감
│
└─ 데이터 가용성:
   ├─ Land Registry 공개 데이터 (모든 거래)
   ├─ Rightmove, Zoopla 등 포털
   └─ 거래량: 매우 충분 (연간 800K+ 거래)
```

---

#### **15.2.4 Germany, Australia, Canada** (Week 8)

**병렬 개발**:
```
동시 진행:
├─ Germany (DE)
│  └─ 특징: Berlin, Munich 대도시 중심
│
├─ Australia (AU)
│  └─ 특징: Sydney, Melbourne 대도시 중심
│
└─ Canada (CA)
   └─ 특징: Toronto, Vancouver 대도시 중심
```

---

### 15.3 모델 성능 최적화 (GPU/NPU)

#### **15.3.1 GPU 가속 학습** (병렬)

**LightGBM GPU 학습**:
```python
# phase15_gpu_training.py

import lightgbm as lgb
from sklearn.model_selection import train_test_split
import numpy as np

# 데이터 로드
X_train, y_train = load_kr_training_data()
X_test, y_test = load_kr_test_data()

# GPU 설정 (NVIDIA RTX 5050)
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'device': 'gpu',
    'gpu_platform_id': 0,
    'gpu_device_id': 0,
    'num_leaves': 31,
    'learning_rate': 0.05,
    'verbose': 1
}

# 학습 (GPU)
train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

start = time.time()
model = lgb.train(
    params,
    train_data,
    num_boost_round=100,
    valid_sets=[test_data],
    verbose_eval=10
)
gpu_time = time.time() - start

print(f"GPU 학습 시간: {gpu_time:.1f}초 (7-8배 빠름)")
# 예상: 5-7분 (CPU로 35-50분)
```

**성능 비교**:
```
┌──────────────┬─────────┬────────┬────────┐
│ 모델         │ CPU     │ GPU    │ 개선   │
├──────────────┼─────────┼────────┼────────┤
│ LightGBM     │ 45분    │ 6분    │ 7.5배  │
│ XGBoost      │ 35분    │ 4분    │ 8.75배 │
│ CatBoost     │ 40분    │ 5분    │ 8배    │
└──────────────┴─────────┴────────┴────────┘
```

---

#### **15.3.2 ONNX → OpenVINO IR 변환** (병렬)

**추론 최적화**:
```
목적: ONNX → OpenVINO Intermediate Representation (IR)
장점: NPU (Neural Processing Unit) 지원

변환 프로세스:
```python
# phase15_onnx_to_openvino.py

from openvino.tools import mo

# ONNX 모델 변수환
ov_model = mo.convert_model(
    "KR_seoul_lite.onnx",
    input_shape=[1, 22],  # Batch, 특징
    input_type=np.float32,
    output_dir="ir_models/",
    compress_to_fp16=True  # 메모리 50% 절감
)

# 검증
ov_model.reshape([1, 22])
ov_model.outputs[0].node.name = "price_prediction"

# 저장
ov.serialize(ov_model, "KR_seoul_ir.xml")
# 생성 파일: KR_seoul_ir.xml + KR_seoul_ir.bin
```

**크기 비교**:
```
┌─────────────────────┬──────┬──────┐
│ 형식                │ 크기 │ 지원 │
├─────────────────────┼──────┼──────┤
│ ONNX                │ 50KB │ CPU  │
│ OpenVINO IR (FP32)  │ 50KB │ CPU  │
│ OpenVINO IR (FP16)  │ 25KB │ NPU  │
│ TFLite (Quantized)  │ 12KB │ TPU  │
└─────────────────────┴──────┴──────┘
```

---

#### **15.3.3 NPU 배포** (현장 테스트)

**장치 지원**:
```
Intel 통합 NPU (최신 프로세서):
├─ Meteor Lake (Core Ultra)
├─ Arrow Lake
└─ Lunar Lake (추측)

ARM 기반 NPU:
├─ Qualcomm Snapdragon X (Windows ARM)
├─ Apple Neural Engine (A17/M4)
└─ MediaTek Dimensity

배포 전략:
├─ Phase 15: CPU 유지 (안정성)
├─ Phase 16: 특정 기기에 NPU 활성화 (A/B 테스트)
└─ Phase 17: 전체 NPU 확대
```

**성능 목표**:
```
CPU 추론:     100ms
NPU 추론:     10ms (10배 개선)
배터리 절감:  70% (전력 소비 1/10)
```

---

### 15.4 앱 기능 고도화

#### **15.4.1 새로운 기능**:

**1. 가격 변동 예측 (Trend Prediction)**:
```
기존: 현재 시세 예측
신규: 향후 1년 가격 추세

구현:
├─ 시계열 모델 추가 (ARIMA, Prophet)
├─ 거시경제 지표 통합 (금리, GDP)
└─ 사용자 입력 범위 (±10%)

UI:
├─ 그래프: 과거 1년 + 향후 1년 예측
├─ 신뢰도: 예측 범위 시각화
└─ 알림: "가격이 3개월 내 상승 예상"
```

**2. 비교 기능 (Comparison)**:
```
기존: 단일 부동산 감정
신규: 여러 부동산 비교

구현:
├─ 최대 5개 부동산 선택
├─ 나란히 표시
└─ 차이 강조

UI:
├─ Comparison view 추가
├─ 테이블: 가격, 신뢰도, 나이 등
└─ 선택: "이것을 선택할 이유?"
```

**3. 시뮬레이터 (What-if Analysis)**:
```
기존: 고정 입력
신규: 동적 변수 조정

예: "리모델링 후 가격은?"
└─ 건축연도를 5년 앞당기면?
└─ 면적을 20% 늘리면?

구현:
├─ 슬라이더로 변수 조정
├─ 실시간 가격 업데이트
└─ 영향도 분석 (영향도 순)

UI:
├─ "What-if" 탭
├─ 시나리오 저장
└─ 공유 가능
```

**4. 시간 기반 알림 (Notifications)**:
```
기존: 수동 예측만
신규: 주기적 알림

예:
├─ "이 지역 평균 가격이 5% 상승했습니다"
├─ "당신의 예상 가격: +₩20M"
└─ "지금이 좋은 매매 시기입니다"

권한: 사용자 동의
통합: Firebase Cloud Messaging
```

---

### 15.5 Phase 15 완료 기준

**성공 기준**:
```
✅ 추가 지역 모델
  ├─ Busan: R² >0.85, MAPE <9%
  ├─ Daegu: R² >0.84, MAPE <10.5%
  └─ Incheon: R² >0.84, MAPE <10%

✅ 국제 시장
  ├─ Singapore: 배포 완료
  ├─ Japan: 배포 완료 (도쿄, 오사카)
  ├─ UK: 배포 완료
  ├─ Germany, Australia, Canada: 배포 완료
  └─ 누적 다운로드: 10,000+

✅ 성능 최적화
  ├─ GPU 학습: 7-8배 가속
  ├─ OpenVINO 변환: 완료
  └─ NPU 테스트: A/B 테스트 준비

✅ 기능 고도화
  ├─ 가격 변동 예측: 배포
  ├─ 비교 기능: 배포
  ├─ What-if 시뮬레이터: 배포
  └─ 알림: 배포
```

**일정**: 2026-09-04 ~ 2026-10-31 (8주)

---

## 프로젝트 일정 & 자원 계획

### 전체 마일스톤

```
┌─────────────┬──────────────────────┬────────┬────────┐
│ 페이즈      │ 설명                 │ 기간   │ 상태   │
├─────────────┼──────────────────────┼────────┼────────┤
│ Phase 14.2  │ 한국 모델 통합       │ 완료   │ ✅     │
│ Phase 14.3  │ 기기 테스트          │ 8일    │ 예정   │
│ Phase 14.4  │ 앱 스토어 제출       │ 11일   │ 예정   │
│ Phase 14.5  │ 배포 후 모니터링     │ 14일   │ 예정   │
│ Phase 15    │ 모델 최적화 & 확장   │ 56일   │ 예정   │
│ Phase 16    │ 고급 기능 & 통합     │ 42일   │ 예정   │
└─────────────┴──────────────────────┴────────┴────────┘

합계: 2026-08-03 ~ 2026-12-31 (약 5개월)
```

### 자원 계획

**개발팀**:
```
Phase 14.3-14.4:
├─ iOS 개발: 1명 (풀타임)
├─ Android 개발: 1명 (풀타임)
└─ QA: 1명 (풀타임)

Phase 14.5:
├─ DevOps: 1명 (모니터링)
├─ 지원팀: 1명 (사용자 대응)
└─ 기존팀: 유지

Phase 15:
├─ ML Engineer: 1명 (국제 모델)
├─ iOS/Android 개발: 각 1명
├─ Data Engineer: 1명 (데이터 수집)
└─ 총: 5명 (풀타임)

Phase 16+:
├─ 추가 엔지니어: +2명
└─ 마케팅: +1명
```

**비용 예상**:
```
iOS App Store: 연 $99 (개발자 계정)
Android Play Store: 일회 $25 (개발자 계정)
Firebase (분석 + Crashlytics): 무료 (기본)
  → 프리미엄 필요시: 월 $50-100

앱 마케팅: 월 $2-5K
클라우드 인프라: 월 $1-2K

합계: 월 $3-7K
```

---

### 팀 구성 & 역할

```
프로젝트 리더
├─ 기술 리더 (Phase 14-15)
│  ├─ iOS 리드 개발자
│  ├─ Android 리드 개발자
│  └─ ML 엔지니어 (국제 확장)
│
├─ QA 리더
│  └─ 자동화 테스트, 기기 테스트
│
├─ DevOps 엔지니어
│  ├─ CI/CD 파이프라인
│  ├─ 모니터링 대시보드
│  └─ 크래시 분석
│
└─ 마케팅 & 성장팀 (Phase 14.5+)
   ├─ 앱 스토어 최적화
   ├─ 사용자 확보
   └─ 커뮤니티 관리
```

---

### 위험 요소 & 대응

**기술적 위험**:
```
1. 국제 시장 데이터 부족
   └─ 대응: 공개 데이터 + 파트너 협력

2. 모델 성능 저하 (다양한 시장)
   └─ 대응: 지역별 커스터마이징

3. 규제 이슈 (국가별 금융 규제)
   └─ 대응: 법무 팀 협력, Disclaimer 추가

4. 경쟁 출현
   └─ 대응: 기술 격차 유지, 고도화
```

**비즈니스 위험**:
```
1. 초기 사용자 수 저조
   └─ 대응: 마케팅 강화, PR

2. 매출 창출 어려움
   └─ 대응: 프리미엄 기능 (향후)

3. 투자 유치 실패
   └─ 대응: 자체 자금 또는 파트너십
```

---

**문서 작성 완료**: 2026-08-03  
**다음 단계**: Phase 14.3 Device Testing 시작 (2026-08-10)  
**최종 목표**: Phase 15 완료로 글로벌 6개국 서비스 (2026-10-31)
