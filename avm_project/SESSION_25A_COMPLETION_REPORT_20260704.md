# Session 25A 개발 완료 보고

## Comparable Coverage QA Pack

- 작성일: 2026-07-04
- 프로젝트 루트: `F:\NPL전례\avm_project`
- 대상 서버: `NPL AVM FastAPI`
- 실행 기준: `http://127.0.0.1:8000`
- 기준 명세: `SESSION_25A_COMPARABLE_COVERAGE_FINAL_SPEC_WBS_20260704.md`
- 우선순위 실행계획: `SESSION_25A_PRIORITY_EXECUTION_PLAN_20260704.md`
- 최종 판정: **NEEDS_HUMAN_REVIEW**

## 1. 작업 요약

Session 25A는 가격 산정 로직을 바꾸지 않고, 비교사례 coverage 문제를 dry-run으로 진단하는 QA Pack을 구현했다. 중요도와 델타값 기준으로 `diagnostic → taxonomy/crosswalk → candidate queue → verifier → 회귀 테스트` 순서로 개발했다.

이번 작업의 산출물은 후보를 만드는 것까지다. 모든 신규 후보는 `review_status=NEEDS_REVIEW`, `customer_safe=false`로 고정되어 있으며, 고객 산출물 또는 estimator에는 연결하지 않았다.

## 2. 우선순위 실행 결과

| 순위 | 작업 | 산출물 | 결과 |
|---:|---|---|---|
| 1 | Coverage diagnostic batch | `scripts/session25_coverage_diagnostic.py` | 완료 |
| 2 | Type taxonomy 후보 | `config/session25_property_type_taxonomy_candidates.json` | 완료 |
| 3 | District crosswalk 후보 | `config/session25_sigungu_crosswalk_candidates.json` | 완료 |
| 4 | Candidate queue | `results/session25_comparable_candidate_queue_20260704.*` | 완료 |
| 5 | Coverage verifier | `scripts/session25_coverage_verifier.py` | PASS |
| 6 | 회귀 테스트 | py_compile, pytest, Session 24 smoke | PASS |
| 7 | 완료 보고 | 본 문서 | 완료 |

## 3. 구현 파일

| 파일 | 설명 |
|---|---|
| `SESSION_25A_PRIORITY_EXECUTION_PLAN_20260704.md` | 중요도/델타값 기반 실행계획 |
| `scripts/session25_coverage_diagnostic.py` | DB 기반 coverage diagnostic 및 dry-run 후보 생성 |
| `scripts/session25_coverage_verifier.py` | false-positive/customer-safe/API smoke 검증 |
| `config/session25_sigungu_crosswalk_candidates.json` | 행정구역 후보 3건 |
| `config/session25_property_type_taxonomy_candidates.json` | 자산유형 taxonomy 후보 90건 |
| `results/session25_coverage_diagnostic_20260704.json` | 기계 판독용 diagnostic |
| `results/session25_coverage_diagnostic_20260704.md` | 사람 검토용 diagnostic 보고 |
| `results/session25_comparable_candidate_queue_20260704.csv` | 검토용 후보 큐 CSV |
| `results/session25_comparable_candidate_queue_20260704.json` | 검토용 후보 큐 JSON |
| `results/session25_coverage_verifier_20260704.json` | verifier 결과 |
| `results/session25_coverage_verifier_20260704.md` | verifier 요약 |

## 4. 주요 실측 결과

| 항목 | 값 |
|---|---:|
| 진단 group | 60 |
| `NO_SOURCE_BACKED_COMPARABLES` | 36 |
| `HAS_SOURCE_BACKED_COMPARABLES` | 24 |
| 행정구역 crosswalk 후보 | 3 |
| 자산유형 taxonomy 후보 | 90 |
| candidate queue row | 3 |
| `customer_safe=true` 신규 후보 | 0 |
| false-promotion | 0 |

대표 케이스 `경기도 / 화성시 / 아파트`는 Session 24와 같은 기준으로 재현됐다.

