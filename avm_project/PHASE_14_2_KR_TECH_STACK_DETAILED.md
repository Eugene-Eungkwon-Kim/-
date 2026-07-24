# Phase 14.2.KR - 모바일 앱 기술 스택 상세 설명

**작성일**: 2026-07-24  
**상태**: 개발 승인  
**우선순위**: iOS, Android 병행 개발

---

## 📱 개요

한국 부동산 자동 평가(AVM) 모바일 앱의 기술 스택 및 구현 전략입니다.

- **iOS**: Swift + Core ML
- **Android**: Kotlin + TensorFlow Lite
- **모델**: 43.3MB 최적화 ONNX-INT8 (전국 1개 + 지역 5개)
- **특성**: 완전 오프라인 추론, 로컬 캐싱, 배터리 최적화

---

## 🍎 iOS 기술 스택

### 언어 & 프레임워크

```
Swift 5.9+
├─ Foundation (기본 API)
├─ SwiftUI (UI 레이아웃)
├─ Combine (비동기 처리)
├─ Core ML (모델 추론)
├─ Vision (이미지 처리)
└─ Accelerate (수치 연산)
```

### 아키텍처

**MVVM (Model-View-ViewModel)**
```
App
├─ Models (데이터 구조)
│  ├─ PropertyInput (입력 데이터)
│  ├─ PredictionResult (예측 결과)
│  └─ CacheEntry (캐시 항목)
│
├─ Views (UI 계층)
│  ├─ PropertyInputView (입력 폼)
│  ├─ PredictionResultView (결과 표시)
│  └─ SettingsView (설정)
│
├─ ViewModels (상태 관리)
│  ├─ PropertyInputViewModel (입력 로직)
│  └─ PredictionViewModel (예측 로직)
│
└─ Services (비즈니스 로직)
   ├─ MLModelService (모델 로딩/추론)
   ├─ CacheService (로컬 캐싱)
   ├─ FeatureEngineer (특성 생성)
   └─ ValidationService (입력 검증)
```

### Core ML 통합

**모델 변환 파이프라인**
```
ONNX → Core ML Tools → .mlmodel
        ↓
   Core ML Format
        ↓
   Xcode Build
        ↓
   App Bundle (자동 최적화)
```

**코드 예시**
```swift
import CoreML

class MLModelService {
    let models: [String: MLModel] = [:]
    
    func loadModels() throws {
        // 번들에서 모델 로드 (자동 optimized)
        guard let nationwide = try? KR_nationwide_lite(configuration: .init())
            .model else {
            throw ModelError.loadFailed
        }
        models["nationwide"] = nationwide
    }
    
    func predictProperty(input: PropertyInput) -> Double? {
        guard let model = selectModel(for: input.region) else {
            return nil
        }
        
        // Core ML 입력 생성
        let features = try? createMLFeatures(from: input)
        guard let prediction = try? model.prediction(input: features) else {
            return nil
        }
        
        return prediction.price  // 예측 가격
    }
    
    private func selectModel(for region: String) -> MLModel? {
        // 지역별 모델 선택 (기본: 전국)
        return models[region] ?? models["nationwide"]
    }
}
```

### 성능 특성

| 항목 | 수치 | 비고 |
|------|------|------|
| 모델 로딩 | < 500ms | 앱 시작 시 1회 |
| 예측 지연 | 5-15ms | Core ML의 최적화된 추론 |
| 메모리 사용 | ~80MB | 모델(43.3MB) + 런타임 |
| 배터리 영향 | < 1% per hour | 낮은 연산 요구 |
| 앱 크기 | < 50MB | 모델 포함 |

### SwiftUI 레이아웃

