# 모델 성능 진단 보고서
**작성일:** 2026-06-24  
**주제:** Decision Tree, Gradient Boosting, Linear Regression의 정확도 차이 분석  
**결론:** 3가지 모델의 성능 차이는 알고리즘 특성과 하이퍼파라미터의 차이에서 비롯됨

---

## 📊 Executive Summary

| 모델 | R² | RMSE | Gap | 상태 |
|------|-----|------|-----|------|
| **XGBoost (Reference)** | **0.9983** | **79.2M** | 0.00% | ✅ 최고 |
| **Decision Tree** | 0.9940 | 107.8M | 0.43% | ⚠️ 개선 가능 |
| **Gradient Boosting** | 0.9918 | 121.5M | 0.65% | ⚠️ 개선 가능 |
| **Linear Regression** | 0.7189 | 537.8M | 27.94% | ❌ 근본 한계 |

**핵심 발견:**
- Decision Tree + Gradient Boosting: 미미한 성능 차 (최대 0.65%)
- Linear Regression: 근본적인 모델 한계로 심각한 성능 격차 (27.94%)
- 모두 하이퍼파라미터 튜닝으로 개선 가능

---

## 🔍 상세 분석

### 1️⃣ LINEAR REGRESSION (R² = 0.7189)

#### 문제점

**❌ 1. 비선형 관계 학습 불가 (근본적 한계)**

부동산 가격은 **선형 함수가 아님**
```
실제 관계: price = f(area, floor, location, condition) [복잡한 비선형]
선형 모델: price = c₀ + c₁·area + c₂·floor + ...        [단순 일차식]
```

**증거:**
- Percentile별 오차 분석:
  - 0 percentile (저가): 오차 35.7M (12%)
  - 25 percentile: 오차 66.1M (10.9%)  
  - 50 percentile: 오차 92.0M (11.1%) ← 중간값도 11% 오류
  - 75 percentile: 오차 42.9M (3.7%)
  - 100 percentile: 오차 108.3M (6%)

→ 선형 모델은 모든 구간에서 일정한 오차 유지 (비선형 패턴 학습 못함)

**❌ 2. 이상치(Outliers)에 극도로 민감**

```
최대 잔차: 836.7M 원 (평균 872M의 96%)
표준편차: 187.4M 원 (매우 높음)
→ 극값 몇 개가 회귀선 전체를 왜곡
```

**❌ 3. Feature 상호작용(Interaction) 무시**

```
선형 모델 가정: 각 feature의 영향이 독립적
실제: area가 클수록 floor 수와의 상호작용 중요
      → 넓은 건물의 층수가 가격에 더 큰 영향
```

**❌ 4. Feature 비선형 변환 미적용**

```
미적용:
- log(price) → 우측 왜도 제거 못함
- sqrt(area) → 면적의 제곱근 효과 미포착
- polynomial features → 고차 관계 학습 불가
```

#### Feature 가중치 분석

```
회귀 계수 (상위 5개):
  area_sqm:     +7.44e+06  (가장 중요)
  total_floor:  +3.76e+05
  floor:        +3.67e+05
  year_built:   +2.18e+05
  age_years:    -2.18e+05
```

→ **선형 모델은 면적(area_sqm)에만 지나치게 의존**
→ 다른 feature들의 미세한 효과 포착 불가

#### 예상 개선

```
현재: R² = 0.7189
개선 후: R² = 0.78~0.85 (최대)

개선 방법:
1. Feature 변환
   - log1p(market_price)
   - sqrt(area_sqm)
   - Polynomial features (degree=2)

2. 정규화(Ridge/Lasso)
   - Ridge: alpha=0.1~1.0
   - Lasso: alpha=0.01~0.1

3. 이상치 제거
   - IQR 방식
   - Z-score > 3

⚠️ 여전히 0.99 달성 불가 (선형의 근본 한계)
```

---

### 2️⃣ GRADIENT BOOSTING (R² = 0.9918)

#### 성능 특성

```
R² = 0.9918 (우수)
RMSE = 121.5M (XGBoost 대비 1.5배)
평균 오차: 1.3M (거의 0, 균형 잡힘)
최대 오차: 171.7M (합리적)
```

#### 문제점

**⚠️ 1. 하이퍼파라미터 최적화 미흡**

```python
현재 설정:
GradientBoostingRegressor(
    n_estimators=100,          # 보통 수준
    learning_rate=0.1,         # 높은 편
    # max_depth 미설정 (기본값 3)
    # subsample 미설정 (기본값 1.0)
    # colsample_bytree 미설정
)

문제점:
- learning_rate=0.1: 너무 빨리 학습 → 수렴 부정확
- max_depth=3: 기본값으로 너무 얕음
- subsample=1.0: Stochastic boosting 미사용
```

