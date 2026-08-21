# AVM 프로젝트 - 중대 결함 시정 계획

**작성일:** 2026-06-15  
**검토 기준:** 100% 무결점 개발 완료  
**중대 결함:** 8개 (CRITICAL)  
**우선순위 높음:** 6개 (HIGH)  
**추정 시정 시간:** 35-50시간

---

## 1. CRITICAL SECURITY ISSUES (즉시 시정 필요)

### 1.1 API 키 노출 - CRITICAL
**현황:** API 키가 소스 코드에 평문 저장됨  
**파일:** download_data.py:16-17, test_api_collection.py  
**위험:** Git 히스토리에 영구 저장, Docker 이미지에 포함, 무단 API 사용 가능  

**시정 방법:**

#### Step 1: .env 파일 생성 및 구성
```bash
# .env 생성
cat > .env << 'EOF'
DATAGOVKR_API_KEY="your_actual_api_key_here"
VWORLD_API_KEY="your_actual_vworld_key_here"
AVM_DATA_PATH="/mnt/avm_data"
API_HOST="0.0.0.0"
API_PORT="8000"
LOG_LEVEL="INFO"
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080"
EOF

# .gitignore에 추가
echo ".env
.env.local
*.pkl
models/**
data/raw/**
data/processed/**
logs/**" >> .gitignore
```

#### Step 2: 모든 스크립트 수정
```python
# download_data.py, debug_data.py 등 모두 수정
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# 이전: DATAGOVKR_API_KEY = '9+Sz4Yn+...'  ❌
# 변경:
DATAGOVKR_API_KEY = os.getenv('DATAGOVKR_API_KEY')
VWORLD_API_KEY = os.getenv('VWORLD_API_KEY')

if not DATAGOVKR_API_KEY:
    raise ValueError("DATAGOVKR_API_KEY not configured in environment")
if not VWORLD_API_KEY:
    raise ValueError("VWORLD_API_KEY not configured in environment")

D_DRIVE_PATH = os.getenv('AVM_DATA_PATH', '/mnt/avm_data')
```

#### Step 3: 기존 API 키 순환 (회전)
```bash
# Data.go.kr 포털에서 새로운 API 키 발급
# Vworld에서 새로운 API 키 발급
# .env 파일에만 새로운 키 저장
# 기존 키는 포털에서 비활성화
```

#### Step 4: Git 히스토리 정제
```bash
# 기존 커밋에서 API 키 제거
git-filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch avm_project/scripts/download_data.py" \
  --prune-empty --tag-name-filter cat -- --all

# 또는 git-secrets 설치 후 스캔
npm install -g git-secrets
git-secrets --install
git-secrets --register-aws  # AWS 패턴 추가
```

**완성도:** ✅ 완료 기준
- [ ] .env 파일 생성 및 모든 API 키 이동
- [ ] 모든 스크립트 (6개) 수정 완료
- [ ] .gitignore 업데이트
- [ ] 기존 API 키 순환 (회전)
- [ ] Git 히스토리 정제
- [ ] CI/CD에 .env 시크릿 추가 (GitHub Secrets)

**시정 시간:** 2-3시간

---

### 1.2 CORS 보안 설정 오류 - CRITICAL
**현황:** CORS 정책이 모든 출처를 허용 (`allow_origins=["*"]`)  
**파일:** api_server.py:35-41  
**위험:** CSRF 공격, 자격증명 탈취, 무단 API 접근  

**시정 방법:**

```python
# api_server.py 수정
import os
from fastapi.middleware.cors import CORSMiddleware

# 환경변수에서 허용 출처 읽기
ALLOWED_ORIGINS = os.getenv(
    'ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8080'
).split(',')

# 이전 (❌ 위험):
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 모든 출처 허용
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# 변경 (✅ 안전):
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=False,  # 필요한 경우만 True
    allow_methods=["GET", "POST"],  # 필요한 메서드만
    allow_headers=["Content-Type", "Authorization"],  # 필요한 헤더만
    max_age=600,  # 프리플라이트 캐시 10분
)
```

**완성도:** ✅ 완료 기준
- [ ] CORS 설정 제한 (특정 도메인만)
- [ ] 불필요한 메서드 제거 (GET, POST만)
- [ ] 불필요한 헤더 제거
- [ ] 환경변수로 동적 설정 가능하게 변경
- [ ] 테스트: OPTIONS 요청 Origin 검증

