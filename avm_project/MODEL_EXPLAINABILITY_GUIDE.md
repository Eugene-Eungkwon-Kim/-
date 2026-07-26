# 🔬 SHAP 기반 모델 설명성 가이드

**상태**: ✅ 완성 및 테스트 (2026-06-17)  
**기술**: SHAP (SHapley Additive exPlanations) TreeExplainer  
**목적**: 모델의 의사결정 과정을 해석하고 특성별 기여도 분석

---

## 📋 목차

1. [개요](#개요)
2. [기본 사용법](#기본-사용법)
3. [분석 항목](#분석-항목)
4. [해석 방법](#해석-방법)
5. [고급 활용](#고급-활용)
6. [트러블슈팅](#트러블슈팅)

---

## 개요

### SHAP란?

**SHAP** (SHapley Additive exPlanations)는 게임 이론 기반의 모델 해석 방법으로:

- **개별 예측 설명**: 단일 샘플에 대해 각 특성이 예측값에 얼마나 기여했는지 정량화
- **전역 특성 중요도**: 모든 샘플에 대한 평균 기여도로 특성의 전체 중요도 파악
- **모델-무관성**: 모든 유형의 모델(선형, 트리, 신경망 등)에 적용 가능
- **수학적 근거**: Shapley 값으로 보장된 공정성과 일관성

### 왜 필요한가?

| 상황 | SHAP의 역할 |
|------|----------|
| 높은 예측값이 나온 이유 | 각 특성의 개별 영향도 정량화 |
| 모델이 어떤 패턴을 학습했나 | 특성-예측값 관계 시각화 |
| 특정 특성이 중요한가 | Mean Absolute SHAP으로 순위 판정 |
| 모델 의사결정이 타당한가 | 예측 과정의 투명성 제공 |

---

## 기본 사용법

### 🚀 실행 방법

```bash
# 기본 실행 (프로덕션 모델 사용)
python3 scripts/model_explainability.py

# 또는 특정 데이터로 실행
python3 scripts/model_explainability.py --data data/processed/sample.csv
```

### 📊 샘플 실행 결과

```
================================================================================
🚀 SHAP 기반 모델 설명성 분석
================================================================================
📥 모델 로드
   ✅ 로드: production_model.joblib

📊 데이터 로드
   ✅ 샘플 생성: 500 × 19

[Step 1/4] 전역 특성 중요도
======================================================================
   계산 중... (샘플: 500개)

📊 상위 10개 특성 (SHAP 영향도)
   1. Feature_16: 451851385.48
   2. Feature_0: 306333703.22
   3. Feature_18: 254543594.91
   4. Feature_9: 220336344.43
   5. Feature_17: 165120208.37
   ...

[Step 2/4] 개별 예측 설명
======================================================================

🔍 샘플 #0 예측
   예측값: 372538750.88
   
   상위 5개 영향 특성:
     ↓ Feature_16: -1.0128 (SHAP: -672190654.12)
     ↓ Feature_8: -0.4695 (SHAP: -73838248.75)
     ↑ Feature_11: -0.4657 (SHAP: 60971059.33)
     ↑ Feature_10: -0.4634 (SHAP: 45286693.65)
     ↓ Feature_7: 0.7674 (SHAP: -37155988.08)
```

---

## 분석 항목

### 1️⃣ 전역 특성 중요도 (Global Feature Importance)

**목적**: 모든 샘플에 대한 평균 기여도로 특성의 전체 중요도 파악

**계산 방법**: Mean Absolute SHAP
```
특성 중요도 = |SHAP 값|의 평균
```

**해석**:
```
Feature_16: 451,851,385 ← 가장 중요 (예측에 가장 많은 영향)
Feature_0:  306,333,703 ← 두 번째 중요
Feature_18: 254,543,595 ← 세 번째 중요
...
```

**활용**:
- 모델이 배운 주요 패턴 파악
- 특성 선택 및 제거 결정
- 비즈니스 인사이트 도출

---

### 2️⃣ 개별 예측 설명 (Individual Prediction Explanation)

**목적**: 단일 샘플의 예측값이 어떻게 구성되었는지 설명

**핵심 정보**:
```json
{
  "sample_idx": 0,
  "prediction": 372538750.88,
  "top_contributing_features": [
    {
      "feature": "Feature_16",
      "shap_value": -672190654.12,      // 특성이 예측을 얼마나 변화시켰나
      "feature_value": -1.0128            // 해당 샘플의 특성값
    },
    ...
  ]
}
```

**해석 방법**:
1. `shap_value > 0` → 예측값을 높임 (↑)
2. `shap_value < 0` → 예측값을 낮춤 (↓)
3. 절댓값이 클수록 영향도가 큼

**예시**:
```
Feature_16 = -1.0128 → SHAP: -672,190,654 (큰 음수)
→ 이 특성의 낮은 값이 예측을 크게 낮혔음
→ 따라서 최종 예측이 (기본값) - (672M) = (낮은 값)

Feature_11 = -0.4657 → SHAP: +60,971,059 (양수)
→ 이 특성이 예측을 올려주는 방향으로 기여
→ 특성-SHAP 관계가 비선형일 가능성
```

---

### 3️⃣ 특성 의존도 분석 (Feature Dependence Analysis)

**목적**: 특성값과 SHAP 값의 관계 파악 (비선형성 확인)

**통계**:
```
특성값 범위: [-2.8723, 3.8527]
SHAP값 범위: [-631,799,119, 302,613,515]
상관도: 0.8122 (강한 양의 관계)
```

**해석**:
| 상관도 | 의미 |
|-------|------|
| > 0.5 | 강한 선형 관계 (단순 의존성) |
| 0.3-0.5 | 중간 관계 |
| < 0.3 | 약한 관계 (비선형) |
| NaN | 특성이 예측에 영향 없음 |

**예시**:
```
Feature_0 상관도 = 0.8122
→ 특성값이 높을수록 SHAP 값도 높음
→ 선형에 가까운 관계
→ 모델의 의사결정 과정이 해석하기 쉬움
```

---

### 4️⃣ 모델 의사결정 경로 (Decision Path)

**목적**: 예측값이 모델의 기본값(base value)에서 어떻게 변했는지 추적

**구조**:
```
Base Value (모델 기본값)
      ↓
  + 특성 1 기여도
  + 특성 2 기여도
  - 특성 3 기여도
      ↓
Final Prediction (최종 예측값)
```

**예시**:
```
Base Value: 1,491,267,335
+ Feature 기여도 합: -666,891,824
= Final Prediction: 824,375,511

(기본 수준에서 666M을 뺀 결과)
```

---

## 해석 방법

### 📊 실제 예시

#### Case 1: 특성이 예측을 크게 낮추는 경우

```
Feature_16 = -1.0128
SHAP = -672,190,654

해석:
├─ Feature_16의 값이 매우 낮음 (-1.0128)
├─ 이로 인해 예측값이 672M 감소
├─ 즉, 이 특성의 낮은 값이 낮은 예측을 유도
└─ 모델이 "Feature_16이 낮으면 결과도 낮다"고 학습함
```

#### Case 2: 특성이 예측을 높이는 경우

```
Feature_11 = -0.4657
SHAP = +60,971,059

해석:
├─ Feature_11의 값이 낮음 (-0.4657)
├─ 하지만 예측값은 61M 증가
├─ 즉, 이 특성의 낮은 값이 높은 예측을 유도
└─ 모델이 "Feature_11이 낮을수록 결과는 높다"고 학습함
```

### 🎯 의사결정 기준

```
1. 절댓값 순으로 정렬 → 가장 영향 있는 특성 파악
2. 부호 확인 → 예측을 높이거나 낮추는 방향
3. 상관도 확인 → 특성-SHAP 관계가 선형인지 비선형인지
4. 비즈니스 검증 → 모델의 의사결정이 합리적인지 확인
```

---

## 고급 활용

### 1️⃣ 모델 신뢰성 검증

```python
# SHAP 리포트 로드
import json
with open('output/model_explainability_*.json') as f:
    report = json.load(f)

# 상위 특성 추출
top_features = report['insights']['top_3_features']
print(f"모델의 주요 판단 기준: {top_features}")

# 비즈니스 검증
if all(feat in EXPECTED_FEATURES for feat in top_features):
    print("✅ 모델이 올바른 특성을 학습함")
else:
    print("⚠️  의외의 특성이 중요함 - 데이터 누수 확인 필요")
```

### 2️⃣ 예측값 설명 자동화

```python
def explain_prediction(sample_idx=0):
    with open('output/model_explainability_*.json') as f:
        report = json.load(f)
    
    explanation = report['individual_explanation']
    prediction = explanation['prediction']
    
    print(f"예측값: {prediction:,.2f}")
    print("\n주요 영향 특성:")
    
    for feat_data in explanation['top_contributing_features'][:3]:
        feat = feat_data['feature']
        shap_val = feat_data['shap_value']
        direction = "↑ 증가" if shap_val > 0 else "↓ 감소"
        print(f"  {direction}: {feat} ({shap_val:,.0f})")
```

### 3️⃣ 특성별 영향도 프로파일

```python
# 모든 특성의 SHAP 값 분포 분석
def analyze_feature_profiles():
    with open('output/model_explainability_*.json') as f:
        report = json.load(f)
    
    importance = report['global_importance']['mean_abs_shap']
    
    # 상위 10개 특성별 영향도 분포
    top_10 = sorted(importance.items(), 
                    key=lambda x: x[1], 
                    reverse=True)[:10]
    
    for feat, imp in top_10:
        bar = "█" * int(imp / 10000000)
        print(f"{feat:12} {bar} {imp:,.0f}")
```

---

## 트러블슈팅

### Q: "ModuleNotFoundError: No module named 'shap'"

**해결책**:
```bash
pip install shap
# 또는
pip install -r requirements.txt
```

### Q: SHAP 값이 모두 0 또는 NaN

**원인**: 특성이 예측에 영향을 주지 않음  
**해결책**:
```bash
# 1. 특성 검증 (누락/중복/상수값 확인)
python3 -c "
import pandas as pd
df = pd.read_csv('data/processed/data.csv')
print(df.isnull().sum())
print(df.nunique())
"

# 2. 모델 재학습 (더 나은 특성으로)
python3 scripts/phase4_model_optimization.py
```

### Q: 실행이 너무 느림

**최적화**:
```python
# KernelExplainer 대신 TreeExplainer 사용 (현재 기본값)
# 필요시 샘플 크기 축소
X_subset = X[:100]  # 처음 100개만 분석
```

### Q: 의존도 상관도가 이상함

**검증**:
```bash
# 특성의 정규화 상태 확인
python3 -c "
import pandas as pd
df = pd.read_csv('data/processed/data.csv')
print(df.describe())
"
# → mean과 std가 0과 1에 가까워야 함
```

---

## 📈 출력 파일

### model_explainability_*.json 구조

```json
{
  "timestamp": "2026-06-17T06:35:34",
  "model_type": "Pipeline",
  "explainer_type": "SHAP TreeExplainer",
  
  "global_importance": {
    "total_features": 19,
    "top_features": {...},
    "mean_abs_shap": {...}
  },
  
  "individual_explanation": {
    "sample_idx": 0,
    "prediction": 372538750.88,
    "top_contributing_features": [...]
  },
  
  "dependence_analysis": {
    "feature_name": "Feature_0",
    "correlation": 0.8122,
    ...
  },
  
  "decision_path": {
    "base_value": 1491267335.38,
    "total_contribution": -666891823.91,
    "final_prediction": 824375511.47
  },
  
  "insights": {
    "top_3_features": ["Feature_16", "Feature_0", "Feature_18"]
  }
}
```

---

## 🔗 연관 파일

- `scripts/model_explainability.py` - SHAP 분석 구현
- `scripts/auto_retraining.py` - 주간 자동 재학습
- `scripts/api_server.py` - REST API (설명성 엔드포인트 확장 가능)
- `output/model_explainability_*.json` - 분석 결과

---

## ✅ 체크리스트

### 모델 해석 전
- [ ] 모델이 학습되어 저장됨
- [ ] shap 패키지 설치됨
- [ ] 데이터 정규화 확인

### 분석 후
- [ ] 상위 3개 특성이 비즈니스 관점에서 합리적인가?
- [ ] 강한 상관도(>0.5)의 특성들이 선형 관계를 보이는가?
- [ ] 예측값의 기본값(base value)과 최종값의 차이가 설명되는가?
- [ ] 이상한 특성(음수 SHAP인데 양수 특성값 등)이 있는가?

---

**마지막 업데이트**: 2026-06-17  
**상태**: ✅ 완성 및 테스트 완료  
**다음 단계**: 대시보드에 SHAP 시각화 통합 (선택사항)
