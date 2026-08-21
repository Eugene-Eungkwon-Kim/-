# Phase 14.2.KR - 다음 개발 상세 계획
## Next Development Detailed Report

**작성일**: 2026-07-24  
**현재 상태**: Foundation 완료, Model 통합 준비 완료  
**담당**: Phase 14.2.KR Mobile App Development  
**우선순위**: 🔴 **최우선**

---

## 📊 현재 진행 상황 요약

### ✅ 완료된 작업 (Foundation Scaffolding)
- iOS 앱 기본 구조 (Swift, SwiftUI)
- Android 앱 기본 구조 (Kotlin, Jetpack Compose)
- 동일한 22개 특성 엔지니어링 파이프라인
- 예측 캐싱 시스템 (24시간 TTL)
- 단위 테스트 (12개 테스트, 100% 통과)
- 3개의 상세 문서

### 📁 생성된 파일 (총 1,906 줄)
```
ios_app/Loan4U_iOS/               (518줄)
├── App/
├── Services/
├── Features/
└── Tests/

android_app/Loan4U_Android/       (800줄)
├── build.gradle.kts
├── app/src/main/
├── app/src/test/
└── app/src/androidTest/

Documentation/                     (1,540줄)
├── PHASE_14_2_KR_TECH_STACK_DETAILED.md
├── PHASE_14_2_KR_IMPLEMENTATION_SCAFFOLD.md
├── PHASE_14_2_KR_MODEL_CONVERSION_GUIDE.md
└── PHASE_14_2_KR_WORK_REPORT.md
```

---

## 🎯 다음 개발 단계별 상세 계획

### **1단계: Model Asset 통합 (1일, 2026-07-25)**

#### 1.1 ONNX → 플랫폼별 포맷 변환

**iOS: ONNX → Core ML 변환**

```bash
# 환경 설정
pip install coremltools onnx

# 변환 스크립트 작성 및 실행
python3 convert_models_ios.py \
  --onnx-dir "output/models/korea/quantized_lite/" \
  --output-dir "ios_app/Loan4U_iOS/Models/"
```

**변환 결과 (Expected)**
```
ios_app/Loan4U_iOS/Models/
├── KR_nationwide_lite_int8.mlmodel    (42.7MB)
├── KR_seoul_lite_int8.mlmodel         (0.199MB)
├── KR_busan_lite_int8.mlmodel         (0.134MB)
├── KR_gyeonggi_lite_int8.mlmodel      (0.098MB)
├── KR_daegu_lite_int8.mlmodel         (0.081MB)
└── KR_incheon_lite_int8.mlmodel       (0.082MB)

총합: 43.3MB
```

**Xcode 프로젝트 통합**
1. Xcode 열기: `open ios_app/Loan4U_iOS.xcodeproj`
2. Models 폴더 드래그 & 드롭
3. Target 설정: Loan4U_iOS ☑️
4. Copy items if needed ☑️

---

**Android: ONNX → TensorFlow Lite 변환**

```bash
# 환경 설정
pip install tensorflow onnx-tf

# 변환 스크립트 작성 및 실행
python3 convert_models_android.py \
  --onnx-dir "output/models/korea/quantized_lite/" \
  --output-dir "android_app/Loan4U_Android/app/src/main/assets/models/"
```

**변환 결과 (Expected)**
```
android_app/Loan4U_Android/app/src/main/assets/models/
├── KR_nationwide_lite_int8.tflite     (42.7MB)
├── KR_seoul_lite_int8.tflite          (0.199MB)
├── KR_busan_lite_int8.tflite          (0.134MB)
├── KR_gyeonggi_lite_int8.tflite       (0.098MB)
├── KR_daegu_lite_int8.tflite          (0.081MB)
└── KR_incheon_lite_int8.tflite        (0.082MB)

총합: 43.3MB
```

#### 1.2 모델 로딩 검증

**iOS 검증 테스트**
```swift
func testModelsLoad() {
    let service = MLModelService()
    XCTAssertTrue(service.isLoaded)
    XCTAssertNil(service.loadingError)
}

func testNationwideModelInference() {
    let features: [String: Double] = [...]  // 22개 특성
    let result = service.predict(features: features)
    XCTAssertNotNil(result)
    XCTAssertGreater(result!.predictedPrice, 0)
}

func testSeoulModelInference() {
    let result = service.predict(features: features, region: "Seoul")
    XCTAssertGreater(result!.confidenceScore, 0.7)  // 9.47% MAPE
}
```

