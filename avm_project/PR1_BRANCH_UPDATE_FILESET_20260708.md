# PR #1 Branch Update File Set

Use this after the real PR branch is fetched or checked out. The goal is to stage only source, config, planning docs, and evidence that updates claude/eloquent-meitner-lqxu9r to the July 4-7 local work without dragging in generated noise.

## Required Source And Config

- .gitignore
- app/api/routes.py
- app/api/routes_rag.py
- app/avm/engine.py
- app/integrations/korea_api.py
- app/main.py
- config/session25_property_type_taxonomy_candidates.json
- config/session25_sigungu_crosswalk_candidates.json
- config/session25b_approved_rules.json
- scripts/fetch_transactions_parallel.py
- scripts/phase7_match_engine.py
- scripts/phase7_grounded_avm.py
- scripts/phase7_c_address_parser_v2.py
- scripts/phase7_d_hammer_rate_model.py
- scripts/session24_api_live_smoke.py
- scripts/session25_coverage_diagnostic.py
- scripts/session25_coverage_verifier.py
- scripts/session25b_approved_dryrun.py
- scripts/session25b_dryrun_verifier.py
- scripts/vworld_multi_layer_collector.py

## Required Planning And Completion Docs

- PR1_BRANCH_UPDATE_PREP_20260708.md
- PR1_BRANCH_UPDATE_FILESET_20260708.md
- SESSION_21_COMPLETION_REPORT.md
- SESSION_21_PHASE7_DETAILED_SPEC_WBS.md
- SESSION_22_COMPLETION_REPORT.md
- SESSION_22_DETAILED_SPEC_WBS.md
- SESSION_23_DETAILED_SPEC_WBS.md
- SESSION_24_API_RELIABILITY_DETAILED_SPEC_20260704.md
- SESSION_24_API_RELIABILITY_WBS_EXECUTION_REPORT_20260704.md
- SESSION_24_NEXT_WORK_DETAILED_SPEC_WBS_20260704.md
- SESSION_24_NEXT_WORK_DETAILED_SPEC_WBS_v2_20260704.md
- SESSION_25_COMPARABLE_COVERAGE_DRAFT_SPEC_20260704.md
- SESSION_25_SPEC_REVIEW_NOTES_20260704.md
- SESSION_25A_COMPARABLE_COVERAGE_FINAL_SPEC_WBS_20260704.md
- SESSION_25A_PRIORITY_EXECUTION_PLAN_20260704.md
- SESSION_25A_COMPLETION_REPORT_20260704.md
- SESSION_25B_APPROVED_DRYRUN_DETAILED_PLAN_SPEC_WBS_20260704.md
- SESSION_25B_SPEC_REVIEW_NOTES_20260704.md
- SESSION_25B_PRIORITY_EXECUTION_PLAN_20260704.md
- SESSION_25B_COMPLETION_REPORT_20260704.md
- AVM_REAL_DATA_COLLECTION_SPECIFICATION.md
- AVM_REAL_DATA_COLLECTION_WBS.md
- AVM_REAL_DATA_COLLECTION_EXECUTION_PLAN.md
- API_KEY_PILOT_TEST_REPORT_20260704.md
- DOCUMENT_REVIEW_FINDINGS.md
- PROJECT_SEQUENCING_ANALYSIS.md
- PHASE1_TEAM_EXECUTION_GUIDE.md
- TEAM_QUICK_START_KIT.md
- PROJECT_MASTER_INDEX.md
- REALTIME_MONITORING_SYSTEM.md
- REAL_AUCTION_DATA_ANALYSIS.md

## Evidence Results To Carry Forward

- results/phase7_match_report.md
- results/phase7_matched_pairs.csv
- results/phase7_final_report.md
- results/phase7_c_match_improvement.md
- results/phase7_c_validation_set_v2.csv
- results/phase7_d_hammer_rate_report.md
- results/session24_api_live_smoke_20260704.json
- results/session24_api_live_smoke_20260704.md
- results/session25_planning_probe_20260704.json
- results/session25_coverage_diagnostic_20260704.json
- results/session25_coverage_diagnostic_20260704.md
- results/session25_comparable_candidate_queue_20260704.json
- results/session25_comparable_candidate_queue_20260704.csv
- results/session25_sigungu_crosswalk_report_20260704.md
- results/session25_property_type_taxonomy_report_20260704.md
- results/session25_coverage_verifier_20260704.json
- results/session25_coverage_verifier_20260704.md
- results/session25b_candidate_review_packet_20260704.md
- results/session25b_approved_dryrun_20260704.json
- results/session25b_approved_dryrun_20260704.md
- results/session25b_dryrun_verifier_20260704.json
- results/session25b_dryrun_verifier_20260704.md
- results/w64_vworld_multi_layer_control_plane_report_20260707.md
- results/w65_vworld_runtime_probe_plan_spec_wbs_reviewed_20260707.md
- results/w65_vworld_runtime_probe_execution_report_20260707.md

## Do Not Stage For PR #1 Update

- app/**/__pycache__/*.pyc
- models/*.pkl unless a separate model artifact review is requested
- data/*checkpoint*.json
- F:\loan4u_avm_data\...
- _FICTION_QUARANTINE/
- avm_project/pytest.ini unless a separate test-config review is requested; preserve the PR branch markers/addopts
- Any future-dated or production-complete claim unless backed by a current verifier output

## Verification Snapshot From 2026-07-08

- py_compile for carry-forward scripts: PASS.
- VWorld no-key probe: WAITING_RUNTIME_KEY, terminal_errors=0.
- VWorld QA: PASS, secret_literal_scan PASS.
- Session 25A verifier: PASS, 5 checks.
- Session 25B verifier: PASS, AWAITING_APPROVAL, preview_rows=0.
- pytest: test assertions reached 4 passed, then the runner hung before process exit and was stopped. Treat as partial process-exit risk, not assertion failure.

## Newly Observed But Not Included

These appeared in the working tree during the prep pass and were not reviewed for PR #1 scope:

- _d_drive_full_lineage_20260708_1215/
- _d_drive_session25b_code_review_20260708_1200/
- results/d_drive_full_lineage_correction_report_20260708.md
- results/d_drive_session25b_code_review_report_20260708.md
- results/d_drive_sessions_1_22_backfill_report_20260708.md
- results/overall_work_status_report_20260708.md

Do not stage them for the PR #1 branch update unless a separate review says they belong.
