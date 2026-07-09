# Session 25A 최종 명세서 및 WBS

## Comparable Coverage QA Pack

- 작성일: 2026-07-04
- 상태: **Final after review tuning**
- 대상 루트: `F:\NPL전례\avm_project`
- 대상 서버: `NPL AVM FastAPI` (`http://127.0.0.1:8000`)
- 선행 완료: Session 24 API Reliability PASS
- 초안: `SESSION_25_COMPARABLE_COVERAGE_DRAFT_SPEC_20260704.md`
- 리뷰 노트: `SESSION_25_SPEC_REVIEW_NOTES_20260704.md`
- 계획 근거: `results/session25_planning_probe_20260704.json`
- 최종 판정: **CONDITIONAL GO**

---

## 1. 한 줄 결론

다음 작업은 가격 산정 로직을 바로 넓히는 일이 아니라, **비교사례가 비는 원인을 배치로 계량하고, 행정구역/자산유형 후보를 dry-run 큐로 만든 뒤, false-positive 0건을 검증하는 QA 팩**이다.

이번 세션에서는 estimator 결과를 바꾸지 않는다.

---

## 2. 근거 요약

Session 24 라이브 스모크는 최종 PASS다.

| 항목 | 값 |
|---|---|
| API smoke | PASS, 6/6 |
| OpenAPI missing schema | `[]` |
| `/api/v1/precedents` UTF-8 샘플 | 3건 |
| `/api/v1/auction-stats` UTF-8 샘플 | 1그룹 |
| `/api/v4/health` | `degraded` |
| disabled services | `milvus`, `openai` |

DB와 비교사례 coverage 현황:

| 테이블 | 건수 |
|---|---:|
| deals | 14 |
| properties | 2,694 |
| appraisals | 2,346 |
| auctions | 904 |
| comparable_sales | 357 |

대표 빈 결과 케이스:

| 항목 | 값 |
|---|---|
| query | `경기도 / 화성시 / 아파트` |
| comparable_count | 0 |
| diagnostics.status | `NO_COMPARABLES` |
| reason | `NO_SOURCE_BACKED_COMPARABLES` |
| sido_count | 1,139 |
| sigungu_count | 113 |
| property_type_count | 27 |
| appraisal_candidate_count | 0 |
| transaction_candidate_count | 0 |

추가 관찰:

- `properties`에는 `경기도/화성시`가 존재한다.
- `comparable_sales`에는 `경기도/화성만세구`, `경기도/화성효행구`가 존재한다.
- 현재 `%아파트%` 필터는 `아파트`, `아파트형공장`, `공동주택아파트` 등 의미가 다른 유형을 함께 잡을 수 있다.

---

## 3. 작업 목표

### 목표명

**Session 25A: Comparable Coverage QA Pack**

### 목표

1. `NO_SOURCE_BACKED_COMPARABLES` 발생 구간을 배치 진단한다.
2. 행정구역 표현 차이 후보를 만들되, estimate에는 연결하지 않는다.
3. 자산유형 substring 충돌 후보를 분리한다.
4. 사람이 검토 가능한 비교사례 후보 큐를 생성한다.
5. verifier로 false-promotion 위험을 먼저 차단한다.
6. Session 24 API smoke를 회귀 게이트로 유지한다.

### 비목표

- 가격 산정 결과 개선 주장
- estimator query 확장 반영
- 고객 export 생성
- VWorld 개발키 저장
- 외부 API 대량 호출
- Milvus/OpenAI 기동
- 토지 PNU 대량 복원
- Pebble5 product gate 변경

---

## 4. 최종 설계 원칙

| 원칙 | 내용 |
|---|---|
| Dry-run only | 후보를 만들지만 `AVM estimate` 결과는 바꾸지 않는다. |
| Customer safe default false | 새 후보는 기본적으로 고객 산출물 사용 불가다. |
| False-positive first | coverage 증가보다 잘못된 승격 0건이 우선이다. |
| Source-backed only | 후보는 DB row, 원천 테이블, rule id를 가져야 한다. |
| Reviewable artifact | 사람이 검토할 CSV/MD/JSON을 모두 남긴다. |
| Regression locked | Session 24 live smoke 6/6 PASS를 유지해야 한다. |

---

## 5. 상세 요구사항

### S25A-R01. Coverage Diagnostic Batch

목적: estimate가 빈 결과를 내는 구간을 수작업이 아니라 배치로 계량한다.

신규 스크립트:

- `scripts/session25_coverage_diagnostic.py`

입력:

- `data/npl_avm.db`
- 상위 `properties` 지역/유형 그룹
- 상위 `comparable_sales` 지역/유형 그룹

처리:

1. 상위 property group을 추출한다.
2. 각 group에 대해 현재 estimate 후보 수와 reason code를 계산한다.
3. `NO_SOURCE_BACKED_COMPARABLES`, `NO_SIGUNGU_MATCH`, `NO_PROPERTY_TYPE_MATCH` 등을 집계한다.
4. 상위 blocker 순위를 만든다.

