# Phase 12 이후 다음 개발 단계 - 상세 보고

**작성일**: 2026-06-25  
**현재 상태**: Phase 12.F-G 완료, 12.H-I 준비 중  
**선택**: Phase 12.H/I (2-3일) → Phase 13 (15-20일)

---

## 1️⃣ Phase 12 마무리 - Task 12.H/I (2-3일)

### Task 12.H: PDF 리포트 생성 (1일, 6시간)

**목표**: Loan4U_Phase12_Final_Report.pdf (1-2페이지 전문가용)

**구현 방식**:
```python
# weasyprint 권장 (간단 & 효율적)
# pip install weasyprint

from weasyprint import HTML

html_template = """
<html>
<head><style>
  body { font-family: Arial; margin: 20px; }
  h1 { color: #1F4E78; border-bottom: 2px solid #1F4E78; }
  table { border-collapse: collapse; width: 100%; margin: 20px 0; }
  th { background: #1F4E78; color: white; padding: 10px; }
  td { border: 1px solid #ddd; padding: 8px; }
  .metric { font-size: 16px; font-weight: bold; color: #1F4E78; }
</style></head>
<body>
  <h1>Loan4U Phase 12 Global Validation Report</h1>
  <p class="metric">Review Date: 2026-06-25</p>
  
  <h2>Executive Summary</h2>
  <p>8 countries covered. Properties validated. Model ensemble ready.</p>
  
  <h2>Country Summary</h2>
  <table>
    <tr><th>Country</th><th>Properties</th><th>Audited</th><th>Pass Rate</th></tr>
    <!-- 8 rows -->
  </table>
</body>
</html>
"""

HTML(string=html_template).write_pdf('output/Loan4U_Phase12_Final_Report.pdf')
```

**시간**: 1일 (45분 코딩 + 15분 검증)

---

### Task 12.I: 검증 & 최종화 (1-2일)

**12.I.1: 파일 무결성** (30분)
- Excel sheets: 21개 확인
- 검증 컬럼: 모두 채워짐
- 색상 코딩: 올바른 그레이드 매핑

**12.I.2: 품질 평가** (30분)
```
Metrics:
├─ 적정: >60% (Green)
├─ 확인필요: 20-30% (Yellow)
├─ 편차주의: <10% (Red)
└─ 추가확인: <5% (Error)
```

**12.I.3: Git & 배포** (30분)
- 최종 커밋
- 브랜치 병합
- 배포 문서 작성

**시간**: 1-2일 (2-3시간 개발 + 검증)

---

## 2️⃣ Phase 13: 글로벌 모델 학습 (15-20일)

### 13.1: 데이터 수집 & 전처리 (5일)

**입력 소스**:
```
UK: HM Land Registry (200K 레코드)
SG: URA Singapore (80K)
JP: 토지총합정보 (150K)
DE: Immobilienspiegel (120K)
AU: CoreLogic (180K)
CA: MLS Canada (160K)
TH: DDproperty (60K)
HK: Centaline (90K)
```

**특성 생성** (30-35개/국가):
```
기본: price, area, rooms, bathrooms, age
파생:
  - price_per_sqm (가격/면적)
  - location_tier (지역 등급)
  - walkability_score (보행성)
  - school_proximity (학교 거리)
  - crime_rate_nearby (범죄율)
  - neighborhood_density (지역 밀도)
  - price_trend_3m (3개월 추세)
  + 국가별 특화 5-10개
```

**전처리**:
- 중복 제거
- 결측치 처리
- 특성 정규화
- 학습/검증 분할 (80/20)

**산출물**: 8개국 × (train.parquet + test.parquet)

---

### 13.2: 모델 학습 (8일 → GPU로 5일)

**모델 구조**:
```
3개 모델 × 8개국 = 24개 모델 (+ 1개 글로벌 앙상블)

1) XGBoost (GPU boosting)
   ├─ tree_method: gpu_hist (CUDA 가속)
   ├─ 500 trees, max_depth=6
   └─ 학습시간: 5분 (GPU) vs 35분 (CPU) → 7배 가속

2) LightGBM (GPU accelerated)
   ├─ device_type: gpu
   ├─ 500 trees, num_leaves=31
   └─ 학습시간: 3분 (GPU) vs 25분 (CPU) → 8배 가속

3) Gradient Boosting (CPU baseline)
   ├─ 500 trees, max_depth=6
   └─ 학습시간: 40분 (CPU only)

앙상블: 0.4×XGBoost + 0.4×LightGBM + 0.2×GB
```

