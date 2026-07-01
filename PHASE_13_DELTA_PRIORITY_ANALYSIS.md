# Phase 13 델타값 우선순위 분석 및 로드맵
## Phase 13.1-13.5 및 부가 작업의 순차 실행 계획

**분석일**: 2026-07-01  
**기준**: 델타값 = ROI × (1 - 위험도) / 시간  
**방향**: 높은 ROI, 낮은 위험, 짧은 기간 우선  

---

## 📊 Phase 13 구성 요소

| Phase | 내용 | 기간 | ROI | 위험 | 상태 |
|-------|------|------|-----|------|------|
| 13.1-KR | 한국 실거래 데이터 수집 | 1주 | 높음 | 중간 | ✅ 계획 완료 |
| 13.2 | GPU 모델 학습 | 1주 | 높음 | 중간 | 🟡 코드 준비 |
| 13.3 | 모델 검증 & 성능 최적화 | 3-5일 | 높음 | 낮음 | 🟡 코드 준비 |
| 13.4 | NPU 배포 & API 서비스 | 3-5일 | 높음 | 높음 | 🔴 버그 2개 |
| 13.5 | 자동화 & 모니터링 | 3-5일 | 중간 | 낮음 | 🟡 코드 준비 |
| 13.1-GBL | 8개국 확대 (UK/SG/JP/DE/AU/CA/TH/HK) | 2-3주 | 중간 | 중간 | ⏳ 미계획 |

**Total Phase 13**: 3주 (intensive) + 2-3주 (확대) = 5-6주

---

## 🎯 델타값 계산

### 델타값 공식
```
ΔValue = (ROI × (1 - Risk) / Time) × (Dependencies) × (BlockerSeverity)
```

| 변수 | 범위 | 설명 |
|------|------|------|
| ROI | 0-1 | 비즈니스 가치 (0=없음, 1=극대) |
| Risk | 0-1 | 구현 위험도 (0=안전, 1=극고) |
| Time | 1-42일 | 예상 소요 시간 |
| Dependencies | 0-1 | 선행작업 필요도 (0=독립, 1=완전종속) |
| BlockerSeverity | 0-1 | 차단기 심각도 (0=없음, 1=critical) |

### 각 Phase 점수

#### 1️⃣ Phase 13.1-KR (한국 실거래 데이터)
```
ROI: 1.0 (핵심: 모든 후속 단계의 기반)
Risk: 0.4 (API 지연 가능성, 데이터 품질)
Time: 7일
Dependencies: 0.0 (독립적)
BlockerSeverity: 0.9 (없으면 전체 일정 지연)

ΔValue = (1.0 × (1-0.4) / 7) × 0.0 × 0.9 = 0.086
실제: 우선순위 1순위 (Critical Path)
```

#### 2️⃣ Phase 13.2 (GPU 모델 학습)
```
ROI: 0.95 (R² >0.84 달성 시 매우 높음)
Risk: 0.35 (GPU 메모리, 수렴 실패 가능)
Time: 7일
Dependencies: 1.0 (13.1 완료 필수)
BlockerSeverity: 0.95 (없으면 배포 불가)

ΔValue = (0.95 × (1-0.35) / 7) × 1.0 × 0.95 = 0.188
우선순위: 2순위 (13.1 직후)
```

#### 3️⃣ Phase 13.3 (모델 검증)
```
ROI: 0.90 (품질 보증)
Risk: 0.20 (표준 ML 검증)
Time: 4일
Dependencies: 1.0 (13.2 완료 필수)
BlockerSeverity: 0.85 (배포 전 필수)

ΔValue = (0.90 × (1-0.20) / 4) × 1.0 × 0.85 = 0.153
우선순위: 3순위 (13.2 직후)
```

#### 4️⃣ Phase 13.4 (NPU 배포 & API)
```
ROI: 0.85 (운영 시작)
Risk: 0.65 (import bug 수정했지만 OpenVINO 미완성)
Time: 5일
Dependencies: 1.0 (13.3 완료 필수)
BlockerSeverity: 0.80 (운영 시작에 필수)

ΔValue = (0.85 × (1-0.65) / 5) × 1.0 × 0.80 = 0.042
우선순위: 4순위 (높은 위험도: model_converter 미완성)
```

#### 5️⃣ Phase 13.5 (자동화 & 모니터링)
```
ROI: 0.70 (효율성 개선)
Risk: 0.25 (표준 자동화)
Time: 5일
Dependencies: 1.0 (13.4 완료 필수)
BlockerSeverity: 0.50 (선택사항)

ΔValue = (0.70 × (1-0.25) / 5) × 1.0 × 0.50 = 0.053
우선순위: 5순위
```