출력:

- `results/session25_coverage_diagnostic_20260704.json`
- `results/session25_coverage_diagnostic_20260704.md`

완료 기준:

- 최소 30개 group 진단
- reason code별 count 산출
- 화성시 케이스가 재현됨

---

### S25A-R02. District Crosswalk Candidate Pack

목적: 행정구역 표현 차이 후보를 만들되, 승인 전에는 매칭에 쓰지 않는다.

신규 산출물:

- `config/session25_sigungu_crosswalk_candidates.json`
- `results/session25_sigungu_crosswalk_report_20260704.md`

후보 예시:

| query_sigungu | candidate_sigungu | status |
|---|---|---|
| 화성시 | 화성만세구 | NEEDS_REVIEW |
| 화성시 | 화성효행구 | NEEDS_REVIEW |

필수 필드:

- `rule_id`
- `query_sido`
- `query_sigungu`
- `candidate_sido`
- `candidate_sigungu`
- `evidence_property_count`
- `evidence_comparable_count`
- `match_basis`
- `review_status`
- `customer_safe`

완료 기준:

- 모든 후보 `review_status=NEEDS_REVIEW`
- 모든 후보 `customer_safe=false`
- estimate 검색 로직 변경 없음

---

### S25A-R03. Property Type Taxonomy Candidate Pack

목적: substring 기반 자산유형 혼합 위험을 분리한다.

신규 산출물:

- `config/session25_property_type_taxonomy_candidates.json`
- `results/session25_property_type_taxonomy_report_20260704.md`

최소 클래스:

| class | 포함 예 | 주의 |
|---|---|---|
| `RESIDENTIAL_APARTMENT` | `아파트`, `공동주택(아파트)` | `아파트형공장` 제외 |
| `MULTIFAMILY` | `다세대주택`, `다가구주택`, `연립주택` | 아파트와 분리 |
| `OFFICETEL_RESIDENTIAL` | `오피스텔(주거)` | 비주거와 분리 |
| `OFFICETEL_NON_RESIDENTIAL` | `오피스텔(비주거)` | 주거와 분리 |
| `KNOWLEDGE_INDUSTRIAL_CENTER` | `아파트형공장`, `지식산업센터` | 아파트와 분리 |
| `FACTORY` | `공장`, `제조업소` | 산업용 |
| `RETAIL` | `근린상가`, `근린생활시설` | 상업용 |
| `LAND` | `대`, `답`, `전`, `임야` | PNU 복원 전 dry-run |
| `OTHER` | 미분류 | 승격 금지 |

완료 기준:

- `아파트` 요청이 `아파트형공장`으로 자동 승격되지 않음을 verifier가 확인
- 원문 `property_type`은 보존
- taxonomy는 후보 파일로만 저장

---

### S25A-R04. Comparable Candidate Queue

목적: 사람이 검토할 수 있는 비교사례 보강 후보를 만든다.

신규 산출물:

- `results/session25_comparable_candidate_queue_20260704.csv`
- `results/session25_comparable_candidate_queue_20260704.json`

필수 필드:

| 필드 | 설명 |
|---|---|
| `queue_id` | 후보 식별자 |
| `query_sido` | 요청 시도 |
| `query_sigungu` | 요청 시군구 |
| `query_property_type` | 요청 자산유형 |
| `candidate_source` | `appraisal` 또는 `transaction` |
| `candidate_sido` | 후보 시도 |
| `candidate_sigungu` | 후보 시군구 |
| `candidate_property_type` | 후보 자산유형 |
| `district_rule_id` | 행정구역 후보 규칙 |
| `type_rule_id` | 자산유형 후보 규칙 |
| `evidence_count` | 후보 근거 row 수 |
| `risk_flags` | 위험 플래그 |
| `review_status` | `NEEDS_REVIEW` |
| `customer_safe` | `false` |

완료 기준:

- 후보 row가 0건이어도 실패가 아니다. 이유 보고가 있으면 PASS다.
- 후보가 있더라도 고객 산출물 사용 가능 후보는 0건이어야 한다.

---

### S25A-R05. Coverage Verifier

목적: 후보 생성이 잘못된 승격으로 이어지지 않음을 증명한다.

신규 스크립트:

- `scripts/session25_coverage_verifier.py`

검증 항목:

1. `아파트`가 `아파트형공장` 후보와 customer-safe로 연결되지 않는다.
2. `화성시` crosswalk 후보는 `NEEDS_REVIEW` 상태로만 남는다.
3. `customer_safe=true` 후보는 0건이다.
4. Session 24 smoke 결과가 계속 PASS다.
5. estimate 응답 shape가 깨지지 않는다.

출력:

- `results/session25_coverage_verifier_20260704.json`
- `results/session25_coverage_verifier_20260704.md`

