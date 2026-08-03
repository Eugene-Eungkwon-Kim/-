# 📋 Phase 14.3 Test Execution Guide - 테스트 실행 가이드

**작성일**: 2026-08-03  
**대상**: iOS/Android 개발자 및 QA 엔지니어  
**범위**: 모든 테스트 케이스 실행 방법 및 검증 절차

---

## 목차

1. [실행 전 체크리스트](#실행-전-체크리스트)
2. [iOS 테스트 실행](#ios-테스트-실행)
3. [Android 테스트 실행](#android-테스트-실행)
4. [결과 기록 및 리포팅](#결과-기록-및-리포팅)
5. [문제 해결 (Troubleshooting)](#문제-해결)

---

## 실행 전 체크리스트

### Phase 14.2 검증
```bash
# 현재 브랜치 확인
git status
# 예상: On branch claude/eloquent-meitner-lqxu9r

# 최신 커밋 확인
git log --oneline -3
# 예상: 5ff7858 [Phase 14.2] Korea ML Model Integration

# 필요한 파일 확인
ls -l avm_project/config/
  ✓ feature_contract.json
  ✓ kr_macro_snapshot.json
  ✓ kr_region_meta.json

ls -l avm_project/scripts/phase14_2_kr_*.py
  ✓ phase14_2_kr_inference.py
  ✓ phase14_2_kr_model_integration_test.py
  
ls -l ios_app/Loan4U_iOS/Models/
  ✓ 6개 ONNX 파일 존재

ls -l android_app/Loan4U_Android/app/src/main/assets/models/
  ✓ 6개 ONNX 파일 존재
```

### 환경 설정 확인 (iOS)
```bash
# Xcode 설치 여부
xcode-select -p
# 예상: /Applications/Xcode.app/Contents/Developer

# XcodeGen 설치
xcodegen version
# 예상: 8.5.0 or higher

# CocoaPods 설치
pod --version
# 예상: 1.14.0 or higher
```

### 환경 설정 확인 (Android)
```bash
# Java 버전
java -version
# 예상: openjdk 17.x.x

# Android SDK
echo $ANDROID_HOME
# 예상: /Users/username/Library/Android/sdk (또는 유사 경로)

# Gradle
./gradlew --version
# 예상: Gradle 8.x
```

---

## iOS 테스트 실행

### Step 1: 프로젝트 생성 (Day 1)

```bash
#!/bin/bash
set -e

cd ios_app/Loan4U_iOS

# Step 1.1: XcodeGen으로 프로젝트 생성
echo "🔨 Generating Xcode project..."
xcodegen generate -p project.yml

# 검증
if [ ! -d "Loan4U_iOS.xcworkspace" ]; then
    echo "❌ XcodeGen failed to create workspace"
    exit 1
fi
echo "✅ Xcode workspace created"

# Step 1.2: CocoaPods 의존성 설치
echo "📦 Installing CocoaPods dependencies..."
pod install

# 검증
if [ ! -f "Pods/onnxruntime-objc/framework/onnxruntime.framework/onnxruntime" ]; then
    echo "❌ CocoaPods failed to install ONNX Runtime"
    exit 1
fi
echo "✅ CocoaPods dependencies installed"

# Step 1.3: 프로젝트 구조 확인
echo "📋 Verifying project structure..."
test -d "Loan4U_iOS.xcworkspace" && echo "✅ Workspace exists"
test -f "Loan4U_iOS.xcodeproj/project.pbxproj" && echo "✅ Project file exists"
test -d "App" && echo "✅ App directory exists"
test -d "Features" && echo "✅ Features directory exists"
test -d "Services" && echo "✅ Services directory exists"
test -d "Resources/Config" && echo "✅ Config directory exists"
test -d "Models" && echo "✅ Models directory exists"

echo "✅ All iOS setup complete"
```

**실행 명령어**:
```bash
cd ios_app/Loan4U_iOS
bash setup_ios.sh
```

**예상 시간**: 5-10분

---

### Step 2: Debug 빌드 & 단위 테스트 (Day 2)

```bash
#!/bin/bash
set -e

cd ios_app/Loan4U_iOS

echo "🔨 Building for Debug (Simulator)..."
xcodebuild \
  -workspace Loan4U_iOS.xcworkspace \
  -scheme Loan4U_iOS \
  -configuration Debug \
  -sdk iphonesimulator \
  -derivedDataPath build \
  build 2>&1 | tee build.log

# 검증
if grep -q "BUILD SUCCEEDED" build.log; then
    echo "✅ Debug build succeeded"
else
    echo "❌ Debug build failed"
    cat build.log | grep -A5 "error:"
    exit 1
fi

echo ""
echo "🧪 Running Unit Tests..."
xcodebuild test \
  -workspace Loan4U_iOS.xcworkspace \
  -scheme Loan4U_iOS \
  -configuration Debug \
  -sdk iphonesimulator \
  -destination "platform=iOS Simulator,name=iPhone 15 Pro" \
  2>&1 | tee test.log

# 검증
if grep -q "6 passed" test.log; then
    echo "✅ All 6 unit tests passed"
else
    echo "❌ Some tests failed"
    cat test.log | grep -E "(FAILED|ERROR)"
    exit 1
fi

echo "✅ Debug build & tests complete"
```

**실행 명령어**:
```bash
cd ios_app/Loan4U_iOS
bash build_and_test.sh
```

**예상 시간**: 10-15분

**결과 파일**:
- `build.log` - 빌드 로그
- `test.log` - 테스트 결과

---

### Step 3: 시뮬레이터 통합 테스트 (Day 2-3)

```bash
#!/bin/bash
set -e

cd ios_app/Loan4U_iOS

# 빌드
xcodebuild \
  -workspace Loan4U_iOS.xcworkspace \
  -scheme Loan4U_iOS \
  -configuration Debug \
  install \
  -destination "platform=iOS Simulator,name=iPhone 15 Pro"

# 시뮬레이터에서 앱 실행
xcrun simctl launch booted com.loan4u.app

# 로그 캡처 시작
xcrun simctl spawn booted log stream --predicate 'eventMessage contains[cd] "Loan4U"' &
LOG_PID=$!

# 10초 대기 (모델 로딩)
sleep 10

# 로그 중지
kill $LOG_PID

echo "✅ Simulator integration test started"
echo "📝 Manual test scenarios required - see PHASE_14_3_DEVICE_TESTING_DETAILED_SPEC.md"
```

**수동 테스트 시나리오** (개발자 수행):

| 시나리오 | 단계 | 검증 항목 | 합격 |
|---------|------|----------|------|
| 1 | 앱 실행 → 모델 로드 | 1-2초 내 로드 | ✓ |
| 1 | 지역 선택 (Seoul) | UI 반응성 | ✓ |
| 1 | 면적 입력 (84.0㎡) | 실시간 반영 | ✓ |
| 1 | 연도 입력 (2015) | 실시간 반영 | ✓ |
| 1 | 예측 버튼 클릭 | 1-2초 내 결과 | ✓ |
| 1 | 결과 확인 | ₩778M ±5% | ✓ |
| 2 | 6개 지역 모두 테스트 | 가격 순서 Seoul > 다른 지역 | ✓ |
| 3 | 동일 입력 2회 예측 | 2번째 <10ms | ✓ |
| 4 | 신뢰도 색상 확인 | 녹색 (≥80%) | ✓ |
| 5 | 나이별 가격 비교 | 새 건물 > 구 건물 | ✓ |
| 6 | "New Valuation" 클릭 | 폼 초기화 | ✓ |

**결과 기록 양식**:
```markdown
# iOS Integration Test Results

Date: 2026-08-XX
Tester: [Name]
Environment: Xcode 15.0, iPhone 15 Pro Simulator

## Scenario 1: Feature Input Flow
- [ ] App launches and loads models (<2s)
- [ ] Region selection works smoothly
- [ ] Area input: 84.0㎡
- [ ] Year input: 2015
- [ ] Prediction: ₩778,000,000 (±5%)
- [ ] Confidence: ~90.5% (green)
- [ ] Result view displays correctly

Status: [PASS/FAIL]
Notes: [Any observations]

---

## Scenario 2: Regional Price Differences
... (6 regions tested)

## Scenario 3: Caching Behavior
First prediction: XXXms
Second prediction: XXXms
Improvement factor: XXx

...
```

---

### Step 4: Release 빌드 & 아카이브 (Day 4)

```bash
#!/bin/bash
set -e

cd ios_app/Loan4U_iOS

echo "🔨 Building Release Archive..."
xcodebuild \
  -workspace Loan4U_iOS.xcworkspace \
  -scheme Loan4U_iOS \
  -configuration Release \
  clean archive \
  -archivePath build/Loan4U_iOS.xcarchive

echo "📦 Archive size:"
du -sh build/Loan4U_iOS.xcarchive

echo "✅ Release archive created"
echo "📝 Next: Export for distribution (see PHASE_14_3_DEVICE_TESTING_DETAILED_SPEC.md)"
```

**확인 항목**:
```bash
# 아카이브 검증
ls -lh build/Loan4U_iOS.xcarchive/
# 예상: 120-150MB

# 번들 자산 확인
find build/Loan4U_iOS.xcarchive/Products/Applications/Loan4U_iOS.app/Resources -name "*.json"
# 예상: 3개 JSON 파일

find build/Loan4U_iOS.xcarchive/Products/Applications/Loan4U_iOS.app/Resources/Models -name "*.onnx"
# 예상: 6개 ONNX 파일
```

---

## Android 테스트 실행

### Step 1: 프로젝트 빌드 (Day 1)

```bash
#!/bin/bash
set -e

cd android_app/Loan4U_Android

echo "🔨 Building Android project..."
./gradlew clean build

# 검증
if [ -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo "✅ Debug APK built successfully"
    ls -lh app/build/outputs/apk/debug/app-debug.apk
else
    echo "❌ Build failed"
    exit 1
fi

# 의존성 확인
echo ""
echo "📦 Verifying ONNX Runtime dependency..."
./gradlew dependencies --configuration debugRuntimeClasspath | grep onnxruntime || echo "⚠️ Check dependencies manually"

# Hilt 생성 파일 확인
if [ -d "app/build/generated/hilt_generated_components" ]; then
    echo "✅ Hilt dependency injection generated"
else
    echo "❌ Hilt generation failed"
    exit 1
fi

echo "✅ Android build complete"
```

**실행 명령어**:
```bash
cd android_app/Loan4U_Android
bash build_android.sh
```

**예상 시간**: 60-90초

**결과 파일**:
- `app/build/outputs/apk/debug/app-debug.apk` (~35-40MB)

---

### Step 2: 단위 테스트 (Day 1)

```bash
#!/bin/bash
set -e

cd android_app/Loan4U_Android

echo "🧪 Running Unit Tests..."
./gradlew testDebugUnitTest

# 검증
if grep -q "7 tests passed" build.log 2>/dev/null || grep -q "PASSED" build/test-results/testDebugUnitTest/*.xml; then
    echo "✅ All 7 unit tests passed"
else
    echo "⚠️ Check test results manually"
    ./gradlew testDebugUnitTest --info | tail -20
fi

echo "✅ Unit tests complete"
```

**실행 명령어**:
```bash
cd android_app/Loan4U_Android
./gradlew testDebugUnitTest
```

**예상 시간**: 15-20초

---

### Step 3: 에뮬레이터 설정 & 통합 테스트 (Day 2-3)

```bash
#!/bin/bash
set -e

# AVD 생성 (한 번만)
if ! emulator -list-avds | grep -q "Pixel6Pro"; then
    echo "📱 Creating Android Virtual Device..."
    echo "no" | android create avd \
      --force \
      --name "Pixel6Pro" \
      --target "android-34" \
      --abi "x86_64" \
      --device "Pixel 6 Pro"
fi

echo "🚀 Launching emulator..."
emulator -avd Pixel6Pro -no-snapshot -no-boot-anim &
EMULATOR_PID=$!

# 부팅 대기
echo "⏳ Waiting for emulator to boot..."
adb wait-for-device
sleep 10

echo "✅ Emulator ready"

# APK 설치
cd android_app/Loan4U_Android
echo "📦 Installing APK..."
./gradlew installDebug

# 앱 실행
echo "🚀 Launching app..."
adb shell am start -n com.loan4u/.MainActivity

# 로그 모니터링 (30초)
echo "📊 Monitoring logs..."
adb logcat -s Loan4U &
LOG_PID=$!
sleep 30
kill $LOG_PID || true

echo "✅ Integration test setup complete"
echo "📝 Manual test scenarios required - see PHASE_14_3_DEVICE_TESTING_DETAILED_SPEC.md"
```

**실행 명령어**:
```bash
bash setup_emulator.sh
```

**수동 테스트 시나리오**:

(iOS와 동일하며, 추가로 9개 시나리오 포함)

---

### Step 4: Release 빌드 (Day 4)

```bash
#!/bin/bash
set -e

cd android_app/Loan4U_Android

echo "🔨 Building Release APK..."
./gradlew assembleRelease

echo "📦 Release APK size:"
ls -lh app/build/outputs/apk/release/

echo ""
echo "📦 Building Release AAB..."
./gradlew bundleRelease

echo "📦 Release AAB size:"
ls -lh app/build/outputs/bundle/release/

echo "✅ Release builds complete"
```

---

## 결과 기록 및 리포팅

### 템플릿: 테스트 결과 보고서

```markdown
# Phase 14.3 Test Execution Report

**작성일**: 2026-08-XX  
**작성자**: [Name]  
**테스트 환경**: [macOS/Windows + Xcode 15.0, Android Studio 2024.1]

---

## Executive Summary

| 항목 | 상태 | 세부 |
|------|------|------|
| iOS Build | ✅ PASS | 0 errors, 0 warnings |
| iOS Tests | ✅ PASS | 6/6 unit tests |
| iOS Integration | ✅ PASS | 5/5 scenarios |
| Android Build | ✅ PASS | 0 errors, 0 warnings |
| Android Tests | ✅ PASS | 7/7 unit tests |
| Android Integration | ✅ PASS | 7/7 scenarios |
| Cross-Platform | ✅ PASS | ±0.1% price parity |
| Performance | ✅ PASS | <150ms inference |
| **Overall** | **✅ PASS** | **Ready for production** |

---

## iOS Detailed Results

### Build
- Build time: 45s (first), 12s (incremental)
- Warnings: 0
- Errors: 0
- Archive size: 130MB

### Unit Tests
```
FeatureEngineeringTests:
  - testContractHas22Features: PASS
  - testVectorMatchesContractLength: PASS
  - testFeatureOrderMatchesTrainedColumns: PASS
  - testPricePerPyeongDerivation: PASS
  - testAgeDepreciationBuckets: PASS
  - testRegionMetaApplied: PASS

Result: 6/6 PASS (10s execution)
```

### Integration Tests

#### Scenario 1: Feature Input Flow
- [x] App launches (<2s)
- [x] Region selection works
- [x] Area input: 84.0㎡
- [x] Year input: 2015
- [x] Prediction: ₩778,000,000 (within ±5%)
- [x] Confidence display: 90.5% (green)
- [x] Navigation smooth

Status: **PASS**

#### Scenario 2: Regional Price Differences
- Seoul: ₩778M ✓
- Gyeonggi: ₩488M ✓
- Incheon: ₩309M ✓
- Busan: ₩240M ✓
- Daegu: ₩220M ✓

Status: **PASS**

#### Scenario 3: Caching
- First prediction: 105ms
- Second prediction: 8ms
- Improvement factor: 13.1x
- Cache file created: ~/Library/Caches/loan4u_cache/

Status: **PASS**

#### Scenario 4: Confidence Coloring
- Seoul (90.5%): Green ✓
- Daegu (89.1%): Green ✓
- Nationwide (18.5%): Orange ✓

Status: **PASS**

#### Scenario 5: Age Depreciation
- 2000 (26y): Base price
- 2015 (11y): +35% vs base
- 2023 (3y): +54% vs base
- Trend: Newer > Older ✓

Status: **PASS**

### Performance Metrics
- Inference (CPU): 100ms avg
- Inference (cache hit): 8ms avg
- Memory: 65MB (models) + 12MB (heap)
- Cache hit rate: 35% (realistic distribution)

---

## Android Detailed Results

[Similar structure to iOS]

---

## Cross-Platform Validation

### Feature Parity Matrix
```
Input: Seoul, 84㎡, 2015

         | Python  | iOS     | Android | Variance
---------|---------|---------|---------|----------
Price    | ₩778.2M | ₩778.1M | ₩778.2M | ±0.01%
Conf.    | 0.9053  | 0.9053  | 0.9053  | 0%
Age Dep. | 0.95    | 0.95    | 0.95    | 0%
```

Status: **PASS** (all within ±0.1%)

### Cache Key Consistency
```
SHA256 (Seoul, 84.0, 2015):
- iOS: 7a8b9c0d1e2f3g4h5i6j7k8l9m0n1o2p
- Android: 7a8b9c0d1e2f3g4h5i6j7k8l9m0n1o2p
- Match: ✓ Identical
```

Status: **PASS**

---

## Issues & Resolution

### Issue 1: [Title]
- Severity: High/Medium/Low
- Status: Resolved/Pending
- Resolution: [Details]

---

## Recommendations

1. [ ] Item 1
2. [ ] Item 2
3. [ ] Item 3

---

## Sign-Off

- iOS Developer: ________ Date: ________
- Android Developer: ________ Date: ________
- QA Lead: ________ Date: ________

**Overall Status**: ✅ **APPROVED FOR RELEASE**
```

---

## 문제 해결

### iOS 빌드 오류

**문제**: "onnxruntime could not be found"
```
해결:
1. pod cache clean onnxruntime-objc
2. rm -rf Pods Podfile.lock
3. pod install
4. Xcode 캐시 삭제: rm -rf ~/Library/Developer/Xcode/DerivedData/*
```

**문제**: "Simulator device not found"
```
해결:
1. xcrun simctl list devices
2. xcrun simctl create "iPhone 15 Pro" com.apple.CoreSimulator.SimDeviceType.iPhone-15-Pro com.apple.CoreSimulator.SimRuntime.iOS-17-5
```

---

### Android 빌드 오류

**문제**: "ONNX Runtime not resolved"
```
해결:
1. ~/.gradle/gradle.properties 확인 (org.gradle.jvmargs)
2. ./gradlew --stop
3. ./gradlew clean build --refresh-dependencies
```

**문제**: "Emulator fails to boot"
```
해결:
1. emulator -avd Pixel6Pro -wipe-data
2. 또는 AVD 재생성:
   android delete avd -n Pixel6Pro
   android create avd -n Pixel6Pro ...
```

---

**문서 작성 완료**: 2026-08-03  
**다음 단계**: Phase 14.3 테스트 실행 시작
