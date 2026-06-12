# 주유소 PNU/NPL 검색 서비스 상용화 문서 패키지

작성일: 2026-06-01

이 문서 패키지는 전국 주유소 PNU 기반 영업이력/NPL 분석 데이터를 상용 검색 서비스로 제공하기 위한 개발 기준서다. 2026-06-01 외부 적정성 검토 의견을 반영해 Sprint 0, 라이선스 게이트, V1 범위 축소, 검색 뷰 정정, 위험등급 보류 원칙을 업데이트했다.

## 최신 실행 산출물: 2026-06-12 G3~G12 통과 실행팩

|파일|용도|
|---|---|
|[docs/1174_planning_future_gap_workpack_20260612.md](docs/1174_planning_future_gap_workpack_20260612.md)|현재 용도지역-only 4,752시설 미래영향 추가 workpack 생성 보고|
|[docs/1175_completion_execution_board_after_planning_future_gap_20260612.md](docs/1175_completion_execution_board_after_planning_future_gap_20260612.md)|신규 G11 workpack을 반영한 100% 통합 실행보드|
|[docs/1176_gate_pass_gap_projection_after_planning_future_gap_20260612.md](docs/1176_gate_pass_gap_projection_after_planning_future_gap_20260612.md)|G11/G12 통과 필요량과 실행보드 가용량 재산정|
|[docs/1177_gate_pass_minimum_batch_queue_after_planning_future_gap_20260612.md](docs/1177_gate_pass_minimum_batch_queue_after_planning_future_gap_20260612.md)|G3~G12 통과를 위한 최소 배치 큐 최신판|
|[docs/1178_platform_qa_suite_after_planning_future_gap_20260612.md](docs/1178_platform_qa_suite_after_planning_future_gap_20260612.md)|QA suite g77, API 포함 22/22 PASS 보고|
|[docs/1179_platform_completion_gate_after_planning_future_gap_20260612.md](docs/1179_platform_completion_gate_after_planning_future_gap_20260612.md)|완료 게이트 최신판, 6 PASS / 10 FAIL|
|[docs/1180_planning_future_gap_workpack_implementation_report_20260612.md](docs/1180_planning_future_gap_workpack_implementation_report_20260612.md)|G11/G12 workpack 구현·검증·WBS 종합 보고|
|[docs/1181_minimum_batch_operator_bundle_20260612.md](docs/1181_minimum_batch_operator_bundle_20260612.md)|G3~G12 최소 통과 배치 362개 작업자용 운영 bundle|
|[docs/1182_platform_qa_suite_after_minimum_operator_bundle_20260612.md](docs/1182_platform_qa_suite_after_minimum_operator_bundle_20260612.md)|운영 bundle 추가 후 QA suite g78, API 포함 22/22 PASS 보고|
|[docs/1183_platform_completion_gate_after_minimum_operator_bundle_20260612.md](docs/1183_platform_completion_gate_after_minimum_operator_bundle_20260612.md)|운영 bundle 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1184_minimum_batch_operator_bundle_implementation_report_20260612.md](docs/1184_minimum_batch_operator_bundle_implementation_report_20260612.md)|최소 배치 운영 bundle 구현·검증·다음 실행 기준 보고|
|[docs/1185_minimum_batch_operator_preflight_20260612.md](docs/1185_minimum_batch_operator_preflight_20260612.md)|최소 배치 운영 bundle 결과양식 preflight, READY 0개 판정|
|[docs/1186_platform_qa_suite_after_minimum_operator_preflight_20260612.md](docs/1186_platform_qa_suite_after_minimum_operator_preflight_20260612.md)|운영 bundle preflight 추가 후 QA suite g79, API 포함 22/22 PASS 보고|
|[docs/1187_platform_completion_gate_after_minimum_operator_preflight_20260612.md](docs/1187_platform_completion_gate_after_minimum_operator_preflight_20260612.md)|운영 bundle preflight 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1188_minimum_batch_operator_preflight_implementation_report_20260612.md](docs/1188_minimum_batch_operator_preflight_implementation_report_20260612.md)|운영 bundle preflight 구현·검증·다음 실행 조건 보고|
|[docs/1189_platform_qa_suite_after_minimum_preflight_api_ui_20260612.md](docs/1189_platform_qa_suite_after_minimum_preflight_api_ui_20260612.md)|최소 배치 결과양식 점검 API/UI 반영 후 QA suite g80, API 포함 22/22 PASS 보고|
|[docs/1190_platform_completion_gate_after_minimum_preflight_api_ui_20260612.md](docs/1190_platform_completion_gate_after_minimum_preflight_api_ui_20260612.md)|최소 배치 결과양식 점검 API/UI 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1191_minimum_preflight_api_ui_implementation_report_20260612.md](docs/1191_minimum_preflight_api_ui_implementation_report_20260612.md)|최소 배치 결과양식 점검 API/UI 구현·검증·다음 실행 조건 보고|
|[docs/1192_minimum_batch_execution_plan_20260612.md](docs/1192_minimum_batch_execution_plan_20260612.md)|최소 배치 실행대장 생성, Dry-run 가능 0개·입력대기 361개·모델대기 1개 보고|
|[docs/1193_platform_qa_suite_after_minimum_execution_plan_20260612.md](docs/1193_platform_qa_suite_after_minimum_execution_plan_20260612.md)|최소 배치 실행대장 반영 후 QA suite g81, API 포함 22/22 PASS 보고|
|[docs/1194_platform_completion_gate_after_minimum_execution_plan_20260612.md](docs/1194_platform_completion_gate_after_minimum_execution_plan_20260612.md)|최소 배치 실행대장 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1195_minimum_batch_execution_plan_implementation_report_20260612.md](docs/1195_minimum_batch_execution_plan_implementation_report_20260612.md)|최소 배치 실행대장 DB/API/UI 구현·검증·다음 실행 조건 보고|
|[docs/1196_internal_uplift_opportunity_audit_20260612.md](docs/1196_internal_uplift_opportunity_audit_20260612.md)|내부 데이터만으로 즉시 coverage 상향 가능한지 감사, 즉시 적용 0건 판정|
|[docs/1197_internal_same_address_pnu_dryrun_20260612.md](docs/1197_internal_same_address_pnu_dryrun_20260612.md)|동일 주소 기반 PNU 내부 보강 dry-run, ready match 0건 판정|
|[docs/1198_geocode_api_key_preflight_20260612.md](docs/1198_geocode_api_key_preflight_20260612.md)|주소 API key preflight, `KEY_NOT_CONFIGURED` 및 pending 6,094건 보고|
|[docs/1199_pnu_geocode_priority_pack_20260612.md](docs/1199_pnu_geocode_priority_pack_20260612.md)|PNU·좌표 우선 수집팩 7,575건 생성, P0 1,887건 확정|
|[docs/1200_platform_qa_suite_after_pnu_geocode_priority_pack_20260612.md](docs/1200_platform_qa_suite_after_pnu_geocode_priority_pack_20260612.md)|PNU·좌표 우선 수집팩 테이블 추가 후 QA suite g82 PASS 보고|
|[docs/1201_platform_completion_gate_after_pnu_geocode_priority_pack_20260612.md](docs/1201_platform_completion_gate_after_pnu_geocode_priority_pack_20260612.md)|PNU·좌표 우선 수집팩 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1202_platform_qa_suite_db_code_after_pnu_geocode_priority_api_ui_20260612.md](docs/1202_platform_qa_suite_db_code_after_pnu_geocode_priority_api_ui_20260612.md)|PNU·좌표 API/UI 반영 후 DB/코드 QA g84, 19/19 PASS 보고|
|[docs/1203_platform_completion_gate_after_pnu_geocode_priority_api_ui_20260612.md](docs/1203_platform_completion_gate_after_pnu_geocode_priority_api_ui_20260612.md)|PNU·좌표 API/UI 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1204_platform_qa_suite_api_ui_after_pnu_geocode_priority_api_ui_20260612.md](docs/1204_platform_qa_suite_api_ui_after_pnu_geocode_priority_api_ui_20260612.md)|PNU·좌표 API/UI 반영 후 HTTP API/UI smoke g84, 5/5 PASS 보고|
|[docs/1205_pnu_geocode_priority_pack_api_ui_implementation_report_20260612.md](docs/1205_pnu_geocode_priority_pack_api_ui_implementation_report_20260612.md)|PNU·좌표 우선 수집팩 DB/API/UI 구현·검증·다음 실행 WBS 보고|
|[docs/1206_pnu_geocode_priority_queue_seed_dryrun_20260612.md](docs/1206_pnu_geocode_priority_queue_seed_dryrun_20260612.md)|P0 PNU·좌표 우선팩 geocode request 큐 주입 최초 dry-run, 신규 가능 1,738건 확인|
|[docs/1207_pnu_geocode_priority_queue_seed_20260612.md](docs/1207_pnu_geocode_priority_queue_seed_20260612.md)|P0 PNU·좌표 geocode READY 큐 최종 주입, 신규 34건·중복 1,853건 보고|
|[docs/1208_pnu_geocode_priority_queue_seed_optimized_dryrun_20260612.md](docs/1208_pnu_geocode_priority_queue_seed_optimized_dryrun_20260612.md)|큐 주입 스크립트 최적화 후 dry-run, 잔여 신규 가능 34건 확인|
|[docs/1209_pnu_geocode_priority_queue_seed_post_import_dryrun_20260612.md](docs/1209_pnu_geocode_priority_queue_seed_post_import_dryrun_20260612.md)|P0 큐 주입 완료 검산, 추가 가능 0건·중복 1,887건 확인|
|[docs/1210_g3_geocode_api_batch_dry_check_after_p0_queue_seed_20260612.md](docs/1210_g3_geocode_api_batch_dry_check_after_p0_queue_seed_20260612.md)|G3 주소 API 배치 dry-check, 대기 7,832건·key 미설정 차단 보고|
|[docs/1211_platform_qa_suite_db_code_after_p0_queue_seed_20260612.md](docs/1211_platform_qa_suite_db_code_after_p0_queue_seed_20260612.md)|P0 큐 주입 후 DB/코드 QA suite g85, 19/19 PASS 보고|
|[docs/1212_platform_completion_gate_after_p0_queue_seed_20260612.md](docs/1212_platform_completion_gate_after_p0_queue_seed_20260612.md)|P0 큐 주입 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1213_platform_qa_suite_api_ui_after_p0_queue_seed_20260612.md](docs/1213_platform_qa_suite_api_ui_after_p0_queue_seed_20260612.md)|P0 큐 주입 API/UI 반영 후 HTTP smoke g85, 5/5 PASS 보고|
|[docs/1214_p0_pnu_geocode_queue_seed_implementation_report_20260612.md](docs/1214_p0_pnu_geocode_queue_seed_implementation_report_20260612.md)|P0 PNU·좌표 geocode READY 큐 주입 구현·검증·다음 실행 조건 보고|
|[docs/P0_geocode_queue_seed_dryrun_20260612_102837.md](docs/P0_geocode_queue_seed_dryrun_20260612_102837.md)|P0 secure pipeline dry-check 큐 검산, 추가 가능 0건 확인|
|[docs/P0_geocode_key_preflight_20260612_102837.md](docs/P0_geocode_key_preflight_20260612_102837.md)|P0 secure pipeline 주소 API key preflight, `KEY_NOT_CONFIGURED`·대기 7,832건 보고|
|[docs/1215_platform_qa_suite_db_code_after_p0_secure_pipeline_20260612.md](docs/1215_platform_qa_suite_db_code_after_p0_secure_pipeline_20260612.md)|P0 secure pipeline 추가 후 DB/코드 QA suite, 19/19 PASS 보고|
|[docs/1216_platform_completion_gate_after_p0_secure_pipeline_20260612.md](docs/1216_platform_completion_gate_after_p0_secure_pipeline_20260612.md)|P0 secure pipeline 추가 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1217_p0_geocode_secure_pipeline_implementation_report_20260612.md](docs/1217_p0_geocode_secure_pipeline_implementation_report_20260612.md)|P0 주소 API secure pipeline 구현·검증·실행 방법 보고|
|[docs/1218_platform_qa_suite_api_ui_after_p0_secure_pipeline_20260612.md](docs/1218_platform_qa_suite_api_ui_after_p0_secure_pipeline_20260612.md)|P0 secure pipeline 추가 후 API/UI smoke, 5/5 PASS 보고|
|[docs/1219_p0_geocode_execution_monitor_dryrun_20260612.md](docs/1219_p0_geocode_execution_monitor_dryrun_20260612.md)|P0 주소 API 실행 모니터 dry-run, 1,887개 READY_FOR_API 확인|
|[docs/1220_p0_geocode_execution_monitor_20260612.md](docs/1220_p0_geocode_execution_monitor_20260612.md)|P0 주소 API 실행 모니터 DB 적재 보고|
|[docs/1221_platform_qa_suite_db_code_after_p0_geocode_monitor_20260612.md](docs/1221_platform_qa_suite_db_code_after_p0_geocode_monitor_20260612.md)|P0 실행 모니터 추가 후 DB/코드 QA suite g86, 19/19 PASS 보고|
|[docs/1222_platform_completion_gate_after_p0_geocode_monitor_20260612.md](docs/1222_platform_completion_gate_after_p0_geocode_monitor_20260612.md)|P0 실행 모니터 추가 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1223_platform_qa_suite_api_ui_after_p0_geocode_monitor_20260612.md](docs/1223_platform_qa_suite_api_ui_after_p0_geocode_monitor_20260612.md)|P0 실행 모니터 API/UI smoke g86, 5/5 PASS 보고|
|[docs/1224_p0_geocode_execution_monitor_implementation_report_20260612.md](docs/1224_p0_geocode_execution_monitor_implementation_report_20260612.md)|P0 주소 API 실행 모니터 DB/API/UI 구현·검증·다음 실행 보고|
|[docs/1225_g3_geocode_one_request_per_site_dry_check_20260612.md](docs/1225_g3_geocode_one_request_per_site_dry_check_20260612.md)|시설당 1건 주소 API 호출 dry-check, 7,832 요청행·6,094 시설·중복 1,738행 확인|
|[docs/1226_platform_qa_suite_db_code_after_one_request_per_site_20260612.md](docs/1226_platform_qa_suite_db_code_after_one_request_per_site_20260612.md)|시설당 1건 호출 옵션 반영 후 DB/코드 QA suite, 19/19 PASS 보고|
|[docs/1227_platform_completion_gate_after_one_request_per_site_20260612.md](docs/1227_platform_completion_gate_after_one_request_per_site_20260612.md)|시설당 1건 호출 옵션 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1228_platform_qa_suite_api_ui_after_one_request_per_site_20260612.md](docs/1228_platform_qa_suite_api_ui_after_one_request_per_site_20260612.md)|시설당 1건 호출 옵션 반영 후 API/UI smoke, 5/5 PASS 보고|
|[docs/1229_one_request_per_site_geocode_batch_implementation_report_20260612.md](docs/1229_one_request_per_site_geocode_batch_implementation_report_20260612.md)|시설별 최우선 주소 요청 1건만 호출하도록 API 배치 최적화 구현·검증·WBS 보고|
|[docs/1230_p0_geocode_execution_monitor_with_effective_calls_20260612.md](docs/1230_p0_geocode_execution_monitor_with_effective_calls_20260612.md)|P0 주소 API 모니터에 READY 요청행·실효 호출·중복 READY 지표 추가 적재|
|[docs/1231_platform_qa_suite_db_code_after_p0_effective_call_monitor_20260612.md](docs/1231_platform_qa_suite_db_code_after_p0_effective_call_monitor_20260612.md)|P0 실효 호출 모니터 반영 후 DB/코드 QA suite, 19/19 PASS 보고|
|[docs/1232_platform_completion_gate_after_p0_effective_call_monitor_20260612.md](docs/1232_platform_completion_gate_after_p0_effective_call_monitor_20260612.md)|P0 실효 호출 모니터 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1233_platform_qa_suite_api_ui_after_p0_effective_call_monitor_20260612.md](docs/1233_platform_qa_suite_api_ui_after_p0_effective_call_monitor_20260612.md)|P0 실효 호출 모니터 반영 후 API/UI smoke, 5/5 PASS 보고|
|[docs/1234_p0_effective_call_monitor_implementation_report_20260612.md](docs/1234_p0_effective_call_monitor_implementation_report_20260612.md)|P0 주소 API 실효 호출 모니터 DB/API/UI 구현·검증·다음 실행 조건 보고|
|[docs/1235_100pct_control_tower_20260612.md](docs/1235_100pct_control_tower_20260612.md)|G3~G12 실패 Gate 10개를 결과양식·필수필드·다음 명령 기준으로 묶은 100% 도달 관제 보드|
|[docs/1236_platform_qa_suite_db_code_after_100pct_control_tower_20260612.md](docs/1236_platform_qa_suite_db_code_after_100pct_control_tower_20260612.md)|100% 도달 관제 보드 반영 후 DB/코드 QA suite, 19/19 PASS 보고|
|[docs/1237_platform_completion_gate_after_100pct_control_tower_20260612.md](docs/1237_platform_completion_gate_after_100pct_control_tower_20260612.md)|100% 도달 관제 보드 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1238_platform_qa_suite_api_ui_after_100pct_control_tower_20260612.md](docs/1238_platform_qa_suite_api_ui_after_100pct_control_tower_20260612.md)|100% 도달 관제 보드 API 추가 후 API/UI smoke, 5/5 PASS 보고|
|[docs/1239_100pct_control_tower_implementation_report_20260612.md](docs/1239_100pct_control_tower_implementation_report_20260612.md)|100% 도달 관제 보드 DB/API/QA 구현·검증·다음 실행 보고|
|[docs/1240_auction_provider_secure_access_preflight_current_session_20260612.md](docs/1240_auction_provider_secure_access_preflight_current_session_20260612.md)|인포케어·옥션원 ID/PW 미보유와 브라우저 로그인 필요 상태를 현재 세션 기준으로 재확인|
|[docs/1241_platform_completion_gate_after_auction_provider_preflight_refresh_20260612.md](docs/1241_platform_completion_gate_after_auction_provider_preflight_refresh_20260612.md)|경매 Provider 보안접속 재점검 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1242_platform_qa_suite_db_code_after_auction_provider_preflight_refresh_20260612.md](docs/1242_platform_qa_suite_db_code_after_auction_provider_preflight_refresh_20260612.md)|경매 Provider 보안접속 재점검 후 DB/코드 QA suite, 19/19 PASS 보고|
|[docs/1243_platform_qa_suite_api_ui_after_auction_provider_preflight_refresh_20260612.md](docs/1243_platform_qa_suite_api_ui_after_auction_provider_preflight_refresh_20260612.md)|경매 Provider 보안접속 재점검 후 API/UI smoke, 5/5 PASS 보고|
|[docs/1244_threshold_result_workpack_after_current_auction_no_case_guard_20260612.md](docs/1244_threshold_result_workpack_after_current_auction_no_case_guard_20260612.md)|현재경매 없음 증빙 강화 후 G3~G12 threshold 결과양식 128,521행 재생성|
|[docs/1245_100pct_control_tower_after_current_auction_no_case_guard_20260612.md](docs/1245_100pct_control_tower_after_current_auction_no_case_guard_20260612.md)|현재경매 없음 증빙 강화 후 100% 관제 보드 1차 갱신|
|[docs/1246_platform_completion_gate_after_current_auction_no_case_guard_20260612.md](docs/1246_platform_completion_gate_after_current_auction_no_case_guard_20260612.md)|병렬 QA 순서상 최신 QA 5건을 읽은 임시 완료 게이트, 후속 1249로 대체|
|[docs/1247_platform_qa_suite_db_code_after_current_auction_no_case_guard_20260612.md](docs/1247_platform_qa_suite_db_code_after_current_auction_no_case_guard_20260612.md)|현재경매 없음 증빙 강화 후 DB/코드 QA suite, 19/19 PASS 보고|
|[docs/1248_platform_qa_suite_full_after_current_auction_no_case_guard_20260612.md](docs/1248_platform_qa_suite_full_after_current_auction_no_case_guard_20260612.md)|현재경매 없음 증빙 강화 후 API 포함 전체 QA suite, 22/22 PASS 보고|
|[docs/1249_platform_completion_gate_after_full_qa_current_auction_no_case_guard_20260612.md](docs/1249_platform_completion_gate_after_full_qa_current_auction_no_case_guard_20260612.md)|최종 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1250_100pct_control_tower_after_full_qa_current_auction_no_case_guard_20260612.md](docs/1250_100pct_control_tower_after_full_qa_current_auction_no_case_guard_20260612.md)|최종 100% 관제 보드, 실패 Gate 10개·입력 대기 361개|
|[docs/1251_current_auction_no_case_guard_implementation_report_20260612.md](docs/1251_current_auction_no_case_guard_implementation_report_20260612.md)|현재경매 없음도 확인일과 원천증빙이 모두 있어야 import되도록 강화한 구현 보고|
|[docs/1252_100pct_control_tower_with_threshold_required_fields_20260612.md](docs/1252_100pct_control_tower_with_threshold_required_fields_20260612.md)|100% 관제 보드 필수필드와 결과양식 경로를 threshold workpack 기준으로 갱신|
|[docs/1253_100pct_control_tower_threshold_commands_20260612.md](docs/1253_100pct_control_tower_threshold_commands_20260612.md)|100% 관제 보드 다음 명령을 threshold runner 기준으로 정렬|
|[docs/1254_platform_qa_suite_full_after_control_tower_threshold_commands_20260612.md](docs/1254_platform_qa_suite_full_after_control_tower_threshold_commands_20260612.md)|관제 보드 threshold 명령 정렬 후 전체 QA suite, 23/23 PASS 보고|
|[docs/1255_platform_completion_gate_after_control_tower_threshold_commands_20260612.md](docs/1255_platform_completion_gate_after_control_tower_threshold_commands_20260612.md)|관제 보드 threshold 명령 정렬 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1256_100pct_control_tower_after_completion_gate_threshold_commands_20260612.md](docs/1256_100pct_control_tower_after_completion_gate_threshold_commands_20260612.md)|최종 100% 관제 보드, 실패 Gate 10개·추가 필요 Gate-시설 64,292개|
|[docs/1257_control_tower_threshold_command_alignment_report_20260612.md](docs/1257_control_tower_threshold_command_alignment_report_20260612.md)|100% 관제 보드 결과양식·필수필드·다음 명령을 threshold 기준으로 정렬한 구현 보고|
|[docs/1258_next_input_operator_brief_threshold_aligned_20260612.md](docs/1258_next_input_operator_brief_threshold_aligned_20260612.md)|다음 입력 운영 브리프를 최신 threshold 결과양식·증빙 필드 기준으로 재생성|
|[docs/1259_platform_qa_suite_full_after_next_input_brief_threshold_alignment_20260612.md](docs/1259_platform_qa_suite_full_after_next_input_brief_threshold_alignment_20260612.md)|운영 브리프 threshold 정렬 후 전체 QA suite, 24/24 PASS 보고|
|[docs/1260_platform_completion_gate_after_next_input_brief_threshold_alignment_20260612.md](docs/1260_platform_completion_gate_after_next_input_brief_threshold_alignment_20260612.md)|운영 브리프 threshold 정렬 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1261_100pct_control_tower_after_next_input_brief_threshold_alignment_20260612.md](docs/1261_100pct_control_tower_after_next_input_brief_threshold_alignment_20260612.md)|운영 브리프 threshold 정렬 후 최종 100% 관제 보드 재계산|
|[docs/1262_next_input_operator_brief_threshold_alignment_report_20260612.md](docs/1262_next_input_operator_brief_threshold_alignment_report_20260612.md)|다음 입력 운영 브리프를 threshold 기준으로 정렬한 구현 보고|
|[docs/1263_platform_qa_suite_full_after_threshold_gate_input_preflight_20260612.md](docs/1263_platform_qa_suite_full_after_threshold_gate_input_preflight_20260612.md)|threshold 입력 preflight 추가 후 전체 QA suite, 25/25 PASS 보고|
|[docs/1264_platform_action_preflight_after_threshold_input_guard_20260612.md](docs/1264_platform_action_preflight_after_threshold_input_guard_20260612.md)|G7/G8 증빙 기준 강화 후 플랫폼 action preflight 재생성|
|[docs/1265_minimum_batch_operator_preflight_after_threshold_input_guard_20260612.md](docs/1265_minimum_batch_operator_preflight_after_threshold_input_guard_20260612.md)|G7/G8 증빙 기준 강화 후 최소 배치 운영 preflight 재생성|
|[docs/1266_platform_qa_suite_full_after_preflight_db_refresh_20260612.md](docs/1266_platform_qa_suite_full_after_preflight_db_refresh_20260612.md)|preflight DB 갱신 후 전체 QA suite, 25/25 PASS 보고|
|[docs/1267_platform_completion_gate_after_threshold_input_guard_20260612.md](docs/1267_platform_completion_gate_after_threshold_input_guard_20260612.md)|threshold 입력 guard 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1269_100pct_control_tower_after_completion_gate_threshold_input_guard_20260612.md](docs/1269_100pct_control_tower_after_completion_gate_threshold_input_guard_20260612.md)|threshold 입력 guard 반영 후 100% 관제 보드 최종 재계산|
|[docs/1270_threshold_gate_input_preflight_implementation_report_20260612.md](docs/1270_threshold_gate_input_preflight_implementation_report_20260612.md)|빈 결과양식·증빙 누락·부분 import 차단 구현 및 다음 WBS 보고|
|[docs/1271_auction_case_quality_after_case_resolution_pack_smoke_20260612.md](docs/1271_auction_case_quality_after_case_resolution_pack_smoke_20260612.md)|경매 사건번호 품질 재판정, 117행 모두 provider 관리번호·법원 사건번호 0건 확인|
|[docs/1272_auction_case_resolution_pack_after_smoke_guard_20260612.md](docs/1272_auction_case_resolution_pack_after_smoke_guard_20260612.md)|과거경매 관리번호→법원 사건번호 보정팩 76행/49시설 재생성|
|[docs/1273_current_auction_reference_resolution_pack_after_smoke_guard_20260612.md](docs/1273_current_auction_reference_resolution_pack_after_smoke_guard_20260612.md)|현재/예정 경매 관리번호 보정팩 1행/1시설 재생성|
|[docs/1274_platform_qa_suite_full_after_auction_case_resolution_pack_smoke_20260612.md](docs/1274_platform_qa_suite_full_after_auction_case_resolution_pack_smoke_20260612.md)|경매 보정팩 smoke guard 추가 후 전체 QA suite, 26/26 PASS 보고|
|[docs/1275_platform_completion_gate_after_auction_case_resolution_pack_smoke_20260612.md](docs/1275_platform_completion_gate_after_auction_case_resolution_pack_smoke_20260612.md)|경매 보정팩 smoke guard 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1277_100pct_control_tower_after_completion_gate_auction_case_resolution_pack_smoke_20260612.md](docs/1277_100pct_control_tower_after_completion_gate_auction_case_resolution_pack_smoke_20260612.md)|경매 보정팩 smoke guard 반영 후 100% 관제 보드 최종 재계산|
|[docs/1278_auction_case_resolution_pack_smoke_guard_implementation_report_20260612.md](docs/1278_auction_case_resolution_pack_smoke_guard_implementation_report_20260612.md)|관리번호를 법원 사건번호로 오인하지 않도록 보정팩 smoke guard 구현 보고|
|[docs/1279_platform_action_queue_after_current_auction_secondary_pack_link_20260612.md](docs/1279_platform_action_queue_after_current_auction_secondary_pack_link_20260612.md)|G8 현재경매 보정팩을 플랫폼 action queue 보조 작업팩으로 연결|
|[docs/1280_platform_action_preflight_after_current_auction_secondary_pack_link_20260612.md](docs/1280_platform_action_preflight_after_current_auction_secondary_pack_link_20260612.md)|G8 보정팩 연결 후 action preflight 재생성|
|[docs/1281_external_workpack_manifest_after_current_auction_secondary_pack_link_20260612.md](docs/1281_external_workpack_manifest_after_current_auction_secondary_pack_link_20260612.md)|외부 작업팩 manifest에 현재경매 보정팩 경로 반영|
|[docs/1282_result_file_execution_plan_after_current_auction_secondary_pack_link_20260612.md](docs/1282_result_file_execution_plan_after_current_auction_secondary_pack_link_20260612.md)|외부 결과파일 실행계획 재생성, ready 0개 유지|
|[docs/1283_external_dependency_blockers_after_current_auction_secondary_pack_link_20260612.md](docs/1283_external_dependency_blockers_after_current_auction_secondary_pack_link_20260612.md)|외부 의존 blocker 재산정, open 총 63,470건|
|[docs/1284_platform_qa_suite_full_after_current_auction_secondary_pack_link_20260612.md](docs/1284_platform_qa_suite_full_after_current_auction_secondary_pack_link_20260612.md)|G8 보정팩 연결 검사 추가 후 전체 QA suite 27/27 PASS|
|[docs/1285_platform_completion_gate_after_current_auction_secondary_pack_link_20260612.md](docs/1285_platform_completion_gate_after_current_auction_secondary_pack_link_20260612.md)|최신 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1286_100pct_control_tower_after_current_auction_secondary_pack_link_20260612.md](docs/1286_100pct_control_tower_after_current_auction_secondary_pack_link_20260612.md)|최신 100% 관제 보드, 실패 Gate 10개·입력 대기 361개|
|[docs/1288_current_auction_secondary_pack_link_implementation_report_20260612.md](docs/1288_current_auction_secondary_pack_link_implementation_report_20260612.md)|현재경매 보정팩 운영 큐 연결 구현·검증·WBS 보고|
|[docs/1289_auction_provider_secure_access_preflight_after_account_marker_20260612.md](docs/1289_auction_provider_secure_access_preflight_after_account_marker_20260612.md)|인포케어·옥션원 계정 제공 신호를 비밀번호 저장 없이 preflight에 반영|
|[docs/1290_auction_provider_session_launcher_after_account_marker_20260612.md](docs/1290_auction_provider_session_launcher_after_account_marker_20260612.md)|계정 제공 신호 반영 후 경매 Provider 세션 실행팩 56행 재생성|
|[docs/1291_auction_provider_browser_workboard_after_account_marker_20260612.md](docs/1291_auction_provider_browser_workboard_after_account_marker_20260612.md)|G7/G8 경매 브라우저 작업보드 120행 최신 재생성|
|[docs/1292_platform_qa_suite_full_after_auction_provider_account_marker_20260612.md](docs/1292_platform_qa_suite_full_after_auction_provider_account_marker_20260612.md)|경매 Provider 보안접속 smoke 추가 후 전체 QA suite 28/28 PASS|
|[docs/1293_platform_completion_gate_after_auction_provider_account_marker_20260612.md](docs/1293_platform_completion_gate_after_auction_provider_account_marker_20260612.md)|계정 제공 신호 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1294_100pct_control_tower_after_auction_provider_account_marker_20260612.md](docs/1294_100pct_control_tower_after_auction_provider_account_marker_20260612.md)|계정 제공 신호 반영 후 100% 관제 보드 재계산|
|[docs/1295_auction_provider_account_marker_security_flow_implementation_report_20260612.md](docs/1295_auction_provider_account_marker_security_flow_implementation_report_20260612.md)|경매 Provider 계정 제공 신호 보안 흐름 구현·검증 보고|
|[docs/1296_auction_provider_browser_workboard_with_direct_provider_links_20260612.md](docs/1296_auction_provider_browser_workboard_with_direct_provider_links_20260612.md)|경매 작업보드에 Provider 포털·대법원 직접 링크와 입력 안내 컬럼 추가|
|[docs/1297_platform_qa_suite_full_after_auction_workboard_direct_links_20260612.md](docs/1297_platform_qa_suite_full_after_auction_workboard_direct_links_20260612.md)|경매 작업보드 직접 링크 QA 추가 후 전체 QA suite 29/29 PASS|
|[docs/1298_platform_completion_gate_after_auction_workboard_direct_links_20260612.md](docs/1298_platform_completion_gate_after_auction_workboard_direct_links_20260612.md)|경매 작업보드 직접 링크 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1299_100pct_control_tower_after_auction_workboard_direct_links_20260612.md](docs/1299_100pct_control_tower_after_auction_workboard_direct_links_20260612.md)|경매 작업보드 직접 링크 반영 후 100% 관제 보드 재계산|
|[docs/1300_platform_qa_suite_full_after_service_restart_auction_workboard_direct_links_20260612.md](docs/1300_platform_qa_suite_full_after_service_restart_auction_workboard_direct_links_20260612.md)|서비스 재시작 후 전체 QA suite 29/29 PASS|
|[docs/1301_platform_completion_gate_after_service_restart_auction_workboard_direct_links_20260612.md](docs/1301_platform_completion_gate_after_service_restart_auction_workboard_direct_links_20260612.md)|서비스 재시작 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1302_100pct_control_tower_after_service_restart_auction_workboard_direct_links_20260612.md](docs/1302_100pct_control_tower_after_service_restart_auction_workboard_direct_links_20260612.md)|서비스 재시작 후 100% 관제 보드 재계산|
|[docs/1303_auction_workboard_direct_provider_links_implementation_report_20260612.md](docs/1303_auction_workboard_direct_provider_links_implementation_report_20260612.md)|경매 작업보드 Provider 직접 링크 보강 구현·검증 보고|
|[docs/1304_auction_first_run_priority_pack_20260612.md](docs/1304_auction_first_run_priority_pack_20260612.md)|G7/G8 경매 원천 입력을 시작하기 위한 1차 우선 조회팩 162행 생성|
|[docs/1305_platform_qa_suite_full_after_auction_first_run_priority_pack_20260612.md](docs/1305_platform_qa_suite_full_after_auction_first_run_priority_pack_20260612.md)|경매 1차 우선 조회팩 검증 추가 후 전체 QA suite 30/30 PASS|
|[docs/1306_platform_completion_gate_after_auction_first_run_priority_pack_20260612.md](docs/1306_platform_completion_gate_after_auction_first_run_priority_pack_20260612.md)|경매 1차 우선 조회팩 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1307_100pct_control_tower_after_auction_first_run_priority_pack_20260612.md](docs/1307_100pct_control_tower_after_auction_first_run_priority_pack_20260612.md)|경매 1차 우선 조회팩 반영 후 100% 관제 보드 재계산|
|[docs/1308_auction_first_run_priority_pack_implementation_report_20260612.md](docs/1308_auction_first_run_priority_pack_implementation_report_20260612.md)|경매 1차 우선 조회팩 구현·검증·다음 실행 기준 보고|
|[docs/1309_auction_first_run_priority_pack_with_result_template_20260612.md](docs/1309_auction_first_run_priority_pack_with_result_template_20260612.md)|경매 1차 우선 조회팩에 결과입력 템플릿 CSV 추가 생성|
|[docs/1310_auction_first_run_priority_result_template_blank_preflight_20260612.md](docs/1310_auction_first_run_priority_result_template_blank_preflight_20260612.md)|빈 결과입력 템플릿 preflight, ready 0행·blank 162행 확인|
|[docs/1311_platform_qa_suite_full_after_auction_first_run_result_template_20260612.md](docs/1311_platform_qa_suite_full_after_auction_first_run_result_template_20260612.md)|결과입력 템플릿 추가 후 전체 QA suite 30/30 PASS|
|[docs/1312_platform_completion_gate_after_auction_first_run_result_template_20260612.md](docs/1312_platform_completion_gate_after_auction_first_run_result_template_20260612.md)|결과입력 템플릿 추가 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1313_100pct_control_tower_after_auction_first_run_result_template_20260612.md](docs/1313_100pct_control_tower_after_auction_first_run_result_template_20260612.md)|결과입력 템플릿 추가 후 100% 관제 보드 재계산|
|[docs/1314_auction_first_run_result_template_implementation_report_20260612.md](docs/1314_auction_first_run_result_template_implementation_report_20260612.md)|경매 1차 우선 조회팩 결과입력 템플릿 구현·검증 보고|
|[docs/1315_auction_first_run_result_pipeline_blank_waiting_20260612.md](docs/1315_auction_first_run_result_pipeline_blank_waiting_20260612.md)|경매 1차 결과 안전 실행기, 빈 템플릿 `INPUT_WAITING` 판정|
|[docs/1316_platform_qa_suite_full_after_auction_first_run_pipeline_20260612.md](docs/1316_platform_qa_suite_full_after_auction_first_run_pipeline_20260612.md)|경매 1차 결과 안전 실행기 smoke 추가 후 전체 QA suite 31/31 PASS|
|[docs/1317_platform_completion_gate_after_auction_first_run_pipeline_20260612.md](docs/1317_platform_completion_gate_after_auction_first_run_pipeline_20260612.md)|경매 1차 결과 안전 실행기 반영 후 완료 게이트, 6 PASS / 10 FAIL|
|[docs/1318_100pct_control_tower_after_auction_first_run_pipeline_20260612.md](docs/1318_100pct_control_tower_after_auction_first_run_pipeline_20260612.md)|경매 1차 결과 안전 실행기 반영 후 100% 관제 보드 재계산|
|[docs/1319_auction_first_run_result_pipeline_implementation_report_20260612.md](docs/1319_auction_first_run_result_pipeline_implementation_report_20260612.md)|경매 1차 결과 안전 실행기 구현·검증·다음 실행 기준 보고|

