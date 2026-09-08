# Phase 13.4 기술 명세서
## NPU 배포 & API 서비스 최적화

**작성일**: 2026-07-01  
**버전**: 1.0  
**상태**: 📋 설계 중  
**기술 스택**: OpenVINO, FastAPI, LightGBM ONNX  

---

## 1. 모델 변환 명세

### 1.1 ONNX 변환 상세

```python
# Configuration
ONNX_CONVERSION_CONFIG = {
    'source_model': 'models/best_model_kr.pkl',
    'output_path': 'models/best_model_kr.onnx',
    'opset_version': 14,
    'target_opset': 14,
    'do_constant_folding': True,
    'verbose': True,
    'ir_version': 8,
}

# Input signature
INPUT_SPEC = {
    'input_name': 'float_input',
    'input_shape': [None, 45],
    'input_type': 'float32',
    'description': 'Normalized feature vector (45 features, StandardScaler)'
}

# Output signature
OUTPUT_SPEC = {
    'output_name': 'predictions',
    'output_shape': [None, 1],
    'output_type': 'float64',
    'description': 'Predicted property price in KRW'
}

# Validation
VALIDATION_THRESHOLD = {
    'r2_loss': 0.005,  # <0.5% loss acceptable
    'prediction_diff': 100000,  # <100K KRW difference
    'speed_ratio': 1.0  # No speed penalty vs pkl
}
```

### 1.2 변환 프로세스

```python
import onnxmltools
import lightgbm as lgb
import onnx

def convert_lightgbm_to_onnx():
    # Load model
    model = lgb.Booster(model_file='models/best_model_kr.pkl')
    
    # Get initial types
    from skl2onnx.common.data_types import FloatTensorType
    initial_types = [('float_input', FloatTensorType([None, 45]))]
    
    # Convert
    onnx_model = onnxmltools.convert_lightgbm(
        model,
        initial_types=initial_types,
        target_opset=14,
        model_name='best_model_kr'
    )
    
    # Validate
    onnx.checker.check_model(onnx_model)
    
    # Save
    onnx.save_model(onnx_model, 'models/best_model_kr.onnx')
    print(f"✓ ONNX model saved: {onnx_model.graph.node.__len__()} nodes")
    
    return onnx_model
```

### 1.3 OpenVINO IR 변환

```bash
# Command line conversion
mo --input_model models/best_model_kr.onnx \
   --output_dir models/openvino_ir \
   --model_name best_model_kr \
   --compress_to_fp16 \
   --verbose

# Output files
models/openvino_ir/
├── best_model_kr.xml (graph definition, ~3MB)
├── best_model_kr.bin (weights, ~8MB)
└── best_model_kr.mapping (variable mapping)

# Python conversion (alternative)
from openvino.tools import mo

ir_model = mo.convert_model(
    'models/best_model_kr.onnx',
    model_name='best_model_kr',
    compress_to_fp16=True,  # FP32→FP16 optimization
)
ov.save_model(ir_model, 'models/openvino_ir/best_model_kr.xml')
```

### 1.4 정확도 검증

```python
def validate_conversion_accuracy():
    """Compare predictions: LightGBM pkl vs ONNX vs OpenVINO IR"""
    
    # Load models
    model_pkl = lgb.Booster(model_file='models/best_model_kr.pkl')
    
    import onnxruntime as ort
    session_onnx = ort.InferenceSession('models/best_model_kr.onnx')
    
    from openvino.runtime import Core
    core = Core()
    model_ir = core.read_model('models/openvino_ir/best_model_kr.xml')
    
    # Test on 1000 validation samples
    test_samples = X_test[:1000]  # (1000, 45)
    
    # Predictions
    pred_pkl = model_pkl.predict(test_samples)
    pred_onnx = session_onnx.run(None, {'float_input': test_samples.astype('float32')})[0]
    
    # Comparison
    diff_onnx = np.mean(np.abs(pred_pkl - pred_onnx.flatten()))
    r2_loss = 1 - np.corrcoef(pred_pkl, pred_onnx.flatten())[0, 1]
    
    assert diff_onnx < 100_000, f"ONNX diff too large: {diff_onnx}"
    assert r2_loss < 0.005, f"R² loss too large: {r2_loss}"
    
    print(f"✓ Conversion validation passed")
    print(f"  - Max price diff: {np.max(np.abs(pred_pkl - pred_onnx.flatten())):,.0f} KRW")
    print(f"  - R² loss: {r2_loss*100:.2f}%")
```

---

## 2. NPU 추론 엔진 명세

### 2.1 NPUInferenceEngine 클래스

