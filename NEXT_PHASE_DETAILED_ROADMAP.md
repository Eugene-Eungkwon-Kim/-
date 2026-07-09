# Phase 13.2-14 상세 로드맵

**작성일**: 2026-07-09  
**상태**: Phase 13.1-GBL 완료, 기술적 부채 기준 수립  
**담당**: Eugene Eungkwon Kim

---

## 🎯 현재 상황 분석

### Phase 13.1-GBL 달성 현황
```
✅ 6개국 확대 완료 (KR, SG, HK, UK, AU, TH)
✅ Country-aware EnsembleEngine 구현
✅ 45개 통합 테스트 통과
✅ 기술적 부채 기준 수립 (CODING_STANDARDS.md)
✅ GitHub 커밋 3개 (TH pilot, Tech debt framework, completion report)
```

### 다음 선택지 분석
```
┌─────────────────────────────────────────────────┐
│ 3가지 병렬 진행 경로                             │
├─────────────────────────────────────────────────┤
│ 1. Phase 13.2 (GPU 모델 훈련) [CLAUDE.md 기준]  │
│ 2. VWorld 통합 DB (데이터 수집) [별도 기획서]   │
│ 3. 기술적 부채 해결 (API 리팩토링) [즉시]       │
└─────────────────────────────────────────────────┘
```

---

## 📍 Phase 13.2: GPU-가속 모델 훈련

### 목표
RTX 5050 GPU를 활용한 6개국 모델 훈련 (35분→5분 가속)

### 범위
```
13.2.1 GPU 환경 설정 (2시간)
├─ CUDA/cuDNN 설정 확인
├─ XGBoost gpu_hist 활성화
├─ LightGBM gpu 활성화
└─ 성능 벤치마크

13.2.2 국가별 모델 훈련 (6시간)
├─ KR: XGBoost + LightGBM + Gradient Boosting
├─ SG: 3개 모델 병렬 훈련
├─ HK: 3개 모델 병렬 훈련
├─ UK: 3개 모델 병렬 훈련
├─ AU: 3개 모델 병렬 훈련
└─ TH: 3개 모델 병렬 훈련

13.2.3 하이퍼파라미터 튜닝 (3시간)
├─ GridSearchCV (GPU 가속)
├─ Cross-validation (5-fold)
└─ 성능 기록 (R² >0.84, MAPE <10.5%)

13.2.5 ONNX 모델 변환 (2시간)
├─ XGBoost → ONNX
├─ LightGBM → ONNX
└─ Gradient Boosting → ONNX 호환성 검증
```

### 예상 일정
- **기간**: 13일 (평행 처리)
- **선행 조건**: RTX 5050 드라이버 확인 ✓
- **산출물**: 18개 ONNX 모델 (국가×3)
- **테스트**: 국가별 4개 = 24개 검증 테스트

### 완료 기준
```
✓ 모든 6개국 R² >0.84
✓ MAPE <10.5%
✓ ONNX 변환 성공 100%
✓ 테스트 24/24 통과
✓ 성능 로그 기록
```

---

## 🌍 VWorld 통합 DB 프로젝트

### 개요
한국 부동산 데이터의 14개 API/레이어를 통합하는 데이터 수집 엔진

### 범위 (14개 항목)
```
1. search20 (검색 API 2.0)
2. geocoder20 (지오코더 API 2.0) [NEW]
3. wms_wfs20_reference (WMS/WFS API 참조)
4. continuous_cadastral_map (연속지적도)
5. building_by_use (용도별 건물)
6. gis_building_general (GIS 건물 일반)
7. gis_building_integrated (GIS 건물 통합)
8. land_characteristics (토지특성)
9. land_use_plan (토지이용계획)
10. apart_housing_price (공동주택가격) [기존 파일럿]
11. individual_house_price (개별주택가격)
12. land_right_register_list (대지권등록)
13. land_price_change_region_wms (지역별 지가변동률)
14. land_price_change_usage_wms (이용상황별 지가변동률)
```