#### 6️⃣ Phase 13.1-GBL (8개국 확대)
```
ROI: 0.60 (수익 증대, 장기)
Risk: 0.40 (각 국가별 API 통합)
Time: 21일
Dependencies: 1.0 (전체 13.1-13.5 완료 필수)
BlockerSeverity: 0.30 (사업 확대 선택)

ΔValue = (0.60 × (1-0.40) / 21) × 1.0 × 0.30 = 0.005
우선순위: 6순위
```

---

## 📋 최종 우선순위 순서

| 순위 | Phase | 델타값 | 기간 | 선행 | 상태 |
|------|-------|--------|------|------|------|
| 1 | 13.1-KR | 0.086 | 7일 | - | ✅ 계획 완료 |
| 2 | 13.2 | 0.188 | 7일 | 13.1 | 🟡 준비 중 |
| 3 | 13.3 | 0.153 | 4일 | 13.2 | 🟡 준비 중 |
| 4 | 13.4 | 0.042 | 5일 | 13.3 | 🔴 2개 버그 수정 필요 |
| 5 | 13.5 | 0.053 | 5일 | 13.4 | 🟡 준비 중 |
| 6 | 13.1-GBL | 0.005 | 21일 | 13.1-13.5 | ⏳ 미계획 |

**Critical Path**: 13.1 → 13.2 → 13.3 → 13.4 → 13.5 (총 28일)  
**병렬 가능**: 13.5는 13.4와 부분 병렬 가능 (Monitoring setup 미리 준비)

---

## 🚨 발견된 구현 갭 & 버그

### Critical Blockers (13.4 차단)

#### 버그 1: model_converter.py - OpenVINO 변환 미완성
```
위치: avm_project/scripts/phase13_model_converter.py:160
심각도: HIGH
영향: NPU 배포 불가 (INT8 모델 파일 생성 안 됨)
현상: quantize_onnx_to_ir() 정의만 있고 호출 안 됨
대안: ONNX→OpenVINO 변환 실제 구현 필요 (3-5시간)
```

#### 버그 2: data_collector.py - 한국 데이터 소스 없음
```
위치: avm_project/scripts/phase13_data_collector.py:44-52
심각도: CRITICAL (Phase 13.1-KR 시작 불가)
영향: data.go.kr/MOLIT API 연동 구현 필요
현상: COUNTRIES_CONFIG에 KR 없음, _collect_country_data() = 합성 데이터만
대안: Week 1 작업으로 구현 예정 (계획서 존재)
```

### Medium Blockers (13.4 품질)

#### 버그 3: api_service.py - Import 경로 수정됨 ✅
```
위치: avm_project/scripts/phase13_api_service.py:63
심각도: MEDIUM (이미 수정)
상태: ✅ Fixed (커밋 ba40627)
```

#### 버그 4: model_registry.py - 레지스트리 재로드 ✅
```
위치: avm_project/scripts/phase13_model_registry.py:61
심각도: MEDIUM (이미 수정)
상태: ✅ Fixed (커밋 ba40627)
```

---

## 📅 실행 계획 타임라인

### Week 1 (2026-07-01 ~ 2026-07-07): Phase 13.1-KR
```
Day 1-2: data.go.kr API 연동 (현 계획서 Week 1)
Day 3-5: MOLIT CSV 수집 & 통합
Day 6-7: QA & 검증
Output: 50K 거래 데이터셋 + 품질 보고서
```

### Week 2 (2026-07-08 ~ 2026-07-14): Phase 13.2-13.3
```
Day 1-2: 특성 엔지니어링 (45 features)
Day 3-5: GPU 학습 (XGBoost/LightGBM/GB)
Day 6: 교차 검증 및 하이퍼파라미터 튜닝
Day 7: 성능 검증 (R² >0.84, MAPE <10.5%)
Output: 최적화된 모델 + 검증 리포트
```

### Week 3 (2026-07-15 ~ 2026-07-21): Phase 13.4 (Phase 13.5 병렬)
```
Day 1-2: model_converter.py 완성 (ONNX→OpenVINO INT8)
Day 3: NPU 배포 & 추론 테스트
Day 4: FastAPI 서비스 통합
Day 5-7: 자동화 파이프라인 + 모니터링 (13.5 병렬)
Output: 운영 준비 완료, API 서비스 런칭
```