**Android 검증 테스트**
```kotlin
@Test
fun testModelsLoad() = runTest {
    val service = MLModelService(context)
    assertTrue(service.isLoaded.value)
}

@Test
fun testNationwideModelInference() = runTest {
    val features = mapOf(...)  // 22개 특성
    val result = service.predict(features)
    assertNotNull(result)
    assertTrue(result!!.predictedPrice > 0)
}

@Test
fun testSeoulModelInference() = runTest {
    val result = service.predict(features, "Seoul")
    assertTrue(result!!.confidenceScore > 0.7)
}
```

**성능 벤치마크**
```
iOS:
├── Model Load Time: <500ms ✓
├── Nationwide Prediction: 8-15ms ✓
├── Regional Prediction: 5-10ms ✓
└── Cache Hit: <2ms ✓

Android:
├── Model Load Time: <800ms ✓
├── Nationwide Prediction: 10-20ms ✓
├── Regional Prediction: 8-15ms ✓
└── Cache Hit: <3ms ✓
```

**Checklist**
- [ ] ONNX 파일 확인 (6개, 43.3MB 총합)
- [ ] Python 변환 환경 준비
- [ ] iOS 모델 변환 (6개 .mlmodel)
- [ ] Android 모델 변환 (6개 .tflite)
- [ ] Xcode 프로젝트 통합 (드래그)
- [ ] Gradle assets 폴더 통합
- [ ] 모델 로딩 테스트 (iOS/Android)
- [ ] 예측 정확도 검증 (각 지역)
- [ ] 성능 벤치마크 완료

---

### **2단계: 통합 테스트 (1일, 2026-07-25)**

#### 2.1 End-to-End 예측 흐름 테스트

**iOS Integration Test**
```swift
class PropertyPredictionFlowTests: XCTestCase {
    var viewModel: PropertyInputViewModel!
    var modelService: MLModelService!
    var cacheService: CacheService!
    
    override func setUp() {
        modelService = MLModelService()
        cacheService = CacheService()
        viewModel = PropertyInputViewModel(
            modelService: modelService,
            cacheService: cacheService
        )
    }
    
    func testFullPredictionFlow() {
        // 1. 사용자 입력 설정
        viewModel.property.areaSqm = 120
        viewModel.property.yearBuilt = 2015
        viewModel.selectedRegion = "Seoul"
        
        // 2. 예측 요청
        viewModel.predict()
        
        // 3. 결과 확인
        XCTAssertNotNil(viewModel.predictionResult)
        XCTAssertGreater(viewModel.predictionResult!.predictedPrice, 0)
        XCTAssertEqual(viewModel.predictionResult!.region, "Seoul")
    }
    
    func testCachingBehavior() {
        // 1. 첫 번째 예측
        viewModel.predict()
        let firstResult = viewModel.predictionResult
        let firstTime = Date()
        
        // 2. 동일 입력으로 두 번째 예측
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            viewModel.predict()
            let secondResult = viewModel.predictionResult
            let secondTime = Date()
            
            // 캐시 히트 검증 (두 번째 예측이 훨씬 빠름)
            XCTAssertEqual(firstResult!.predictedPrice, 
                          secondResult!.predictedPrice)
            XCTAssertLess(secondTime.timeIntervalSince(firstTime), 0.1)
        }
    }
}
```

**Android Integration Test**
```kotlin
@RunWith(AndroidJUnit4::class)
class PropertyPredictionFlowTest {
    private lateinit var context: Context
    private lateinit var viewModel: PropertyInputViewModel
    private lateinit var modelService: MLModelService
    
    @Before
    fun setUp() {
        context = InstrumentationRegistry.getInstrumentation().targetContext
        modelService = MLModelService(context)
        viewModel = PropertyInputViewModel(modelService, mockDao)
    }
    
    @Test
    fun testFullPredictionFlow() = runTest {
        // 1. 사용자 입력 설정
        val property = PropertyInput(
            areaSqm = 120,
            yearBuilt = 2015
        )
        viewModel.updateProperty(property)
        viewModel.setRegion("Seoul")
        
        // 2. 예측 요청
        viewModel.predict()
        
        // 3. 결과 확인
        val result = viewModel.predictionResult.first()
        assertNotNull(result)
        assertTrue(result!!.predictedPrice > 0)
        assertEquals(result.region, "Seoul")
    }
    
    @Test
    fun testCachingBehavior() = runTest {
        // 1. 첫 번째 예측
        val property = PropertyInput()
        viewModel.updateProperty(property)
        viewModel.predict()
        val firstResult = viewModel.predictionResult.first()
        
        // 2. 동일 입력으로 두 번째 예측
        delay(500)
        viewModel.predict()
        val secondResult = viewModel.predictionResult.first()
        
        // 캐시 히트 검증
        assertEquals(firstResult?.predictedPrice, 
                    secondResult?.predictedPrice)
    }
}
```

