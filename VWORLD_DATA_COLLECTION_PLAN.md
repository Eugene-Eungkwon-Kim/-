# VWorld 데이터 수집 상세 계획

**담당**: 개발자 1-2 (2명)  
**기간**: 2026-07-24 ~ 2026-08-14 (21일)  
**목표**: 14개 API 레이어 통합, SQLite/DuckDB 생성  

---

## 📋 API 키 및 환경 설정

### API 키 확정
```
VWorld API Key:    <REDACTED-환경변수 VWORLD_API_KEY 참조> ✓
data.go.kr Key:    <REDACTED-환경변수 DATAGOVKR_API_KEY 참조> ✓
주소승인키 (정보제공): <REDACTED-환경변수 JUSO_API_KEY_PROVIDE 참조> ✓
주소승인키 (정보):    <REDACTED-환경변수 JUSO_API_KEY_INFO 참조> ✓
```

### 환경 준비 체크리스트
- [ ] SQLite3 설치 확인
- [ ] DuckDB Python 라이브러리 설치
- [ ] requests/pandas 라이브러리 설치
- [ ] D:\loan4u_avm_data\vworld_wfs_multi_layer\ 디렉토리 생성
- [ ] Git 브랜치 생성: feature/vworld-integration

---

## 📅 주간 계획

### Week 1 (2026-07-24 ~ 07-30): Layer 1-7

#### Day 1-2 (07-24 ~ 07-25): 환경 구성 및 API 검증
```
담당: 모두 (2명)

□ Step 1: API 연결 검증
  - VWorld API 테스트 스크립트 작성
  - data.go.kr API 테스트
  - 각 엔드포인트 접속 확인
  
□ Step 2: 데이터베이스 스키마 설계
  - 14개 API별 컬럼 정의
  - SQLite 테이블 구조 설계
  - 기본키/외래키 관계도 작성
  
□ Step 3: 데이터 수집 파이프라인 구성
  - 공통 HTTP 클라이언트 작성
  - 에러 처리/재시도 로직
  - 로깅 시스템 구축

산출물:
  - vworld_api_connector.py (공통 모듈)
  - database_schema.sql (SQLite 스키마)
  - logging_config.json (로깅 설정)
```

#### Day 3-4 (07-26 ~ 07-27): Layer 1-3 (지리 정보)
```
담당: 개발자 1

Layer 1: search20 (검색 API 2.0)
- API: search?q=<query>&coord=<coord>
- 목표: 10,000개 부동산 객체
- 필드: id, name, address, lat, lon, type, price
- 진행도: □□□

Layer 2: geocoder20 (지오코더 API 2.0)
- API: geocode?query=<address>
- 목표: 좌표 정규화 (10,000건)
- 필드: address, lat, lon, level, accuracy
- 진행도: □□□

Layer 3: wms_wfs20_reference (WMS/WFS 참조)
- API: reference?layer=<name>
- 목표: 메타데이터 수집
- 필드: layer_name, layer_id, description, srs
- 진행도: □□□

데이터 검증:
  ✓ NaN 값 없음
  ✓ 좌표 범위 확인 (위도/경도)
  ✓ 주소 정규화

산출물:
  - layer1_search20.csv
  - layer2_geocoder20.csv
  - layer3_reference.csv
```

#### Day 5-6 (07-28 ~ 07-29): Layer 4-7 (건물 정보)
```
담당: 개발자 2

Layer 4: continuous_cadastral_map (연속지적도)
- API: cadastral?quad=<quad>
- 목표: 지적 필지 정보 (10,000건)
- 필드: quad_id, lot_number, area, owner, zoning
- 진행도: □□□

Layer 5: building_by_use (용도별 건물)
- API: building?use=<use>&area=<area>
- 목표: 용도 분류 (5,000건)
- 필드: building_id, use_code, use_name, count
- 진행도: □□□

Layer 6: gis_building_general (GIS 건물 일반)
- API: gis/building?extent=<extent>
- 목표: 건물 기하형 정보 (10,000건)
- 필드: building_id, geom, height, stories, material
- 진행도: □□□

Layer 7: gis_building_integrated (GIS 건물 통합)
- API: gis/integrated?id=<id>
- 목표: 건물 통합 정보 (5,000건)
- 필드: building_id, address, geom, attributes
- 진행도: □□□

데이터 검증:
  ✓ 중복 제거
  ✓ 기하 형태 검증
  ✓ 속성 일관성 확인

산출물:
  - layer4_cadastral_map.csv
  - layer5_building_by_use.csv
  - layer6_gis_building_general.csv
  - layer7_gis_building_integrated.csv
```

