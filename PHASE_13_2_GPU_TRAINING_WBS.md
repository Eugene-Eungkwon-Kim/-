# Phase 13.2 상세 WBS
## GPU 모델 학습 파이프라인 — 작업 분해 구조

**프로젝트**: Loan4U AVM Phase 13.2  
**기간**: 2026-07-08 ~ 2026-07-14 (7일, Week 2)  
**팀**: Claude Agent (ML)  
**총 투입시간**: 50h (1명주)

---

## 📋 WBS 계층 구조

```
Phase 13.2 (0)
├─ 13.2.1 데이터 준비 & 검증 (4h)
├─ 13.2.2 특성 엔지니어링 (15h)
│   ├─ 13.2.2.1 Base 10 features
│   ├─ 13.2.2.2 Temporal 4 features
│   ├─ 13.2.2.3 Location 6 features
│   ├─ 13.2.2.4 Market 3 features
│   ├─ 13.2.2.5 Categorical 12 features
│   ├─ 13.2.2.6 Interaction 10 features
│   └─ 13.2.2.7 정규화 & 검증
├─ 13.2.3 GPU 모델 학습 (20h)
│   ├─ 13.2.3.1 XGBoost 학습 & 튜닝 (8h)
│   ├─ 13.2.3.2 LightGBM 학습 & 튜닝 (8h)
│   └─ 13.2.3.3 Gradient Boosting 학습 (4h)
├─ 13.2.4 모델 검증 & 최적화 (15h)
│   ├─ 13.2.4.1 성능 평가 (3h)
│   ├─ 13.2.4.2 5-fold Cross-validation (4h)
│   ├─ 13.2.4.3 하이퍼파라미터 재튜닝 (5h)
│   └─ 13.2.4.4 Feature importance 분석 (3h)
└─ 13.2.5 최종화 & 보고 (6h)
    ├─ 13.2.5.1 최적 모델 선정
    ├─ 13.2.5.2 성능 보고서 작성
    └─ 13.2.5.3 모델 저장 & 문서화
```

---

## 📅 Week 2 상세 일정

### Day 1-2 (Jul 8-9): 특성 엔지니어링

#### Task 13.2.1: 데이터 준비 & 검증

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.2.1.1 | Phase 13.1 output 로드 | kr_validated.parquet 읽기 | 1h | 13.1 완료 | Agent | 🟡 대기 |
| 13.2.1.2 | 데이터 프로파일링 | 통계 분석 (min/max/mean/std) | 1h | 13.2.1.1 | Agent | 🟡 대기 |
| 13.2.1.3 | Train/Test 검증 | 시간순 split 검증 (40K/10K) | 1h | 13.2.1.2 | Agent | 🟡 대기 |
| 13.2.1.4 | 기본 10 특성 추출 | area_sqm, old_price, lat, lon 등 | 1h | 13.2.1.3 | Agent | 🟡 대기 |
| **소계** | | | **4h** | | | |

**Output**: X_train (40K×10), X_test (10K×10), 기본 특성 검증 완료

#### Task 13.2.2: 특성 엔지니어링 (45개로 확대)

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.2.2.1 | Temporal features (4) | 거래년도, 월, 분기, 건물나이² | 2h | 13.2.1.4 | Agent | 🟡 대기 |
| 13.2.2.2 | Location features (6) | K-means clustering, 거리 인코딩 | 3h | 13.2.2.1 | Agent | 🟡 대기 |
| 13.2.2.3 | Market features (3) | 지역별 월평균가, 가격추이, 물량 | 2h | 13.2.2.2 | Agent | 🟡 대기 |
| 13.2.2.4 | Categorical (12) | One-hot (용도), target encoding (지역) | 3h | 13.2.2.3 | Agent | 🟡 대기 |
| 13.2.2.5 | Interaction (10) | 면적×나이, 나이², 면적×위도 등 | 2h | 13.2.2.4 | Agent | 🟡 대기 |
| 13.2.2.6 | Standardization | StandardScaler (fit train, transform test) | 2h | 13.2.2.5 | Agent | 🟡 대기 |
| 13.2.2.7 | 특성 검증 & QA | 45 features 확인, 이상치 재검사 | 1h | 13.2.2.6 | Agent | 🟡 대기 |
| **소계** | | **45 features** | **15h** | | | |

**Output**: X_train (40K×45), X_test (10K×45), 정규화 완료, feature_names.txt

---

### Day 3-4 (Jul 10-11): GPU 모델 학습

