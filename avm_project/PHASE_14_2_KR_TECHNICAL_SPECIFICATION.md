# Phase 14.2.KR - 모바일 앱 배포 기술 명세서

**버전**: 1.0  
**작성일**: 2026-07-22  
**상태**: 기술 명세 완성  
**목표 기간**: 2026-08-02 ~ 2026-08-15

---

## 📱 iOS 애플리케이션 명세

### 기술 스택
```
언어: Swift 5.9
프레임워크: SwiftUI
ML 프레임워크: Core ML
배포 대상: iOS 15.0+
개발 환경: Xcode 15.0+
패키지 관리: Swift Package Manager
```

### 프로젝트 구조
```
KoreaAVMApp/
├── App/
│  └── KoreaAVMApp.swift (50줄)
│
├── Models/
│  ├── KoreaPropertyModel.swift (80줄)
│  ├── PredictionResult.swift (60줄)
│  └── MarketTrend.swift (70줄)
│
├── ViewModels/
│  ├── PropertyInputViewModel.swift (150줄)
│  └── PredictionViewModel.swift (120줄)
│
├── Views/
│  ├── ContentView.swift (100줄)
│  ├── PropertyInputView.swift (200줄)
│  ├── PredictionResultView.swift (180줄)
│  ├── MarketAnalysisView.swift (150줄)
│  └── SettingsView.swift (80줄)
│
├── Services/
│  ├── MLModelService.swift (120줄)
│  ├── PropertyService.swift (100줄)
│  └── CacheService.swift (80줄)
│
├── Resources/
│  ├── Models/
│  │  ├── KR_nationwide_v1.mlmodel
│  │  ├── KR_seoul_v1.mlmodel
│  │  └── ... (5개 모델)
│  └── Assets.xcassets/
│     └── Colors, Images, Icons
│
└── Info.plist
```

### 핵심 클래스 명세

#### 1. MLModelService
```swift
class MLModelService {
    static let shared = MLModelService()
    
    private var models: [String: MLModel] = [:]
    private let modelLoader = MLModelConfiguration()
    
    func loadModels() throws -> Void {
        // 6개 모델 로드
        // - KR_nationwide_v1.mlmodel
        // - KR_seoul_v1.mlmodel
        // - KR_busan_v1.mlmodel
        // - KR_gyeonggi_v1.mlmodel
        // - KR_daegu_v1.mlmodel
        // - KR_incheon_v1.mlmodel
    }
    
    func predict(
        region: String,
        input: PropertyInputData
    ) throws -> PredictionResult {
        // 입력 검증
        // 특성 엔지니어링
        // 모델 선택 (지역별)
        // 추론 실행
        // 결과 반환
    }
}

struct PropertyInputData {
    var region: String
    var propertyType: String
    var areaSqm: Double
    var yearBuilt: Int
    var latitude: Double
    var longitude: Double
}
```

#### 2. PropertyInputViewModel
```swift
@MainActor
class PropertyInputViewModel: ObservableObject {
    @Published var region: String = "Seoul"
    @Published var propertyType: String = "아파트"
    @Published var areaSqm: String = ""
    @Published var yearBuilt: String = ""
    @Published var latitude: Double = 37.5
    @Published var longitude: Double = 127.0
    
    @Published var isLoading: Bool = false
    @Published var error: String? = nil
    @Published var predictionResult: PredictionResult? = nil
    
    func predict() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            let input = PropertyInputData(
                region: region,
                propertyType: propertyType,
                areaSqm: Double(areaSqm) ?? 0,
                yearBuilt: Int(yearBuilt) ?? 2020,
                latitude: latitude,
                longitude: longitude
            )
            
            let result = try MLModelService.shared.predict(
                region: region,
                input: input
            )
            
            self.predictionResult = result
            CacheService.shared.save(result)
            
        } catch {
            self.error = error.localizedDescription
        }
    }
}
```