#### Day 7 (07-30): 주간 검증
```
□ 데이터 품질 체크
  - 누락값 확인
  - 범위 이상치 확인
  - 중복 데이터 제거
  
□ SQLite 임시 테이블에 로드
  - 각 CSV → SQLite 테이블 변환
  - 무결성 제약 검증
  
□ 주간 진도 보고
  - 7/14 API 완료 (50%)
  - 이슈 및 개선 사항 정리
```

---

### Week 2 (2026-07-31 ~ 08-06): Layer 8-14

#### Day 8-9 (07-31 ~ 08-01): Layer 8-10 (토지 정보)
```
담당: 개발자 1

Layer 8: land_characteristics (토지 특성)
- API: land/characteristics?lot=<lot>
- 목표: 토지 특성 (10,000건)
- 필드: lot_id, slope, soil_type, water_accessibility
- 진행도: □□□

Layer 9: land_use_plan (토지 이용계획)
- API: land/useplan?area=<area>
- 목표: 지역별 이용계획 (5,000건)
- 필드: area_id, plan_zone, height_limit, coverage_rate
- 진행도: □□□

Layer 10: land_right_register_list (대지권 등록)
- API: land/rights?lot=<lot>
- 목표: 대지권 정보 (3,000건)
- 필드: lot_id, right_type, owner, registration_date
- 진행도: □□□

산출물:
  - layer8_land_characteristics.csv
  - layer9_land_use_plan.csv
  - layer10_land_right_register.csv
```

#### Day 10-11 (08-02 ~ 08-03): Layer 11-14 (가격 정보)
```
담당: 개발자 2

Layer 11: apart_housing_price (공동주택가격)
- API: price/apart?area=<area>&period=<period>
- 목표: 공동주택 공시가격 (20,000건)
- 필드: apt_id, address, price_per_m2, price_total, date
- 진행도: □□□
- 참고: 파일럿 완료, 기존 데이터 활용

Layer 12: individual_house_price (개별주택가격)
- API: price/house?area=<area>&period=<period>
- 목표: 개별주택 공시가격 (15,000건)
- 필드: house_id, address, price_per_m2, price_total, date
- 진행도: □□□

Layer 13: land_price_change_region_wms (지역별 지가변동)
- API: price/region?year=<year>
- 목표: 지역별 변동률 (시군구별 3년)
- 필드: region_code, year, change_rate, index
- 진행도: □□□

Layer 14: land_price_change_usage_wms (이용상황별 지가변동)
- API: price/usage?year=<year>&use=<use>
- 목표: 용도별 변동률 (5개 용도 × 3년)
- 필드: use_code, year, change_rate, index
- 진행도: □□□

산출물:
  - layer11_apart_housing_price.csv
  - layer12_individual_house_price.csv
  - layer13_land_price_region.csv
  - layer14_land_price_usage.csv
```

#### Day 12-13 (08-04 ~ 08-05): 데이터 통합 및 검증
```
담당: 모두 (2명)

□ 데이터 품질 검증
  - 14개 레이어 모두 품질 > 95%
  - 누락값 < 5%
  - 이상치 제거
  
□ 관계 설정
  - 지리 정보 (Layer 1-3) ← 건물 정보 (Layer 4-7)
  - 건물/토지 ← 가격 정보 (Layer 11-14)
  
□ SQLite 최종 테이블 생성
  - 14개 테이블 생성
  - 인덱스 설정 (조회 성능 최적화)
  - 제약 조건 추가

산출물:
  - vworld_wfs_multi_layer.sqlite (14개 테이블)
```

#### Day 14 (08-06): 주간 검증
```
□ 통합 데이터 검증
  - 테이블 간 참조 무결성 확인
  - 조회 성능 테스트
  - API 응답 시간 < 500ms 확인
  
□ 주간 진도 보고
  - 14/14 API 완료 (100%) ✓
  - SQLite 생성 완료 ✓
  - 데이터 품질 보고서
```

