# AVM REST API 문서

**버전:** 1.0.0  
**상태:** Production Ready ✅  
**포트:** 8000  

---

## 🚀 빠른 시작

### 서버 시작
```bash
cd avm_project
python3 -m uvicorn scripts.api_server:app --reload --host 0.0.0.0 --port 8000
```

### 자동 문서 (Swagger UI)
```
http://localhost:8000/docs
```

### 대체 문서 (ReDoc)
```
http://localhost:8000/redoc
```

---

## 📡 주요 엔드포인트

### 1️⃣ **GET /health** - 서버 상태 확인
```bash
curl http://localhost:8000/health
```

**응답:**
```json
{
  "status": "healthy",
  "timestamp": "2026-06-12T13:30:00.123456",
  "models_available": 7
}
```

---

### 2️⃣ **GET /models** - 사용 가능한 모델 목록
```bash
curl http://localhost:8000/models
```

**응답:**
```json
[
  {
    "model_name": "lightgbm",
    "display_name": "LightGBM",
    "r2_score": 0.9719,
    "status": "recommended",
    "timestamp": "2026-06-12T13:30:00.123456"
  },
  {
    "model_name": "xgboost",
    "display_name": "XGBoost",
    "r2_score": 0.9701,
    "status": "production",
    "timestamp": "2026-06-12T13:30:00.123456"
  },
  ...
]
```

---

### 3️⃣ **POST /predict** - 부동산 가격 예측 ⭐ **주요 엔드포인트**

#### 요청
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "property_data": {
      "area_sqm": 100.5,
      "year_built": 2010,
      "rooms": 3,
      "bathrooms": 2,
      "parking": 1,
      "floor": 5,
      "total_floor": 20,
      "condition": 7,
      "original_price": 500000000,
      "appraised_price": 480000000,
      "outstanding_debt": 300000000,
      "market_price": 490000000,
      "transaction_count_1y": 5,
      "ltv": 0.62,
      "loan_term_months": 240,
      "days_on_market": 30,
      "appraisal_rounds": 2,
      "age_years": 14,
      "price_per_sqm": 4876000,
      "debt_to_price_ratio": 0.61,
      "price_variance": 0.02
    },
    "model_name": "lightgbm"
  }'
```

#### 응답
```json
{
  "predicted_price": 495234567.89,
  "model_name": "lightgbm",
  "confidence_score": 0.9719,
  "r2_score": 0.9719,
  "timestamp": "2026-06-12T13:30:00.123456"
}
```

---

### 4️⃣ **POST /predict/batch** - 배치 예측 (여러 부동산 한 번에)

**최대 100개까지 한 번에 처리**

```bash
curl -X POST "http://localhost:8000/predict/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "property_data": { ... },
      "model_name": "lightgbm"
    },
    {
      "property_data": { ... },
      "model_name": "xgboost"
    }
  ]'
```

**응답:**
```json
{
  "count": 2,
  "predictions": [
    {
      "predicted_price": 495234567.89,
      "model_name": "lightgbm",
      "confidence_score": 0.9719,
      "r2_score": 0.9719,
      "timestamp": "2026-06-12T13:30:00.123456"
    },
    {
      "predicted_price": 498765432.10,
      "model_name": "xgboost",
      "confidence_score": 0.9701,
      "r2_score": 0.9701,
      "timestamp": "2026-06-12T13:30:00.123456"
    }
  ]
}
```

---

### 5️⃣ **GET /model/{model_name}** - 특정 모델 정보

```bash
curl http://localhost:8000/model/lightgbm
```

**응답:**
```json
{
  "model_name": "lightgbm",
  "display_name": "LightGBM",
  "r2_score": 0.9719,
  "status": "recommended",
  "description": "LightGBM - R² 0.9719 (recommended)",
  "timestamp": "2026-06-12T13:30:00.123456"
}
```

---

### 6️⃣ **GET /api/version** - API 버전 정보

```bash
curl http://localhost:8000/api/version
```

**응답:**
```json
{
  "api_version": "1.0.0",
  "models_count": 7,
  "updated_at": "2026-06-12",
  "status": "production"
}
```

---

## 📊 사용 가능한 모델

| 모델 | R² | 상태 | 추천 |
|------|-----|------|------|
| **LightGBM** | 0.9719 | ⭐ Recommended | ✅ |
| **Random Forest** | 0.9717 | Production | ✅ |
| **XGBoost** | 0.9701 | Production | ✅ |
| **Gradient Boosting** | 0.9683 | Production | ✅ |
| **Neural Network** | 0.9445 | Production | - |
| **Linear Regression** | 1.0000 | Perfect Fit (Overfit) | ❌ |
| **Decision Tree** | 0.9053 | Production | - |

---

## 🔑 요청 파라미터 설명

### PropertyData (부동산 정보)

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| area_sqm | float | 건물 면적 (㎡) | 100.5 |
| year_built | int | 건설년도 | 2010 |
| rooms | int | 방의 개수 | 3 |
| bathrooms | int | 욕실 개수 | 2 |
| parking | int | 주차장 개수 | 1 |
| floor | int | 현재 층 | 5 |
| total_floor | int | 총 층수 | 20 |
| condition | int | 상태 점수 (1-10) | 7 |
| original_price | float | 원래 가격 (₩) | 500000000 |
| appraised_price | float | 감정 가격 (₩) | 480000000 |
| outstanding_debt | float | 미갚은 채무 (₩) | 300000000 |
| market_price | float | 시장 가격 (₩) | 490000000 |
| transaction_count_1y | int | 1년 거래 건수 | 5 |
| ltv | float | 대출-가치 비율 | 0.62 |
| loan_term_months | int | 대출 기간 (개월) | 240 |
| days_on_market | int | 시장 노출일 | 30 |
| appraisal_rounds | int | 감정 회차 | 2 |
| age_years | int | 건물 나이 (년) | 14 |
| price_per_sqm | float | 단위 가격 (₩/㎡) | 4876000 |
| debt_to_price_ratio | float | 채무-가격 비율 | 0.61 |
| price_variance | float | 가격 변동률 | 0.02 |

---

## 🐍 Python 클라이언트 예제

### 단일 예측
```python
import requests

