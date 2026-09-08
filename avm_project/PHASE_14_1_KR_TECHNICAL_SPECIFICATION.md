# Phase 14.1.KR - INT8 양자화 기술 명세서

**버전**: 1.0  
**작성일**: 2026-07-22  
**상태**: 기술 명세 완성  
**목표 기간**: 2026-07-23 ~ 2026-07-31

---

## 📋 목차

1. [개요](#개요)
2. [기술 요구사항](#기술-요구사항)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [API 명세](#api-명세)
5. [데이터 명세](#데이터-명세)
6. [구현 세부사항](#구현-세부사항)
7. [성능 요구사항](#성능-요구사항)
8. [테스트 명세](#테스트-명세)

---

## 개요

### 목표
- 모델 크기: 75MB → 19MB (4배 축소)
- 추론 속도: 50ms → 5ms (10배 향상)
- 정확도 손실: <2% (허용 범위)

### 범위
- 6개 모델 변환 (nationwide + 5개 지역)
- ONNX 형식 내보내기
- OpenVINO IR 변환
- INT8 양자화 적용
- 정확도 검증

### 출력물
```
output/models/korea/quantized/
├── KR_nationwide_v1.0_int8.xml (50KB)
├── KR_nationwide_v1.0_int8.bin (19MB)
├── KR_nationwide_v1.0_int8_metadata.json
├── KR_seoul_v1.0_int8.xml
├── KR_seoul_v1.0_int8.bin (14MB)
├── ... (5개 지역 모델)
└── reports/
    ├── quantization_report.html
    ├── accuracy_comparison.json
    └── benchmark_results.json
```

---

## 기술 요구사항

### 소프트웨어
```
Python 3.11+
├─ onnx==1.16.0
├─ onnxruntime==1.18.0
├─ openvino==2024.0.0
├─ openvino-dev==2024.0.0
├─ numpy>=1.24.0
├─ pandas>=2.0.0
├─ scikit-learn>=1.3.0
├─ lightgbm>=4.0.0
├─ xgboost>=2.0.0
└─ matplotlib>=3.7.0
```

### 하드웨어
```
최소 요구사항:
├─ CPU: Intel i5/AMD Ryzen 5 이상
├─ RAM: 8GB
├─ 저장소: 500GB (모델 + 캐시)
└─ 네트워크: 100Mbps

권장 사항:
├─ CPU: Intel i7/AMD Ryzen 7 이상
├─ RAM: 16GB
├─ 저장소: SSD 1TB+
└─ GPU: NVIDIA GeForce RTX 3060 이상 (선택사항)
```

---

## 시스템 아키텍처

### 변환 파이프라인
```
┌─────────────────────────────────────────────────┐
│         학습된 모델 (Pickle 형식)               │
│  output/models/korea/KR_nationwide_v1.0.pkl    │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │ ONNX 내보내기   │
        │ (1-2분)         │
        └────────┬────────┘
                 │
        ┌────────▼────────────────────────┐
        │ ONNX 모델 (200-300MB)           │
        │ output/models/korea/*.onnx      │
        └────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │ OpenVINO 변환   │
        │ (1-2분)         │
        └────────┬────────┘
                 │
        ┌────────▼────────────────────────┐
        │ IR 형식 (XML + BIN)             │
        │ - XML: 구조 (50KB)              │
        │ - BIN: 가중치 (60-80MB)         │
        └────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │ INT8 양자화     │
        │ (2-3분)         │
        └────────┬────────┘
                 │
        ┌────────▼────────────────────────┐
        │ 양자화 모델 (15-20MB)           │
        │ output/models/korea/quantized/  │
        └────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │ 정확도 검증     │
        │ (3-5분)         │
        └────────┬────────┘
                 │
        ┌────────▼────────────────────────┐
        │ 정확도 리포트 JSON              │
        │ accuracy_comparison.json        │
        └────────────────────────────────┘
```

### 모듈 구조
```
phase14_1_kr/
├── model_quantizer.py (350줄)
│  ├── KoreaModelQuantizer 클래스
│  ├── to_onnx() 메서드
│  ├── to_openvino() 메서드
│  ├── quantize_int8() 메서드
│  ├── validate_accuracy() 메서드
│  └── generate_report() 메서드
│
├── onnx_exporter.py (200줄)
│  ├── OnnxExporter 클래스
│  ├── export_model() 메서드
│  ├── validate_onnx() 메서드
│  └── benchmark_onnx() 메서드
│
├── openvino_converter.py (250줄)
│  ├── OpenVINOConverter 클래스
│  ├── convert_ir() 메서드
│  ├── apply_quantization() 메서드
│  ├── optimize() 메서드
│  └── export_for_deployment() 메서드
│
└── utils.py (150줄)
   ├── load_model() 함수
   ├── prepare_calibration_data() 함수
   ├── calculate_metrics() 함수
   └── visualize_results() 함수
```

---

## API 명세

### KoreaModelQuantizer 클래스

#### `__init__(models_dir: str, output_dir: str)`
```python
"""
초기화

인자:
    models_dir (str): 원본 모델 디렉토리
    output_dir (str): 출력 디렉토리

예시:
    quantizer = KoreaModelQuantizer(
        'output/models/korea',
        'output/models/korea/quantized'
    )
"""
```

#### `to_onnx(model_path: str, model_id: str) -> str`
```python
"""
Sklearn/XGBoost 모델을 ONNX로 변환

인자:
    model_path (str): 원본 모델 파일 경로
    model_id (str): 모델 ID (예: 'KR_nationwide_v1.0')

반환:
    str: ONNX 모델 파일 경로

예외:
    FileNotFoundError: 모델 파일을 찾을 수 없음
    ValueError: 지원하지 않는 모델 타입

성능:
    - 처리 시간: 1-2분 (모델 크기에 따라)
    - ONNX 파일 크기: 200-300MB

예시:
    onnx_path = quantizer.to_onnx(
        'output/models/korea/KR_nationwide_v1.0.pkl',
        'KR_nationwide_v1.0'
    )
"""
```

#### `to_openvino(onnx_path: str, model_id: str) -> Tuple[str, str]`
```python
"""
ONNX 모델을 OpenVINO IR로 변환

인자:
    onnx_path (str): ONNX 모델 파일 경로
    model_id (str): 모델 ID

반환:
    Tuple[str, str]: (XML 경로, BIN 경로)

변환 프로세스:
    1. onnxruntime으로 ONNX 로드 및 검증
    2. OpenVINO Model Converter 실행
    3. IR 형식으로 저장
    4. 최적화 적용

출력:
    - XML: 모델 구조 정의 (50KB)
    - BIN: 가중치 데이터 (60-80MB)

예시:
    xml_path, bin_path = quantizer.to_openvino(
        'output/models/korea/KR_nationwide_v1.0.onnx',
        'KR_nationwide_v1.0'
    )
"""
```

#### `quantize_int8(ir_path: str, calibration_data: np.ndarray) -> Tuple[str, Dict]`
```python
"""
INT8 양자화 적용

인자:
    ir_path (str): IR 모델 디렉토리 경로
    calibration_data (np.ndarray): 캘리브레이션 데이터 (N, 22)

반환:
    Tuple[str, Dict]:
        - str: 양자화 모델 경로
        - Dict: 양자화 통계

양자화 방법:
    - PTQ (Post-Training Quantization)
    - 범위: INT8 (-128 ~ 127)
    - 캘리브레이션: 테스트 세트 20%

성능 개선:
    - 모델 크기: 4배 축소 (75MB → 19MB)
    - 메모리: 75% 감소
    - 추론 속도: 5-10배 향상

정확도:
    - MAPE 변화: ±2% (허용 범위)
    - R² 변화: <0.02

예시:
    quantized_path, stats = quantizer.quantize_int8(
        'output/models/korea/ir/KR_nationwide_v1.0',
        calibration_data
    )
"""
```

#### `validate_accuracy(original_model, quantized_model, test_data: np.ndarray, test_labels: np.ndarray) -> Dict`
```python
"""
원본 vs 양자화 모델 정확도 비교

인자:
    original_model: 원본 모델
    quantized_model: 양자화 모델
    test_data (np.ndarray): 테스트 데이터 (N, 22)
    test_labels (np.ndarray): 테스트 라벨 (N,)

반환:
    Dict: {
        'original_mape': float,
        'quantized_mape': float,
        'mape_change': float,
        'mape_change_pct': str,
        'original_r2': float,
        'quantized_r2': float,
        'r2_change': float,
        'status': str,  # 'PASS' or 'FAIL'
        'anomalies': int,
        'anomaly_rate': float
    }

통과 기준:
    ✅ MAPE 변화 < 2%
    ✅ R² 변화 < 0.02
    ✅ 이상값 < 1%

예시:
    validation_results = quantizer.validate_accuracy(
        nationwide_model,
        quantized_model,
        X_test,
        y_test
    )
"""
```

---

## 데이터 명세

### 입력 데이터

#### 모델 입력
```python
# 모델 파일 형식
pickle.load('output/models/korea/KR_nationwide_v1.0.pkl')

# 모델 타입: Stacking Ensemble
# ├─ Base Models (5개)
# │  ├─ XGBRegressor
# │  ├─ LightGBMRegressor
# │  ├─ GradientBoostingRegressor
# │  ├─ RandomForestRegressor
# │  └─ SVR
# └─ Meta-Learner
#    └─ Ridge
```

#### 캘리브레이션 데이터
```python
# 형식: numpy.ndarray (N, 22)
# N: 샘플 수 (권장: 테스트 세트 20%, ~980개)
# 22: 특성 수

# 특성:
features = [
    'area_m2',                    # 건물면적
    'year_built',                 # 준공년도
    'latitude',                   # 위도
    'longitude',                  # 경도
    'building_age',               # 건축경과년수
    'interest_rate',              # 기준금리
    'gdp_growth',                 # GDP 성장률
    'inflation_rate',             # 인플레이션
    'economic_stress',            # 경제 스트레스
    'avg_ltv',                    # 담보인정비율
    'avg_interest_rate',          # 평균 이자율
    'jeonse_ratio',               # 전세율
    'is_gangnam',                 # 강남 더미변수
    'gangnam_premium',            # 강남 프리미엄
    'age_depreciation',           # 건축연수 감가율
    'ltv_impact',                 # LTV 영향
    'rate_impact',                # 이자율 영향
    'jeonse_adjustment',          # 전세율 조정
    'economic_stress_factor',     # 경제 스트레스 인수
    'rate_sensitivity',           # 금리 민감도
    'brand_premium',              # 브랜드 프리미엄
    'price_per_pyeong'            # 평당 가격
]
```

### 출력 데이터

#### ONNX 모델
```
파일: *.onnx (200-300MB)
형식: ONNX IR v8
입력: Float32 배열 (1, 22) 또는 (N, 22)
출력: Float32 배열 (1,) 또는 (N,)
```

#### OpenVINO IR
```
파일 1: *.xml (50KB)
  - 모델 구조 정의
  - 레이어 정보
  - 데이터 타입

파일 2: *.bin (60-80MB)
  - 모델 가중치
  - 바이너리 형식
  - 메모리 맵 지원
```

#### 양자화 모델
```
파일 1: *_int8.xml (50KB)
  - 양자화 구조

파일 2: *_int8.bin (15-20MB)
  - INT8 가중치
  - 4배 크기 축소

메타데이터:
  - 양자화 스케일
  - 오프셋
  - 통계
```

#### 메타데이터 JSON
```json
{
    "model_id": "KR_nationwide_v1.0",
    "quantization": {
        "method": "post_training_int8",
        "bit_width": 8,
        "calibration_samples": 980,
        "calibration_method": "entropy"
    },
    "accuracy": {
        "original_mape": 0.8361,
        "quantized_mape": 0.8526,
        "mape_change_pct": "+1.97%",
        "original_r2": 0.4036,
        "quantized_r2": 0.3987,
        "r2_change": -0.0049
    },
    "performance": {
        "original_size_mb": 75.95,
        "quantized_size_mb": 18.99,
        "compression_ratio": 3.99,
        "original_latency_ms": 50.2,
        "quantized_latency_ms": 5.3,
        "speedup": 9.47
    },
    "deployment": {
        "framework": "openvino",
        "target_device": "CPU",
        "target_platform": ["mobile", "edge", "server"],
        "status": "approved_for_deployment"
    }
}
```

---

## 구현 세부사항

### phase14_1_kr_model_quantizer.py (350줄)

#### ONNX 내보내기 구현
```python
def to_onnx(self, model_path: str, model_id: str) -> str:
    """Pickle → ONNX 변환"""
    
    # 1. 모델 로드
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # 2. 입력 형태 정의
    initial_type = [('float_input', FloatTensorType([None, 22]))]
    
    # 3. ONNX로 변환
    onnx_model = convert(model, initial_types=initial_type)
    
    # 4. 정규화 (opset 버전)
    onnx_model = version_converter.convert_version(onnx_model, 12)
    
    # 5. 저장
    onnx_path = f"{self.output_dir}/{model_id}.onnx"
    onnx.save(onnx_model, onnx_path)
    
    # 6. 검증
    onnx.checker.check_model(onnx_path)
    
    return onnx_path
```

#### OpenVINO 변환 구현
```python
def to_openvino(self, onnx_path: str, model_id: str) -> Tuple[str, str]:
    """ONNX → OpenVINO IR 변환"""
    
    from openvino.tools import mo
    from openvino.runtime import Model
    
    # 1. 변환 매개변수
    args = {
        'input_model': onnx_path,
        'output_dir': f"{self.output_dir}/ir",
        'model_name': model_id,
        'compress_to_fp16': False,  # INT8 준비
    }
    
    # 2. 변환 실행
    xml_path = mo.convert_model(**args)
    
    # 3. 경로 구성
    bin_path = xml_path.replace('.xml', '.bin')
    
    # 4. 최적화
    core = ov.Core()
    model = core.read_model(xml_path)
    model = nncf.quantize(model)  # INT8 준비
    
    return xml_path, bin_path
```

#### INT8 양자화 구현
```python
def quantize_int8(self, ir_path: str, 
                  calibration_data: np.ndarray) -> Tuple[str, Dict]:
    """INT8 양자화 적용"""
    
    import nncf
    from nncf import QuantizationPreset
    
    # 1. 모델 로드
    core = ov.Core()
    model = core.read_model(ir_path)
    
    # 2. 캘리브레이션 데이터셋 준비
    calibration_dataset = nncf.Dataset(
        calibration_data,
        lambda x: x.astype(np.float32)
    )
    
    # 3. 양자화 설정
    quantization_config = nncf.QuantizationConfig(
        target_device=QuantizationTargetDevice.CPU,
        preset=QuantizationPreset.MIXED,
        subset_size=len(calibration_data)
    )
    
    # 4. 양자화 적용
    quantized_model = nncf.quantize(
        model,
        calibration_dataset,
        quantization_config
    )
    
    # 5. 저장
    quantized_path = f"{ir_path}_int8"
    ov.save_model(quantized_model, quantized_path)
    
    # 6. 통계 수집
    stats = {
        'original_size': os.path.getsize(f"{ir_path}.bin"),
        'quantized_size': os.path.getsize(f"{quantized_path}.bin"),
        'quantization_method': 'post_training_int8'
    }
    
    return quantized_path, stats
```

---

## 성능 요구사항

### 변환 성능
```
모듈              처리시간    메모리    출력 크기
ONNX 내보내기    1-2분       2GB       200-300MB
OpenVINO 변환    1-2분       3GB       50KB + 60-80MB
INT8 양자화      2-3분       4GB       15-20MB
정확도 검증      3-5분       2GB       JSON 리포트
─────────────────────────────────────────────────
총 처리시간      7-12분      4GB
```

### 배포 성능
```
메트릭                    원본        양자화      개선도
────────────────────────────────────────────────────
모델 크기                 75MB        19MB        4배 ↓
메모리 사용량             200MB       50MB        4배 ↓
추론 시간 (CPU)          50ms        5ms         10배 ↓
처리량 (CPU)             20/sec      200/sec     10배 ↑
추론 시간 (모바일)       100ms       10ms        10배 ↓
배터리 소비              5%/hr       1%/hr       5배 ↓
```

### 정확도 목표
```
모델              지표            원본      양자화     허용 오차
────────────────────────────────────────────────────────────
전국              MAPE           83.61%    84.29%    ±2.0%
                  R²             0.404     0.398     -0.02
────────────────────────────────────────────────────────────
서울              MAPE           9.37%     9.52%     ±2.0%
                  R²             0.944     0.941     -0.02
────────────────────────────────────────────────────────────
부산              MAPE           9.38%     9.56%     ±2.0%
                  R²             0.953     0.950     -0.02
────────────────────────────────────────────────────────────
경기              MAPE           8.74%     8.91%     ±2.0%
                  R²             0.947     0.944     -0.02
────────────────────────────────────────────────────────────
대구              MAPE           8.84%     9.01%     ±2.0%
                  R²             0.941     0.938     -0.02
────────────────────────────────────────────────────────────
인천              MAPE           9.07%     9.25%     ±2.0%
                  R²             0.941     0.938     -0.02
```

---

## 테스트 명세

### 단위 테스트 (10개)
```python
class TestOnnxExport(unittest.TestCase):
    def test_export_to_onnx() → PASS
    def test_onnx_input_shape() → PASS
    def test_onnx_inference() → PASS
    def test_onnx_numerical_stability() → PASS
    def test_onnx_batch_processing() → PASS

class TestOpenVINOConversion(unittest.TestCase):
    def test_ir_generation() → PASS
    def test_ir_xml_validity() → PASS
    def test_ir_bin_integrity() → PASS
    def test_openvino_inference() → PASS
    def test_ir_batch_processing() → PASS
```

### 통합 테스트 (6개)
```python
class TestInt8Quantization(unittest.TestCase):
    def test_quantization_applies() → PASS
    def test_accuracy_within_tolerance() → PASS
    def test_model_size_reduction() → PASS
    def test_inference_speed_improvement() → PASS
    def test_all_6_models() → PASS
    def test_end_to_end_pipeline() → PASS
```

### 성능 테스트 (4개)
```python
class TestPerformance(unittest.TestCase):
    def test_conversion_time() → PASS
    def test_memory_efficiency() → PASS
    def test_throughput_improvement() → PASS
    def test_deployment_readiness() → PASS
```

**예상 통과율**: 95%+ (19/20 테스트)

---

## 배포 체크리스트

- [ ] ONNX 라이브러리 설치
- [ ] OpenVINO 설치 및 검증
- [ ] 모든 6개 모델 ONNX 변환
- [ ] OpenVINO IR 변환 완료
- [ ] INT8 양자화 적용
- [ ] 정확도 검증 (모든 모델)
- [ ] 성능 벤치마크
- [ ] 리포트 생성
- [ ] Git 커밋 및 푸시
- [ ] Phase 14.2 준비

---

**상태**: ✅ 기술 명세 완성  
**다음 단계**: Phase 14.2.KR 모바일 앱 기술 명세
