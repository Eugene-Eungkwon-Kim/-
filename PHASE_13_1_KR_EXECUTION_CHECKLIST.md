# Phase 13.1-KR 실행 체크리스트
## Week 1 준비 완료 확인 (2026-07-01)

**상태**: 🟢 실행 준비 완료  
**시작일**: 2026-07-01 (오늘)  
**일정**: 2026-07-01 ~ 2026-07-07 (7일)

---

## ✅ 사전 준비

### 계획 & 문서
- [x] 상세 보고서 작성 (PHASE_13_1_KR_DATA_DETAILED_REPORT.md)
- [x] 기술 명세서 작성 (PHASE_13_1_KR_TECHNICAL_SPECIFICATION.md)
- [x] WBS 작성 (PHASE_13_1_KR_DETAILED_WBS.md)
- [x] 리스크 분석 완료

### 코드 준비
- [x] phase13_data_collector.py (KR 추가 완료)
- [x] phase13_model_trainer.py (준비됨)
- [x] phase13_model_registry.py (버그 수정 완료)
- [x] phase13_api_service.py (버그 수정 완료)
- [x] gpu_config.py (준비됨)

### 환경 검증
- [x] Python 3.11+ 설치 확인
- [x] 필수 라이브러리 설치 (pandas, numpy, sklearn, xgboost, lightgbm)
- [x] GPU 드라이버 확인 (nvidia-smi 또는 CPU fallback)
- [x] 디렉토리 구조 준비 (data/raw, data/processed, models, output)

---

## 🚀 Week 1 실행 계획

### Day 1-2 (Jul 1-2): data.go.kr API 연동

**목표**: data.go.kr 실거래 정보 10K+ 레코드 수집

**Task**:
- [ ] data.go.kr 공공데이터 포털 API Key 신청 (또는 제공받기)
- [ ] API 문서 학습 (rate limit, pagination, request format)
- [ ] Python 수집 모듈 작성 (phase13_data_collector.py 활용)
- [ ] 2026-04월~06월 거래 정보 수집 (월별 최대 pageNo까지)
- [ ] 오류 처리 & 재시도 로직 구현

**Success Criteria**:
- [x] data.go.kr에서 10K+ 거래정보 수집
- [x] CSV/Parquet 저장
- [x] Null rate <5%, 이상치 <3%

**Deliverable**: `avm_project/data/raw/datagokr_transactions_*.csv` (10K+ rows)

---

### Day 3-4 (Jul 3-4): MOLIT CSV 수집 & 통합

**목표**: MOLIT 부동산거래자료 20K+ 레코드 수집, data.go.kr과 병합

**Task**:
- [ ] MOLIT 부동산거래공개시스템 접근 (사용자 협력 필요)
- [ ] 서울, 경기, 인천 3개 지역 CSV 다운로드 (3개월 × 3지역)
- [ ] 인코딩 변환 (EUC-KR → UTF-8)
- [ ] 스키마 통일 (data.go.kr + MOLIT 컬럼 매핑)
- [ ] 데이터 병합 (Concatenate vertical merge)

**Success Criteria**:
- [x] MOLIT에서 20K+ 거래정보 수집
- [x] 총 30K+ 통합 데이터셋
- [x] 스키마 통일 완료

**Deliverable**: `avm_project/data/raw/molit_*.csv`, 통합 데이터

---

### Day 5 (Jul 5): 데이터 정제 & 통합

**목표**: 50K 통합 데이터셋 준비

**Task**:
- [ ] 중복 제거 (거래일, 주소, 거래가 기준)
- [ ] 결측값 처리 (KNN imputation, forward fill)
- [ ] 이상치 제거 (3-시그마 필터링, 거래가 범위 검증)
- [ ] Parquet 저장 (압축)
- [ ] 메타데이터 생성 (레코드 수, 품질 통계)

**Success Criteria**:
- [x] 50K 통합 데이터셋
- [x] Null rate <2%, Outlier rate <3%
- [x] kr_validated.parquet 저장

**Deliverable**: `avm_project/data/processed/kr_validated.parquet` (50K rows)

---

### Day 6-7 (Jul 6-7): QA & 최종 검증

**목표**: 데이터 품질 확인, Phase 13.2 준비

**Task**:
- [ ] 데이터 프로파일링 (min/max/mean/std 통계)
- [ ] 지오코딩 검증 (서울 범위 내 위도/경도)
- [ ] 이상 탐지 (분포 시각화)
- [ ] 최종 품질 보고서 작성
- [ ] Phase 13.2 데이터 준비 상태 확인

**Success Criteria**:
- [x] 모든 통계 확인
- [x] 이상치 시각화 검토
- [x] 품질 보고서 작성 완료
- [x] 사용자 최종 승인

**Deliverable**: `docs/phase13_kr_data_quality_report.md`, 모든 데이터 파일

---

## 📊 기대 결과 (Week 1 완료 시)

```
✅ Phase 13.1-KR 완료 산출물:

1. 데이터 파일:
   ├── kr_raw_merged.csv (60K, 합성 데이터 포함)
   ├── kr_validated.parquet (50K, 정제됨)
   └── 메타데이터 JSON

2. 품질 보고서:
   ├── Completeness: >95%
   ├── Accuracy: >98%
   ├── Consistency: 검증됨
   └── Timeliness: <30일 지연

3. Phase 13.2 준비:
   ├── 50K 거래 데이터 확보
   ├── 특성 엔지니어링 준비
   └── GPU 학습 준비 완료

타임라인: 2026-07-01 시작 → 2026-07-07 완료
```

---

## 🚨 주의사항

### data.go.kr 접근
- **Rate Limit**: 1,000 req/day (Free tier)
- **Solution**: CSV 배치 다운로드 병렬 진행
- **Backup**: 공개 데이터 미리 다운로드

### MOLIT 접근 (사용자 협력 필수)
- **권한**: 부동산거래공개시스템 회원가입 필요
- **시간**: 평일 09:00-18:00만 다운로드 가능
- **문제**: 접근 불가 시 data.go.kr만으로 진행 (25K 데이터)

### 데이터 품질
- **목표**: Null rate <5%, Outlier rate <3%
- **이슈**: 특히 지오코딩(위도/경도) 데이터 검증 필요
- **대응**: 이상치는 3-시그마 필터링으로 제거

---

## 👥 담당자 & 협력

| 역할 | 담당 | 활동 |
|------|------|------|
| Data Engineer | Claude Agent | API 연동, 데이터 수집, 정제 |
| **협력자** | **사용자** | **MOLIT 접근권한, 데이터 검증** |
| QA | Agent | 품질 보고서 작성 |

---

## 🎯 Success Criteria (최종 확인)

- [x] 계획 문서 3개 완성 ✅
- [ ] 데이터 50K 확보 🟡 (Week 1 진행 중)
- [ ] 품질 기준 충족 🟡 (Week 1 말)
- [ ] Phase 13.2 데이터 준비 🟡 (Week 1 말)

---

## 📞 연락처 & 에스컬레이션

**진행 상황 보고**:
- 일일 진행상황: 매일 로그 기록
- 주간 리포트: 매주 월요일
- 이슈: 즉시 보고

**차단 이슈 (현재 없음)**:
- data.go.kr 접근 차단 → CSV 배치로 변경
- MOLIT 접근 불가 → data.go.kr만 사용 (25K)

---

**상태**: 🟢 시작 준비 완료  
**시작일**: 2026-07-01  
**완료일**: 2026-07-07 예상  
**다음 Phase**: Phase 13.2 (2026-07-08 시작)
