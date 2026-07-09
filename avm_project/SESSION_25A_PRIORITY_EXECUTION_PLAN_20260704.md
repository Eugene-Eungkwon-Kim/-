# Session 25A 중요도/델타값 기반 실행계획

- 작성일: 2026-07-04
- 대상: `F:\NPL전례\avm_project`
- 기준 명세: `SESSION_25A_COMPARABLE_COVERAGE_FINAL_SPEC_WBS_20260704.md`
- 실행 원칙: 계획/명세/WBS 검토 후 중요도와 델타값 순서대로 순차 개발
- 고객 영향: 없음. 이번 작업은 dry-run QA Pack이다.

## 1. 우선순위 산정 기준

점수는 `중요도 × 델타값 ÷ 위험/노력`으로 판단했다. 단, 안전 게이트 의존성이 있으면 순서를 앞당겼다.

| 순위 | 작업 | 중요도 | 델타값 | 위험/노력 | 판정 | 이유 |
|---:|---|---:|---:|---:|---|---|
| 1 | Coverage diagnostic batch | 5 | 5 | 2 | P0 | 빈 결과 원인을 계량하지 못하면 후속 후보가 전부 감으로 변함 |
| 2 | Type taxonomy 후보 | 5 | 4 | 2 | P0 | `아파트` vs `아파트형공장` 오승격은 가격 산정 안전성 직결 |
| 3 | District crosswalk 후보 | 4 | 4 | 3 | P1 | `화성시` vs `화성만세구/화성효행구` coverage 개선 가능성 큼 |
| 4 | Candidate queue 생성 | 4 | 4 | 2 | P1 | 사람이 검토 가능한 산출물 없이는 25B 승인 불가 |
| 5 | Coverage verifier | 5 | 3 | 2 | P0 gate | false-positive 0건을 보장하는 완료 게이트 |
| 6 | 회귀 테스트 | 5 | 3 | 1 | P0 gate | Session 24 API 안정성 보존 확인 |
| 7 | 완료 보고 | 3 | 3 | 1 | P1 | 다음 의사결정용 증거 패키지 |

## 2. 순차 개발 순서

1. `scripts/session25_coverage_diagnostic.py`
   - DB group별 reason code를 계량한다.
   - diagnostic JSON/MD를 생성한다.
2. 같은 스크립트에서 taxonomy/crosswalk 후보를 dry-run으로 생성한다.
   - 후보는 모두 `NEEDS_REVIEW`, `customer_safe=false`.
3. candidate queue CSV/JSON을 생성한다.
   - 사람이 볼 수 있는 후보 큐를 만든다.
4. `scripts/session25_coverage_verifier.py`
   - false-promotion 0건, customer-safe 0건, Session 24 smoke PASS를 확인한다.
5. 테스트와 완료 보고
   - `py_compile`, `pytest`, Session 24 smoke, Session 25 verifier를 실행한다.

## 3. 개발 중 금지사항

- `app/avm/engine.py`의 estimate 검색 로직 변경 금지
- 신규 후보를 고객 산출물로 승격 금지
- 외부 API 호출 금지
- VWorld 키 저장 금지
- RAG/Milvus/OpenAI 상태를 정상으로 포장 금지

## 4. 완료 기준

| 기준 | 합격 |
|---|---|
| Coverage diagnostic | 30개 이상 group 진단 |
| Type taxonomy | `아파트`와 `아파트형공장` 분리 |
| District crosswalk | 후보 전부 `NEEDS_REVIEW` |
| Candidate queue | `customer_safe=true` 0건 |
| Verifier | overall PASS |
| Regression | `pytest`, Session 24 smoke PASS |
| 최종 상태 | `NEEDS_HUMAN_REVIEW` 정상 완료 |