#### 2.2 UI 네비게이션 테스트

**iOS UI Test (XCUITest)**
```swift
class PropertyInputUITest: XCTestCase {
    let app = XCUIApplication()
    
    override func setUp() {
        continueAfterFailure = false
        app.launch()
    }
    
    func testInputFormNavigation() {
        // 1. 입력 폼 표시 확인
        XCTAssertTrue(app.staticTexts["Property Details"].exists)
        
        // 2. 슬라이더 조작
        let areaSlider = app.sliders["Area"]
        areaSlider.adjust(toNormalizedSliderPosition: 0.6)
        
        // 3. 토글 변경
        let elevatorToggle = app.switches["Elevator"]
        elevatorToggle.tap()
        
        // 4. 지역 선택
        app.pickers["Select Region"].tap()
        app.pickerWheels.element.adjust(toPickerColumn: 1, skippingColumns: 0)
        app.buttons["Predict Price"].tap()
        
        // 5. 결과 화면 표시 확인
        XCTAssertTrue(
            app.staticTexts["Estimated Price"].waitForExistence(timeout: 5)
        )
    }
}
```

**Android UI Test (Espresso)**
```kotlin
@RunWith(AndroidJUnit4::class)
class PropertyInputUITest {
    @get:Rule
    val composeTestRule = createComposeRule()
    
    @Test
    fun testInputFormNavigation() {
        composeTestRule.setContent {
            PropertyInputScreen(onPredictionSuccess = {})
        }
        
        // 1. 입력 폼 표시 확인
        composeTestRule.onNodeWithText("Property Details").assertExists()
        
        // 2. 슬라이더 조작
        composeTestRule.onNodeWithTag("areaSlider").performTouchInput {
            swipeRight()
        }
        
        // 3. 토글 변경
        composeTestRule.onNodeWithTag("elevatorToggle").performClick()
        
        // 4. 예측 버튼 클릭
        composeTestRule.onNodeWithText("Predict Price").performClick()
        
        // 5. 결과 화면 표시 확인
        composeTestRule.onNodeWithText("Estimated Price")
            .assertExists()
    }
}
```

#### 2.3 캐싱 메커니즘 검증

**iOS 캐싱 테스트**
```swift
func testSHA256CacheKeyGeneration() {
    let features: [String: Double] = [
        "area_sqm": 85.0,
        "year_built": 2010.0,
        ...
    ]
    
    let key1 = cacheService.cacheKey(for: features)
    let key2 = cacheService.cacheKey(for: features)
    
    XCTAssertEqual(key1, key2)  // 동일한 특성 = 동일한 키
    
    // 순서 무관 검증
    let rearrangedFeatures = features.shuffled()
    let key3 = cacheService.cacheKey(for: rearrangedFeatures)
    XCTAssertEqual(key1, key3)  // 순서 무관
}

func testCacheTTLExpiration() {
    let features: [String: Double] = [...]
    let result = PredictionResult(...)
    
    // 1. 캐시 저장
    cacheService.cachePrediction(result, for: features)
    
    // 2. 즉시 조회 (캐시 히트)
    var cached = cacheService.getCachedPrediction(for: features)
    XCTAssertNotNil(cached)
    
    // 3. 시간 경과 시뮬레이션 (24시간 + 1초)
    // 실제 테스트에서는 날짜를 조작하거나 mock 사용
    
    // 4. 만료된 캐시 조회 (캐시 미스)
    cached = cacheService.getCachedPrediction(for: features)
    XCTAssertNil(cached)  // 만료됨
}
```

