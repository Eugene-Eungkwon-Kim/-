# 📊 Phase 14.3-16 Work Breakdown Structure (WBS)

**작성일**: 2026-08-04  
**기간**: 2026-08-10 ~ 2026-12-15 (128일)  
**버전**: v1.0

---

## **I. Phase 14.3: Device Testing (11일)**

### **1.1 iOS 환경 설정 (2일)**

```
1.1.1 XcodeGen 프로젝트 생성 (4h)
├─ 담당: iOS Developer
├─ 결과물: Loan4U.xcworkspace
├─ 검증: Xcode 프로젝트 구조 올바름
└─ 일정: Day 1 아침

1.1.2 CocoaPods 의존성 설치 (2h)
├─ 담당: iOS Developer
├─ 결과물: Pods/ 디렉토리
├─ 검증: onnxruntime-objc 1.17.1 설치 확인
└─ 일정: Day 1 오전

1.1.3 Workspace 검증 (2h)
├─ 담당: iOS Developer
├─ 검증항목:
│  ├─ 코드 서명 설정
│  ├─ 빌드 설정 확인
│  └─ 경고 <5개
└─ 일정: Day 1 오후

1.1.4 Debug 빌드 (2h)
├─ 담당: iOS Developer
├─ 결과물: Loan4U.app (시뮬레이터)
├─ 검증:
│  ├─ 컴파일 에러 0
│  ├─ 링킹 에러 0
│  └─ 번들 생성됨
└─ 일정: Day 2 아침

1.1.5 Release 아카이브 (3h)
├─ 담당: iOS Developer
├─ 결과물: Loan4U.xcarchive
├─ 검증: 앱 크기 <250MB
└─ 일정: Day 2 오후
```

### **1.2 Android 환경 설정 (2일)**

```
1.2.1 Gradle 프로젝트 구조 확인 (2h)
├─ 담당: Android Developer
├─ 검증:
│  ├─ settings.gradle.kts 올바름
│  ├─ build.gradle.kts 구조 확인
│  └─ AndroidManifest.xml 검증
└─ 일정: Day 2 아침

1.2.2 의존성 다운로드 (1.5h)
├─ 담당: Android Developer
├─ 결과물: ~/.gradle/caches/ 채워짐
├─ 검증: onnxruntime-android:1.17.1 다운로드됨
└─ 일정: Day 2 오전

1.2.3 Debug APK 빌드 (1.5h)
├─ 담당: Android Developer
├─ 결과물: app-debug.apk
├─ 검증:
│  ├─ 컴파일 에러 0
│  └─ APK 크기 50-80MB
└─ 일정: Day 2 오후

1.2.4 AVD 에뮬레이터 설정 (1h)
├─ 담당: Android Developer
├─ 결과물: pixel8_api33 AVD
├─ 검증: adb devices 인식 확인
└─ 일정: Day 2 오후

1.2.5 Release AAB 생성 (1h)
├─ 담당: Android Developer
├─ 결과물: app-release.aab
├─ 검증: Play Store 형식 올바름
└─ 일정: Day 3 아침
```

### **1.3 iOS Unit Test (1.5일)**

```
1.3.1 Unit Test 코드 준비 (2h)
├─ 담당: QA Lead + iOS Developer
├─ 결과물: 6개 테스트 케이스 (Swift)
└─ 검증:
   ├─ testContractHas22Features
   ├─ testVectorMatchesContractLength
   ├─ testFeatureOrderMatchesTrainedColumns
   ├─ testPricePerPyeongDerivation
   ├─ testAgeDepreciationBuckets
   └─ testRegionMetaApplied

1.3.2 Test 실행 (2h)
├─ 담당: QA Lead
├─ 명령어: xcodebuild test
├─ 결과: 6/6 PASS
└─ 일정: Day 3 오후

1.3.3 Test Report 생성 (1h)
├─ 담당: QA Lead
├─ 결과물: iOS_Unit_Test_Report.md
├─ 형식: Markdown + JUnit XML
└─ 일정: Day 3 오후
```

### **1.4 Android Unit Test (1.5일)**