#### Task 13.2.3: 3개 모델 동시 학습

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|-----|------|
| 13.2.3.1a | XGBoost 설정 | 하이퍼파라미터 초기화 (max_depth=8, lr=0.05) | 1h | 13.2.2.7 | Agent | 🟡 대기 |
| 13.2.3.1b | XGBoost 학습 | GPU 학습 실행 (15분 예상) | 6h | 13.2.3.1a | Agent | 🟡 대기 |
| 13.2.3.1c | XGBoost 검증 & 저장 | R², MAPE 기록, JSON 저장 | 1h | 13.2.3.1b | Agent | 🟡 대기 |
| 13.2.3.2a | LightGBM 설정 | 하이퍼파라미터 초기화 (num_leaves=31, lr=0.05) | 1h | 13.2.2.7 | Agent | 🟡 대기 |
| 13.2.3.2b | LightGBM 학습 | GPU 학습 실행 (8분 예상) ⚡ | 6h | 13.2.3.2a | Agent | 🟡 대기 |
| 13.2.3.2c | LightGBM 검증 & 저장 | R², MAPE 기록, txt 저장 | 1h | 13.2.3.2b | Agent | 🟡 대기 |
| 13.2.3.3a | GB 설정 | 하이퍼파라미터 초기화 (n_estimators=200) | 1h | 13.2.2.7 | Agent | 🟡 대기 |
| 13.2.3.3b | GB 학습 | CPU 학습 실행 (30분 예상) | 3h | 13.2.3.3a | Agent | 🟡 대기 |
| 13.2.3.3c | GB 검증 & 저장 | R², MAPE 기록, pkl 저장 | 1h | 13.2.3.3b | Agent | 🟡 대기 |
| **소계** | | **3 models** | **20h** | | | |

**병렬화 가능**: 13.2.3.1 / 13.2.3.2 / 13.2.3.3는 독립적 (→ 8h로 축약 가능)

**Output**: 
- xgboost_kr.json (100-150 MB)
- lightgbm_kr.txt (50-80 MB)
- gradient_boosting_kr.pkl (150-200 MB)
- models_comparison.csv

---

### Day 5-6 (Jul 12-13): 검증 & 최적화

#### Task 13.2.4: 성능 검증 & 최적화

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|--:|------|
| 13.2.4.1a | R²/MAPE/RMSE 계산 | 3개 모델 평가 지표 산출 | 1h | 13.2.3.3c | Agent | 🟡 대기 |
| 13.2.4.1b | 성능 비교표 작성 | 3개 모델 나열, 최적 모델 선정 | 1h | 13.2.4.1a | Agent | 🟡 대기 |
| 13.2.4.1c | 성능 분석 | 모델별 강점/약점 분석 | 1h | 13.2.4.1b | Agent | 🟡 대기 |
| 13.2.4.2a | 5-fold CV 설정 | TimeSeriesSplit 구성 | 1h | 13.2.3.3c | Agent | 🟡 대기 |
| 13.2.4.2b | CV 학습 & 평가 | 3개 모델 각 5회 학습 | 3h | 13.2.4.2a | Agent | 🟡 대기 |
| 13.2.4.2c | CV 결과 분석 | 평균 & 표준편차 보고 | 1h | 13.2.4.2b | Agent | 🟡 대기 |
| 13.2.4.3a | 하이퍼파라미터 재튜닝 | GridSearch / RandomSearch | 3h | 13.2.4.1a | Agent | 🟡 대기 |
| 13.2.4.3b | 재튜닝 모델 학습 | 상위 5개 조합 테스트 | 1h | 13.2.4.3a | Agent | 🟡 대기 |
| 13.2.4.3c | 재튜닝 결과 평가 | 개선 여부 판단 | 1h | 13.2.4.3b | Agent | 🟡 대기 |
| 13.2.4.4a | Feature importance 추출 | 45개 특성 중요도 계산 | 2h | 13.2.3.2c | Agent | 🟡 대기 |
| 13.2.4.4b | Top 10 특성 시각화 | 막대 그래프 + 테이블 | 1h | 13.2.4.4a | Agent | 🟡 대기 |
| **소계** | | **최적 모델 선정** | **15h** | | | |

**Output**: 성능 보고서, Top 10 features, CV 결과, 하이퍼파라미터 이력

---

### Day 7 (Jul 14): 최종화 & 보고

#### Task 13.2.5: 최종화 & 문서화

