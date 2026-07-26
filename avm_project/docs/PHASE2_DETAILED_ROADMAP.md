# AVM 프로젝트 Phase 2-5 상세 로드맵
## 다음 개발 단계 계획서

**작성일:** 2026-06-12  
**현재 상태:** Phase 1 완료, Phase 2 준비 중  
**총 예상 기간:** 4-6주

---

## 📊 프로젝트 상황 분석

### 완료된 작업 (Phase 1)
✅ 프로젝트 폴더 구조 생성  
✅ 데이터 전처리 파이프라인 개발  
✅ 4개 기본 ML 모델 구현  
✅ 한국 부동산 데이터 API 연동  
✅ Loop Engineering 자동화 시스템  
✅ 종합 문서화 (1500+ 줄)  

### 현재 문제점
⚠️ **API 403 Forbidden** - Data.go.kr API 인증 필요
- 문제: API 키 승인/활성화 확인 필요
- 영향: 실제 데이터 수집 불가
- 해결책: Data.go.kr 포털에서 API 상태 확인 및 재신청

### 테스트 성과
✅ 샘플 데이터로 전체 파이프라인 성공
✅ 모든 모델 R² > 0.90 달성
✅ 자동화 시스템 작동 확인
✅ 로깅 및 리포팅 정상 작동

---

## 🎯 Phase 2-5 세부 계획

## **PHASE 2: 데이터 수집 및 모델 개발** (2주)
*목표: 실제 데이터로 모델 검증 및 성능 최적화*

### Week 1: API 인증 & 데이터 수집

#### Task 2.1: API 인증 해결 (1일)
```
담당자: 사용자 (Data.go.kr 포털 작업)
예상 소요: 1일

절차:
1. Data.go.kr 포털 방문 → 로그인
2. 마이페이지 → API 관리 → "부동산 실거래 정보"
3. API 상태 확인
   ├─ 승인됨: 기존 API 키로 진행
   ├─ 거절됨: 재신청 필요
   └─ 대기중: 승인 대기
4. API 키 확인 및 업데이트
   - 환경 변수 설정: export DATAGOVKR_API_KEY="new-key"
   - 또는 avm_config.json 업데이트

검증 방법:
python3 scripts/test_api_collection.py --api-key "your-key"
```

**결과물:**
- ✅ API 키 활성화 완료
- ✅ API 연결 테스트 성공 로그

---

#### Task 2.2: 2024년 전체 데이터 수집 (3-4일)
```
담당자: 자동화 시스템
예상 소요: 3-4일 (월 1일)

실행 명령:
python3 scripts/avm_orchestrator.py \
  --start-date 202401 --end-date 202412

수집 대상 데이터:
- 부동산 실거래 정보 (2024-01 ~ 2024-12)
- 월별 약 1,000-5,000건
- 예상 총 데이터: 12,000-60,000건

저장 위치:
data/raw/
├── real_estate_202401.csv
├── real_estate_202402.csv
├── ...
└── real_estate_202412.csv

검증 기준:
□ 각 월별 파일 크기 > 100KB
□ 컬럼 수 >= 20개
□ 결측값 < 10%
□ 데이터 타입 일치

모니터링:
- 로그: tail -f logs/avm_orchestration_*.log
- 리포트: cat output/orchestration_report_*.json | jq .
```

**결과물:**
- ✅ 12개월 데이터 CSV 파일
- ✅ 데이터 품질 검증 리포트
- ✅ 수집 성공 로그 기록

---

### Week 2: 모델 개발 및 최적화

#### Task 2.3: 고급 모델 추가 (2일)
```
담당자: 개발자
예상 소요: 2일

추가 모델:
1. XGBoost 모델
   - 파일: scripts/model_development.py 확장
   - 메서드: train_xgboost()
   - 예상 R²: 0.88-0.92
   
2. LightGBM 모델
   - 메서드: train_lightgbm()
   - 예상 R²: 0.87-0.91
   
3. Neural Network (TensorFlow)
   - 메서드: train_neural_network()
   - 아키텍처: 3-layer dense network
   - 예상 R²: 0.85-0.90

구현 코드 예시:
```python
def train_xgboost(self, X_train, y_train):
    import xgboost as xgb
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        random_state=42
    )
    model.fit(X_train, y_train)
    return model