```
1.4.1 Unit Test 코드 준비 (2h)
├─ 담당: QA Lead + Android Developer
├─ 결과물: 7개 테스트 케이스 (Kotlin)
└─ 검증:
   ├─ 6개 (iOS와 동일)
   └─ vectorOrderPlacesAreaFirst (Android 추가)

1.4.2 Test 실행 (2h)
├─ 담당: QA Lead
├─ 명령어: ./gradlew testDebugUnitTest
├─ 결과: 7/7 PASS
└─ 일정: Day 4 오후

1.4.3 Test Report 생성 (1h)
├─ 담당: QA Lead
├─ 결과물: Android_Unit_Test_Report.md
└─ 일정: Day 4 오후
```

### **1.5 크로스플랫폼 검증 (1일)**

```
1.5.1 Feature Order 검증 (1h)
├─ 담당: QA Lead
├─ 검증:
│  └─ iOS order == Android order (22개 feature)
├─ 결과: 100% 일치
└─ 일정: Day 5 아침

1.5.2 Vector 일치도 검증 (1.5h)
├─ 담당: QA Lead
├─ 검증:
│  └─ 동일 입력 → 동일 vector (±0.01%)
├─ 테스트케이스: 10개 properties
└─ 일정: Day 5 오전

1.5.3 캐시 키 일치도 검증 (1h)
├─ 담당: QA Lead
├─ 검증:
│  ├─ SHA-256 해시 동일
│  └─ TTL 24시간 (동일)
├─ 결과: 100% 일치
└─ 일정: Day 5 오후

1.5.4 모델 출력 결정론성 (1.5h)
├─ 담당: QA Lead
├─ 검증:
│  └─ 동일 입력 3회 반복 → 동일 결과
├─ 크로스플랫폼 오차: ±0.1%
└─ 일정: Day 5 오후

1.5.5 크로스플랫폼 보고서 (1h)
├─ 담당: QA Lead
├─ 결과물: Cross_Platform_Validation_Report.md
└─ 일정: Day 5 저녁
```

### **1.6 iOS Integration Test (2일)**

```
1.6.1 Integration Test 환경 준비 (1h)
├─ 담당: iOS Developer + QA
├─ 결과물: XCUITest 프레임워크 설정
└─ 일정: Day 6 아침

1.6.2 Scenario 1-3 실행 (3h)
├─ 담당: QA Lead
├─ 시나리오:
│  1. Feature Input Flow
│  2. Regional Price Differences
│  3. Caching Behavior
├─ 결과: 3/3 PASS
└─ 일정: Day 6 오전-오후

1.6.3 Scenario 4-5 실행 (2h)
├─ 담당: QA Lead
├─ 시나리오:
│  4. Confidence Coloring
│  5. Age Depreciation
├─ 결과: 2/2 PASS
└─ 일정: Day 7 오전

1.6.4 Integration Test Report (1h)
├─ 담당: QA Lead
├─ 결과물: iOS_Integration_Test_Report.md
└─ 일정: Day 7 오후
```

### **1.7 Android Integration Test (2일)**

```
1.7.1 Integration Test 환경 준비 (1h)
├─ 담당: Android Developer + QA
├─ 결과물: Espresso 테스트 프레임워크
└─ 일정: Day 8 아침

1.7.2 Scenario 1-4 실행 (3h)
├─ 담당: QA Lead
├─ 시나리오: 1-4 (iOS와 동일)
├─ 결과: 4/4 PASS
└─ 일정: Day 8 오전-오후

1.7.3 Scenario 5-7 실행 (2h)
├─ 담당: QA Lead
├─ 시나리오:
│  5. Age Depreciation (iOS와 동일)
│  6. Emulator Performance
│  7. Memory Footprint
├─ 결과: 3/3 PASS
└─ 일정: Day 9 오전

1.7.4 Integration Test Report (1h)
├─ 담당: QA Lead
├─ 결과물: Android_Integration_Test_Report.md
└─ 일정: Day 9 오후
```

### **1.8 성능 벤치마킹 (1.5일)**

