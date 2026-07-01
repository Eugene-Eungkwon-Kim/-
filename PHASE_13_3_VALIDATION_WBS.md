# Phase 13.3 WBS (Work Breakdown Structure)
## 모델 검증 & 성능 최적화

**기간**: 2026-07-15 ~ 2026-07-18 (4일, Week 3)  
**팀**: Claude Agent (1명)  
**주요 마일스톤**: CV 완료 (Day 2), 튜닝 완료 (Day 3), 최적 모델 선정 (Day 4)

---

## 1. 전체 작업 분해

```
Phase 13.3 (4일 × ~10h = 40시간)
│
├─ 1. 모델 로드 및 검증 (1h)
│  ├─ 1.1 pickle 모델 로드 (30min)
│  ├─ 1.2 모델 구조 검증 (20min)
│  └─ 1.3 Test set에서 기존 성능 재현 (10min)
│
├─ 2. 5-Fold Cross-Validation (6h)
│  ├─ 2.1 CV 설정 (30min)
│  ├─ 2.2 XGBoost 5-fold 실행 (2h)
│  ├─ 2.3 LightGBM 5-fold 실행 (2h)
│  ├─ 2.4 Gradient Boosting 5-fold 실행 (1h)
│  └─ 2.5 CV 결과 분석 및 통계 (30min)
│
├─ 3. 하이퍼파라미터 튜닝 (8h)
│  ├─ 3.1 GridSearch 설정 (1h)
│  ├─ 3.2 XGBoost 튜닝 (2h)
│  ├─ 3.3 LightGBM 튜닝 (2h)
│  ├─ 3.4 Gradient Boosting 튜닝 (1.5h)
│  ├─ 3.5 Best params 저장 및 모델 재학습 (1.5h)
│  └─ 3.6 튜닝 전후 비교 분석 (30min)
│
├─ 4. Feature Importance 분석 (6h)
│  ├─ 4.1 Built-in importance 추출 (2h)
│  ├─ 4.2 Permutation importance 계산 (2h)
│  ├─ 4.3 SHAP 분석 (1h)
│  └─ 4.4 시각화 (1h)
│
├─ 5. 최적 모델 선정 (2h)
│  ├─ 5.1 가중치 기반 스코링 (30min)
│  ├─ 5.2 최적 모델 확정 (30min)
│  ├─ 5.3 최종 모델 저장 (30min)
│  └─ 5.4 메타데이터 기록 (30min)
│
├─ 6. 보고서 작성 (12h)
│  ├─ 6.1 성능 비교표 작성 (2h)
│  ├─ 6.2 하이퍼파라미터 튜닝 이력 (2h)
│  ├─ 6.3 Feature importance 해석 (4h)
│  ├─ 6.4 SHAP 분석 보고 (2h)
│  ├─ 6.5 최종 권장사항 (1h)
│  └─ 6.6 마크다운 문서 생성 (1h)
│
└─ 7. QA 및 검증 (5h)
   ├─ 7.1 모든 결과 재검증 (2h)
   ├─ 7.2 통계 유의성 확인 (1h)
   ├─ 7.3 보고서 리뷰 (1.5h)
   └─ 7.4 Phase 13.4 준비 확인 (30min)
```

---

## 2. 일일 진행 계획

### Day 1 (2026-07-15): 모델 로드 & CV 설정

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   1.1 모델 로드                Claude  ✓      3개 pkl 로드
09:30   1.2 모델 검증                Claude  ✓      구조 확인
10:00   1.3 기존 성능 재현           Claude  ✓      R², MAPE, RMSE
10:30   Break (30min)
11:00   2.1 CV 설정                 Claude  ✓      TimeSeriesSplit 구성
12:00   2.2 XGBoost CV 실행          Claude  ⏳     Fold 1-2 완료 (50%)
13:00   Lunch (1h)
14:00   2.2 XGBoost CV 실행 (계속)   Claude  ⏳     Fold 3-5 완료
16:00   Daily Standup & Log
17:00   End of Day 1
```

**Day 1 산출물**:
- ✅ 3개 모델 구조 검증 완료
- ⏳ XGBoost 5-fold CV 진행 중 (예상 100% 다음날)
- 📊 기본 성능 기준선 설정

---

### Day 2 (2026-07-16): CV 완료 & 분석

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   2.2 XGBoost CV 완료          Claude  ✓      Fold 1-5 완료
10:00   2.3 LightGBM CV 실행         Claude  ⏳     ~2h (병렬)
12:00   2.4 GB CV 실행               Claude  ⏳     ~1h (CPU)
13:00   Lunch & CV 계속 진행
14:00   2.5 CV 결과 분석             Claude  ✓      mean ± std
15:00   CV 결과 테이블 작성          Claude  ✓      R², MAPE 비교
16:00   Daily Standup & Log
17:00   End of Day 2
```

**Day 2 산출물**:
- ✅ 5-fold CV 완료 (3개 모델)
- 📊 CV 결과 통계: mean, std, confidence interval
- 📋 성능 비교표 작성 (3개 모델 × 5 지표)

