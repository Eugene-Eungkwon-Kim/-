# W65 VWorld Runtime Probe Plan, Spec, and WBS

- 작성일: 2026-07-07
- 기준 산출물: `results\w64_vworld_multi_layer_control_plane_report_20260707.md`
- 대상 코드: `scripts\vworld_multi_layer_collector.py`
- 데이터 루트: `F:\loan4u_avm_data\vworld_wfs_multi_layer`

## 1. 목표

Rev.4 control plane의 다음 단계로 `probe-endpoints --key-prompt --write`를
구현한다. API key는 런타임 입력으로만 받고, 코드/명령줄/ledger/보고서에는
저장하지 않는다.

## 2. 상세 명세

| 항목 | 명세 |
|---|---|
| key 입력 | `--key-prompt`, `--key-stdin` |
| 기본 안전 상태 | `--dry-run`이 아니고 key 입력 옵션이 없으면 `WAITING_RUNTIME_KEY` |
| live 호출 | Search, Geocoder, WFS/WMS/NED 후보 중 endpoint가 확정된 layer만 단건 probe |
| endpoint 미확정 | `blocked_endpoint_contract` 유지 |
| reference layer | `reference_only` 유지 |
| ledger 저장 | key 없는 request metadata, status, http_status, response hash, byte length |
| raw 저장 | 이번 W65에서는 저장하지 않음 |
| QA | secret literal scan, probe summary, live/safe-stop 상태 점검 |

## 3. 범위 제외

- API key 값 저장
- raw payload 대량 저장
- parser/SQLite/DuckDB 적재
- 전체 14개 batch 수집

## 4. 중요도 및 델타 기준 WBS

| 순위 | WBS | 작업 | 중요도 | 델타 | 완료 기준 |
|---:|---|---|---:|---:|---|
| 1 | W65-1 | no-key safe-stop | 10 | 35 | key 옵션 없으면 `WAITING_RUNTIME_KEY` |
| 2 | W65-2 | runtime key reader | 10 | 32 | prompt/stdin 입력, 저장 0 |
| 3 | W65-3 | live probe request builder | 10 | 31 | 확정 endpoint별 sample request 생성 |
| 4 | W65-4 | secret-safe ledger | 10 | 30 | key 없는 metadata만 저장 |
| 5 | W65-5 | probe status classifier | 9 | 26 | ok/no_features/error 분류 |
| 6 | W65-6 | QA 보강 | 9 | 24 | secret scan + summary PASS |
| 7 | W65-7 | test/report | 8 | 18 | py_compile + dry-run + safe-stop + QA |

## 5. 자체 검토

| 관점 | 검토 결과 |
|---|---|
| 보안 | key는 `getpass` 또는 stdin으로만 받고 payload에는 넣지 않는다. |
| 운영 | network/key가 없으면 실패가 아니라 안전 정지로 기록한다. |
| 코드 품질 | 기존 단일 CLI 구조를 유지하되 함수 단위로 추가한다. |
| 정직성 | live API 성공은 실제 key와 네트워크로 실행하기 전까지 주장하지 않는다. |

## 6. 개발 순서

1. `probe-endpoints` CLI 옵션 확장
2. runtime key reader 추가
3. endpoint별 sample request builder 추가
4. urllib 기반 live probe 추가
5. no-key safe-stop 테스트
6. dry-run 회귀 테스트
7. QA와 최종 보고서 작성