### Week 4 (2026-07-22 ~ 2026-08-04): Phase 13.1-GBL (8개국 확대)
```
Day 1-3: 각 국가별 data_collector 구현 (UK/SG/JP/DE/AU/CA/TH/HK)
Day 4-7: 국가별 모델 학습 & 배포
Output: 글로벌 AVM 시스템 준비 완료
```

---

## 🎯 각 Phase별 상세 계획 & 명세 작성 순서

### Immediate (이번 세션)
- [ ] **Phase 13.1-KR** - 상세 보고서 ✅ 
- [ ] **Phase 13.1-KR** - 기술 명세 ✅
- [ ] **Phase 13.1-KR** - WBS ✅

### Next (이 문서 후)
- [ ] **Phase 13.2** - 상세 보고서 (GPU 모델 학습)
- [ ] **Phase 13.2** - 기술 명세
- [ ] **Phase 13.2** - WBS

- [ ] **Phase 13.3** - 상세 보고서 (검증)
- [ ] **Phase 13.3** - 기술 명세
- [ ] **Phase 13.3** - WBS

- [ ] **Phase 13.4** - 상세 보고서 (배포, **2개 버그 수정 포함**)
- [ ] **Phase 13.4** - 기술 명세
- [ ] **Phase 13.4** - WBS

- [ ] **Phase 13.5** - 상세 보고서 (자동화)
- [ ] **Phase 13.5** - 기술 명세
- [ ] **Phase 13.5** - WBS

---

## ⚠️ 위험 & 완화 전략

### Top 3 Risks

| 위험 | 확률 | 영향 | 완화책 |
|------|------|------|--------|
| data.go.kr API 지연/오류 | 30% | 1주 | CSV 배치 다운로드 병렬 진행 |
| model_converter 구현 미완성 | 25% | Phase 13.4 차단 | 즉시 우선 구현 (Day 1) |
| 모델 성능 미달 (R² <0.80) | 15% | 3-5일 | 하이퍼파라미터 광범위 탐색 준비 |

### 버그 수정 우선순위

1. **Critical (Week 1 Day 1)**: model_converter.py OpenVINO 변환 구현
2. **Critical (Week 1 Day 1)**: data_collector.py KR 데이터 소스 추가
3. Done ✅: api_service.py import 경로
4. Done ✅: model_registry.py metadata 역직렬화

---

## 📋 검토 체크리스트

### Phase 13.1-KR 검토 ✅
- [x] 상세 보고서 작성 (PHASE_13_1_KR_DATA_DETAILED_REPORT.md)
- [x] 기술 명세 작성 (PHASE_13_1_KR_TECHNICAL_SPECIFICATION.md)
- [x] WBS 작성 (PHASE_13_1_KR_DETAILED_WBS.md)
- [x] 사용자 승인 대기

### Phase 13.2-13.5 계획 ⏳
- [ ] 이 문서 (델타값 분석) 검토 & 승인
- [ ] Phase 13.2 3개 문서 작성
- [ ] Phase 13.3 3개 문서 작성
- [ ] Phase 13.4 3개 문서 작성 (버그 수정 포함)
- [ ] Phase 13.5 3개 문서 작성

### 버그 수정 실행 ⏳
- [ ] model_converter.py - quantize_onnx_to_ir() 실제 호출 구현
- [ ] data_collector.py - KR 데이터 소스 추가 (data.go.kr/MOLIT)
- [ ] 커밋 & 푸시

### 실행 시작 ⏳
- [ ] 모든 계획 문서 검토 승인
- [ ] Week 1 Day 1 (2026-07-01) 시작
- [ ] 주간 진행상황 보고 (매주 월요일)

---

## 📞 다음 단계

**즉시 필요**:
1. 이 델타값 분석 검토 & 승인
2. Phase 13.1-KR 최종 승인 (data source, 일정, 리소스)
3. 버그 수정 2개 (model_converter, data_collector) 우선 실행

**일정**:
- Today (2026-07-01): 계획 최종화 & 승인
- 2026-07-02: Phase 13.2-13.5 3개 문서 작성 시작
- 2026-07-03: 버그 수정 + 모든 계획 완성
- 2026-07-04: Week 1 Day 1 실행 (금요일 시작)

---

**작성자**: Claude Agent (claude-sonnet-5)  
**최종 검토**: TBD (사용자 승인 대기)  
**상태**: 🟡 검토 대기