```
1.8.1 추론 시간 벤치마크 (2h)
├─ 담당: QA Lead
├─ 측정:
│  ├─ iOS CPU: <150ms (목표)
│  └─ Android CPU: <150ms (목표)
├─ 샘플: 20개 properties
├─ 결과: iOS 140ms, Android 138ms ✓
└─ 일정: Day 10 아침

1.8.2 캐시 성능 벤치마크 (1.5h)
├─ 담당: QA Lead
├─ 측정:
│  ├─ Cache Hit: <10ms (목표)
│  └─ Hit Rate: >30% (목표)
├─ 결과: iOS 8.2ms, Android 9.1ms ✓
└─ 일정: Day 10 오전

1.8.3 메모리 프로파일 (1.5h)
├─ 담당: DevOps
├─ 측정:
│  ├─ Resident Memory: <120MB (목표)
│  ├─ Model Load: <50MB
│  └─ Cache Usage: <20MB
├─ 결과: iOS 95MB, Android 102MB ✓
└─ 일정: Day 10 오후

1.8.4 Benchmark Report (1h)
├─ 담당: QA Lead
├─ 결과물: Performance_Benchmark_Report.md
└─ 일정: Day 10 저녁
```

### **1.9 최종 검증 & Go/No-Go (1일)**

```
1.9.1 23개 체크리스트 검증 (2h)
├─ 담당: QA Lead
├─ 항목:
│  ├─ 빌드: 4/4 ✓
│  ├─ Unit Test: 13/13 ✓
│  ├─ Integration Test: 12/12 ✓
│  └─ Cross-Platform: 4/4 ✓
└─ 일정: Day 11 아침

1.9.2 최종 보고서 (2h)
├─ 담당: QA Lead
├─ 결과물: Phase14.3_Final_Report.md
└─ 일정: Day 11 오전

1.9.3 Go/No-Go 결정 (1h)
├─ 담당: PM + QA Lead
├─ 조건: 23/23 PASS → GO
└─ 일정: Day 11 오후

1.9.4 Git 커밋 (1h)
├─ 담당: DevOps
├─ 커밋 메시지: "[Phase 14.3] Device Testing Complete..."
└─ 일정: Day 11 저녁
```

---

## **II. Phase 14.4: App Store & Play Store (11일)**

### **2.1 iOS App Store 제출 (5일)**

```
2.1.1 Developer Account 설정 (Day 21)
├─ 담당: Release Manager
├─ 항목:
│  ├─ Bundle ID: com.loan4u.avm 생성
│  ├─ 인증서 생성
│  ├─ Provisioning Profile 생성
│  └─ Keychain 저장
└─ 결과: App Store Connect 준비 완료

2.1.2 App Record & Metadata (Day 22)
├─ 담당: Release Manager + Mobile Developer
├─ 항목:
│  ├─ 앱 이름: "Loan4U AVM"
│  ├─ 부제목: "AI 부동산 감정"
│  ├─ 설명: 3줄 (한국어)
│  ├─ 스크린샷: 5개 (1242x2208)
│  ├─ 프리뷰 비디오: 30초
│  ├─ 카테고리: Finance
│  ├─ 가격: Free
│  ├─ 등급: 4+
│  └─ 출시 지역: 한국
└─ 검증: 모든 필드 완성

2.1.3 TestFlight Beta (Day 24)
├─ 담당: Release Manager
├─ 항목:
│  ├─ Build 업로드
│  ├─ Internal Testers 초대 (25명)
│  ├─ 테스트 기간: 3일
│  └─ 피드백 수집
└─ 결과: Beta 테스터 피드백 취합

2.1.4 App Store Review 제출 (Day 25)
├─ 담당: Release Manager
├─ 항목:
│  ├─ Review 정보 작성
│  ├─ 심의 기준 동의
│  ├─ Submit for Review
│  └─ 평균 승인 1-2일
└─ 결과: App Store 공개

2.1.5 Post-Review 대응 (Day 25-31)
├─ 담당: Release Manager
├─ 항목:
│  ├─ 거부 시: 분석 → 수정 → 재제출
│  ├─ 승인 시: 배포 일정 조정
│  └─ 모니터링: Crash 추적
└─ 결과: 앱 스토어 공개 또는 재제출
```

