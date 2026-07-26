# Session 24 다음 진행 예정 작업 상세명세서 및 WBS

- 작성일: 2026-07-04
- 대상 서버: NPL AVM FastAPI (`http://127.0.0.1:8000`)
- 현재 브라우저 위치: `/docs#/default/get_precedents_api_v1_precedents_get`
- 문서 목적: 다음 개발 착수 전 작업 범위, 산출물, 검증 게이트, WBS를 확정한다.
- 중요 경계: 2026-07-07 제품 배포 판단 기준은 Pebble5 evidence-gated 트랙이다. 본 문서는 현재 실행 가능한 NPL FastAPI 서버의 검증/보강 작업 계획이며, Pebble5 제품 게이트를 대체하지 않는다.

---

## 1. 현황 검토 요약

### 1.1 실측 서버 상태

| 항목 | 결과 |
|---|---|
| 루트 헬스 | `GET /` → `{"status":"ok","docs":"/docs"}` |
| Swagger/OpenAPI | `/openapi.json` 응답 확인 |
| 실행 포트 | `8000` LISTENING |
| 실행 PID | `12264` |
| RAG 헬스 | `/api/v4/health` → `degraded` (`p6_model=true`, `milvus=false`, `openai=false`) |

### 1.2 DB 실측 카운트

| 테이블 | 건수 |
|---|---:|
| deals | 14 |
| properties | 2,694 |
| appraisals | 2,346 |
| auctions | 904 |
| comparable_sales | 357 |

### 1.3 API 샘플 응답

| 엔드포인트 | 샘플 | 결과 | 시사점 |
|---|---|---|---|
| `/api/v1/precedents` | `sido=경기도&limit=3` | 3건 반환 | 전례 조회는 기본 동작 가능 |
| `/api/v1/auction-stats` | `property_type=아파트&sido=경기도` | 낙찰통계 반환 | 경매 통계 기본 동작 가능 |
| `/api/v1/avm/estimate` | 경기도/화성시/아파트 | `LOW`, 비교사례 0건 | 빈 결과 진단/폴백 필요 |
| `/api/v4/health` | 없음 | `degraded` | RAG 의존성은 아직 배포 가능 상태 아님 |

### 1.4 기존 문서와의 충돌 검토

`SESSION_22_COMPLETION_REPORT.md`는 토지 지번 100% 마스킹으로 토지 정밀 매칭을 NO-GO로 판정했다. 반면 `SESSION_23_DETAILED_SPEC_WBS.md`는 PNU 복원으로 GO 전환을 가정한다. 이 가정은 아직 실측 검증 전이므로 다음 작업에서 바로 개발하지 않고, 선행 feasibility gate로 분리한다.

---

## 2. 다음 작업 목표

### 목표명

**Session 24: NPL FastAPI 실사용 검증 하네스 및 API 신뢰성 보강**

### 목표

현재 실행 가능한 FastAPI 서버를 기준으로, Swagger에서 보이는 API가 실제 샘플 질의·한글 파라미터·빈 결과·RAG degraded 상태를 정직하게 처리하는지 검증하고, 고객/운영자가 오해하지 않도록 응답 스키마와 진단 산출물을 보강한다.

### 비목표

- Pebble5 evidence-gated 제품 트랙의 P1 구현은 본 작업 범위가 아니다.
- Milvus/OpenAI 키 또는 Docker daemon을 강제로 요구하지 않는다.
- 토지 PNU 복원은 본 작업에서 구현하지 않는다. 먼저 가능성 검증 게이트만 설계한다.
- 합성/부분표본 성능을 제품 성능으로 포장하지 않는다.

---

## 3. 상세명세

### S24-R01. API 라이브 스모크 하네스 작성

| 항목 | 명세 |
|---|---|
| 목적 | Swagger 수동 클릭이 아니라 재실행 가능한 스모크로 API 상태를 증명 |
| 대상 | `/`, `/openapi.json`, `/api/v1/precedents`, `/api/v1/auction-stats`, `/api/v1/avm/estimate`, `/api/v4/health` |
| 신규 산출물 | `scripts/session24_api_live_smoke.py` |
| 보고 산출물 | `results/session24_api_live_smoke_20260704.json`, `.md` |
| 핵심 요구 | 한글 쿼리는 URL encoding을 강제하고, POST JSON은 UTF-8로 전송 |
| 실패 처리 | HTTP 오류, JSON 파싱 오류, 빈 결과를 별도 reason code로 기록 |

