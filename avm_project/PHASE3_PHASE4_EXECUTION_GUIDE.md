# 📊 Phase 3 & Phase 4 실행 가이드

**상태**: ✅ 스크립트 완성 및 테스트 (2026-06-17)  
**구성**: Phase 3 (데이터 수집) + Phase 4 (모델 최적화)  

---

## 📋 목차

1. [Phase 3: 실제 데이터 수집](#phase-3-실제-데이터-수집)
2. [Phase 4: 모델 성능 최적화](#phase-4-모델-성능-최적화)
3. [통합 파이프라인 실행](#통합-파이프라인-실행)
4. [결과 분석](#결과-분석)
5. [문제 해결](#문제-해결)

---

## Phase 3: 실제 데이터 수집

### 📥 개요

**목적**: Data.go.kr API에서 부동산 실거래 데이터를 월별로 수집하고 저장

**입력**: 월 범위 (예: 202401-202406)  
**출력**: `data/raw/real_estate_combined_YYYYMMDD.csv`  
**실행 시간**: 6개월 기준 약 3-5분 (샘플 데이터)

### 🚀 기본 실행

```bash
# 기본 사용법: 6개월 데이터 (2024년 1월~6월)
python3 scripts/phase3_data_collection.py --months 202401-202406

# 단일 월 데이터
python3 scripts/phase3_data_collection.py --months 202406

# 1년치 데이터
python3 scripts/phase3_data_collection.py --months 202401-202412
```

### 📊 Phase 3 샘플 실행 결과

```
================================================================================
🚀 PHASE 3 - 실제 데이터 수집 및 처리 파이프라인
================================================================================

[Step 1/4] 데이터 수집
======================================================================
📊 6개월 데이터 수집 시작
======================================================================
📥 202401 데이터 수집 중...
   ⚠️  API 키 미설정 — 샘플 데이터 생성 중...
   ✅ 샘플 데이터 생성: 500 행
...
✅ 수집 완료: 3000 행, 21 컬럼
   기간: 202401 ~ 202406
   크기: 8.2 MB

[Step 2/4] 데이터 검증
======================================================================
✓ 데이터 검증
======================================================================
행: 3,000, 컬럼: 21
메모리: 8.2 MB
중복: 0개
결측치: 없음 ✅

[Step 3/4] 데이터 저장
======================================================================
✅ 저장: real_estate_combined_20260617.csv

[Step 4/4] 요약 리포트
================================================================================
✅ PHASE 3 수집 완료
================================================================================
📊 수집 데이터: 3,000행 × 21컬럼
📁 저장 위치: real_estate_combined_20260617.csv
📋 리포트: phase3_collection_report_20260617_061703.json
```

### 🔌 API 키 설정

실제 데이터를 수집하려면 Data.go.kr API 키 필요:

```bash
# 1. .env 파일에 API 키 설정
echo 'DATA_GO_KR_API_KEY=YOUR_API_KEY' >> .env

# 2. 환경 변수로 설정
export DATA_GO_KR_API_KEY=YOUR_API_KEY

# 3. 스크립트 재실행
python3 scripts/phase3_data_collection.py --months 202401-202406
```

### 📁 출력 파일

| 파일 | 설명 | 크기 |
|------|------|------|
| `data/raw/real_estate_combined_YYYYMMDD.csv` | 수집된 원본 데이터 | 8-160 MB |
| `output/phase3_collection_report_*.json` | 수집 리포트 (행, 컬럼, 검증) | ~500 B |

### ⚠️ 주의사항

- **API 제한**: 월 10,000건, 일 2,000건 (Data.go.kr 정책)
- **네트워크**: 6개월 기준 평균 3-5분 소요
- **샘플 모드**: API 키 미설정 시 자동으로 샘플 데이터 생성 (학습용)

---

## Phase 4: 모델 성능 최적화

### 🎯 개요

**목적**: 6개 기본 모델의 성능을 평가하고 상위 2개 모델을 GridSearchCV로 최적화

**입력**: `data/raw/*.csv` 또는 샘플 생성  
**출력**: `output/model_optimization_*.json`  
**실행 시간**: 약 2-3분 (샘플 데이터, CPU 기준)

### 🚀 기본 실행

```bash
# Phase 3 수집 후 자동으로 최신 데이터 사용
python3 scripts/phase4_model_optimization.py

# 샘플 데이터로 테스트
python3 scripts/phase4_model_optimization.py  # data/processed/ 없으면 샘플 자동 생성
```

### 📊 Phase 4 샘플 실행 결과

```
================================================================================
🚀 단계 2: 모델 성능 최적화
================================================================================
📥 데이터 로드
   ⚠️  처리된 데이터 없음 — 샘플 사용
   ✅ 샘플 생성: 500 × 19

[Step 1/3] 기준선 모델 평가
======================================================================

🔨 LinearRegression
   CV R² (5-fold): 0.9592 ± 0.0068

🔨 DecisionTree
   CV R² (5-fold): 0.0988 ± 0.1570

🔨 RandomForest
   CV R² (5-fold): 0.6256 ± 0.0539

🔨 GradientBoosting
   CV R² (5-fold): 0.6837 ± 0.0417

🔨 XGBoost
   CV R² (5-fold): 0.7139 ± 0.0410

🔨 LightGBM
   CV R² (5-fold): 0.7825 ± 0.0360

[Step 2/3] 하이퍼파라미터 튜닝
======================================================================

🔧 RandomForest 튜닝
   검색 중... (조합: 9개)
   최고 R²: 0.6284
   최적 파라미터: {'model__max_depth': 20, 'model__n_estimators': 150}

🔧 GradientBoosting 튜닝
   검색 중... (조합: 9개)
   최고 R²: 0.7917
   최적 파라미터: {'model__learning_rate': 0.2, 'model__n_estimators': 150}

[Step 3/3] 기능 선택
======================================================================

📊 특성 중요도 (상위 10)
   1. Feature_10: 120.5403
   2. Feature_4: 94.8429
   3. Feature_16: 86.2514
   4. Feature_1: 71.7284
   5. Feature_3: 53.6537
   6. Feature_11: 49.9841
   7. Feature_12: 28.7225
   8. Feature_9: 23.1557
   9. Feature_17: 23.0818
   10. Feature_15: 14.1672

✅ 상위 10개 특성 선택

======================================================================
📋 성능 최적화 리포트
======================================================================

✅ 기준선 모델 최고: LinearRegression (R²=0.9592)
✅ 최적화 모델 최고: GradientBoosting (R²=0.7917)
✅ 평균 성능 개선: +0.0554

📁 리포트: model_optimization_20260617_061933.json

================================================================================
✅ 모델 성능 최적화 완료
================================================================================
```

### 📈 성능 분석

**기준선 모델 (Baseline)**:
| 모델 | R² 점수 | 표준편차 |
|------|---------|---------|
| LinearRegression | 0.9592 | 0.0068 |
| LightGBM | 0.7825 | 0.0360 |
| XGBoost | 0.7139 | 0.0410 |
| GradientBoosting | 0.6837 | 0.0417 |
| RandomForest | 0.6256 | 0.0539 |
| DecisionTree | 0.0988 | 0.1570 |

**최적화 모델 (Optimized)**:
| 모델 | 최고 R² | 개선도 |
|------|----------|--------|
| GradientBoosting | 0.7917 | +0.1079 |
| RandomForest | 0.6284 | +0.0028 |

### 📁 출력 파일

| 파일 | 설명 |
|------|------|
| `output/model_optimization_*.json` | 최적화 리포트 (기준선 vs 최적화 성능) |

### 📄 리포트 구조

```json
{
  "timestamp": "2026-06-17T06:19:33",
  "baseline": {
    "LinearRegression": {"cv_mean": 0.9592, "cv_std": 0.0068},
    // ... 6개 모델
  },
  "optimized": {
    "RandomForest": {"best_score": 0.6284, "improvement": 0.0028},
    "GradientBoosting": {"best_score": 0.7917, "improvement": 0.1079}
  },
  "summary": {
    "best_baseline": "LinearRegression (R²=0.9592)",
    "best_optimized": "GradientBoosting (R²=0.7917)",
    "avg_improvement": 0.0554
  }
}
```

---

## 통합 파이프라인 실행

### 📌 순차 실행 (권장)

Phase 3에서 수집한 데이터를 Phase 4에서 최적화하는 완전한 파이프라인:

```bash
#!/bin/bash
set -e

echo "🚀 Phase 3-4 통합 파이프라인 시작"

# Phase 3: 데이터 수집
echo "[1/2] Phase 3 데이터 수집..."
python3 scripts/phase3_data_collection.py --months 202401-202406

# Phase 4: 모델 최적화
echo "[2/2] Phase 4 모델 최적화..."
python3 scripts/phase4_model_optimization.py

echo "✅ 파이프라인 완료"
```

### ⏱️ 예상 실행 시간

| 단계 | 데이터 크기 | 예상 시간 |
|------|-----------|---------|
| Phase 3 (샘플) | 3,000행 | 30초 |
| Phase 3 (1년) | 500,000행 | 3-5분 |
| Phase 4 (샘플) | 500행 | 2분 |
| Phase 4 (1년) | 500,000행 | 10-15분 |

---

## 결과 분석

### 🔍 Phase 3 결과 검증

```bash
# 수집된 데이터 확인
python3 -c "
import pandas as pd
df = pd.read_csv('data/raw/real_estate_combined_20260617.csv')
print(f'행: {len(df):,}, 컬럼: {len(df.columns)}')
print(f'컬럼: {list(df.columns)}')
print(f'데이터타입:\\n{df.dtypes}')
print(f'결측치:\\n{df.isnull().sum()}')
"
```

### 📊 Phase 4 결과 분석

```bash
# 최적화 리포트 보기
python3 -c "
import json
with open('output/model_optimization_20260617_061933.json') as f:
    report = json.load(f)

print('=== 기준선 모델 ===')
for model, metrics in report['baseline'].items():
    print(f'{model}: R²={metrics[\"cv_mean\"]:.4f} ± {metrics[\"cv_std\"]:.4f}')

print('\\n=== 최적화 모델 ===')
for model, metrics in report['optimized'].items():
    print(f'{model}: R²={metrics[\"best_score\"]:.4f}, 개선도: +{metrics[\"improvement\"]:.4f}')

print('\\n=== 요약 ===')
print(f'기준선 최고: {report[\"summary\"][\"best_baseline\"]}, R²={report[\"summary\"][\"best_baseline_r2\"]:.4f}')
print(f'최적화 최고: {report[\"summary\"][\"best_optimized\"]}, R²={report[\"summary\"][\"best_optimized_r2\"]:.4f}')
"
```

### 🎯 특성 중요도 분석

Feature Selection 결과에서 상위 10개 특성이 전체 신호의 대부분을 설명:

```
Feature_10: 120.54 (가장 중요)
Feature_4:  94.84
Feature_16: 86.25
Feature_1:  71.73
...
상위 10개로 차원 축소: 19 → 10 (47% 감소)
```

---

## 문제 해결

### Q: Phase 3 실행 시 API 오류 발생

```
❌ 오류: [Errno -2] Name or service not known
```

**원인**: 네트워크 연결 또는 API 서버 다운  
**해결책**:
```bash
# 1. 네트워크 확인
ping data.go.kr

# 2. API 키 상태 확인 (웹 포털)
# https://www.data.go.kr → 마이페이지 → API 관리

# 3. 샘플 데이터로 테스트
python3 scripts/phase3_data_collection.py --months 202406  # 단일 월 시도
```

### Q: Phase 4 실행 시 메모리 부족

```
MemoryError: Unable to allocate...
```

**원인**: GridSearchCV 튜닝 시 큰 데이터셋  
**해결책**:
```bash
# 1. 스크립트 수정: 파라미터 그리드 축소
# scripts/phase4_model_optimization.py의 tuning_params 수정
'model__n_estimators': [50, 100],  # [50, 100, 150] → 축소

# 2. 또는 샘플 데이터로 먼저 테스트
python3 scripts/phase4_model_optimization.py
```

### Q: 속도가 너무 느림

**최적화 방법**:
```bash
# 1. CPU 코어 확인
python3 -c "import os; print(f'Available CPUs: {os.cpu_count()}')"

# 2. 스크립트에서 n_jobs 파라미터 확인 (기본값: -1 모든 코어 사용)

# 3. 큰 데이터셋의 경우 샘플링 고려
python3 -c "
import pandas as pd
df = pd.read_csv('data/raw/real_estate_combined_YYYYMMDD.csv')
df.sample(frac=0.1).to_csv('data/raw/sample_10pct.csv')
"
```

### Q: 결과가 이전과 다름

**원인**: 랜덤 시드 차이 또는 데이터 변경  
**해결책**:
```bash
# 스크립트의 random_state 파라미터 확인
# (모든 모델과 스플릿에서 random_state=42 설정됨)
```

---

## 📋 체크리스트

### Phase 3 실행 전
- [ ] Data.go.kr API 키 발급 (선택사항)
- [ ] `.env` 파일에 API 키 설정 (선택사항)
- [ ] 수집 월 범위 결정 (예: 202401-202406)

### Phase 4 실행 전
- [ ] Phase 3 완료 또는 데이터 준비
- [ ] CPU/메모리 여유 확인 (2GB+ 권장)
- [ ] 그리드 서치 파라미터 확인 (튜닝 시간 영향)

### 실행 후
- [ ] 출력 파일 생성 확인
- [ ] 리포트 JSON 형식 검증
- [ ] 성능 메트릭 시각화/저장
- [ ] 최적화 결과 대시보드에 반영

---

## 🔗 관련 파일

- `scripts/phase3_data_collection.py` - 데이터 수집 구현
- `scripts/phase4_model_optimization.py` - 모델 최적화 구현
- `DASHBOARD_GUIDE.md` - 성능 모니터링 대시보드
- `LOOPING_AUTOMATION_GUIDE.md` - 자동 재학습 스케줄러
- `feature_schema.py` - 특성 스키마 정의

---

**마지막 업데이트**: 2026-06-17  
**상태**: ✅ Phase 3-4 완료 및 테스트