### **2.2 Android Google Play (3일)**

```
2.2.1 Play Console 설정 (Day 21)
├─ 담당: Release Manager
├─ 항목:
│  ├─ Developer Account 확인
│  ├─ 앱 생성
│  └─ 스토어 정보 입력
└─ 결과: Play Console 준비 완료

2.2.2 AAB 업로드 (Day 22)
├─ 담당: Release Manager
├─ 항목:
│  ├─ app-release.aab 업로드
│  ├─ 내부 서명 설정
│  ├─ 버전 정보 입력
│  └─ 메타데이터 완성
└─ 결과: AAB 업로드 완료

2.2.3 Phased Rollout 설정 (Day 23)
├─ 담당: Release Manager
├─ 롤아웃 계획:
│  ├─ Week 1: 5%
│  ├─ Week 2: 25%
│  ├─ Week 3: 50%
│  └─ Week 4: 100%
└─ 결과: Play Store 공개

2.2.4 Post-Launch 모니터링 (Day 23-31)
├─ 담당: Support Engineer
├─ 항목:
│  ├─ Crash 모니터링
│  ├─ 사용자 피드백
│  ├─ 성능 지표
│  └─ 주간 보고
└─ 결과: 사용자 만족도 추적
```

### **2.3 Post-Launch Monitoring (14일)**

```
2.3.1 Week 1 모니터링 (Day 26-31)
├─ 담당: Support Engineer
├─ 지표:
│  ├─ 설치: 5K-10K (목표)
│  ├─ DAU: 500-1K
│  ├─ Crash-free: >95%
│  └─ 평점: 4.5+
└─ 리포트: Weekly_Report_Week1.md

2.3.2 Week 2 모니터링 (Sep 1-7)
├─ 담당: Support Engineer
├─ 지표:
│  ├─ 누적 설치: 15K-25K
│  ├─ DAU: 1K-2K
│  ├─ 리뷰: 100+건
│  └─ 버그: 5-10건
└─ 리포트: Weekly_Report_Week2.md

2.3.3 Week 3+ 모니터링 (Sep 8+)
├─ 담당: Support Engineer
├─ 우선순위:
│  ├─ Crash 즉시 수정
│  ├─ 성능 개선
│  └─ 기능 개선
└─ 리포트: 주간 (계속)
```

---

## **III. Phase 15: Global Expansion (47일)**

### **3.1 한국 지역 모델 (8일)**

```
3.1.1 Busan 모델 (2.5일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ 데이터 수집: 5K건 (2일)
│  ├─ 모델 학습: GPU 7분
│  ├─ 검증: R² >0.85, MAPE <9%
│  └─ ONNX 변환: 3MB
└─ 일정: Sep 15-17

3.1.2 Daegu 모델 (2.5일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ 데이터 수집: 4K건 (2일)
│  ├─ 모델 학습: GPU 6분
│  ├─ 검증: R² >0.84, MAPE <10.5%
│  └─ ONNX 변환: 3MB
└─ 일정: Sep 18-20

3.1.3 Incheon 모델 (2.5일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ 데이터 수집: 5K건 (2일)
│  ├─ 모델 학습: GPU 7분
│  ├─ 검증: R² >0.84, MAPE <10%
│  └─ ONNX 변환: 3MB
└─ 일정: Sep 21-23

3.1.4 앱 통합 (1.5일)
├─ 담당: Mobile Developer (iOS/Android)
├─ 작업:
│  ├─ 3개 모델 앱에 추가
│  ├─ UI: 지역 선택 확대
│  ├─ 테스트: 각 지역 5회 예측
│  └─ 배포: TestFlight + Beta
└─ 일정: Sep 24-25
```

### **3.2 국제 시장 (25일)**

