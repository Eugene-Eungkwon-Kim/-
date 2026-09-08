# Session 21 완료 보고서: 코드 디버깅 + Phase 7 하이브리드 AVM

**작성일**: 2026-07-03
**기준 문서**: [SESSION_21_PHASE7_DETAILED_SPEC_WBS.md](SESSION_21_PHASE7_DETAILED_SPEC_WBS.md)
**원칙**: 모든 수치는 재실행 가능한 스크립트의 직접 출력. 손으로 쓴 추정치 없음.

---

## 요약

| Track | 항목 | 상태 |
|---|---|---|
| A.1 | 22개 스크립트 경로 수정 (D:→F:) | ✅ 완료 |
| A.2 | 실제 held-out MAPE 확인 | ✅ 완료 (78.23%) |
| A.3 | `p6_calibration.py` 데이터 누수 수정 | ✅ 완료 (66.64%) |
| A.4 | `p7_generate_evaluation_results.py` 가짜 평가 제거 | ✅ 완료 |
| A.5 | 문서 정정 | ✅ 완료 (핵심 문서 + 정정공지) |
| B.1 | 데이터 인벤토리 | ✅ 완료 (158,780건 확인) |
| B.2 | NPL 스키마 확인 | ✅ 완료 (2,694건, 아파트 379건) |
| B.3 | 매칭 엔진 | ✅ 완료 (T1 매칭률 86.0%) |
| B.4/B.5 | 그라운딩 예측기 + 검증 | ✅ 완료 (MAPE 9.40%/15.12%) |

---

## Track A: 코드 디버깅 결과

### A.1 — 경로 수정
외장 드라이브 문자가 D:→F:로 바뀌며 깨졌던 22개 스크립트(`scripts/*.py`)의 하드코딩 경로를
전부 수정. `_archive_legacy/` 내 15개 사장 코드는 미사용으로 판단해 그대로 둠.

### A.2 — 실제 성능 확인 (핵심 발견)

`models/p6_advanced_hammer_ensemble.pkl`에 학습 스크립트(`p6_advanced_training.py`)
자체가 저장한, 한 번도 학습/튜닝에 쓰이지 않은 진짜 test set(118건) 결과:

| 지표 | 실제 값 | 과거 보고값 |
|---|---:|---:|
| MAPE | **78.23%** | 0.46% |
| ±5% 달성률 | 11.02% | 93.3% |
| ±10% 달성률 | 21.19% | (언급 없음) |
| ±20% 달성률 | 32.20% | (언급 없음) |

`p6_advanced_training.py`의 train/val/test 분할 로직 자체는 정상(데이터 누수 없음) —
문제는 그 다음 단계인 `p6_calibration.py`에서 발생했음.

### A.3 — Calibration 데이터 누수 수정

원본 `p6_calibration.py`는 전체 589건에 대해 보정(fit)과 평가를 동시에 수행해 결과가
부풀려져 있었음. 학습 스크립트와 동일한 분할(`random_state=42`)을 재현해
train+val(471건)에서만 보정을 적합시키고, 한 번도 보지 않은 test(118건)에서만 평가하도록 재작성.

**재실행 결과 (leak-free)**:
- 보정 전 MAPE: 78.23% (A.2와 일치 — 정합성 확인됨)
- 보정 후 MAPE: **66.64%**
- ±3% 달성률: 8.5%
- ±5% 달성률: 11.0%

→ Isotonic 보정으로 78.23%→66.64%까지는 개선되나, 실사용 가능 수준(±3~5%)에는 크게 못 미침.
589건 순수 회귀 방식의 한계로 판단, Track B로 방향 전환.

### A.4 — RAG 평가 가짜 데이터 제거

조사 결과 이 프로젝트에는 **RAG 설명 생성 파이프라인이 전혀 구현되어 있지 않음**을 확인:
- `requirements.txt`에 벡터DB(Milvus 등) 의존성 없음
- 코드베이스 전체에서 실제 검색/생성 파이프라인 미검출
- `p7_test_embedding.py`는 OpenAI 임베딩 API 연결 확인용 스모크 테스트일 뿐

원본 `p7_generate_evaluation_results.py`는 `np.random.normal()`로 점수를 생성해
"8.05/10.0, PASS"로 보고했었음. 이를 제거하고 `status: NOT_EVALUATED,
reason: BLOCKED_NO_RAG_PIPELINE`으로 정직하게 재작성.

### A.5 — 문서 정정

- [CORRECTIONS_20260703.md](CORRECTIONS_20260703.md) 신규 작성 — 모든 허위 수치와 실제 값을 표로 대조
- `PROJECT_COMPLETION_SUMMARY.md` 상단에 정정 공지 삽입
- `EXECUTION_LOG.md`의 "2026-07-04 사용자 승인 완료" 등 허위(미래를 과거로 기재) 이력 제거

---

## Track B: Phase 7 하이브리드 AVM 결과

### B.1 — 데이터 인벤토리