#### 3. PropertyInputView
```swift
struct PropertyInputView: View {
    @ObservedObject var viewModel: PropertyInputViewModel
    
    var body: some View {
        NavigationStack {
            Form {
                // 지역 선택
                Picker("지역", selection: $viewModel.region) {
                    Text("서울").tag("Seoul")
                    Text("부산").tag("Busan")
                    Text("경기").tag("Gyeonggi")
                    Text("대구").tag("Daegu")
                    Text("인천").tag("Incheon")
                }
                
                // 건물 유형
                Picker("건물유형", selection: $viewModel.propertyType) {
                    Text("아파트").tag("아파트")
                    Text("오피스텔").tag("오피스텔")
                    Text("주택").tag("주택")
                    Text("상가").tag("상가")
                }
                
                // 면적 입력
                TextField("면적 (m²)", text: $viewModel.areaSqm)
                    .keyboardType(.decimalPad)
                
                // 건축년도
                TextField("건축년도", text: $viewModel.yearBuilt)
                    .keyboardType(.numberPad)
                
                // 위치 선택
                HStack {
                    VStack(alignment: .leading) {
                        Text("위도: \(String(format: "%.2f", viewModel.latitude))")
                        Slider(value: $viewModel.latitude, in: 33.0...43.0)
                    }
                    
                    VStack(alignment: .leading) {
                        Text("경도: \(String(format: "%.2f", viewModel.longitude))")
                        Slider(value: $viewModel.longitude, in: 125.0...131.0)
                    }
                }
                
                // 평가 버튼
                Button(action: {
                    Task {
                        await viewModel.predict()
                    }
                }) {
                    HStack {
                        if viewModel.isLoading {
                            ProgressView()
                        }
                        Text("평가 분석")
                    }
                    .frame(maxWidth: .infinity)
                }
                .disabled(viewModel.isLoading)
            }
            .navigationTitle("부동산 평가")
        }
    }
}
```

#### 4. PredictionResultView
```swift
struct PredictionResultView: View {
    let result: PredictionResult
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // 예상 가격
                VStack(alignment: .center) {
                    Text("예상 가격")
                        .font(.headline)
                    Text("\(formatPrice(result.estimatedPrice)) \(result.currency)")
                        .font(.system(size: 28, weight: .bold))
                        .foregroundColor(.blue)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue.opacity(0.1))
                .cornerRadius(12)
                
                // 신뢰도
                VStack(alignment: .leading) {
                    HStack {
                        Text("신뢰도")
                        Spacer()
                        Text("\(String(format: "%.1f", result.confidence * 100))%")
                            .font(.headline)
                    }
                    ProgressView(value: result.confidence)
                        .tint(.green)
                }
                
                // 가격 범위
                VStack(alignment: .leading) {
                    Text("가격 범위")
                        .font(.headline)
                    
                    HStack {
                        VStack {
                            Text("최소")
                                .font(.caption)
                            Text(formatPrice(result.range.min))
                                .font(.subheadline)
                        }
                        Spacer()
                        VStack {
                            Text("최대")
                                .font(.caption)
                            Text(formatPrice(result.range.max))
                                .font(.subheadline)
                        }
                    }
                }
                
                // 시장 분석
                VStack(alignment: .leading) {
                    Text("시장 분석")
                        .font(.headline)
                    
                    ForEach(result.factors.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                        HStack {
                            Text(key)
                            Spacer()
                            Text("\(String(format: "%.1f", value))%")
                                .foregroundColor(value > 0 ? .green : .red)
                        }
                        .font(.subheadline)
                    }
                }
                
                Spacer()
            }
            .padding()
        }
        .navigationTitle("평가 결과")
    }
    
    private func formatPrice(_ price: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "KRW"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: price)) ?? ""
    }
}
```

---

## 🤖 Android 애플리케이션 명세

### 기술 스택
```
언어: Kotlin 1.9
프레임워크: Jetpack Compose
ML 프레임워크: TensorFlow Lite
대상 API: 28+
개발 환경: Android Studio 2024.1
패키지 관리: Gradle
```

### 프로젝트 구조
```
KoreaAVMApp/
├── app/src/main/
│  ├── kotlin/com/korea/avm/
│  │  ├── MainActivity.kt (80줄)
│  │  │
│  │  ├── models/
│  │  │  ├── PropertyInputModel.kt (50줄)
│  │  │  ├── PredictionResult.kt (60줄)
│  │  │  └── MarketTrend.kt (70줄)
│  │  │
│  │  ├── viewmodels/
│  │  │  ├── PropertyInputViewModel.kt (150줄)
│  │  │  └── PredictionViewModel.kt (120줄)
│  │  │
│  │  ├── ui/
│  │  │  ├── screens/
│  │  │  │  ├── PropertyInputScreen.kt (200줄)
│  │  │  │  ├── PredictionResultScreen.kt (180줄)
│  │  │  │  └── MarketAnalysisScreen.kt (150줄)
│  │  │  └── components/
│  │  │     ├── RegionSelector.kt (80줄)
│  │  │     ├── PriceDisplay.kt (100줄)
│  │  │     └── ConfidenceMeter.kt (80줄)
│  │  │
│  │  ├── services/
│  │  │  ├── MLModelService.kt (120줄)
│  │  │  ├── PropertyService.kt (100줄)
│  │  │  └── CacheService.kt (80줄)
│  │  │
│  │  └── utils/
│  │     ├── PriceFormatter.kt (40줄)
│  │     ├── ValidationUtils.kt (60줄)
│  │     └── Constants.kt (50줄)
│  │
│  ├── assets/
│  │  └── models/
│  │     ├── KR_nationwide_v1.tflite
│  │     ├── KR_seoul_v1.tflite
│  │     └── ... (5개 모델)
│  │
│  └── AndroidManifest.xml
│
├── build.gradle.kts
├── proguard-rules.pro
└── ...
```