```python
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np
import time
from openvino.runtime import Core, get_version
import logging

logger = logging.getLogger(__name__)

@dataclass
class InferenceResult:
    """Inference result container"""
    predicted_price: float
    confidence: float  # 0-1
    latency_ms: float
    device: str
    timestamp: str

class NPUInferenceEngine:
    """OpenVINO IR 기반 NPU 추론 엔진"""
    
    def __init__(
        self,
        model_path: str,
        device: str = 'NPU',
        auto_fallback: bool = True
    ):
        """
        Args:
            model_path: Path to .xml file (e.g., 'models/openvino_ir/best_model_kr.xml')
            device: 'NPU' | 'CPU' | 'GPU' (primary device)
            auto_fallback: Fallback to CPU if device unavailable
        """
        self.model_path = model_path
        self.primary_device = device
        self.auto_fallback = auto_fallback
        self.current_device = None
        self.model = None
        self.compiled_model = None
        self.infer_request = None
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize OpenVINO runtime and load model"""
        try:
            core = Core()
            logger.info(f"OpenVINO version: {get_version()}")
            
            # Read model
            self.model = core.read_model(self.model_path)
            logger.info(f"Model loaded: {self.model_path}")
            
            # Compile with primary device
            devices = core.available_devices
            logger.info(f"Available devices: {devices}")
            
            if self.primary_device in devices:
                self.compiled_model = core.compile_model(
                    self.model, 
                    self.primary_device
                )
                self.current_device = self.primary_device
                logger.info(f"✓ Model compiled for {self.primary_device}")
            elif self.auto_fallback and 'CPU' in devices:
                logger.warning(f"Device {self.primary_device} not available, falling back to CPU")
                self.compiled_model = core.compile_model(self.model, 'CPU')
                self.current_device = 'CPU'
            else:
                raise RuntimeError(f"No suitable device found. Available: {devices}")
            
            # Create infer request
            self.infer_request = self.compiled_model.create_infer_request()
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    def predict(self, features: np.ndarray) -> InferenceResult:
        """
        Single prediction
        
        Args:
            features: (45,) normalized array
        
        Returns:
            InferenceResult
        """
        start_time = time.time()
        
        try:
            # Prepare input
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            input_name = self.model.inputs[0].any_name
            input_tensor = ov.Tensor(
                features.astype('float32'),
                ov.Type.f32
            )
            
            # Inference
            self.infer_request.set_input_tensor(input_tensor)
            self.infer_request.infer()
            
            # Extract output
            output_name = self.model.outputs[0].any_name
            output_tensor = self.infer_request.get_output_tensor(output_name)
            prediction = float(output_tensor.data[0, 0])
            
            latency_ms = (time.time() - start_time) * 1000
            
            return InferenceResult(
                predicted_price=prediction,
                confidence=0.95,  # Mock (can enhance with uncertainty quantification)
                latency_ms=latency_ms,
                device=self.current_device,
                timestamp=datetime.now().isoformat()
            )
        
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def batch_predict(
        self, 
        features: np.ndarray,
        batch_size: int = 32
    ) -> List[InferenceResult]:
        """
        Batch prediction (memory-efficient)
        
        Args:
            features: (N, 45) array
            batch_size: Process in chunks to avoid memory overflow
        
        Returns:
            List[InferenceResult]
        """
        results = []
        for i in range(0, len(features), batch_size):
            batch = features[i:i+batch_size]
            for j in range(batch.shape[0]):
                results.append(self.predict(batch[j]))
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get device performance metrics"""
        return {
            'device': self.current_device,
            'model_path': self.model_path,
            'num_inputs': len(self.model.inputs),
            'num_outputs': len(self.model.outputs),
            'num_parameters': sum(
                np.prod(output.shape) 
                for output in self.model.outputs
            ),
        }
```

### 2.2 성능 특성 명세

```
Device Performance Specification:

┌─────────────────────────────────────────────────┐
│ NPU (Intel Integrated)                          │
├─────────────────────────────────────────────────┤
│ Latency (p50):      6.5ms                       │
│ Latency (p99):     12.0ms                       │
│ Throughput:    >1000 req/min                    │
│ Memory:          <500 MB                        │
│ Power:             ~5 W                         │
│ Price:            Integrated (free)            │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ GPU (RTX 5050, fallback)                        │
├─────────────────────────────────────────────────┤
│ Latency (p50):      1.5ms                       │
│ Latency (p99):      3.0ms                       │
│ Throughput:   10,000 req/min                    │
│ Memory:         4,000 MB                        │
│ Power:           100 W                          │
│ Price:        $500/unit                         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ CPU (Intel Core i7, fallback)                   │
├─────────────────────────────────────────────────┤
│ Latency (p50):     45ms                         │
│ Latency (p99):    120ms                         │
│ Throughput:     200 req/min                     │
│ Memory:        2,000 MB                         │
│ Power:           20 W                           │
│ Price:        Integrated                        │
└─────────────────────────────────────────────────┘
```