### 예상 일정
- **기간**: 21일 (WBS 순서대로)
- **선행 조건**: data.go.kr API 키 발급 필요 (사용자 책임)
- **산출물**: 
  - `vworld_wfs_multi_layer.sqlite` (raw DB)
  - `vworld_wfs_integrated.duckdb` (mart DB)
  - 14개 레이어별 피처 테이블
  
### 배포 구조
```
D:\loan4u_avm_data\vworld_wfs_multi_layer\
├── raw/ (14개 API별 원본 데이터)
├── ledger/ (호출 기록 + 에러 로그)
├── db/
│   ├── vworld_wfs_multi_layer.sqlite
│   └── vworld_wfs_integrated.duckdb
├── exports/ (AVM 연동 parquet/csv)
└── tmp/ (작업 디렉토리)
```

### 완료 기준
```
Reference gate
├─ WMS/WFS API 2.0 reference snapshot ✓
└─ Layer catalog hash 기록 ✓

Endpoint gate
├─ 14개 대상이 ok/no_features/fallback 판정 ✓
└─ Blocked endpoint 문서화 ✓

Data gate
├─ Raw sha256 100% 기록 ✓
├─ Parse 성공률 >95% ✓
└─ DB 적재 완료 ✓

Integration gate
├─ 최종 mart 생성 ✓
└─ Coverage 점수 산출 ✓
```

---

## 🔧 기술적 부채 해결 (병렬)

### Phase 13 코드 개선
```
우선순위  작업                         시간    CODING_STANDARDS 준수
────────────────────────────────────────────────────────────────
1        api_server.py type hints    40m    ✓ (50줄, 100% hints)
2        data_collection_handler.py  30m    ✓ (분해)
3        api_server 테스트           20m    ✓ (45+ 테스트)
```

### 예상 효과
- Type hints: 38% → 85%
- 평균 함수 크기: 70줄 → 45줄
- 테스트: +15개

---

## 🎯 3가지 경로 비교

| 요소 | Phase 13.2 | VWorld DB | TechDebt 해결 |
|------|-----------|-----------|-------------|
| **기간** | 13일 | 21일 | 7일 |
| **복잡도** | 중간 | 높음 | 낮음 |
| **AVM 영향** | 직접 (모델) | 직접 (데이터) | 간접 (품질) |
| **우선순위** | 높음 | 높음 | 중간 |
| **병렬 가능** | 가능 | 가능 | 가능 (동시) |
| **선행 조건** | GPU 확인 | API 키 발급 | 없음 |
| **완료 기준** | 명확 | 명확 | 명확 |

---

## 📊 추천 진행 순서

### 최적 전략: 3중 병렬 처리 (권장)
```
┌─────────────────────────────────────┐
│ Week 1 (2026-07-10~16)              │
├─────────────────────────────────────┤
│ 👤 담당자 1: Phase 13.2 시작         │
│   - GPU 환경 설정                    │
│   - KR/SG 모델 훈련 (병렬)          │
│                                      │
│ 👤 담당자 2: VWorld 시작             │
│   - Endpoint probe 스크립트         │
│   - Search/Geocoder API 수집        │
│                                      │
│ 👤 담당자 3: TechDebt 개선          │
│   - api_server.py type hints 추가   │
│   - data_collection_handler.py 분해  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Week 2-3 (2026-07-17~30)            │
├─────────────────────────────────────┤
│ 👤 담당자 1: 모델 훈련 계속          │
│   - 전체 6개국 완료                  │
│   - ONNX 변환                        │
│   - 테스트 24/24                     │
│                                      │
│ 👤 담당자 2: VWorld 데이터 수집     │
│   - WFS 레이어 수집                 │
│   - 공시가격 API                     │
│   - SQLite/DuckDB 적재              │
│                                      │
│ 👤 담당자 3: API 테스트 작성        │
│   - api_server.py 45+ 테스트        │
│   - 통합 테스트                      │
└─────────────────────────────────────┘
```