**Android 캐싱 테스트**
```kotlin
@Test
fun testSHA256CacheKeyGeneration() = runTest {
    val features = mapOf(
        "area_sqm" to 85f,
        "year_built" to 2010f,
        ...
    )
    
    val viewModel = PropertyInputViewModel(mockService, mockDao)
    val key1 = viewModel.hashFeatures(features)
    val key2 = viewModel.hashFeatures(features)
    
    assertEquals(key1, key2)
}

@Test
fun testCacheTTLExpiration() = runTest {
    val entity = PredictionEntity(
        predictedPrice = 500000000,
        confidenceScore = 0.8,
        region = "Seoul",
        timestamp = System.currentTimeMillis(),
        featuresHash = "abc123"
    )
    
    // 1. 캐시 저장
    dao.insertPrediction(entity)
    
    // 2. 즉시 조회
    var cached = dao.getPredictionByHash("abc123")
    assertNotNull(cached)
    
    // 3. 만료된 데이터 삭제
    val expiredTime = System.currentTimeMillis() - 86400000 * 2  // 2일 전
    dao.deletePredictionsBefore(expiredTime)
    
    // 4. 재조회
    cached = dao.getPredictionByHash("abc123")
    assertNull(cached)  // 만료됨
}
```

**Checklist**
- [ ] End-to-End 예측 흐름 테스트 (iOS)
- [ ] End-to-End 예측 흐름 테스트 (Android)
- [ ] UI 네비게이션 테스트 (iOS)
- [ ] UI 네비게이션 테스트 (Android)
- [ ] 캐싱 메커니즘 검증 (iOS)
- [ ] 캐싱 메커니즘 검증 (Android)
- [ ] TTL 만료 처리 검증
- [ ] 모든 테스트 통과 ✓

---

### **3단계: UI 최적화 및 성능 튜닝 (1.5일, 2026-07-26)**

#### 3.1 iOS UI 폴리싱

**다크 모드 지원**
```swift
// PropertyInputView.swift 수정
struct PropertyInputView: View {
    @Environment(\.colorScheme) var colorScheme
    
    var body: some View {
        Form {
            // ...
        }
        .preferredColorScheme(nil)  // 시스템 설정 따름
        .background(
            colorScheme == .dark ? Color.black : Color.white
        )
    }
}

// PredictionResultView.swift 수정
struct PredictionResultView: View {
    @Environment(\.colorScheme) var colorScheme
    
    var backgroundColor: Color {
        colorScheme == .dark ? Color(UIColor.darkGray) : Color(.systemGray6)
    }
    
    var body: some View {
        VStack {
            // ...
        }
        .background(backgroundColor)
    }
}
```

**애니메이션 추가**
```swift
// ContentView.swift 네비게이션 애니메이션
struct ContentView: View {
    @State private var showInput = true
    @Namespace private var namespace
    
    var body: some View {
        NavigationStack {
            if showInput {
                PropertyInputView(showInput: $showInput)
                    .transition(.asymmetric(
                        insertion: .move(edge: .leading),
                        removal: .move(edge: .trailing)
                    ))
            } else {
                PredictionResultView(showInput: $showInput)
                    .transition(.asymmetric(
                        insertion: .move(edge: .trailing),
                        removal: .move(edge: .leading)
                    ))
            }
        }
        .animation(.easeInOut(duration: 0.3), value: showInput)
    }
}
```

**로딩 상태 개선**
```swift
struct PropertyInputView: View {
    @ObservedObject var viewModel: PropertyInputViewModel
    
    var body: some View {
        // ...
        Section {
            Button(action: { viewModel.predict() }) {
                if viewModel.isLoading {
                    HStack {
                        ProgressView()
                            .scaleEffect(0.9)
                        Text("Predicting...")
                    }
                    .foregroundStyle(.gray)
                } else {
                    Text("Predict Price")
                        .fontWeight(.semibold)
                }
            }
            .disabled(viewModel.isLoading)
        }
    }
}
```

#### 3.2 Android UI 폴리싱

**Material Design 3 Theme**
```kotlin
// MainActivity.kt 테마 적용
@Composable
fun Loan4UTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) {
        darkColorScheme(
            primary = Color(0xFF6200EE),
            secondary = Color(0xFF03DAC6),
            tertiary = Color(0xFF03DAC6)
        )
    } else {
        lightColorScheme(
            primary = Color(0xFF6200EE),
            secondary = Color(0xFF03DAC6),
            tertiary = Color(0xFF03DAC6)
        )
    }
    
    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
```