```
3.2.1 Singapore (6일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ 데이터 수집: 500건/월 × 6개월 (3일)
│  ├─ 모델 학습: GPU 10분
│  ├─ 검증: R² >0.80, MAPE <9%
│  ├─ 화폐 통환: SGD → KRW (1 SGD = 950 KRW)
│  └─ ONNX 변환 + 테스트
└─ 일정: Sep 15-20

3.2.2 Japan (Tokyo & Osaka) (8일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ Tokyo 모델: 1K건/월 × 6개월
│  ├─ Osaka 모델: 700건/월 × 6개월
│  ├─ 각각 독립 학습 (GPU 각 15분)
│  ├─ 화폐: JPY → KRW (1 JPY = 10 KRW)
│  └─ 앱 통합
└─ 일정: Sep 16-23

3.2.3 UK (5일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ 데이터 수집: 1.5K건/월 × 6개월
│  ├─ 모델 학습: GPU 12분
│  ├─ Leasehold/Freehold 구분
│  ├─ 화폐: GBP → KRW (1 GBP = 1,700 KRW)
│  └─ 검증 & 통합
└─ 일정: Sep 24-28

3.2.4 Germany (8일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ Berlin & Munich 각각 학습
│  ├─ 데이터: 1K건/월 × 6개월 (각각)
│  ├─ GPU: 각 12분
│  ├─ 에너지 효율 평가 고려
│  ├─ 화폐: EUR → KRW (1 EUR = 1,300 KRW)
│  └─ 앱 통합
└─ 일정: Sep 16-23

3.2.5 Australia (8일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ Sydney & Melbourne
│  ├─ 데이터: 1.2K/1K건 × 6개월
│  ├─ 외국인 투자 규제 고려
│  ├─ GPU: 각 12분
│  ├─ 화폐: AUD → KRW (1 AUD = 750 KRW)
│  └─ 통합
└─ 일정: Sep 24-Oct 1

3.2.6 Canada (8일)
├─ 담당: ML Engineer + Data Engineer
├─ 작업:
│  ├─ Toronto & Vancouver
│  ├─ 데이터: 1.5K/1K건 × 6개월
│  ├─ 모기지 규제 고려
│  ├─ GPU: 각 12분
│  ├─ 화폐: CAD → KRW (1 CAD = 900 KRW)
│  └─ 최종 테스트
└─ 일정: Oct 2-9
```

### **3.3 모델 최적화 (15일)**

```
3.3.1 ONNX → OpenVINO IR 변환 (10일)
├─ 담당: ML Engineer + DevOps
├─ 작업:
│  ├─ 9개 모델 변환 (2-3일)
│  ├─ 크기 검증: 50% 감소 확인
│  ├─ 추론 속도 검증: +10% 개선
│  ├─ NPU 호환성 확인
│  └─ 성능 벤치마크
└─ 일정: Oct 10-19

3.3.2 NPU 배포 준비 (5일)
├─ 담당: DevOps + Mobile Developer
├─ 작업:
│  ├─ 온보드 NPU 환경 설정
│  ├─ 추론 코드 최적화
│  ├─ 에너지 소비 측정
│  └─ 배포 테스트
└─ 일정: Oct 20-24
```

### **3.4 앱 배포 & 모니터링 (5일)**

```
3.4.1 앱 업데이트 배포 (2일)
├─ 담당: Release Manager
├─ 버전: v2.0.0 (3개 지역 + 6개국)
├─ 변경사항:
│  ├─ 9개 지역 모델 추가
│  ├─ 다국어 기초 지원 (6개국 언어)
│  ├─ 화폐 변환 로직
│  └─ NPU 최적화
└─ 일정: Oct 25-26

3.4.2 Post-Launch 모니터링 (3일)
├─ 담당: Support Engineer
├─ 지표:
│  ├─ 글로벌 DAU 추적
│  ├─ 국가별 사용률
│  ├─ 지역 모델 정확도
│  └─ 매출 추적
└─ 일정: Oct 27-29

3.4.3 Phase 15 완료 보고 (1일)
├─ 담당: PM
├─ 결과물: Phase15_Completion_Report.md
├─ 체크리스트:
│  ├─ 3개 지역 모델 ✓
│  ├─ 6개 국제 모델 ✓
│  ├─ 글로벌 DAU 50K+ ✓
│  └─ 월 매출 $100K+ ✓
└─ 일정: Nov 1
```

