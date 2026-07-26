# Session 25 Draft Spec: Source-Backed Comparable Coverage v1

- 작성일: 2026-07-04
- 상태: Draft for review
- 대상 루트: `F:\NPL전례\avm_project`
- 선행 완료: Session 24 API Reliability PASS
- 근거 파일:
  - `results/session24_api_live_smoke_20260704.json`
  - `results/session25_planning_probe_20260704.json`

## 1. 문제 정의

Session 24에서 API 계약과 라이브 스모크는 PASS로 닫혔다. 그러나 실제 샘플 `경기도/화성시/아파트`는 비교사례 0건으로 남았다.

핵심 증거:

| 항목 | 값 |
|---|---:|
| properties | 2,694 |
| appraisals | 2,346 |
| auctions | 904 |
| comparable_sales | 357 |
| 경기도 화성시 property 후보 | 113 |
| 경기도 화성시 `%아파트%` 후보 | 27 |
| appraisal 후보 | 0 |
| transaction 후보 | 0 |

즉 서버는 정상이고 진단도 가능하지만, 산출 가능한 비교사례 채널이 빈다. 다음 작업은 모델을 복잡하게 하는 것이 아니라, 소스 기반 비교사례가 왜 비는지 구조화하고 채울 수 있는 경로를 만든다.

## 2. 초안 목표

**목표명**: Session 25 Source-Backed Comparable Coverage v1

목표:

1. `NO_SOURCE_BACKED_COMPARABLES` 발생 케이스를 배치로 수집한다.
2. 행정구역 표현 차이와 자산유형 substring 충돌을 분리한다.
3. 비교사례 채널 확장 전, 후보를 고객 산출물에 쓰지 않는 QA 큐로 만든다.
4. 통과한 후보만 `AVM estimate`의 비교사례 검색에 연결한다.

## 3. 범위 포함

| 구분 | 작업 |
|---|---|
| Coverage probe | 대표 지역/유형별 estimate 진단 배치 |
| District crosswalk | `화성시` ↔ `화성만세구/화성효행구` 같은 표현 차이 후보 추출 |
| Type taxonomy | `아파트`가 `아파트형공장`을 잡는 substring 문제 분리 |
| Candidate queue | 비교사례 후보를 검토용 CSV/JSON으로 생성 |
| Verifier | 후보 확장 전후 false-positive 방지 테스트 |
| API smoke | 기존 Session 24 smoke 유지 + coverage smoke 추가 |

## 4. 범위 제외

- VWorld 개발키 저장
- 외부 API 대량 호출
- Milvus/OpenAI 기동
- 가격 폴백을 억지로 생성
- 토지 PNU 대량 복원
- 고객 export 자동 생성

## 5. 상세 요구사항 초안

### S25-R01. Coverage Diagnostic Batch

입력:

- `data/npl_avm.db`
- 기존 `AVM estimate` 진단 로직
- 상위 property group 및 comparable_sales group

출력:

- `results/session25_coverage_diagnostic_20260704.json`
- `results/session25_coverage_diagnostic_20260704.md`

검사 항목:

- 지역/유형별 `sido_count`
- `sigungu_count`
- `property_type_count`
- `appraisal_candidate_count`
- `transaction_candidate_count`
- `reason_codes`

### S25-R02. District Crosswalk Candidate

문제 예시:

- properties: `경기도/화성시`
- comparable_sales: `경기도/화성만세구`, `경기도/화성효행구`

초안 접근:

- 문자열 prefix/contains 기반 후보를 만든다.
- 바로 매칭에 쓰지 않고 `candidate_only=true`로 저장한다.
- 사람이 검토 가능한 dictionary 초안을 만든다.

출력:

- `config/session25_sigungu_crosswalk_candidates.json`
- `results/session25_sigungu_crosswalk_report.md`

### S25-R03. Property Type Taxonomy

문제 예시:

- 요청: `아파트`
- 현재 필터: `Property.property_type.ilike("%아파트%")`
- 위험: `아파트형공장`, `공동주택아파트`, `20층 아파트`가 같은 계층으로 섞일 수 있음

초안 접근:

- 원문 `property_type_raw`를 보존한다.
- `property_type_class`를 별도로 부여한다.
- 최소 클래스:
  - `RESIDENTIAL_APARTMENT`
  - `MULTIFAMILY`
  - `OFFICETEL_RESIDENTIAL`
  - `OFFICETEL_NON_RESIDENTIAL`
  - `KNOWLEDGE_INDUSTRIAL_CENTER`
  - `FACTORY`
  - `RETAIL`
  - `LAND`
  - `OTHER`

출력:

- `config/session25_property_type_taxonomy.json`
- `results/session25_property_type_taxonomy_report.md`

### S25-R04. Candidate Queue

후보 큐 필드:

- `query_sido`
- `query_sigungu`
- `query_property_type`
- `candidate_source`
- `candidate_sido`
- `candidate_sigungu`
- `candidate_property_type`
- `crosswalk_rule`
- `type_rule`
- `evidence_count`
- `review_status`
- `customer_safe`

초기값:

- `review_status=NEEDS_REVIEW`
- `customer_safe=false`

출력:

- `results/session25_comparable_candidate_queue.csv`
- `results/session25_comparable_candidate_queue.json`

### S25-R05. Verifier

검증 항목:

- `아파트`가 `아파트형공장`으로 승격되지 않는다.
- 행정구역 crosswalk는 후보 큐에서는 허용되지만, 승인 전 estimate에는 반영되지 않는다.
- source-backed 후보 수가 늘어도 `customer_safe=false`인 후보는 고객 산출물로 나가지 않는다.
- Session 24 smoke 6/6을 유지한다.

출력:

- `scripts/session25_coverage_verifier.py`
- `results/session25_coverage_verifier_20260704.json`
- `results/session25_coverage_verifier_20260704.md`

## 6. 초안 WBS

| WBS | 작업 | 산출물 | 예상 |
|---|---|---|---:|
| 1.0 | Coverage diagnostic 배치 | diagnostic JSON/MD | 1.0h |
| 2.0 | 행정구역 crosswalk 후보 생성 | crosswalk candidates | 1.5h |
| 3.0 | 자산유형 taxonomy 초안 | taxonomy JSON/MD | 1.5h |
| 4.0 | 후보 큐 생성 | candidate queue CSV/JSON | 1.5h |
| 5.0 | verifier 작성 | verifier JSON/MD | 1.0h |
| 6.0 | API smoke 회귀 | Session 24 smoke 재실행 | 0.5h |
| 7.0 | 완료보고 | execution report | 0.5h |

예상 합계: 7.5h

## 7. 초안 완료 기준

- diagnostic 배치가 재실행 가능하다.
- crosswalk와 taxonomy가 파일로 저장된다.
- 고객 산출물 사용 가능 후보는 0건으로 시작한다.
- verifier가 false-positive 방지 조건을 확인한다.
- Session 24 API smoke가 계속 PASS다.