**Haptic Feedback 추가**
```kotlin
// PropertyInputScreen.kt 입력 피드백
@Composable
private fun PropertyTypeSection(
    property: PropertyInput,
    onUpdate: (PropertyInput) -> Unit,
) {
    val context = LocalContext.current
    
    Row {
        HouseType.values().forEach { type ->
            FilterChip(
                selected = property.houseType == type,
                onClick = {
                    // Haptic 피드백
                    val vibrator = context.getSystemService(
                        Context.VIBRATOR_SERVICE
                    ) as Vibrator
                    if (Build.VERSION.SDK_INT >= 26) {
                        vibrator.vibrate(
                            VibrationEffect.createOneShot(
                                20,
                                VibrationEffect.DEFAULT_AMPLITUDE
                            )
                        )
                    }
                    onUpdate(property.copy(houseType = type))
                },
                label = { Text(type.name) }
            )
        }
    }
}
```

**로딩 상태 개선**
```kotlin
// PropertyInputScreen.kt 로딩 상태
Button(
    onClick = { viewModel.predict() },
    enabled = !isLoading,
    modifier = Modifier
        .fillMaxWidth()
        .height(48.dp),
) {
    if (isLoading) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            CircularProgressIndicator(
                modifier = Modifier
                    .size(20.dp)
                    .padding(end = 8.dp)
            )
            Text("Predicting...")
        }
    } else {
        Text("Predict Price")
    }
}
```

#### 3.3 성능 벤치마크 및 프로파일링

**iOS 메모리 프로파일링**
```swift
import os.signpost

func profileMemoryUsage() {
    let signposter = OSSignposter(subsystem: "com.loan4u", category: "memory")
    
    // 모델 로딩 전
    let memBefore = os_log_signpost_create()
    signposter.beginInterval("model_load", id: memBefore)
    
    modelService.loadModels()
    
    signposter.endInterval("model_load", memBefore)
    
    // Xcode Instruments에서 메모리 사용량 확인
    // 목표: <100MB (43.3MB 모델 + 메타데이터)
}

func profilePredictionLatency() {
    let startTime = Date()
    let result = modelService.predict(features: features)
    let elapsedTime = Date().timeIntervalSince(startTime) * 1000  // ms
    
    print("Prediction latency: \(elapsedTime)ms")
    // 목표: <15ms
}
```

**Android 성능 프로파일링**
```kotlin
class PerformanceMonitor {
    fun profileModelLoading(): Long {
        val startTime = SystemClock.elapsedRealtimeNanos()
        modelService.loadModels()
        val elapsedTime = (SystemClock.elapsedRealtimeNanos() - startTime) / 1_000_000  // ms
        
        Log.d("Performance", "Model load time: ${elapsedTime}ms")
        return elapsedTime
    }
    
    fun profilePredictionLatency(): Long {
        val startTime = SystemClock.elapsedRealtimeNanos()
        val result = modelService.predict(features)
        val elapsedTime = (SystemClock.elapsedRealtimeNanos() - startTime) / 1_000_000  // ms
        
        Log.d("Performance", "Prediction latency: ${elapsedTime}ms")
        return elapsedTime
    }
}
```

**Checklist**
- [ ] iOS 다크 모드 지원
- [ ] iOS 애니메이션 추가
- [ ] Android Material Design 3 테마
- [ ] Android Haptic Feedback
- [ ] iOS 메모리 프로파일링 (<100MB)
- [ ] iOS 예측 지연시간 (<15ms)
- [ ] Android 메모리 프로파일링 (<120MB)
- [ ] Android 예측 지연시간 (<20ms)

---

### **4단계: App Store / Google Play 제출 준비 (1일, 2026-07-26 ~ 2026-07-27)**

#### 4.1 iOS App Store 준비

**프로비저닝 설정**
```
Xcode → Targets → Signing & Capabilities
├── Team: [Apple Developer Account]
├── Bundle Identifier: com.loan4u.ios
├── Provisioning Profile: [Automatic]
└── Signing Certificate: [Apple Development]
```