`F:\loan4u_avm_data`(실제 데이터 위치, D:는 별개의 빈 드라이브였음) 확인:
- RTMS 비교사례 마트: **158,780건** (단지명/지번/면적/가격 완비)
- RTMS 전체 거래 fact: **799,075건** (2026-07-01 최신 빌드)
- 상세: [results/phase7_data_inventory.md](results/phase7_data_inventory.md)

### B.2 — NPL 데이터 스키마 확인

`data/npl_avm.db`의 `properties` 테이블에 실거래 매칭 가능한 실 데이터 확인:
- 전체 2,694건 (기존 ML 파이프라인이 쓴 589건보다 훨씬 큼)
- 아파트 379건 — `address_detail`에 단지명·지번·동/층/호가 파싱 가능한 형태로 존재
  (예: `"565외 1필지 우성아파트 제14동 제10층 제1003호"`)
- `complexes`/`units`/`transactions`/`rtech_comparables` 테이블은 스키마만 있고 **비어있음** (0건) — 과거 세션이 설계만 하고 채우지 않은 것으로 확인

### B.3 — 매칭 엔진 (`scripts/phase7_match_engine.py`)

아파트 379건을 RTMS 비교사례 158,780건과 매칭:

| Tier | 정의 | 건수 | 비율 |
|---|---|---:|---:|
| T1 | 동+지번 정확 매칭 | 326 | **86.0%** |
| T2 | 동+단지명+면적±15% | 3 | 0.8% |
| T3 | 매칭 불가 | 50 | 13.2% |

상세: [results/phase7_match_report.md](results/phase7_match_report.md), 매칭 원자료: [results/phase7_matched_pairs.csv](results/phase7_matched_pairs.csv)

### B.4/B.5 — 그라운딩 예측기 검증 (`scripts/phase7_grounded_avm.py`)

**검증 표본**: `onbid_auction_results`의 '주거용건물' 중 실제 `hammer_price`를 보유한 124건
(내부 매칭 성공 32건 — 이 표는 주소 형식이 달라 동 추출률이 56%로 낮았음, 개선 여지 있음)

| 검증 | 비교 대상 | MAPE | 비고 |
|---|---|---:|---|
| A | 그라운딩 시세 추정치 vs 실제 감정가 | **9.40%** | n=32 |
| B | 그라운딩 시세 × 낙찰가율(leave-one-out) vs 실제 낙찰가 | **15.12%** | n=32, ±5% 달성 18.8% |

### 방식 비교 (모두 leak-free, 실측)

| 방식 | MAPE |
|---|---:|
| 순수 회귀 (589건, p6 앙상블+보정) | 66.64% |
| 시세 그라운딩 (감정가 대비) | 9.40% |
| 시세 그라운딩×낙찰가율 (실제 낙찰가 대비) | 15.12% |

**결론**: 표본은 아직 작지만(n=32), 실거래 비교사례에 앵커링하는 방식이 순수 회귀보다
수 배 이상 정확함이 실측으로 확인됨. Phase 7 방향 전환이 옳았음.

---

## 한계 및 다음 단계 (정직하게 명시)

1. **검증 B의 낙찰가율(hammer rate)은 검증된 모델이 아니라 leave-one-out 단순 평균** — 이 부분을 실제 모델(회귀 또는 규칙 기반)로 교체하면 15.12%보다 개선 가능성 있음
2. **매칭 대상이 아파트(379건)와 주거용건물(124건, 매칭 32건)로 제한** — 공장/상가/토지 등 비아파트 자산(전체 2,694건 중 다수)은 이 방법 적용 안 됨. 별도 트랙 필요
3. **onbid 주소 파싱률 56%** — 정규식이 properties.address_detail 형식에 맞춰져 있어 address_raw 형식에는 최적화 안 됨. 개선 시 매칭 표본 확대 가능
4. **표본 크기(n=32)가 작아 신뢰구간이 넓음** — 더 많은 실제 hammer_price 보유 물건 확보 필요

### 권장 다음 작업
- onbid_auction_results 주소 파싱 로직 개선 (매칭 표본 32→100+ 목표)
- 낙찰가율을 leave-one-out 평균 대신 실제 모델(지역/자산유형별)로 교체
- 비아파트 자산(토지/상가/공장)에 대한 별도 그라운딩 전략 검토

---

## 산출물 목록

### 수정된 파일
- `scripts/p6_calibration.py` (데이터 누수 수정)
- `scripts/p7_generate_evaluation_results.py` (가짜 평가 제거)
- 22개 스크립트 (경로 수정)
- `PROJECT_COMPLETION_SUMMARY.md`, `EXECUTION_LOG.md` (정정 고지)

### 신규 파일
- `CORRECTIONS_20260703.md`
- `scripts/phase7_match_engine.py`
- `scripts/phase7_grounded_avm.py`
- `results/phase7_data_inventory.md`
- `results/phase7_match_report.md` + `results/phase7_matched_pairs.csv`
- `results/phase7_final_report.md`
- `models/p6_calibration.pkl` (leak-free 버전으로 재생성)
- `results/p7_evaluation_results.json` + `results/p7_evaluation_analysis.md` (정직화 버전으로 재생성)

---

**본 보고서의 모든 수치는 위 스크립트를 재실행하면 동일하게 재현된다.**