def train_lightgbm(self, X_train, y_train):
    import lightgbm as lgb
    model = lgb.LGBMRegressor(
        n_estimators=100,
        learning_rate=0.1,
        num_leaves=31
    )
    model.fit(X_train, y_train)
    return model
```

테스트:
python3 -c "from scripts.model_development import AVMModelDeveloper; dev = AVMModelDeveloper(); print(dev.train_xgboost)"

결과물:
- ✅ XGBoost 모델 코드
- ✅ LightGBM 모델 코드
- ✅ Neural Network 모델 코드
- ✅ 모든 모델 테스트 통과
```

---

#### Task 2.4: 하이퍼파라미터 최적화 (2일)
```
담당자: 개발자
예상 소요: 2일

대상 모델:
- Linear Regression (간단한 튜닝만)
- Decision Tree (max_depth, min_samples_split)
- Random Forest (n_estimators, max_depth)
- Gradient Boosting (learning_rate, n_estimators)
- XGBoost (max_depth, learning_rate, subsample)

구현 방법:
1. GridSearchCV 또는 RandomizedSearchCV 사용
2. 5-fold Cross Validation
3. 성능 지표: R² score

파라미터 그리드 예시:
```python
param_grids = {
    'random_forest': {
        'n_estimators': [50, 100, 200],
        'max_depth': [10, 15, 20],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    },
    'gradient_boosting': {
        'n_estimators': [100, 200, 300],
        'learning_rate': [0.01, 0.05, 0.1],
        'max_depth': [3, 4, 5],
        'subsample': [0.7, 0.8, 0.9]
    }
}
```

예상 개선:
- Random Forest: R² 0.9717 → 0.98+
- Gradient Boosting: R² 0.9683 → 0.97+
- XGBoost: R² 신규 → 0.96+

결과물:
- ✅ 최적화된 하이퍼파라미터 파일
- ✅ 파라미터 튜닝 로그
- ✅ 성능 비교 리포트
```

---

#### Task 2.5: 모델 검증 및 평가 (1일)
```
담당자: 개발자
예상 소요: 1일

검증 방법:
1. 시계열 크로스 검증 (Time Series CV)
   - 2024-01~06: 훈련
   - 2024-07~12: 검증 (월별)
   
2. 성능 지표 계산
   - R² Score (결정 계수)
   - RMSE (평균 제곱근 오차)
   - MAE (평균 절대 오차)
   - MAPE (평균 절대 백분율 오차)
   
3. 혼동 행렬 및 잔차 분석
   - 예측값 vs 실제값 플롯
   - 잔차 분포 분석
   - 이상값 탐지

코드:
```python
def evaluate_models_comprehensive(models, X_test, y_test):
    results = {}
    for name, model in models.items():
        y_pred = model.predict(X_test)
        
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        mape = np.mean(np.abs((y_test - y_pred) / y_test))
        
        results[name] = {
            'r2': r2,
            'rmse': rmse,
            'mae': mae,
            'mape': mape
        }
    
    return results
```

결과물:
- ✅ 모델 성능 비교 리포트
- ✅ 그래프/시각화 (matplotlib)
- ✅ 최고 성능 모델 선정
```

---

**Phase 2 완료 기준:**
✅ API 인증 및 실제 데이터 수집  
✅ 6개 이상의 ML 모델 구현  
✅ 하이퍼파라미터 최적화 완료  
✅ 모든 모델 R² > 0.90 달성  
✅ 모델 검증 리포트 작성  