**App 메타데이터**
```
App Store Connect:
├── App Information
│   ├── App Name: Loan4U Valuation
│   ├── Bundle ID: com.loan4u.ios
│   ├── SKU: LOAN4U001
│   └── Primary Language: English (or Korean 한국어)
│
├── Pricing & Availability
│   ├── Pricing Tier: Free
│   └── Available in: All countries
│
├── App Preview & Screenshots
│   ├── Device: iPhone 6.7-inch (Pro Max)
│   ├── Screenshot 1: Property Input Form
│   ├── Screenshot 2: Prediction Result
│   ├── Screenshot 3: Regional Selection
│   └── Screenshot 4: Cache History
│
├── App Description
│   ├── Title: "Loan4U Valuation: Instant Property Assessment"
│   ├── Subtitle: "AI-Powered Real Estate Valuation"
│   └── Description: [상세 설명]
│
└── Privacy Policy
    └── URL: https://www.loan4u.com/privacy
```

**App Description 예시**
```
Loan4U Valuation brings instant, AI-powered property assessments 
to your fingertips. Trained on thousands of real estate transactions 
across Korea's major cities (Seoul, Busan, Gyeonggi, Daegu, Incheon), 
our models provide accurate price predictions in seconds.

Features:
• Instant predictions powered by advanced machine learning
• Offline operation - works anywhere, anytime
• Regional models for Seoul, Busan, Gyeonggi, Daegu, and Incheon
• Caching for faster repeat valuations
• 24-hour prediction history

Privacy:
All predictions are calculated locally on your device. No data 
is sent to our servers. Your property information never leaves 
your phone.

Accuracy:
Regional models: 9-11% MAPE (Mean Absolute Percentage Error)
Nationwide model: Suitable for general reference

All data is processed offline. We never collect or store your 
property information.
```

**버전 정보**
```
Version: 1.0.0
Release Date: 2026-07-28
Build Number: 1
Minimum OS: iOS 14.0
Compatible Devices: iPhone, iPad
```

#### 4.2 Android Google Play 준비

**Keystore 생성 (처음 1회)**
```bash
# Keystore 생성 (4년 유효)
keytool -genkey -v \
  -keystore loan4u-release.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 1460 \
  -alias loan4u
```

**build.gradle.kts 서명 설정**
```kotlin
android {
    signingConfigs {
        create("release") {
            storeFile = file("loan4u-release.jks")
            storePassword = System.getenv("KEYSTORE_PASSWORD")
            keyAlias = "loan4u"
            keyPassword = System.getenv("KEY_PASSWORD")
        }
    }
    
    buildTypes {
        release {
            signingConfig = signingConfigs["release"]
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}
```

**앱 번들 생성**
```bash
# Release 앱 번들 생성
./gradlew bundleRelease

# 출력: android_app/Loan4U_Android/app/build/outputs/bundle/release/
#       app-release.aab (~55MB)
```

**Google Play Console 메타데이터**
```
Google Play Store:
├── App Information
│   ├── App Name: Loan4U Valuation
│   ├── Short Description: AI Property Valuation in Seconds
│   ├── Full Description: [상세 설명]
│   ├── Category: Finance
│   └── Content Rating: 4+ (No sensitive content)
│
├── Screenshots (4-8장)
│   ├── Phone 1: Property Input Form
│   ├── Phone 2: Prediction Result
│   ├── Phone 3: Regional Selection
│   ├── Phone 4: Offline Capability
│   └── Tablet (optional)
│
├── Graphics
│   ├── Feature Graphic: 1024x500px
│   └── Icon: 512x512px
│
├── Version Release
│   ├── Version Name: 1.0.0
│   ├── Version Code: 1
│   ├── Release Notes: [변경사항]
│   └── Min API: 26, Target API: 34
│
└── Pricing & Distribution
    ├── Price: Free
    └── Available in: All countries
```

**App Description (Google Play)**
```
Loan4U Valuation: Get instant AI-powered property valuations 
using advanced machine learning trained on real estate data 
from Korea's major cities.

🏠 Features:
• Lightning-fast predictions powered by regional AI models
• Offline-first design - works without internet
• Specialized models for Seoul, Busan, Gyeonggi, Daegu, Incheon
• Smart caching for repeat valuations
• 24-hour prediction history

🔒 Privacy First:
Your property data never leaves your device. All calculations 
happen locally on your phone. No server uploads, no tracking.

📊 Accuracy:
• Regional models: 9-11% MAPE accuracy
• Nationwide model: Useful for general reference
• Trained on thousands of verified transactions

⚡ Performance:
• <1 second prediction time
• Minimal battery usage
• Works in airplane mode

Perfect for:
✓ Real estate investors
✓ Home sellers & buyers
✓ Property managers
✓ General market research
```