| ID | 태스크 | 설명 | 시간 | 선행 | 담당 | 상태 |
|-------|--------|------|------|------|--:|------|
| 13.2.5.1 | 최적 모델 선정 | R² 최고 + MAPE 최저 기준 | 1h | 13.2.4.3c | Agent | 🟡 대기 |
| 13.2.5.2a | 모델 재검증 | 최적 모델 최종 성능 확인 | 1h | 13.2.5.1 | Agent | 🟡 대기 |
| 13.2.5.2b | 메타데이터 생성 | best_model_metadata.json | 1h | 13.2.5.2a | Agent | 🟡 대기 |
| 13.2.5.3 | 모델 파일 확인 | 저장 경로, 파일 크기 검증 | 1h | 13.2.5.2b | Agent | 🟡 대기 |
| 13.2.5.4 | 성능 최종 보고서 | Phase 13.2 완료 리포트 | 1h | 13.2.5.3 | Agent | 🟡 대기 |
| 13.2.5.5 | Phase 13.3 준비 | 데이터 준비 상태 확인 | 1h | 13.2.5.4 | Agent | 🟡 대기 |
| **소계** | | **Ready for Phase 13.3** | **6h** | | | |

**Output**: 최종 성능 보고서, 메타데이터, 모델 파일 확인

---

## ⏱️ 전체 일정 (Gantt View)

```
Day 1 (Jul 8):  특성공학 Day 1 ███ [8h, ~40% 완료]
Day 2 (Jul 9):  특성공학 Day 2 ███ [8h, 마무리+검증]
Day 3 (Jul 10): GPU 학습 Day 1 (XGBoost/LightGBM) ███ [10h 병렬]
Day 4 (Jul 11): GPU 학습 Day 2 (GB + 평가) ██ [10h]
Day 5 (Jul 12): 검증 Day 1 (CV + 재튜닝) ██ [8h]
Day 6 (Jul 13): 검증 Day 2 (Feature imp.) ██ [7h]
Day 7 (Jul 14): 최종화 & 보고 █ [6h]

Total: 50h (1명주)
병렬화 시: 40h (6일)

Critical Path: 13.2.2.7 → 13.2.3 → 13.2.4 → 13.2.5
```

---

## 👥 역할 분담 (RACI)

| Task | Agent | User | QA | 상태 |
|------|-------|------|-----|------|
| 13.2.1 (데이터 준비) | **Accountable** | Approves | Validates | 🟡 Ready |
| 13.2.2 (특성공학) | **Accountable** | Consults | Validates | 🟡 Ready |
| 13.2.3 (GPU 학습) | **Accountable** | Monitors | Validates | 🟡 Ready |
| 13.2.4 (검증) | **Accountable** | Approves | **QA Lead** | 🟡 Ready |
| 13.2.5 (최종화) | **Accountable** | Reviews | **QA Lead** | 🟡 Ready |

---

## 🎯 의존성 그래프

```
Start
  │
  └─ 13.2.1 (데이터 준비) ──┐
                            │
                            ├─ 13.2.2 (특성공학) ──┐
                            │                     │
                            ├─ 13.2.3a (XGBoost) ─┤
                            │                     ├─ 13.2.4 (검증) ─── 13.2.5 (최종화) ──→ End
                            ├─ 13.2.3b (LightGBM) ┤
                            │                     │
                            └─ 13.2.3c (GB) ──────┘
                            [병렬 가능]

Critical Path Duration: 50h sequential → 40h parallelized (Day 7 finish)
```

---

## ⚠️ 위험 & 완화

| 위험 | 확률 | 영향 | 완화책 |
|------|------|------|--------|
| GPU 메모리 부족 | 25% | Day 3 정지 | 배치 축소, feature select |
| CV 시간 초과 | 15% | Day 5-6 연장 | 3-fold로 축약 (CV는 검증용) |
| 모델 성능 미달 (R²<0.80) | 15% | Day 6 확대 | 재튜닝 2-3일 추가 투자 |

---

## ✅ 성공 기준 (Acceptance Criteria)

### Phase 13.2.2 (특성공학)
- [ ] 45개 특성 생성 완료
- [ ] 정규화 (StandardScaler) 적용
- [ ] Train/Test (40K/10K) 분할 검증

### Phase 13.2.3 (학습)
- [ ] 3개 모델 학습 완료
- [ ] 각 모델 저장 (pkl/json/txt)

### Phase 13.2.4 (검증)
- [ ] **R² > 0.84 달성** ✅
- [ ] **MAPE < 10.5% 달성** ✅
- [ ] CV 결과 기록
- [ ] Top 10 특성 추출

### Phase 13.2.5 (최종화)
- [ ] 최적 모델 선정 (LightGBM 예상)
- [ ] 메타데이터 저장
- [ ] 성능 보고서 작성
- [ ] Phase 13.3 준비 확인

---

**문서 버전**: 1.0  
**작성일**: 2026-07-01  
**최종 검토**: TBD (사용자 승인 대기)  
**상태**: 🟡 검토 대기
