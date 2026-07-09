# PR #1 Branch Update Prep

- Target PR branch: claude/eloquent-meitner-lqxu9r
- Local update source: F:\NPL전례\avm_project
- Local repo state checked: 2026-07-08
- Local branch: master
- Local master HEAD: ad83a41b016a36c4f353e3c22d723f8a1f716e04
- Available local comparison branch: week14-f1-f2-integration at a9abd708be7f39c5281d4d9be717a66cd4eea3d7

## Resolution Boundary

The checkout does not currently have a GitHub remote configured, and no local ref named
claude/eloquent-meitner-lqxu9r exists under .git\refs. The exact PR #1 patch cannot
be fetched from this workspace without the owner/repo identifier or a configured remote.

This prep therefore compares the committed local baseline plus known local refs against the
July 4-7 working tree in F:\NPL전례\avm_project and marks what should be carried into the
PR branch once that branch is available.

## Carry Forward

| Area | Include | Why |
|---|---|---|
| Session 24 API reliability | app/api/routes.py; app/api/routes_rag.py; app/avm/engine.py; app/main.py; scripts/session24_api_live_smoke.py; SESSION_24_*; results/session24_api_live_smoke_20260704.* | Adds explicit response models, no-comparable diagnostics, degraded RAG health contract, and smoke evidence. |
| Session 25A coverage QA | scripts/session25_coverage_diagnostic.py; scripts/session25_coverage_verifier.py; config/session25_*candidates.json; SESSION_25*; results/session25_coverage_*; results/session25_comparable_candidate_queue_20260704.* | Already implemented dry-run comparable coverage diagnostics. Do not rebuild; preserve evidence and review-only candidate state. |
| Session 25B approval gate | scripts/session25b_approved_dryrun.py; scripts/session25b_dryrun_verifier.py; config/session25b_approved_rules.json; results/session25b_* | Empty approval file is intentional: AWAITING_HUMAN_APPROVAL, zero approved rules, zero preview rows, and no estimator mutation. |
| Phase 7 Track C/D | scripts/phase7_c_address_parser_v2.py; scripts/phase7_d_hammer_rate_model.py; results/phase7_c_*; results/phase7_d_hammer_rate_report.md | Track C improves address parsing; Track D is important because it exposes leakage/outlier risk and prevents overclaiming model quality. |
| RTMS collection hardening | app/integrations/korea_api.py; scripts/fetch_transactions_parallel.py; .gitignore | Updates data.go.kr endpoints, supports multiple runtime key env names, redacts service keys in errors, raises explicit API failures, and prevents checkpoint JSON from being accidentally committed. |
| W64/W65 VWorld control plane | scripts/vworld_multi_layer_collector.py; results/w64_vworld_multi_layer_control_plane_report_20260707.md; results/w65_vworld_runtime_probe_*_20260707.md | Adds Rev.4 14-layer registry/probe/QA CLI, no-key safe-stop, prompt/stdin runtime key handling, and secret-free ledger metadata. |
| Current project routing docs | PROJECT_MASTER_INDEX.md; TEAM_QUICK_START_KIT.md; PHASE1_TEAM_EXECUTION_GUIDE.md; PROJECT_SEQUENCING_ANALYSIS.md; REALTIME_MONITORING_SYSTEM.md; REAL_AUCTION_DATA_ANALYSIS.md | Useful as planning/routing docs only after stale or speculative status is clearly marked as plan or pending evidence. |

## Leave Out

| Area | Exclude from PR update | Reason |
|---|---|---|
| Python bytecode | app/**/__pycache__/*.pyc | Generated artifacts; tracked modifications should not be used as evidence of code work. |
| Model binaries | models/*.pkl unless explicitly required | Generated binary state; include only with a model-card/evaluation gate. |
| Runtime data roots | F:\loan4u_avm_data\... | External runtime evidence/output, not source code. Reports may reference these paths. |
| Local checkpoint files | data/*checkpoint*.json | Runtime resume state; now ignored. |
| Fiction quarantine | _FICTION_QUARANTINE/ | Deliberately separated non-authoritative or fictionalized material; now ignored. |

## Already Handled, Do Not Redo

- Session 25A diagnostic already found the real blocker: 경기도 / 화성시 / 아파트
  with NO_SOURCE_BACKED_COMPARABLES, appraisal_candidate_count=0, and
  transaction_candidate_count=0.
- Session 25B already has the correct safe state: config/session25b_approved_rules.json
  is intentionally empty until a human adds approved rule IDs.
- W64/W65 already built the VWorld control-plane and runtime-key safe-stop. The next
  VWorld step is a live probe with a runtime-entered key, not another registry rewrite.

## Verification Targets Before PR Push

PowerShell command for compile check:

    C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe -m py_compile scripts\session24_api_live_smoke.py scripts\session25_coverage_diagnostic.py scripts\session25_coverage_verifier.py scripts\session25b_approved_dryrun.py scripts\session25b_dryrun_verifier.py scripts\vworld_multi_layer_collector.py

PowerShell command for no-key VWorld safe-stop:

    C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py probe-endpoints --root F:\loan4u_avm_data\vworld_wfs_multi_layer --write

Expected no-key result: WAITING_RUNTIME_KEY, terminal_errors=0, and no persisted secret.

PowerShell command for VWorld QA:

    C:\Users\eungk\AppData\Local\Programs\Python\Python312\python.exe scripts\vworld_multi_layer_collector.py qa --root F:\loan4u_avm_data\vworld_wfs_multi_layer --write

Expected result: overall=PASS.

## GitHub Follow-Up

Once the GitHub repo is known, fetch the PR branch, then apply only the carry-forward set above.
Do not merge the whole working tree blindly: the current local tree also contains generated
bytecode, model binaries, runtime result files, and quarantined material.