**Day 2 기대 결과**:
```
Model        R² Mean   R² Std    MAPE Mean   Notes
─────────────────────────────────────────────────
XGBoost      0.847     0.012     0.091       ✓
LightGBM     0.851     0.011     0.090       ✓ Best
Gradient B   0.835     0.018     0.104       ✓
```

---

### Day 3 (2026-07-17): 하이퍼파라미터 튜닝

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   3.1 GridSearch 설정          Claude  ✓      param_grid 정의
09:30   3.2 XGBoost GridSearch       Claude  ⏳     108 조합 (병렬)
11:30   3.3 LightGBM GridSearch      Claude  ⏳     81 조합 (병렬)
13:30   Lunch
14:30   3.4 GB GridSearch            Claude  ⏳     27 조합 (순차)
15:30   3.5 Best params 추출         Claude  ✓      각 모델 top 5
16:00   3.6 Before/After 비교        Claude  ✓      개선도 분석
17:00   Daily Standup & Log
17:30   End of Day 3
```

**Day 3 산출물**:
- ✅ GridSearch 완료 (3개 모델)
- 📊 Best hyperparameters 추출 (각 모델)
- 📈 튜닝 전후 성능 개선도 (예상 0.5-1.0%)
- 📋 하이퍼파라미터 튜닝 이력 표

**Day 3 기대 결과**:
```
Model        Before R²  After R²  Improvement  Best Params
────────────────────────────────────────────────────────
XGBoost      0.847      0.851     +0.4%       max_depth=8
LightGBM     0.851      0.853     +0.2%       num_leaves=31
Gradient B   0.835      0.839     +0.4%       n_est=250
```

---

### Day 4 (2026-07-18): Feature Importance & 최종 보고서

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   4.1 Built-in importance      Claude  ✓      3모델 상위 10
10:30   4.2 Permutation importance   Claude  ✓      순열 기반 중요도
12:00   Lunch
13:00   4.3 SHAP 분석                Claude  ✓      SHAP values
14:00   4.4 시각화 생성              Claude  ✓      3장 × 3모델
15:00   5.1 가중치 스코링            Claude  ✓      최적 모델 선정
15:30   5.2 최적 모델 확정           Claude  ✓      LightGBM (예상)
16:00   5.3-5.4 메타데이터 저장      Claude  ✓      모델 + 메타
16:30   6.1-6.6 보고서 작성          Claude  ✓      마크다운
17:00   7.1-7.4 QA & 검증            Claude  ✓      최종 확인
17:30   Daily Standup & Final Log
18:00   End of Day 4
```

**Day 4 산출물**:
- ✅ Feature Importance 분석 완료 (3가지 방법)
- 📊 Top 10 features × 3 모델
- 📈 시각화: bar chart, SHAP plot, cumulative curve
- 📋 최종 보고서: PHASE_13_3_VALIDATION_REPORT.md
- ✅ 최적 모델 선정 및 저장 완료
- ✅ Phase 13.4 진행 가능 확인

---

## 3. 작업 의존성 분석

```
Task Dependency Graph:

1.1 Model Load
    │
    ├─→ 1.2 Validation
    │    │
    │    └─→ 1.3 Baseline Performance
    │         │
    │         └─→ 2.1 CV Setup ──→ 2.2 XGBoost CV
    │                                    │
    │                                    ├─→ 2.3 LightGBM CV
    │                                    │     │
    │                                    │     └─→ 2.4 GB CV
    │                                    │          │
    │                                    └─────────→ 2.5 CV Analysis
    │                                                │
    └────────────────────────────────────────────────→ 3.1 GridSearch Setup
                                                     │
                                                     ├─→ 3.2 XGBoost Tune
                                                     ├─→ 3.3 LightGBM Tune
                                                     └─→ 3.4 GB Tune
                                                          │
                                                          └─→ 3.5 Best Params
                                                               │
                                                               └─→ 3.6 Compare
                                                                    │
                                                                    └─→ 4.1 Importance
                                                                         │
                                                                         ├─→ 4.2 Permutation
                                                                         ├─→ 4.3 SHAP
                                                                         └─→ 4.4 Visualize
                                                                              │
                                                                              └─→ 5.1 Score
                                                                                   │
                                                                                   ├─→ 5.2 Select
                                                                                   ├─→ 5.3 Save
                                                                                   └─→ 5.4 Metadata
                                                                                        │
                                                                                        └─→ 6.1-6.6 Report
                                                                                             │
                                                                                             └─→ 7.1-7.4 QA
```

**크리티컬 패스**: 1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 4.1 → 4.2 → 4.3 → 4.4 → 5.1 → 6.1 → 7.1

**병렬화 가능 작업**:
- 2.2 (XGBoost CV) + 2.3 (LightGBM CV): 2h 단축 가능 (Day 2)
- 3.2 (XGBoost) + 3.3 (LightGBM): 1h 단축 가능 (Day 3)
- 4.1 + 4.2 + 4.3: 1h 단축 가능 (Day 4)

---

## 4. 리소스 및 시간 할당

### 4.1 총 투입 시간