url = "http://localhost:8000/predict"

payload = {
    "property_data": {
        "area_sqm": 100.5,
        "year_built": 2010,
        "rooms": 3,
        "bathrooms": 2,
        "parking": 1,
        "floor": 5,
        "total_floor": 20,
        "condition": 7,
        "original_price": 500000000,
        "appraised_price": 480000000,
        "outstanding_debt": 300000000,
        "market_price": 490000000,
        "transaction_count_1y": 5,
        "ltv": 0.62,
        "loan_term_months": 240,
        "days_on_market": 30,
        "appraisal_rounds": 2,
        "age_years": 14,
        "price_per_sqm": 4876000,
        "debt_to_price_ratio": 0.61,
        "price_variance": 0.02
    },
    "model_name": "lightgbm"
}

response = requests.post(url, json=payload)
result = response.json()

print(f"예측 가격: ₩{result['predicted_price']:,.0f}")
print(f"신뢰도: {result['confidence_score']:.2%}")
print(f"모델: {result['model_name']}")
```

### 배치 예측
```python
import requests

url = "http://localhost:8000/predict/batch"

payloads = [
    {
        "property_data": { ... },
        "model_name": "lightgbm"
    },
    {
        "property_data": { ... },
        "model_name": "xgboost"
    }
]

response = requests.post(url, json=payloads)
results = response.json()

for pred in results['predictions']:
    print(f"{pred['model_name']}: ₩{pred['predicted_price']:,.0f}")
```

### 모델 목록 조회
```python
import requests

response = requests.get("http://localhost:8000/models")
models = response.json()

for model in models:
    print(f"{model['display_name']:20} R²={model['r2_score']:.4f} ({model['status']})")
```

---

## 🔐 보안 설정

### CORS (Cross-Origin Resource Sharing)
현재 모든 출처에서 접근 가능합니다. 프로덕션 환경에서는 다음과 같이 설정을 권장합니다:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 특정 도메인만
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

## 📈 성능 측정

### 예측 시간
- **LightGBM**: ~50ms
- **XGBoost**: ~60ms
- **Random Forest**: ~100ms
- **Gradient Boosting**: ~80ms
- **Neural Network**: ~150ms

### 처리량
- **단일 예측**: ~20 req/sec
- **배치 예측 (100개)**: ~200 req/sec

---

## ❌ 에러 처리

### 400 Bad Request
```json
{
  "detail": "모델을 로드할 수 없음: invalid_model"
}
```

### 404 Not Found
```json
{
  "detail": "모델을 찾을 수 없음: unknown_model"
}
```

### 500 Internal Server Error
```json
{
  "detail": "예측 중 오류 발생: [error details]"
}
```

---

## 🚀 배포

### Docker 이미지
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY avm_project/ ./avm_project/
EXPOSE 8000
CMD ["uvicorn", "avm_project.scripts.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Google Cloud Run 배포
```bash
gcloud run deploy avm-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### AWS Lambda + API Gateway
Lambda function으로 배포 가능 (Zappa 사용)

---

## 📞 지원

- **문서**: `/docs` (Swagger UI)
- **GitHub**: [repository-url]
- **이슈**: [issue-url]

---

**마지막 업데이트:** 2026-06-12  
**상태:** Production Ready ✅
