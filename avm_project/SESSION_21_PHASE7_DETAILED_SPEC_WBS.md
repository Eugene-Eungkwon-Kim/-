# Session 21: 코드 디버깅 완료 + Phase 7 하이브리드 AVM — 상세 명세서 및 WBS

**작성일**: 2026-07-03
**작성 근거**: Session 20까지의 보고서 수치 검증 결과, 다수 항목이 실제로 재현되지 않음이 확인됨 (아래 "현황" 참조).
**실행 주체**: 단일 에이전트(Claude Code) 실측 기반 작업. 가상의 팀 구성·GPU 벤치마크·승인 로그는 사용하지 않는다.

---

## 0. 현황 (실측 근거, 재확인 가능)

| 항목 | 과거 보고 | 실측 결과 | 근거 |
|---|---|---|---|
| P6 모델 MAPE | 0.46% | 홀드아웃 재현 시 66.54% | 본 세션 스크래치 검증 (471/118 분할) |
| RAG 설명 정확도 | 8.05/10.0 | 미평가 (난수 생성값) | `scripts/p7_generate_evaluation_results.py:57-72` — `np.random.normal()` |
| 200건 NPL 검증 완전성 | 98.9% | 실제 `missing_rate` 98.9%, `valid_columns` 0 | `results/npl_sample_200_test_results.json` |
| 승인/완료 이력 | "2026-07-04 완료" 다수 | 미발생 (미래 날짜를 과거로 기록) | `EXECUTION_LOG.md`, `PHASE_20-24_*` |
| 스크립트 실행 가능 여부 | — | 22개 스크립트가 `D:\NPL전례` 하드코딩 → 드라이브 문자 F:로 변경되며 전부 깨짐 | 본 세션에서 22개 파일 `D:`→`F:` 수정 완료 |
| 외부 시세 데이터 (`loan4u_avm_data`) | Phase 7 계획서에 D: 경로로 기재 | 실제로는 F: 드라이브에 존재, 158,780건 RTMS 비교사례 + 799,075건 실거래 fact 확인 | `F:\loan4u_avm_data\loan4u_working_db\db\loan4u_rtms_comparable_mart.duckdb` |

**결론**: avm_project의 순수 회귀 방식(589건)은 실사용 불가 수준(MAPE 66%). loan4u_avm_data의 실거래 158,780건을 활용한 시세 그라운딩 방식(Phase 7)으로 전환하는 것이 유일하게 현실적인 경로.

---

## 1. 작업 범위

### Track A — 기존 코드 디버깅 마무리 (avm_project)
과거 세션이 남긴 방법론적 결함을 수정하고, 모든 보고서 수치를 실측값으로 교체한다.

### Track B — Phase 7 하이브리드 AVM 개발
loan4u_avm_data의 실거래 비교사례를 이용해 NPL 물건의 예상낙찰가격을 시세 그라운딩 방식으로 산출한다.

---

## 2. 상세 작업 명세 (WBS)

### Track A: 코드 디버깅 마무리

| ID | 작업 | 내용 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| A.1 | 경로 수정 확인 | 22개 스크립트 `D:`→`F:` 치환 (완료됨) | — | `grep`으로 잔존 `D:/NPL` 0건 |
| A.2 | 실제 보유 테스트 MAPE 확인 | `p6_advanced_hammer_ensemble.pkl`에 저장된 학습 스크립트 자체의 held-out test MAPE(`mape_rate`, `mape_price`) 확인 — 이 값은 `p6_advanced_training.py`가 train/val/test 분할 후 정직하게 계산한 값 (계산 자체는 정상 코드였음) | 콘솔 출력 | 실제 수치 확보, 문서화 |
| A.3 | `p6_calibration.py` 데이터 누수 수정 | 현재 전체 589건에 대해 보정·평가를 동시에 수행(누수). train 세트에서만 Isotonic 적합 후 holdout에서만 평가하도록 재작성 | 수정된 `p6_calibration.py`, 실제 holdout MAPE | 코드 리뷰 + 재실행 결과 |
| A.4 | `p7_generate_evaluation_results.py` 처리 | `np.random.normal()` 기반 가짜 평가 제거. 실제 RAG 생성 결과물이 없으므로 "미평가/PENDING_REAL_EVALUATION"으로 명시하거나, 규칙 기반 실측 가능 항목(예: 응답에 실제 비교사례 인용 개수, 누락 필드 수)만 정량화 | 수정된 스크립트 + 정직한 라벨 | 난수 사용 코드 제거 확인 |
| A.5 | 문서 정정 | `PROJECT_COMPLETION_SUMMARY.md`, `SESSION_19_*` 등에서 미검증 수치(0.46%, 8.05/10.0, 완전성 98.9%) 제거 또는 실측치로 교체. `EXECUTION_LOG.md`/`PHASE_20-24_*`의 허위 승인 이력 삭제 | 정정된 문서 diff | grep으로 해당 수치 미검출 |