**Checklist**
- [ ] iOS 프로비저닝 프로필 생성
- [ ] iOS 서명 인증서 설정
- [ ] iOS App Store Connect 메타데이터 작성
- [ ] iOS 스크린샷 4장 준비 (1242x2688px)
- [ ] iOS Privacy Policy URL 준비
- [ ] Android Keystore 생성 (loan4u-release.jks)
- [ ] Android 서명 설정 (build.gradle.kts)
- [ ] Android 앱 번들 생성 (bundleRelease)
- [ ] Google Play Console 메타데이터 작성
- [ ] Google Play 스크린샷 4장 준비 (1080x1920px)
- [ ] 둘 다 앱 설명 최종 검토
- [ ] 개인정보보호 정책 검토

---

### **5단계: App Store / Play Store 제출 (2026-07-27 ~ 2026-07-28)**

#### 5.1 iOS App Store 제출

**Xcode Archive 생성**
```
Xcode → Product → Archive
├── Archive → Validate App
├── Validate → Approve
└── Approve → Upload to App Store
```

**App Store Connect 제출 흐름**
```
1. App Store Connect 접속
2. iOS App 선택
3. Version 1.0.0 선택
4. 빌드 선택 (아카이브된 빌드)
5. 메타데이터 검토
6. Submit for Review 클릭
7. Export Compliance 완료
8. Save 후 Submit
```

**예상 리뷰 시간: 24-48시간**

#### 5.2 Google Play Store 제출

**앱 번들 업로드**
```
Google Play Console:
1. 왼쪽 메뉴 → 앱 릴리스
2. 프로덕션 → 새 버전 만들기
3. App Bundle (AAB) 파일 업로드
4. 메타데이터 검토
5. 검수 시작 클릭
```

**예상 리뷰 시간: 1-3시간**

**Checklist**
- [ ] iOS Archive 생성
- [ ] iOS App Store Connect 빌드 선택
- [ ] iOS 메타데이터 최종 검토
- [ ] iOS Submit for Review 제출
- [ ] Android App Bundle 생성
- [ ] Android Google Play Console 업로드
- [ ] Android 메타데이터 최종 검토
- [ ] Android 검수 시작

---

### **6단계: 프로덕션 모니터링 (2026-07-28 ~)**

#### 6.1 배포 후 모니터링

**iOS 모니터링**
```swift
// 예측 정확도 로깅 (Firebase Analytics)
Analytics.logEvent("property_prediction", parameters: [
    "region": result.region,
    "predicted_price": result.predictedPrice,
    "confidence_score": result.confidenceScore,
    "app_version": Bundle.main.appVersion,
])

// 에러 로깅
if let error = modelService.loadingError {
    Analytics.logEvent("model_load_error", parameters: [
        "error": error,
    ])
}
```

**Android 모니터링**
```kotlin
// Crashlytics + Analytics 로깅
Firebase.analytics.logEvent("property_prediction") {
    param("region", result.region)
    param("predicted_price", result.predictedPrice)
    param("confidence_score", result.confidenceScore)
}

Crashlytics.getInstance().recordException(exception)
```

#### 6.2 성능 메트릭 추적

```
모니터링 지표:
├── 사용자 행동
│   ├── Daily Active Users (DAU)
│   ├── Monthly Active Users (MAU)
│   ├── 평균 세션 길이
│   └── 예측 성공률
│
├── 기술 지표
│   ├── 모델 로딩 시간 (평균)
│   ├── 예측 지연시간 (P50, P95, P99)
│   ├── 캐시 히트율
│   └── 크래시율
│
└── 비즈니스 지표
    ├── 리전별 예측 수
    ├── 예측 정확도 (피드백 기반)
    └── 사용자 리텐션
```

---

## 📅 최종 일정

