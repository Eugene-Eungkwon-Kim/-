# API Key Pilot Test Report

작성일: 2026-07-04  
대상: NPL AVM 실거래 데이터 수집 파이프라인  
키 처리: 사용자 제공 개발키는 런타임 환경변수로만 사용했고, 파일에는 저장하지 않음

## 1. 수행 작업

1. `scripts/fetch_transactions_parallel.py` 런타임 방어 보강
   - placeholder API 키 검사 강화
   - `KOREA_API_KEY`, `RTMS_SERVICE_KEY`, `DATA_GO_KR_SERVICE_KEY`, `PUBLIC_DATA_SERVICE_KEY` 환경변수 인식
   - API 실패 시 오류 건수 집계
   - API 실패 시 checkpoint 완료 처리 방지
   - 최종 성공률 계산 오류 수정

2. `app/integrations/korea_api.py` 최신 endpoint 반영
   - 기존: `http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest`
   - 변경: `https://apis.data.go.kr/1613000`
   - 아파트/연립다세대/오피스텔 매매 endpoint를 기존 AVM RTMS 파이프라인과 동일한 패턴으로 교체
   - 요청 오류 로그에서 `serviceKey` 마스킹
   - 연결 실패/XML 파싱 실패/API 오류 응답을 빈 리스트가 아니라 예외로 처리

## 2. 검증 결과

### 2.1 문법 검증

명령:

```powershell
python -m py_compile app/integrations/korea_api.py scripts/fetch_transactions_parallel.py
```

결과: PASS

### 2.2 접속성 확인

- `https://www.data.go.kr`: 접속 가능
- `http://openapi.molit.go.kr`: 접속 실패
- `https://openapi.molit.go.kr`: 접속 실패
- `https://apis.data.go.kr`: host 접속 가능

판정: 기존 `openapi.molit.go.kr` endpoint는 현재 실행 경로에서 사용할 수 없고, `apis.data.go.kr/1613000` 계열로 전환하는 것이 맞음.

### 2.3 Pilot API 호출

대상:

- SGG: `41590`
- 연월: `2026-06`
- 유형: 아파트, 연립다세대, 오피스텔
- workers: 1

결과:

| 유형 | 결과 |
|---|---|
| 아파트 | 401 Unauthorized |
| 연립다세대 | 401 Unauthorized |
| 오피스텔 | 401 Unauthorized |

집계:

- inserted: 0
- skipped: 0
- errors: 3
- checkpoint: 실패로 인해 신규 완료 checkpoint 미생성

판정: URL/네트워크 문제는 해결됐으나, 현재 개발키는 해당 RTMS 서비스에 대한 인증/활용권한이 없음.

## 3. 기존 실거래 데이터 확인

API 신규 수집은 401로 차단됐지만, 로컬에는 이미 사용 가능한 RTMS 실거래 데이터가 존재함.

### 3.1 RTMS fact SQLite

파일: `F:\loan4u_avm_data\loan4u_working_db\db\rtms_transaction_fact.sqlite`

실측:

- row count: 799,075
- date range: 2025-05-01 ~ 2026-06-29

서비스별 row count:

| source_service | rows |
|---|---:|
| apt_rent | 282,874 |
| apt_trade | 223,533 |
| land_trade | 152,007 |
| rh_rent | 57,039 |
| rh_trade | 22,326 |
| commercial_trade | 21,956 |
| single_house_trade | 17,432 |
| presale_right_trade | 17,099 |
| factory_warehouse_trade | 4,809 |

### 3.2 RTMS comparable mart DuckDB

파일: `F:\loan4u_avm_data\loan4u_working_db\db\loan4u_rtms_comparable_mart.duckdb`

실측:

- table: `rtms_comparable_mart`
- row count: 158,780

## 4. 결론

현재 개발키는 RTMS 신규 API 수집에는 아직 사용할 수 없다. data.go.kr에서 아래 서비스들의 활용신청/승인 상태 확인이 필요하다.

- 국토교통부_아파트 매매 실거래가 자료
- 국토교통부_연립다세대 매매 실거래가 자료
- 국토교통부_오피스텔 매매 실거래가 자료

다만 기존 로컬 RTMS fact 799,075건과 비교사례 마트 158,780건이 있으므로, 키 승인 전에도 모델 재학습/검증 작업은 기존 데이터 기반으로 진행 가능하다.

## 5. 다음 작업 순서

1. data.go.kr에서 개발키의 RTMS 서비스 활용신청/승인 상태 확인
2. 승인 후 동일 Pilot 재실행
3. 승인 전에는 `rtms_transaction_fact.sqlite` 및 `loan4u_rtms_comparable_mart.duckdb` 기반 재학습 데이터셋 생성으로 우회 진행
4. 실패 테스트 checkpoint `data/pilot_api_key_test_checkpoint.json`은 잘못된 endpoint 시도에서 생성된 테스트 산출물이므로 실제 수집 재개에 사용 금지