**시정 시간:** 1시간

---

### 1.3 입력 검증 부재 - CRITICAL
**현황:** PropertyData 모델에 제약 없음  
**파일:** api_server.py (Pydantic 모델)  
**위험:** 비논리적 입력 (year_built=5000, area=-100) 허용 → 쓰레기 예측  

**시정 방법:**

```python
# schemas.py 또는 api_server.py에 추가
from pydantic import BaseModel, Field, validator
from typing import Optional

class PropertyData(BaseModel):
    """부동산 데이터 - 엄격한 검증 포함"""
    
    # 물리적 특성
    area_sqm: float = Field(
        ...,
        gt=0,
        le=1000,
        description="건물 면적 (m²), 10-1000 범위"
    )
    year_built: int = Field(
        ...,
        ge=1900,
        le=2026,
        description="건축년도, 1900-2026 범위"
    )
    rooms: int = Field(..., ge=0, le=20, description="방 개수")
    bathrooms: int = Field(..., ge=0, le=10, description="욕실 개수")
    parking: int = Field(..., ge=0, le=10, description="주차 공간")
    floor: int = Field(..., ge=0, le=100, description="현재 층수")
    total_floor: int = Field(..., ge=1, le=100, description="총 층수")
    condition: int = Field(..., ge=1, le=10, description="건물 상태 (1-10)")
    
    # 가격 정보
    original_price: float = Field(..., gt=0, description="원래 가격 (만원)")
    appraised_price: float = Field(..., gt=0, description="감정가 (만원)")
    outstanding_debt: float = Field(..., ge=0, description="미상환 채무 (만원)")
    market_price: float = Field(..., gt=0, description="시장 가격 (만원)")
    
    # 거래 정보
    transaction_count_1y: int = Field(
        ...,
        ge=0,
        le=500,
        description="1년 내 거래 횟수"
    )
    ltv: float = Field(..., ge=0, le=2, description="LTV (부채/자산 비율)")
    loan_term_months: int = Field(..., ge=1, le=600, description="대출 기간 (개월)")
    days_on_market: int = Field(..., ge=0, le=3650, description="시장 노출 일수 (0-10년)")
    appraisal_rounds: int = Field(..., ge=1, le=10, description="감정 횟수")
    
    # 파생 특성
    age_years: int = Field(..., ge=0, le=150, description="건물 경과 연수")
    price_per_sqm: float = Field(..., gt=0, description="m²당 가격")
    debt_to_price_ratio: float = Field(..., ge=0, le=2, description="채무/가격 비율")
    price_variance: float = Field(..., ge=0, le=1, description="가격 변동성")
    
    # 경제 지표
    market_trend: float = Field(..., ge=-1, le=1, description="시장 추세 (-1~1)")
    interest_rate: float = Field(..., ge=0, le=0.2, description="이자율 (0-20%)")
    
    @validator('year_built')
    def validate_year_built(cls, v):
        from datetime import datetime
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f'건축년도는 현재보다 미래일 수 없습니다: {v}')
        if current_year - v > 100:
            raise ValueError(f'건축년도가 너무 오래됨: {v} (100년 이상)')
        return v
    
    @validator('area_sqm')
    def validate_area(cls, v):
        if v < 10:
            raise ValueError('면적은 최소 10m² 이상이어야 합니다')
        if v > 500:
            raise ValueError('면적이 일반적인 범위를 초과합니다 (> 500m²)')
        return v
    
    @validator('appraised_price', 'original_price', 'market_price', always=True)
    def validate_prices_reasonable(cls, v, values):
        if v < 100:  # 1000만원 미만
            raise ValueError('가격이 너무 낮습니다 (최소 1000만원)')
        if v > 100000:  # 10억원 이상
            raise ValueError('가격이 너무 높습니다 (최대 10억원)')
        return v
    
    @validator('debt_to_price_ratio')
    def validate_debt_ratio(cls, v):
        if v > 2:
            raise ValueError('채무비율이 비정상입니다 (2.0 초과)')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "area_sqm": 84.5,
                "year_built": 2015,
                "rooms": 3,
                "bathrooms": 2,
                "parking": 1,
                "floor": 5,
                "total_floor": 15,
                "condition": 7,
                "original_price": 450000,
                "appraised_price": 455000,
                "outstanding_debt": 250000,
                "market_price": 460000,
                "transaction_count_1y": 12,
                "ltv": 0.55,
                "loan_term_months": 240,
                "days_on_market": 30,
                "appraisal_rounds": 2,
                "age_years": 11,
                "price_per_sqm": 5326,
                "debt_to_price_ratio": 0.55,
                "price_variance": 0.02,
                "market_trend": 0.05,
                "interest_rate": 0.045
            }
        }
```