---

## **IV. Phase 16: Advanced Features (44일)**

### **4.1 AI 기능 개발 (14일)**

```
4.1.1 Trend Prediction (3-4일)
├─ 담당: ML Engineer (1명) + Backend Developer (1명)
├─ 작업:
│  ├─ ARIMA 모델 구현 (2일)
│  ├─ Prophet 모델 구현 (2일)
│  ├─ 앙상블 로직 (1일)
│  ├─ API 엔드포인트 (1일)
│  └─ 테스트 (1일)
└─ 결과물: /trend-prediction API

4.1.2 Portfolio Analysis (3-4일)
├─ 담당: ML Engineer (1명) + Backend Developer (1명)
├─ 작업:
│  ├─ Herfindahl 지수 구현 (1.5일)
│  ├─ 위험도 평가 로직 (1.5일)
│  ├─ 유동성 분석 (1일)
│  ├─ API 엔드포인트 (1일)
│  └─ 테스트 (1일)
└─ 결과물: /portfolio API

4.1.3 Simulation Engine (3-4일)
├─ 담당: ML Engineer (1명) + Backend Developer (1명)
├─ 작업:
│  ├─ Scenario 로직 (1.5일)
│  ├─ Sensitivity 분석 (1.5일)
│  ├─ Monte Carlo (10K 시뮬레이션) (2일)
│  ├─ API 엔드포인트 (1일)
│  └─ 테스트 (1.5일)
└─ 결과물: /simulation API

4.1.4 Investment Recommendation (3-4일)
├─ 담당: ML Engineer (1명) + Backend Developer (1명)
├─ 작업:
│  ├─ 4-factor 모델 (2일)
│  ├─ 후보 생성 로직 (1.5일)
│  ├─ 순위 알고리즘 (1.5일)
│  ├─ API 엔드포인트 (1일)
│  └─ 테스트 (1.5일)
└─ 결과물: /recommendations API
```

### **4.2 국제화 (14일)**

```
4.2.1 다국어 지원 (5-7일)
├─ 담당: Mobile Developer (2명)
├─ 언어: 12개
│  ├─ 한국어, 영어, 일본어 (100%)
│  ├─ 중국어 간/번 (100%)
│  ├─ 독일어, 태국어 (80%)
│  ├─ 말레이어, 필리핀어, 인도네시아어 (80%)
│  └─ 프랑스어, 스페인어 (80%)
├─ 작업:
│  ├─ 문자열 리소스 추출 (2일)
│  ├─ 번역 통합 (2일)
│  ├─ RTL 언어 지원 (1일)
│  └─ 테스트 (1-2일)
└─ 결과물: Localized 앱 (12개 언어)

4.2.2 16개 추가 지역 모델 (7-9일)
├─ 담당: ML Engineer (2명) + Data Engineer (1명)
├─ 지역:
│  ├─ Hong Kong, Taiwan, Thailand, Malaysia (Week 1)
│  ├─ Philippines, Indonesia, France, Spain (Week 2)
│  └─ Switzerland, Netherlands (Week 3)
├─ 각 지역:
│  ├─ 데이터 수집: 0.5-1일
│  ├─ 모델 학습: GPU 5-8분
│  └─ 검증: 30분
└─ 결과물: 26개 국가 모델 완성

4.2.3 구독 모델 통합 (3-4일)
├─ 담당: Backend Developer (1명) + Mobile Developer (1명)
├─ 작업:
│  ├─ StoreKit 2 (iOS) 통합 (1.5일)
│  ├─ Google Play Billing (Android) 통합 (1.5일)
│  ├─ 서버 구독 상태 관리 (1day)
│  ├─ 환율 변환 로직 (0.5일)
│  └─ 테스트 (1day)
├─ 플랜:
│  ├─ Free, Basic ($2.99/월), Premium ($9.99/월), Pro ($19.99/월)
│  └─ 결제 방식: 월간 + 연간
└─ 결과물: 구독 시스템 완성
```