| 작업군 | 예상시간 | 실제시간* | 효율 |
|--------|---------|---------|------|
| **1. 모델 로드 & 검증** | 1h | - | - |
| **2. Cross-Validation** | 6h | - | - |
| **3. 하이퍼파라미터 튜닝** | 8h | - | - |
| **4. Feature Importance** | 6h | - | - |
| **5. 모델 선택** | 2h | - | - |
| **6. 보고서 작성** | 12h | - | - |
| **7. QA & 검증** | 5h | - | - |
| **TOTAL** | **40h** | **TBD** | **TBD** |

### 4.2 일일 시간표

```
Day 1 (Jul 15):  9h (모델 로드 + CV 설정 + XGBoost 50%)
Day 2 (Jul 16):  9h (CV 완료 + 분석)
Day 3 (Jul 17):  9h (하이퍼파라미터 튜닝 + 비교)
Day 4 (Jul 18):  9h (Feature analysis + Report + QA)
───────────────────
Total:          36h (병렬화 시 4시간 단축)
```

### 4.3 컴퓨팅 리소스

```
리소스            할당량          비용    비고
────────────────────────────────────────────
GPU (RTX 5050)    Day 2-3 활용   $0     5-fold × 3 모델
CPU (4 cores)     Day 2-4        $0     GB CV + 직렬 작업
메모리 (16GB)     8-10GB         $0     모델 + 데이터 로드
디스크            500MB          $0     결과 저장
────────────────────────────────────────────
Total:                          $0     로컬 리소스만 사용
```

---

## 5. 마일스톤 및 체크포인트

| 마일스톤 | 날짜 | 목표 | 성공기준 |
|---------|------|------|--------|
| **M1: 모델 로드** | Jul 15 09:00 | 3개 모델 검증 | 구조 확인, 기본 성능 재현 ✓ |
| **M2: CV 완료** | Jul 16 15:00 | 5-fold 검증 | R² mean ± std 기록, 3모델 모두 R²>0.83 ✓ |
| **M3: 튜닝 완료** | Jul 17 16:00 | 하이퍼파라미터 최적화 | GridSearch 완료, 개선도 0.2-0.5% ✓ |
| **M4: 최적 모델 선정** | Jul 18 15:30 | 최종 모델 확정 | LightGBM, R²>0.85, 저장 완료 ✓ |
| **M5: 보고서 완료** | Jul 18 17:00 | 문서화 | 마크다운 + 시각화 4장 ✓ |
| **M6: QA 통과** | Jul 18 18:00 | 검증 완료 | Phase 13.4 진행 가능 ✓ |

---

## 6. 위험 관리 및 대응

### 6.1 일정 위험

| 위험 | 확률 | 영향 | 대응책 |
|------|------|------|--------|
| GridSearch 시간 초과 | 20% | Day 3 밤샘 | Random search 전환 (100 샘플) |
| CV 성능 하락 | 15% | R²<0.84 달성 불가 | Early stopping 추가, regularization |
| SHAP 분석 오류 | 10% | Feature 해석 불가 | Permutation importance로 대체 |
| 메모리 부족 | 5% | 계산 중단 | Batch 처리, 데이터 샘플링 |

### 6.2 기술 위험

```
위험 1: Cross-validation 불안정
├─ 증상: fold마다 R² 편차 큼 (std > 0.03)
├─ 원인: 시계열 데이터 특성 + 이상치
└─ 대응:
   - 이상치 재확인 및 제거
   - TimeSeriesSplit 재조정
   - 별도 validation set 추가

위험 2: 모델 간 성능 차이 미미
├─ 증상: R² 모두 0.84-0.85 범위 (유의한 차이 없음)
├─ 원인: 특성 포화 또는 과적합
└─ 대응:
   - 특성 추가 엔지니어링 (45→60)
   - 앙상블 모델 고려
   - 다음 phase로 연기 검토
```

---

## 7. 커뮤니케이션 계획

### 7.1 일일 보고

```
Daily Standup (16:00-16:15)
├─ 완료한 작업
├─ 예상 블로커
└─ 다음날 계획

Weekly Review (매주 금요일)
├─ Phase 진행률
├─ 주요 성과물
└─ 다음 Phase 준비상태
```

### 7.2 최종 산출물

```
Phase 13.3 Complete Deliverables:
├── models/best_model_kr.pkl (최적 모델)
├── models/models_cv_results.json (CV 결과)
├── models/models_metadata.json (메타데이터)
├── output/PHASE_13_3_VALIDATION_REPORT.md (성능 보고서)
├── output/CV_Performance_Comparison.csv (비교표)
└── output/Feature_Importance_Plots.png (시각화)
```

---

## 8. Phase 13.4 이행조건

```
Phase 13.3 완료 조건 (모두 만족해야 13.4 시작):
✅ 최적 모델 R² > 0.84
✅ MAPE < 10.5%
✅ Top 10 features 분석 완료
✅ SHAP 해석가능성 > 0.95
✅ best_model_kr.pkl 저장 완료
✅ 모든 메타데이터 기록
└─→ Phase 13.4 (NPU 배포) 시작 가능
```

---

**WBS 완성**  
**총 프로젝트 기간**: 4일 (36-40시간)  
**예상 완료**: 2026-07-18 18:00