### 핵심 클래스 명세

#### 1. MLModelService
```kotlin
class MLModelService(context: Context) {
    private var tfliteInterpreter: Interpreter? = null
    private val models = mutableMapOf<String, Interpreter>()
    
    init {
        loadModels(context)
    }
    
    private fun loadModels(context: Context) {
        // TFLite 모델 로드
        // - KR_nationwide_v1.tflite
        // - KR_seoul_v1.tflite
        // - KR_busan_v1.tflite
        // - KR_gyeonggi_v1.tflite
        // - KR_daegu_v1.tflite
        // - KR_incheon_v1.tflite
    }
    
    suspend fun predict(
        region: String,
        input: PropertyInputModel
    ): PredictionResult = withContext(Dispatchers.Default) {
        val interpreter = models[region] ?: models["nationwide"]!!
        
        // 입력 배열 준비
        val inputArray = prepareInput(input)
        
        // 출력 배열 준비
        val outputArray = FloatArray(1)
        
        // 추론 실행
        interpreter.run(inputArray, outputArray)
        
        // 결과 변환
        return@withContext PredictionResult(
            estimatedPrice = outputArray[0],
            confidence = calculateConfidence(outputArray[0]),
            factors = calculateFactors(input)
        )
    }
    
    private fun prepareInput(input: PropertyInputModel): Array<FloatArray> {
        return arrayOf(floatArrayOf(
            input.areaSqm.toFloat(),
            input.yearBuilt.toFloat(),
            input.latitude.toFloat(),
            input.longitude.toFloat(),
            // ... 18개 더 추가
        ))
    }
}
```

#### 2. PropertyInputViewModel
```kotlin
@HiltViewModel
class PropertyInputViewModel @Inject constructor(
    private val mlModelService: MLModelService,
    private val cacheService: CacheService
) : ViewModel() {
    
    private val _uiState = MutableStateFlow<PropertyInputState>(
        PropertyInputState.Idle
    )
    val uiState: StateFlow<PropertyInputState> = _uiState.asStateFlow()
    
    var region by mutableStateOf("Seoul")
    var propertyType by mutableStateOf("아파트")
    var areaSqm by mutableStateOf("")
    var yearBuilt by mutableStateOf("")
    var latitude by mutableStateOf(37.5)
    var longitude by mutableStateOf(127.0)
    
    fun predict() {
        viewModelScope.launch {
            try {
                _uiState.value = PropertyInputState.Loading
                
                val input = PropertyInputModel(
                    region = region,
                    propertyType = propertyType,
                    areaSqm = areaSqm.toDoubleOrNull() ?: 0.0,
                    yearBuilt = yearBuilt.toIntOrNull() ?: 2020,
                    latitude = latitude,
                    longitude = longitude
                )
                
                val result = mlModelService.predict(region, input)
                
                cacheService.save(result)
                _uiState.value = PropertyInputState.Success(result)
                
            } catch (e: Exception) {
                _uiState.value = PropertyInputState.Error(e.message ?: "Unknown error")
            }
        }
    }
}

sealed class PropertyInputState {
    object Idle : PropertyInputState()
    object Loading : PropertyInputState()
    data class Success(val result: PredictionResult) : PropertyInputState()
    data class Error(val message: String) : PropertyInputState()
}
```

#### 3. PropertyInputScreen
```kotlin
@Composable
fun PropertyInputScreen(
    viewModel: PropertyInputViewModel,
    onNavigateToPrediction: (PredictionResult) -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "한국 부동산 평가",
            style = MaterialTheme.typography.headlineMedium
        )
        
        // 지역 선택
        RegionSelector(
            selected = viewModel.region,
            onRegionChanged = { viewModel.region = it }
        )
        
        // 건물 유형
        PropertyTypeSelector(
            selected = viewModel.propertyType,
            onTypeChanged = { viewModel.propertyType = it }
        )
        
        // 면적 입력
        OutlinedTextField(
            value = viewModel.areaSqm,
            onValueChange = { viewModel.areaSqm = it },
            label = { Text("면적 (m²)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
        )
        
        // 건축년도
        OutlinedTextField(
            value = viewModel.yearBuilt,
            onValueChange = { viewModel.yearBuilt = it },
            label = { Text("건축년도") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )
        
        // 평가 버튼
        Button(
            onClick = { viewModel.predict() },
            modifier = Modifier.fillMaxWidth(),
            enabled = viewModel.areaSqm.isNotEmpty()
        ) {
            if (uiState is PropertyInputState.Loading) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
            }
            Text("평가 분석")
        }
        
        // 상태 처리
        when (uiState) {
            is PropertyInputState.Success -> {
                onNavigateToPrediction((uiState as PropertyInputState.Success).result)
            }
            is PropertyInputState.Error -> {
                Text(
                    (uiState as PropertyInputState.Error).message,
                    color = Color.Red
                )
            }
            else -> {}
        }
    }
}
```