### 단일 개발자 순서 (Sequential)
```
1단계: Phase 13.2 (13일)
├─ GPU 환경 설정
├─ 6개국 모델 훈련
└─ ONNX 변환 + 테스트

2단계: VWorld DB (21일)
├─ Endpoint probe
├─ 데이터 수집
└─ 통합 mart 생성

3단계: TechDebt 해결 (7일)
├─ Phase 13 코드 개선
└─ 테스트 강화
```

---

## 🚀 선택 가이드

### ❓ 어느 작업부터 시작할까?

**선택 1: Phase 13.2 (모델 훈련)**
- 📌 CLAUDE.md에서 명시한 다음 단계
- 🎯 GPU 자원 활용 (RTX 5050)
- ⏱️ 상대적으로 짧음 (13일)
- 📈 AVM 핵심 기능 (모델 성능)
- ✅ 선행 조건 충족 (GPU 드라이버 있음)

**선택 2: VWorld 통합 DB**
- 📌 별도 기획서 있음 (Rev.4, 상세 명세)
- 🎯 데이터 통합 (14개 API)
- ⏱️ 상대적으로 길음 (21일)
- 📊 AVM 입력 데이터 풍부화
- ❌ 선행 조건: API 키 발급 필요 (사용자)

**선택 3: TechDebt 해결**
- 📌 지금 바로 시작 가능
- 🎯 코드 품질 개선
- ⏱️ 짧음 (7일)
- 🛠️ 기술적 기반 구축
- ✅ 선행 조건 없음

---

## 💡 최종 권장

### 🥇 추천: Phase 13.2 + TechDebt (병렬)
```
이유:
1. Phase 13.2는 CLAUDE.md 기준 다음 단계
2. TechDebt는 병렬 처리 가능 (다른 인력)
3. GPU는 계속 활용해야 하는 자원
4. 모델 완성까지 기다릴 필요 없음

일정:
- Phase 13.2: 2026-07-10 ~ 2026-07-23 (13일)
- TechDebt: 2026-07-10 ~ 2026-07-17 (7일)
- VWorld: 2026-07-24 ~ (21일) ← 이후 시작

결과:
- 2026-07-23: Phase 13.2 완료 (6개국 모델 + ONNX)
- 2026-07-17: Phase 13 코드 품질 개선
- 2026-08-14: VWorld 통합 DB 완료
```

---

## 📋 실행 체크리스트

### Phase 13.2 시작 전
- [ ] RTX 5050 드라이버 버전 확인
- [ ] CUDA 11.x+ 설치 확인
- [ ] cuDNN 8.x+ 설치 확인
- [ ] XGBoost[gpu] 설치 확인: `pip show xgboost`
- [ ] LightGBM[gpu] 설치 확인: `pip show lightgbm`
- [ ] 데이터 준비 (국가별 10,000행)
- [ ] 성능 벤치마크 수집 스크립트 준비

### VWorld DB 시작 전
- [ ] data.go.kr API 키 발급 (사용자)
- [ ] VWorld API 키 확인
- [ ] D:\loan4u_avm_data 디렉토리 확인
- [ ] 기존 파일럿 DB 확인: vworld_wfs_apart_price.sqlite
- [ ] Endpoint 문서 준비 (Rev.4 기획서)

### TechDebt 시작 전
- [ ] CODING_STANDARDS.md 검토 완료
- [ ] api_server.py 분석 완료 (함수 목록)
- [ ] Test template 준비 완료

---

## 📞 의사결정 요청

### 선택 필요 사항
1. **병렬 vs 순차**
   - 🔵 병렬 (권장): 3명 이상 팀, GPU 충분
   - 🟡 순차: 단일 개발자

2. **VWorld API 키 상태**
   - 🔵 이미 발급됨 → VWorld 병렬 진행 가능
   - 🔴 미발급 → data.go.kr에서 신청 필요 (1-2일 소요)

3. **GPU 성능 확인**
   - 🔵 RTX 5050 확인됨 → Phase 13.2 시작 가능
   - 🟡 미확인 → 사전 벤치마크 필요 (1시간)

---

**보고서 작성자**: Claude Code  
**검토**: Eugene Eungkwon Kim  
**배포일**: 2026-07-09  
**다음 회의**: 2026-07-10 (의사결정)