---

## 3. REST API 명세

### 3.1 FastAPI 애플리케이션

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import logging

app = FastAPI(
    title="Loan4U AVM API",
    version="1.0.0",
    description="Property valuation API using NPU-optimized ML model"
)

# Request/Response Models
class PropertyValuationRequest(BaseModel):
    """Property valuation request"""
    area_sqm: float = Field(..., ge=20, le=500, description="Area in square meters")
    old_price: int = Field(..., ge=1000000, description="Old price in KRW")
    latitude: float = Field(..., ge=37.0, le=38.0, description="Latitude (Seoul area)")
    longitude: float = Field(..., ge=126.5, le=127.5, description="Longitude (Seoul area)")
    building_age: int = Field(..., ge=0, le=100, description="Building age in years")
    floor: int = Field(..., ge=1, le=50, description="Floor number")
    distance_subway: int = Field(..., ge=0, le=5000, description="Distance to subway (m)")
    distance_school: int = Field(..., ge=0, le=5000, description="Distance to school (m)")
    distance_park: int = Field(..., ge=0, le=5000, description="Distance to park (m)")
    property_type: int = Field(default=0, ge=0, le=2, description="Type: 0=apt, 1=house, 2=villa")

class PropertyValuationResponse(BaseModel):
    """Property valuation response"""
    predicted_price: int = Field(..., description="Predicted price in KRW")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    latency_ms: float = Field(..., description="Inference latency in milliseconds")
    device: str = Field(..., description="Device used (NPU/GPU/CPU)")
    timestamp: str = Field(..., description="Response timestamp (ISO 8601)")

# API Endpoints
@app.post("/api/valuation", response_model=PropertyValuationResponse)
async def valuate_property(
    request: PropertyValuationRequest,
    background_tasks: BackgroundTasks
) -> PropertyValuationResponse:
    """
    Valuate property using NPU-optimized model
    
    Performance:
    - Latency: <10ms (p99)
    - Throughput: >1000 req/min
    - Accuracy: R² > 0.85
    """
    try:
        # Feature engineering
        features_45 = feature_engineering_pipeline.transform(request)
        
        # Inference
        result = npu_engine.predict(features_45)
        
        # Background logging
        background_tasks.add_task(log_valuation_request, request, result)
        
        return PropertyValuationResponse(
            predicted_price=int(result.predicted_price),
            confidence=result.confidence,
            latency_ms=result.latency_ms,
            device=result.device,
            timestamp=result.timestamp
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Valuation failed: {e}")
        raise HTTPException(status_code=500, detail="Valuation failed")

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "device": npu_engine.current_device,
        "model_loaded": npu_engine.model is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/performance")
async def performance_metrics() -> Dict[str, Any]:
    """Get device performance metrics"""
    return npu_engine.get_performance_stats()
```

### 3.2 배포 환경

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install OpenVINO dependencies
RUN apt-get update && apt-get install -y \
    libopenvino-dev \
    libopenvino-c-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy application
COPY avm_project/ ./avm_project/

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "avm_project.scripts.phase13_api_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.3 배포 및 모니터링

```yaml
# docker-compose.yml
version: '3.8'

services:
  npu-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEVICE=NPU
      - AUTO_FALLBACK=true
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models:ro
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

---

## 4. 모니터링 및 로깅

### 4.1 메트릭 수집

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
request_count = Counter(
    'avm_requests_total',
    'Total valuation requests',
    ['device', 'status']
)

request_latency = Histogram(
    'avm_request_latency_ms',
    'Request latency in milliseconds',
    ['device'],
    buckets=[1, 5, 10, 20, 50, 100, 200]
)

device_usage = Gauge(
    'avm_device_usage',
    'Current device usage (0=CPU, 1=GPU, 2=NPU)',
)

model_accuracy = Gauge(
    'avm_model_accuracy',
    'Model accuracy (R² score)',
)
```

### 4.2 로깅

```python
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)

# JSON structured logging
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)

# Usage
logger.info("Valuation request", extra={
    'device': 'NPU',
    'latency_ms': 8.5,
    'model': 'lightgbm_kr',
    'status': 'success'
})
```

---

## 5. 의존성

```python
# requirements-api.txt
fastapi==0.136.3
uvicorn==0.32.1
pydantic==2.9.0
numpy==1.26.0
openvino==2024.1.0
prometheus-client==0.21.0
python-json-logger==2.0.7
python-dotenv==1.0.1
```

---

**기술 명세서 완성**  
**다음 문서**: Phase 13.4 WBS (Work Breakdown Structure)