---

### Week 3 (2026-08-07 ~ 08-13): DB 생성 및 최종 검증

#### Day 15-18 (08-07 ~ 08-10): DuckDB Mart DB 생성
```
담당: 개발자 1

□ DuckDB 스키마 설계
  - SQLite 테이블 정규화
  - 뷰(View) 생성 (복잡 조회용)
  - 집계 테이블 (캐시용)
  
□ ETL 파이프라인 구현
  - SQLite → DuckDB 데이터 마이그레이션
  - 데이터 타입 최적화
  - 인덱스 생성
  
□ 성능 최적화
  - 쿼리 응답 < 100ms
  - 메모리 사용량 최소화
  - 병렬 처리 설정

산출물:
  - vworld_wfs_integrated.duckdb
  - duckdb_schema.sql
  - performance_benchmark.json
```

#### Day 19-20 (08-11 ~ 08-12): AVM 연동 준비
```
담당: 개발자 2

□ AVM 입력 데이터 매핑
  - VWorld 스키마 ← AVM 입력 스키마
  - 필드 변환/파생 로직
  - 결측값 처리 규칙
  
□ Export 포맷 생성
  - Parquet 형식 (고압축, 고성능)
  - CSV 형식 (호환성)
  - JSON 형식 (API 연동)
  
□ 데이터 통합 테스트
  - Phase 13.3 모델 입력으로 로드 테스트
  - 성능 검증

산출물:
  - vworld_avm_input.parquet
  - vworld_avm_input.csv
  - vworld_avm_input.json
  - data_mapping.json
```

#### Day 21 (08-13): 최종 검증 및 인수인계
```
담당: 모두 (2명)

□ 최종 검증
  - 14개 API 수집 성공 여부 확인
  - 데이터 품질 > 95% 달성 확인
  - 성능 벤치마크 목표 달성 확인
  
□ 문서화
  - VWORLD_INTEGRATION_REPORT.md 작성
  - API 명세 정리
  - 스키마 문서 정리
  
□ 인수인계
  - DuckDB 경로 공유
  - 데이터 액세스 방법 설명
  - 문제 발생 시 연락처 제공

산출물:
  - VWORLD_INTEGRATION_REPORT.md
  - vworld_api_documentation.md
  - vworld_schema_guide.md
```

---

## 🎯 완료 기준

```
✓ 14개 API 모두 수집 성공
✓ 데이터 품질 > 95%
  - 누락값 < 5%
  - 이상치 제거됨
  - 중복 제거됨

✓ 데이터베이스 생성 완료
  - vworld_wfs_multi_layer.sqlite (원본 14개 테이블)
  - vworld_wfs_integrated.duckdb (mart DB)

✓ AVM 입력 데이터 준비 완료
  - Parquet/CSV/JSON 형식
  - 스키마 매핑 완료
  - 성능 < 500ms

✓ 문서화 완료
  - API 명세
  - 스키마 정의
  - 사용 가이드
```

---

## 📊 진도 관리

| Week | Day | 담당 | 내용 | 진도 |
|------|-----|------|------|------|
| 1 | 1-2 | 모두 | 환경 구성 | □□□ |
| 1 | 3-4 | 1 | Layer 1-3 | □□□ |
| 1 | 5-6 | 2 | Layer 4-7 | □□□ |
| 1 | 7 | 모두 | 주간 검증 | □ |
| 2 | 8-9 | 1 | Layer 8-10 | □□□ |
| 2 | 10-11 | 2 | Layer 11-14 | □□□ |
| 2 | 12-13 | 모두 | 데이터 통합 | □□ |
| 2 | 14 | 모두 | 주간 검증 | □ |
| 3 | 15-18 | 1 | DuckDB 생성 | □□□□ |
| 3 | 19-20 | 2 | AVM 연동 | □□ |
| 3 | 21 | 모두 | 최종 검증 | □ |

---

## 🔗 참고 자료

- VWorld API: https://www.vworld.kr/
- data.go.kr: https://www.data.go.kr/
- SQLite 문서: https://sqlite.org/
- DuckDB 문서: https://duckdb.org/

---

**상태**: ✅ 준비 완료, 2026-07-24 시작  
**연락처**: eugene1108@gmail.com