**PropertyInputView**
```swift
struct PropertyInputView: View {
    @StateObject var viewModel: PropertyInputViewModel
    
    var body: some View {
        NavigationStack {
            Form {
                Section("부동산 정보") {
                    // 지역 선택
                    Picker("지역", selection: $viewModel.region) {
                        ForEach(regions, id: \.self) { region in
                            Text(region).tag(region)
                        }
                    }
                    
                    // 면적 입력 (슬라이더)
                    VStack {
                        Text("면적: \(Int(viewModel.area))㎡")
                        Slider(
                            value: $viewModel.area,
                            in: 20...300,
                            step: 1
                        )
                    }
                    
                    // 건축년도
                    DatePicker(
                        "건축년도",
                        selection: $viewModel.buildYear,
                        displayedComponents: .date
                    )
                    
                    // 기타 입력들...
                }
                
                Section {
                    Button(action: { viewModel.predict() }) {
                        HStack {
                            Image(systemName: "house.fill")
                            Text("가격 평가")
                        }
                    }
                    .disabled(!viewModel.isValid)
                }
            }
            .navigationTitle("부동산 평가")
        }
    }
}
```

**PredictionResultView**
```swift
struct PredictionResultView: View {
    @ObservedObject var viewModel: PredictionViewModel
    
    var body: some View {
        VStack(spacing: 20) {
            // 예측 가격
            VStack {
                Text("예상 가격")
                    .font(.caption)
                    .foregroundColor(.gray)
                Text(viewModel.result.estimatedPrice.formatted(.currency(code: "KRW")))
                    .font(.system(size: 32, weight: .bold))
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            // 신뢰도 게이지
            VStack {
                HStack {
                    Text("신뢰도")
                    Spacer()
                    Text(String(format: "%.0f%%", viewModel.result.confidence * 100))
                }
                .font(.caption)
                
                ProgressView(value: viewModel.result.confidence)
                    .tint(confidenceColor(viewModel.result.confidence))
            }
            .padding()
            
            // 가격 범위
            VStack(alignment: .leading, spacing: 8) {
                Text("예상 범위")
                    .font(.caption2)
                    .foregroundColor(.gray)
                
                HStack {
                    VStack(alignment: .leading) {
                        Text("최소")
                            .font(.caption)
                        Text(viewModel.result.priceMin.formatted(.currency(code: "KRW")))
                            .font(.subheadline)
                    }
                    
                    Spacer()
                    
                    VStack(alignment: .trailing) {
                        Text("최대")
                            .font(.caption)
                        Text(viewModel.result.priceMax.formatted(.currency(code: "KRW")))
                            .font(.subheadline)
                    }
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(12)
            
            Spacer()
            
            // 공유 버튼
            Button(action: { viewModel.shareResult() }) {
                Label("결과 공유", systemImage: "square.and.arrow.up")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }
    
    private func confidenceColor(_ confidence: Double) -> Color {
        confidence > 0.8 ? .green : confidence > 0.6 ? .orange : .red
    }
}
```

### 데이터 영속성 (LocalStorage)

```swift
import Foundation

class CacheService {
    private let fileManager = FileManager.default
    private let cacheDirectory: URL
    
    init() {
        let paths = fileManager.urls(
            for: .cachesDirectory,
            in: .userDomainMask
        )
        cacheDirectory = paths[0].appendingPathComponent("loan4u_cache")
        try? fileManager.createDirectory(
            at: cacheDirectory,
            withIntermediateDirectories: true
        )
    }
    
    func savePrediction(_ result: PredictionResult) throws {
        let encoder = JSONEncoder()
        let data = try encoder.encode(result)
        
        let filename = "\(result.requestID).json"
        let fileURL = cacheDirectory.appendingPathComponent(filename)
        
        try data.write(to: fileURL)
    }
    
    func getPredictionHistory(limit: Int = 100) -> [PredictionResult] {
        let urls = try? fileManager.contentsOfDirectory(
            at: cacheDirectory,
            includingPropertiesForKeys: nil
        )
        
        var results: [PredictionResult] = []
        for url in urls?.prefix(limit) ?? [] {
            if let data = try? Data(contentsOf: url),
               let result = try? JSONDecoder().decode(
                   PredictionResult.self,
                   from: data
               ) {
                results.append(result)
            }
        }
        
        return results.sorted { $0.timestamp > $1.timestamp }
    }
}
```