#### 4. PredictionResultScreen
```kotlin
@Composable
fun PredictionResultScreen(result: PredictionResult) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "평가 결과",
            style = MaterialTheme.typography.headlineMedium
        )
        
        // 예상 가격
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("예상 가격", style = MaterialTheme.typography.titleMedium)
                Text(
                    formatPrice(result.estimatedPrice),
                    style = MaterialTheme.typography.headlineLarge,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
        
        // 신뢰도
        Column {
            Text("신뢰도", style = MaterialTheme.typography.titleMedium)
            LinearProgressIndicator(
                progress = result.confidence.toFloat(),
                modifier = Modifier.fillMaxWidth()
            )
            Text(
                "${String.format("%.1f", result.confidence * 100)}%",
                modifier = Modifier.align(Alignment.End)
            )
        }
        
        // 가격 범위
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            PriceRangeCard("최소", result.range.min)
            PriceRangeCard("최대", result.range.max)
        }
        
        // 시장 분석
        Column {
            Text("시장 분석", style = MaterialTheme.typography.titleMedium)
            result.factors.forEach { (factor, value) ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(factor)
                    Text(
                        "${String.format("%.1f", value)}%",
                        color = if (value > 0) Color.Green else Color.Red
                    )
                }
            }
        }
    }
}
```

---

## 📊 공통 데이터 명세

### PropertyInputData / PropertyInputModel
```
region: String
  - "Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon"

propertyType: String
  - "아파트", "오피스텔", "주택", "상가"

areaSqm: Double
  - 범위: 10.0 ~ 1000.0 m²
  - 기본값: 100.0

yearBuilt: Int
  - 범위: 1980 ~ 2024
  - 기본값: 2020

latitude: Double
  - 범위: 33.0 ~ 43.0
  - 기본값: 37.5 (서울)

longitude: Double
  - 범위: 125.0 ~ 131.0
  - 기본값: 127.0 (서울)
```

### PredictionResult
```json
{
    "estimatedPrice": 520000000,
    "currency": "KRW",
    "confidence": 0.942,
    "range": {
        "min": 480000000,
        "max": 560000000
    },
    "factors": {
        "gangnamPremium": 15.0,
        "ageDepreciation": -8.0,
        "locationMultiplier": 5.0,
        "interestRateImpact": -2.0,
        "jeonseAdjustment": 10.0
    },
    "timestamp": "2026-08-06T14:30:00Z"
}
```

---

## 🔄 오프라인 기능

### 로컬 캐시
```
구조:
├─ last_predictions.json (최근 10개)
├─ cached_models.db (모델 캐시)
└─ settings.json (사용자 설정)

캐시 정책:
- 예측 결과: 7일 보관
- 모델 파일: 30일 보관
- 설정: 무제한 보관

검색 시간: <100ms (로컬 저장소)
```

### 오프라인 추론
```
요구사항:
- 인터넷 연결 불필요
- 모든 6개 모델 탑재
- 실시간 추론 (로컬)

성능:
- 모바일에서 50ms 이내
- 배터리: 1% per 100 predictions
- 메모리: 100MB
```

---

## 📋 배포 체크리스트

### iOS
- [ ] Xcode 프로젝트 설정
- [ ] Core ML 모델 변환 및 통합
- [ ] SwiftUI 뷰 구현
- [ ] ViewModel 구현
- [ ] 오프라인 캐시 구현
- [ ] Unit 테스트 (20개)
- [ ] UI 테스트 (10개)
- [ ] 성능 테스트
- [ ] App Store 제출 준비
- [ ] 마케팅 자료

### Android
- [ ] Gradle 프로젝트 설정
- [ ] TFLite 모델 통합
- [ ] Compose UI 구현
- [ ] ViewModel 구현
- [ ] 오프라인 캐시 구현
- [ ] Unit 테스트 (20개)
- [ ] Instrumentation 테스트 (10개)
- [ ] 성능 테스트
- [ ] Google Play 제출 준비
- [ ] 마케팅 자료

---

**상태**: ✅ 기술 명세 완성  
**다음 단계**: Phase 15.KR 서버 배포 기술 명세