**산출물:**
- 12개월 실제 데이터 (12 × CSV 파일)
- 최적화된 6개 모델 (models/*.pkl)
- 성능 비교 리포트 (output/model_comparison.json)
- 검증 리포트 (docs/MODEL_VALIDATION_REPORT.md)

---

## **PHASE 3: 모델 검증 및 평가** (1주)
*목표: 모델 신뢰도 검증 및 프로덕션 준비*

### Task 3.1: Feature Importance 분석 (2일)
```
담당자: 개발자
예상 소요: 2일

분석 대상:
- Random Forest: feature_importances_
- Gradient Boosting: feature_importances_
- XGBoost: get_booster().get_score()
- SHAP values: shap library 활용

구현:
```python
import shap

def analyze_feature_importance(model, X_test, model_type='tree'):
    if model_type == 'tree':
        importances = model.feature_importances_
        return pd.DataFrame({
            'feature': X_test.columns,
            'importance': importances
        }).sort_values('importance', ascending=False)
    
    elif model_type == 'shap':
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        return shap_values

```

산출물:
- Feature Importance 그래프
- Top 10 중요 특성 목록
- SHAP Summary Plot
```

### Task 3.2: 모델 해석 및 신뢰도 평가 (2일)
```
담당자: 개발자
예상 소요: 2일

평가 항목:
1. 모델 안정성
   - 다양한 데이터셋에서의 성능 일관성
   - 극단값 처리 능력
   
2. 편향성 (Bias) 분석
   - 지역별 예측 편향
   - 가격대별 예측 편향
   
3. 불확실성 (Uncertainty)
   - 신뢰 구간 추정
   - 예측 신뢰도 점수

산출물:
- 신뢰도 평가 리포트
- 모델 안정성 그래프
- 권장 사항 문서
```

### Task 3.3: A/B 테스트 설계 (2일)
```
담당자: 개발자 + 사용자
예상 소요: 2일

설계 내용:
1. 베이스라인 모델 설정
   - 현재 운영 중인 평가 방식 또는 간단한 선형 모델
   
2. 신규 모델 테스트
   - 랜덤 포레스트 vs XGBoost
   - 각 100건 샘플 테스트
   
3. 성과 지표
   - 예측 정확도 (MAE)
   - 사용 용이성
   - 실행 속도

산출물:
- A/B 테스트 계획서
- 테스트 결과 분석
- 최종 모델 선정 기준서
```

---

## **PHASE 4: 시스템 통합 및 배포** (2주)
*목표: 프로덕션 환경에 배포하고 자동화 완성*

### Task 4.1: 웹 API 개발 (3일)
```
담당자: 개발자
예상 소요: 3일

프레임워크: FastAPI
파일: scripts/api_server.py

주요 엔드포인트:
1. POST /predict
   - 요청: 부동산 정보 JSON
   - 응답: 예상 가격 + 신뢰도 점수
   
2. GET /models
   - 응답: 사용 가능한 모델 목록
   
3. GET /health
   - 응답: 서버 상태
   
4. POST /retrain
   - 요청: 새 데이터로 모델 재학습
   - 응답: 재학습 완료 확인

코드 예시:
```python
from fastapi import FastAPI
from pydantic import BaseModel
import pickle

app = FastAPI()

class PropertyInfo(BaseModel):
    area_sqm: float
    year_built: int
    location: str
    rooms: int
    condition: str

@app.post("/predict")
def predict(property: PropertyInfo):
    # 데이터 전처리
    X = preprocess_input(property)
    
    # 모델 로드
    with open('models/best_model.pkl', 'rb') as f:
        model = pickle.load(f)
    
    # 예측
    price = model.predict([X])[0]
    confidence = calculate_confidence(model, X)
    
    return {
        "predicted_price": price,
        "confidence": confidence
    }
```

결과물:
- ✅ FastAPI 서버 (api_server.py)
- ✅ API 문서 (자동 생성 Swagger)
- ✅ 테스트 완료
```

### Task 4.2: Docker 컨테이너화 (2일)
```
담당자: 개발자
예상 소요: 2일

파일:
- Dockerfile
- docker-compose.yml
- .dockerignore

Dockerfile 예시:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY avm_project/ ./avm_project/

EXPOSE 8000

CMD ["uvicorn", "avm_project.scripts.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

빌드 및 실행:
```bash
docker build -t avm-api:1.0 .
docker run -p 8000:8000 avm-api:1.0
```

결과물:
- ✅ Docker 이미지 (avm-api:1.0)
- ✅ docker-compose.yml
- ✅ 이미지 테스트 완료
```

### Task 4.3: 클라우드 배포 (2일)
```
담당자: 개발자 + DevOps
예상 소요: 2일

배포 옵션:
1. AWS EC2 + RDS
   - 인스턴스 타입: t3.medium
   - 데이터베이스: PostgreSQL
   
2. Google Cloud Run (권장)
   - 서버리스 배포
   - 자동 스케일링
   - 비용 효율적
   
3. Azure Container Instances
   - 컨테이너 기반 배포
   - 관리형 서비스

배포 절차:
1. 클라우드 프로젝트 생성
2. Docker 이미지 레지스트리 업로드
3. 서비스 배포 및 설정
4. SSL 인증서 설정
5. 모니터링 활성화

결과물:
- ✅ 클라우드 배포 완료
- ✅ 접근 가능한 API 엔드포인트
- ✅ 배포 가이드 문서
```

### Task 4.4: CI/CD 파이프라인 구축 (2일)
```
담당자: DevOps
예상 소요: 2일

도구: GitHub Actions

파일: .github/workflows/deploy.yml

워크플로우:
1. 코드 푸시 감지
2. 자동 테스트 실행
3. Docker 이미지 빌드
4. 레지스트리 업로드
5. 클라우드 배포

예시 구성:
```yaml
name: Deploy AVM

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: docker build -t avm-api:latest .
      - run: docker push gcr.io/project-id/avm-api:latest
      - run: gcloud run deploy avm-api --image gcr.io/project-id/avm-api:latest
```

결과물:
- ✅ CI/CD 파이프라인 구성
- ✅ 자동 테스트 및 배포
- ✅ 배포 로그 및 모니터링
```

---

## **PHASE 5: 문서화 및 최종 보고** (1주)
*목표: 완벽한 프로젝트 완성 및 인수인계 준비*

### Task 5.1: 사용자 가이드 작성 (2일)
```
담당자: 기술 문서 작성자
예상 소요: 2일

작성 내용:
1. 시스템 설치 및 설정
2. API 사용 방법
3. 모델 재학습 절차
4. 문제 해결 가이드
5. FAQ

파일: docs/USER_GUIDE.md (500+ 줄)
```

### Task 5.2: 기술 문서 작성 (2일)
```
담당자: 기술 문서 작성자
예상 소요: 2일

작성 내용:
1. 아키텍처 설명
2. 데이터 흐름
3. 모델 상세 설명
4. API 명세
5. 데이터베이스 스키마

파일: docs/TECHNICAL_DOCUMENTATION.md (600+ 줄)
```

### Task 5.3: 성과 평가 및 보고 (2일)
```
담당자: 프로젝트 매니저
예상 소요: 2일

내용:
1. 프로젝트 목표 달성도 평가
2. 주요 성과 정리
3. 과제 및 해결 방안
4. 향후 개선 방향

산출물:
- 최종 완료 보고서 (FINAL_PROJECT_REPORT.md)
- 성과 지표 정리
- 투자 수익률 (ROI) 분석
```

### Task 5.4: 인수인계 및 교육 (1일)
```
담당자: 개발자 + 운영팀
예상 소요: 1일

활동:
1. 운영팀 교육
   - 시스템 사용법
   - 문제 해결 방법
   - 긴급 상황 대응
   
2. 운영 매뉴얼 전달
   - 일일 점검 항목
   - 주간 유지보수 작업
   - 월간 성과 분석
   
3. 연락처 및 지원 방안 수립

산출물:
- 운영 매뉴얼
- 교육 자료
- 기술 지원 체계
```

---

## 📅 종합 일정표

```
Week 1-2 (Phase 2)
├─ Day 1: API 인증 해결
├─ Day 2-5: 데이터 수집 (자동화)
├─ Day 6-7: 고급 모델 추가
├─ Day 8-9: 하이퍼파라미터 최적화
└─ Day 10: 모델 검증

Week 3 (Phase 3)
├─ Day 1-2: Feature Importance 분석
├─ Day 3-4: 신뢰도 평가
└─ Day 5: A/B 테스트 설계

Week 4-5 (Phase 4)
├─ Day 1-3: 웹 API 개발
├─ Day 4-5: Docker 컨테이너화
├─ Day 6-7: 클라우드 배포
└─ Day 8-9: CI/CD 파이프라인

Week 6 (Phase 5)
├─ Day 1-2: 사용자 가이드
├─ Day 3-4: 기술 문서
├─ Day 5: 성과 보고
└─ Day 6: 인수인계

총 기간: 4-6주
```

---

## 💰 자원 할당

| 역할 | 투입 | 기간 |
|------|------|------|
| 개발자 | 240시간 | 6주 |
| DevOps | 40시간 | 2주 |
| 기술 문서 | 40시간 | 1주 |
| 프로젝트 관리 | 20시간 | 6주 |
| **총합** | **340시간** | **6주** |

---

## ✅ 성공 기준

### Phase 2 완료
- [ ] API 403 오류 해결
- [ ] 12개월 데이터 수집 완료
- [ ] 6개 이상 모델 구현
- [ ] 모든 모델 R² > 0.90
- [ ] 하이퍼파라미터 최적화 완료

### Phase 3 완료
- [ ] Feature Importance 분석 완료
- [ ] 모델 신뢰도 > 95%
- [ ] A/B 테스트 설계 완료

### Phase 4 완료
- [ ] FastAPI 서버 배포 완료
- [ ] Docker 컨테이너화 완료
- [ ] 클라우드 배포 완료
- [ ] CI/CD 파이프라인 작동

### Phase 5 완료
- [ ] 사용자 가이드 작성 완료
- [ ] 기술 문서 작성 완료
- [ ] 최종 보고서 제출
- [ ] 운영팀 인수인계 완료

---

## 🚀 즉시 실행 항목

### 우선순위 1 (이번 주)
```bash
# 1. API 인증 확인
# Data.go.kr 포털 → 마이페이지 → API 관리
# "부동산 실거래 정보" API 상태 확인

# 2. API 키 환경 변수 설정
export DATAGOVKR_API_KEY="your-api-key"
echo "export DATAGOVKR_API_KEY='your-api-key'" >> ~/.bashrc

# 3. API 연결 테스트
python3 scripts/test_api_collection.py

# 4. 자동화 시스템 배포
./scripts/setup_cron_automation.sh
```

### 우선순위 2 (2주)
```bash
# 1. 데이터 수집 (자동)
# crontab에 이미 설정됨, 매주 목요일 10:00 자동 실행

# 2. 수집 상황 모니터링
tail -f logs/cron_execution.log

# 3. 데이터 품질 확인
# output/orchestration_report_*.json 확인
```

---

## 📞 연락처 및 지원

| 역할 | 담당자 | 연락처 |
|------|--------|--------|
| 프로젝트 전체 | 프로젝트 매니저 | PM@company.com |
| 개발 | Claude AI | AI Assistant |
| 인프라 | DevOps 팀 | devops@company.com |
| 데이터 | 데이터 팀 | data@company.com |

---

## 📚 참고 문서

- [LOOP_ENGINEERING_GUIDE.md](./LOOP_ENGINEERING_GUIDE.md)
- [AVM_COMPLETE_GUIDE.md](./AVM_COMPLETE_GUIDE.md)
- [KOREAN_REAL_ESTATE_DATA_COLLECTION.md](./KOREAN_REAL_ESTATE_DATA_COLLECTION.md)
- [PHASE_1_REPORT.md](./PHASE_1_REPORT.md)

---

**작성자:** Claude AI Assistant  
**버전:** 1.0  
**마지막 업데이트:** 2026-06-12  
**상태:** 검토 대기 중