---

## 🤖 Android 기술 스택

### 언어 & 프레임워크

```
Kotlin 1.9+
├─ Jetpack (Google 권장)
│  ├─ Compose (UI)
│  ├─ ViewModel (상태 관리)
│  ├─ LiveData (반응형 데이터)
│  ├─ Room (로컬 DB)
│  └─ DataStore (설정 저장)
│
├─ TensorFlow Lite (모델 추론)
│
└─ Hilt (의존성 주입)
```

### 아키텍처

**MVVM + Repository Pattern**
```
App
├─ data/
│  ├─ models/
│  │  ├─ PropertyInput.kt
│  │  ├─ PredictionResult.kt
│  │  └─ CacheEntry.kt
│  │
│  ├─ dao/
│  │  └─ PredictionDao.kt (Room)
│  │
│  ├─ database/
│  │  └─ PredictionDatabase.kt
│  │
│  └─ repository/
│     ├─ PredictionRepository.kt
│     └─ CacheRepository.kt
│
├─ ui/
│  ├─ screens/
│  │  ├─ PropertyInputScreen.kt
│  │  ├─ PredictionResultScreen.kt
│  │  └─ HistoryScreen.kt
│  │
│  ├─ components/
│  │  ├─ RegionPicker.kt
│  │  ├─ AreaSlider.kt
│  │  └─ ConfidenceMeter.kt
│  │
│  └─ theme/
│     ├─ Theme.kt
│     ├─ Color.kt
│     └─ Typography.kt
│
├─ viewmodel/
│  ├─ PropertyInputViewModel.kt
│  └─ PredictionViewModel.kt
│
└─ services/
   ├─ MLModelService.kt (TFLite)
   ├─ FeatureEngineer.kt
   └─ ValidationService.kt
```

### TensorFlow Lite 통합

**모델 변환 파이프라인**
```
ONNX → ONNX Converter → .pb → TFLite Converter → .tflite
                                    ↓
                            assets/models/
                                    ↓
                            Android App Load
```

**코드 예시**
```kotlin
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.support.tensorbuffer.TensorBuffer
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

class MLModelService(private val context: Context) {
    private val models = mutableMapOf<String, Interpreter>()
    
    fun loadModels() {
        // 모델 로드 (assets/models에서)
        val nationwide = loadModelFromAssets("KR_nationwide_lite_int8.tflite")
        models["nationwide"] = Interpreter(nationwide)
        
        // 지역별 모델 로드
        listOf("seoul", "busan", "gyeonggi", "daegu", "incheon").forEach { region ->
            val model = loadModelFromAssets("KR_${region}_lite_int8.tflite")
            models[region] = Interpreter(model)
        }
    }
    
    fun predictProperty(input: PropertyInput): Double? {
        val model = selectModel(input.region)
        
        // TFLite 입력 생성 (float32 배열)
        val inputFeatures = createInputArray(input)
        val inputBuffer = TensorBuffer.createFixedSize(
            intArrayOf(1, 22),  // batch=1, features=22
            DataType.FLOAT32
        )
        inputBuffer.loadArray(inputFeatures)
        
        // 추론 실행
        val outputBuffer = TensorBuffer.createFixedSize(
            intArrayOf(1, 1),  // batch=1, output=1
            DataType.FLOAT32
        )
        
        model.run(inputBuffer.buffer, outputBuffer.buffer)
        
        // 결과 추출
        val output = outputBuffer.floatArray
        return if (output.isNotEmpty()) output[0].toDouble() else null
    }
    
    private fun selectModel(region: String): Interpreter {
        return models[region] ?: models["nationwide"]!!
    }
    
    private fun loadModelFromAssets(filename: String): MappedByteBuffer {
        val fileDescriptor = context.assets.openFd(filename)
        val inputStream = FileInputStream(fileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        
        return fileChannel.map(
            FileChannel.MapMode.READ_ONLY,
            fileDescriptor.startOffset,
            fileDescriptor.declaredLength
        )
    }
}
```