완료 기준:

- verifier overall PASS
- false-promotion 0건
- customer-safe 신규 후보 0건

---

## 6. WBS

| WBS | 작업 | 상세 | 산출물 | 예상 | 상태 기준 |
|---|---|---|---|---:|---|
| 1.0 | 기준 증거 고정 | Session 24 smoke, DB count, probe JSON 재확인 | planning probe | 0.3h | evidence 파일 존재 |
| 2.0 | Coverage diagnostic 구현 | group별 reason code 집계 | diagnostic script/report | 1.2h | 30개+ group |
| 3.0 | District crosswalk 후보 생성 | 시군구 표현 차이 후보 추출 | crosswalk JSON/MD | 1.3h | all NEEDS_REVIEW |
| 4.0 | Type taxonomy 후보 생성 | substring 충돌 분리 | taxonomy JSON/MD | 1.5h | 아파트/아파트형공장 분리 |
| 5.0 | Candidate queue 생성 | 후보 통합 큐 CSV/JSON | queue CSV/JSON | 1.2h | customer_safe=false |
| 6.0 | Verifier 구현 | false-promotion/customer-safe/smoke 검증 | verifier script/report | 1.2h | overall PASS |
| 7.0 | 회귀 테스트 | py_compile, pytest, Session 24 smoke | test logs | 0.6h | 3개 PASS |
| 8.0 | 완료 보고 | 결과/한계/25B 게이트 정리 | completion report | 0.5h | 보고서 저장 |

예상 총합: 7.8h  
권장 실행 단위: 1일

---

## 7. 테스트 계획

| 테스트 | 명령 | 합격 기준 |
|---|---|---|
| Syntax | `python -m py_compile scripts/session25_coverage_diagnostic.py scripts/session25_coverage_verifier.py` | PASS |
| 기존 단위 테스트 | `python -m pytest` | PASS |
| API 회귀 | `python scripts/session24_api_live_smoke.py --base-url http://127.0.0.1:8000` | PASS 6/6 |
| Coverage verifier | `python scripts/session25_coverage_verifier.py` | PASS |
| 후보 안전성 | verifier 내부 | `customer_safe=true` 0건 |
| 타입 충돌 | verifier 내부 | `아파트` -> `아파트형공장` 자동 승격 0건 |
| 행정구역 후보 | verifier 내부 | crosswalk 후보 전부 `NEEDS_REVIEW` |

---

## 8. 완료 판정

| 판정 | 조건 |
|---|---|
| `GO_TO_25B` | diagnostic/queue/verifier PASS, 사람이 일부 후보를 승인 |
| `NEEDS_HUMAN_REVIEW` | 후보는 생성됐지만 검토 전이라 연결 불가 |
| `NO_GO` | 후보 생성이 불안정하거나 false-positive가 발견됨 |

Session 25A의 기본 완료 상태는 `NEEDS_HUMAN_REVIEW`가 정상이다. `GO_TO_25B`는 사람이 후보를 승인한 뒤에만 가능하다.

---

## 9. 개발 착수 순서

1. `scripts/session25_coverage_diagnostic.py` 작성
2. diagnostic JSON/MD 생성
3. crosswalk candidate JSON/MD 생성
4. taxonomy candidate JSON/MD 생성
5. candidate queue CSV/JSON 생성
6. `scripts/session25_coverage_verifier.py` 작성
7. `py_compile`, `pytest`, Session 24 smoke, Session 25 verifier 실행
8. `SESSION_25A_COMPLETION_REPORT_20260704.md` 작성

---

## 10. 리뷰 후 튜닝 반영 사항

초안 대비 최종본에서 조정한 내용:

| 항목 | 초안 | 최종 |
|---|---|---|
| estimate 연결 | 후보 연결 가능성 포함 | 연결 금지, dry-run only |
| 성공 기준 | coverage 증가 중심 | false-promotion 0건 중심 |
| 후보 상태 | review 예정 | 전부 `NEEDS_REVIEW`, `customer_safe=false` 고정 |
| Session 범위 | Coverage v1 | Coverage QA Pack 25A |
| 후속 작업 | 바로 개선 가능 | 사람 승인 후 25B |

---

## 11. 잔여 경계

- RAG는 여전히 `degraded`다. Milvus/OpenAI가 켜지기 전까지 가격 설명용으로 쓰지 않는다.
- VWorld 개발키는 이 작업에서 쓰지 않는다. 필요한 경우 runtime-only 별도 smoke로 분리한다.
- Pebble5 evidence-gated 제품 트랙의 RTMS 배선은 같은 철학을 공유하지만, 이 NPL FastAPI QA Pack과 동일 작업으로 합치지 않는다.
- 현 작업트리에는 기존 변경/미추적 파일이 많으므로, 개발 시 Session 25A 파일만 범위로 관리한다.