**GPU 병렬화**:
```
현재: CPU만 → 8일 (순차)
GPU: RTX 5050 → 5-6일 (병렬)
  └─ 각 국가 20분 → 5분

총 절감: 2-3일
```

**하이퍼파라미터 튜닝** (GridSearchCV + GPU):
```python
param_grid = {
    'max_depth': [5, 6, 7, 8],
    'learning_rate': [0.01, 0.03, 0.05, 0.1],
    'n_estimators': [300, 400, 500],
}
# 5-fold CV 자동 실행
```

---

### 13.3: 모델 검증 (5일)

**성능 지표** (목표):
```
UK:   R²>0.88, MAPE<8.5%
SG:   R²>0.85, MAPE<10%
JP:   R²>0.87, MAPE<9%
DE:   R²>0.86, MAPE<9.5%
AU:   R²>0.84, MAPE<11%
CA:   R²>0.85, MAPE<10.5%
TH:   R²>0.80, MAPE<13%
HK:   R²>0.83, MAPE<12%

Avg:  R²>0.84, MAPE<10.5%
```

**분석**:
- SHAP 특성 중요도
- Residual 분석 (Q-Q plot)
- 과적합 진단

---

### 13.4: 배포 & 자동화 (2일)

**FastAPI 엔드포인트**:
```python
@app.post("/predict")
def predict(country: str, properties: List[Dict]):
    # 앙상블 예측
    price = (
        0.4 * xgb.predict(X) +
        0.4 * lgb.predict(X) +
        0.2 * gb.predict(X)
    )
    return {"price": price, "confidence": 0.92}
```

**자동 재학습** (Cron):
```bash
# 매주 일요일 00:00
0 0 * * 0 /home/user/-/scripts/phase13_retraining.sh

# 스크립트:
# 1. 신규 거래 데이터 수집
# 2. 8개국 모델 재학습 (GPU)
# 3. 성능 검증
# 4. 결과 리포팅
```

---

## 3️⃣ 통합 로드맵

```
Phase 12:
├─ 12.H: PDF (1일)
├─ 12.I: 최종화 (1-2일)
└─ Deadline: 2026-06-28

Phase 13 (병렬 가능):
├─ 13.1: 데이터 수집 (5일, 2026-06-28 ~ 7-03)
├─ 13.2: 모델 학습 (5-8일, GPU 병렬, 2026-07-03 ~ 07-10)
├─ 13.3: 검증 (5일, 2026-07-10 ~ 07-15)
├─ 13.4: 배포 (2일, 2026-07-15 ~ 07-17)
└─ Deadline: 2026-07-18 (총 20일)

병렬 진행 시:
└─ Phase 12.H/I 중 데이터 수집 시작 → 2-3일 단축
```

---

## 4️⃣ 리소스 & 비용

| 항목 | Phase 12 | Phase 13 |
|------|---------|---------|
| CPU | 4 cores | 8 cores |
| GPU | - | RTX 5050 (필수) |
| 메모리 | 8GB | 16GB |
| 저장소 | 100GB | 500GB |
| 개발자 | 1명 | 1명 |
| 시간 | 40시간 | 140시간 |

**GPU 가속 ROI**:
- 투자: RTX 5050 (보유중)
- 절감: 2-3일 (약 16-24시간)
- 효과: 140시간 → 120시간 (14% 효율 증가)

---

## 5️⃣ 즉시 액션

```
내일 (2026-06-26):
[ ] Task 12.H: PDF 생성 코딩 (2시간)
[ ] Task 12.I: 검증 체크리스트 (1시간)
[ ] Phase 13.1 준비: API 엔드포인트 리스팅 (2시간)

이후 3일:
[ ] Phase 12 최종 완료 & 커밋
[ ] 데이터 수집 파이프라인 구현 시작
[ ] GPU 환경 테스트 (XGBoost/LightGBM)
```

---

**상태**: 준비 완료 ✓  
**다음 검토**: 2026-06-26