**완성도:** ✅ 완료 기준
- [ ] PropertyData 모델 모든 필드에 범위 제약 추가
- [ ] 모든 필드에 설명(description) 추가
- [ ] validator 함수로 논리적 검증 추가
- [ ] 예제(example) 값 추가
- [ ] 테스트: 유효하지 않은 입력 422 오류 확인

**시정 시간:** 2-3시간

---

### 1.4 경로 하드코딩 (Windows 전용) - CRITICAL
**현황:** 모든 스크립트가 `D:\LG_AVM_...` Windows 경로 사용  
**파일:** 모든 .py 스크립트 (6개)  
**위험:** Cloud Run (Linux), CI/CD, 크로스플랫폼 실행 불가  

**시정 방법:**

```python
# 모든 스크립트 상단에 추가 - data_path_config.py 생성
from pathlib import Path
import os
import platform

def get_data_path() -> Path:
    """
    플랫폼 독립적 데이터 경로 반환
    
    우선순위:
    1. 환경변수 AVM_DATA_PATH
    2. Windows: D:\LG_AVM_Workspace_Data_Moved_20260604
    3. Linux/Mac: /mnt/avm_data 또는 ./data
    """
    
    # 1. 환경변수 확인
    env_path = os.getenv('AVM_DATA_PATH')
    if env_path:
        data_path = Path(env_path)
        if data_path.exists():
            return data_path
    
    # 2. 플랫폼별 기본 경로
    if platform.system() == 'Windows':
        default_path = Path(r'D:\LG_AVM_Workspace_Data_Moved_20260604')
    else:  # Linux, macOS
        default_path = Path('/mnt/avm_data')
        if not default_path.exists():
            default_path = Path.home() / 'avm_data'
    
    # 경로가 없으면 생성 시도
    if not default_path.exists():
        try:
            default_path.mkdir(parents=True, exist_ok=True)
            print(f"Created data path: {default_path}")
        except Exception as e:
            raise RuntimeError(f"Cannot create data path {default_path}: {e}")
    
    return default_path

def get_subpath(relative_path: str) -> Path:
    """서브 경로 생성 및 반환"""
    base = get_data_path()
    subpath = base / relative_path
    subpath.mkdir(parents=True, exist_ok=True)
    return subpath

# 사용 예제:
DATA_BASE_PATH = get_data_path()
RAW_DATA_PATH = get_subpath('Raw_Data')
CLEANSED_DATA_PATH = get_subpath('Cleansed_Data')
MODELS_PATH = get_subpath('models')
```

#### 모든 스크립트 수정 (6개):
```python
# download_data.py, migrate_data.py, debug_data.py, index_data.py, cleanse_data.py, api_server.py

# 이전:
# D_DRIVE_PATH = r'D:\LG_AVM_Workspace_Data_Moved_20260604'

# 변경:
from scripts.data_path_config import get_data_path, get_subpath

class DataDownloader:
    def __init__(self):
        self.base_path = get_data_path()
        self.raw_path = get_subpath('Raw_Data')
        # ...
```

**완성도:** ✅ 완료 기준
- [ ] data_path_config.py 생성
- [ ] 모든 스크립트 (6개) 수정
- [ ] Windows 테스트 (D:\... 경로)
- [ ] Linux 테스트 (/mnt/... 경로)
- [ ] Docker 테스트 (컨테이너 내부 경로)
- [ ] CI/CD 테스트 (환경변수 사용)

**시정 시간:** 2-3시간

---