**⚠️ 2. XGBoost 대비 알고리즘 차이**

```
표준 Gradient Boosting:
  ├─ 기본 그래디언트 부스팅
  ├─ 정규화 없음 (L1/L2)
  ├─ 병렬 처리 제한적
  └─ 느린 트리 생성

XGBoost (개선):
  ├─ 정규화 포함 (L1/L2) ✅
  ├─ 효율적 병렬 처리 ✅
  ├─ 캐싱, 블록 최적화 ✅
  └─ 더 빠르고 정확한 트리 생성 ✅

결과: R² 차이 0.0065 (0.65%)
```

**⚠️ 3. Feature Importance 편중**

```
상위 Feature:
  area_sqm:    55.36% (주도적)
  price_per_sqm: 44.14% (보조)
  floor:        0.19% (거의 무시)
  year_built:   0.15%
  age_years:    0.11%

→ 단 2개 feature가 99.5% 점유
→ 다른 17개 feature는 거의 쓸모 없음
```

#### 예상 개선

```
현재: R² = 0.9918
개선 후: R² = 0.9950~0.9970 (예상)

개선 방법:
1. Learning Rate 감소
   learning_rate: 0.1 → 0.05
   → 더 정교한 학습

2. 트리 수 증가
   n_estimators: 100 → 200~300
   → 더 많은 부스팅 라운드

3. Max Depth 증가
   max_depth: 3 (기본) → 5~7
   → 더 복잡한 트리 구조

4. Stochastic Boosting
   subsample: 0.8
   colsample_bytree: 0.8
   → 노이즈 저항성 증가

최적 파라미터 예시:
GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
```

---

### 3️⃣ DECISION TREE (R² = 0.9940)

#### 성능 특성

```
R² = 0.9940 (우수)
RMSE = 107.8M (GB 보다 좋음)
평균 오차: -413K (거의 0)
최대 오차: 200.5M (GB 보다 약간 높음)
```

**Decision Tree는 GB보다 성능이 더 좋음!** (R² 0.9940 > 0.9918)

#### 문제점

**⚠️ 1. Shallow Tree (얕은 트리)**

```python
현재:
DecisionTreeRegressor(
    max_depth=10,  # 제약 조건
    random_state=42
)

비교:
- Decision Tree: max_depth=10
- Random Forest: max_depth=15  ← 더 깊음
- XGBoost: adaptive (자동 결정) ← 최적 깊이

트리 깊이별 학습 능력:
  depth=5:   선형 근처 패턴만 학습
  depth=10:  중간 복잡도 패턴 학습 ✓
  depth=15:  높은 복잡도 패턴 학습 ✓✓
  depth=20:  매우 복잡한 패턴 (과적합 위험)
```

**⚠️ 2. Greedy Split 알고리즘의 한계**

```
각 노드에서 "현재 최적"만 선택
↓
전역 최적 구조 보장 안 됨
↓
특정 분할이 나중 단계의 최적성을 해칠 수 있음

예시:
  첫 번째 분할: area_sqm < 100 ✓ (국소 최적)
  하지만 이것이 3단계 후의 성능을 해칠 수 있음

해결책:
  Random Forest/Boosting: 여러 트리로 보완
  XGBoost: adaptive 알고리즘으로 개선
```

**⚠️ 3. 단일 트리의 한계**

```
Single Decision Tree:
  ├─ 1개 트리만 사용
  ├─ 오류가 누적 안 됨 (좋은 점)
  └─ 다양한 패턴 표현 못 함 (약점)

Ensemble (RF/GB):
  ├─ 여러 트리 결합 (장점)
  ├─ 각 트리의 오류 상쇄
  └─ 더 안정적 (낮은 분산)

증거 - Residuals:
  DT 최대 오차: 200.5M
  GB 최대 오차: 171.7M ← 앙상블이 더 나음
```

#### Feature Importance

```
상위:
  area_sqm:    57.66% (DT도 area에 의존)
  price_per_sqm: 41.96%
  floor:        0.19%

→ 패턴은 GB와 유사하지만,
  단일 트리이므로 세부 미묘함 포착 불가
```

#### 예상 개선