관련 코드: [backend/mvp_api.py](backend/mvp_api.py), [frontend/index.html](frontend/index.html), [scripts/build_energy_site_planning_future_gap_workpack.py](scripts/build_energy_site_planning_future_gap_workpack.py), [scripts/build_energy_site_minimum_batch_operator_bundle.py](scripts/build_energy_site_minimum_batch_operator_bundle.py), [scripts/build_energy_site_minimum_batch_operator_preflight.py](scripts/build_energy_site_minimum_batch_operator_preflight.py), [scripts/build_energy_site_minimum_batch_execution_plan.py](scripts/build_energy_site_minimum_batch_execution_plan.py), [scripts/build_energy_site_pnu_geocode_priority_pack.py](scripts/build_energy_site_pnu_geocode_priority_pack.py), [scripts/seed_geocode_requests_from_pnu_priority_pack.py](scripts/seed_geocode_requests_from_pnu_priority_pack.py), [scripts/run_energy_site_geocode_requests.py](scripts/run_energy_site_geocode_requests.py), [scripts/run_g3_geocode_api_batch.py](scripts/run_g3_geocode_api_batch.py), [scripts/run_p0_geocode_secure_pipeline.ps1](scripts/run_p0_geocode_secure_pipeline.ps1), [scripts/build_p0_geocode_execution_monitor.py](scripts/build_p0_geocode_execution_monitor.py), [scripts/build_energy_site_100pct_control_tower.py](scripts/build_energy_site_100pct_control_tower.py), [scripts/build_energy_site_platform_action_queue.py](scripts/build_energy_site_platform_action_queue.py), [scripts/build_energy_site_platform_action_preflight.py](scripts/build_energy_site_platform_action_preflight.py), [scripts/build_energy_site_external_workpack_manifest.py](scripts/build_energy_site_external_workpack_manifest.py), [scripts/build_energy_site_external_dependency_blockers.py](scripts/build_energy_site_external_dependency_blockers.py), [scripts/run_energy_site_threshold_gate.py](scripts/run_energy_site_threshold_gate.py), [scripts/smoke_threshold_gate_input_preflight.py](scripts/smoke_threshold_gate_input_preflight.py), [scripts/smoke_auction_case_resolution_pack_export.py](scripts/smoke_auction_case_resolution_pack_export.py), [scripts/run_energy_site_platform_qa_suite.py](scripts/run_energy_site_platform_qa_suite.py)

## 문서 목록

