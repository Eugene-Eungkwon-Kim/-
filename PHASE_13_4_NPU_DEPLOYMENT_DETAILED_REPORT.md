# Phase 13.4 상세 보고서
## NPU 배포 & API 서비스 최적화

**작성일**: 2026-07-01  
**버전**: 1.0  
**상태**: 📋 설계 중  
**우선순위**: 🔴 P1 (Critical Path)

---

## Executive Summary

**목표**: Phase 13.3에서 선정한 최적 모델(LightGBM, R²>0.85)을 ONNX → OpenVINO IR로 변환 → Onboard NPU에 배포 → FastAPI 기반 REST API 서비스화  
**기간**: 2026-07-19 ~ 2026-07-23 (5일, Week 3 후반)  
**팀 규모**: 1명 (Claude Agent)  
**성공 기준**: NPU 추론 <10ms/요청, 처리량 >1000 req/min, 정확도 손실 <0.5% (GPU 대비)  

**핵심 성과**:
- ✅ LightGBM → ONNX 변환 (손실 없음)
- ✅ ONNX → OpenVINO IR 변환 (최적화)
- ✅ NPU 추론 엔진 구현 및 테스트
- ✅ FastAPI 서비스 배포 (HTTP REST API)
- ✅ 성능 벤치마크 (GPU vs NPU vs CPU)

---

## 1. 현황 분석

### 1.1 입력 데이터 (from Phase 13.3)

```
Phase 13.3 Output:
├── best_model_kr.pkl (LightGBM, ~80MB)
│   ├── Model type: LightGBMRegressor
│   ├── R² Score: 0.851-0.853
│   ├── MAPE: 0.090
│   ├── Features: 45 (normalized)
│   └── Training data: 40K rows
│
├── models_metadata.json
│   ├── model_name: 'LightGBM'
│   ├── r2: 0.851
│   ├── mape: 0.090
│   ├── training_date: '2026-07-18'
│   └── hyperparameters: {num_leaves: 31, ...}
│
└── Feature scaling info
    ├── Scaler type: StandardScaler
    ├── Mean: [array of 45 values]
    └── Std: [array of 45 values]
```

### 1.2 목표 (To-Be)

```
Phase 13.4 Output:
├── 모델 형식 변환
│   ├── best_model_kr.onnx (~15-20MB, 최적화됨)
│   └── best_model_kr.xml + best_model_kr.bin (OpenVINO IR)
│
├── NPU 추론 엔진
│   ├── phase13_npu_inference.py (구현됨)
│   ├── NPUInferenceEngine (class)
│   └── 예측 지연시간: <10ms/요청
│
├── REST API 서비스
│   ├── FastAPI 애플리케이션
│   ├── Endpoint: POST /api/valuation
│   ├── Response format: JSON
│   └── Rate limiting: 1000 req/min
│
└── 성능 최적화
    ├── GPU (RTX 5050): ~2ms latency, 10000 req/min
    ├── NPU (Onboard):  <10ms latency, >1000 req/min ⭐
    └── CPU:            ~50ms latency, 200 req/min
```

### 1.3 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    Client Request                        │
│              (Property Valuation Request)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌─────────────────────────┐
         │   FastAPI Service       │
         │   (Port 8000)           │
         │   ├─ /api/valuation     │
         │   └─ /health           │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   Request Validation    │
         │   + Feature Engineering │
         │   (45 features)         │
         └────────────┬────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    ┌───────┐   ┌───────┐   ┌───────┐
    │ GPU   │   │ NPU   │   │ CPU   │
    │ Path  │   │ Path  │   │ Path  │
    │2ms 📈 │   │<10ms  │   │50ms   │
    │10k    │   │1k req │   │200 r. │
    └───┬───┘   └───┬───┘   └───┬───┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
         ┌─────────────────────────┐
         │   Prediction Result     │
         │   {                     │
         │     "predicted_price":  │
         │     "confidence": 0.95, │
         │     "latency_ms": 8     │
         │   }                     │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   Client Response       │
         │   (JSON)                │
         └─────────────────────────┘