### Jetpack Compose 레이아웃

**PropertyInputScreen**
```kotlin
@Composable
fun PropertyInputScreen(
    viewModel: PropertyInputViewModel,
    onPredictClick: () -> Unit
) {
    var expandedRegion by remember { mutableStateOf(false) }
    val regions = listOf("전국", "서울", "부산", "경기", "대구", "인천")
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "부동산 평가",
            style = MaterialTheme.typography.headlineMedium
        )
        
        // 지역 선택 (DropdownMenu)
        ExposedDropdownMenuBox(
            expanded = expandedRegion,
            onExpandedChange = { expandedRegion = it }
        ) {
            OutlinedTextField(
                value = viewModel.region,
                onValueChange = { },
                label = { Text("지역") },
                readOnly = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor(),
                trailingIcon = {
                    ExposedDropdownMenuDefaults.TrailingIcon(
                        expanded = expandedRegion
                    )
                }
            )
            
            ExposedDropdownMenu(
                expanded = expandedRegion,
                onDismissRequest = { expandedRegion = false }
            ) {
                regions.forEach { region ->
                    DropdownMenuItem(
                        text = { Text(region) },
                        onClick = {
                            viewModel.updateRegion(region)
                            expandedRegion = false
                        }
                    )
                }
            }
        }
        
        // 면적 슬라이더
        Column {
            Text(
                "면적: ${viewModel.area.toInt()}㎡",
                style = MaterialTheme.typography.labelMedium
            )
            Slider(
                value = viewModel.area,
                onValueChange = { viewModel.updateArea(it) },
                valueRange = 20f..300f,
                modifier = Modifier.fillMaxWidth()
            )
        }
        
        // 건축년도 (DatePicker)
        OutlinedTextField(
            value = viewModel.buildYear,
            onValueChange = { viewModel.updateBuildYear(it) },
            label = { Text("건축년도") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )
        
        // 기타 입력들...
        
        Spacer(modifier = Modifier.weight(1f))
        
        // 예측 버튼
        Button(
            onClick = onPredictClick,
            enabled = viewModel.isValid(),
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Home,
                contentDescription = null,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text("가격 평가")
        }
    }
}
```

**PredictionResultScreen**
```kotlin
@Composable
fun PredictionResultScreen(
    result: PredictionResult,
    onShareClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 예측 가격 카드
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "예상 가격",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    "${String.format("%,d", result.estimatedPrice.toLong())}원",
                    style = MaterialTheme.typography.displaySmall,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
            }
        }
        
        // 신뢰도 게이지
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("신뢰도")
                    Text("${(result.confidence * 100).toInt()}%")
                }
                
                LinearProgressIndicator(
                    progress = result.confidence.toFloat(),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp),
                    color = confidenceColor(result.confidence),
                    trackColor = MaterialTheme.colorScheme.surfaceVariant
                )
            }
        }
        
        // 가격 범위
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("예상 범위", style = MaterialTheme.typography.labelMedium)
                
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("최소", style = MaterialTheme.typography.labelSmall)
                        Text(
                            "${String.format("%,d", result.priceMin.toLong())}원",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("최대", style = MaterialTheme.typography.labelSmall)
                        Text(
                            "${String.format("%,d", result.priceMax.toLong())}원",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        // 공유 버튼
        Button(
            onClick = onShareClick,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Share,
                contentDescription = null
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text("결과 공유")
        }
    }
}

@Composable
private fun confidenceColor(confidence: Double): Color {
    return when {
        confidence > 0.8 -> Color.Green
        confidence > 0.6 -> Color.Yellow
        else -> Color.Red
    }
}
```

### Room 데이터베이스