|파일|용도|
|---|---|
|[docs/00_commercial_service_report_20260601.md](docs/00_commercial_service_report_20260601.md)|상용화 종합 보고서|
|[docs/01_roadmap_to_commercial_launch.md](docs/01_roadmap_to_commercial_launch.md)|100% 상용 출시까지의 개발 로드맵|
|[docs/02_wireframes.md](docs/02_wireframes.md)|검색 앱 주요 화면 와이어프레임|
|[docs/03_tech_stack_architecture.md](docs/03_tech_stack_architecture.md)|기술스택 및 서비스 아키텍처|
|[docs/04_database_schema_and_build_plan.md](docs/04_database_schema_and_build_plan.md)|DB 구조 및 구축 계획|
|[docs/05_development_execution_plan.md](docs/05_development_execution_plan.md)|개발 실행 계획|
|[docs/06_launch_operations_checklist.md](docs/06_launch_operations_checklist.md)|상용 출시 및 운영 체크리스트|
|[docs/07_review_response_upgrade_notes_20260601.md](docs/07_review_response_upgrade_notes_20260601.md)|외부 검토 의견 반영 내역|
|[docs/08_current_progress_fast_service_assessment_20260601.md](docs/08_current_progress_fast_service_assessment_20260601.md)|현재 개발 진행자료 기준 빠른 서비스화 판단|
|[docs/09_score100_uplift_resolution_report_20260601.md](docs/09_score100_uplift_resolution_report_20260601.md)|100점 상향 보완 실행 보고서|
|[docs/10_next_development_direction_20260601.md](docs/10_next_development_direction_20260601.md)|추가 개발 방향성|
|[docs/11_private_pilot_implementation_backlog_20260601.md](docs/11_private_pilot_implementation_backlog_20260601.md)|Private Pilot 구현 백로그|
|[docs/12_release_blocker_resolution_runbook_20260601.md](docs/12_release_blocker_resolution_runbook_20260601.md)|Release blocker 해소 Runbook|
|[docs/13_codebase_stabilization_refactor_plan_20260601.md](docs/13_codebase_stabilization_refactor_plan_20260601.md)|코드 구조 안정화 및 리팩터링 계획|
|[docs/14_beta_public_expansion_roadmap_20260601.md](docs/14_beta_public_expansion_roadmap_20260601.md)|Beta/Public 확장 로드맵|
|[docs/15_private_pilot_approval_pack_template_20260601.md](docs/15_private_pilot_approval_pack_template_20260601.md)|Private Pilot 승인팩 템플릿|
|[docs/16_hub_building_register_ingestion_report_20260601.md](docs/16_hub_building_register_ingestion_report_20260601.md)|전국 건축물대장 다운로드 및 DB 적재 결과 보고|
|[docs/17_hub_extra_datasets_ingestion_report_20260602.md](docs/17_hub_extra_datasets_ingestion_report_20260602.md)|건축HUB 추가 데이터셋 다운로드 및 기존 DuckDB 주입 보고|
|[docs/18_service_mvp_detailed_execution_plan_20260602.md](docs/18_service_mvp_detailed_execution_plan_20260602.md)|검색 서비스 MVP 상세 실행 계획서|
|[docs/19_service_mvp_technical_specification_20260602.md](docs/19_service_mvp_technical_specification_20260602.md)|검색 서비스 MVP 기술명세서|
|[docs/20_final_mvp_execution_governance_report_20260602.md](docs/20_final_mvp_execution_governance_report_20260602.md)|보완사항 반영 최종 실행 및 기술 거버넌스 보고서|
|[docs/21_hub_column_mapping_dictionary_20260602.md](docs/21_hub_column_mapping_dictionary_20260602.md)|건축HUB 컬럼 매핑 사전|
|[docs/22_mvp_quality_check_report_20260602.md](docs/22_mvp_quality_check_report_20260602.md)|MVP 품질검사 결과|
|[docs/23_development_approval_kickoff_report_20260602.md](docs/23_development_approval_kickoff_report_20260602.md)|개발 승인 후 착수 보고서|
|[docs/24_next_development_station_matching_execution_plan_20260602.md](docs/24_next_development_station_matching_execution_plan_20260602.md)|다음 개발 상세 실행계획서: 주유소 원천 적재 및 건축HUB 매칭|
|[docs/25_next_development_station_matching_technical_specification_20260602.md](docs/25_next_development_station_matching_technical_specification_20260602.md)|다음 개발 기술명세서: 주유소 원천 적재, PNU 매칭, 검색 마트 활성화|
|[docs/26_station_source_inventory_report_20260602.md](docs/26_station_source_inventory_report_20260602.md)|주유소 원천 데이터 후보 점검 결과|
|[docs/27_npl_blueprint_schema_alignment_report_20260602.md](docs/27_npl_blueprint_schema_alignment_report_20260602.md)|PNU/NPL 선행 산출물 반영 및 공식 원천 적재 보고|
|[docs/28_development_approval_implementation_report_20260602.md](docs/28_development_approval_implementation_report_20260602.md)|개발 승인 후 구현 완료 보고서|
|[docs/29_station_master_load_report_20260602.md](docs/29_station_master_load_report_20260602.md)|공식 주유소 원천 적재 실행 보고서|
|[docs/30_station_hub_match_report_20260602.md](docs/30_station_hub_match_report_20260602.md)|주유소-건축HUB 매칭 실행 보고서|
|[docs/31_next_development_status_report_20260602.md](docs/31_next_development_status_report_20260602.md)|다음 개발 상황 상세 보고서|
|[docs/32_next_development_implementation_report_20260602.md](docs/32_next_development_implementation_report_20260602.md)|다음 개발 착수 구현 보고서|
|[docs/33_next_development_status_after_detail_api_20260602.md](docs/33_next_development_status_after_detail_api_20260602.md)|상세 API 및 운영 화면 보강 이후 다음 개발 상황 보고서|
|[docs/34_data_precision_improvement_execution_plan_20260602.md](docs/34_data_precision_improvement_execution_plan_20260602.md)|데이터 정밀도 개선 상세 실행계획서|
|[docs/35_data_precision_development_start_report_20260602.md](docs/35_data_precision_development_start_report_20260602.md)|데이터 정밀도 개선 개발 착수 및 1차 구현 보고서|
|[docs/36_address_precision_profile_build_report_20260602.md](docs/36_address_precision_profile_build_report_20260602.md)|주소 정밀도 프로파일 구축 보고서|
|[docs/37_pnu_candidate_build_report_20260602.md](docs/37_pnu_candidate_build_report_20260602.md)|PNU 후보 생성 실행 보고서|
|[docs/38_station_precision_quality_report_20260602.md](docs/38_station_precision_quality_report_20260602.md)|주유소 데이터 정밀도 품질검사 보고서|
|[docs/39_station_area_facility_storage_extension_plan_20260602.md](docs/39_station_area_facility_storage_extension_plan_20260602.md)|주유소 면적·건축물·위험물/가스 저장시설 확장 개발 요구사항|
|[docs/40_unified_fuel_charging_site_db_injection_plan_wbs_20260602.md](docs/40_unified_fuel_charging_site_db_injection_plan_wbs_20260602.md)|주유소·LPG/CNG/LNG/수소충전소 통합 DB 인젝션 개발계획서 및 WBS|
|[docs/41_unified_energy_site_immediate_implementation_report_20260602.md](docs/41_unified_energy_site_immediate_implementation_report_20260602.md)|주유소·충전소 통합 DB 즉시 실행 구현 보고서|
|[docs/42_energy_site_station_injection_report_20260602.md](docs/42_energy_site_station_injection_report_20260602.md)|통합 에너지 사이트 기존 주유소 인젝션 보고서|
|[docs/43_energy_site_mart_build_report_20260602.md](docs/43_energy_site_mart_build_report_20260602.md)|통합 에너지 사이트 마트 구축 보고서|
|[docs/44_energy_site_quality_report_20260602.md](docs/44_energy_site_quality_report_20260602.md)|통합 에너지 사이트 품질검사 보고서|
|[docs/45_energy_source_download_injection_report_20260602.md](docs/45_energy_source_download_injection_report_20260602.md)|충전소 원천데이터 다운로드 및 통합 DB 인젝션 보고서|
|[docs/46_energy_site_mart_rebuild_after_source_injection_20260602.md](docs/46_energy_site_mart_rebuild_after_source_injection_20260602.md)|원천 인젝션 후 통합 에너지 사이트 마트 재구축 보고서|
|[docs/47_energy_site_quality_after_source_injection_20260602.md](docs/47_energy_site_quality_after_source_injection_20260602.md)|원천 인젝션 후 통합 에너지 사이트 품질검사 보고서|
|[docs/48_next_development_work_report_after_source_injection_20260602.md](docs/48_next_development_work_report_after_source_injection_20260602.md)|원천 인젝션 후 다음 개발 작업 상세 보고서|
|[docs/49_energy_site_precision_pipeline_implementation_report_20260602.md](docs/49_energy_site_precision_pipeline_implementation_report_20260602.md)|통합 에너지 사이트 정밀도 파이프라인 구현 보고서|
|[docs/50_energy_site_precision_mart_rebuild_report_20260602.md](docs/50_energy_site_precision_mart_rebuild_report_20260602.md)|정밀도 후보 반영 통합 마트 재구축 보고서|
|[docs/51_energy_site_precision_quality_report_20260602.md](docs/51_energy_site_precision_quality_report_20260602.md)|통합 에너지 사이트 정밀도 품질검사 보고서|
|[docs/52_next_charging_station_pnu_precision_spec_wbs_20260602.md](docs/52_next_charging_station_pnu_precision_spec_wbs_20260602.md)|충전소 PNU/건축HUB 정밀 매칭 2차 개발 상세 명세서 및 WBS|
|[docs/53_next_energy_site_precision_technical_spec_20260602.md](docs/53_next_energy_site_precision_technical_spec_20260602.md)|통합 에너지 사이트 다음 개발 상세 기술명세서|
|[docs/54_next_energy_site_precision_wbs_20260602.md](docs/54_next_energy_site_precision_wbs_20260602.md)|통합 에너지 사이트 다음 개발 WBS 및 실행계획서|
|[docs/55_energy_site_geocode_processing_report_20260602.md](docs/55_energy_site_geocode_processing_report_20260602.md)|주소 결과 처리 및 PNU 후보 병합 dry-run 실행 보고서|
|[docs/56_claude_gate_development_implementation_report_20260602.md](docs/56_claude_gate_development_implementation_report_20260602.md)|Claude식 보완 반영 개발 실행 보고서|
|[docs/57_code_cleanup_report_20260602.md](docs/57_code_cleanup_report_20260602.md)|개발 코드 1차 클렌징 보고서|
|[docs/58_next_pnu_uplift_and_cleanup_technical_spec_20260602.md](docs/58_next_pnu_uplift_and_cleanup_technical_spec_20260602.md)|다음 개발 상세 개발명세서: 충전소 PNU 실주입 및 2차 코드 클렌징|
|[docs/59_next_pnu_uplift_wbs_claude_review_20260602.md](docs/59_next_pnu_uplift_wbs_claude_review_20260602.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서|
|[docs/60_next_execution_sprint_technical_spec_20260602.md](docs/60_next_execution_sprint_technical_spec_20260602.md)|다음 실행 스프린트 상세 개발명세서|
|[docs/61_next_execution_sprint_wbs_claude_reflection_20260602.md](docs/61_next_execution_sprint_wbs_claude_reflection_20260602.md)|다음 실행 스프린트 WBS 및 Claude 비판 반영 보고서|
|[docs/62_immediate_export_audit_common_utils_technical_spec_20260602.md](docs/62_immediate_export_audit_common_utils_technical_spec_20260602.md)|즉시 구현 패키지 상세 개발명세서: Export, Audit, Common Utils|
|[docs/63_immediate_export_audit_common_utils_wbs_claude_review_20260602.md](docs/63_immediate_export_audit_common_utils_wbs_claude_review_20260602.md)|즉시 구현 패키지 WBS 및 Claude 비판 반영 보고서|
|[docs/64_energy_site_geocode_export_execution_report_20260602.md](docs/64_energy_site_geocode_export_execution_report_20260602.md)|충전소 주소 요청 Export 실행 보고서|
|[docs/65_energy_site_pnu_audit_sample_report_20260602.md](docs/65_energy_site_pnu_audit_sample_report_20260602.md)|충전소 PNU 감사 샘플 실행 보고서|
|[docs/66_immediate_export_audit_implementation_report_20260602.md](docs/66_immediate_export_audit_implementation_report_20260602.md)|즉시 구현 패키지 구현 및 검증 보고서|
|[docs/67_next_geocode_import_pnu_uplift_technical_spec_20260602.md](docs/67_next_geocode_import_pnu_uplift_technical_spec_20260602.md)|다음 개발 상세 개발명세서: 충전소 주소결과 Import 및 PNU Coverage 상향|
|[docs/68_next_geocode_import_pnu_uplift_wbs_claude_review_20260602.md](docs/68_next_geocode_import_pnu_uplift_wbs_claude_review_20260602.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서|
|[docs/69_charging_station_geocode_import_runner_implementation_report_20260602.md](docs/69_charging_station_geocode_import_runner_implementation_report_20260602.md)|충전소 주소결과 Import Runner 구현 보고서|
|[docs/70_charging_station_pnu_coverage_uplift_blocker_report_20260602.md](docs/70_charging_station_pnu_coverage_uplift_blocker_report_20260602.md)|충전소 PNU Coverage 상향 차단조건 보고서|
|[docs/71_energy_site_precision_quality_after_geocode_import_20260602.md](docs/71_energy_site_precision_quality_after_geocode_import_20260602.md)|주소결과 Import 대비 정밀도 품질검사 보고서|
|[docs/72_next_address_api_acquisition_technical_spec_20260602.md](docs/72_next_address_api_acquisition_technical_spec_20260602.md)|다음 개발 상세 개발명세서: 주소 API 결과 수집 자동화 및 충전소 PNU Coverage 상향|
|[docs/73_next_address_api_acquisition_wbs_claude_review_20260602.md](docs/73_next_address_api_acquisition_wbs_claude_review_20260602.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: 주소 API 결과 수집 자동화|
|[docs/74_address_api_collection_runner_implementation_report_20260602.md](docs/74_address_api_collection_runner_implementation_report_20260602.md)|주소 API 결과 수집 자동화 Runner 구현 보고서|
|[docs/75_address_api_collection_execution_report_20260602.md](docs/75_address_api_collection_execution_report_20260602.md)|주소 API 수집 실행 보고서: API key 미설정 차단|
|[docs/76_public_data_key_juso_compatibility_smoke_report_20260602.md](docs/76_public_data_key_juso_compatibility_smoke_report_20260602.md)|공공데이터포털 키 JUSO API 호환성 Smoke 보고서|
|[docs/77_data_go_kr_15096712_direct_download_attempt_report_20260602.md](docs/77_data_go_kr_15096712_direct_download_attempt_report_20260602.md)|data.go.kr 15096712 직접 다운로드 시도 보고서|
|[docs/78_data_go_kr_15059078_vworld_road_building_api_review_20260602.md](docs/78_data_go_kr_15059078_vworld_road_building_api_review_20260602.md)|data.go.kr 15059078 / VWorld 도로명주소 건물 API 검토 보고서|
|[docs/79_next_key_independent_charging_pnu_uplift_technical_spec_20260602.md](docs/79_next_key_independent_charging_pnu_uplift_technical_spec_20260602.md)|다음 개발 상세 개발명세서: API Key 비의존 충전소 PNU 후보 상향 및 VWorld 보강 Queue|
|[docs/80_next_key_independent_charging_pnu_uplift_wbs_claude_review_20260602.md](docs/80_next_key_independent_charging_pnu_uplift_wbs_claude_review_20260602.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: API Key 비의존 충전소 PNU 상향|
|[docs/81_service_ui_ux_implementation_report_20260602.md](docs/81_service_ui_ux_implementation_report_20260602.md)|서비스 UI/UX 디자인 구현 보고서|
|[docs/82_next_public_service_ux_feature_technical_spec_20260603.md](docs/82_next_public_service_ux_feature_technical_spec_20260603.md)|다음 개발 상세 개발명세서: 일반 사용자용 검색 서비스 고도화|
|[docs/83_next_public_service_ux_feature_wbs_claude_review_20260603.md](docs/83_next_public_service_ux_feature_wbs_claude_review_20260603.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: 일반 사용자용 검색 서비스 고도화|
|[docs/84_public_service_ux_feature_implementation_report_20260603.md](docs/84_public_service_ux_feature_implementation_report_20260603.md)|일반 사용자용 검색 서비스 고도화 구현 보고서|
|[docs/85_next_pnu_admin_ops_hardening_technical_spec_20260603.md](docs/85_next_pnu_admin_ops_hardening_technical_spec_20260603.md)|다음 개발 상세 개발명세서: PNU 매칭률 상향, 관리자 검토, Export 통제, 운영 준비|
|[docs/86_next_pnu_admin_ops_hardening_wbs_claude_review_20260603.md](docs/86_next_pnu_admin_ops_hardening_wbs_claude_review_20260603.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: PNU 매칭률 상향, 관리자 검토, Export 통제, 운영 준비|
|[docs/87_hyundaicard_ui_naver_maps_implementation_report_20260603.md](docs/87_hyundaicard_ui_naver_maps_implementation_report_20260603.md)|현대카드식 UI/UX 및 NAVER Maps API 구현·테스트 보고서|
|[docs/88_vworld_openlayers_free_map_implementation_report_20260603.md](docs/88_vworld_openlayers_free_map_implementation_report_20260603.md)|VWorld/OpenLayers 무료 지도 전환 구현 보고서|
|[docs/89_next_map_data_ops_hardening_technical_spec_20260603.md](docs/89_next_map_data_ops_hardening_technical_spec_20260603.md)|다음 개발 상세 개발명세서: VWorld 지도 상용화, 좌표 정밀도, 운영 안정화|
|[docs/90_next_map_data_ops_wbs_claude_review_20260603.md](docs/90_next_map_data_ops_wbs_claude_review_20260603.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: VWorld 지도 상용화, 좌표 정밀도, 운영 안정화|
|[docs/91_map_data_ops_hardening_implementation_report_20260603.md](docs/91_map_data_ops_hardening_implementation_report_20260603.md)|VWorld 지도 상용화, 좌표 정밀도, 운영 안정화 구현 보고서|
|[docs/92_next_commercial_launch_readiness_technical_spec_20260603.md](docs/92_next_commercial_launch_readiness_technical_spec_20260603.md)|다음 개발 상세 개발명세서: 상용 출시 게이트, 인증/권한, 배포/갱신 자동화|
|[docs/93_next_commercial_launch_readiness_wbs_claude_review_20260603.md](docs/93_next_commercial_launch_readiness_wbs_claude_review_20260603.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: 상용 출시 게이트, 인증/권한, 배포/갱신 자동화|
|[docs/94_commercial_launch_readiness_implementation_report_20260603.md](docs/94_commercial_launch_readiness_implementation_report_20260603.md)|상용 출시 준비 기능 구현 보고서: 인증/권한, 감사, Export 통제, readiness, 백업/refresh|
|[docs/95_next_full_commercialization_technical_spec_20260603.md](docs/95_next_full_commercialization_technical_spec_20260603.md)|다음 개발 상세 개발명세서: 상용 100% 전환 운영 콘솔, 배포, 백업, 모니터링, 반출 승인|
|[docs/96_next_full_commercialization_wbs_claude_review_20260603.md](docs/96_next_full_commercialization_wbs_claude_review_20260603.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: 상용 100% 전환|
|[docs/97_full_commercialization_implementation_report_20260603.md](docs/97_full_commercialization_implementation_report_20260603.md)|상용 100% 전환 운영 기능 구현 보고서|
|[docs/98_license_gate_report_20260603.md](docs/98_license_gate_report_20260603.md)|라이선스 게이트 보고서|
|[docs/99_next_final_launch_gate_closure_technical_spec_20260603.md](docs/99_next_final_launch_gate_closure_technical_spec_20260603.md)|다음 개발 상세 개발명세서: 최종 상용 출시 게이트 폐쇄 및 100% 판정 패키지|
|[docs/100_next_final_launch_gate_closure_wbs_claude_review_20260603.md](docs/100_next_final_launch_gate_closure_wbs_claude_review_20260603.md)|다음 개발 WBS 및 Claude 관점 비판 반영 보고서: 최종 출시 게이트 폐쇄|
|[docs/101_final_launch_gate_check_report_20260603.md](docs/101_final_launch_gate_check_report_20260603.md)|최종 출시 게이트 점검 보고서|
|[docs/102_final_commercial_launch_approval_pack_20260603.md](docs/102_final_commercial_launch_approval_pack_20260603.md)|최종 상용 출시 승인팩|
|[docs/103_final_launch_gate_closure_implementation_report_20260603.md](docs/103_final_launch_gate_closure_implementation_report_20260603.md)|최종 출시 게이트 폐쇄 구현 보고서|
|[docs/104_next_100_percent_completion_technical_spec_20260604.md](docs/104_next_100_percent_completion_technical_spec_20260604.md)|100% 상용 완료 기준 상세 개발명세서|
|[docs/105_next_100_percent_completion_wbs_claude_review_20260604.md](docs/105_next_100_percent_completion_wbs_claude_review_20260604.md)|100% 상용 완료 WBS 및 Claude 관점 비판 반영 보고서|
|[docs/106_100_percent_completion_implementation_report_20260604.md](docs/106_100_percent_completion_implementation_report_20260604.md)|100% 상용 완료 스프린트 구현 보고서|
|[docs/107_lg_external_data_migration_report_20260604.md](docs/107_lg_external_data_migration_report_20260604.md)|LG 외장하드 데이터 이관 보고서|
|[docs/108_agent_common_handoff_20260604.md](docs/108_agent_common_handoff_20260604.md)|Agent Common Handoff 공통 실행 규칙|
|[docs/109_agent_common_handoff_implementation_report_20260604.md](docs/109_agent_common_handoff_implementation_report_20260604.md)|Agent Common Handoff 구현 보고서|
|[db/gas_station_commercial_schema.sql](db/gas_station_commercial_schema.sql)|상용 서비스용 PostgreSQL/PostGIS 스키마 초안|

## 최신 작업 산출물

|파일|용도|
|---|---|
|[docs/872_external_dependency_blockers_revenue_focus_20260611.md](docs/872_external_dependency_blockers_revenue_focus_20260611.md)|G9/G10 카드·재무·수익가치 외부 의존성 차단 원장 최신 갱신|
|[docs/873_card_revenue_batch_manifest_refresh_20260611.md](docs/873_card_revenue_batch_manifest_refresh_20260611.md)|G9 카드결제 12개월 입력 102,816행, 876개 배치 최신 manifest|
|[docs/874_financial_revenue_batch_manifest_refresh_20260611.md](docs/874_financial_revenue_batch_manifest_refresh_20260611.md)|G10 재무자료 2025년 입력 8,568행, 73개 배치 최신 manifest|
|[docs/875_revenue_confirmation_pack_refresh_20260611.md](docs/875_revenue_confirmation_pack_refresh_20260611.md)|권한증빙 기반 카드·재무 결과 입력 통합 확인팩 최신 export|
|[docs/876_completion_execution_board_after_revenue_refresh_20260611.md](docs/876_completion_execution_board_after_revenue_refresh_20260611.md)|G9/G10 최신 배치팩 경로 반영 100% 통합 실행 보드|
|[docs/877_external_workpack_manifest_after_revenue_refresh_20260611.md](docs/877_external_workpack_manifest_after_revenue_refresh_20260611.md)|외부 원천 workpack manifest 및 import 명령 원장 최신 갱신|
|[docs/878_external_intake_status_after_revenue_refresh_20260611.md](docs/878_external_intake_status_after_revenue_refresh_20260611.md)|외부 결과파일 intake 상태 DB 기록 최신 갱신|
|[docs/879_result_file_execution_plan_after_revenue_refresh_20260611.md](docs/879_result_file_execution_plan_after_revenue_refresh_20260611.md)|외부 결과파일 자동탐색 실행계획 최신 갱신, import 가능 파일 0건 판정|
|[docs/882_platform_qa_suite_after_revenue_refresh_api_g57_20260611.md](docs/882_platform_qa_suite_after_revenue_refresh_api_g57_20260611.md)|API 포함 G15 QA suite 12/12 PASS 최신 보고|
|[docs/883_platform_completion_gate_after_revenue_refresh_api_qa_20260611.md](docs/883_platform_completion_gate_after_revenue_refresh_api_qa_20260611.md)|G9/G10 갱신 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/884_completion_input_gap_after_revenue_refresh_20260611.md](docs/884_completion_input_gap_after_revenue_refresh_20260611.md)|카드·재무 실데이터 미주입 상태를 포함한 입력 Gap 최신 보고|
|[docs/885_revenue_gap_refresh_implementation_report_20260611.md](docs/885_revenue_gap_refresh_implementation_report_20260611.md)|G9/G10 카드·재무·수익가치 갭 보강 실행 종합 보고|
|[docs/886_external_dependency_blockers_after_revenue_refresh_final_20260611.md](docs/886_external_dependency_blockers_after_revenue_refresh_final_20260611.md)|최신 실행 보드 경로 반영 외부 의존성 차단 원장 최종 갱신|
|[docs/887_platform_completion_gate_final_after_revenue_refresh_20260611.md](docs/887_platform_completion_gate_final_after_revenue_refresh_20260611.md)|G9/G10 갱신 후 최종 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/888_auction_case_no_source_reaudit_20260611.md](docs/888_auction_case_no_source_reaudit_20260611.md)|과거 경매 법원 사건번호 원천 재감사 및 exact match 0건 판정|
|[docs/889_g11_planning_internal_uplift_reaudit_20260611.md](docs/889_g11_planning_internal_uplift_reaudit_20260611.md)|G11 도시계획 내부 보강 가능성 재감사, 내부 안전 보강 없음 판정|
|[docs/890_current_auction_reference_candidates_rebuild_20260611.md](docs/890_current_auction_reference_candidates_rebuild_20260611.md)|현재경매 provider reference 후보 1건 재생성 보고|
|[docs/891_current_auction_review_status_rebuild_20260611.md](docs/891_current_auction_review_status_rebuild_20260611.md)|현재경매 확인상태 8,568개 미검증 및 provider 검색큐 34,272행 재구축|
|[docs/892_auction_case_quality_rebuild_20260611.md](docs/892_auction_case_quality_rebuild_20260611.md)|과거 경매 사건번호 품질 재감사, 유효 법원 사건번호 0건 판정|
|[docs/893_auction_history_batch_manifest_refresh_20260611.md](docs/893_auction_history_batch_manifest_refresh_20260611.md)|G7 과거경매 검색 65,733행, 291개 배치 최신 manifest|
|[docs/894_current_auction_batch_manifest_refresh_20260611.md](docs/894_current_auction_batch_manifest_refresh_20260611.md)|G8 현재경매 검색 34,272행, 292개 배치 최신 manifest|
|[docs/895_auction_case_resolution_pack_refresh_20260611.md](docs/895_auction_case_resolution_pack_refresh_20260611.md)|과거경매 provider reference 76행/49개 시설 법원 사건번호 보정팩|
|[docs/896_current_auction_reference_resolution_pack_refresh_20260611.md](docs/896_current_auction_reference_resolution_pack_refresh_20260611.md)|현재경매 provider reference 1행/1개 시설 법원 사건번호 보정팩|
|[docs/897_completion_execution_board_after_auction_refresh_20260611.md](docs/897_completion_execution_board_after_auction_refresh_20260611.md)|G7/G8 최신 배치팩 반영 100% 통합 실행 보드|
|[docs/898_external_workpack_manifest_after_auction_refresh_20260611.md](docs/898_external_workpack_manifest_after_auction_refresh_20260611.md)|G7/G8 갱신 후 외부 workpack manifest 최신 보고|
|[docs/899_external_intake_status_after_auction_refresh_20260611.md](docs/899_external_intake_status_after_auction_refresh_20260611.md)|G7/G8 갱신 후 외부 결과파일 intake 상태 최신 보고|
|[docs/900_result_file_execution_plan_after_auction_refresh_20260611.md](docs/900_result_file_execution_plan_after_auction_refresh_20260611.md)|G7/G8 갱신 후 외부 결과파일 실행계획, import 가능 0건 판정|
|[docs/901_external_dependency_blockers_after_auction_refresh_20260611.md](docs/901_external_dependency_blockers_after_auction_refresh_20260611.md)|경매·도시계획 재감사 후 외부 의존성 원장 최신 보고|
|[docs/902_platform_qa_suite_after_auction_refresh_api_g57_20260611.md](docs/902_platform_qa_suite_after_auction_refresh_api_g57_20260611.md)|경매 재감사 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/903_platform_completion_gate_after_auction_planning_reaudit_20260611.md](docs/903_platform_completion_gate_after_auction_planning_reaudit_20260611.md)|경매·도시계획 재감사 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/904_auction_planning_reaudit_implementation_report_20260611.md](docs/904_auction_planning_reaudit_implementation_report_20260611.md)|G7/G8 경매 및 G11/G12 도시계획·예측 재감사 종합 보고|
|[docs/905_geocode_api_key_preflight_reaudit_20260611.md](docs/905_geocode_api_key_preflight_reaudit_20260611.md)|주소 API key preflight 재감사, KEY_NOT_CONFIGURED 판정|
|[docs/906_geocode_intake_preflight_reaudit_20260611.md](docs/906_geocode_intake_preflight_reaudit_20260611.md)|G3 좌표 결과파일 strict preflight, import 가능 0건 판정|
|[docs/907_coordinate_uplift_candidate_reaudit_20260611.md](docs/907_coordinate_uplift_candidate_reaudit_20260611.md)|내부 좌표 보강 후보 재감사, ready 후보 0건 판정|
|[docs/908_land_area_pnu_uplift_reaudit_20260611.md](docs/908_land_area_pnu_uplift_reaudit_20260611.md)|PNU 기반 토지면적 내부 보강 재감사, 추가 상승 없음 판정|
|[docs/909_building_internal_pnu_uplift_dryrun_20260611.md](docs/909_building_internal_pnu_uplift_dryrun_20260611.md)|G5 건물 내부 PNU 후보 dry-run 보고|
|[docs/910_building_internal_pnu_uplift_apply_20260611.md](docs/910_building_internal_pnu_uplift_apply_20260611.md)|G5 건물 내부 PNU 후보 56행 재삽입 보고|
|[docs/911_pnu_internal_address_match_dryrun_20260611.md](docs/911_pnu_internal_address_match_dryrun_20260611.md)|PNU 내부 주소 매칭 dry-run, ready match 0건 판정|
|[docs/912_attached_lots_land_link_sync_reaudit_20260611.md](docs/912_attached_lots_land_link_sync_reaudit_20260611.md)|건축물대장 부속지번 토지 링크 동기화 재확인 보고|
|[docs/913_geocode_result_confirmation_pack_refresh_20260611.md](docs/913_geocode_result_confirmation_pack_refresh_20260611.md)|G3 좌표 확인팩 6,094건 최신 export|
|[docs/914_geocode_batch_manifest_refresh_20260611.md](docs/914_geocode_batch_manifest_refresh_20260611.md)|G3 좌표 batch manifest 21개 배치 최신 생성|
|[docs/915_land_area_confirmation_pack_refresh_20260611.md](docs/915_land_area_confirmation_pack_refresh_20260611.md)|G4 토지/PNU/면적 확인팩 3,587건 최신 export|
|[docs/916_land_area_batch_manifest_refresh_20260611.md](docs/916_land_area_batch_manifest_refresh_20260611.md)|G4 토지 batch manifest 96개 배치 최신 생성|
|[docs/917_building_confirmation_pack_refresh_20260611.md](docs/917_building_confirmation_pack_refresh_20260611.md)|G5 건축물대장 확인팩 3,368건 최신 export|
|[docs/918_building_batch_manifest_refresh_20260611.md](docs/918_building_batch_manifest_refresh_20260611.md)|G5 건축물 batch manifest 66개 배치 최신 생성|
|[docs/919_completion_execution_board_after_g3_g5_reaudit_20260611.md](docs/919_completion_execution_board_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 최신 입력팩 반영 100% 통합 실행 보드|
|[docs/920_external_workpack_manifest_after_g3_g5_reaudit_20260611.md](docs/920_external_workpack_manifest_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 갱신 후 외부 workpack manifest 최신 보고|
|[docs/921_external_intake_status_after_g3_g5_reaudit_20260611.md](docs/921_external_intake_status_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 갱신 후 외부 결과파일 intake 상태 최신 보고|
|[docs/922_result_file_execution_plan_after_g3_g5_reaudit_20260611.md](docs/922_result_file_execution_plan_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 갱신 후 결과파일 실행계획, import 가능 0건 판정|
|[docs/923_external_dependency_blockers_after_g3_g5_reaudit_20260611.md](docs/923_external_dependency_blockers_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 재감사 후 외부 의존성 원장 최신 보고|
|[docs/924_completion_input_gap_after_g3_g5_reaudit_20260611.md](docs/924_completion_input_gap_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 재감사 후 입력 Gap 최신 보고|
|[docs/925_platform_qa_suite_after_g3_g5_reaudit_api_g57_20260611.md](docs/925_platform_qa_suite_after_g3_g5_reaudit_api_g57_20260611.md)|G3/G4/G5 재감사 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/926_platform_completion_gate_after_g3_g5_reaudit_20260611.md](docs/926_platform_completion_gate_after_g3_g5_reaudit_20260611.md)|G3/G4/G5 재감사 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/927_g3_g5_location_land_building_reaudit_report_20260611.md](docs/927_g3_g5_location_land_building_reaudit_report_20260611.md)|G3/G4/G5 위치·토지·건물 재감사 및 입력팩 갱신 종합 보고|
|[docs/928_storage_source_audit_reaudit_20260611.md](docs/928_storage_source_audit_reaudit_20260611.md)|G6 저장량 원천 후보 컬럼 23개 테이블/185개 컬럼 재감사|
|[docs/929_storage_raw_text_strict_extract_reaudit_20260611.md](docs/929_storage_raw_text_strict_extract_reaudit_20260611.md)|G6 원문 strict 저장량 후보 2개 시설/3행 추출 보고|
|[docs/930_storage_uplift_candidate_reaudit_20260611.md](docs/930_storage_uplift_candidate_reaudit_20260611.md)|G6 저장/설비 후보 17,437행, 8,568개 시설 재생성 보고|
|[docs/931_storage_capacity_confirmation_pack_refresh_20260611.md](docs/931_storage_capacity_confirmation_pack_refresh_20260611.md)|G6 저장량 확인팩 12,303행, 8,567개 시설 최신 export|
|[docs/932_storage_batch_manifest_refresh_20260611.md](docs/932_storage_batch_manifest_refresh_20260611.md)|G6 저장량 batch manifest 96개 배치 최신 생성|
|[docs/933_completion_execution_board_after_storage_reaudit_20260611.md](docs/933_completion_execution_board_after_storage_reaudit_20260611.md)|G6 최신 입력팩 반영 100% 통합 실행 보드|
|[docs/934_external_workpack_manifest_after_storage_reaudit_20260611.md](docs/934_external_workpack_manifest_after_storage_reaudit_20260611.md)|G6 갱신 후 외부 workpack manifest 최신 보고|
|[docs/935_external_intake_status_after_storage_reaudit_20260611.md](docs/935_external_intake_status_after_storage_reaudit_20260611.md)|G6 갱신 후 외부 결과파일 intake 상태 최신 보고|
|[docs/936_result_file_execution_plan_after_storage_reaudit_20260611.md](docs/936_result_file_execution_plan_after_storage_reaudit_20260611.md)|G6 갱신 후 결과파일 실행계획, import 가능 0건 판정|
|[docs/937_external_dependency_blockers_after_storage_reaudit_20260611.md](docs/937_external_dependency_blockers_after_storage_reaudit_20260611.md)|G6 저장량 재감사 후 외부 의존성 원장 최신 보고|
|[docs/938_completion_input_gap_after_storage_reaudit_20260611.md](docs/938_completion_input_gap_after_storage_reaudit_20260611.md)|G6 저장량 재감사 후 입력 Gap 최신 보고|
|[docs/939_platform_qa_suite_after_storage_reaudit_api_g57_20260611.md](docs/939_platform_qa_suite_after_storage_reaudit_api_g57_20260611.md)|G6 저장량 재감사 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/940_platform_completion_gate_after_storage_reaudit_20260611.md](docs/940_platform_completion_gate_after_storage_reaudit_20260611.md)|G6 저장량 재감사 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/941_g6_storage_capacity_reaudit_report_20260611.md](docs/941_g6_storage_capacity_reaudit_report_20260611.md)|G6 유류·가스·수소 저장량 재감사 및 입력팩 갱신 종합 보고|
|[docs/942_import_smoke_suite_20260611.md](docs/942_import_smoke_suite_20260611.md)|G3~G12 결과양식 export/import/모델 smoke 통합 suite 19/19 PASS 보고|
|[docs/943_import_smoke_suite_implementation_report_20260611.md](docs/943_import_smoke_suite_implementation_report_20260611.md)|G3~G12 Import Smoke Suite 구현 및 토큰 미기록 검증 보고|
|[docs/944_platform_qa_suite_after_import_smoke_suite_api_g57_20260611.md](docs/944_platform_qa_suite_after_import_smoke_suite_api_g57_20260611.md)|Import Smoke Suite 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/945_platform_completion_gate_after_import_smoke_suite_20260611.md](docs/945_platform_completion_gate_after_import_smoke_suite_20260611.md)|Import Smoke Suite 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/946_external_impact_priority_after_import_smoke_suite_20260611.md](docs/946_external_impact_priority_after_import_smoke_suite_20260611.md)|외부 원천 투입 영향도 우선순위 최신 보고, 최상위 G3 경기도 주유소 좌표 배치|
|[docs/947_g3_g5_workpack_index_after_import_smoke_suite_20260611.md](docs/947_g3_g5_workpack_index_after_import_smoke_suite_20260611.md)|G3~G5 workpack index 183개, 13,049행 및 우선 사이트 1,000개 생성 보고|
|[docs/948_next_input_operator_brief_after_import_smoke_suite_20260611.md](docs/948_next_input_operator_brief_after_import_smoke_suite_20260611.md)|다음 외부 입력 운영 브리프, gate별 최우선 결과양식과 작업 규칙 정리|
|[docs/949_platform_qa_suite_after_operator_brief_api_g57_20260611.md](docs/949_platform_qa_suite_after_operator_brief_api_g57_20260611.md)|운영 브리프 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/950_platform_completion_gate_after_operator_brief_20260611.md](docs/950_platform_completion_gate_after_operator_brief_20260611.md)|운영 브리프 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/951_auction_provider_secure_access_preflight_refresh_20260611.md](docs/951_auction_provider_secure_access_preflight_refresh_20260611.md)|인포케어·옥션원 계정값 미보유 및 브라우저 로그인 필요 상태 최신 재확인|
|[docs/952_auction_case_quality_refresh_after_credential_check_20260611.md](docs/952_auction_case_quality_refresh_after_credential_check_20260611.md)|경매 117행 사건번호 품질 재검사, 유효 법원 사건번호 0건 판정|
|[docs/953_auction_case_resolution_pack_after_credential_check_20260611.md](docs/953_auction_case_resolution_pack_after_credential_check_20260611.md)|옥션원 관리번호 76행/49개 시설 법원 사건번호 보정팩 최신 재생성|
|[docs/954_external_provider_session_plan_after_credential_check_20260611.md](docs/954_external_provider_session_plan_after_credential_check_20260611.md)|외부 Provider 9개 세션 계획 최신화, 준비 세션 0개 및 남은 입력 128,499건|
|[docs/955_auction_provider_workbench_after_credential_check_20260611.md](docs/955_auction_provider_workbench_after_credential_check_20260611.md)|G7/G8 경매 작업대 583개 배치와 검색행 100,005행 최신 갱신|
|[docs/956_auction_provider_intake_preflight_after_credential_check_20260611.md](docs/956_auction_provider_intake_preflight_after_credential_check_20260611.md)|G7/G8 경매 결과파일 strict preflight, import 가능 0행 판정|
|[docs/957_auction_credential_case_resolution_status_report_20260611.md](docs/957_auction_credential_case_resolution_status_report_20260611.md)|경매 계정·사건번호 보강 상태 요약 및 다음 실행 기준|
|[docs/958_platform_qa_suite_after_auction_credential_refresh_api_g57_20260611.md](docs/958_platform_qa_suite_after_auction_credential_refresh_api_g57_20260611.md)|경매 계정·사건번호 보강 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/959_platform_completion_gate_after_auction_credential_refresh_20260611.md](docs/959_platform_completion_gate_after_auction_credential_refresh_20260611.md)|경매 계정·사건번호 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/960_g11_planning_internal_uplift_reaudit_after_auction_refresh_20260611.md](docs/960_g11_planning_internal_uplift_reaudit_after_auction_refresh_20260611.md)|G11 도시계획 내부 상향 가능성 재감사, 내부 안전 보강 후보 없음 판정|
|[docs/961_bldrg_zoning_planning_rejoin_dryrun_after_auction_refresh_20260611.md](docs/961_bldrg_zoning_planning_rejoin_dryrun_after_auction_refresh_20260611.md)|건축HUB 용도지역 재조인 dry-run, 후보 11,601행/4,752시설로 기존 반영분과 동일 확인|
|[docs/962_planning_batch_manifest_refresh_after_internal_reaudit_20260611.md](docs/962_planning_batch_manifest_refresh_after_internal_reaudit_20260611.md)|G11 도시계획·도로 영향 미연결 3,816건 최신 배치 manifest 재생성|
|[docs/963_g11_g12_planning_pass_threshold_pack_20260611.md](docs/963_g11_g12_planning_pass_threshold_pack_20260611.md)|G11/G12 80% 통과를 위한 최소 우선 배치팩 86개/2,179시설 생성|
|[docs/964_platform_qa_suite_after_g11_threshold_pack_api_g57_20260611.md](docs/964_platform_qa_suite_after_g11_threshold_pack_api_g57_20260611.md)|G11/G12 threshold pack 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/965_platform_completion_gate_after_g11_threshold_pack_20260611.md](docs/965_platform_completion_gate_after_g11_threshold_pack_20260611.md)|G11/G12 threshold pack 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/966_g9_g10_revenue_pass_threshold_pack_20260611.md](docs/966_g9_g10_revenue_pass_threshold_pack_20260611.md)|G9/G10 카드·재무 80% 통과를 위한 최소 입력팩 6,855시설/910배치 생성|
|[docs/967_platform_qa_suite_after_revenue_threshold_pack_api_g57_20260611.md](docs/967_platform_qa_suite_after_revenue_threshold_pack_api_g57_20260611.md)|G9/G10 threshold pack 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/968_platform_completion_gate_after_revenue_threshold_pack_20260611.md](docs/968_platform_completion_gate_after_revenue_threshold_pack_20260611.md)|G9/G10 threshold pack 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/969_g3_g5_pass_threshold_pack_20260611.md](docs/969_g3_g5_pass_threshold_pack_20260611.md)|G3/G4/G5 위치·토지·건물 동시 통과를 위한 최소 입력팩 7,195시설 생성|
|[docs/970_platform_qa_suite_after_g3_g5_threshold_pack_api_g57_20260611.md](docs/970_platform_qa_suite_after_g3_g5_threshold_pack_api_g57_20260611.md)|G3/G4/G5 threshold pack 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/971_platform_completion_gate_after_g3_g5_threshold_pack_20260611.md](docs/971_platform_completion_gate_after_g3_g5_threshold_pack_20260611.md)|G3/G4/G5 threshold pack 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/972_g6_storage_pass_threshold_pack_20260611.md](docs/972_g6_storage_pass_threshold_pack_20260611.md)|G6 저장량 95% 통과를 위한 최소 입력팩 8,138시설 생성|
|[docs/973_platform_qa_suite_after_g6_threshold_pack_api_g57_20260611.md](docs/973_platform_qa_suite_after_g6_threshold_pack_api_g57_20260611.md)|G6 threshold pack 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/974_platform_completion_gate_after_g6_threshold_pack_20260611.md](docs/974_platform_completion_gate_after_g6_threshold_pack_20260611.md)|G6 threshold pack 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/975_g7_g8_auction_pass_threshold_pack_20260611.md](docs/975_g7_g8_auction_pass_threshold_pack_20260611.md)|G7/G8 경매 검색 100,005행을 시설 단위 8,568행으로 압축한 통과 입력팩|
|[docs/976_platform_qa_suite_after_g7_g8_threshold_pack_api_g57_20260611.md](docs/976_platform_qa_suite_after_g7_g8_threshold_pack_api_g57_20260611.md)|G7/G8 threshold pack 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/977_platform_completion_gate_after_g7_g8_threshold_pack_20260611.md](docs/977_platform_completion_gate_after_g7_g8_threshold_pack_20260611.md)|G7/G8 threshold pack 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/978_threshold_execution_board_20260611.md](docs/978_threshold_execution_board_20260611.md)|G3~G12 threshold pack과 strict importer를 연결한 통합 실행보드|
|[docs/979_platform_qa_suite_after_threshold_execution_board_api_g57_20260611.md](docs/979_platform_qa_suite_after_threshold_execution_board_api_g57_20260611.md)|Threshold 실행보드 및 인증 응답 개선 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/980_platform_completion_gate_after_threshold_execution_board_20260611.md](docs/980_platform_completion_gate_after_threshold_execution_board_20260611.md)|Threshold 실행보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/981_platform_qa_suite_after_threshold_board_api_ui_g58_20260611.md](docs/981_platform_qa_suite_after_threshold_board_api_ui_g58_20260611.md)|G3~G12 Threshold 실행보드 API/UI 연결 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/982_platform_completion_gate_after_threshold_board_api_ui_20260611.md](docs/982_platform_completion_gate_after_threshold_board_api_ui_20260611.md)|G3~G12 Threshold 실행보드 API/UI 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/983_threshold_execution_board_api_ui_implementation_report_20260611.md](docs/983_threshold_execution_board_api_ui_implementation_report_20260611.md)|G3~G12 Threshold 실행보드 API/UI 구현 및 검증 종합 보고|
|[docs/984_threshold_execution_board_safe_runner_20260611.md](docs/984_threshold_execution_board_safe_runner_20260611.md)|G3~G12 Threshold 실행보드를 안전 실행기 기반 명령으로 재생성|
|[docs/985_platform_qa_suite_after_threshold_safe_runner_api_g58_20260611.md](docs/985_platform_qa_suite_after_threshold_safe_runner_api_g58_20260611.md)|Threshold 안전 실행기 반영 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/986_platform_completion_gate_after_threshold_safe_runner_20260611.md](docs/986_platform_completion_gate_after_threshold_safe_runner_20260611.md)|Threshold 안전 실행기 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/987_threshold_safe_runner_implementation_report_20260611.md](docs/987_threshold_safe_runner_implementation_report_20260611.md)|G3~G12 Threshold 안전 실행기 구현 및 검증 종합 보고|
|[docs/988_platform_qa_suite_after_threshold_runner_plan_api_ui_g59_20260611.md](docs/988_platform_qa_suite_after_threshold_runner_plan_api_ui_g59_20260611.md)|Threshold 안전 실행기 Plan API/UI 추가 후 API 포함 G15 QA 12/12 PASS 보고|
|[docs/989_platform_completion_gate_after_threshold_runner_plan_api_ui_20260611.md](docs/989_platform_completion_gate_after_threshold_runner_plan_api_ui_20260611.md)|Threshold 안전 실행기 Plan API/UI 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/990_threshold_runner_plan_api_ui_implementation_report_20260611.md](docs/990_threshold_runner_plan_api_ui_implementation_report_20260611.md)|Threshold 안전 실행기 Plan API/UI 구현 및 검증 종합 보고|
|[docs/991_threshold_result_workpack_20260611.md](docs/991_threshold_result_workpack_20260611.md)|G3~G12 최소 통과용 결과양식 Workpack 10개 Gate / 128,521행 생성 보고|
|[docs/992_platform_qa_suite_after_threshold_result_workpack_api_ui_g60_20260611.md](docs/992_platform_qa_suite_after_threshold_result_workpack_api_ui_g60_20260611.md)|Threshold 결과양식 Workpack API/UI 추가 후 G15 QA 12/12 PASS 보고|
|[docs/993_platform_completion_gate_after_threshold_result_workpack_20260611.md](docs/993_platform_completion_gate_after_threshold_result_workpack_20260611.md)|Threshold 결과양식 Workpack 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/994_threshold_result_workpack_api_ui_implementation_report_20260611.md](docs/994_threshold_result_workpack_api_ui_implementation_report_20260611.md)|Threshold 결과양식 Workpack 생성기, API, UI 구현 종합 보고|
|[docs/995_auction_provider_secure_access_preflight_session_alias_refresh_20260611.md](docs/995_auction_provider_secure_access_preflight_session_alias_refresh_20260611.md)|인포케어·옥션원 계정 별칭 감지 보강 후 Codex 계정값 미보유 재확인|
|[docs/996_auction_provider_credential_policy_alias_refresh_20260611.md](docs/996_auction_provider_credential_policy_alias_refresh_20260611.md)|경매 Provider 계정 보안정책 별칭 감지 및 QA 보강 보고|
|[docs/997_platform_qa_suite_after_auction_credential_policy_alias_g61_20260611.md](docs/997_platform_qa_suite_after_auction_credential_policy_alias_g61_20260611.md)|경매 계정 보안정책 별칭 보강 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/998_platform_completion_gate_after_auction_credential_policy_alias_20260611.md](docs/998_platform_completion_gate_after_auction_credential_policy_alias_20260611.md)|경매 계정 보안정책 별칭 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/999_external_result_contract_audit_20260611.md](docs/999_external_result_contract_audit_20260611.md)|G3~G12 외부 결과 CSV 계약감사, 결과양식 128,521행 및 주입 후보 0행 판정|
|[docs/1000_platform_qa_suite_after_external_result_contract_audit_api_ui_g62_20260611.md](docs/1000_platform_qa_suite_after_external_result_contract_audit_api_ui_g62_20260611.md)|외부 결과 CSV 계약감사 API/UI 추가 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1001_platform_completion_gate_after_external_result_contract_audit_20260611.md](docs/1001_platform_completion_gate_after_external_result_contract_audit_20260611.md)|외부 결과 CSV 계약감사 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/1002_external_result_contract_audit_api_ui_implementation_report_20260611.md](docs/1002_external_result_contract_audit_api_ui_implementation_report_20260611.md)|외부 결과 CSV 계약감사 DB/API/UI 구현 종합 보고|
|[docs/1003_external_intake_status_after_alias_aware_contract_20260611.md](docs/1003_external_intake_status_after_alias_aware_contract_20260611.md)|한글 별칭 인식 반영 후 외부 intake 상태 갱신 보고|
|[docs/1004_external_result_file_scan_after_alias_aware_contract_20260611.md](docs/1004_external_result_file_scan_after_alias_aware_contract_20260611.md)|한글 별칭 인식 반영 후 외장하드 result CSV 240파일 스캔 보고|
|[docs/1005_result_file_execution_plan_after_alias_aware_contract_20260611.md](docs/1005_result_file_execution_plan_after_alias_aware_contract_20260611.md)|한글 별칭 인식 반영 후 외부 결과파일 실행대장 갱신 보고|
|[docs/1006_external_result_contract_audit_after_alias_aware_scan_20260611.md](docs/1006_external_result_contract_audit_after_alias_aware_scan_20260611.md)|한글 별칭 인식 반영 후 외부 결과 CSV 계약감사 최신 보고|
|[docs/1007_platform_qa_suite_after_alias_aware_result_contract_g63_20260611.md](docs/1007_platform_qa_suite_after_alias_aware_result_contract_g63_20260611.md)|한글 별칭 인식 보강 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1008_platform_completion_gate_after_alias_aware_result_contract_20260611.md](docs/1008_platform_completion_gate_after_alias_aware_result_contract_20260611.md)|한글 별칭 인식 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/1009_alias_aware_external_result_contract_implementation_report_20260611.md](docs/1009_alias_aware_external_result_contract_implementation_report_20260611.md)|외부 결과 CSV 한글/Provider 별칭 인식 보강 종합 보고|
|[docs/1010_auction_provider_session_launcher_20260611.md](docs/1010_auction_provider_session_launcher_20260611.md)|인포케어·옥션원 브라우저 로그인 기반 경매 세션 실행팩 32행 생성 보고|
|[docs/1011_platform_qa_suite_after_auction_session_launcher_g64_20260611.md](docs/1011_platform_qa_suite_after_auction_session_launcher_g64_20260611.md)|경매 세션 실행팩 API/UI 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1012_platform_completion_gate_after_auction_session_launcher_20260611.md](docs/1012_platform_completion_gate_after_auction_session_launcher_20260611.md)|경매 세션 실행팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/1013_auction_provider_session_launcher_implementation_report_20260611.md](docs/1013_auction_provider_session_launcher_implementation_report_20260611.md)|경매 세션 실행팩 DB/API/UI/QA 구현 종합 보고|
|[docs/1014_auction_provider_browser_workboard_20260611.md](docs/1014_auction_provider_browser_workboard_20260611.md)|인포케어·옥션원 브라우저 검색용 경매 작업보드 120행 생성 보고|
|[docs/1015_platform_qa_suite_after_auction_browser_workboard_g65_20260611.md](docs/1015_platform_qa_suite_after_auction_browser_workboard_g65_20260611.md)|경매 브라우저 작업보드 API/UI 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1016_platform_completion_gate_after_auction_browser_workboard_20260611.md](docs/1016_platform_completion_gate_after_auction_browser_workboard_20260611.md)|경매 브라우저 작업보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/1017_auction_provider_browser_workboard_implementation_report_20260611.md](docs/1017_auction_provider_browser_workboard_implementation_report_20260611.md)|경매 브라우저 작업보드 DB/API/UI/QA 구현 종합 보고|
|[docs/1018_auction_browser_workboard_result_adapter_20260611.md](docs/1018_auction_browser_workboard_result_adapter_20260611.md)|경매 브라우저 작업보드 결과 CSV 어댑터 실행 보고|
|[docs/1019_platform_qa_suite_after_auction_workboard_result_adapter_g66_20260611.md](docs/1019_platform_qa_suite_after_auction_workboard_result_adapter_g66_20260611.md)|경매 작업보드 결과 어댑터 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1020_platform_completion_gate_after_auction_workboard_result_adapter_20260611.md](docs/1020_platform_completion_gate_after_auction_workboard_result_adapter_20260611.md)|경매 작업보드 결과 어댑터 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/1021_auction_workboard_result_adapter_implementation_report_20260611.md](docs/1021_auction_workboard_result_adapter_implementation_report_20260611.md)|경매 작업보드 결과 어댑터 구현 종합 보고|
|[docs/1022_auction_provider_session_launcher_gate_balanced_20260611.md](docs/1022_auction_provider_session_launcher_gate_balanced_20260611.md)|provider+gate 단위 경매 세션 런처 재생성 보고|
|[docs/1023_current_auction_browser_workboard_20260611.md](docs/1023_current_auction_browser_workboard_20260611.md)|현재 경매 G8 브라우저 작업보드 120행 생성 보고|
|[docs/1024_current_auction_workboard_result_adapter_20260611.md](docs/1024_current_auction_workboard_result_adapter_20260611.md)|현재 경매 G8 작업보드 결과 어댑터 실행 보고|
|[docs/1025_platform_qa_suite_after_current_auction_workboard_g67_20260611.md](docs/1025_platform_qa_suite_after_current_auction_workboard_g67_20260611.md)|현재 경매 작업보드 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1026_platform_completion_gate_after_current_auction_workboard_20260611.md](docs/1026_platform_completion_gate_after_current_auction_workboard_20260611.md)|현재 경매 작업보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/1027_current_auction_workboard_implementation_report_20260611.md](docs/1027_current_auction_workboard_implementation_report_20260611.md)|현재 경매 G8 브라우저 작업보드 구현 종합 보고|
|[docs/1028_auction_browser_workboard_g7_g8_balanced_20260612.md](docs/1028_auction_browser_workboard_g7_g8_balanced_20260612.md)|G7/G8 통합 경매 브라우저 작업보드 240행 생성 보고|
|[docs/1029_auction_workboard_g7_g8_result_adapter_20260612.md](docs/1029_auction_workboard_g7_g8_result_adapter_20260612.md)|G7/G8 통합 경매 작업보드 결과 어댑터 실행 보고|
|[docs/1030_platform_qa_suite_after_g7_g8_workboard_g68_20260612.md](docs/1030_platform_qa_suite_after_g7_g8_workboard_g68_20260612.md)|G7/G8 통합 경매 작업보드 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1031_platform_completion_gate_after_g7_g8_workboard_20260612.md](docs/1031_platform_completion_gate_after_g7_g8_workboard_20260612.md)|G7/G8 통합 경매 작업보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1032_platform_qa_suite_after_g7_g8_interleaved_api_g69_20260612.md](docs/1032_platform_qa_suite_after_g7_g8_interleaved_api_g69_20260612.md)|G7/G8 교차 API 정렬 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1033_platform_completion_gate_after_g7_g8_interleaved_api_20260612.md](docs/1033_platform_completion_gate_after_g7_g8_interleaved_api_20260612.md)|G7/G8 교차 API 정렬 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1034_g7_g8_balanced_auction_workboard_implementation_report_20260612.md](docs/1034_g7_g8_balanced_auction_workboard_implementation_report_20260612.md)|G7/G8 통합 경매 작업보드와 교차 API 정렬 구현 종합 보고|
|[docs/1035_revenue_input_workboard_20260612.md](docs/1035_revenue_input_workboard_20260612.md)|G9/G10 카드·재무 입력 작업보드 240행 생성 보고|
|[docs/1036_platform_qa_suite_after_revenue_input_workboard_g70_20260612.md](docs/1036_platform_qa_suite_after_revenue_input_workboard_g70_20260612.md)|매출·재무 입력 작업보드 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1037_platform_completion_gate_after_revenue_input_workboard_20260612.md](docs/1037_platform_completion_gate_after_revenue_input_workboard_20260612.md)|매출·재무 입력 작업보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1038_revenue_input_workboard_implementation_report_20260612.md](docs/1038_revenue_input_workboard_implementation_report_20260612.md)|매출·재무 입력 작업보드 API/UI/QA 구현 종합 보고|
|[docs/1039_revenue_input_workboard_result_adapter_20260612.md](docs/1039_revenue_input_workboard_result_adapter_20260612.md)|G9/G10 매출·재무 작업보드 결과 입력 CSV를 strict import-ready CSV로 변환하는 어댑터 실행 보고|
|[docs/1040_platform_qa_suite_after_revenue_workboard_result_adapter_g71_20260612.md](docs/1040_platform_qa_suite_after_revenue_workboard_result_adapter_g71_20260612.md)|매출·재무 결과 어댑터 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1041_platform_completion_gate_after_revenue_workboard_result_adapter_20260612.md](docs/1041_platform_completion_gate_after_revenue_workboard_result_adapter_20260612.md)|매출·재무 결과 어댑터 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1042_revenue_workboard_result_adapter_implementation_report_20260612.md](docs/1042_revenue_workboard_result_adapter_implementation_report_20260612.md)|매출·재무 결과 어댑터 구현, 스모크 테스트, QA, 완료율 종합 보고|
|[docs/1043_internal_uplift_opportunity_refresh_20260612.md](docs/1043_internal_uplift_opportunity_refresh_20260612.md)|G3~G6 내부 자동 보강 가능성 재감사 보고|
|[docs/1044_g11_planning_internal_uplift_refresh_20260612.md](docs/1044_g11_planning_internal_uplift_refresh_20260612.md)|G11 도시계획 내부 보강 가능성 재감사 보고|
|[docs/1045_planning_input_workboard_20260612.md](docs/1045_planning_input_workboard_20260612.md)|G11 도시계획·도로 입력 작업보드 240행 생성 보고|
|[docs/1046_planning_workboard_result_adapter_20260612.md](docs/1046_planning_workboard_result_adapter_20260612.md)|G11 도시계획·도로 작업보드 결과 어댑터 실행 보고|
|[docs/1047_platform_qa_suite_after_planning_workboard_g72_20260612.md](docs/1047_platform_qa_suite_after_planning_workboard_g72_20260612.md)|G11 작업보드 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1048_platform_completion_gate_after_planning_workboard_20260612.md](docs/1048_platform_completion_gate_after_planning_workboard_20260612.md)|G11 작업보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1049_planning_workboard_implementation_report_20260612.md](docs/1049_planning_workboard_implementation_report_20260612.md)|G11 작업보드/API/어댑터/QA 구현 종합 보고|
|[docs/1050_platform_qa_suite_after_planning_ui_detail_g73_20260612.md](docs/1050_platform_qa_suite_after_planning_ui_detail_g73_20260612.md)|G11 상세 UI 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1051_platform_completion_gate_after_planning_ui_detail_20260612.md](docs/1051_platform_completion_gate_after_planning_ui_detail_20260612.md)|G11 상세 UI 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1052_planning_ui_detail_implementation_report_20260612.md](docs/1052_planning_ui_detail_implementation_report_20260612.md)|G11 도시계획 작업보드 상세 UI 구현 보고|
|[docs/1053_platform_qa_suite_after_workboard_preflight_ui_g74_20260612.md](docs/1053_platform_qa_suite_after_workboard_preflight_ui_g74_20260612.md)|작업보드 결과 preflight UI/API 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1054_platform_completion_gate_after_workboard_preflight_ui_20260612.md](docs/1054_platform_completion_gate_after_workboard_preflight_ui_20260612.md)|작업보드 결과 preflight UI/API 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1055_energy_site_indexes_after_workboard_preflight_20260612.md](docs/1055_energy_site_indexes_after_workboard_preflight_20260612.md)|작업보드 결과 preflight 조회 인덱스 적용 보고|
|[docs/1056_platform_qa_suite_after_workboard_preflight_index_g75_20260612.md](docs/1056_platform_qa_suite_after_workboard_preflight_index_g75_20260612.md)|preflight 인덱스 반영 후 최종 플랫폼 QA 12/12 PASS 보고|
|[docs/1057_platform_completion_gate_after_workboard_preflight_index_20260612.md](docs/1057_platform_completion_gate_after_workboard_preflight_index_20260612.md)|preflight 인덱스 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1058_workboard_result_preflight_ui_implementation_report_20260612.md](docs/1058_workboard_result_preflight_ui_implementation_report_20260612.md)|작업보드 결과 preflight UI/API/인덱스 구현 종합 보고|
|[docs/1059_platform_qa_suite_after_preflight_csv_download_g76_20260612.md](docs/1059_platform_qa_suite_after_preflight_csv_download_g76_20260612.md)|preflight CSV 다운로드 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1060_platform_completion_gate_after_preflight_csv_download_20260612.md](docs/1060_platform_completion_gate_after_preflight_csv_download_20260612.md)|preflight CSV 다운로드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1061_preflight_csv_download_implementation_report_20260612.md](docs/1061_preflight_csv_download_implementation_report_20260612.md)|작업보드 결과 preflight CSV 다운로드 구현 보고|
|[docs/1062_external_result_file_scan_template_status_20260612.md](docs/1062_external_result_file_scan_template_status_20260612.md)|외장하드 result CSV 4,000개를 미입력 결과양식으로 분리 판정한 스캔 보고|
|[docs/1063_result_file_execution_plan_after_template_status_20260612.md](docs/1063_result_file_execution_plan_after_template_status_20260612.md)|미입력 결과양식 상태 반영 후 외부 결과파일 실행대장 보고|
|[docs/1064_external_result_contract_audit_after_template_status_20260612.md](docs/1064_external_result_contract_audit_after_template_status_20260612.md)|미입력 결과양식 상태 반영 후 외부 결과 CSV 계약감사 보고|
|[docs/1065_platform_qa_suite_after_template_status_scan_g77_20260612.md](docs/1065_platform_qa_suite_after_template_status_scan_g77_20260612.md)|미입력 결과양식 상태 가드 반영 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1066_platform_completion_gate_after_template_status_scan_20260612.md](docs/1066_platform_completion_gate_after_template_status_scan_20260612.md)|미입력 결과양식 상태 가드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1067_external_result_template_status_guard_implementation_report_20260612.md](docs/1067_external_result_template_status_guard_implementation_report_20260612.md)|외부 결과파일 템플릿 상태 가드 구현 종합 보고|
|[docs/1068_internal_coordinate_match_dryrun_20260612.md](docs/1068_internal_coordinate_match_dryrun_20260612.md)|G3 내부 동일주소 좌표 보강 dry-run 결과 적용 후보 0건 보고|
|[docs/1069_coordinate_uplift_apply_dryrun_20260612.md](docs/1069_coordinate_uplift_apply_dryrun_20260612.md)|G3 좌표 uplift 후보 적용 dry-run 결과 적용 후보 0건 보고|
|[docs/1070_geocode_api_key_preflight_no_key_20260612.md](docs/1070_geocode_api_key_preflight_no_key_20260612.md)|JUSO API key 미설정 상태와 좌표 누락 READY 요청 6,094건 보고|
|[docs/1071_g3_geocode_secure_batch_drycheck_no_key_20260612.md](docs/1071_g3_geocode_secure_batch_drycheck_no_key_20260612.md)|G3 보안 배치 dry-check key 미설정 차단 보고|
|[docs/1072_g3_geocode_secure_batch_with_preflight_drycheck_20260612.md](docs/1072_g3_geocode_secure_batch_with_preflight_drycheck_20260612.md)|preflight 포함 G3 보안 배치 dry-check 차단 보고|
|[docs/1073_g3_geocode_secure_preflight_drycheck_20260612.md](docs/1073_g3_geocode_secure_preflight_drycheck_20260612.md)|preflight 포함 G3 보안 배치의 JUSO key 점검 보고|
|[docs/1074_g3_coordinate_readiness_and_secure_runner_report_20260612.md](docs/1074_g3_coordinate_readiness_and_secure_runner_report_20260612.md)|G3 좌표 보강 준비상태와 보안 실행 스크립트 보강 종합 보고|
|[docs/1075_platform_qa_suite_after_g3_readiness_hardening_g78_20260612.md](docs/1075_platform_qa_suite_after_g3_readiness_hardening_g78_20260612.md)|G3 보안 실행 흐름 보강 후 플랫폼 QA 12/12 PASS 보고|
|[docs/1076_platform_completion_gate_after_g3_readiness_hardening_20260612.md](docs/1076_platform_completion_gate_after_g3_readiness_hardening_20260612.md)|G3 보안 실행 흐름 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1077_land_area_pnu_uplift_rerun_20260612.md](docs/1077_land_area_pnu_uplift_rerun_20260612.md)|G4 PNU 직접 대지면적 보강 재실행, 추가 상향 없음 보고|
|[docs/1078_internal_pnu_building_link_dryrun_20260612.md](docs/1078_internal_pnu_building_link_dryrun_20260612.md)|G5 내부 PNU 기반 건축물 링크 dry-run, 기존 후보와 동일 확인|
|[docs/1079_internal_same_address_pnu_dryrun_20260612.md](docs/1079_internal_same_address_pnu_dryrun_20260612.md)|내부 동일주소 PNU 보강 dry-run, 적용 후보 0건 보고|
|[docs/1080_g11_planning_internal_uplift_audit_20260612.md](docs/1080_g11_planning_internal_uplift_audit_20260612.md)|G11 도시계획 내부 상향 가능성 감사, 내부 안전 보강 없음 판정|
|[docs/1081_bldrg_zoning_planning_rejoin_dryrun_20260612.md](docs/1081_bldrg_zoning_planning_rejoin_dryrun_20260612.md)|건축HUB 용도지역 재조인 dry-run, 기존 11,601행/4,752시설과 동일 확인|
|[docs/1082_platform_completion_gate_before_current_uplift_20260612.md](docs/1082_platform_completion_gate_before_current_uplift_20260612.md)|G4/G5/G11 재감사 중간 100% 완료 게이트 read-only 보고|
|[docs/1083_platform_completion_gate_after_g4_g5_g11_reaudit_20260612.md](docs/1083_platform_completion_gate_after_g4_g5_g11_reaudit_20260612.md)|G4/G5/G11 재감사 후 100% 완료 게이트 DB write 성공 보고|
|[docs/1084_operational_duckdb_lock_blocker_audit_after_reaudit_20260612.md](docs/1084_operational_duckdb_lock_blocker_audit_after_reaudit_20260612.md)|운영 DuckDB lock blocker 재감사, write blocker 없음 확인|
|[docs/1085_platform_qa_suite_after_g4_g5_g11_reaudit_20260612.md](docs/1085_platform_qa_suite_after_g4_g5_g11_reaudit_20260612.md)|G4/G5/G11 재감사 후 API 제외 QA 9 PASS / 1 SKIP 중간 보고|
|[docs/1086_platform_qa_suite_after_g4_g5_g11_reaudit_api_20260612.md](docs/1086_platform_qa_suite_after_g4_g5_g11_reaudit_api_20260612.md)|G4/G5/G11 재감사 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/1087_platform_completion_gate_after_g4_g5_g11_reaudit_api_qa_20260612.md](docs/1087_platform_completion_gate_after_g4_g5_g11_reaudit_api_qa_20260612.md)|G4/G5/G11 재감사 및 API QA 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1088_g4_g5_g11_reaudit_implementation_report_20260612.md](docs/1088_g4_g5_g11_reaudit_implementation_report_20260612.md)|G4/G5/G11 내부 보강 재감사 종합 보고, 현재 37.5% 완료 판정|
|[docs/1089_import_smoke_suite_after_current_auction_strict_guard_20260612.md](docs/1089_import_smoke_suite_after_current_auction_strict_guard_20260612.md)|G8 현재경매 strict guard 보강 후 G3~G12 import smoke suite 19/19 PASS 보고|
|[docs/1090_current_auction_strict_import_guard_report_20260612.md](docs/1090_current_auction_strict_import_guard_report_20260612.md)|G8 현재경매 확인일·원천증빙·시설ID strict import guard 보강 보고|
|[docs/1091_platform_qa_suite_after_current_auction_strict_guard_20260612.md](docs/1091_platform_qa_suite_after_current_auction_strict_guard_20260612.md)|G8 strict guard 보강 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/1092_platform_completion_gate_after_current_auction_strict_guard_20260612.md](docs/1092_platform_completion_gate_after_current_auction_strict_guard_20260612.md)|G8 strict guard 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1093_import_smoke_suite_after_auction_history_strict_guard_20260612.md](docs/1093_import_smoke_suite_after_auction_history_strict_guard_20260612.md)|G7 과거 경매 strict guard 보강 후 G3~G12 import smoke suite 19/19 PASS 보고|
|[docs/1094_auction_history_strict_import_guard_report_20260612.md](docs/1094_auction_history_strict_import_guard_report_20260612.md)|G7 과거 경매 확인일·원천증빙 분리 strict import guard 보강 보고|
|[docs/1095_platform_qa_suite_after_auction_history_strict_guard_20260612.md](docs/1095_platform_qa_suite_after_auction_history_strict_guard_20260612.md)|G7 strict guard 보강 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/1096_platform_completion_gate_after_auction_history_strict_guard_20260612.md](docs/1096_platform_completion_gate_after_auction_history_strict_guard_20260612.md)|G7 strict guard 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1097_import_smoke_suite_after_revenue_strict_guard_20260612.md](docs/1097_import_smoke_suite_after_revenue_strict_guard_20260612.md)|G9/G10 카드·재무 strict guard 보강 후 G3~G12 import smoke suite 19/19 PASS 보고|
|[docs/1098_revenue_strict_import_guard_report_20260612.md](docs/1098_revenue_strict_import_guard_report_20260612.md)|G9/G10 카드·재무 확인일·원천증빙 분리 strict import guard 보강 보고|
|[docs/1099_platform_qa_suite_after_revenue_strict_guard_20260612.md](docs/1099_platform_qa_suite_after_revenue_strict_guard_20260612.md)|G9/G10 strict guard 보강 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/1100_platform_completion_gate_after_revenue_strict_guard_20260612.md](docs/1100_platform_completion_gate_after_revenue_strict_guard_20260612.md)|G9/G10 strict guard 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1101_import_smoke_suite_after_planning_strict_guard_20260612.md](docs/1101_import_smoke_suite_after_planning_strict_guard_20260612.md)|G11/G12 도시계획 strict guard 보강 후 G3~G12 import smoke suite 19/19 PASS 보고|
|[docs/1102_platform_qa_suite_after_planning_strict_guard_20260612.md](docs/1102_platform_qa_suite_after_planning_strict_guard_20260612.md)|G11/G12 strict guard 보강 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/1103_platform_completion_gate_after_planning_strict_guard_20260612.md](docs/1103_platform_completion_gate_after_planning_strict_guard_20260612.md)|G11/G12 strict guard 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1104_planning_strict_import_guard_report_20260612.md](docs/1104_planning_strict_import_guard_report_20260612.md)|G11/G12 도시계획 확인일·원천증빙 strict import guard 보강 보고|
|[docs/1105_platform_qa_suite_after_prediction_strict_gate_20260612.md](docs/1105_platform_qa_suite_after_prediction_strict_gate_20260612.md)|G12 예측 strict completion gate 반영 후 API 포함 플랫폼 QA 12/12 PASS 보고|
|[docs/1106_platform_completion_gate_after_prediction_strict_gate_20260612.md](docs/1106_platform_completion_gate_after_prediction_strict_gate_20260612.md)|G12 예측 strict completion gate 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1107_platform_qa_suite_after_prediction_gate_qa_guard_20260612.md](docs/1107_platform_qa_suite_after_prediction_gate_qa_guard_20260612.md)|G12 full-input 산식 QA guard 추가 후 플랫폼 QA 13/13 PASS 보고|
|[docs/1108_platform_completion_gate_after_prediction_gate_qa_guard_20260612.md](docs/1108_platform_completion_gate_after_prediction_gate_qa_guard_20260612.md)|G12 full-input 산식 QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1109_prediction_strict_completion_gate_report_20260612.md](docs/1109_prediction_strict_completion_gate_report_20260612.md)|G12 예측 완료 산식 full-input 기준 정정 및 QA guard 보강 보고|
|[docs/1110_platform_completion_gate_after_planning_strict_impact_gate_20260612.md](docs/1110_platform_completion_gate_after_planning_strict_impact_gate_20260612.md)|G11 CURRENT_ZONING 과대평가 제거 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1111_platform_qa_suite_after_planning_strict_impact_gate_20260612.md](docs/1111_platform_qa_suite_after_planning_strict_impact_gate_20260612.md)|G11 strict planning 산식 QA guard 추가 후 플랫폼 QA 14/14 PASS 보고|
|[docs/1112_platform_completion_gate_after_planning_strict_qa_guard_20260612.md](docs/1112_platform_completion_gate_after_planning_strict_qa_guard_20260612.md)|G11 strict planning QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1113_planning_strict_completion_gate_report_20260612.md](docs/1113_planning_strict_completion_gate_report_20260612.md)|G11 도시계획 완료 산식 future-impact 기준 정정 및 QA guard 보강 보고|
|[docs/1114_platform_completion_gate_after_land_building_strict_gate_20260612.md](docs/1114_platform_completion_gate_after_land_building_strict_gate_20260612.md)|G4/G5 토지·건물 usable 정보 기준 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1115_platform_qa_suite_after_land_building_strict_gate_20260612.md](docs/1115_platform_qa_suite_after_land_building_strict_gate_20260612.md)|G4/G5 strict 산식 QA guard 추가 후 플랫폼 QA 16/16 PASS 보고|
|[docs/1116_platform_completion_gate_after_land_building_qa_guard_20260612.md](docs/1116_platform_completion_gate_after_land_building_qa_guard_20260612.md)|G4/G5 strict QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1117_land_building_strict_completion_gate_report_20260612.md](docs/1117_land_building_strict_completion_gate_report_20260612.md)|G4/G5 토지·건물 완료 산식 usable 정보 기준 정정 및 QA guard 보강 보고|
|[docs/1118_platform_completion_gate_after_storage_strict_gate_20260612.md](docs/1118_platform_completion_gate_after_storage_strict_gate_20260612.md)|G6 저장량 value+unit+source 기준 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1119_platform_qa_suite_after_storage_strict_gate_20260612.md](docs/1119_platform_qa_suite_after_storage_strict_gate_20260612.md)|G6 strict 산식 QA guard 추가 후 플랫폼 QA 17/17 PASS 보고|
|[docs/1120_platform_completion_gate_after_storage_qa_guard_20260612.md](docs/1120_platform_completion_gate_after_storage_qa_guard_20260612.md)|G6 strict QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1121_storage_strict_completion_gate_report_20260612.md](docs/1121_storage_strict_completion_gate_report_20260612.md)|G6 저장량 완료 산식 value+unit+source 기준 정정 및 QA guard 보강 보고|
|[docs/1122_platform_completion_gate_after_auction_strict_gate_20260612.md](docs/1122_platform_completion_gate_after_auction_strict_gate_20260612.md)|G7/G8 경매 strict 완료 산식 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1123_platform_qa_suite_after_auction_strict_gate_20260612.md](docs/1123_platform_qa_suite_after_auction_strict_gate_20260612.md)|G7/G8 strict 산식 QA guard 추가 후 플랫폼 QA 19/19 PASS 보고|
|[docs/1124_platform_completion_gate_after_auction_qa_guard_20260612.md](docs/1124_platform_completion_gate_after_auction_qa_guard_20260612.md)|G7/G8 strict QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1125_auction_strict_completion_gate_report_20260612.md](docs/1125_auction_strict_completion_gate_report_20260612.md)|G7/G8 경매 완료 산식 사건번호·출처·확인일 기준 정정 및 클로드 관점 비판 반영 보고|
|[docs/1126_platform_completion_gate_after_revenue_strict_gate_20260612.md](docs/1126_platform_completion_gate_after_revenue_strict_gate_20260612.md)|G9/G10 카드·재무·수익가치 strict 완료 산식 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1127_platform_qa_suite_after_revenue_strict_gate_20260612.md](docs/1127_platform_qa_suite_after_revenue_strict_gate_20260612.md)|G9/G10 strict 산식 QA guard 추가 후 플랫폼 QA 21/21 PASS 보고|
|[docs/1128_platform_completion_gate_after_revenue_qa_guard_20260612.md](docs/1128_platform_completion_gate_after_revenue_qa_guard_20260612.md)|G9/G10 strict QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1129_revenue_strict_completion_gate_report_20260612.md](docs/1129_revenue_strict_completion_gate_report_20260612.md)|G9/G10 카드·재무·수익가치 완료 산식 권한·출처·확인일 기준 정정 및 클로드 관점 비판 반영 보고|
|[docs/1130_platform_completion_gate_after_location_strict_gate_20260612.md](docs/1130_platform_completion_gate_after_location_strict_gate_20260612.md)|G3 위치 strict 완료 산식 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1131_platform_qa_suite_after_location_strict_gate_20260612.md](docs/1131_platform_qa_suite_after_location_strict_gate_20260612.md)|G3 strict 산식 QA guard 추가 후 플랫폼 QA 22/22 PASS 보고|
|[docs/1132_platform_completion_gate_after_location_qa_guard_20260612.md](docs/1132_platform_completion_gate_after_location_qa_guard_20260612.md)|G3 strict QA guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1133_location_strict_completion_gate_report_20260612.md](docs/1133_location_strict_completion_gate_report_20260612.md)|G3 위치 완료 산식 좌표범위·품질·출처·확인일 기준 정정 및 클로드 관점 비판 반영 보고|
|[docs/1134_g3_g6_internal_uplift_opportunity_audit_20260612.md](docs/1134_g3_g6_internal_uplift_opportunity_audit_20260612.md)|G3~G6 내부 자동상향 가능성 재감사, 즉시 적용 0건 및 외부 원천 필요 판정|
|[docs/1135_coordinate_uplift_candidate_refresh_20260612.md](docs/1135_coordinate_uplift_candidate_refresh_20260612.md)|G3 좌표 후보 refresh, 6,094건 전부 GEOCODE_REQUEST_READY 판정|
|[docs/1136_internal_coordinate_match_dry_run_20260612.md](docs/1136_internal_coordinate_match_dry_run_20260612.md)|내부 동일주소 좌표 매칭 dry-run, 적용 가능 0건 판정|
|[docs/1137_geocode_api_key_preflight_after_location_strict_20260612.md](docs/1137_geocode_api_key_preflight_after_location_strict_20260612.md)|JUSO 주소 API key preflight, KEY_NOT_CONFIGURED 및 6,094 READY 요청 보고|
|[docs/1138_g3_geocode_api_batch_dry_check_20260612.md](docs/1138_g3_geocode_api_batch_dry_check_20260612.md)|G3 좌표 API 배치 dry-check, API key 미설정으로 BLOCKED 보고|
|[docs/1139_geocode_batch_manifest_after_location_strict_20260612.md](docs/1139_geocode_batch_manifest_after_location_strict_20260612.md)|G3 좌표 누락 6,094건 외장하드 21개 geocode 배치 manifest 생성 보고|
|[docs/1140_platform_qa_suite_after_g3_execution_pack_20260612.md](docs/1140_platform_qa_suite_after_g3_execution_pack_20260612.md)|G3 실행팩 생성 후 플랫폼 QA 22/22 PASS 보고|
|[docs/1141_platform_completion_gate_after_g3_execution_pack_20260612.md](docs/1141_platform_completion_gate_after_g3_execution_pack_20260612.md)|G3 실행팩 생성 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1142_g3_coordinate_execution_pack_status_20260612.md](docs/1142_g3_coordinate_execution_pack_status_20260612.md)|G3 좌표 보강 실행팩 상태, 외장하드 manifest와 API key 보안 실행조건 보고|
|[docs/1143_land_area_batch_manifest_after_g3_execution_pack_20260612.md](docs/1143_land_area_batch_manifest_after_g3_execution_pack_20260612.md)|G4 토지 지번·면적 3,587행/96개 외장하드 배치 manifest 최신화|
|[docs/1144_building_batch_manifest_after_g3_execution_pack_20260612.md](docs/1144_building_batch_manifest_after_g3_execution_pack_20260612.md)|G5 건축물대장 건물 3,368행/66개 외장하드 배치 manifest 최신화|
|[docs/1145_g3_g5_gap_table_after_g4_g5_manifest_20260612.md](docs/1145_g3_g5_gap_table_after_g4_g5_manifest_20260612.md)|G3~G5 gap table 최신화, 7,605 gap / 963 complete 보고|
|[docs/1146_g3_g5_pass_threshold_pack_after_manifest_20260612.md](docs/1146_g3_g5_pass_threshold_pack_after_manifest_20260612.md)|G3~G5 95/98% 통과 최소 입력팩 7,195시설 생성 보고|
|[docs/1147_g3_g5_workpack_index_after_manifest_20260612.md](docs/1147_g3_g5_workpack_index_after_manifest_20260612.md)|G3~G5 통합 workpack index 183개/13,049행 생성 보고|
|[docs/1148_platform_qa_suite_after_g4_g5_workpacks_20260612.md](docs/1148_platform_qa_suite_after_g4_g5_workpacks_20260612.md)|G4/G5 작업팩 생성 후 플랫폼 QA 22/22 PASS 보고|
|[docs/1149_platform_completion_gate_after_g4_g5_workpacks_20260612.md](docs/1149_platform_completion_gate_after_g4_g5_workpacks_20260612.md)|G4/G5 작업팩 생성 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1150_g4_g5_land_building_workpack_status_20260612.md](docs/1150_g4_g5_land_building_workpack_status_20260612.md)|G4/G5 토지·건물 보강 workpack 경로와 통과 최소 입력량 종합 보고|
|[docs/1151_auction_provider_secure_access_preflight_20260612.md](docs/1151_auction_provider_secure_access_preflight_20260612.md)|인포케어·옥션원 계정값 미보유, 브라우저 세션 미선언, 즉시 검색 가능 0개 재확인|
|[docs/1152_threshold_result_workpack_refresh_20260612.md](docs/1152_threshold_result_workpack_refresh_20260612.md)|G3~G12 100% 통과용 결과양식 workpack 10개 Gate / 128,521행 최신 생성|
|[docs/1153_threshold_execution_board_refresh_20260612.md](docs/1153_threshold_execution_board_refresh_20260612.md)|최신 결과양식과 strict importer를 연결한 G3~G12 threshold 실행보드 갱신|
|[docs/1154_platform_completion_gate_after_threshold_refresh_20260612.md](docs/1154_platform_completion_gate_after_threshold_refresh_20260612.md)|Threshold workpack 갱신 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1155_external_result_file_scan_after_threshold_refresh_20260612.md](docs/1155_external_result_file_scan_after_threshold_refresh_20260612.md)|외장하드 결과 CSV 260개 스캔, 전부 미입력 양식 및 dry-run 가능 0건 판정|
|[docs/1156_result_file_execution_plan_after_threshold_refresh_20260612.md](docs/1156_result_file_execution_plan_after_threshold_refresh_20260612.md)|외부 결과파일 실행대장 갱신, 실행 가능 0건·입력 대기 260건 보고|
|[docs/1157_external_result_contract_audit_after_threshold_refresh_20260612.md](docs/1157_external_result_contract_audit_after_threshold_refresh_20260612.md)|G3~G12 외부 결과 CSV 계약감사 갱신, 주입 후보 0행 판정|
|[docs/1158_platform_qa_suite_after_threshold_refresh_20260612.md](docs/1158_platform_qa_suite_after_threshold_refresh_20260612.md)|Threshold 갱신 후 API 포함 플랫폼 QA 22/22 PASS 보고|
|[docs/1159_platform_completion_gate_after_result_contract_refresh_20260612.md](docs/1159_platform_completion_gate_after_result_contract_refresh_20260612.md)|결과파일 계약감사·QA 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1160_next_input_operator_brief_after_threshold_refresh_20260612.md](docs/1160_next_input_operator_brief_after_threshold_refresh_20260612.md)|G3~G12 다음 외부 입력 운영 브리프, Gate별 필수값·결과양식·dry-run/import 명령 정리|
|[docs/1161_platform_qa_suite_after_next_input_brief_20260612.md](docs/1161_platform_qa_suite_after_next_input_brief_20260612.md)|다음 입력 운영 브리프 생성기와 DB 테이블 반영 후 API 포함 플랫폼 QA 22/22 PASS 보고|
|[docs/1162_platform_completion_gate_after_next_input_brief_20260612.md](docs/1162_platform_completion_gate_after_next_input_brief_20260612.md)|다음 입력 운영 브리프 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1163_platform_qa_suite_after_next_input_brief_api_ui_20260612.md](docs/1163_platform_qa_suite_after_next_input_brief_api_ui_20260612.md)|다음 입력 운영 브리프 API/UI 연결 후 플랫폼 QA 22/22 PASS 보고|
|[docs/1164_platform_completion_gate_after_next_input_brief_api_ui_20260612.md](docs/1164_platform_completion_gate_after_next_input_brief_api_ui_20260612.md)|다음 입력 브리프 API/UI 연결 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1165_next_input_operator_brief_api_ui_implementation_report_20260612.md](docs/1165_next_input_operator_brief_api_ui_implementation_report_20260612.md)|다음 입력 운영 브리프 API·운영 화면 연결 구현 보고|
|[docs/1166_gate_pass_gap_projection_20260612.md](docs/1166_gate_pass_gap_projection_20260612.md)|G3~G12 100% Gate 통과까지 필요한 추가 Gate-시설 수와 첫 실행 파일 산정|
|[docs/1167_platform_qa_suite_after_gate_pass_gap_projection_20260612.md](docs/1167_platform_qa_suite_after_gate_pass_gap_projection_20260612.md)|Gate 통과 Gap Projection API/UI 연결 후 플랫폼 QA 22/22 PASS 보고|
|[docs/1168_platform_completion_gate_after_gate_pass_gap_projection_20260612.md](docs/1168_platform_completion_gate_after_gate_pass_gap_projection_20260612.md)|Gate 통과 Gap Projection 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1169_gate_pass_gap_projection_implementation_report_20260612.md](docs/1169_gate_pass_gap_projection_implementation_report_20260612.md)|Gate 통과 Gap Projection 구현 및 운영 우선순위 보고|
|[docs/1170_gate_pass_minimum_batch_queue_20260612.md](docs/1170_gate_pass_minimum_batch_queue_20260612.md)|전체 실행보드에서 100% Gate 통과에 필요한 335개 최소 배치 큐 산정|
|[docs/1171_platform_qa_suite_after_minimum_batch_queue_20260612.md](docs/1171_platform_qa_suite_after_minimum_batch_queue_20260612.md)|최소 배치 큐 API/UI 반영 후 플랫폼 QA 22/22 PASS 보고|
|[docs/1172_platform_completion_gate_after_minimum_batch_queue_20260612.md](docs/1172_platform_completion_gate_after_minimum_batch_queue_20260612.md)|최소 배치 큐 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1173_gate_pass_minimum_batch_queue_implementation_report_20260612.md](docs/1173_gate_pass_minimum_batch_queue_implementation_report_20260612.md)|Gate 통과 최소 배치 큐 구현 및 G11/G12 추가 workpack 필요성 보고|
|[docs/542_opinet_handoff_delta_audit_20260610.md](docs/542_opinet_handoff_delta_audit_20260610.md)|OPINET handoff ZIP 재주입 효과 감사. 새 PNU/좌표 보강 가능 건수 0건 판정|
|[docs/545_platform_completion_gate_after_opinet_delta_audit_20260610.md](docs/545_platform_completion_gate_after_opinet_delta_audit_20260610.md)|OPINET 감사 이후 G0~G15 100% 완료 게이트 최신 보고|
|[docs/548_platform_action_queue_after_opinet_delta_audit_20260610.md](docs/548_platform_action_queue_after_opinet_delta_audit_20260610.md)|G3~G12 외부 결과파일 주입 실행 큐 최신 보고|
|[docs/550_external_intake_status_after_opinet_delta_audit_20260610.md](docs/550_external_intake_status_after_opinet_delta_audit_20260610.md)|외부 결과 CSV 인젝션 가능 여부 최신 점검|
|[docs/551_opinet_delta_audit_and_gate_refresh_implementation_report_20260610.md](docs/551_opinet_delta_audit_and_gate_refresh_implementation_report_20260610.md)|OPINET 감사, QA, 완료 게이트, handoff 갱신 최종 구현 보고|
|[docs/565_g3_geocode_batch_manifest_implementation_report_20260610.md](docs/565_g3_geocode_batch_manifest_implementation_report_20260610.md)|G3 좌표 누락 6,110건을 표준 시도/유형별 22개 배치로 분리한 구현 보고|
|[docs/575_g4_land_area_batch_manifest_implementation_report_20260610.md](docs/575_g4_land_area_batch_manifest_implementation_report_20260610.md)|G4 토지 지번·면적 누락 3,587건을 상태/시도/유형별 96개 배치로 분리한 구현 보고|
|[docs/576_building_batch_manifest_20260610.md](docs/576_building_batch_manifest_20260610.md)|G5 건물정보 누락 3,368건을 건물 미연결 중심 66개 배치로 분리한 manifest 보고|
|[docs/577_storage_batch_manifest_20260610.md](docs/577_storage_batch_manifest_20260610.md)|G6 저장량 후보 12,303행, 8,567개 시설을 물질/기관/지역별 96개 배치로 분리한 manifest 보고|
|[docs/582_platform_qa_suite_after_building_storage_batches_20260610.md](docs/582_platform_qa_suite_after_building_storage_batches_20260610.md)|G5/G6 배치팩 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/583_platform_completion_gate_after_building_storage_batch_qa_20260610.md](docs/583_platform_completion_gate_after_building_storage_batch_qa_20260610.md)|G5/G6 배치팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/584_platform_action_queue_after_building_storage_batch_qa_20260610.md](docs/584_platform_action_queue_after_building_storage_batch_qa_20260610.md)|G5/G6 보조 배치팩 경로가 연결된 최신 실행 큐|
|[docs/587_g5_g6_building_storage_batch_manifest_implementation_report_20260610.md](docs/587_g5_g6_building_storage_batch_manifest_implementation_report_20260610.md)|G5/G6 건물·저장량 배치 Manifest 구현 종합 보고|
|[docs/588_auction_history_batch_manifest_20260610.md](docs/588_auction_history_batch_manifest_20260610.md)|G7 과거 경매 이력 검색 65,733행을 provider/시설유형/시도별 291개 배치로 분리한 manifest 보고|
|[docs/589_current_auction_batch_manifest_20260610.md](docs/589_current_auction_batch_manifest_20260610.md)|G8 현재 경매 진행 여부 검색 34,272행을 provider/시설유형/시도별 292개 배치로 분리한 manifest 보고|
|[docs/591_platform_qa_suite_after_auction_batches_20260610.md](docs/591_platform_qa_suite_after_auction_batches_20260610.md)|G7/G8 경매 배치팩 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/592_platform_completion_gate_after_auction_batch_qa_20260610.md](docs/592_platform_completion_gate_after_auction_batch_qa_20260610.md)|G7/G8 배치팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/593_platform_action_queue_after_auction_batch_qa_20260610.md](docs/593_platform_action_queue_after_auction_batch_qa_20260610.md)|G7/G8 배치 Manifest와 사건번호 보정팩이 연결된 최신 실행 큐|
|[docs/596_g7_g8_auction_batch_manifest_implementation_report_20260610.md](docs/596_g7_g8_auction_batch_manifest_implementation_report_20260610.md)|G7/G8 경매 배치 Manifest 구현 종합 보고|
|[docs/597_card_revenue_batch_manifest_20260610.md](docs/597_card_revenue_batch_manifest_20260610.md)|G9 카드결제 12개월 입력 102,816행을 876개 배치로 분리한 manifest 보고|
|[docs/598_financial_revenue_batch_manifest_20260610.md](docs/598_financial_revenue_batch_manifest_20260610.md)|G10 재무자료 2025년 입력 8,568행을 73개 배치로 분리한 manifest 보고|
|[docs/600_platform_qa_suite_after_revenue_batches_20260610.md](docs/600_platform_qa_suite_after_revenue_batches_20260610.md)|G9/G10 매출·재무 배치팩 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/601_platform_completion_gate_after_revenue_batch_qa_20260610.md](docs/601_platform_completion_gate_after_revenue_batch_qa_20260610.md)|G9/G10 배치팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/602_platform_action_queue_after_revenue_batch_qa_20260610.md](docs/602_platform_action_queue_after_revenue_batch_qa_20260610.md)|G9/G10 카드·재무 배치 Manifest가 연결된 최신 실행 큐|
|[docs/604_external_intake_status_after_revenue_batch_qa_20260610.md](docs/604_external_intake_status_after_revenue_batch_qa_20260610.md)|G9/G10 배치팩 반영 후 외부 intake 상태 보고|
|[docs/605_g9_g10_revenue_batch_manifest_implementation_report_20260610.md](docs/605_g9_g10_revenue_batch_manifest_implementation_report_20260610.md)|G9/G10 카드·재무 배치 Manifest 구현 종합 보고|
|[docs/607_planning_batch_manifest_20260610.md](docs/607_planning_batch_manifest_20260610.md)|G11 도시계획·도로 영향 미확인 3,816건을 103개 배치로 분리한 manifest 보고|
|[docs/609_platform_qa_suite_after_planning_batch_20260610.md](docs/609_platform_qa_suite_after_planning_batch_20260610.md)|G11/G12 배치팩 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/610_platform_completion_gate_after_planning_batch_qa_20260610.md](docs/610_platform_completion_gate_after_planning_batch_qa_20260610.md)|G11/G12 배치팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/612_external_intake_status_after_planning_batch_qa_20260610.md](docs/612_external_intake_status_after_planning_batch_qa_20260610.md)|G11/G12 배치팩 반영 후 외부 intake 상태 보고|
|[docs/613_g11_g12_planning_prediction_batch_manifest_implementation_report_20260610.md](docs/613_g11_g12_planning_prediction_batch_manifest_implementation_report_20260610.md)|G11/G12 도시계획·예측 배치 Manifest 구현 종합 보고|
|[docs/614_completion_execution_board_20260610.md](docs/614_completion_execution_board_20260610.md)|G3~G12 배치 manifest 1,916개를 하나의 100% 통합 실행 우선순위 보드로 정리한 보고|
|[docs/615_platform_qa_suite_after_execution_board_20260610.md](docs/615_platform_qa_suite_after_execution_board_20260610.md)|통합 실행 보드 API/UI/DB 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/616_platform_completion_gate_after_execution_board_qa_20260610.md](docs/616_platform_completion_gate_after_execution_board_qa_20260610.md)|통합 실행 보드 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/617_external_workpack_manifest_after_execution_board_qa_20260610.md](docs/617_external_workpack_manifest_after_execution_board_qa_20260610.md)|통합 실행 보드 반영 후 외부 workpack manifest 갱신 보고|
|[docs/618_external_intake_status_after_execution_board_qa_20260610.md](docs/618_external_intake_status_after_execution_board_qa_20260610.md)|통합 실행 보드 반영 후 결과파일 intake 상태 갱신 보고|
|[docs/619_completion_execution_board_implementation_report_20260610.md](docs/619_completion_execution_board_implementation_report_20260610.md)|100% 통합 실행 보드 DB/API/UI/QA 구현 보고|
|[docs/620_completion_execution_ledger_20260610.md](docs/620_completion_execution_ledger_20260610.md)|G3~G12 1,916개 배치 결과양식 입력상태를 점검한 100% 실행 Ledger 보고|
|[docs/621_platform_qa_suite_after_execution_ledger_20260610.md](docs/621_platform_qa_suite_after_execution_ledger_20260610.md)|실행 Ledger API/UI 반영 후 읽기 전용 G15 QA suite 11/11 PASS 보고|
|[docs/622_completion_execution_ledger_implementation_report_20260610.md](docs/622_completion_execution_ledger_implementation_report_20260610.md)|100% 실행 Ledger DB/API/UI 구현 및 G4 dry-run 오판 정정 보고|
|[docs/623_platform_completion_gate_after_execution_ledger_qa_20260610.md](docs/623_platform_completion_gate_after_execution_ledger_qa_20260610.md)|실행 Ledger 반영 후 g21 QA DB 기록 기준 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/624_completion_input_gap_report_20260610.md](docs/624_completion_input_gap_report_20260610.md)|G3~G12 strict dry-run 진입에 필요한 핵심 입력 컬럼과 249,141행 누락 Gap 보고|
|[docs/625_platform_qa_suite_after_input_gap_20260610.md](docs/625_platform_qa_suite_after_input_gap_20260610.md)|입력 Gap 빌더 포함 후 읽기 전용 G15 QA suite 11/11 PASS 보고|
|[docs/626_platform_qa_suite_after_input_gap_api_ui_20260610.md](docs/626_platform_qa_suite_after_input_gap_api_ui_20260610.md)|입력 Gap API/UI 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/627_platform_completion_gate_after_input_gap_api_ui_qa_20260610.md](docs/627_platform_completion_gate_after_input_gap_api_ui_qa_20260610.md)|입력 Gap API/UI 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 성공 보고|
|[docs/628_platform_qa_suite_after_input_gap_table_20260610.md](docs/628_platform_qa_suite_after_input_gap_table_20260610.md)|입력 Gap DB 테이블을 G15 핵심 테이블로 승격한 뒤 QA suite 11/11 PASS 보고|
|[docs/629_platform_completion_gate_after_input_gap_table_qa_20260610.md](docs/629_platform_completion_gate_after_input_gap_table_qa_20260610.md)|입력 Gap DB 테이블과 g23 QA 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최종 보고|
|[docs/630_completion_input_gap_api_ui_table_implementation_report_20260610.md](docs/630_completion_input_gap_api_ui_table_implementation_report_20260610.md)|100% 입력 Gap DB/API/UI 구현 및 249,141행 누락 입력 기준 확정 보고|
|[docs/631_external_provider_session_plan_20260610.md](docs/631_external_provider_session_plan_20260610.md)|인포케어·옥션원 등 외부 Provider 세션/검색/결과입력 계획을 비밀번호 미저장 원칙으로 정리한 보고|
|[docs/632_platform_qa_suite_after_provider_session_plan_20260610.md](docs/632_platform_qa_suite_after_provider_session_plan_20260610.md)|외부 Provider 세션 계획 API/UI 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/633_platform_completion_gate_after_provider_session_plan_qa_20260610.md](docs/633_platform_completion_gate_after_provider_session_plan_qa_20260610.md)|외부 Provider 세션 계획 반영 후 read-only 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/634_external_provider_session_plan_implementation_report_20260610.md](docs/634_external_provider_session_plan_implementation_report_20260610.md)|외부 Provider 세션 계획 DB/API/UI/QA 구현과 writer lock 보류사항 보고|
|[docs/635_platform_qa_suite_after_provider_session_table_20260610.md](docs/635_platform_qa_suite_after_provider_session_table_20260610.md)|외부 Provider 세션 계획 DB 테이블 고정 후 G15 QA suite 11/11 PASS 보고|
|[docs/636_platform_completion_gate_after_provider_session_table_qa_20260610.md](docs/636_platform_completion_gate_after_provider_session_table_qa_20260610.md)|외부 Provider 세션 계획 DB 테이블과 g24 QA 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/637_auction_provider_workbench_20260610.md](docs/637_auction_provider_workbench_20260610.md)|G7/G8 경매 Provider 검색 583개 배치와 100,005개 검색행 작업대 보고|
|[docs/638_platform_qa_suite_after_auction_provider_workbench_20260610.md](docs/638_platform_qa_suite_after_auction_provider_workbench_20260610.md)|경매 Provider 작업대 API/UI/DB 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/639_platform_completion_gate_after_auction_provider_workbench_qa_20260610.md](docs/639_platform_completion_gate_after_auction_provider_workbench_qa_20260610.md)|경매 Provider 작업대 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/640_auction_provider_workbench_implementation_report_20260610.md](docs/640_auction_provider_workbench_implementation_report_20260610.md)|경매 Provider 작업대 DB/API/UI/QA 구현 종합 보고|
|[docs/641_auction_provider_intake_preflight_20260610.md](docs/641_auction_provider_intake_preflight_20260610.md)|G7/G8 경매 결과양식 100,005행 strict dry-run preflight 보고|
|[docs/642_auction_provider_intake_preflight_implementation_report_20260610.md](docs/642_auction_provider_intake_preflight_implementation_report_20260610.md)|경매 결과 Preflight script/API/UI/QA 구현 및 DB 적재 완료 보고|
|[docs/643_platform_qa_suite_after_auction_preflight_20260610.md](docs/643_platform_qa_suite_after_auction_preflight_20260610.md)|경매 결과 Preflight API/UI 반영 후 g25 G15 QA suite 11/11 PASS 보고|
|[docs/644_platform_completion_gate_after_auction_preflight_qa_20260610.md](docs/644_platform_completion_gate_after_auction_preflight_qa_20260610.md)|경매 결과 Preflight 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/645_coordinate_internal_enrich_dryrun_20260610.md](docs/645_coordinate_internal_enrich_dryrun_20260610.md)|내부 동일주소 좌표 보강 dry-run 결과: 적용 후보 0건|
|[docs/646_pnu_internal_enrich_dryrun_20260610.md](docs/646_pnu_internal_enrich_dryrun_20260610.md)|내부 동일주소 PNU 보강 dry-run 결과: 적용 후보 0건|
|[docs/648_storage_source_audit_after_auction_preflight_20260610.md](docs/648_storage_source_audit_after_auction_preflight_20260610.md)|저장량·설비 원천 후보 164개 컬럼 감사 보고|
|[docs/649_internal_uplift_opportunity_audit_20260610.md](docs/649_internal_uplift_opportunity_audit_20260610.md)|내부 원천만으로 즉시 coverage 상향 가능한 후보가 없음을 확정한 감사 보고|
|[docs/650_platform_qa_suite_after_internal_uplift_audit_20260610.md](docs/650_platform_qa_suite_after_internal_uplift_audit_20260610.md)|내부 원천 상향 가능성 감사 후 읽기 전용 G15 QA suite 11/11 PASS 보고|
|[docs/651_platform_completion_gate_after_internal_uplift_audit_20260610.md](docs/651_platform_completion_gate_after_internal_uplift_audit_20260610.md)|내부 원천 상향 가능성 감사 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/652_geocode_intake_preflight_20260610.md](docs/652_geocode_intake_preflight_20260610.md)|G3 좌표 결과양식 22개 배치, 6,110행 strict dry-run preflight 보고|
|[docs/655_platform_qa_suite_after_geocode_preflight_api_20260610.md](docs/655_platform_qa_suite_after_geocode_preflight_api_20260610.md)|좌표 결과 Preflight API/UI 반영 후 G15 QA suite 11/11 PASS 보고|
|[docs/656_geocode_intake_preflight_implementation_report_20260610.md](docs/656_geocode_intake_preflight_implementation_report_20260610.md)|G3 좌표 결과 Preflight script/API/UI 구현 및 DuckDB writer lock 보류사항 보고|
|[docs/659_platform_completion_gate_after_auth_lock_hardening_20260610.md](docs/659_platform_completion_gate_after_auth_lock_hardening_20260610.md)|인증 lock-resilience 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/660_platform_qa_suite_after_auth_lock_hardening_g26_20260610.md](docs/660_platform_qa_suite_after_auth_lock_hardening_g26_20260610.md)|잘못된 토큰 500 방지 검사 포함 G15 QA suite g26 12/12 PASS 보고|
|[docs/661_auth_lock_resilience_implementation_report_20260610.md](docs/661_auth_lock_resilience_implementation_report_20260610.md)|DuckDB writer lock 중 관리자 인증 500 방지 구현 보고|
|[docs/662_geocode_intake_preflight_lock_resilient_20260610.md](docs/662_geocode_intake_preflight_lock_resilient_20260610.md)|G3 좌표 결과 Preflight 22개 배치 DB 적재 성공 보고|
|[docs/664_platform_completion_gate_after_geocode_preflight_db_20260610.md](docs/664_platform_completion_gate_after_geocode_preflight_db_20260610.md)|G3 좌표 Preflight DB 고정 후 completion gate DB snapshot 6 PASS / 10 FAIL 보고|
|[docs/667_platform_qa_suite_after_geocode_preflight_db_target_20260610.md](docs/667_platform_qa_suite_after_geocode_preflight_db_target_20260610.md)|운영 DB 명시 기준 G15 QA suite 12/12 PASS 보고|
|[docs/668_geocode_preflight_db_and_completion_lock_resilience_report_20260610.md](docs/668_geocode_preflight_db_and_completion_lock_resilience_report_20260610.md)|G3 좌표 Preflight DB 고정 및 completion gate lock-resilience 구현 보고|
|[docs/669_external_intake_status_after_geocode_preflight_db_20260610.md](docs/669_external_intake_status_after_geocode_preflight_db_20260610.md)|G4/G5 포함 외부 결과파일 intake를 strict importer 기준으로 재점검한 보고|
|[docs/670_platform_qa_suite_external_intake_strict_report_only_20260610.md](docs/670_platform_qa_suite_external_intake_strict_report_only_20260610.md)|G4/G5 strict intake 보강 후 읽기 전용 G15 QA suite 12/12 PASS 보고|
|[docs/671_platform_completion_gate_after_external_intake_strict_report_only_20260610.md](docs/671_platform_completion_gate_after_external_intake_strict_report_only_20260610.md)|G4/G5 strict intake 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/672_external_intake_strict_land_building_lock_resilience_report_20260610.md](docs/672_external_intake_strict_land_building_lock_resilience_report_20260610.md)|G4/G5 외부 인젝션 strict 판정 및 DuckDB lock-resilience 구현 보고|
|[docs/673_platform_qa_suite_lock_resilient_g27_20260610.md](docs/673_platform_qa_suite_lock_resilient_g27_20260610.md)|DuckDB writer lock 중에도 G15 QA suite g27 12/12 PASS를 산출한 보고|
|[docs/674_platform_completion_gate_after_qa_lock_resilience_g27_20260610.md](docs/674_platform_completion_gate_after_qa_lock_resilience_g27_20260610.md)|QA g27 lock-resilience 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/675_qa_suite_lock_resilience_g27_implementation_report_20260610.md](docs/675_qa_suite_lock_resilience_g27_implementation_report_20260610.md)|G15 QA suite DB write best-effort 및 strict 옵션 구현 보고|
|[docs/676_platform_qa_suite_write_retry_g28_20260610.md](docs/676_platform_qa_suite_write_retry_g28_20260610.md)|G15 QA suite g28 DB write retry 검증 보고|
|[docs/677_platform_completion_gate_write_retry_g28_20260610.md](docs/677_platform_completion_gate_write_retry_g28_20260610.md)|Completion gate DB write retry 검증 후 6 PASS / 10 FAIL 보고|
|[docs/678_external_intake_status_write_retry_20260610.md](docs/678_external_intake_status_write_retry_20260610.md)|외부 결과파일 intake DB write retry 검증 보고|
|[docs/679_duckdb_write_retry_lock_resilience_implementation_report_20260610.md](docs/679_duckdb_write_retry_lock_resilience_implementation_report_20260610.md)|DuckDB write retry 공통 유틸 및 3개 운영 스크립트 적용 보고|
|[docs/680_duckdb_read_snapshot_report_20260610.md](docs/680_duckdb_read_snapshot_report_20260610.md)|단순 DuckDB 파일 스냅샷 손상 확인 및 검증 보고|
|[docs/682_duckdb_table_snapshot_smoke_report_20260610.md](docs/682_duckdb_table_snapshot_smoke_report_20260610.md)|DuckDB table snapshot smoke 성공 보고|
|[docs/683_platform_qa_suite_snapshot_tools_g29_20260610.md](docs/683_platform_qa_suite_snapshot_tools_g29_20260610.md)|snapshot 도구 포함 G15 QA suite g29 12/12 PASS 보고|
|[docs/684_platform_completion_gate_after_snapshot_tools_g29_20260610.md](docs/684_platform_completion_gate_after_snapshot_tools_g29_20260610.md)|snapshot 도구 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/685_duckdb_snapshot_tools_implementation_report_20260610.md](docs/685_duckdb_snapshot_tools_implementation_report_20260610.md)|DuckDB read/table snapshot 도구 구현 및 손상 스냅샷 정리 보고|
|[docs/686_vworld_snapshot_batch_command_report_20260610.md](docs/686_vworld_snapshot_batch_command_report_20260610.md)|full snapshot 부재 시 VWorld snapshot batch 실행을 막는 command guard 보고|
|[docs/687_platform_qa_suite_vworld_snapshot_command_g30_20260610.md](docs/687_platform_qa_suite_vworld_snapshot_command_g30_20260610.md)|VWorld snapshot command guard 포함 G15 QA suite g30 12/12 PASS 보고|
|[docs/688_platform_completion_gate_after_vworld_snapshot_command_g30_20260610.md](docs/688_platform_completion_gate_after_vworld_snapshot_command_g30_20260610.md)|VWorld snapshot command guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/689_vworld_snapshot_command_guard_implementation_report_20260610.md](docs/689_vworld_snapshot_command_guard_implementation_report_20260610.md)|VWorld snapshot batch command guard 구현 보고|
|[docs/690_vworld_snapshot_safe_runner_report_20260610.md](docs/690_vworld_snapshot_safe_runner_report_20260610.md)|full snapshot 부재 시 VWorld 실행을 중단하는 safe runner 보고|
|[docs/691_platform_qa_suite_snapshot_safe_runner_g31_20260610.md](docs/691_platform_qa_suite_snapshot_safe_runner_g31_20260610.md)|VWorld snapshot safe runner 포함 G15 QA suite g31 12/12 PASS 보고|
|[docs/692_platform_completion_gate_after_snapshot_safe_runner_g31_20260610.md](docs/692_platform_completion_gate_after_snapshot_safe_runner_g31_20260610.md)|VWorld snapshot safe runner 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/693_vworld_snapshot_safe_runner_implementation_report_20260610.md](docs/693_vworld_snapshot_safe_runner_implementation_report_20260610.md)|VWorld snapshot safe runner 구현 보고|
|[docs/694_external_intake_status_post_lock_retry_20260610.md](docs/694_external_intake_status_post_lock_retry_20260610.md)|G4/G5 strict 외부 intake 재시도 및 writer lock 잔존 보고|
|[docs/697_platform_qa_suite_after_healthz_recovery_g31_20260610.md](docs/697_platform_qa_suite_after_healthz_recovery_g31_20260610.md)|healthz 복구 후 G15 QA suite g31 12/12 PASS 보고|
|[docs/698_platform_completion_gate_after_healthz_recovery_20260610.md](docs/698_platform_completion_gate_after_healthz_recovery_20260610.md)|healthz 복구 후 100% 완료 게이트 6 PASS / 10 FAIL 최신 보고|
|[docs/699_healthz_recovery_and_gate_status_report_20260610.md](docs/699_healthz_recovery_and_gate_status_report_20260610.md)|healthz 복구, QA 정상화, 남은 100% 차단 게이트 종합 보고|
|[docs/700_next_100pct_gap_closure_spec_wbs_claude_review_20260610.md](docs/700_next_100pct_gap_closure_spec_wbs_claude_review_20260610.md)|100% 무결점 도달 기준 다음 개발 명세서, WBS, Claude 관점 비판 반영 보고|
|[docs/701_g3_g5_gap_table_report_20260610.md](docs/701_g3_g5_gap_table_report_20260610.md)|G3~G5 위치·토지·건축물 통합 gap table 산정 보고|
|[docs/702_platform_qa_suite_after_g3_g5_gap_g32_20260610.md](docs/702_platform_qa_suite_after_g3_g5_gap_g32_20260610.md)|G3~G5 gap table/API/UI 반영 후 G15 QA suite g32 12/12 PASS 보고|
|[docs/703_platform_completion_gate_after_g3_g5_gap_20260610.md](docs/703_platform_completion_gate_after_g3_g5_gap_20260610.md)|G3~G5 gap table 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/704_g3_g5_gap_table_implementation_report_20260610.md](docs/704_g3_g5_gap_table_implementation_report_20260610.md)|G3~G5 통합 gap table DB/API/UI/QA 구현 종합 보고|
|[docs/705_g3_g5_workpack_index_report_20260610.md](docs/705_g3_g5_workpack_index_report_20260610.md)|G3~G5 좌표·토지·건물 보강 작업팩 184개 통합 index 보고|
|[docs/706_platform_qa_suite_after_g3_g5_workpack_g33_20260610.md](docs/706_platform_qa_suite_after_g3_g5_workpack_g33_20260610.md)|G3~G5 workpack API/UI 반영 후 G15 QA suite g33 12/12 PASS 보고|
|[docs/707_platform_completion_gate_after_g3_g5_workpack_20260610.md](docs/707_platform_completion_gate_after_g3_g5_workpack_20260610.md)|G3~G5 workpack 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/708_g3_g5_workpack_index_implementation_report_20260610.md](docs/708_g3_g5_workpack_index_implementation_report_20260610.md)|G3~G5 통합 workpack index DB/API/UI/QA 구현 종합 보고|
|[docs/709_g3_g5_workpack_index_db_persist_report_20260610.md](docs/709_g3_g5_workpack_index_db_persist_report_20260610.md)|G3~G5 workpack index DB table write 성공 및 최신 외장하드 CSV 재생성 보고|
|[docs/710_platform_qa_suite_after_g3_g5_download_g34_20260610.md](docs/710_platform_qa_suite_after_g3_g5_download_g34_20260610.md)|G3~G5 workpack 다운로드 API/UI 반영 후 G15 QA suite g34 12/12 PASS 보고|
|[docs/711_platform_completion_gate_after_g3_g5_download_20260610.md](docs/711_platform_completion_gate_after_g3_g5_download_20260610.md)|G3~G5 다운로드 기능 반영 후 100% 완료 게이트 6 PASS / 10 FAIL DB snapshot 보고|
|[docs/712_g3_g5_workpack_download_and_db_persist_report_20260610.md](docs/712_g3_g5_workpack_download_and_db_persist_report_20260610.md)|G3~G5 workpack DB 고정, 다운로드 API/UI, QA/Completion 검증 종합 보고|
|[docs/713_coordinate_source_candidates_recheck_20260610.md](docs/713_coordinate_source_candidates_recheck_20260610.md)|G3 좌표 내부 원천 재점검 보고|
|[docs/714_g3_geocode_api_batch_runner_report_20260610.md](docs/714_g3_geocode_api_batch_runner_report_20260610.md)|G3 좌표 API batch runner dry-check 및 API key 미설정 차단 보고|
|[docs/715_g3_geocode_secure_runner_drycheck_20260610.md](docs/715_g3_geocode_secure_runner_drycheck_20260610.md)|PowerShell secure runner dry-check 보고|
|[docs/716_platform_qa_suite_after_g3_secure_runner_g35_20260610.md](docs/716_platform_qa_suite_after_g3_secure_runner_g35_20260610.md)|G3 secure runner 반영 후 G15 QA suite g35 12/12 PASS 보고|
|[docs/717_platform_completion_gate_after_g3_secure_runner_20260610.md](docs/717_platform_completion_gate_after_g3_secure_runner_20260610.md)|G3 secure runner 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/718_g3_secure_geocode_runner_implementation_report_20260610.md](docs/718_g3_secure_geocode_runner_implementation_report_20260610.md)|G3 좌표 API key-safe 실행 runner 구현 종합 보고|
|[docs/719_storage_internal_raw_extraction_report_20260611.md](docs/719_storage_internal_raw_extraction_report_20260611.md)|KOGAS LCNG 원문 주요설비에서 실제 저장탱크·저장용기 숫자만 추출한 보고|
|[docs/720_storage_uplift_candidate_after_raw_extraction_20260611.md](docs/720_storage_uplift_candidate_after_raw_extraction_20260611.md)|저장량·설비 후보 재생성 및 원문 저장량 후보 API 연결 보고|
|[docs/722_platform_qa_suite_after_storage_internal_extraction_g36_20260611.md](docs/722_platform_qa_suite_after_storage_internal_extraction_g36_20260611.md)|G6 내부 원문 추출 반영 후 G15 QA suite g36 12/12 PASS 보고|
|[docs/723_platform_completion_gate_after_storage_internal_extraction_qa_20260611.md](docs/723_platform_completion_gate_after_storage_internal_extraction_qa_20260611.md)|G6 내부 원문 추출 및 QA 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/724_storage_internal_raw_extraction_implementation_report_20260611.md](docs/724_storage_internal_raw_extraction_implementation_report_20260611.md)|G6 저장량 내부 원문 추출, 오인식 수정, API 검증 구현 종합 보고|
|[docs/725_auction_case_quality_refresh_20260611.md](docs/725_auction_case_quality_refresh_20260611.md)|경매 117행 사건번호 품질 재판정 및 provider 관리번호 49시설 확인 보고|
|[docs/726_auction_case_resolution_queue_refresh_20260611.md](docs/726_auction_case_resolution_queue_refresh_20260611.md)|옥션원 관리번호 76행을 법원 사건번호로 역조회하기 위한 보정 큐와 결과양식 보고|
|[docs/727_current_auction_reference_candidate_report_20260611.md](docs/727_current_auction_reference_candidate_report_20260611.md)|현재/예정 경매 provider 관리번호 후보 1건 분리 보고|
|[docs/728_platform_qa_suite_after_auction_reference_candidates_g37_20260611.md](docs/728_platform_qa_suite_after_auction_reference_candidates_g37_20260611.md)|경매 보정 후보 반영 후 G15 QA suite g37 12/12 PASS 보고|
|[docs/729_platform_completion_gate_after_auction_reference_candidates_qa_20260611.md](docs/729_platform_completion_gate_after_auction_reference_candidates_qa_20260611.md)|경매 보정 후보 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/730_auction_reference_candidate_implementation_report_20260611.md](docs/730_auction_reference_candidate_implementation_report_20260611.md)|G7/G8 경매 사건번호 보정 큐, 현재경매 후보, QA 반영 구현 종합 보고|
|[docs/731_energy_site_index_application_after_raw_storage_current_ref_20260611.md](docs/731_energy_site_index_application_after_raw_storage_current_ref_20260611.md)|저장량 원문 후보와 현재경매 관리번호 후보 테이블 인덱스 적용 보고|
|[docs/732_platform_qa_suite_after_raw_storage_current_ref_indexes_g38_20260611.md](docs/732_platform_qa_suite_after_raw_storage_current_ref_indexes_g38_20260611.md)|신규 후보 테이블 인덱스 반영 후 G15 QA suite g38 12/12 PASS 보고|
|[docs/733_platform_completion_gate_after_raw_storage_current_ref_indexes_20260611.md](docs/733_platform_completion_gate_after_raw_storage_current_ref_indexes_20260611.md)|신규 후보 테이블 인덱스 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/734_raw_storage_current_ref_index_implementation_report_20260611.md](docs/734_raw_storage_current_ref_index_implementation_report_20260611.md)|저장량 원문 후보·현재경매 후보 인덱싱 및 운영 검증 구현 보고|
|[docs/735_platform_qa_suite_after_current_auction_reference_api_ui_g39_20260611.md](docs/735_platform_qa_suite_after_current_auction_reference_api_ui_g39_20260611.md)|현재/예정 경매 후보 API/UI 반영 후 G15 QA suite g39 12/12 PASS 보고|
|[docs/736_platform_completion_gate_after_current_auction_reference_api_ui_20260611.md](docs/736_platform_completion_gate_after_current_auction_reference_api_ui_20260611.md)|현재/예정 경매 후보 API/UI 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/737_current_auction_reference_api_ui_implementation_report_20260611.md](docs/737_current_auction_reference_api_ui_implementation_report_20260611.md)|현재/예정 경매 후보 API·UI 노출 및 역조회 대기상태 구현 보고|
|[docs/738_current_auction_reference_resolution_pack_report_20260611.md](docs/738_current_auction_reference_resolution_pack_report_20260611.md)|현재/예정 경매 후보 1건을 옥션원 관리번호 역조회 작업팩으로 export한 보고|
|[docs/739_current_auction_reference_blank_template_import_dryrun_20260611.md](docs/739_current_auction_reference_blank_template_import_dryrun_20260611.md)|빈 현재경매 역조회 결과양식이 확정 import되지 않고 반려되는 dry-run 보고|
|[docs/740_platform_qa_suite_after_current_auction_reference_resolution_pack_g40_20260611.md](docs/740_platform_qa_suite_after_current_auction_reference_resolution_pack_g40_20260611.md)|현재경매 후보 역조회 작업팩 반영 후 G15 QA suite g40 12/12 PASS 보고|
|[docs/741_platform_completion_gate_after_current_auction_reference_resolution_pack_20260611.md](docs/741_platform_completion_gate_after_current_auction_reference_resolution_pack_20260611.md)|현재경매 후보 역조회 작업팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/742_current_auction_reference_resolution_pack_implementation_report_20260611.md](docs/742_current_auction_reference_resolution_pack_implementation_report_20260611.md)|현재/예정 경매 후보 역조회 작업팩 구현 및 안전장치 검증 보고|
|[docs/743_g3_g6_internal_uplift_opportunity_audit_20260611.md](docs/743_g3_g6_internal_uplift_opportunity_audit_20260611.md)|G3~G6 내부 자동상향 가능성 0건 및 외부 원천 필요성 감사 보고|
|[docs/744_platform_qa_suite_after_internal_uplift_audit_g41_20260611.md](docs/744_platform_qa_suite_after_internal_uplift_audit_g41_20260611.md)|G3~G6 내부 자동상향 감사 반영 후 G15 QA suite g41 12/12 PASS 보고|
|[docs/745_platform_completion_gate_after_internal_uplift_audit_20260611.md](docs/745_platform_completion_gate_after_internal_uplift_audit_20260611.md)|G3~G6 내부 자동상향 감사 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/746_g3_g6_internal_uplift_audit_implementation_report_20260611.md](docs/746_g3_g6_internal_uplift_audit_implementation_report_20260611.md)|G3~G6 내부 자동상향 감사 구현 및 다음 외부 원천 작업 기준 보고|
|[docs/747_external_impact_priority_report_20260611.md](docs/747_external_impact_priority_report_20260611.md)|G3~G12 외부 원천 투입 영향도 우선순위 10개 게이트 DB 적재 보고|
|[docs/748_platform_qa_suite_after_external_impact_priority_g42_20260611.md](docs/748_platform_qa_suite_after_external_impact_priority_g42_20260611.md)|외부투입 영향도 API/UI 반영 후 G15 QA suite g42 12/12 PASS 보고|
|[docs/749_platform_completion_gate_after_external_impact_priority_20260611.md](docs/749_platform_completion_gate_after_external_impact_priority_20260611.md)|외부투입 영향도 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/750_external_impact_priority_implementation_report_20260611.md](docs/750_external_impact_priority_implementation_report_20260611.md)|외부투입 영향도 DB/API/UI/QA 구현 종합 보고|
|[docs/751_g3_top_batch_blank_template_dryrun_20260611.md](docs/751_g3_top_batch_blank_template_dryrun_20260611.md)|G3 최우선 좌표 결과양식 500행 빈 양식 strict dry-run 반려 보고|
|[docs/752_g3_geocode_api_batch_readiness_20260611.md](docs/752_g3_geocode_api_batch_readiness_20260611.md)|G3 좌표 API batch readiness 및 API key 미설정 차단 보고|
|[docs/753_g3_geocode_blocker_and_readonly_dryrun_report_20260611.md](docs/753_g3_geocode_blocker_and_readonly_dryrun_report_20260611.md)|G3 좌표 보강 실행 차단 원인과 read-only dry-run 전환 보고|
|[docs/754_platform_qa_suite_after_g3_readonly_dryrun_g43_20260611.md](docs/754_platform_qa_suite_after_g3_readonly_dryrun_g43_20260611.md)|G3 read-only dry-run 안전화 후 G15 QA suite g43 12/12 PASS 보고|
|[docs/755_platform_completion_gate_after_g3_readonly_dryrun_20260611.md](docs/755_platform_completion_gate_after_g3_readonly_dryrun_20260611.md)|G3 read-only dry-run 안전화 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/756_g3_readonly_dryrun_implementation_report_20260611.md](docs/756_g3_readonly_dryrun_implementation_report_20260611.md)|G3 좌표 import dry-run 안전화 구현 보고|
|[docs/757_vworld_building_unit_extract_progress_20260611.md](docs/757_vworld_building_unit_extract_progress_20260611.md)|VWorld 건물단위 추출 진행률 read-only 감사 보고|
|[docs/758_vworld_building_unit_extract_progress_implementation_report_20260611.md](docs/758_vworld_building_unit_extract_progress_implementation_report_20260611.md)|VWorld 건물단위 추출 진행률 감사 구현 보고|
|[docs/759_platform_qa_suite_after_vworld_extract_audit_g44_20260611.md](docs/759_platform_qa_suite_after_vworld_extract_audit_g44_20260611.md)|VWorld 건물단위 추출 감사 반영 후 G15 QA suite g44 12/12 PASS 보고|
|[docs/760_platform_completion_gate_after_vworld_extract_audit_20260611.md](docs/760_platform_completion_gate_after_vworld_extract_audit_20260611.md)|VWorld 건물단위 추출 감사 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/761_g11_bldrg_zoning_recheck_dryrun_20260611.md](docs/761_g11_bldrg_zoning_recheck_dryrun_20260611.md)|건축HUB bldrg_zoning 전체 조인 재점검 dry-run 보고|
|[docs/761_g11_planning_internal_uplift_audit_20260611.md](docs/761_g11_planning_internal_uplift_audit_20260611.md)|G11 도시계획 내부 상향 가능성 read-only 감사 보고|
|[docs/762_g11_planning_internal_uplift_audit_implementation_report_20260611.md](docs/762_g11_planning_internal_uplift_audit_implementation_report_20260611.md)|G11 내부 상향 감사 스크립트/QA 반영 구현 보고|
|[docs/763_platform_qa_suite_after_g11_internal_audit_g45_20260611.md](docs/763_platform_qa_suite_after_g11_internal_audit_g45_20260611.md)|G11 내부 상향 감사 반영 후 G15 QA suite g45 12/12 PASS 보고|
|[docs/764_platform_completion_gate_after_g11_internal_audit_20260611.md](docs/764_platform_completion_gate_after_g11_internal_audit_20260611.md)|G11 내부 상향 감사 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/765_g3_g6_internal_uplift_recheck_20260611.md](docs/765_g3_g6_internal_uplift_recheck_20260611.md)|G3~G6 내부 자동상향 후보 최신 재점검 보고|
|[docs/766_external_result_file_scan_20260611.md](docs/766_external_result_file_scan_20260611.md)|외장하드 exports 결과 CSV 자동탐색 및 주입 가능 여부 스캔 보고|
|[docs/767_external_result_file_scan_implementation_report_20260611.md](docs/767_external_result_file_scan_implementation_report_20260611.md)|외부 결과파일 자동탐색 스캐너/API/UI/QA 구현 보고|
|[docs/768_platform_qa_suite_after_result_file_scan_g46_20260611.md](docs/768_platform_qa_suite_after_result_file_scan_g46_20260611.md)|외부 결과파일 자동탐색 반영 후 G15 QA suite g46 12/12 PASS 보고|
|[docs/769_platform_completion_gate_after_result_file_scan_20260611.md](docs/769_platform_completion_gate_after_result_file_scan_20260611.md)|외부 결과파일 자동탐색 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/770_external_result_file_scan_with_commands_20260611.md](docs/770_external_result_file_scan_with_commands_20260611.md)|외장하드 결과 CSV 스캔 결과에 dry-run/import 명령을 포함한 보고|
|[docs/771_external_result_file_scan_commands_implementation_report_20260611.md](docs/771_external_result_file_scan_commands_implementation_report_20260611.md)|외부 결과파일별 실행 명령 생성 DB/API/UI 구현 보고|
|[docs/772_platform_qa_suite_after_result_file_commands_g47_20260611.md](docs/772_platform_qa_suite_after_result_file_commands_g47_20260611.md)|외부 결과파일 명령 생성 반영 후 G15 QA suite g47 12/12 PASS 보고|
|[docs/773_platform_completion_gate_after_result_file_commands_20260611.md](docs/773_platform_completion_gate_after_result_file_commands_20260611.md)|외부 결과파일 명령 생성 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/774_result_file_execution_plan_20260611.md](docs/774_result_file_execution_plan_20260611.md)|외부 결과파일 실행대장 생성 및 입력대기/실행가능 파일 분리 보고|
|[docs/775_result_file_execution_plan_implementation_report_20260611.md](docs/775_result_file_execution_plan_implementation_report_20260611.md)|외부 결과파일 실행대장 DB/API/UI/권한보강 구현 보고|
|[docs/776_platform_qa_suite_after_result_file_execution_plan_g48_20260611.md](docs/776_platform_qa_suite_after_result_file_execution_plan_g48_20260611.md)|외부 결과파일 실행대장 반영 후 G15 QA suite g48 12/12 PASS 보고|
|[docs/777_platform_completion_gate_after_result_file_execution_plan_20260611.md](docs/777_platform_completion_gate_after_result_file_execution_plan_20260611.md)|외부 결과파일 실행대장 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/778_auction_provider_secure_access_preflight_20260611.md](docs/778_auction_provider_secure_access_preflight_20260611.md)|인포케어·옥션원 등 경매 Provider 보안접속 준비상태와 Codex 계정값 미보유 판정 보고|
|[docs/779_auction_provider_secure_access_preflight_implementation_report_20260611.md](docs/779_auction_provider_secure_access_preflight_implementation_report_20260611.md)|경매 Provider 보안접속 Preflight DB/API/UI/QA 구현 보고|
|[docs/780_platform_qa_suite_after_auction_provider_access_preflight_g49_20260611.md](docs/780_platform_qa_suite_after_auction_provider_access_preflight_g49_20260611.md)|경매 Provider 보안접속 Preflight 반영 후 G15 QA suite g49 12/12 PASS 보고|
|[docs/781_platform_completion_gate_after_auction_provider_access_preflight_20260611.md](docs/781_platform_completion_gate_after_auction_provider_access_preflight_20260611.md)|경매 Provider 보안접속 Preflight 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/782_coordinate_source_candidate_recheck_20260611.md](docs/782_coordinate_source_candidate_recheck_20260611.md)|좌표 원천 후보 테이블 재스캔 보고|
|[docs/783_g3_g6_internal_uplift_recheck_20260611.md](docs/783_g3_g6_internal_uplift_recheck_20260611.md)|G3~G6 내부 자동상향 가능성 재감사 보고|
|[docs/784_g3_geocode_api_batch_probe_20260611.md](docs/784_g3_geocode_api_batch_probe_20260611.md)|기존 좌표 API 호출 방식 소량 probe 및 `admCd` 누락 오류 확인 보고|
|[docs/785_g3_geocode_api_two_stage_probe_20260611.md](docs/785_g3_geocode_api_two_stage_probe_20260611.md)|주소검색 후 좌표검색 2단계 probe 및 JUSO key 승인 오류 확인 보고|
|[docs/786_g3_geocode_api_two_stage_fix_and_key_probe_20260611.md](docs/786_g3_geocode_api_two_stage_fix_and_key_probe_20260611.md)|G3 좌표 API 2단계 수정, 디코딩 방어, key 검증 및 요청 복구 보고|
|[docs/787_platform_qa_suite_after_g3_geocode_two_stage_fix_g49_20260611.md](docs/787_platform_qa_suite_after_g3_geocode_two_stage_fix_g49_20260611.md)|G3 좌표 API 2단계 수정 후 G15 QA suite g49 12/12 PASS 보고|
|[docs/788_platform_completion_gate_after_g3_geocode_two_stage_fix_20260611.md](docs/788_platform_completion_gate_after_g3_geocode_two_stage_fix_20260611.md)|G3 좌표 API 2단계 수정 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/789_geocode_api_key_preflight_20260611.md](docs/789_geocode_api_key_preflight_20260611.md)|JUSO 주소 API key 승인상태 preflight와 G3 좌표대기 6,110건 차단 원인 보고|
|[docs/790_geocode_api_key_preflight_implementation_report_20260611.md](docs/790_geocode_api_key_preflight_implementation_report_20260611.md)|JUSO 주소 API key preflight DB/API/UI/QA 구현 보고|
|[docs/791_platform_qa_suite_after_geocode_api_key_preflight_g50_20260611.md](docs/791_platform_qa_suite_after_geocode_api_key_preflight_g50_20260611.md)|JUSO 주소 API key preflight 반영 후 G15 QA suite g50 12/12 PASS 보고|
|[docs/792_platform_completion_gate_after_geocode_api_key_preflight_20260611.md](docs/792_platform_completion_gate_after_geocode_api_key_preflight_20260611.md)|JUSO 주소 API key preflight 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/796_platform_qa_suite_after_auction_reference_visibility_g51_20260611.md](docs/796_platform_qa_suite_after_auction_reference_visibility_g51_20260611.md)|경매 사건번호/관리번호 표시 개선 후 G15 QA suite g51 12/12 PASS 보고|
|[docs/797_platform_completion_gate_after_auction_reference_visibility_g51_20260611.md](docs/797_platform_completion_gate_after_auction_reference_visibility_g51_20260611.md)|경매 사건번호/관리번호 표시 개선 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/798_auction_reference_visibility_implementation_report_20260611.md](docs/798_auction_reference_visibility_implementation_report_20260611.md)|경매이력 목록의 법원 사건번호와 Provider 관리번호 구분 표시 구현 보고|
|[docs/799_internal_same_address_pnu_enrichment_dryrun_20260611.md](docs/799_internal_same_address_pnu_enrichment_dryrun_20260611.md)|내부 동일주소 PNU 보강 dry-run: 신규 적용 후보 0건 확인|
|[docs/800_internal_coordinate_match_enrichment_dryrun_20260611.md](docs/800_internal_coordinate_match_enrichment_dryrun_20260611.md)|내부 동일주소 좌표 보강 dry-run: 신규 적용 후보 0건 확인|
|[docs/801_coordinate_uplift_candidate_rebuild_20260611.md](docs/801_coordinate_uplift_candidate_rebuild_20260611.md)|좌표 보강 후보 재생성: 6,110건 전부 외부 지오코딩 결과 대기 상태로 정리|
|[docs/802_g11_planning_internal_uplift_audit_20260611.md](docs/802_g11_planning_internal_uplift_audit_20260611.md)|G11 도시계획 내부 상향 가능성 감사: 추가 내부 uplift 불가 및 외부 고시 필요량 산정|
|[docs/803_platform_qa_suite_after_internal_source_exhaustion_recheck_20260611.md](docs/803_platform_qa_suite_after_internal_source_exhaustion_recheck_20260611.md)|내부 원천 소진 재검토 후 플랫폼 QA 12/12 PASS 보고|
|[docs/804_platform_completion_gate_after_internal_source_exhaustion_recheck_20260611.md](docs/804_platform_completion_gate_after_internal_source_exhaustion_recheck_20260611.md)|내부 원천 소진 재검토 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/808_external_result_file_scan_full_20260611.md](docs/808_external_result_file_scan_full_20260611.md)|외장하드 전체 결과 CSV 3,556개 strict 스캔: 주입 후보 0행 확인|
|[docs/809_external_dependency_blockers_after_full_result_scan_20260611.md](docs/809_external_dependency_blockers_after_full_result_scan_20260611.md)|전체 결과 CSV 스캔 이후 G3~G12 외부 의존성 차단 원장 갱신|
|[docs/810_result_file_execution_plan_after_full_result_scan_20260611.md](docs/810_result_file_execution_plan_after_full_result_scan_20260611.md)|전체 결과 CSV 기준 실행대장 3,556건 DB 반영 및 dry-run 가능 0건 확인|
|[docs/814_platform_qa_suite_after_full_external_result_scan_dbwrite_20260611.md](docs/814_platform_qa_suite_after_full_external_result_scan_dbwrite_20260611.md)|전체 결과 CSV 스캔 이후 플랫폼 QA 12/12 PASS 및 DB 기록 완료|
|[docs/815_platform_completion_gate_after_full_external_result_scan_qa_pass_20260611.md](docs/815_platform_completion_gate_after_full_external_result_scan_qa_pass_20260611.md)|전체 결과 CSV 스캔 이후 100% 완료 게이트 6 PASS / 10 FAIL 최종 보고|
|[docs/816_platform_qa_suite_healthz_lock_resilience_g52_20260611.md](docs/816_platform_qa_suite_healthz_lock_resilience_g52_20260611.md)|healthz lock-resilience 반영 후 플랫폼 QA g52 12/12 PASS 및 DB retry 기록|
|[docs/817_platform_completion_gate_after_healthz_lock_resilience_g52_20260611.md](docs/817_platform_completion_gate_after_healthz_lock_resilience_g52_20260611.md)|healthz lock-resilience 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/818_healthz_lock_resilience_implementation_report_20260611.md](docs/818_healthz_lock_resilience_implementation_report_20260611.md)|DuckDB lock 상황의 healthz 500 방지 및 QA retry 구현 보고|
|[docs/819_unsafe_db_reader_process_audit_20260611.md](docs/819_unsafe_db_reader_process_audit_20260611.md)|운영 DuckDB 직접 reader 프로세스 감사 결과 및 unsafe_count=0 기록|
|[docs/820_platform_qa_suite_after_unsafe_db_reader_api_g53_20260611.md](docs/820_platform_qa_suite_after_unsafe_db_reader_api_g53_20260611.md)|unsafe DB reader API 반영 후 플랫폼 QA g53 12/12 PASS 보고|
|[docs/821_platform_completion_gate_after_unsafe_db_reader_api_g53_20260611.md](docs/821_platform_completion_gate_after_unsafe_db_reader_api_g53_20260611.md)|unsafe DB reader guard 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/822_unsafe_db_reader_process_guard_implementation_report_20260611.md](docs/822_unsafe_db_reader_process_guard_implementation_report_20260611.md)|운영 DB 직접 reader 감지용 감사기, DB, API, QA 구현 보고|
|[docs/823_platform_qa_suite_after_unsafe_db_reader_readme_g53_20260611.md](docs/823_platform_qa_suite_after_unsafe_db_reader_readme_g53_20260611.md)|README 반영 후 플랫폼 QA g53 12/12 PASS 및 DB 기록 완료|
|[docs/824_platform_completion_gate_after_unsafe_db_reader_readme_g53_20260611.md](docs/824_platform_completion_gate_after_unsafe_db_reader_readme_g53_20260611.md)|unsafe reader lock으로 completion gate DB write가 지연된 증거 보고|
|[docs/825_unsafe_db_reader_process_audit_live_detection_20260611.md](docs/825_unsafe_db_reader_process_audit_live_detection_20260611.md)|운영 DB 직접 reader PID 26628/22284 실시간 감지 보고|
|[docs/826_unsafe_db_reader_process_audit_after_stop_20260611.md](docs/826_unsafe_db_reader_process_audit_after_stop_20260611.md)|unsafe reader 중단 후 unsafe_count=0 및 DB write PASS 보고|
|[docs/827_platform_completion_gate_after_unsafe_db_reader_stop_20260611.md](docs/827_platform_completion_gate_after_unsafe_db_reader_stop_20260611.md)|unsafe reader 중단 후 100% 완료 게이트 DB snapshot 정상 기록|
|[docs/828_unsafe_db_reader_live_remediation_report_20260611.md](docs/828_unsafe_db_reader_live_remediation_report_20260611.md)|운영 DB 직접 reader 실시간 감지, 중단, completion gate 정상화 종합 보고|
|[docs/829_g3_g6_internal_uplift_reaudit_after_guard_20260611.md](docs/829_g3_g6_internal_uplift_reaudit_after_guard_20260611.md)|G3~G6 내부 자동상향 후보 재감사 및 즉시 적용 후보 0건 확인|
|[docs/837_coordinate_uplift_candidate_exact_address_report_20260611.md](docs/837_coordinate_uplift_candidate_exact_address_report_20260611.md)|KGS 교차 원천 정확주소 좌표 후보 18행/16시설 생성 보고|
|[docs/840_coordinate_uplift_candidate_reapply_after_materialized_fix_20260611.md](docs/840_coordinate_uplift_candidate_reapply_after_materialized_fix_20260611.md)|좌표 후보 materialized apply 수정 후 16시설 실제 반영 보고|
|[docs/842_coordinate_uplift_candidate_cleanup_after_apply_20260611.md](docs/842_coordinate_uplift_candidate_cleanup_after_apply_20260611.md)|좌표 반영 후 잔여 ready 후보 2건 superseded 정리 보고|
|[docs/843_platform_qa_suite_after_coordinate_uplift_g54_20260611.md](docs/843_platform_qa_suite_after_coordinate_uplift_g54_20260611.md)|교차 원천 좌표 보강 후 플랫폼 QA g54 12/12 PASS 보고|
|[docs/844_platform_completion_gate_after_coordinate_uplift_g54_20260611.md](docs/844_platform_completion_gate_after_coordinate_uplift_g54_20260611.md)|교차 원천 좌표 보강 후 completion gate 6 PASS / 10 FAIL 보고|
|[docs/845_coordinate_uplift_cross_source_implementation_report_20260611.md](docs/845_coordinate_uplift_cross_source_implementation_report_20260611.md)|KGS 교차 원천 좌표 보강 구현, QA, 완료 게이트 종합 보고|
|[docs/846_unsafe_db_reader_post_coordinate_uplift_20260611.md](docs/846_unsafe_db_reader_post_coordinate_uplift_20260611.md)|좌표 보강 종료 후 unsafe DB reader 0건 및 DB write PASS 최종 감사|
|[docs/847_g11_planning_internal_uplift_reaudit_20260611.md](docs/847_g11_planning_internal_uplift_reaudit_20260611.md)|G11/G12 내부 도시계획 자동상향 후보 0건 재감사 보고|
|[docs/848_vworld_operational_db_guard_smoke_20260611.md](docs/848_vworld_operational_db_guard_smoke_20260611.md)|VWorld 운영 DB 직접 reader 차단 smoke PASS 보고|
|[docs/849_unsafe_db_reader_after_vworld_guard_patch_20260611.md](docs/849_unsafe_db_reader_after_vworld_guard_patch_20260611.md)|VWorld guard 패치 후 unsafe DB reader 0건 감사 보고|
|[docs/850_g11_reaudit_and_vworld_source_guard_implementation_report_20260611.md](docs/850_g11_reaudit_and_vworld_source_guard_implementation_report_20260611.md)|G11 재감사와 VWorld 운영 DB source guard 구현 종합 보고|
|[docs/851_platform_qa_suite_after_vworld_source_guard_g55_20260611.md](docs/851_platform_qa_suite_after_vworld_source_guard_g55_20260611.md)|VWorld source guard 반영 후 플랫폼 QA g55 12/12 PASS 보고|
|[docs/852_platform_completion_gate_after_vworld_source_guard_g55_20260611.md](docs/852_platform_completion_gate_after_vworld_source_guard_g55_20260611.md)|VWorld source guard 반영 후 completion gate 6 PASS / 10 FAIL 보고|
|[docs/853_unsafe_db_reader_final_after_vworld_guard_qa_gate_20260611.md](docs/853_unsafe_db_reader_final_after_vworld_guard_qa_gate_20260611.md)|QA/gate 이후 unsafe DB reader 0건 및 DB write PASS 최종 감사|
|[docs/854_auction_case_no_source_audit_20260611.md](docs/854_auction_case_no_source_audit_20260611.md)|DB/대법원/온비드 원천의 법원 사건번호 감사와 provider 관리번호 역조회 blocker 보고|
|[docs/855_platform_qa_suite_after_auction_case_no_source_audit_g56_20260611.md](docs/855_platform_qa_suite_after_auction_case_no_source_audit_g56_20260611.md)|경매 사건번호 원천 감사 반영 후 QA g56 read-only 실행 보고|
|[docs/856_platform_completion_gate_after_auction_case_no_source_audit_g56_20260611.md](docs/856_platform_completion_gate_after_auction_case_no_source_audit_g56_20260611.md)|경매 사건번호 원천 감사 반영 후 completion gate read-only 6 PASS / 10 FAIL 보고|
|[docs/857_operational_duckdb_lock_blocker_audit_20260611.md](docs/857_operational_duckdb_lock_blocker_audit_20260611.md)|운영 DuckDB write lock blocker 프로세스 감사 및 서비스 프로세스 분리 보고|
|[docs/858_platform_qa_suite_after_duckdb_lock_blocker_audit_g57_20260611.md](docs/858_platform_qa_suite_after_duckdb_lock_blocker_audit_g57_20260611.md)|DuckDB lock blocker 감사 반영 후 플랫폼 QA g57 12/12 PASS 보고|
|[docs/859_platform_completion_gate_after_duckdb_lock_blocker_audit_g57_20260611.md](docs/859_platform_completion_gate_after_duckdb_lock_blocker_audit_g57_20260611.md)|DuckDB lock blocker 감사 반영 후 completion gate DB write 6 PASS / 10 FAIL 보고|
|[docs/860_g3_g6_internal_uplift_opportunity_reaudit_20260611.md](docs/860_g3_g6_internal_uplift_opportunity_reaudit_20260611.md)|G3~G6 내부 자동상향 후보 재감사 및 즉시 적용 후보 0건 판정 보고|
|[docs/861_coordinate_uplift_candidate_refresh_20260611.md](docs/861_coordinate_uplift_candidate_refresh_20260611.md)|G3 좌표 후보 갱신 및 6,094건 외부 지오코딩 필요 보고|
|[docs/862_storage_uplift_candidate_refresh_20260611.md](docs/862_storage_uplift_candidate_refresh_20260611.md)|G6 저장량·설비 후보 17,437행/8,568시설 갱신 보고|
|[docs/863_geocode_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md](docs/863_geocode_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md)|G3 좌표 누락 6,094건을 21개 외부 처리 배치로 재생성한 보고|
|[docs/864_storage_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md](docs/864_storage_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md)|G6 저장량 12,303 후보행/8,567시설을 96개 배치로 재생성한 보고|
|[docs/865_land_area_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md](docs/865_land_area_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md)|G4 토지면적·지번 보강 3,587행을 96개 배치로 재생성한 보고|
|[docs/866_building_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md](docs/866_building_batch_manifest_refresh_after_g3_g6_reaudit_20260611.md)|G5 건축물대장 보강 3,368행을 66개 배치로 재생성한 보고|
|[docs/867_external_workpack_manifest_refresh_after_g3_g6_reaudit_20260611.md](docs/867_external_workpack_manifest_refresh_after_g3_g6_reaudit_20260611.md)|외부 결과 workpack 통합 manifest 10행 재생성 및 dry-run 준비 0건 보고|
|[docs/868_external_intake_status_refresh_after_g3_g6_reaudit_20260611.md](docs/868_external_intake_status_refresh_after_g3_g6_reaudit_20260611.md)|외부 결과파일 intake 상태 11건 재산정 및 입력대기 10건 보고|
|[docs/869_result_file_execution_plan_refresh_after_g3_g6_reaudit_20260611.md](docs/869_result_file_execution_plan_refresh_after_g3_g6_reaudit_20260611.md)|외부 결과파일 실행대장 3,556건 재생성 및 전건 입력대기 보고|
|[docs/870_platform_qa_suite_after_g3_g6_workpack_refresh_g57_20260611.md](docs/870_platform_qa_suite_after_g3_g6_workpack_refresh_g57_20260611.md)|G3~G6 workpack 갱신 후 플랫폼 QA g57 12/12 PASS 보고|
|[docs/871_platform_completion_gate_after_g3_g6_workpack_refresh_20260611.md](docs/871_platform_completion_gate_after_g3_g6_workpack_refresh_20260611.md)|G3~G6 workpack 갱신 후 completion gate DB write 6 PASS / 10 FAIL 보고|
|[docs/1320_platform_qa_suite_full_after_auction_first_run_api_ui_20260612.md](docs/1320_platform_qa_suite_full_after_auction_first_run_api_ui_20260612.md)|경매 1차 우선 조회팩 API·UI 연결 후 플랫폼 QA g97 31/31 PASS 보고|
|[docs/1321_platform_completion_gate_after_auction_first_run_api_ui_20260612.md](docs/1321_platform_completion_gate_after_auction_first_run_api_ui_20260612.md)|경매 1차 우선 조회팩 API·UI 연결 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1322_100pct_control_tower_after_auction_first_run_api_ui_20260612.md](docs/1322_100pct_control_tower_after_auction_first_run_api_ui_20260612.md)|경매 1차 우선 조회팩 API·UI 연결 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1323_auction_first_run_api_ui_implementation_report_20260612.md](docs/1323_auction_first_run_api_ui_implementation_report_20260612.md)|경매 1차 우선 조회팩 API·UI 구현, 보안 확인, 다음 실행절차 보고|
|[docs/1324_platform_qa_suite_after_auction_first_run_file_download_g98_20260612.md](docs/1324_platform_qa_suite_after_auction_first_run_file_download_g98_20260612.md)|경매 1차 우선 조회팩 다운로드 동선 추가 후 플랫폼 QA g98 31/31 PASS 보고|
|[docs/1325_platform_completion_gate_after_auction_first_run_file_download_20260612.md](docs/1325_platform_completion_gate_after_auction_first_run_file_download_20260612.md)|경매 1차 우선 조회팩 다운로드 동선 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1326_100pct_control_tower_after_auction_first_run_file_download_20260612.md](docs/1326_100pct_control_tower_after_auction_first_run_file_download_20260612.md)|경매 1차 우선 조회팩 다운로드 동선 추가 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1327_auction_first_run_file_download_implementation_report_20260612.md](docs/1327_auction_first_run_file_download_implementation_report_20260612.md)|경매 1차 우선 조회팩 검색파일/결과 템플릿 다운로드 구현 보고|
|[docs/1328_platform_qa_suite_after_auction_first_run_result_status_g99_20260612.md](docs/1328_platform_qa_suite_after_auction_first_run_result_status_g99_20260612.md)|경매 1차 결과 입력상태 API/UI 추가 후 플랫폼 QA g99 31/31 PASS 보고|
|[docs/1329_platform_completion_gate_after_auction_first_run_result_status_20260612.md](docs/1329_platform_completion_gate_after_auction_first_run_result_status_20260612.md)|경매 1차 결과 입력상태 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1330_100pct_control_tower_after_auction_first_run_result_status_20260612.md](docs/1330_100pct_control_tower_after_auction_first_run_result_status_20260612.md)|경매 1차 결과 입력상태 반영 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1331_auction_first_run_result_status_implementation_report_20260612.md](docs/1331_auction_first_run_result_status_implementation_report_20260612.md)|경매 1차 결과 입력상태 API/UI 구현, 보안 확인, 다음 실행절차 보고|
|[docs/1332_platform_qa_suite_after_auction_first_run_ready_smoke_g100_20260612.md](docs/1332_platform_qa_suite_after_auction_first_run_ready_smoke_g100_20260612.md)|경매 1차 결과 ready smoke 보강 후 플랫폼 QA g100 31/31 PASS 보고|
|[docs/1333_platform_completion_gate_after_auction_first_run_ready_smoke_20260612.md](docs/1333_platform_completion_gate_after_auction_first_run_ready_smoke_20260612.md)|경매 1차 결과 ready smoke 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1334_100pct_control_tower_after_auction_first_run_ready_smoke_20260612.md](docs/1334_100pct_control_tower_after_auction_first_run_ready_smoke_20260612.md)|경매 1차 결과 ready smoke 보강 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1335_auction_first_run_ready_smoke_hardening_report_20260612.md](docs/1335_auction_first_run_ready_smoke_hardening_report_20260612.md)|경매 1차 결과 유효행 변환과 strict importer dry-run 검증 보강 보고|
|[docs/1336_platform_qa_suite_after_revenue_smoke_guard_g101_20260612.md](docs/1336_platform_qa_suite_after_revenue_smoke_guard_g101_20260612.md)|매출·재무·수익가치 smoke guard 추가 후 플랫폼 QA g101 34/34 PASS 보고|
|[docs/1337_platform_completion_gate_after_revenue_smoke_guard_20260612.md](docs/1337_platform_completion_gate_after_revenue_smoke_guard_20260612.md)|매출·재무·수익가치 smoke guard 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1338_100pct_control_tower_after_revenue_smoke_guard_20260612.md](docs/1338_100pct_control_tower_after_revenue_smoke_guard_20260612.md)|매출·재무·수익가치 smoke guard 추가 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1339_revenue_smoke_guard_hardening_report_20260612.md](docs/1339_revenue_smoke_guard_hardening_report_20260612.md)|G9/G10 실데이터 입력 이후 importer·가치모델 실행성 보강 보고|
|[docs/1340_platform_qa_suite_after_planning_prediction_smoke_guard_g102_20260612.md](docs/1340_platform_qa_suite_after_planning_prediction_smoke_guard_g102_20260612.md)|도시계획·예측 smoke guard 추가 후 플랫폼 QA g102 37/37 PASS 보고|
|[docs/1341_platform_completion_gate_after_planning_prediction_smoke_guard_20260612.md](docs/1341_platform_completion_gate_after_planning_prediction_smoke_guard_20260612.md)|도시계획·예측 smoke guard 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1342_100pct_control_tower_after_planning_prediction_smoke_guard_20260612.md](docs/1342_100pct_control_tower_after_planning_prediction_smoke_guard_20260612.md)|도시계획·예측 smoke guard 추가 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1343_planning_prediction_smoke_guard_hardening_report_20260612.md](docs/1343_planning_prediction_smoke_guard_hardening_report_20260612.md)|G11/G12 실데이터 입력 이후 importer·예측모델 실행성 보강 보고|
|[docs/1344_platform_qa_suite_after_storage_smoke_guard_g103_20260612.md](docs/1344_platform_qa_suite_after_storage_smoke_guard_g103_20260612.md)|저장량·설비 smoke guard 추가 후 플랫폼 QA g103 39/39 PASS 보고|
|[docs/1345_platform_completion_gate_after_storage_smoke_guard_20260612.md](docs/1345_platform_completion_gate_after_storage_smoke_guard_20260612.md)|저장량·설비 smoke guard 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1346_100pct_control_tower_after_storage_smoke_guard_20260612.md](docs/1346_100pct_control_tower_after_storage_smoke_guard_20260612.md)|저장량·설비 smoke guard 추가 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1347_storage_smoke_guard_hardening_report_20260612.md](docs/1347_storage_smoke_guard_hardening_report_20260612.md)|G6 저장량 실데이터 입력 이후 importer·완료게이트 strictness 보강 보고|
|[docs/1348_platform_qa_suite_after_location_land_building_smoke_guard_g104_20260612.md](docs/1348_platform_qa_suite_after_location_land_building_smoke_guard_g104_20260612.md)|위치·토지·건물 smoke guard 추가 후 플랫폼 QA g104 44/44 PASS 보고|
|[docs/1349_platform_completion_gate_after_location_land_building_smoke_guard_20260612.md](docs/1349_platform_completion_gate_after_location_land_building_smoke_guard_20260612.md)|위치·토지·건물 smoke guard 추가 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1350_100pct_control_tower_after_location_land_building_smoke_guard_20260612.md](docs/1350_100pct_control_tower_after_location_land_building_smoke_guard_20260612.md)|위치·토지·건물 smoke guard 추가 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1351_location_land_building_smoke_guard_hardening_report_20260612.md](docs/1351_location_land_building_smoke_guard_hardening_report_20260612.md)|G3/G4/G5 실데이터 입력 이후 importer·완료게이트 strictness 보강 보고|
|[docs/1352_next_execution_priority_pack_20260612.md](docs/1352_next_execution_priority_pack_20260612.md)|100% 도달 다음 실행 우선순위 팩 37행 생성 보고|
|[docs/1353_platform_qa_suite_after_next_execution_priority_pack_g105_20260612.md](docs/1353_platform_qa_suite_after_next_execution_priority_pack_g105_20260612.md)|다음 실행 우선순위 팩 반영 후 플랫폼 QA g105 45/45 PASS 보고|
|[docs/1354_platform_completion_gate_after_next_execution_priority_pack_20260612.md](docs/1354_platform_completion_gate_after_next_execution_priority_pack_20260612.md)|다음 실행 우선순위 팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1355_100pct_control_tower_after_next_execution_priority_pack_20260612.md](docs/1355_100pct_control_tower_after_next_execution_priority_pack_20260612.md)|다음 실행 우선순위 팩 반영 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1356_next_execution_priority_pack_implementation_report_20260612.md](docs/1356_next_execution_priority_pack_implementation_report_20260612.md)|P0/P1/P2 균형형 다음 실행 우선순위 팩 구현 보고|
|[docs/1357_auction_alias_contract_implementation_report_20260612.md](docs/1357_auction_alias_contract_implementation_report_20260612.md)|경매 결과양식 queue/provider/증빙 한글·영문 alias 계약 보강 보고|
|[docs/1358_platform_qa_suite_after_auction_alias_contract_g106_20260612.md](docs/1358_platform_qa_suite_after_auction_alias_contract_g106_20260612.md)|경매 alias 계약 보강 후 플랫폼 QA g106 45/45 PASS 보고|
|[docs/1359_platform_completion_gate_after_auction_alias_contract_20260612.md](docs/1359_platform_completion_gate_after_auction_alias_contract_20260612.md)|경매 alias 계약 보강 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1360_100pct_control_tower_after_auction_alias_contract_20260612.md](docs/1360_100pct_control_tower_after_auction_alias_contract_20260612.md)|경매 alias 계약 보강 후 100% 관제보드와 대기 실행계획 361건 보고|
|[docs/1364_platform_qa_suite_after_next_execution_priority_api_ui_g107_20260612.md](docs/1364_platform_qa_suite_after_next_execution_priority_api_ui_g107_20260612.md)|다음 실행 우선순위 API/UI 반영 후 플랫폼 QA g107 45/45 PASS 보고|
|[docs/1365_platform_completion_gate_after_next_execution_priority_api_ui_20260612.md](docs/1365_platform_completion_gate_after_next_execution_priority_api_ui_20260612.md)|다음 실행 우선순위 API/UI 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1366_100pct_control_tower_after_next_execution_priority_api_ui_20260612.md](docs/1366_100pct_control_tower_after_next_execution_priority_api_ui_20260612.md)|다음 실행 우선순위 API/UI 반영 후 100% 관제보드와 입력 대기 실행계획 361건 보고|
|[docs/1367_next_execution_priority_api_ui_implementation_report_20260612.md](docs/1367_next_execution_priority_api_ui_implementation_report_20260612.md)|37행 다음 실행 우선순위 팩을 운영 API와 대시보드에 연결한 구현·검증 보고|
|[docs/1368_auction_next_priority_result_pack_20260612.md](docs/1368_auction_next_priority_result_pack_20260612.md)|100% 우선순위 G7/G8 경매 결과 입력팩 1,000행·721시설 생성 보고|
|[docs/1369_platform_qa_suite_after_auction_next_priority_result_pack_g108_20260612.md](docs/1369_platform_qa_suite_after_auction_next_priority_result_pack_g108_20260612.md)|경매 다음 우선순위 입력팩 API/UI 반영 후 플랫폼 QA g108 46/46 PASS 보고|
|[docs/1370_platform_completion_gate_after_auction_next_priority_result_pack_20260612.md](docs/1370_platform_completion_gate_after_auction_next_priority_result_pack_20260612.md)|경매 다음 우선순위 입력팩 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1371_100pct_control_tower_after_auction_next_priority_result_pack_20260612.md](docs/1371_100pct_control_tower_after_auction_next_priority_result_pack_20260612.md)|경매 다음 우선순위 입력팩 반영 후 100% 관제보드와 입력 대기 실행계획 361건 보고|
|[docs/1372_auction_next_priority_result_pack_implementation_report_20260612.md](docs/1372_auction_next_priority_result_pack_implementation_report_20260612.md)|G7/G8 경매 입력팩 DB/API/UI 구현·검증·다음 실행 기준 보고|
|[docs/1373_auction_next_priority_result_pipeline_20260612.md](docs/1373_auction_next_priority_result_pipeline_20260612.md)|경매 다음 우선순위 결과 안전 실행기, 빈 결과팩 `INPUT_WAITING` 판정 보고|
|[docs/1375_platform_qa_suite_after_auction_next_priority_pipeline_g109_20260612.md](docs/1375_platform_qa_suite_after_auction_next_priority_pipeline_g109_20260612.md)|경매 다음 결과 파이프라인 API/UI 반영 후 플랫폼 QA g109 46/46 PASS 보고|
|[docs/1376_platform_completion_gate_after_auction_next_priority_pipeline_20260612.md](docs/1376_platform_completion_gate_after_auction_next_priority_pipeline_20260612.md)|경매 다음 결과 파이프라인 반영 후 100% 완료 게이트 6 PASS / 10 FAIL 보고|
|[docs/1377_100pct_control_tower_after_auction_next_priority_pipeline_20260612.md](docs/1377_100pct_control_tower_after_auction_next_priority_pipeline_20260612.md)|경매 다음 결과 파이프라인 반영 후 100% 관제보드와 입력 대기 실행계획 361건 보고|
|[docs/1378_auction_next_priority_pipeline_implementation_report_20260612.md](docs/1378_auction_next_priority_pipeline_implementation_report_20260612.md)|경매 다음 우선순위 결과 파이프라인 구현·검증·WBS 보고|