### S24-R02. OpenAPI 응답 스키마 정리

| 항목 | 명세 |
|---|---|
| 문제 | GET 계열 일부 응답 스키마가 `{}`로 노출되어 Swagger/클라이언트 계약이 약함 |
| 대상 | `/precedents`, `/auction-stats`, `/properties/{serial}`, `/comparable-sales`, `/api/v4/health` |
| 변경 | Pydantic response model 추가 또는 최소 response shape 문서화 |
| 완료 기준 | `/openapi.json`에서 주요 응답 schema가 빈 객체가 아니어야 함 |
| 주의 | 기능 로직 변경 없이 계약 강화부터 수행 |

### S24-R03. 빈 비교사례 진단 응답 개선

| 항목 | 명세 |
|---|---|
| 문제 | `/api/v1/avm/estimate`가 비교사례 0건이면 `LOW`만 반환하고 왜 비었는지 알 수 없음 |
| 변경 | `diagnostics` 필드 또는 내부 QA용 reason code 추가 |
| 예시 reason | `NO_EXACT_PROPERTY_TYPE_MATCH`, `NO_REGION_MATCH`, `AREA_FILTER_TOO_STRICT`, `FALLBACK_NOT_APPLIED` |
| 폴백 원칙 | 자동 산출가를 억지로 만들지 않고, broadened query 후보 수만 내부 진단으로 제공 |
| 고객 출력 | 비교사례 0건이면 가격 값은 계속 null 허용 |

### S24-R04. RAG degraded 상태의 운영 경계 명시

| 항목 | 명세 |
|---|---|
| 현재 | `p6_model=true`, `milvus=false`, `openai=false` |
| 변경 | `/api/v4/health`에 `status`, `disabled_services`, `safe_to_use_for_pricing` 명시 |
| 원칙 | RAG 설명/유사사례가 꺼진 상태를 정상 성능으로 오해하지 않게 함 |
| 완료 기준 | RAG 의존성 미구성 시에도 API는 죽지 않고 degraded를 명확히 반환 |

### S24-R05. 토지 PNU 복원 feasibility gate 설계

| 항목 | 명세 |
|---|---|
| 배경 | Session 22 NO-GO와 Session 23 GO 가정 충돌 |
| 작업 | 20건 이하 소표본으로 PNU 복원이 실제 가능한지 증명하는 gate만 설계 |
| 금지 | 전체 152,007건 배치 실행 금지 |
| 완료 기준 | API/CSV 원천, 호출 제한, 성공률, 실패 reason을 보고서로 남김 |
| 판정 | `GO_TO_BATCH`, `PARTIAL_ONLY`, `NO_GO_CONFIRMED` 중 하나 |

---

## 4. 산출물 목록

| 산출물 | 경로 | 설명 |
|---|---|---|
| API 스모크 스크립트 | `scripts/session24_api_live_smoke.py` | 서버 상태 재현 검증 |
| API 스모크 JSON | `results/session24_api_live_smoke_20260704.json` | 기계 판독용 결과 |
| API 스모크 보고서 | `results/session24_api_live_smoke_20260704.md` | 사람 검토용 결과 |
| OpenAPI 계약 보강 패치 | `app/api/routes.py`, `app/api/routes_rag.py` | response model 추가 |
| 빈 결과 진단 패치 | `app/avm/engine.py`, `app/api/routes.py` | 비교사례 0건 reason 기록 |
| RAG health 보강 패치 | `app/api/routes_rag.py` | degraded 경계 명확화 |
| 토지 feasibility 계획서 | `results/session24_land_pnu_feasibility_gate_20260704.md` | Session 23 가정 검증용 게이트 |

---

## 5. WBS