**Entity 정의**
```kotlin
import androidx.room.*

@Entity(tableName = "predictions")
data class PredictionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    
    @ColumnInfo(name = "request_id")
    val requestId: String,
    
    @ColumnInfo(name = "region")
    val region: String,
    
    @ColumnInfo(name = "area")
    val area: Double,
    
    @ColumnInfo(name = "estimated_price")
    val estimatedPrice: Double,
    
    @ColumnInfo(name = "confidence")
    val confidence: Double,
    
    @ColumnInfo(name = "timestamp")
    val timestamp: Long = System.currentTimeMillis()
)

@Dao
interface PredictionDao {
    @Insert
    suspend fun insert(prediction: PredictionEntity)
    
    @Query("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getRecent(limit: Int = 100): List<PredictionEntity>
    
    @Query("SELECT * FROM predictions WHERE region = :region ORDER BY timestamp DESC")
    suspend fun getByRegion(region: String): List<PredictionEntity>
    
    @Delete
    suspend fun delete(prediction: PredictionEntity)
}

@Database(entities = [PredictionEntity::class], version = 1)
abstract class PredictionDatabase : RoomDatabase() {
    abstract fun predictionDao(): PredictionDao
}
```

### 의존성 주입 (Hilt)

```kotlin
@HiltAndroidApp
class LoanApp : Application()

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): PredictionDatabase {
        return Room.databaseBuilder(
            context,
            PredictionDatabase::class.java,
            "predictions.db"
        ).build()
    }
    
    @Provides
    @Singleton
    fun providePredictionDao(db: PredictionDatabase): PredictionDao {
        return db.predictionDao()
    }
}

@Module
@InstallIn(SingletonComponent::class)
object ServiceModule {
    @Provides
    @Singleton
    fun provideMLModelService(@ApplicationContext context: Context): MLModelService {
        return MLModelService(context).apply { loadModels() }
    }
    
    @Provides
    @Singleton
    fun providePredictionRepository(
        dao: PredictionDao,
        mlService: MLModelService
    ): PredictionRepository {
        return PredictionRepository(dao, mlService)
    }
}
```

### 성능 특성

| 항목 | 수치 | 비고 |
|------|------|------|
| 모델 로딩 | < 800ms | 앱 시작 시 1회 |
| 예측 지연 | 8-20ms | Snapdragon 8 Gen 2 기준 |
| 메모리 사용 | ~100MB | 모델(43.3MB) + JVM + Compose |
| 배터리 영향 | < 1.5% per hour | 다소 높음 (JVM 오버헤드) |
| 앱 크기 | < 60MB | 모델 포함, Release 빌드 |

---

## 🔄 공통 아키텍처

### 특성 엔지니어링 (양쪽 동일)

```
PropertyInput
    ↓
┌─────────────────────┐
│ FeatureEngineering  │
├─────────────────────┤
│ 1. 기본 특성        │
│    - area_m2        │
│    - building_age   │
│    - floor          │
│                     │
│ 2. 파생 특성        │
│    - price_per_m2   │
│    - is_gangnam     │
│    - rate_impact    │
│                     │
│ 3. 정규화           │
│    - StandardScaler │
│    - [0, 1] 범위   │
└─────────────────────┘
    ↓
22개 특성 배열 [float32]
    ↓
모델 입력
```

### 오프라인 추론 워크플로우

```
사용자 입력
    ↓
입력 검증
    ↓
특성 엔지니어링 (22개)
    ↓
캐시 확인 (SHA256 해시)
    ├─ HIT: 캐시된 결과 반환 (2ms)
    └─ MISS:
       ↓
       지역별 모델 선택
       ↓
       Core ML / TFLite 추론 (5-20ms)
       ↓
       결과 후처리
       ↓
       캐시 저장 (24h TTL)
       ↓
       결과 반환
```

### 모델 선택 로직