### 1.5 예외 처리 부재 (Bare Exception) - CRITICAL
**현황:** 모든 예외를 `Exception`으로 처리  
**파일:** api_server.py, download_data.py, cleanse_data.py 등  
**위험:** 프로그래밍 오류 은폐, 디버깅 어려움, 의도하지 않은 종료  

**시정 방법:**

```python
# exceptions.py 생성 - 커스텀 예외 클래스
class AVMException(Exception):
    """AVM 프로젝트 기본 예외"""
    pass

class ModelNotFoundError(AVMException):
    """모델을 찾을 수 없을 때"""
    pass

class InvalidInputError(AVMException):
    """유효하지 않은 입력"""
    pass

class PredictionError(AVMException):
    """예측 중 오류"""
    pass

class DataProcessingError(AVMException):
    """데이터 처리 중 오류"""
    pass

# api_server.py 수정
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from exceptions import *
import logging

logger = logging.getLogger(__name__)

@app.post("/predict")
async def predict(request: PredictionRequest):
    try:
        # 입력 검증 (Pydantic이 자동으로 함)
        # 모델 로드
        model = load_model(request.model_name)
        if model is None:
            raise ModelNotFoundError(f"Model not found: {request.model_name}")
        
        # 예측
        X = prepare_features(request.property_data)
        prediction = model.predict(X)
        
        return {
            "predicted_price": float(prediction[0]),
            "model": request.model_name,
            "timestamp": datetime.now().isoformat()
        }
    
    except ModelNotFoundError as e:
        logger.warning(f"Model error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except InvalidInputError as e:
        logger.warning(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except PredictionError as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")
    
    except Exception as e:
        logger.exception(f"Unexpected error in /predict: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

**완성도:** ✅ 완료 기준
- [ ] exceptions.py 생성 (5-10개 커스텀 예외)
- [ ] api_server.py 예외 처리 개선
- [ ] download_data.py 예외 처리 개선
- [ ] cleanse_data.py 예외 처리 개선
- [ ] 모든 스크립트 로깅 일관성 확인

**시정 시간:** 2-3시간

---

### 1.6 단위 테스트 부재 - CRITICAL
**현황:** /tests 폴더는 있으나 모든 테스트 파일 부재 (0% 커버리지)  
**파일:** tests/ (비어있음)  
**위험:** 회귀 감지 불가, 품질 보증 불가, CI/CD 신뢰도 낮음  

**시정 방법:**

#### tests/conftest.py (공통 설정)
```python
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def temp_data_dir():
    """임시 데이터 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_property_data():
    """샘플 부동산 데이터"""
    return {
        "area_sqm": 84.5,
        "year_built": 2015,
        "rooms": 3,
        "bathrooms": 2,
        "parking": 1,
        "floor": 5,
        "total_floor": 15,
        "condition": 7,
        "original_price": 450000,
        "appraised_price": 455000,
        "outstanding_debt": 250000,
        "market_price": 460000,
        "transaction_count_1y": 12,
        "ltv": 0.55,
        "loan_term_months": 240,
        "days_on_market": 30,
        "appraisal_rounds": 2,
        "age_years": 11,
        "price_per_sqm": 5326,
        "debt_to_price_ratio": 0.55,
        "price_variance": 0.02,
        "market_trend": 0.05,
        "interest_rate": 0.045
    }
```

#### tests/test_api_server.py (API 테스트)
```python
import pytest
from fastapi.testclient import TestClient
from scripts.api_server import app

client = TestClient(app)

class TestHealthCheck:
    def test_health_endpoint_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestModelList:
    def test_list_models_returns_models(self):
        response = client.get("/models")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0

class TestPredictEndpoint:
    def test_predict_with_valid_input(self, sample_property_data):
        payload = {
            "property_data": sample_property_data,
            "model_name": "lightgbm"
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "predicted_price" in data
        assert "model" in data
        assert data["model"] == "lightgbm"
        assert data["predicted_price"] > 0
    
    def test_predict_with_invalid_area_negative(self, sample_property_data):
        sample_property_data["area_sqm"] = -100
        payload = {
            "property_data": sample_property_data,
            "model_name": "lightgbm"
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 422  # Validation error

    def test_predict_with_invalid_year_future(self, sample_property_data):
        sample_property_data["year_built"] = 2050
        payload = {
            "property_data": sample_property_data,
            "model_name": "lightgbm"
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 422

    def test_predict_with_nonexistent_model(self, sample_property_data):
        payload = {
            "property_data": sample_property_data,
            "model_name": "nonexistent_model"
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 404
```

#### tests/test_data_cleaner.py (데이터 처리 테스트)
```python
import pytest
import pandas as pd
import numpy as np
from scripts.cleanse_data import DataCleaner

class TestDataCleaner:
    @pytest.fixture
    def cleaner(self, temp_data_dir):
        cleaner = DataCleaner()
        cleaner.raw_path = temp_data_dir
        cleaner.cleansed_path = temp_data_dir / "cleansed"
        cleaner.cleansed_path.mkdir()
        return cleaner
    
    def test_handle_missing_values(self, cleaner):
        # 결측치 포함 데이터 생성
        df = pd.DataFrame({
            'area': [100.0, np.nan, 200.0],
            'year': [2010, 2015, np.nan],
            'name': ['A', np.nan, 'C']
        })
        
        result = cleaner.handle_missing_values(df, 'test.csv')
        assert result['area'].isnull().sum() == 0
        assert result['year'].isnull().sum() == 0
        assert result['name'].isnull().sum() == 0
    
    def test_remove_outliers(self, cleaner):
        # 아웃라이어 포함 데이터
        df = pd.DataFrame({
            'price': [100, 110, 105, 2000, 95]  # 2000은 아웃라이어
        })
        
        result = cleaner.remove_outliers(df, 'test.csv')
        assert len(result) == 4  # 아웃라이어 1개 제거
        assert 2000 not in result['price'].values
    
    def test_normalize_data(self, cleaner):
        df = pd.DataFrame({
            'price': [100, 200, 300]
        })
        
        result = cleaner.normalize_data(df, 'test.csv')
        assert result['price'].min() >= 0
        assert result['price'].max() <= 1
```

**완성도:** ✅ 완료 기준
- [ ] conftest.py 작성
- [ ] test_api_server.py 작성 (최소 10개 테스트)
- [ ] test_data_cleaner.py 작성 (최소 8개 테스트)
- [ ] test_hyperparameter_tuning.py 작성
- [ ] pytest 실행 및 80% 이상 커버리지 확인
- [ ] CI/CD에 테스트 단계 추가

**시정 시간:** 8-10시간

---

## 2. HIGH PRIORITY ISSUES (우선 시정)

### 2.1 API 키 버전 고정 부재
**원인:** requirements.txt에서 `>=` 사용 (버전 범위)  
**해결:** 정확한 버전으로 고정  
**시정 시간:** 1시간  

### 2.2 모델 메타데이터 하드코딩
**원인:** 실제 모델 성능 대신 R²=1.0 고정값 사용  
**해결:** 실제 모델 학습 후 성능 지표 자동 저장  
**시정 시간:** 3-4시간  

### 2.3 로깅 미흡
**원인:** 기본 logging 사용, 구조화된 로깅 없음  
**해결:** python-json-logger 사용, 로그 로테이션 추가  
**시정 시간:** 2-3시간  

### 2.4 Dockerfile 보안 문제
**원인:** 루트 사용자, 이미지 해시 미지정  
**해결:** 비루트 사용자 추가, 이미지 해시 고정  
**시정 시간:** 1-2시간  

### 2.5 모델 직렬화 보안
**원인:** pickle 사용 (임의 코드 실행 위험)  
**해결:** joblib 사용 + 해시 검증  
**시정 시간:** 1-2시간  

### 2.6 설정 관리 부재
**원인:** 모든 설정이 소스 코드에 하드코딩  
**해결:** Pydantic Settings로 환경변수 관리  
**시정 시간:** 2-3시간  

---

## 3. 종합 시정 계획표

| 순번 | 결함 | 심각도 | 파일 | 예상시간 | 상태 |
|------|------|--------|------|---------|------|
| 1 | API 키 노출 | CRITICAL | .env, 6개 script | 2-3h | ⏳ |
| 2 | CORS 보안 | CRITICAL | api_server.py | 1h | ⏳ |
| 3 | 입력 검증 | CRITICAL | api_server.py | 2-3h | ⏳ |
| 4 | 경로 하드코딩 | CRITICAL | 6개 script | 2-3h | ⏳ |
| 5 | 예외 처리 | CRITICAL | 6개 script | 2-3h | ⏳ |
| 6 | 단위 테스트 | CRITICAL | tests/ | 8-10h | ⏳ |
| 7 | 버전 고정 | HIGH | requirements.txt | 1h | ⏳ |
| 8 | 모델 메타데이터 | HIGH | api_server.py | 3-4h | ⏳ |
| 9 | 로깅 개선 | HIGH | 6개 script | 2-3h | ⏳ |
| 10 | Dockerfile 보안 | HIGH | Dockerfile | 1-2h | ⏳ |
| 11 | 모델 직렬화 | HIGH | api_server.py | 1-2h | ⏳ |
| 12 | 설정 관리 | HIGH | config.py | 2-3h | ⏳ |
| | **합계** | | | **35-50h** | |

---

## 4. 구현 순서 (우선순위)

### Week 1: CRITICAL 이슈 해결 (20-25시간)
```
Day 1: API 키 관리 (2-3h) + CORS 설정 (1h) = 3-4h
Day 2: 입력 검증 (2-3h) + 예외 처리 (2-3h) = 4-6h
Day 3: 경로 문제 (2-3h) + 테스트 기초 (3h) = 5-6h
Day 4-5: 단위 테스트 작성 (8-10h) + 테스트 실행

총 Week 1: 20-26시간
```

### Week 2: HIGH Priority + 검증 (15-25시간)
```
Day 1: 버전 고정 (1h) + 로깅 개선 (2-3h) = 3-4h
Day 2: 모델 메타데이터 (3-4h) + Dockerfile (1-2h) = 4-6h
Day 3: 모델 직렬화 (1-2h) + 설정 관리 (2-3h) = 3-5h
Day 4-5: 통합 테스트 + CI/CD 설정

총 Week 2: 15-24시간
```

---

## 5. 검증 기준 (Definition of Done)

### CRITICAL Issues
- [ ] API 키 .env에만 저장됨 (.gitignore 확인)
- [ ] CORS 특정 도메인만 허용
- [ ] 모든 입력에 Pydantic 검증 적용
- [ ] 모든 경로가 환경변수 지원
- [ ] 모든 예외가 구체적으로 처리됨
- [ ] 단위 테스트 80% 이상 커버리지
- [ ] CI/CD에 테스트 자동 실행

### HIGH Priority
- [ ] requirements.txt 모든 패키지 버전 고정
- [ ] 모델 메타데이터 동적 로드 구현
- [ ] 구조화된 JSON 로깅 적용
- [ ] Dockerfile non-root 사용자 추가
- [ ] 모델 직렬화에 해시 검증 추가
- [ ] config.py로 모든 설정 관리
- [ ] 모든 변경사항 Git 커밋 및 푸시

---

## 6. 위험 완화

| 위험 | 현재 | 완화 후 |
|------|------|--------|
| API 키 노출 | 높음 | 낮음 (환경변수) |
| 보안 공격 (CORS) | 높음 | 낮음 (제한된 출처) |
| 무결성 검증 실패 | 높음 | 낮음 (입력 검증) |
| 프로덕션 배포 실패 | 높음 | 낮음 (테스트 통과) |
| 회귀 감지 불가 | 높음 | 낮음 (80% 테스트 커버리지) |

---

## 7. 예상 효과

### Before (현재)
- 🔴 0% 테스트 커버리지
- 🔴 API 키 노출 위험
- 🔴 Cloud Run 배포 불가능
- 🔴 입력 검증 부재

### After (시정 완료)
- 🟢 80% 이상 테스트 커버리지
- 🟢 API 키 안전하게 관리
- 🟢 Cloud Run 배포 가능
- 🟢 모든 입력 검증됨

---

## 8. 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Logging Best Practices](https://docs.python.org/3/library/logging.html)
- [Docker Security](https://docs.docker.com/engine/security/)

---

**작성일:** 2026-06-15  
**검토 완료:** 🟢 모든 중대 결함 파악 및 해결 방안 제시  
**다음 단계:** 즉시 구현 시작 (Week 1부터)  
**목표 완료:** 2026-06-30 (추정)