## 전제와 게이트

- V1 기준 검색 조회는 주유소 1행 단위의 `v_station_search_list`를 사용한다. 기존 호환명 `v_station_npl_base`도 같은 원칙으로 유지한다.
- 상세 화면의 필지, 영업이력, 가격이력은 별도 상세 API와 상세 뷰에서 조회한다.
- 개발 착수 전 Sprint 0에서 원천 데이터 접근권, 상용 재판매 라이선스, 주소-PNU 자동 매칭률, 배포 계정을 go/no-go로 검증한다.
- V1은 단일 조직 또는 설계 파트너 기준의 검색 서비스로 좁힌다. API 상품화, 포트폴리오 업로드, 다조직 과금, A-E 위험등급은 V2 이후로 둔다.
- V1의 NPL 분석 표시는 투명한 규칙 기반 `LOW/MEDIUM/HIGH` red-flag만 사용한다.

## 권장 읽기 순서

1. `00_commercial_service_report_20260601.md`
2. `01_roadmap_to_commercial_launch.md`
3. `02_wireframes.md`
4. `03_tech_stack_architecture.md`
5. `04_database_schema_and_build_plan.md`
6. `05_development_execution_plan.md`
7. `06_launch_operations_checklist.md`
8. `07_review_response_upgrade_notes_20260601.md`
9. `08_current_progress_fast_service_assessment_20260601.md`
10. `09_score100_uplift_resolution_report_20260601.md`
11. `10_next_development_direction_20260601.md`
12. `11_private_pilot_implementation_backlog_20260601.md`
13. `12_release_blocker_resolution_runbook_20260601.md`
14. `13_codebase_stabilization_refactor_plan_20260601.md`
15. `14_beta_public_expansion_roadmap_20260601.md`
16. `15_private_pilot_approval_pack_template_20260601.md`
17. `16_hub_building_register_ingestion_report_20260601.md`
18. `17_hub_extra_datasets_ingestion_report_20260602.md`
19. `18_service_mvp_detailed_execution_plan_20260602.md`
20. `19_service_mvp_technical_specification_20260602.md`
21. `20_final_mvp_execution_governance_report_20260602.md`
22. `21_hub_column_mapping_dictionary_20260602.md`
23. `22_mvp_quality_check_report_20260602.md`
24. `23_development_approval_kickoff_report_20260602.md`
25. `24_next_development_station_matching_execution_plan_20260602.md`
26. `25_next_development_station_matching_technical_specification_20260602.md`
27. `26_station_source_inventory_report_20260602.md`
28. `27_npl_blueprint_schema_alignment_report_20260602.md`
29. `28_development_approval_implementation_report_20260602.md`
30. `29_station_master_load_report_20260602.md`
31. `30_station_hub_match_report_20260602.md`
32. `31_next_development_status_report_20260602.md`
33. `32_next_development_implementation_report_20260602.md`
34. `33_next_development_status_after_detail_api_20260602.md`
35. `34_data_precision_improvement_execution_plan_20260602.md`
36. `35_data_precision_development_start_report_20260602.md`
37. `36_address_precision_profile_build_report_20260602.md`
38. `37_pnu_candidate_build_report_20260602.md`
39. `38_station_precision_quality_report_20260602.md`
40. `39_station_area_facility_storage_extension_plan_20260602.md`
41. `40_unified_fuel_charging_site_db_injection_plan_wbs_20260602.md`
42. `41_unified_energy_site_immediate_implementation_report_20260602.md`
43. `42_energy_site_station_injection_report_20260602.md`
44. `43_energy_site_mart_build_report_20260602.md`
45. `44_energy_site_quality_report_20260602.md`
46. `45_energy_source_download_injection_report_20260602.md`
47. `46_energy_site_mart_rebuild_after_source_injection_20260602.md`
48. `47_energy_site_quality_after_source_injection_20260602.md`
49. `48_next_development_work_report_after_source_injection_20260602.md`
50. `49_energy_site_precision_pipeline_implementation_report_20260602.md`
51. `50_energy_site_precision_mart_rebuild_report_20260602.md`
52. `51_energy_site_precision_quality_report_20260602.md`
53. `52_next_charging_station_pnu_precision_spec_wbs_20260602.md`
54. `53_next_energy_site_precision_technical_spec_20260602.md`
55. `54_next_energy_site_precision_wbs_20260602.md`
56. `55_energy_site_geocode_processing_report_20260602.md`
57. `56_claude_gate_development_implementation_report_20260602.md`
58. `57_code_cleanup_report_20260602.md`
59. `58_next_pnu_uplift_and_cleanup_technical_spec_20260602.md`
60. `59_next_pnu_uplift_wbs_claude_review_20260602.md`
61. `60_next_execution_sprint_technical_spec_20260602.md`
62. `61_next_execution_sprint_wbs_claude_reflection_20260602.md`
63. `62_immediate_export_audit_common_utils_technical_spec_20260602.md`
64. `63_immediate_export_audit_common_utils_wbs_claude_review_20260602.md`
65. `64_energy_site_geocode_export_execution_report_20260602.md`
66. `65_energy_site_pnu_audit_sample_report_20260602.md`
67. `66_immediate_export_audit_implementation_report_20260602.md`
68. `67_next_geocode_import_pnu_uplift_technical_spec_20260602.md`
69. `68_next_geocode_import_pnu_uplift_wbs_claude_review_20260602.md`
70. `69_charging_station_geocode_import_runner_implementation_report_20260602.md`
71. `70_charging_station_pnu_coverage_uplift_blocker_report_20260602.md`
72. `71_energy_site_precision_quality_after_geocode_import_20260602.md`
73. `72_next_address_api_acquisition_technical_spec_20260602.md`
74. `73_next_address_api_acquisition_wbs_claude_review_20260602.md`
75. `74_address_api_collection_runner_implementation_report_20260602.md`
76. `75_address_api_collection_execution_report_20260602.md`
77. `76_public_data_key_juso_compatibility_smoke_report_20260602.md`
78. `77_data_go_kr_15096712_direct_download_attempt_report_20260602.md`
79. `78_data_go_kr_15059078_vworld_road_building_api_review_20260602.md`
80. `79_next_key_independent_charging_pnu_uplift_technical_spec_20260602.md`
81. `80_next_key_independent_charging_pnu_uplift_wbs_claude_review_20260602.md`
82. `81_service_ui_ux_implementation_report_20260602.md`
83. `82_next_public_service_ux_feature_technical_spec_20260603.md`
84. `83_next_public_service_ux_feature_wbs_claude_review_20260603.md`
85. `84_public_service_ux_feature_implementation_report_20260603.md`
86. `85_next_pnu_admin_ops_hardening_technical_spec_20260603.md`
87. `86_next_pnu_admin_ops_hardening_wbs_claude_review_20260603.md`
88. `87_hyundaicard_ui_naver_maps_implementation_report_20260603.md`
89. `88_vworld_openlayers_free_map_implementation_report_20260603.md`
90. `89_next_map_data_ops_hardening_technical_spec_20260603.md`
91. `90_next_map_data_ops_wbs_claude_review_20260603.md`
92. `91_map_data_ops_hardening_implementation_report_20260603.md`
93. `92_next_commercial_launch_readiness_technical_spec_20260603.md`
94. `93_next_commercial_launch_readiness_wbs_claude_review_20260603.md`
95. `94_commercial_launch_readiness_implementation_report_20260603.md`
96. `95_next_full_commercialization_technical_spec_20260603.md`
97. `96_next_full_commercialization_wbs_claude_review_20260603.md`
98. `97_full_commercialization_implementation_report_20260603.md`
99. `98_license_gate_report_20260603.md`
100. `99_next_final_launch_gate_closure_technical_spec_20260603.md`
101. `100_next_final_launch_gate_closure_wbs_claude_review_20260603.md`
102. `101_final_launch_gate_check_report_20260603.md`
103. `102_final_commercial_launch_approval_pack_20260603.md`
104. `103_final_launch_gate_closure_implementation_report_20260603.md`
105. `104_next_100_percent_completion_technical_spec_20260604.md`
106. `105_next_100_percent_completion_wbs_claude_review_20260604.md`
107. `106_100_percent_completion_implementation_report_20260604.md`
108. `107_lg_external_data_migration_report_20260604.md`
109. `108_agent_common_handoff_20260604.md`
110. `109_agent_common_handoff_implementation_report_20260604.md`