| 항목 | 값 |
|---|---|
| reason | `NO_SOURCE_BACKED_COMPARABLES` |
| property group count | 9 |
| property_type_count | 27 |
| appraisal_candidate_count | 0 |
| transaction_candidate_count | 0 |
| class | `RESIDENTIAL_APARTMENT` |

## 5. 발견 오류 및 수정

| 오류 | 원인 | 조치 | 결과 |
|---|---|---|---|
| diagnostic appraisal count 불일치 | 최초 구현이 모든 감정평가를 세고, 엔진처럼 최신 감정평가 1건 기준을 쓰지 않음 | `latest appraisal per property` 기준으로 SQL 수정 | 화성시/아파트 0건 재현 |
| crosswalk 과잉 후보 | `동래구 → 동구`처럼 짧은 prefix가 후보로 생성됨 | 양쪽 normalized sigungu 길이 2 이상 조건 추가 | bad short prefix 0건 |
| Session 24 smoke 일시 실패 | 서버 프로세스가 꺼져 있어 URLError 발생 | FastAPI를 안정 모드로 재기동 후 smoke 재실행 | PASS 6/6 |
| verifier 동시 실행 race | smoke 재실행과 verifier가 병렬로 돌며 이전 실패 JSON을 읽음 | smoke PASS 후 verifier 단독 재실행 | PASS |

## 6. 검증 결과

| 게이트 | 명령 | 결과 |
|---|---|---|
| Syntax | `python -m py_compile scripts\session25_coverage_diagnostic.py scripts\session25_coverage_verifier.py` | PASS |
| Unit test | `python -m pytest` | PASS, `4 passed in 20.43s` |
| Session 24 API smoke | `python scripts\session24_api_live_smoke.py --base-url http://127.0.0.1:8000` | PASS, 6/6 |
| Session 25 verifier | `python scripts\session25_coverage_verifier.py` | PASS, 5/5 |

Session 24 API smoke 최종 시각:

- `created_at`: `2026-07-04T15:28:01.691484`
- `overall`: `PASS`

Session 25 verifier 최종 시각:

- `created_at`: `2026-07-04T15:28:14.039767`
- `overall`: `PASS`

## 7. 최종 상태

판정: **NEEDS_HUMAN_REVIEW**

이는 실패가 아니라 Session 25A의 정상 완료 상태다. 이번 작업의 목적은 후보를 고객 산출물로 승격하는 것이 아니라, 사람이 검토할 수 있는 dry-run 후보와 false-positive 방지 verifier를 만드는 것이었다.

`GO_TO_25B` 조건:

1. 사람이 `config/session25_sigungu_crosswalk_candidates.json` 후보를 검토한다.
2. 사람이 `config/session25_property_type_taxonomy_candidates.json`의 주요 class를 승인한다.
3. 승인된 후보만 별도 파일로 분리한다.
4. 그 후 Session 25B에서 estimator dry-run wiring을 설계한다.

## 8. 남은 한계

- RAG는 여전히 `degraded`다. Milvus/OpenAI가 꺼져 있어 가격 설명용으로 쓰지 않는다.
- VWorld 개발키는 이번 작업에서 저장하거나 호출하지 않았다.
- candidate queue는 3건이며 모두 검토 대기 상태다.
- estimate 로직은 의도적으로 변경하지 않았다.
- 작업 전부터 worktree에는 다수의 기존 수정/미추적 파일이 있었다. 이번 완료 범위는 Session 25A 파일과 산출물로 한정한다.

## 9. 다음 작업

Session 25B로 넘어가기 전 사람 검토가 필요하다.

권장 검토 순서:

1. `DW-0001`: `화성시 → 화성만세구`
2. `DW-0002`: `화성시 → 화성효행구`
3. `DW-0003`: `화성시 만세구 → 화성시`
4. `TW-0004`: `아파트형공장`은 `KNOWLEDGE_INDUSTRIAL_CENTER`로 유지
5. `TW-0012`: `아파트`는 `RESIDENTIAL_APARTMENT`로 유지

승인 후 다음 개발은 Session 25B `approved-only estimator dry-run wiring`으로 진행한다.

