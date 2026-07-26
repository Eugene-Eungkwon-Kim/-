# Session 25B 명세 리뷰 노트

- 작성일: 2026-07-04
- 리뷰 대상: `SESSION_25B_APPROVED_DRYRUN_DETAILED_PLAN_SPEC_WBS_20260704.md`
- 리뷰 판정: **GO with strict guardrails**

## 1. 리뷰 결론

25B는 개발을 시작해도 된다. 단, 승인 후보가 아직 없으므로 정상 완료 상태는 `AWAITING_HUMAN_APPROVAL`이다. 이 상태에서 preview row가 0건이어야 하며, 그것이 실패가 아니라 안전한 정답이다.

## 2. 핵심 위험

| 위험 | 심각도 | 대응 |
|---|---:|---|
| 미승인 후보가 dry-run에 포함됨 | P0 | approved rule id 양쪽 매칭 필수 |
| preview가 customer_safe로 오해됨 | P0 | 모든 preview row `customer_safe=false` 고정 |
| 운영 estimate 로직 변경 | P0 | app 코드 수정 금지 |
| 승인 rule 오타 | P1 | unknown rule id verifier FAIL |
| 이전 smoke 실패 JSON 사용 | P1 | live smoke 재실행 후 verifier 단독 실행 |

## 3. 튜닝 반영

1. 승인 config는 비어 있는 상태로 시작한다.
2. review packet은 사람이 승인할 후보를 보여주지만 승인하지 않는다.
3. dry-run preview는 승인 rule이 0건이면 0건이어야 한다.
4. verifier는 `AWAITING_HUMAN_APPROVAL`도 PASS 상태로 인정한다.
5. 완료 보고서는 개발 완료와 승인 대기 상태를 분리한다.

## 4. 개발 허용 범위

허용:

- 신규 config 추가
- 신규 scripts 추가
- 신규 results/report 추가

금지:

- `app/` 코드 변경
- DB schema 변경
- 외부 API 호출
- `customer_safe=true` 자동 생성