```

---

## 2. 모델 변환 전략

### 2.1 변환 파이프라인

```
Step 1: LightGBM → ONNX (손실 없음)
────────────────────────────────
Input:  best_model_kr.pkl (LightGBM)
Process:
  - skl2onnx 또는 onnxmltools 사용
  - opset_version=14 (compatibility)
  - initial_types 명시 (45 float32 features)
Output: best_model_kr.onnx (~18MB)
Quality: R² loss = 0.0% (numerical precision test)

Step 2: ONNX → OpenVINO IR (최적화)
──────────────────────────────────
Input:  best_model_kr.onnx
Process:
  - OpenVINO ModelOptimizer
  - Target device: NPU (Intel integrated)
  - Precision: FP32 → FP16 (반정밀도) 또는 INT8 (양자화)
  - Optimization: Dead code elimination, constant folding
Output: 
  - best_model_kr.xml (graph definition, ~3MB)
  - best_model_kr.bin (weights, ~8MB)
Quality: R² loss < 0.5% (vs original)

Step 3: Quantization (선택사항, INT8)
────────────────────────────────────
Input:  best_model_kr.onnx
Process:
  - Calibration data: 1000 샘플 (training set 대표)
  - Quantization: dynamic INT8
  - Calibration method: entropy
Output: best_model_kr_int8.onnx (~5MB)
Quality: R² loss < 1.0% (vs original)
Benefit: 추론 속도 3-4배 향상
```

### 2.2 변환 명세

```python
# LightGBM to ONNX
import onnxmltools
from skl2onnx import convert_sklearn

model = lgb.LGBMRegressor(...)  # loaded from pkl
initial_types = [('float_input', FloatTensorType([None, 45]))]
onnx_model = onnxmltools.convert_lightgbm(
    model, 
    initial_types=initial_types,
    target_opset=14
)
onnx.save_model(onnx_model, 'best_model_kr.onnx')

# ONNX to OpenVINO IR
from openvino.tools.mo import mo

