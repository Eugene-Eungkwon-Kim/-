# 🚀 Phase C 완전 실행 가이드
## 실거래 데이터 → 모델 재학습 → 배포

**작성일**: 2026-06-18  
**목표**: 1-2시간 내 배포 완료  
**전제**: 실거래 CSV 파일 확보

---

## 📋 실행 순서

```
Step 1: 데이터 다운로드 (30분)
   ↓
Step 2: 데이터 검증 및 전처리 (5분)
   ↓
Step 3: 모델 재학습 (2-4시간)
   ↓
Step 4: API 배포 (10분)
   ↓
✅ 프로덕션 준비 완료
```

---

## 🎯 Step 1: 실거래 데이터 다운로드 (30분 ~ 1시간)

### 옵션 A: 국토교통부 (⭐ 권장)

**빠르고 신뢰할 수 있음**

```bash
# 1. 수동 다운로드 가이드 보기
python scripts/phase_c_step1_download_molit.py

# 2. 브라우저에서 직접 진행:
# https://rt.molit.go.kr/
# → "부동산 거래 현황" 선택
# → 2024년 선택
# → 서울/경기/부산 등 선택
# → "CSV 다운로드" 클릭
# → 파일 저장

# 3. 파일 이동
mv ~/Downloads/real_estate_*.csv avm_project/data/raw/real_estate_2024.csv
```

### 옵션 B: Data.go.kr

```bash
# 1. 수동 다운로드 가이드 보기
python scripts/phase_c_step1_download_datagokr.py

# 2. 브라우저에서 직접 진행:
# https://www.data.go.kr/
# → 검색: "부동산 실거래 정보"
# → 데이터셋 선택
# → CSV 다운로드

# 3. 파일 이동
mv ~/Downloads/*부동산*.csv avm_project/data/raw/real_estate_2024.csv
```

### 옵션 C: 지역별 오픈데이터

```bash
# 1. 수동 다운로드 가이드 보기
python scripts/phase_c_step1_download_regional.py

# 2. 서울시 데이터: https://data.seoul.go.kr/
# 3. 경기도 데이터: https://data.gg.go.kr/
# 4. CSV 다운로드 및 통합

# 5. 파일 저장
# avm_project/data/raw/real_estate_2024.csv
```

---

## ✅ Step 2: 데이터 검증 및 전처리 (5분)

**자동 14-point 검증**

```bash
# 검증 실행
python scripts/phase_c_step2_validate_and_preprocess.py

# 예상 출력:
# ✅ 파일 로드 성공
# ✅ 컬럼명 자동 표준화
# ✅ 누수 컬럼 제거
# ✅ 필수 컬럼 확인 (거래금액, 거래일, 면적, 지역)
# ✅ 14-point 체크리스트 통과
# ✅ 정제 데이터 저장: avm_project/data/raw/real_estate_2024.csv
```

**확인 사항**:
```bash
# 정제된 파일 확인
wc -l avm_project/data/raw/real_estate_2024.csv
head avm_project/data/raw/real_estate_2024.csv

# 기대값:
# - 행 수: 5,000~200,000+
# - 컬럼: 최소 4개 (거래금액, 거래일, 면적, 지역)
```

---

## 🎯 Step 3: 모델 재학습 (2-4시간)

**6-모델 앙상블 자동 재학습**

```bash
# 재학습 실행
python scripts/phase_c_step3_retrain_models.py

# 실시간 모니터링 (다른 터미널):
tail -f output/retrain_results_*.json
```

**예상 결과**:
```
✅ 6-모델 성능 평가
   1. Linear Regression: R² = 0.82-0.88
   2. Decision Tree: R² = 0.80-0.87
   3. Random Forest: R² = 0.84-0.90
   4. Gradient Boosting: R² = 0.85-0.91 ⭐ (최고)
   5. XGBoost: R² = 0.84-0.90
   6. LightGBM: R² = 0.85-0.90

✅ ENSEMBLE (평균): R² = 0.83-0.89

🏆 최고 성능: Gradient Boosting (R² = 0.85+)

✅ 배포 준비: R² ≥ 0.80 달성
   다음 단계: python scripts/phase_c_step4_deploy.py
```

**모델 저장 위치**:
```
avm_project/models/
├── LinearRegression_model_real_2024.joblib
├── DecisionTree_model_real_2024.joblib
├── RandomForest_model_real_2024.joblib
├── GradientBoosting_model_real_2024.joblib
├── XGBoost_model_real_2024.joblib
├── LightGBM_model_real_2024.joblib
└── production_model_real_2024.joblib (앙상블)
```

---

## 🚀 Step 4: 배포 (10분)

### 옵션 1: 로컬 개발 서버 (권장 - 테스트용)

```bash
# 서버 시작
python -m uvicorn scripts.api_server:app --reload --port 8000

# 브라우저 접속:
# http://localhost:8000/              (메인 페이지)
# http://localhost:8000/dashboard     (실시간 대시보드)
# http://localhost:8000/docs          (API 문서)
```

