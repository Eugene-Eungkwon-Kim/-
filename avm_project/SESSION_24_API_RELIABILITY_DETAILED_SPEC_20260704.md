# Session 24 API Reliability 상세명세서

- 작성일: 2026-07-04
- 대상 서버: `NPL AVM FastAPI`
- 실행 기준 URL: `http://127.0.0.1:8000/`
- 대상 루트: `F:\NPL전례\avm_project`
- 작성 목적: 브라우저 `/docs`에서 확인 가능한 API 계약과 실제 한국어 요청 동작을 테스트로 고정하고, 비교사례 0건 및 RAG degraded 상태를 과장 없이 설명하도록 보강한다.

## 1. 배경

현재 FastAPI 서버는 기동 가능하고 `/`, `/docs`, `/api/v1`, `/api/v4/health` 접근이 가능하다. 다만 다음 사용성 결함이 남아 있다.

1. 일부 GET API의 OpenAPI 응답 스키마가 비어 있어 `/docs`에서 응답 구조를 검토하기 어렵다.
2. `POST /api/v1/avm/estimate`가 비교사례 0건일 때 `estimated_value=null`만 반환하고, 어떤 필터에서 막혔는지 설명하지 않는다.
3. `/api/v4/health`는 `degraded` 상태를 반환하지만, 어떤 서비스가 비활성인지와 가격 산정용으로 안전한지 여부를 명시하지 않는다.
4. PowerShell/curl 조합에서는 한국어 쿼리와 JSON body 인코딩이 흔들릴 수 있어 Python UTF-8 기반 라이브 스모크가 필요하다.

## 2. 작업 목표

이번 작업은 제품 로직 확장이 아니라 API 신뢰성 보강이다.

- API 계약을 OpenAPI에 명시한다.
- 한국어 파라미터 요청을 UTF-8로 실측 검증한다.
- 비교사례 0건 응답에 원인 진단 정보를 추가한다.
- RAG health degraded 상태를 명시적으로 해석 가능한 응답으로 바꾼다.
- 모든 변경은 라이브 서버 스모크, Python 컴파일, 기존 pytest로 확인한다.

## 3. 범위 포함

| 구분 | 작업 | 산출물 |
|---|---|---|
| 상세명세 | 현재 API 신뢰성 결함과 수정 기준 정의 | 본 문서 |
| 테스트 하네스 | 라이브 서버 대상 UTF-8 API 스모크 작성 | `scripts/session24_api_live_smoke.py` |
| API 계약 | GET 응답 모델 및 health 응답 모델 추가 | `app/api/routes.py`, `app/api/routes_rag.py`, `app/main.py` |
| 진단 응답 | 비교사례 0건 시 reason code/probe count 반환 | `app/avm/engine.py`, `app/api/routes.py` |
| 검증 결과 | JSON/Markdown 테스트 결과 저장 | `results/session24_api_live_smoke_20260704.*` |
| WBS/보고 | 실제 실행 결과 기반 WBS 및 완료 보고 | `SESSION_24_API_RELIABILITY_WBS_EXECUTION_REPORT_20260704.md` |

## 4. 범위 제외

- VWorld 개발키 저장 또는 외부 API 호출 자동화
- Milvus/OpenAI/RAG 서비스 기동
- Docker daemon 문제 해결
- Pebble5 evidence-gated 트랙의 RTMS 채널 배선
- PNU 복원 또는 전국 단위 batch 수집
- 모델 정확도 개선 또는 신규 학습

## 5. 기능 명세

### 5.1 라이브 스모크 하네스

하네스는 표준 라이브러리만 사용한다.

- 기본 URL: `http://127.0.0.1:8000`
- 출력:
  - `results/session24_api_live_smoke_20260704.json`
  - `results/session24_api_live_smoke_20260704.md`
- 필수 검사:
  - `GET /` 응답 200 및 `status=ok`
  - `GET /openapi.json` 응답 모델 존재 여부
  - `GET /api/v1/precedents?sido=경기도&limit=3`
  - `GET /api/v1/auction-stats?property_type=아파트&sido=경기도`
  - `POST /api/v1/avm/estimate` 한국어 JSON body
  - `GET /api/v4/health`

### 5.2 OpenAPI 응답 모델

다음 엔드포인트는 빈 응답 스키마가 없어야 한다.

- `/`
- `/api/v1/precedents`
- `/api/v1/auction-stats`
- `/api/v1/properties/{property_serial}`
- `/api/v1/comparable-sales`
- `/api/v4/health`

### 5.3 비교사례 0건 진단

`POST /api/v1/avm/estimate`에서 `comparable_count=0`이면 `diagnostics`를 반환한다.

필수 필드:

- `status`: `NO_COMPARABLES`
- `reason_codes`: 원인 코드 목록
- `query`: 입력 필터 요약
- `probe_counts`: 필터 단계별 후보 수
- `customer_safe`: 고객 산출물 사용 가능 여부. 0건이면 `false`.

원인 코드:

- `NO_SIDO_MATCH`
- `NO_SIGUNGU_MATCH`
- `NO_PROPERTY_TYPE_MATCH`
- `NO_SOURCE_BACKED_COMPARABLES`
- `COMPARABLE_FILTERS_RETURNED_ZERO`

### 5.4 RAG health 응답

`GET /api/v4/health`는 기존 `status/services`에 더해 다음을 반환한다.

- `disabled_services`: 비활성 서비스 목록
- `safe_to_use_for_pricing`: 모든 서비스가 정상일 때만 `true`
- `warnings`: 사람이 읽을 수 있는 경고 코드 목록

현재 Milvus/OpenAI가 비활성인 상태라면 `status=degraded`, `safe_to_use_for_pricing=false`가 정직한 응답이다.

## 6. 테스트 명세

| 테스트 | 명령 | 합격 기준 |
|---|---|---|
| 컴파일 | `python -m py_compile ...` | 대상 파일 syntax error 0건 |
| 기존 단위 테스트 | `python -m pytest -q` | 기존 테스트 PASS |
| 라이브 스모크 | `python scripts/session24_api_live_smoke.py --base-url http://127.0.0.1:8000` | 전체 상태 PASS |
| OpenAPI 검사 | 라이브 스모크 내부 | 대상 엔드포인트 응답 스키마 비어 있지 않음 |
| 한국어 요청 | 라이브 스모크 내부 | URL-encoded query/UTF-8 JSON body 정상 처리 |
| 0건 진단 | 라이브 스모크 내부 | `diagnostics.status=NO_COMPARABLES` |
| RAG degraded | 라이브 스모크 내부 | disabled services와 pricing unsafe 명시 |

## 7. 완료 기준

- 상세명세서 저장 완료
- 코드 변경 후 syntax 검증 PASS
- 기존 pytest PASS
- 라이브 스모크 PASS
- 테스트 결과 JSON/Markdown 저장
- WBS/완료보고서 저장
- 남은 blocker를 과장 없이 명시

## 8. 위험 및 통제

| 위험 | 통제 |
|---|---|
| 실행 중인 uvicorn reload 지연 | 코드 변경 후 라이브 스모크 재시도 |
| 한국어 콘솔 출력 깨짐 | 파일은 UTF-8로 저장하고 검증은 JSON 필드 기준 수행 |
| OpenAPI 모델 추가로 Pydantic validation 실패 | Optional 필드와 dict 기반 상세 응답 모델 사용 |
| RAG degraded를 정상으로 오해 | `safe_to_use_for_pricing=false` 명시 |
| 외부 키 유출 | VWorld 키는 저장/로그/명령행에 사용하지 않음 |