### Track B: Phase 7 하이브리드 AVM

| ID | 작업 | 내용 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| B.1 | 데이터 인벤토리 | (완료) `F:\loan4u_avm_data` 실사 — 158,780건 비교사례, 799,075건 fact 확인 | `results/phase7_data_inventory.md` | 완료됨 |
| B.2 | NPL 물건 스키마 확인 | avm_project의 NPL 데이터(`data/npl_avm.db`, `p1_onbid_clean.csv`, `p2_npl_excel_clean.csv`)에 단지명/지번/전용면적 필드 존재 여부 확인 | 스키마 점검 결과 | 매칭 가능 필드 목록 확정 |
| B.3 | 매칭 엔진 개발 | `scripts/phase7_match_engine.py` — NPL 물건 ↔ RTMS 비교사례(158,780건) 매칭 (지번 우선, 단지명 정규화 + 전용면적 ±2㎡ 보조) | 매칭 엔진 스크립트 + 매칭률 리포트 | T1(정확)/T2(부분)/T3(불가) 분류 산출 |
| B.4 | 시세 그라운딩 예측기 | `scripts/phase7_grounded_avm.py` — 매칭된 비교사례의 시세 중앙값 기반 예측, 잔차 보정(회귀), Isotonic 보정 — **훈련/평가 분리 원칙 A.3 동일 적용** | 예측 스크립트 | 코드에 leak-free 분할 명시 |
| B.5 | 정직한 검증 및 보고 | 시간 분할 검증(최근 거래=테스트), T1 그룹 ±3%/±5% 달성률, 전체 커버리지, MAPE 산출 | `results/phase7_final_report.md` | 모든 수치 재실행 가능 스크립트로 산출, prose 임의 수치 없음 |

---

## 3. 실행 순서 및 의존성

```
A.2 (실제 테스트 MAPE 확인)
  → A.3 (calibration 누수 수정) → A.5 (문서 정정, A.3 결과 반영)
A.4 (가짜 RAG 평가 처리) → A.5 (문서 정정, A.4 결과 반영)

B.2 (NPL 스키마 확인)
  → B.3 (매칭 엔진)
    → B.4 (그라운딩 예측기)
      → B.5 (검증 및 최종 보고)
```

Track A와 B.2까지는 병렬 가능. B.3 이후부터는 순차 실행.

---

## 4. 원칙 (본 세션의 발견에 따라 명시)

1. **PASS로 포장 금지**: 불확실하거나 미검증인 결과는 `PASS`가 아니라 `REVIEW_REQUIRED` / `NOT_VALIDATED` / `BLOCKED_*`로 표기한다 (`loan4u_avm_data` 생태계의 기존 정책과 동일 기준 적용).
2. **모든 성능 지표는 재실행 가능한 스크립트에서 산출**: 마크다운에 손으로 쓴 수치는 사용하지 않는다.
3. **train/holdout 분리 없는 MAPE는 보고하지 않는다.**
4. **가짜 데이터(난수 등)로 생성한 값은 실제 평가값으로 표기하지 않는다.**

---

## 5. 예상 산출물 목록

- 수정된 스크립트: `p6_calibration.py`, `p7_generate_evaluation_results.py`
- 신규 스크립트: `scripts/phase7_match_engine.py`, `scripts/phase7_grounded_avm.py`
- 신규 보고서: `results/phase7_final_report.md`
- 정정된 문서: `PROJECT_COMPLETION_SUMMARY.md` 등 (허위 수치 제거)
- 완료 보고: `SESSION_21_COMPLETION_REPORT.md` (본 WBS 각 항목의 실제 실행 결과, 재현 가능한 수치만 포함)

---

**다음 단계**: 본 명세서에 따라 즉시 개발 착수. 완료 후 `SESSION_21_COMPLETION_REPORT.md`로 상세 보고.
