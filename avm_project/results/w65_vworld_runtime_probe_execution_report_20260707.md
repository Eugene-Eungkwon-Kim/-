# W65 VWorld Runtime Probe Execution Report

- 작성일: 2026-07-07
- 대상 코드: `scripts\vworld_multi_layer_collector.py`
- 계획서/명세서/WBS: `results\w65_vworld_runtime_probe_plan_spec_wbs_reviewed_20260707.md`
- 데이터 루트: `F:\loan4u_avm_data\vworld_wfs_multi_layer`

## 1. 결론

W65 개발은 완료됐다. `probe-endpoints`는 이제 `--key-prompt` 또는
`--key-stdin`으로 runtime key를 받을 수 있고, key 옵션 없이 실행하면
`WAITING_RUNTIME_KEY`로 안전 정지한다. 실제 live API 호출은 key를 사용자가
런타임에 직접 입력해야 하므로 이번 자동 테스트에서는 실행하지 않았다.

## 2. 구현 내용

| 항목 | 결과 |
|---|---|
| no-key safe-stop | `WAITING_RUNTIME_KEY` |
| runtime key 입력 | `--key-prompt`, `--key-stdin` |
| live request builder | Search, Geocoder, WFS/NED WFS 확정 endpoint |
| endpoint 미확정 layer | `blocked_endpoint_contract` 유지 |
| reference layer | `reference_only` 유지 |
| secret-safe ledger | request metadata에서 key 제외 |
| latest probe output | `endpoint_probe_latest.json` |
| dry-run output | `endpoint_probe_dryrun.json` |

## 3. 테스트 결과

### 3.1 py_compile

```powershell
C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe -m py_compile scripts\vworld_multi_layer_collector.py
```

결과: PASS.

### 3.2 함수 길이

결과: 최대 함수 길이 20 lines.

### 3.3 registry 재생성

```powershell
C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py init-registry --root F:\loan4u_avm_data\vworld_wfs_multi_layer --profile rev4 --write
```

결과:

- status: `INIT_REGISTRY_WRITTEN`
- layer_count: 14
- secret_persisted: false

### 3.4 dry-run 회귀

```powershell
C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py probe-endpoints --root F:\loan4u_avm_data\vworld_wfs_multi_layer --dry-run --write
```

결과:

- mode: `dry_run`
- layer_count: 14
- terminal_errors: 0
- ready_for_runtime_probe: 5
- reference_only: 1
- blocked_endpoint_contract: 5
- blocked_runtime_key: 3

### 3.5 no-key safe-stop

```powershell
C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py probe-endpoints --root F:\loan4u_avm_data\vworld_wfs_multi_layer --write
```

결과:

- mode: `WAITING_RUNTIME_KEY`
- terminal_errors: 0
- waiting_runtime_key: 5
- reference_only: 1
- blocked_endpoint_contract: 5
- blocked_runtime_key: 3

### 3.6 QA

```powershell
C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py qa --root F:\loan4u_avm_data\vworld_wfs_multi_layer --write
```

결과:

- overall: `PASS`
- layer_count_14: PASS
- unique_layer_ids: PASS
- secret_literal_scan: PASS
- probe_summary_exists: PASS

### 3.7 redaction builder

네트워크 호출 없이 dummy key로 live request metadata를 생성한 뒤,
`params_without_secret`에 `key`가 없는지 assert했다.

결과: `redaction_probe_builder=PASS`

## 4. 중요도 및 델타 순 처리 결과

| 순위 | WBS | 작업 | 상태 |
|---:|---|---|---|
| 1 | W65-1 | no-key safe-stop | 완료 |
| 2 | W65-2 | runtime key reader | 완료 |
| 3 | W65-3 | live probe request builder | 완료 |
| 4 | W65-4 | secret-safe ledger | 완료 |
| 5 | W65-5 | probe status classifier | 완료 |
| 6 | W65-6 | QA 보강 | 완료 |
| 7 | W65-7 | test/report | 완료 |

## 5. 정직한 한계

실제 VWorld live API 성공은 아직 검증하지 않았다. 이유는 API key를 대화 로그,
파일, 명령줄, 보고서에 남기지 않기 위해 사용자가 `--key-prompt` 실행 시
직접 입력해야 하기 때문이다. 따라서 현재 완료 범위는 live probe 실행 가능 코드와
secret-safe guard 검증까지다.

## 6. 다음 실행 명령

```powershell
C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py probe-endpoints --root F:\loan4u_avm_data\vworld_wfs_multi_layer --key-prompt --layers search20,geocoder20 --timeout 10 --write
```

위 명령은 key를 프롬프트로 입력받고, ledger에는 key 없는 metadata만 기록한다.
