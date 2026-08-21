# Session 25B 중요도·델타값 기반 실행계획

- 작성일: 2026-07-04
- 대상: Approved-Only Estimator Dry-Run Wiring
- 실행 원칙: 중요도 × 델타값 ÷ 위험/노력 순서로 순차 개발

## 1. 우선순위표

| 순위 | 작업 | 중요도 | 델타값 | 위험/노력 | 판정 | 이유 |
|---:|---|---:|---:|---:|---|---|
| 1 | 승인 게이트 config | 5 | 5 | 1 | P0 | 승인 없이는 25B가 안전하게 진행될 수 없음 |
| 2 | review packet | 4 | 5 | 1 | P0 | 사람이 승인할 수 있는 자료가 있어야 25C로 감 |
| 3 | approved-only dry-run | 5 | 4 | 2 | P0 | 실제 연결 전 영향도 계산 경로 |
| 4 | dry-run verifier | 5 | 4 | 2 | P0 | 미승인 사용과 customer_safe 승격 방지 |
| 5 | 회귀 테스트 | 5 | 3 | 1 | P0 | Session 24/25A 안정성 유지 |
| 6 | 완료 보고 | 3 | 3 | 1 | P1 | 다음 승인 의사결정용 |

## 2. 순차 개발 순서

1. `config/session25b_approved_rules.json` 생성
2. `scripts/session25b_approved_dryrun.py` 구현
3. review packet과 dry-run 결과 생성
4. `scripts/session25b_dryrun_verifier.py` 구현
5. py_compile, pytest, Session 24 smoke, dry-run, verifier 실행
6. `SESSION_25B_COMPLETION_REPORT_20260704.md` 작성

## 3. 게이트

| 게이트 | PASS 기준 |
|---|---|
| 승인 config | 승인 rule 0건, status `AWAITING_HUMAN_APPROVAL` |
| dry-run | preview row 0건, unknown approved id 0건 |
| verifier | overall PASS |
| API smoke | Session 24 smoke 6/6 PASS |
| customer safety | customer_safe true 0건 |

