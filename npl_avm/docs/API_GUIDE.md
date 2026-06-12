# NPL AVM API 사용 가이드

**API 버전**: 1.0.0  
**기준일**: 2026-06-09

---

## 📖 목차

1. [개요](#개요)
2. [인증](#인증)
3. [기본 사용법](#기본-사용법)
4. [엔드포인트](#엔드포인트)
5. [예제](#예제)
6. [에러 처리](#에러-처리)
7. [FAQ](#faq)

---

## 개요

### NPL AVM API란?

NPL AVM (Non-Performing Loans Automated Valuation Model) API는 부동산 물건의 감정가를 자동으로 추정하는 REST API입니다.

**주요 기능**:
- ✅ 단일 물건 감정가 추정 (< 2초)
- ✅ 배치 감정 (최대 1,000건)
- ✅ 비교사례 자동 매칭
- ✅ 실시간 모델 성능 조회

### API 엔드포인트

```
프로덕션: https://api.npl-avm.example.com/api/v1
스테이징: https://staging-api.npl-avm.example.com/api/v1
로컬:    http://localhost:8000/api/v1
```

### SLA

```
p95 응답시간: < 500ms
가용성:      99.9% (월간)
모델 정확도:  R² ≥ 0.85
```

---

## 인증

### API 키 발급

1. NPL AVM 포털 로그인
2. "API 관리" → "새 API 키 발급"
3. API 키 복사

### 요청 헤더

모든 요청에 API 키를 포함해야 합니다:

```http
GET /api/v1/estimate HTTP/1.1
Host: api.npl-avm.example.com
X-API-Key: sk_prod_abc123xyz789
Content-Type: application/json
```

### 보안 주의사항

⚠️ **API 키 관리**:
- 절대 공개 저장소에 커밋하지 마세요
- 환경 변수 또는 보안 볼트에 저장하세요
- 정기적으로 키 회전하세요 (월 1회 권장)
- 노출된 키는 즉시 비활성화하세요

```bash
# ✅ 올바른 방법
export NPL_API_KEY="sk_prod_abc123xyz789"

# ❌ 잘못된 방법
api_key = "sk_prod_abc123xyz789"  # 코드에 하드코딩
```

---

## 기본 사용법

### 1. 라이브러리 설치

**Python**:
```bash
pip install requests
```

**Node.js**:
```bash
npm install axios
```

**cURL**:
```bash
# macOS/Linux에 기본 설치
# Windows: https://curl.se/download.html
```

### 2. 요청 형식

```json
{
  "land_area_sqm": 125.5,
  "building_area_sqm": 95.3,
  "building_age": 5,
  "floor_number": 15,
  "property_type": "아파트",
  "location_sido": "서울",
  "location_sigungu": "강남구"
}
```

### 3. 응답 형식

```json
{
  "estimated_price": 850000000,
  "price_per_sqm": 8921053,
  "confidence_score": 0.87,
  "confidence_interval": {
    "lower_bound": 765000000,
    "upper_bound": 935000000
  },
  "comparable_properties": [
    {
      "id": "prop_001",
      "address": "서울 강남구 테헤란로 123",
      "price": 820000000,
      "price_per_sqm": 8600000,
      "similarity_score": 0.92,
      "transaction_date": "2026-03-15"
    }
  ],
  "model_metadata": {
    "model_name": "XGBoost (Tuned)",
    "r2_score": 0.8721,
    "prediction_time_ms": 45
  }
}
```

---

## 엔드포인트

### 시스템

#### GET /health

서버 가용성 확인

**요청**:
```bash
curl -X GET https://api.npl-avm.example.com/api/v1/health
```

**응답** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-06-09T10:30:00Z",
  "version": "1.0.0"
}
```

---

#### GET /ready

모델과 데이터 로드 확인

**요청**:
```bash
curl -X GET https://api.npl-avm.example.com/api/v1/ready
```

**응답** (200 OK):
```json
{
  "ready": true,
  "checks": {
    "model_loaded": true,
    "database_connected": true,
    "external_api_reachable": true
  }
}
```

---

### 감정

#### POST /estimate

단일 물건 감정가 추정

**요청**:
```bash
curl -X POST https://api.npl-avm.example.com/api/v1/estimate \
  -H "X-API-Key: sk_prod_abc123xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "land_area_sqm": 125.5,
    "building_area_sqm": 95.3,
    "building_age": 5,
    "floor_number": 15,
    "property_type": "아파트",
    "location_sido": "서울",
    "location_sigungu": "강남구"
  }'
```

**응답** (200 OK): [위의 응답 형식 참고]

**응답 시간**: < 2초

---

#### POST /batch-estimate

배치 감정 (최대 1,000건)

**요청**:
```bash
curl -X POST https://api.npl-avm.example.com/api/v1/batch-estimate \
  -H "X-API-Key: sk_prod_abc123xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": [
      {
        "land_area_sqm": 125.5,
        "building_area_sqm": 95.3,
        "building_age": 5,
        "property_type": "아파트",
        "location_sido": "서울"
      },
      {
        "land_area_sqm": 250.0,
        "building_area_sqm": 180.0,
        "building_age": 10,
        "property_type": "주택",
        "location_sido": "경기"
      }
    ]
  }'
```

**응답** (202 Accepted):
```json
{
  "job_id": "job_abc123",
  "status": "processing",
  "created_at": "2026-06-09T10:30:00Z",
  "estimated_completion_time": "2026-06-09T10:32:00Z"
}
```

**처리 시간**: 100건 기준 약 2분

---

#### GET /batch-estimate/{job_id}

배치 결과 조회

**요청**:
```bash
curl -X GET https://api.npl-avm.example.com/api/v1/batch-estimate/job_abc123 \
  -H "X-API-Key: sk_prod_abc123xyz789"
```

**응답** (200 OK):
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "progress": 100,
  "results": [
    {
      "estimated_price": 850000000,
      "confidence_score": 0.87,
      ...
    },
    ...
  ]
}
```

---

#### POST /compare

비교사례 조회

**요청**:
```bash
curl -X POST https://api.npl-avm.example.com/api/v1/compare \
  -H "X-API-Key: sk_prod_abc123xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "prop_001",
    "count": 5,
    "date_range": {
      "from": "2025-06-09",
      "to": "2026-06-09"
    }
  }'
```

**응답** (200 OK):
```json
{
  "property_id": "prop_001",
  "comparable_properties": [
    {
      "id": "prop_002",
      "address": "서울 강남구 테헤란로 456",
      "price": 820000000,
      "similarity_score": 0.92,
      ...
    },
    ...
  ]
}
```

---

### 모니터링

#### GET /metrics

모델 성능 지표

**요청**:
```bash
curl -X GET https://api.npl-avm.example.com/api/v1/metrics \
  -H "X-API-Key: sk_prod_abc123xyz789"
```

**응답** (200 OK):
```json
{
  "model_name": "XGBoost (Tuned)",
  "r2_score": 0.8721,
  "rmse": 446812893,
  "mae": 226196156,
  "mape": 19.56,
  "sample_count": 248,
  "created_at": "2026-06-09T00:00:00Z",
  "last_updated": "2026-06-09T10:30:00Z"
}
```

---

#### GET /models

배포된 모델 목록

**요청**:
```bash
curl -X GET https://api.npl-avm.example.com/api/v1/models \
  -H "X-API-Key: sk_prod_abc123xyz789"
```

**응답** (200 OK):
```json
{
  "current_model": "advanced_best",
  "models": [
    {
      "id": "advanced_best",
      "name": "XGBoost (Tuned)",
      "r2_score": 0.8721,
      "status": "active",
      "created_at": "2026-06-09T00:00:00Z"
    },
    {
      "id": "baseline_best",
      "name": "Random Forest",
      "r2_score": 0.7231,
      "status": "available",
      "created_at": "2026-06-08T00:00:00Z"
    }
  ]
}
```

---

## 예제

### Python 예제

```python
import requests
import os

API_KEY = os.getenv('NPL_API_KEY')
API_BASE = 'https://api.npl-avm.example.com/api/v1'

def estimate_property(property_data):
    """단일 물건 감정가 추정"""
    headers = {'X-API-Key': API_KEY}
    
    response = requests.post(
        f'{API_BASE}/estimate',
        json=property_data,
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

# 사용 예
property_info = {
    'land_area_sqm': 125.5,
    'building_area_sqm': 95.3,
    'building_age': 5,
    'property_type': '아파트',
    'location_sido': '서울',
    'location_sigungu': '강남구'
}

result = estimate_property(property_info)
print(f"추정 감정가: ₩{result['estimated_price']:,}")
print(f"신뢰도: {result['confidence_score']:.1%}")
```

### Node.js 예제

```javascript
const axios = require('axios');

const API_KEY = process.env.NPL_API_KEY;
const API_BASE = 'https://api.npl-avm.example.com/api/v1';

async function estimateProperty(propertyData) {
  try {
    const response = await axios.post(
      `${API_BASE}/estimate`,
      propertyData,
      {
        headers: { 'X-API-Key': API_KEY }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error:', error.response.data);
    throw error;
  }
}

// 사용 예
const propertyInfo = {
  land_area_sqm: 125.5,
  building_area_sqm: 95.3,
  building_age: 5,
  property_type: '아파트',
  location_sido: '서울',
  location_sigungu: '강남구'
};

estimateProperty(propertyInfo).then(result => {
  console.log(`추정 감정가: ₩${result.estimated_price.toLocaleString()}`);
  console.log(`신뢰도: ${(result.confidence_score * 100).toFixed(1)}%`);
});
```

### cURL 예제

```bash
# 환경 변수에서 API 키 로드
API_KEY=$NPL_API_KEY

# 단일 감정가 추정
curl -X POST https://api.npl-avm.example.com/api/v1/estimate \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "land_area_sqm": 125.5,
    "building_area_sqm": 95.3,
    "building_age": 5,
    "floor_number": 15,
    "property_type": "아파트",
    "location_sido": "서울",
    "location_sigungu": "강남구"
  }' | jq '.'
```

---

## 에러 처리

### 에러 응답 형식

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "필수 필드가 누락되었습니다",
  "details": [
    {
      "field": "land_area_sqm",
      "issue": "값이 필수입니다"
    }
  ]
}
```

### HTTP 상태 코드

| 코드 | 설명 | 원인 |
|------|------|------|
| 200 | OK | 요청 성공 |
| 202 | Accepted | 배치 처리 수락 |
| 400 | Bad Request | 요청 형식 오류 |
| 401 | Unauthorized | API 키 오류 |
| 404 | Not Found | 리소스 없음 |
| 429 | Too Many Requests | 요청 제한 초과 |
| 500 | Internal Server Error | 서버 오류 |
| 503 | Service Unavailable | 서비스 사용 불가 |

### 에러 처리 예제

```python
try:
    result = estimate_property(property_data)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        print("API 키가 유효하지 않습니다")
    elif e.response.status_code == 429:
        retry_after = e.response.headers.get('Retry-After', 60)
        print(f"{retry_after}초 후 재시도하세요")
    else:
        print(f"에러: {e.response.json()}")
except requests.exceptions.RequestException as e:
    print(f"네트워크 오류: {e}")
```

---

## FAQ

### Q1: 응답 시간이 500ms보다 깁니다. 어떻게 해야 하나요?

**A:** 일반적으로 p95 응답시간은 45ms입니다. 느린 경우:
1. 네트워크 연결 확인
2. API 서버 상태 확인: `/health` 엔드포인트
3. 모델 로드 확인: `/ready` 엔드포인트
4. 지역 캐시 서버 확인

---

### Q2: 배치 처리에서 일부만 실패했습니다.

**A:** 배치 처리는 부분 실패를 지원합니다. 결과에서:
```json
{
  "status": "partial_success",
  "successful_count": 95,
  "failed_count": 5,
  "errors": [
    {
      "index": 3,
      "error": "Invalid property_type"
    }
  ]
}
```

---

### Q3: API 키 갱신 주기는?

**A:** 보안상 월 1회 갱신 권장:
1. 새 API 키 발급
2. 기존 키로 서비스 유지
3. 코드 및 환경 변수 업데이트
4. 기존 키 비활성화

---

### Q4: 오프라인 모드는 지원하나요?

**A:** 아니요. API는 온라인 전용입니다. 로컬 배포를 위해서는 자체 서버를 구성해야 합니다.

---

### Q5: 어떤 부동산 유형이 지원되나요?

**A:** 현재 지원:
- ✅ 아파트
- ✅ 주택
- ✅ 오피스
- ✅ 상업
- ✅ 공업
- ✅ 토지

(향후 추가: 호텔, 병원 등)

---

## 문의

**문제 발생 시**:
- 📧 이메일: support@npl-avm.example.com
- 💬 Slack: #npl-avm-support
- 📞 전화: 1588-****

---

**최종 업데이트**: 2026-06-09  
**API 버전**: 1.0.0