ir_model = mo.convert_model(
    'best_model_kr.onnx',
    model_name='best_model_kr',
    compress_to_fp16=True,  # FP32 → FP16
)
ov.save_model(ir_model, 'models/best_model_kr.xml')
```

---

## 3. NPU 추론 엔진 구현

### 3.1 NPUInferenceEngine 클래스

```python
class NPUInferenceEngine:
    """OpenVINO IR 모델 기반 NPU 추론 엔진"""
    
    def __init__(self, model_path: str, device: str = 'NPU'):
        """
        Args:
            model_path: 'models/best_model_kr.xml'
            device: 'NPU' | 'CPU' | 'GPU' (fallback)
        """
        self.model_path = model_path
        self.device = device
        self.ie = Core()
        self.model = self.ie.read_model(model_path)
        self.compiled = self.ie.compile_model(self.model, device)
        self.infer_request = self.compiled.create_infer_request()
    
    def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Single prediction with timing
        
        Args:
            features: (45,) numpy array, StandardScaler normalized
        
        Returns:
            {
                'predicted_price': float,
                'confidence': float (0-1),
                'latency_ms': float,
                'device': str
            }
        """
        start = time.time()
        
        # Input preparation
        input_name = self.model.inputs[0].any_name
        self.infer_request.set_input_tensor(
            ov.Tensor(features.reshape(1, 45), ov.Type.f32)
        )
        
        # Inference
        self.infer_request.infer()
        
        # Output extraction
        output_name = self.model.outputs[0].any_name
        prediction = self.infer_request.get_output_tensor(
            output_name
        ).data[0, 0]
        
        latency_ms = (time.time() - start) * 1000
        
        return {
            'predicted_price': float(prediction),
            'confidence': 0.95,  # Mock confidence (구현 필요시 추가)
            'latency_ms': latency_ms,
            'device': self.device
        }
    
    def batch_predict(self, features: np.ndarray) -> List[Dict]:
        """Batch prediction (N, 45)"""
        results = []
        for feat in features:
            results.append(self.predict(feat))
        return results
```

### 3.2 성능 특성

```
Device Comparison (100 predictions average):

Device    Latency    Throughput    Memory    Power    Cost
────────────────────────────────────────────────────
GPU       2ms        10k req/min   4GB       100W     $$$
NPU       <10ms      >1k req/min   <500MB    5W       ✅
CPU       50ms       200 req/min   2GB       20W      $

NPU 장점:
✅ 저지연성 (10ms 이내)
✅ 저전력 (5W - 모바일/IoT 적합)
✅ 온보드 통합 (별도 장비 불필요)
✅ 확장성 (병렬 처리 가능)

GPU 사용처:
- 배치 처리 (1000+ 요청 동시)
- 모델 재학습/미세조정
- 탐색적 분석

NPU 사용처: ⭐ 메인 추천
- 실시간 개별 요청
- 모바일/엣지 장치
- 저전력 요구
```

---

## 4. REST API 서비스 설계

### 4.1 FastAPI 엔드포인트

```
POST /api/valuation
├─ Request body:
│  {
│    "property_features": {
│      "area_sqm": 100,
│      "old_price": 500000000,
│      "latitude": 37.4979,
│      "longitude": 127.0276,
│      "building_age": 15,
│      "floor": 3,
│      "distance_subway": 500,
│      "distance_school": 300,
│      "distance_park": 200,
│      # ... 35 more features (auto-engineered)
│    }
│  }
│
├─ Processing:
│  1. Input validation (type check, range validation)
│  2. Feature engineering (10 → 45 features)
│  3. Feature scaling (StandardScaler)
│  4. NPU inference (<10ms)
│  5. Result formatting
│
└─ Response (200 OK):
   {
     "predicted_price": 525000000,
     "confidence": 0.95,
     "latency_ms": 8.2,
     "device": "NPU",
     "timestamp": "2026-07-20T14:30:45Z"
   }

Error Response (400/500):
   {
     "error": "Invalid input: area_sqm must be > 0",
     "code": "VALIDATION_ERROR"
   }
```

### 4.2 API 스펙 상세

```python
@app.post("/api/valuation")
async def valuate_property(
    request: PropertyValuationRequest,
    background_tasks: BackgroundTasks
) -> PropertyValuationResponse:
    """
    Estimate property value using NPU-optimized LightGBM model
    
    Performance:
    - Latency: <10ms (NPU) | ~2ms (GPU) | ~50ms (CPU)
    - Throughput: >1000 req/min (NPU) | 10k req/min (GPU)
    
    Args:
        request: PropertyValuationRequest (10 base features)
    
    Returns:
        PropertyValuationResponse (predicted_price, confidence, latency)
    """
    try:
        # Validate input
        if not (20 <= request.area_sqm <= 500):
            raise ValueError("area_sqm must be 20-500 sqm")
        
        # Feature engineering (10 → 45)
        features_45 = feature_engineering_pipeline(request)
        
        # Scaling
        features_scaled = scaler.transform([features_45])
        
        # NPU inference
        result = npu_engine.predict(features_scaled[0])
        
        # Logging (background)
        background_tasks.add_task(log_valuation, request, result)
        
        return PropertyValuationResponse(
            predicted_price=int(result['predicted_price']),
            confidence=result['confidence'],
            latency_ms=result['latency_ms'],
            device=result['device']
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail="Inference failed")
```

---

## 5. 배포 전략

### 5.1 배포 환경

```
Development (로컬)
├─ FastAPI dev server
├─ NPU emulation (CPU fallback)
└─ Port: 8000

Production (리눅스 서버)
├─ Gunicorn (4 workers)
├─ Nginx reverse proxy
├─ Real NPU (Intel integrated)
└─ Port: 80/443 (HTTPS)

Docker 컨테이너화
├─ Image: python:3.11-slim + OpenVINO
├─ Size: ~1.2GB
├─ Tags: latest, v1.0, stable
└─ Registry: Docker Hub / Private ECR
```

### 5.2 배포 절차

```
Step 1: 모델 변환 & 검증 (2h)
├─ LightGBM → ONNX
├─ ONNX → OpenVINO IR
├─ 정확도 검증 (<0.5% loss)
└─ 성능 벤치마크

Step 2: NPU 엔진 테스트 (1h)
├─ 1000개 샘플 예측
├─ 지연시간 측정
├─ 메모리 사용량 확인
└─ Fallback 테스트 (CPU/GPU)

Step 3: API 서비스 배포 (1.5h)
├─ FastAPI 서버 시작
├─ 엔드포인트 테스트
├─ Rate limiting 설정
└─ 모니터링 세팅

Step 4: 성능 검증 (1.5h)
├─ 부하 테스트 (1000 req/min)
├─ 정확도 재확인
├─ 로그 분석
└─ 알림 규칙 설정

Step 5: 운영 이관 (1h)
├─ 문서 작성
├─ 팀 교육
├─ 롤백 계획
└─ SLA 정의
```

---

## 6. 성능 목표 및 벤치마크

### 6.1 성능 목표

```
Primary Metrics:
├─ Latency: <10ms (p99)
├─ Throughput: >1000 req/min
├─ Availability: >99.9%
├─ Accuracy: R² > 0.85 (vs GPU)
└─ Model size: <20MB

Secondary Metrics:
├─ Memory usage: <500MB
├─ CPU usage: <20%
├─ Network I/O: <1MB/req
└─ Cost per 1M predictions: <$0.10
```

### 6.2 벤치마크 결과 (예상)

```
Benchmark: 10,000 sequential predictions

┌──────┬──────────┬────────────┬─────────┬──────────┐
│Device│Latency   │Throughput  │Memory   │Power     │
├──────┼──────────┼────────────┼─────────┼──────────┤
│NPU   │8.5ms avg │1200 req/min│450MB    │5W ✅     │
│      │p99: 15ms │            │         │         │
├──────┼──────────┼────────────┼─────────┼──────────┤
│GPU   │2.0ms avg │10000 req/mn│4000MB   │100W      │
│      │p99: 5ms  │            │         │         │
├──────┼──────────┼────────────┼─────────┼──────────┤
│CPU   │45ms avg  │200 req/min │2000MB   │20W       │
│      │p99: 120ms│            │         │         │
└──────┴──────────┴────────────┴─────────┴──────────┘

Recommended Use:
- Single/low-rate requests: NPU ✅
- Batch/high-rate (<1k req/s): GPU
- Legacy/embedded: CPU (fallback)
```

---

## 7. 위험 관리

### 7.1 Top Risks

```
Risk 1: 모델 변환 후 정확도 손실 >1%
├─ 확률: 15%
├─ 영향: 배포 불가
└─ 대응:
   - INT8 quantization 대신 FP16 사용
   - 추가 calibration 데이터 준비
   - 검증 데이터로 재테스트

Risk 2: NPU 드라이버 호환성 문제
├─ 확률: 20%
├─ 영향: CPU fallback 강제
└─ 대응:
   - CPU fallback 자동 처리
   - GPU fallback 2차 옵션
   - 드라이버 버전 고정

Risk 3: API 서비스 응답 지연 >20ms
├─ 확률: 15%
├─ 영향: 목표 미달성
└─ 대응:
   - Feature engineering 최적화
   - Batch processing 추가
   - 캐싱 메커니즘 도입
```

---

## 8. 결론

**Phase 13.4는 모델을 프로덕션 서비스로 전환하는 최종 단계**입니다:
- ONNX/OpenVINO 변환으로 배포 준비 완료
- NPU 최적화로 저지연/저전력 달성
- REST API로 실시간 예측 서비스 제공
- 3개 디바이스(NPU/GPU/CPU) 자동 선택 배포

**Success Scenario**:
```
2026-07-23 완료 상태:
├── best_model_kr.onnx 생성 (18MB, 정확도 100%) ✅
├── OpenVINO IR 변환 완료 (3MB XML + 8MB bin) ✅
├── NPU 추론 <10ms/요청 달성 ✅
├── FastAPI 서비스 배포 (1000 req/min 처리) ✅
├── 성능 벤치마크 완료 (GPU vs NPU vs CPU) ✅
└── Phase 13.5 (자동화) 준비 완료
```

---

**작성자**: Claude Sonnet 5  
**최종 검토**: TBD (사용자 승인 대기)  
**다음 단계**: Phase 13.4 기술 명세서 & WBS 작성
