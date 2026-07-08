# Session 24 API Reliability WBS 및 실행 완료 보고

- 작성일: 2026-07-04
- 프로젝트 루트: `F:\NPL전례\avm_project`
- 서버: `NPL AVM FastAPI`
- 검증 URL: `http://127.0.0.1:8000/`
- 상세명세서: `SESSION_24_API_RELIABILITY_DETAILED_SPEC_20260704.md`
- 최종 판정: **PASS**

## 1. 작업 요약

이번 작업은 `/docs`에서 검토 가능한 API 계약을 보강하고, 한국어 요청과 빈 비교사례 응답을 라이브 테스트로 고정하는 작업이다. 모델 정확도나 외부 API 수집을 확장하지 않고, 현재 실행 중인 FastAPI 서버의 응답 신뢰성을 높이는 범위로 제한했다.

## 2. 초기 테스트 결과

`scripts/session24_api_live_smoke.py`를 먼저 작성한 뒤 현재 서버에 실행했다.

초기 결과:

| 검사 | 결과 | 내용 |
|---|---|---|
| root | PASS | `/` 200, `status=ok` |
| OpenAPI 응답 모델 | FAIL | 6개 GET endpoint response schema 비어 있음 |
| precedents UTF-8 | PASS | `sido=경기도` 조회 3건 |
| auction stats UTF-8 | PASS | `property_type=아파트`, `sido=경기도` 통계 1그룹 |
| estimate 0건 진단 | FAIL | `diagnostics=null` |
| RAG health degraded 계약 | FAIL | `disabled_services` 없음 |

초기 실패는 API 구현 오류 2건과 테스트 수집 설정 오류 1건으로 분류했다.

## 3. 수정 내역

| 파일 | 수정 내용 |
|---|---|
| `app/main.py` | `/` root 응답 모델 `RootResponse` 추가 |
| `app/api/routes.py` | `/precedents`, `/auction-stats`, `/properties/{property_serial}`, `/comparable-sales` 응답 모델 추가 |
| `app/api/routes.py` | `AVMResponse.diagnostics` 추가 |
| `app/avm/engine.py` | 비교사례 0건 시 `NO_COMPARABLES` 진단 생성 |
| `app/api/routes_rag.py` | `/api/v4/health`에 `disabled_services`, `safe_to_use_for_pricing`, `warnings` 추가 |
| `scripts/session24_api_live_smoke.py` | 라이브 UTF-8 API 스모크 하네스 추가 |
| `pytest.ini` | pytest 수집 범위를 `tests/`로 고정 |
| `results/session24_api_live_smoke_20260704.json` | 최종 라이브 스모크 증거 저장 |
| `results/session24_api_live_smoke_20260704.md` | 최종 라이브 스모크 요약 저장 |

## 4. 오류 및 조치

| 오류 | 원인 | 조치 | 결과 |
|---|---|---|---|
| OpenAPI schema 누락 | response_model 미지정 GET endpoint | Pydantic response model 추가 | PASS |
| 비교사례 0건 원인 불명 | `AVMResult`에 진단 필드 없음 | probe count/reason code 추가 | PASS |
| RAG degraded 설명 부족 | health 응답이 `status/services`만 반환 | disabled service와 pricing safety 명시 | PASS |
| 전체 pytest 실행 실패 | `scripts/test_*.py` 수동 스크립트까지 수집 | `pytest.ini`로 `tests/`만 수집 | PASS |

## 5. 최종 테스트 결과

| 테스트 | 명령 | 결과 |
|---|---|---|
| Syntax 검증 | `python -m py_compile app\avm\engine.py app\api\routes.py app\api\routes_rag.py app\main.py scripts\session24_api_live_smoke.py` | PASS |
| 단위 테스트 | `python -m pytest` | PASS, `4 passed in 7.00s` |
| 라이브 스모크 | `python scripts\session24_api_live_smoke.py --base-url http://127.0.0.1:8000` | PASS, 6/6 |

최종 라이브 스모크 주요 증거:

| 항목 | 값 |
|---|---|
| OpenAPI missing schema | `[]` |
| `/api/v1/precedents` 샘플 | 3건 |
| `/api/v1/auction-stats` 샘플 | 1그룹 |
| 0건 진단 status | `NO_COMPARABLES` |
| 0건 진단 reason | `NO_SOURCE_BACKED_COMPARABLES` |
| 화성시 아파트 property 후보 | 27건 |
| appraisal 후보 | 0건 |
| transaction 후보 | 0건 |
| RAG health | `degraded` |
| disabled services | `milvus`, `openai` |

## 6. WBS

| WBS | 작업 | 산출물 | 상태 | 검증 |
|---|---|---|---|---|
| 1.0 | 상세명세 작성 | `SESSION_24_API_RELIABILITY_DETAILED_SPEC_20260704.md` | 완료 | 파일 저장 |
| 2.0 | 라이브 스모크 하네스 작성 | `scripts/session24_api_live_smoke.py` | 완료 | py_compile PASS |
| 3.0 | 초기 실패 재현 | `results/session24_api_live_smoke_20260704.json` | 완료 | FAIL 3건 확인 |
| 4.0 | OpenAPI 응답 모델 보강 | `app/main.py`, `app/api/routes.py`, `app/api/routes_rag.py` | 완료 | missing schema `[]` |
| 5.0 | 비교사례 0건 진단 추가 | `app/avm/engine.py`, `app/api/routes.py` | 완료 | `NO_COMPARABLES` 반환 |
| 6.0 | RAG degraded 계약 명시 | `app/api/routes_rag.py` | 완료 | disabled services 반환 |
| 7.0 | pytest 수집 오류 수정 | `pytest.ini` | 완료 | `4 passed` |
| 8.0 | 최종 회귀 검증 | JSON/MD smoke 결과 | 완료 | 라이브 스모크 PASS |
| 9.0 | WBS/완료보고 | 본 문서 | 완료 | 보고서 저장 |

## 7. 남은 한계

- `/api/v4/health`는 현재 `degraded`가 정상적인 정직한 상태다. Milvus와 OpenAI가 비활성이라 RAG 기반 가격 설명을 고객 산출물로 사용하면 안 된다.
- `safe_to_use_for_pricing=false`는 blocker 해소 전까지 유지되어야 한다.
- VWorld 개발키는 이번 작업에서 저장하거나 호출하지 않았다. 외부 API 연동은 별도 runtime-only 절차로 진행해야 한다.
- 작업 전부터 작업트리에 다수의 수정/미추적 파일이 있었다. 이번 보고의 완료 범위는 위 수정 파일과 테스트 산출물로 한정한다.

## 8. 다음 작업 제안

1. `/api/v1/avm/estimate`에서 `NO_SOURCE_BACKED_COMPARABLES`가 나온 지역/유형을 기준으로 비교사례 보강 큐를 만든다.
2. Milvus/OpenAI 기동 절차를 별도 smoke로 분리해 `/api/v4/health.safe_to_use_for_pricing=true` 전환 조건을 만든다.
3. Pebble5 evidence-gated 트랙의 P1 작업인 RTMS 채널 배선을 별도 명세/WBS로 시작한다.

