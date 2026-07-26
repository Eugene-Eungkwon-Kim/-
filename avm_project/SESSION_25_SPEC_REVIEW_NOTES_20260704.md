# Session 25 Spec Review Notes

- 작성일: 2026-07-04
- 리뷰 대상: `SESSION_25_COMPARABLE_COVERAGE_DRAFT_SPEC_20260704.md`
- 리뷰 판정: **CONDITIONAL GO after tuning**

## 1. 리뷰 요약

초안의 방향은 맞다. Session 24에서 서버/계약 문제가 해결됐고, 다음 병목은 실제 비교사례 coverage다. 다만 초안에는 `crosswalk`와 `taxonomy` 후보를 너무 빨리 `AVM estimate`에 연결할 수 있는 위험이 있다.

따라서 최종본에서는 이번 작업을 **고객 산출물에 영향을 주지 않는 dry-run/QA 단계**로 좁힌다.

## 2. 초안 강점

| 항목 | 평가 |
|---|---|
| Session 24 증거 기반 | 좋음. 실제 smoke와 DB count를 사용함 |
| 문제 분리 | 좋음. 행정구역 표현 차이와 자산유형 substring 충돌을 구분함 |
| 고객 안전 경계 | 좋음. `customer_safe=false`를 기본값으로 둠 |
| verifier 포함 | 좋음. false-positive 방지 장치를 계획함 |

## 3. 초안 약점

| 약점 | 위험 | 튜닝 방향 |
|---|---|---|
| 후보를 estimate에 연결하는 표현이 빠름 | 잘못된 비교사례가 가격 산정에 섞일 수 있음 | 이번 세션은 dry-run만 수행 |
| crosswalk 후보 생성 규칙이 문자열 중심 | `화성시`와 임의 문자열이 오연결될 수 있음 | explicit candidate table + review status 필수 |
| taxonomy 클래스가 많음 | 1차 작업이 과도하게 커질 수 있음 | 최소 충돌 클래스부터 시작 |
| 성공 기준이 coverage 증가 중심 | coverage 증가가 false-positive를 숨길 수 있음 | false-promotion 0건을 최상위 기준으로 둠 |
| P1 Pebble5 제품 트랙과 NPL 서버가 섞일 수 있음 | 배포 판단 혼선 | Session 25는 NPL FastAPI QA, Pebble5 RTMS는 후속 별도 spec |

## 4. 튜닝 결정

1. Session 25는 `25A`로 정의한다.
2. `25A`는 estimate 결과를 바꾸지 않는다.
3. 산출물은 diagnostic batch, candidate queue, verifier, dry-run report로 제한한다.
4. 고객 산출물 사용 가능 후보는 계속 0건으로 둔다.
5. 실제 estimator wiring은 `25B`에서 사람 검토 승인 후 진행한다.
6. Session 24 smoke는 회귀 게이트로 유지한다.

## 5. 최종본 반영 사항

최종 명세서에는 다음을 반영한다.

- 이름: `Session 25A Comparable Coverage QA Pack`
- 최상위 완료 기준: false-promotion 0건
- 고객 영향: none
- 실행 모드: dry-run only
- 산출물: JSON/CSV/MD evidence pack
- 후속 게이트: `GO_TO_25B`, `NEEDS_HUMAN_REVIEW`, `NO_GO`