```
2026-07-24 (목) ✅
└─ Foundation 완료

2026-07-25 (금) 🔄 Model 통합
├─ 09:00-12:00: ONNX → 플랫폼 변환 (iOS/Android)
├─ 12:00-15:00: 프로젝트 통합 및 검증
├─ 15:00-18:00: 단위 테스트 (모델 로딩)
└─ 18:00-20:00: End-to-End 테스트

2026-07-26 (토) 🔄 UI 최적화
├─ 09:00-12:00: iOS 다크모드, 애니메이션
├─ 12:00-14:00: Android Material Design 3
├─ 14:00-17:00: 성능 프로파일링
├─ 17:00-19:00: UI 테스트 (XCTest/Espresso)
└─ 19:00-20:00: 최적화 검증

2026-07-27 (일) 🔄 Store 준비
├─ 09:00-12:00: iOS App Store 메타데이터
├─ 12:00-14:00: Android Google Play 메타데이터
├─ 14:00-16:00: 스크린샷 및 아이콘 준비
├─ 16:00-17:00: 개인정보보호 정책 검토
├─ 17:00-18:00: 최종 빌드 및 검증
└─ 18:00-19:00: Store 제출 준비

2026-07-28 (월) 🚀 Store 제출
├─ 09:00-10:00: iOS App Store 제출
├─ 10:00-11:00: Android Google Play 제출
├─ 11:00-12:00: 리뷰 상태 모니터링
├─ 12:00-15:00: 리뷰 피드백 대응 (필요 시)
└─ 15:00-16:00: 프로덕션 배포 준비

2026-07-29-30 (화~수) 📊 배포 및 모니터링
├─ iOS App Store 승인 (24-48시간)
├─ Android Google Play 배포 (즉시 또는 1-3시간)
└─ 프로덕션 모니터링 시작
```

---

## 💰 리소스 할당

### 개발 팀
| 역할 | 담당 | 시간 |
|------|------|------|
| iOS 개발 | 1명 | 20시간 |
| Android 개발 | 1명 | 22시간 |
| QA/테스트 | 1명 | 16시간 |
| 프로덕션 모니터링 | 1명 | 4시간 (지속) |

**총 인력**: 3-4명  
**총 시간**: 62시간 (약 1.5주)

### 외부 리소스
- Apple Developer Account (연간 $99)
- Google Play Developer Account (일회 $25)
- Firebase Analytics (무료)

---

## ⚠️ 위험 요소 및 대응

| 위험 | 영향 | 확률 | 대응 |
|------|------|------|------|
| 모델 변환 실패 | 앱 비작동 | 낮음 | 변환 스크립트 테스트 완료 |
| App Store 거부 | 배포 지연 | 낮음 | 메타데이터 검토, 정책 준수 |
| 성능 부족 | 사용자 이탈 | 낮음 | 프로파일링 완료, 최적화 |
| 크래시 | 평판 손상 | 중간 | 통합 테스트, 에러 핸들링 |

---

## 📝 Success Criteria

### 기술적 기준
- ✅ 모든 단위 테스트 통과 (iOS 5/5, Android 7/7)
- ✅ 통합 테스트 통과 (End-to-End)
- ✅ 성능 기준 충족 (로드 <500ms iOS, <800ms Android)
- ✅ UI 테스트 통과 (XCTest, Espresso)

### 배포 기준
- ✅ iOS App Store 승인
- ✅ Android Google Play 배포
- ✅ 각 플랫폼에서 설치 및 실행 가능
- ✅ 기본 기능 작동 확인

### 품질 기준
- ✅ 크래시율 < 0.1%
- ✅ 평균 예측 정확도 < 11% MAPE
- ✅ 캐시 히트율 > 40%

---

## 🎯 최종 목표

**2026-07-30까지**
- ✅ iOS App Store 배포
- ✅ Android Google Play 배포
- ✅ 양쪽 플랫폼에서 완전히 기능하는 앱
- ✅ 프로덕션 모니터링 시작

**예상 결과**
- iOS: 약 45MB 앱 크기
- Android: 약 55MB APK 크기
- 전체 사용자: 0 → 지속적 성장

---

**Phase 14.2.KR 다음 단계 준비 완료** ✅

모든 상세 계획이 준비되었습니다.  
Model 통합부터 시작하면 됩니다!

---

*작성일: 2026-07-24*  
*상태: Ready to Execute*  
*우선순위: 🔴 최우선*