## 실행 스크립트

|파일|용도|
|---|---|
|`scripts/build_energy_site_coordinate_quality.py`|통합 에너지 사이트 좌표 품질 테이블 생성/갱신|
|`scripts/audit_opinet_handoff_delta.py`|OPINET handoff ZIP이 현재 DB 누락 PNU/좌표를 실제로 채울 수 있는지 dry-run 감사|
|`scripts/build_energy_site_geocode_batch_manifest.py`|G3 좌표 누락 대기열을 표준 시도/시설유형별 batch manifest와 결과양식으로 분리|
|`scripts/build_energy_site_geocode_intake_preflight.py`|G3 좌표 결과양식을 strict importer 검증 함수로 전수 dry-run하고 반려 사유를 DB/API/UI에 제공|
|`scripts/build_energy_site_external_intake_status.py`|G3~G12 외부 결과파일 intake 상태와 strict importer 판정을 통합 보고|
|`scripts/build_energy_site_land_area_batch_manifest.py`|G4 토지 지번·면적 대기열을 PNU 필요/면적 필요 상태별 batch manifest와 결과양식으로 분리|
|`scripts/build_energy_site_auction_history_batch_manifest.py`|G7 과거 경매 이력 provider 검색 대기열을 배치 manifest와 결과양식으로 분리|
|`scripts/build_energy_site_current_auction_batch_manifest.py`|G8 현재 경매 진행 여부 provider 검색 대기열을 배치 manifest와 결과양식으로 분리|
|`scripts/build_energy_site_current_auction_reference_candidates.py`|법원 사건번호 없는 현재/예정 경매 provider 관리번호 후보를 별도 테이블로 분리|
|`scripts/export_current_auction_reference_resolution_pack.py`|현재/예정 경매 provider 관리번호 후보를 법원 사건번호 역조회 queue/result template으로 export|
|`scripts/smoke_current_auction_reference_resolution_pack_export.py`|현재경매 후보 역조회 작업팩 export smoke test|
|`scripts/build_energy_site_auction_provider_workbench.py`|G7/G8 경매 provider 배치, 결과양식, 필수입력, dry-run/import 명령을 통합 작업대로 생성|
|`scripts/build_energy_site_auction_provider_intake_preflight.py`|G7/G8 경매 결과양식을 strict importer 검증 함수로 전수 dry-run하고 반려 사유를 DB/API/UI에 제공|
|`scripts/build_energy_site_g7_g8_auction_pass_threshold_pack.py`|G7/G8 과거·현재경매 큐와 사건번호 보정 큐를 시설 단위 통과 입력팩으로 압축|
|`scripts/build_energy_site_threshold_execution_board.py`|G3~G12 threshold pack을 strict importer dry-run/import 명령과 후속 완료게이트 명령으로 연결|
|`scripts/run_energy_site_threshold_gate.py`|G3~G12 threshold 결과파일의 placeholder·경로·빈양식·필수값·부분 import 위험을 검증한 뒤 dry-run/import/model/post 실행|
|`scripts/smoke_threshold_gate_input_preflight.py`|threshold gate가 checked_at-only 경매 결과와 부분 import를 실행 전 차단하는지 smoke 검증|
|`scripts/build_energy_site_threshold_result_workpack.py`|G3~G12 최소 통과 대상의 결과양식 CSV와 운영 API용 workpack 색인을 생성|
|`scripts/build_energy_site_next_input_operator_brief.py`|최신 threshold workpack·실행보드·계약감사를 묶어 다음 외부 입력 운영 브리프를 생성|
|`scripts/build_energy_site_gate_pass_gap_projection.py`|G3~G12 Gate별 통과까지 필요한 추가 strict 시설 수와 첫 실행 배치를 계산|
|`scripts/build_energy_site_gate_pass_minimum_batch_queue.py`|전체 실행보드에서 Gate 통과에 필요한 최소 배치 큐를 생성|
|`scripts/build_energy_site_next_execution_priority_pack.py`|G3~G12 최소 배치 큐에서 P0/P1/P2 균형형 다음 실행 우선순위 팩을 생성|
|`scripts/build_energy_site_revenue_batch_manifest.py`|G9/G10 카드결제·재무자료 입력 대기열을 기간/시설유형/시도별 batch manifest와 결과양식으로 분리|
|`scripts/build_energy_site_revenue_input_workboard.py`|G9/G10 카드·재무 threshold pack을 행 단위 입력 작업보드 CSV/HTML/API 테이블로 전개|
|`scripts/import_revenue_input_workboard_results.py`|G9/G10 매출·재무 작업보드 결과 입력 CSV를 CARD/FINANCIAL strict import-ready CSV와 preflight 테이블로 변환|
|`scripts/smoke_revenue_workboard_result_adapter.py`|매출·재무 작업보드 결과 어댑터가 기존 strict importer 계약을 통과하는지 검증|
|`scripts/build_energy_site_planning_batch_manifest.py`|G11/G12 도시계획·도로 영향 미확인 대상을 PNU/좌표 보유 여부와 지역/유형별 batch manifest로 분리|
|`scripts/build_energy_site_planning_input_workboard.py`|G11 도시계획·도로 고시 확인 대상을 행 단위 작업보드 CSV/HTML/API 테이블로 전개|
|`scripts/import_planning_input_workboard_results.py`|G11 작업보드 결과 입력 CSV를 strict import-ready CSV와 preflight 테이블로 변환|
|`scripts/smoke_planning_workboard_result_adapter.py`|G11 작업보드 결과 어댑터가 기존 도시계획 strict importer 계약을 통과하는지 검증|
|`scripts/smoke_map_provider.py`|지도 provider 설정/API/타일 smoke test|
|`scripts/capture_service_screenshots.py`|서비스 데스크톱/모바일 화면 캡처 검증|
|`scripts/inspect_station_source.py`|주유소 원천 후보 파일 점검|
|`scripts/load_station_master.py`|주유소 원천 CSV/XLSX를 표준 station 테이블로 적재|
|`scripts/build_station_hub_matches.py`|station 테이블과 건축HUB 주소 기반 매칭 후보 생성|
|`scripts/build_service_marts.py`|카탈로그/컬럼/검색 마트 생성|
|`scripts/run_mvp_quality_checks.py`|MVP 품질검사 실행 및 DB 결과 저장|
|`scripts/build_station_address_precision_profile.py`|주소 정밀도 프로파일 및 주소 API 요청 대기열 생성|
|`scripts/build_station_pnu_candidates.py`|건축HUB 후보 기반 19자리 PNU 후보 생성|
|`scripts/run_station_precision_quality_checks.py`|주유소 데이터 정밀도 전용 품질검사 실행|
|`scripts/inject_station_master_to_energy_site.py`|기존 주유소 마스터를 통합 에너지 사이트 DB로 인젝션|
|`scripts/download_inject_energy_source_data.py`|LPG/CNG/LNG·LCNG/수소 원천 다운로드 및 통합 에너지 사이트 DB 인젝션|
|`scripts/build_energy_site_precision_pipeline.py`|통합 에너지 사이트 주소 정밀도/PNU/면적/시설/검토 큐 파이프라인 생성|
|`scripts/run_energy_site_geocode_requests.py`|주소 API/import 결과 처리 및 PNU 후보 병합|
|`scripts/lib/duckdb_write_retry.py`|DuckDB writer lock 발생 시 운영 DB write를 제한 횟수만큼 재시도하는 공통 유틸|
|`scripts/create_duckdb_read_snapshot.py`|운영 DuckDB 파일 스냅샷을 `.partial` 검증 후 승격하는 도구|
|`scripts/create_duckdb_table_snapshot.py`|선택 테이블만 새 DuckDB로 복제하는 thin snapshot 도구|
|`scripts/build_vworld_snapshot_batch_command.py`|full table snapshot이 있을 때만 VWorld 배치 실행 명령을 생성하는 guard 도구|
|`scripts/run_vworld_building_unit_extract_snapshot_safe.py`|full table snapshot이 있을 때만 VWorld 건물단위 추출을 실행하는 safe runner|
|`scripts/export_energy_site_geocode_requests.py`|주소 API 투입용 READY 요청 CSV Export 및 품질 보고|
|`scripts/audit_energy_site_pnu_sample.py`|PNU 후보 감사 샘플 테이블 및 검수 보고 생성|
|`scripts/lib/energy_site_common.py`|통합 에너지 사이트 스크립트 공통 유틸|
|`scripts/build_energy_site_marts.py`|통합 에너지 사이트 검색/요약/지역/토지/건축물 마트 생성|
|`scripts/run_energy_site_quality_checks.py`|통합 에너지 사이트 품질검사 실행|
|`scripts/run_energy_site_precision_quality_checks.py`|통합 에너지 사이트 정밀도 품질검사 실행|
|`scripts/build_energy_site_g3_g5_gap_table.py`|G3~G5 좌표·토지 지번·총 토지면적·건축물 링크 누락을 시설별로 산정하는 gap table 빌더|
|`scripts/build_energy_site_g3_g5_workpack_index.py`|G3/G4/G5 manifest를 좌표→토지→건물 순서의 통합 workpack index와 외장하드 CSV로 묶는 빌더|
|`scripts/build_energy_site_g3_g5_pass_threshold_pack.py`|G3/G4/G5 완료게이트 통과에 필요한 최소 우선 시설 입력팩과 DB 테이블 생성|
|`scripts/build_energy_site_g6_storage_pass_threshold_pack.py`|G6 저장량 완료게이트 통과에 필요한 최소 우선 시설 입력팩과 DB 테이블 생성|
|`scripts/run_g3_geocode_api_batch.py`|환경변수 key만 사용해 좌표 누락 G3 요청을 실행하는 key-safe Python runner|
|`scripts/run_g3_geocode_api_batch_secure.ps1`|API key를 파일에 저장하지 않고 현재 세션에서만 받아 G3 좌표 batch를 실행하는 PowerShell wrapper|
|`scripts/build_geocode_api_key_preflight.py`|JUSO 주소검색/좌표검색 API key 승인상태를 key 미저장 원칙으로 점검|
|`scripts/audit_energy_site_internal_uplift_opportunities.py`|G3~G6 내부 DB 자동상향 가능성과 외부 원천 필요성을 read-only 감사|
|`scripts/build_energy_site_external_impact_priority.py`|G3~G12 실패 게이트별 외부 원천 투입 영향도와 최우선 배치를 산정|
|`scripts/audit_vworld_building_unit_extract_progress.py`|VWorld 건물단위 추출 진행률과 G5/G7 승격 가능성을 read-only 감사|
|`scripts/audit_g11_planning_internal_uplift.py`|G11 도시계획 내부 원천 추가 상향 가능성과 외부 고시 투입 필요량을 read-only 감사|
|`scripts/scan_energy_site_external_result_files.py`|외장하드 exports의 결과 CSV를 자동탐색해 Dry-run 가능 파일과 주입 후보 행을 판정|
|`scripts/build_energy_site_result_file_execution_plan.py`|스캔된 외부 결과 CSV를 실행 가능/입력 대기 상태로 분리하고 안전 실행대장을 생성|
|`scripts/build_energy_site_external_result_contract_audit.py`|G3~G12 외부 결과 CSV의 필수계약, 후보행, 실행가능 상태를 Gate별로 감사|
|`scripts/smoke_external_result_alias_contract.py`|한글/Provider식 결과 CSV 컬럼명이 계약감사 후보행으로 잡히는지 smoke 검증|
|`scripts/build_energy_site_platform_action_queue.py`|G3~G12 플랫폼 action queue와 보조 작업팩, dry-run/import 명령 생성|
|`scripts/build_energy_site_platform_action_preflight.py`|action queue 결과양식의 필수값·증빙·빈양식 상태를 사전 점검|
|`scripts/build_energy_site_external_workpack_manifest.py`|외부 작업팩 manifest와 운영자 실행 경로를 JSON/Markdown으로 생성|
|`scripts/build_energy_site_external_dependency_blockers.py`|100% 실패 Gate별 외부 원천 의존 blocker와 open count 산정|
|`scripts/build_auction_provider_secure_access_preflight.py`|인포케어·옥션원 등 경매 Provider 계정/세션 준비상태와 ID/PW 별칭을 비밀번호 미저장 원칙으로 점검|
|`scripts/smoke_auction_provider_secure_access_preflight.py`|경매 Provider 계정 마커는 허용하고 비밀번호 환경변수는 차단하는지 smoke 검증|
|`scripts/build_energy_site_auction_provider_session_launcher.py`|비밀번호 저장 없이 경매 Provider 검색팩·결과양식·세션 마커·strict import 명령을 provider+gate 단위 실행팩으로 묶음|
|`scripts/build_energy_site_auction_provider_browser_workboard.py`|경매 세션 실행팩을 시설 행 단위 브라우저 검색 작업보드 CSV/HTML/API 테이블로 전개하고 복수 `--gate-id`와 `--per-gate-total-limit`로 G7/G8 통합 생성 지원|
|`scripts/build_energy_site_auction_first_run_priority_pack.py`|G7/G8 법원 사건번호 보정과 Provider 조회를 첫 실행 우선순위 CSV/HTML/DB 테이블로 묶음|
|`scripts/run_auction_first_run_result_pipeline.py`|경매 1차 결과 템플릿을 adapter dry-run/import 명령으로 연결하고 빈 입력을 차단|
|`scripts/smoke_auction_first_run_result_pipeline.py`|경매 1차 결과 템플릿이 빈 상태일 때 import 명령을 만들지 않는지 smoke 검증|
|`scripts/import_auction_provider_browser_workboard_results.py`|브라우저 작업보드 결과 입력 CSV를 G7/G8 strict import-ready CSV와 preflight 테이블로 변환하고 실행일 기준 dry-run/import 보고서명 생성|
|`scripts/smoke_auction_browser_workboard_result_adapter.py`|경매 작업보드 결과 어댑터가 기존 G7/G8 importer 검증을 통과하는지 smoke 검증|
|`scripts/audit_energy_site_auction_case_no_sources.py`|DB/대법원/온비드 원천에서 법원 사건번호와 provider 관리번호를 분리 감사|
|`scripts/export_energy_site_auction_case_resolution_pack.py`|과거경매 provider 관리번호를 법원 사건번호로 역조회하기 위한 queue/result template 생성|
|`scripts/smoke_auction_case_resolution_pack_export.py`|과거경매 보정팩이 provider 관리번호를 `case_no`로 오인하지 않는지 smoke 검증|
|`scripts/audit_operational_duckdb_lock_blockers.py`|운영 DuckDB 직접 참조 프로세스를 서비스/스냅샷/unsafe reader로 분리 감사|
|`scripts/extract_energy_site_storage_from_raw_text.py`|KOGAS LCNG 원문 주요설비에서 저장탱크·저장용기 용량 후보만 엄격 추출|
|`scripts/build_energy_site_storage_uplift_candidates.py`|저장량 확정값·원문 저장량 후보·설비·원천필요 상태를 분리해 후보 테이블 재생성|
|`scripts/run_energy_site_platform_qa_suite.py`|G15 플랫폼 자동 QA suite 실행 및 DB/API/UI/코드 계약 검증|
|`scripts/build_energy_site_platform_completion_gates.py`|G0~G15 100% 완료 게이트 coverage 산정 및 DB snapshot 기록|
|`scripts/seed_service_token.py`|서비스 인증 토큰 생성/갱신|
|`scripts/backup_duckdb.py`|DuckDB 파일 백업 및 백업 이력 기록|
|`scripts/restore_duckdb.py`|DuckDB 백업 파일 복구|
|`scripts/smoke_service_readiness.py`|healthz/readyz/지도/검색/감사 API smoke test|
|`scripts/run_service_refresh.py`|좌표 품질, 정밀도 품질, 서비스 마트 갱신 파이프라인 래퍼|
|`scripts/smoke_commercial_ops.py`|토큰/약관/반출승인/모니터/라이선스 상용 운영 API smoke test|
|`scripts/run_restore_rehearsal.py`|백업 파일 복구 리허설 및 결과 기록|
|`scripts/monitor_service_readiness.py`|서비스 readiness 모니터링 및 장애 이벤트 기록|
|`scripts/build_license_gate_report.py`|라이선스 게이트 Markdown 보고서 생성|
|`scripts/update_license_gates_from_manifest.py`|라이선스 증빙 manifest 검증 및 DB 게이트 반영|
|`scripts/run_final_launch_gate_checks.py`|최종 상용 출시 게이트 자동 점검 및 DB 기록|
|`scripts/build_final_launch_approval_pack.py`|최종 출시 게이트 보고서와 승인팩 Markdown 생성|
|`scripts/run_24h_monitor_rehearsal.py`|장시간 운영 모니터링 리허설 실행 및 결과 기록|
|`scripts/validate_duckdb_backup.py`|DuckDB 백업 파일 hash/필수 테이블/행 수 검증 및 이력 기록|
|`scripts/run_cold_duckdb_backup.ps1`|서비스 중지 후 DuckDB cold backup/검증/재기동 실행|
|`scripts/agent-common-handoff.mjs`|공통 에이전트 작업 전/후 handoff 상태 JSON 점검|
|`scripts/start_service_server.ps1`|인증 필수 모드 API 서버 시작|
|`scripts/stop_service_server.ps1`|PID 파일 기반 API 서버 종료|
|`scripts/promote_service_auth_required.ps1`|인증 필수 운영 모드 전환 dry-run/apply 스크립트|
|`scripts/rollback_service_auth_optional.ps1`|인증 선택 모드 롤백 dry-run/apply 스크립트|
|`scripts/register_backup_task.ps1`|Windows 백업 작업 등록|
|`scripts/register_service_task.ps1`|Windows 서비스 시작 작업 등록|