| ID | 작업 | 상세 | 산출물 | 예상 | 의존 | 완료 기준 |
|---|---|---|---|---:|---|---|
| S24-0 | 기준 상태 스냅샷 | 현재 서버 PID, DB 카운트, OpenAPI 엔드포인트 기록 | smoke baseline section | 0.3h | 없음 | baseline JSON 저장 |
| S24-1 | API 라이브 스모크 작성 | UTF-8 GET/POST, timeout, reason code 포함 | smoke script | 1.0h | S24-0 | 6개 엔드포인트 실행 |
| S24-2 | 스모크 샘플 세트 확정 | 경기도 전례, 아파트 통계, 빈 결과 케이스, RAG degraded 케이스 | smoke fixtures | 0.5h | S24-1 | PASS/WARN/FAIL 분류 가능 |
| S24-3 | OpenAPI response model 보강 | 빈 `{}` schema 제거, Pydantic 모델 추가 | routes patch | 1.5h | S24-1 | openapi schema diff PASS |
| S24-4 | 빈 비교사례 진단 추가 | `estimate` 0건 시 reason code와 내부 후보 수 기록 | API patch | 2.0h | S24-2 | 빈 결과가 원인 설명 포함 |
| S24-5 | RAG degraded health 보강 | disabled service와 가격 사용 가능 여부 명시 | health patch | 1.0h | S24-1 | `/api/v4/health` 명확화 |
| S24-6 | 회귀/샘플 테스트 | pytest + live smoke + OpenAPI JSON 검증 | test output | 1.0h | S24-3~5 | 테스트 PASS/WARN 기록 |
| S24-7 | 토지 PNU feasibility gate 문서화 | 전체 배치 전 20건 이하 검증 게이트 설계 | feasibility report | 1.0h | S24-0 | GO/PARTIAL/NO-GO 판정 기준 확정 |
| S24-8 | 완료 보고 | 변경 파일, 실측 결과, 잔여 blocker 보고 | completion report | 0.5h | S24-6~7 | 보고서 저장 및 검토 |

### 총 예상

- 최소 개발/검증: 7.8h
- 버퍼 포함: 1일
- RAG/Milvus 실제 연결 또는 Docker daemon 복구는 별도 작업으로 분리

---

## 6. 테스트 계획

| 테스트 | 명령/방식 | 기대 |
|---|---|---|
| Python compile | `python -m py_compile app/api/routes.py app/api/routes_rag.py scripts/session24_api_live_smoke.py` | PASS |
| Unit/regression | `pytest -q` | 기존 테스트 유지 |
| Root smoke | `GET /` | 200 |
| OpenAPI smoke | `GET /openapi.json` | 주요 response schema 존재 |
| Precedents smoke | `GET /api/v1/precedents?sido=경기도&limit=3` | 1건 이상 또는 명확한 WARN |
| Auction stats smoke | `GET /api/v1/auction-stats?property_type=아파트&sido=경기도` | stats shape 반환 |
| Estimate empty diagnostic | `POST /api/v1/avm/estimate` | 비교사례 0건이면 reason 포함 |
| RAG health | `GET /api/v4/health` | degraded 이유 명확 |

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 한글 URL/PowerShell 인코딩 오류 | Swagger/CLI 샘플 검증 실패 | smoke harness에서 `urllib.parse.urlencode` 사용 |
| DB 데이터 품질 편차 | 빈 결과 또는 낮은 신뢰도 빈발 | 결과를 억지 산출하지 않고 reason code로 분리 |
| RAG 의존성 미구성 | v4 기능 과대평가 위험 | degraded를 정상 상태와 분리 |
| Session 23 PNU 복원 가정 과대 | 대량 작업 낭비 | 20건 이하 feasibility gate 선행 |
| Docker daemon 미실행 | Compose 서버 검증 지연 | FastAPI 작업과 분리, Docker 복구는 별도 운영 작업 |

---

## 8. 검토 판정

### 판정: CONDITIONAL GO

다음 개발은 S24-1부터 S24-6까지 진행 가능하다. 단, 다음 조건을 지킨다.

1. 고객-facing 가격 산출 정확도 개선으로 포장하지 않는다.
2. 비교사례 0건 케이스는 가격을 강제로 만들지 않는다.
3. RAG/Milvus/OpenAI 미구성 상태는 `degraded`로 계속 노출한다.
4. 토지 PNU 복원은 전체 배치가 아니라 feasibility gate부터 수행한다.
5. Pebble5 evidence-gated 제품 트랙과 NPL FastAPI 검증 서버를 혼동하지 않는다.

### 즉시 착수 순서

1. `scripts/session24_api_live_smoke.py` 작성
2. 스모크 실행 및 JSON/MD 결과 저장
3. OpenAPI response model 보강
4. 빈 비교사례 진단 응답 추가
5. RAG health degraded 명확화
6. 테스트 및 완료 보고

---

## 9. 승인 요청 항목

개발 착수 전 확인할 결정은 하나다.

- Session 24의 1차 목표를 **API 신뢰성 보강/스모크 하네스**로 확정할지 여부

확정되면 위 WBS의 S24-1부터 개발을 시작한다.