```kotlin
fun selectModel(region: String): String {
    return when (region.lowercase()) {
        "서울" -> "KR_seoul_lite_int8.tflite"
        "부산" -> "KR_busan_lite_int8.tflite"
        "경기" -> "KR_gyeonggi_lite_int8.tflite"
        "대구" -> "KR_daegu_lite_int8.tflite"
        "인천" -> "KR_incheon_lite_int8.tflite"
        else -> "KR_nationwide_lite_int8.tflite"
    }
}
```

---

## 💾 로컬 스토리지 전략

### iOS (FileSystem)
- **위치**: `~/Library/Caches/loan4u_cache/`
- **형식**: JSON 파일
- **캐시**: `[requestID].json` (24시간 TTL)

### Android (Room + DataStore)
- **Room**: 예측 이력 DB
- **DataStore**: 사용자 설정, 최근 검색

---

## 🔒 보안 & 프라이버시

### 모델 보호
```
✅ 모델은 앱 번들에 내장 (추출 불가)
✅ 네트워크 전송 없음 (완전 오프라인)
✅ INT8 양자화 (복호화 어려움)
```

### 데이터 보호
```
✅ 예측 결과만 로컬 저장
✅ 입력 데이터는 메모리에만 (휘발성)
✅ 사용자 동의하에만 클라우드 동기화
```

### 권한 요청
**iOS**
- 네트워크: 선택사항 (클라우드 동기화)
- 카메라: 선택사항 (사진 업로드)

**Android**
- READ_EXTERNAL_STORAGE (선택)
- INTERNET (클라우드 서비스용, 선택)

---

## 📊 배포 & 배포판

### iOS
- **최소 버전**: iOS 14.0+
- **배포**: App Store
- **사이닝**: Apple Developer Certificate
- **크기**: ~45MB (모델 포함)

### Android
- **최소 API**: API 26 (Android 8.0+)
- **배포**: Google Play
- **사이닝**: Google Play Signing
- **크기**: ~55MB (모델 + JVM 오버헤드)

---

## ⚡ 성능 최적화 체크리스트

### iOS
- [x] Core ML on-device 추론 (네트워크 불필요)
- [x] 모델 로드 시 최적화 (.mlmodel 컴파일)
- [x] 메모리 풀링 (재사용 가능한 버퍼)
- [x] 비동기 UI 업데이트 (Main thread 블로킹 회피)
- [x] 캐시 메모리 관리 (LRU)

### Android
- [x] TFLite GPU Delegate (옵션)
- [x] NNAPI 활용 (가속화, API 29+)
- [x] 코루틴 (비동기 처리)
- [x] LazyColumn (리스트 최적화)
- [x] ProGuard/R8 (코드 최적화)

---

## 🧪 테스트 전략

### 단위 테스트 (Unit Tests)
- FeatureEngineering 로직
- 특성 정규화
- 캐시 키 생성

### 통합 테스트 (Integration Tests)
- 모델 로딩 → 추론 → 결과 저장 전체 플로우
- 캐시 hit/miss 동작
- 오프라인 모드 검증

### UI 테스트 (UI Tests)
- 입력 폼 상호작용
- 결과 화면 표시
- 공유 기능

---

## 📱 앱 개발 일정

| 단계 | iOS | Android | 기간 |
|------|-----|---------|------|
| 1. 프로젝트 셋업 | Xcode | Android Studio | 1일 |
| 2. UI 구현 | SwiftUI | Jetpack Compose | 4일 |
| 3. 모델 통합 | Core ML | TensorFlow Lite | 2일 |
| 4. 기능 구현 | 캐싱, 공유 | 캐싱, 공유 | 2일 |
| 5. 테스트 | Unit + UI | Unit + UI | 2일 |
| 6. 최적화 | 성능 튜닝 | 배터리 최적화 | 1일 |
| 7. 배포 준비 | App Store | Google Play | 2일 |

**총 소요 기간**: 2주 (병행 개발)

---

이제 구현을 시작합니다. iOS와 Android 모두 개발을 진행하겠습니다.