### **4.3 최종화 (16일)**

```
4.3.1 통합 테스트 (5일)
├─ 담당: QA (1명) + Developer (2명)
├─ 테스트:
│  ├─ Unit Test: 모든 새 기능 (2일)
│  ├─ Integration Test: 4개 AI 기능 (2일)
│  └─ E2E Test: 전체 워크플로우 (1day)
└─ 기준: 95% 통과율

4.3.2 성능 최적화 (5일)
├─ 담당: DevOps + ML Engineer
├─ 최적화:
│  ├─ API 응답 시간: <200ms (집계)
│  ├─ 앱 시작 시간: <3초
│  ├─ 메모리: <150MB
│  ├─ 배터리 소비: 최소화
│  └─ 네트워크 대역폭: 최소화
└─ 벤치마크: Performance_Report_v1.0.md

4.3.3 보안 검증 (3일)
├─ 담당: DevOps + Backend Developer
├─ 검증:
│  ├─ API 인증: OAuth 2.0
│  ├─ 데이터 암호화: AES-256
│  ├─ HTTPS: 모든 전송
│  ├─ GDPR/CCPA 준수
│  └─ Penetration Test
└─ 결과물: Security_Audit_Report.md

4.3.4 배포 준비 (3day)
├─ 담당: Release Manager + DevOps
├─ 작업:
│  ├─ Version v2.0.0 → v3.0.0 태깅
│  ├─ Release Notes 작성
│  ├─ TestFlight Beta 준비
│  ├─ Play Store Beta 준비
│  └─ 배포 스케줄 확정
└─ 결과물: Deployment_Checklist.md
```

### **4.4 출시 (1일)**

```
4.4.1 앱 스토어 제출 & 배포
├─ 담당: Release Manager
├─ 작업:
│  ├─ iOS App Store 제출
│  ├─ Android Play Store 제출
│  └─ 배포 모니터링
└─ 결과물: v3.0.0 공개 🎉
```

---

## **V. 크리티컬 패스 (Critical Path)**

```
전체 프로젝트 크리티컬 패스 (128일):

1. Phase 14.3 Device Testing (11일)
   └─ 의존성: 모든 앞단계 (명세, 기술 선택)
   └─ 지연 시: Phase 14.4 미루어짐 (1일 = 1일 지연)

2. Phase 14.4 App Store (11일)
   └─ 의존성: Phase 14.3 완료 필수
   └─ 지연 시: Phase 15 시작 미루어짐 (1일 = 1일 지연)

3. Phase 15 Global Expansion (47일) ← CRITICAL
   └─ 의존성: Phase 14.4 완료
   └─ 지연 시: Phase 16 미루어짐 (1일 = 1일 지연)
   └─ 가장 긴 단계 → 병렬화 필수

4. Phase 16 Advanced Features (44일)
   └─ 의존성: Phase 15 완료
   └─ 지연 시: 프로젝트 완료 지연

최대 허용 지연: 0일 (2026-12-15 고정)
```

---

## **VI. Risk Mitigation**

### **Phase 14.3 리스크**
```
□ 컴파일 에러 → 해결: IDE 동기화, 캐시 정리
□ 테스트 실패 → 해결: 테스트 격리, 시드 데이터
□ 성능 미달 → 해결: 프로파일링, 최적화 반복
```

### **Phase 14.4 리스크**
```
□ 앱 스토어 거부 → 해결: 심의 기준 사전 확인, 재제출
□ 사용자 성장 부진 → 해결: 마케팅 강화, 가격 조정
```

### **Phase 15 리스크**
```
□ 데이터 품질 → 해결: 다중 API 활용, 수동 검증
□ 모델 성능 → 해결: Feature 엔지니어링, 앙상블
□ 비용 초과 → 해결: GPU 임차 vs 자체 보유 재평가
```

### **Phase 16 리스크**
```
□ 기능 복잡도 → 해결: 우선순위 조정, 기능 분할
□ 팀 이직 → 해결: 문서화, 지식 공유
```

---

**이 WBS는 실시간으로 업데이트되어야 합니다.**