**예상 출력**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 옵션 2: Docker 배포

```bash
# 이미지 빌드
docker build -t avm-model .

# 컨테이너 실행
docker run -p 8000:8000 avm-model

# 접속:
# http://localhost:8000/
```

### 옵션 3: Cloud Run 배포

```bash
# 배포 스크립트 실행
bash deploy_cloudrun.sh

# 예상 결과:
# ✅ Cloud Run 배포 완료
# 🌐 URL: https://avm-model-xxxxx.a.run.app/
```

---

## 🧪 배포 후 테스트

### 헬스체크

```bash
curl http://localhost:8000/health

# 예상 응답:
# {"status":"healthy","model":"production_real_2024","r2":0.85}
```

### 단일 예측

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "면적": 85.5,
    "건축년도": 2015,
    "층수": 12,
    "지역": 1,
    "방_개수": 3,
    "욕실_개수": 2,
    "엘리베이터": 1,
    "주차장": 2
  }'

# 예상 응답:
# {"prediction": 350000000, "confidence": 0.85}
```

### 배치 예측

```bash
curl -X POST http://localhost:8000/batch_predict \
  -H "Content-Type: application/json" \
  -d '[
    {"면적": 85.5, "건축년도": 2015, ...},
    {"면적": 102.3, "건축년도": 2018, ...}
  ]'

# 예상 응답:
# [
#   {"prediction": 350000000, "confidence": 0.85},
#   {"prediction": 420000000, "confidence": 0.86}
# ]
```

### 대시보드 확인

```bash
# 브라우저에서 접속:
http://localhost:8000/dashboard

# 실시간 모니터링:
- 모델 성능 (R², RMSE, MAE)
- 응답 시간
- 예측 건수
- 오류율
- CPU/메모리 사용률
```

---

## 🔍 트러블슈팅

### Q: 데이터 검증 실패

```bash
# A: 다음을 확인하세요:
python scripts/phase_c_step2_validate_and_preprocess.py

# 필수 컬럼 확인:
python -c "import pandas as pd; df=pd.read_csv('avm_project/data/raw/real_estate_2024.csv'); print(df.columns)"

# 결측치 확인:
python -c "import pandas as pd; df=pd.read_csv('avm_project/data/raw/real_estate_2024.csv'); print(df.isna().sum())"
```

### Q: 모델 재학습 실패

```bash
# A: 의존성 확인:
pip install -r requirements.txt

# 개별 모델 테스트:
python -c "from sklearn.ensemble import GradientBoostingRegressor; print('✅ scikit-learn OK')"

# XGBoost/LightGBM 선택적 설치:
pip install xgboost lightgbm
```

### Q: API 서버 포트 충돌

```bash
# A: 다른 포트 사용:
python -m uvicorn scripts.api_server:app --port 8001

# 포트 확인:
lsof -i :8000
```

### Q: Docker 빌드 실패

```bash
# A: Docker 재설치:
docker system prune -a
docker build -t avm-model .

# 또는 로컬 서버로 진행:
python -m uvicorn scripts.api_server:app --port 8000
```

---

## 📊 성능 기대치

| 기대 항목 | 예상값 | 실제값 | 판정 |
|---------|-------|--------|------|
| R² 점수 | 0.80~0.90 | ? | 검증 후 확인 |
| 응답 시간 | < 100ms | ? | 모니터링 |
| 처리량 | 100 req/s | ? | 부하 테스트 |
| 가용성 | 99.5% | ? | 24h 모니터링 |

---

## ✅ 완료 체크리스트

- [ ] 1️⃣ 실거래 데이터 다운로드
- [ ] 2️⃣ 데이터 검증 통과
- [ ] 3️⃣ 모델 재학습 완료 (R² ≥ 0.80)
- [ ] 4️⃣ API 서버 실행
- [ ] 5️⃣ 헬스체크 통과
- [ ] 6️⃣ 단일 예측 테스트
- [ ] 7️⃣ 배치 예측 테스트
- [ ] 8️⃣ 대시보드 모니터링
- [ ] 9️⃣ 프로덕션 배포 (선택사항)

---

## 🎊 성공 시 다음 단계

```
✅ Phase C 완료 → Phase D 진입

Phase D: 모니터링 & 최적화
├─ 주간 자동 재학습 설정
├─ 성능 회귀 감지
├─ A/B 테스팅
└─ SLA 모니터링
```

---

## 📞 지원

**문제 발생 시**:
1. 이 가이드의 "트러블슈팅" 섹션 확인
2. 로그 파일 검토: `output/` 디렉토리
3. API 문서: http://localhost:8000/docs

**예상 총 소요 시간**: 1-2시간 (데이터 다운로드 포함)

---

**작성**: 2026-06-18  
**상태**: 🟢 준비 완료  
**다음 액션**: Step 1 시작