```
현재: R² = 0.9940
개선 후: R² = 0.9970 (예상) - RandomForest 수준

개선 방법:
1. 트리 깊이 증가
   max_depth: 10 → 15~20
   → 더 복잡한 분할 학습

2. 최소 샘플 수 조정
   min_samples_split: 2 → 5
   min_samples_leaf: 1 → 2
   → 과적합 방지

3. 앙상블로 전환
   DecisionTree → RandomForest
   n_estimators=100, max_depth=15
   → 여러 트리의 장점 활용

최적 파라미터 예시:
DecisionTreeRegressor(
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42
)

또는 더 나은 선택:
RandomForestRegressor(
    n_estimators=100,
    max_depth=15,
    min_samples_split=5,
    n_jobs=-1,
    random_state=42
)
→ 예상 R² = 0.9978 (현재 실제값)
```

---

## 📈 비교 분석: 왜 XGBoost가 최고인가?

### 성능 비교표

```
모델              R²      RMSE    특징
─────────────────────────────────────────────────
XGBoost      0.9983   79.2M    ⭐ 최고 성능
LightGBM     0.9981   80.1M    ⭐ 거의 동등
Random Forest 0.9978   81.8M    ✅ 매우 우수
Decision Tree 0.9940  107.8M    ✅ 우수 (개선 가능)
Grad Boost   0.9918  121.5M    ⚠️  우수 (개선 가능)
Linear Reg   0.7189  537.8M    ❌ 부적합
```

### XGBoost 우수성 이유

```python
1️⃣  정규화(Regularization)
    - L1/L2 정규화로 과적합 억제
    - 일반화 성능 향상
    
2️⃣  효율적 트리 생성
    - Weighted Quantile Sketch
    - Sparsity-aware split finding
    - 더 빠르고 정확한 분할 기준
    
3️⃣  병렬 처리 및 최적화
    - 캐싱 메커니즘
    - 블록 구조 최적화
    - GPU 가속 지원
    
4️⃣  손실 함수 유연성
    - 커스텀 손실 함수 지원
    - 계층적 손실 (focal loss 등)
    
5️⃣  Adaptive Learning
    - 각 트리가 적응적으로 깊이 결정
    - 데이터 특성에 맞는 최적 구조

결과: R² 0.9983 (최고 정확도)
```

---

## 🎯 최종 권장사항

### 프로덕션 배포 순위

**1순위: XGBoost (R² = 0.9983)** 🏆
```
✅ 최고 성능
✅ 가장 안정적
✅ 가장 빠른 추론
✅ 프로덕션 검증됨
```

**2순위: LightGBM (R² = 0.9981)**
```
✅ XGBoost와 거의 동등
✅ 더 빠른 학습
✅ 메모리 효율적
✅ 좋은 백업 모델
```

**3순위: Random Forest (R² = 0.9978)**
```
✅ 모델 해석가능성 우수
✅ 안정적
✅ 하이퍼파라미터 덜 민감
⚠️ 약간 느린 추론
```

### 회피 또는 개선 필요

**Decision Tree**: 개선 필요
```
현재: R² = 0.9940
개선: max_depth=15로 → R² 예상 0.9970
또는: RandomForest로 → R² 실제 0.9978
권장: RandomForest로 전환
```

**Gradient Boosting**: 개선 필요
```
현재: R² = 0.9918
개선: learning_rate=0.05, n_estimators=300
권장: XGBoost 사용 (더 나음)
```

**Linear Regression**: 폐기
```
현재: R² = 0.7189
문제: 근본적 모델 한계
결론: 부동산 가격 예측에 부적합
권장: 폐기 또는 교육용 모델로만 사용
```

---

## 📋 요약표

| 모델 | R² | 문제점 | 개선 가능성 | 권장 |
|------|-----|--------|----------|------|
| **Linear Reg** | 0.7189 | 근본적 한계 | 낮음 | ❌ 폐기 |
| **Grad Boost** | 0.9918 | 파라미터 최적화 부족 | 높음 | ⚠️ 개선 필요 |
| **Decision Tree** | 0.9940 | max_depth 제약 | 높음 | ⚠️ 개선 또는 RF |
| **XGBoost** | 0.9983 | 없음 | - | ✅ 배포 추천 |
| **LightGBM** | 0.9981 | 없음 | - | ✅ 백업 추천 |

---

**결론:** XGBoost (0.9983)와 LightGBM (0.9981)이 실무에 최적. Decision Tree와 Gradient Boosting은 0.65% 미만의 작은 차이로 모두 우수하지만, 하이퍼파라미터 최적화 시 더 향상 가능. Linear Regression은 비선형 데이터에 근본적으로 부적합하므로 폐기 권장.
