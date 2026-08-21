# Session 25B 상세계획서·명세서·WBS

## Approved-Only Estimator Dry-Run Wiring

- 작성일: 2026-07-04
- 대상 루트: `F:\NPL전례\avm_project`
- 선행 완료: Session 25A Comparable Coverage QA Pack
- 선행 판정: `NEEDS_HUMAN_REVIEW`
- 본 작업 판정: **CONDITIONAL GO**
- 핵심 원칙: 승인된 후보만 dry-run preview에 사용한다. 운영 `estimate` 로직은 변경하지 않는다.

## 1. 배경

Session 25A는 비교사례 coverage 후보를 만들었지만, 모든 후보를 `NEEDS_REVIEW`, `customer_safe=false`로 남겼다. 따라서 다음 작업은 후보를 직접 산정 로직에 연결하는 것이 아니라, 승인 게이트를 만든 뒤 승인된 후보만 dry-run으로 영향도를 계산하는 것이다.

현재 후보 상태:

| 항목 | 값 |
|---|---:|
| 행정구역 crosswalk 후보 | 3 |
| taxonomy 후보 | 90 |
| candidate queue | 3 |
| customer_safe=true | 0 |
| false-promotion | 0 |

## 2. 목표

1. 승인 규칙 파일을 만든다.
2. 사람 검토용 review packet을 생성한다.
3. 승인된 rule id만 dry-run preview에 사용한다.
4. 승인 rule이 0건이면 preview도 0건이어야 한다.
5. 운영 API와 estimator 결과는 변경하지 않는다.

## 3. 범위 포함

| 구분 | 내용 |
|---|---|
| Approval config | `config/session25b_approved_rules.json` |
| Review packet | 사람이 승인할 rule id와 근거를 보는 MD 보고서 |
| Dry-run script | 승인된 rule id만 queue에서 preview로 이동 |
| Verifier | 미승인 후보 사용, customer_safe 승격, API 회귀를 검증 |
| Report | 완료 결과 및 25C 조건 정리 |

## 4. 범위 제외

- `app/avm/engine.py` 수정
- `/api/v1/avm/estimate` 응답 변경
- `customer_safe=true` 자동 설정
- VWorld/외부 API 호출
- Milvus/OpenAI 기동
- 후보의 사람 승인 대행

## 5. 상세명세

### S25B-R01. 승인 규칙 파일

경로:

- `config/session25b_approved_rules.json`

초기값:

- `status=AWAITING_HUMAN_APPROVAL`
- `approved_crosswalk_rule_ids=[]`
- `approved_type_rule_ids=[]`

완료 기준:

- 승인자가 없으면 승인 rule은 0건이어야 한다.
- 승인 rule id가 후보 파일에 존재하지 않으면 verifier FAIL.

### S25B-R02. Candidate Review Packet

경로:

- `results/session25b_candidate_review_packet_20260704.md`

내용:

- crosswalk 후보 3건
- candidate queue 3건
- taxonomy 핵심 rule
- 승인 입력 방식
- 승인 전 영향도 0건 명시

### S25B-R03. Approved-Only Dry-Run

신규 스크립트:

- `scripts/session25b_approved_dryrun.py`

입력:

- `config/session25b_approved_rules.json`
- `config/session25_sigungu_crosswalk_candidates.json`
- `config/session25_property_type_taxonomy_candidates.json`
- `results/session25_comparable_candidate_queue_20260704.json`

출력:

- `results/session25b_approved_dryrun_20260704.json`
- `results/session25b_approved_dryrun_20260704.md`

처리:

1. 승인 rule id를 로드한다.
2. 승인 rule id가 후보 파일에 존재하는지 검증한다.
3. candidate queue 중 `district_rule_id`와 `type_rule_id`가 모두 승인된 row만 preview로 선택한다.
4. 모든 preview row는 `preview_only=true`, `customer_safe=false`를 유지한다.
5. 승인 rule이 0건이면 `status=AWAITING_APPROVAL`, `preview_rows=0`으로 종료한다.

### S25B-R04. Dry-Run Verifier

신규 스크립트:

- `scripts/session25b_dryrun_verifier.py`

검증:

- unknown approved rule id 0건
- 승인 rule 0건일 때 preview row 0건
- preview row 전부 `preview_only=true`
- preview row 전부 `customer_safe=false`
- Session 24 API smoke PASS 유지

출력:

- `results/session25b_dryrun_verifier_20260704.json`
- `results/session25b_dryrun_verifier_20260704.md`

## 6. WBS

| WBS | 작업 | 산출물 | 예상 | 완료 기준 |
|---|---|---|---:|---|
| 1.0 | 승인 게이트 config | approved rules JSON | 0.3h | 승인 0건 초기화 |
| 2.0 | review packet 생성 | review packet MD | 0.5h | 후보/승인법 명시 |
| 3.0 | approved-only dry-run 구현 | dry-run script/result | 1.2h | 승인 0건이면 preview 0 |
| 4.0 | verifier 구현 | verifier script/result | 1.0h | safety checks PASS |
| 5.0 | 회귀 테스트 | py_compile/pytest/smoke | 0.6h | 모두 PASS |
| 6.0 | 완료 보고 | completion report | 0.4h | 25C 조건 명시 |

예상 총합: 4.0h

## 7. 완료 판정

| 판정 | 조건 |
|---|---|
| `AWAITING_HUMAN_APPROVAL` | 승인 rule 0건, dry-run/verifier PASS |
| `DRYRUN_READY` | 승인 rule 존재, preview row 생성, verifier PASS |
| `NO_GO` | 미승인 rule 사용 또는 customer_safe 승격 발생 |

현재 기대 완료 상태는 `AWAITING_HUMAN_APPROVAL`이다.

