# Phase 13.3: 모델 검증 상세 계획

**담당**: 모두 (3명, VWorld/TechDebt 완료 후)  
**기간**: 2026-08-14 ~ 2026-08-27 (13일)  
**목표**: 실제 데이터로 모델 정확도 검증, 배포 준비 완료  

---

## 📋 기본 정보

### 검증 대상
- 6개국 모델 (KR, SG, HK, UK, AU, TH)
- 3가지 모델 유형 (XGBoost, LightGBM, Gradient Boosting)
- 총 18개 모델

### 입력 데이터
- VWorld 통합 DB (담당 1-2가 준비)
- 실제 부동산 거래 데이터 (사용자 제공)
- 데이터 통합: VWorld 스키마 → AVM 입력 스키마

### 성능 기준
```
✓ R² Score: >0.84 (모든 국가, 모든 모델)
✓ MAPE: <10.5% (모든 국가, 모든 모델)
✓ GPU vs CPU: 성능 차이 <5%
✓ ONNX 검증: 오차 ≤1e-5
```

---

## 📅 상세 일정

### Day 1-2 (08-14 ~ 08-15): 데이터 준비 및 통합

#### Step 1: VWorld 데이터 로드 (Day 1)
```
담당: 모두 (2시간)

□ DuckDB 연결
  - vworld_wfs_integrated.duckdb 로드
  - 14개 레이어 테이블 검증
  - 데이터 품질 확인 (누락값 < 5%)

□ 데이터 크기 확인
  - Layer 11-14 (가격 정보): 50,000건
  - Layer 4-7 (건물 정보): 10,000건
  - Layer 1-3 (지리 정보): 10,000건

□ 로그 기록
  - 데이터 로드 시간 기록
  - 메모리 사용량 확인

산출물:
  - vworld_data_summary.json
```

#### Step 2: 실제 거래 데이터 로드 (Day 1)
```
담당: 모두 (2시간)

□ 데이터셋 준비
  - 6개국 거래 데이터 (최소 1,000행/국)
  - 필드 검증 (동일 schema 확인)
  - 데이터 정제 (누락값, 이상치 제거)

□ 데이터 통합
  - VWorld ID ↔ 거래 데이터 ID 매핑
  - 중복 제거
  - 데이터 표준화

산출물:
  - real_estate_data_prepared.parquet
  - data_mapping_report.json
```

#### Step 3: AVM 입력 데이터 생성 (Day 2)
```
담당: 모두 (4시간)

□ 스키마 변환
  - VWorld 스키마 → AVM 입력 스키마
  - 피처 엔지니어링 (파생 피처 생성)
  - 정규화 (0~1 범위)

□ 6개국별 데이터셋 분리
  - KR: 최소 2,000행
  - SG: 최소 1,000행
  - HK: 최소 1,000행
  - UK: 최소 1,000행
  - AU: 최소 1,000행
  - TH: 최소 1,000행

□ Train/Test 분할 (80/20)
  - 재현 가능성을 위해 random_state=42 고정
  - Stratified split (가격대별 균등 분포)

산출물:
  - avm_input_data_KR.parquet (train + test)
  - avm_input_data_SG.parquet
  - ... (6개국 모두)
  - feature_engineering_report.md
```

---

### Day 3-6 (08-16 ~ 08-19): 모델 재훈련 및 검증

#### Day 3 (08-16): KR 모델 재훈련 (기준 설정)
```
담당: 개발자 1 (4시간)

□ KR 모델 훈련 (실제 데이터)
  - Phase 13.2의 GPU 트레이너 사용
  - 입력: avm_input_data_KR.parquet
  - 모델: XGBoost (gpu_hist) + LightGBM (gpu) + GB

□ 성능 측정
  - Train R²: 기준값 기록
  - Test R²: >0.84 확인
  - MAPE: <10.5% 확인
  - 훈련 시간: GPU 시간 기록

□ 결과 저장
  - kr_model_results.json
  - kr_performance_metrics.csv

예상 결과:
  XGBoost R²: 0.87 (기준)
  LightGBM R²: 0.86 (기준)
  GB R²: 0.85 (기준)
```

#### Day 4-6 (08-17 ~ 08-19): 다른 5개국 재훈련
```
담당: 모두 (병렬, 각 6시간)

담당 1: SG + HK 모델
  - avm_input_data_SG.parquet → 모델 훈련
  - avm_input_data_HK.parquet → 모델 훈련
  - 성능 기준 (KR과 비교)

담당 2: UK + AU 모델
  - avm_input_data_UK.parquet → 모델 훈련
  - avm_input_data_AU.parquet → 모델 훈련
  - 성능 기준 (KR과 비교)

담당 3: TH 모델 + 통합 분석
  - avm_input_data_TH.parquet → 모델 훈련
  - 6개국 성능 통합 분석
  - 이상치 조사

산출물:
  - {country}_model_results.json (6개국)
  - {country}_performance_metrics.csv (6개국)
  - cross_country_analysis.md

완료 기준:
  ✓ 6개국 모두 R² >0.84
  ✓ 6개국 모두 MAPE <10.5%
  ✓ 예상 기준값과 ±5% 이내 변동
```

---

### Day 7-9 (08-20 ~ 08-22): A/B 테스트

#### Day 7 (08-20): GPU 모델 vs CPU 모델 비교
```
담당: 모두 (4시간)

□ CPU 모델 훈련
  - Phase 13.2 gpu_trainer 사용 (cpu 모드)
  - 6개국 모두 CPU로 재훈련
  - 훈련 시간 기록 (예상 7배 느림)

□ 성능 비교
  XGBoost:
    GPU R²: 0.87 vs CPU R²: 0.87 (동일)
    성능 오차: < 1e-4 ✓
  
  LightGBM:
    GPU R²: 0.86 vs CPU R²: 0.86 (동일)
    성능 오차: < 1e-4 ✓
  
  GB:
    R²: 0.85 (CPU만 지원)

□ 속도 비교
  XGBoost: GPU 5분 vs CPU 35분 (7배) ✓
  LightGBM: GPU 4분 vs CPU 32분 (8배) ✓

□ 결론
  - GPU와 CPU 성능 동일 ✓
  - GPU 훈련이 7-8배 빠름 ✓
  - 배포 시 GPU 활용 권장

산출물:
  - gpu_vs_cpu_comparison.md
  - performance_speedup_chart.png
```

#### Day 8 (08-21): ONNX 모델 vs pkl 모델 비교
```
담당: 모두 (3시간)

□ ONNX 모델 재검증
  - Phase 13.2의 ONNX 모델 로드
  - 각 국가별 18개 ONNX 모델 로드
  - ONNX Runtime으로 추론

□ 예측값 비교
  - pkl 모델 예측 vs ONNX 모델 예측
  - 각 테스트 샘플별 오차 측정
  - 상대 오차 ≤ 1e-5 확인

□ 성능 비교
  Inference 시간:
    pkl (CPU): 10ms
    ONNX (CPU): 8ms (20% 빠름)
    ONNX (NPU): 2ms (5배 빠름, 예상)

□ 결론
  - ONNX 변환 정확성 100% ✓
  - ONNX가 약간 더 빠름 (최적화) ✓
  - NPU 배포 준비 완료 ✓

산출물:
  - onnx_vs_pkl_comparison.md
  - onnx_accuracy_report.json
```

#### Day 9 (08-22): 성능 이상치 조사
```
담당: 개발자 3 (4시간)

□ 성능 이상 감지
  - R² < 0.84인 모델 찾기
  - MAPE > 10.5%인 모델 찾기
  - 이전 성능과 ±10% 이상 차이

□ 원인 분석
  - 데이터 품질 (누락값, 이상치)
  - 모델 과소적합/과적합
  - 하이퍼파라미터 이상
  - 환경 차이 (GPU vs CPU)

□ 개선 조치
  - 데이터 정제 보강
  - 하이퍼파라미터 재튜닝
  - 모델 재훈련

□ 최종 검증
  ✓ 모든 국가 R² >0.84 달성
  ✓ 모든 국가 MAPE <10.5% 달성

산출물:
  - anomaly_detection_report.md
  - remediation_actions.md
  - final_performance_table.xlsx
```

---

### Day 10-12 (08-23 ~ 08-25): 성능 최적화

#### Day 10-11 (08-23 ~ 08-24): 배치 크기 및 메모리 튜닝
```
담당: 개발자 1-2 (6시간)

□ 배치 크기 최적화
  테스트: batch_size = [1, 8, 16, 32, 64, 128]
  
  결과:
    batch_size=1:   10ms/sample (정확도 높음, 느림)
    batch_size=32:  0.5ms/sample (균형)
    batch_size=128: 0.3ms/sample (빠름, 메모리 사용 증가)
  
  선택: batch_size=32 (응답성과 효율성 균형)

□ 메모리 풀 최적화
  - 모델 로드 후 유지 (재로드 X)
  - 배치 전처리 캐싱
  - 메모리 누수 모니터링

□ 캐시 전략
  - 최근 100개 예측 결과 캐시
  - TTL: 1시간
  - 메모리: < 50MB

산출물:
  - batch_size_optimization.md
  - memory_usage_report.json
  - cache_strategy.md
```

#### Day 12 (08-25): 추론 시간 <2ms 달성
```
담당: 개발자 3 (4시간)

□ 최종 최적화
  현재: pkl (CPU) = 10ms
  목표: ONNX (NPU) = 2ms
  
  단계별:
  1. ONNX (CPU): 8ms → 20% 개선 ✓
  2. 배치 처리: 4ms (batch=32)
  3. 캐싱: 2ms (cache hit)
  4. NPU (예상): 1ms

□ 성능 검증
  - 100개 배치 추론 시간: <200ms ✓
  - 단일 요청 응답: <10ms ✓
  - P99 응답 시간: <50ms ✓

□ 부하 테스트
  - 동시 요청 100개: 처리 가능 ✓
  - 메모리 안정성: 안정 ✓
  - CPU 사용률: < 80% ✓

산출물:
  - performance_optimization_report.md
  - load_test_results.json
  - final_deployment_readiness.md
```

---

### Day 13 (08-26 ~ 08-27): 배포 준비 완료

#### Step 1: 배포 체크리스트 (4시간)
```
담당: 모두 (4시간)

배포 전 최종 검증:

모델 검증:
  ✓ 6개국 모두 R² >0.84
  ✓ 6개국 모두 MAPE <10.5%
  ✓ GPU vs CPU 성능 동일 (<1e-4)
  ✓ ONNX 검증 오차 ≤1e-5

성능 검증:
  ✓ 추론 시간 < 2ms (배치, ONNX)
  ✓ 배치 처리 < 200ms (100개)
  ✓ 메모리 안정 (< 500MB)
  ✓ 동시 요청 100개 처리 가능

코드 품질:
  ✓ 모든 함수 type hints ✓
  ✓ 테스트 커버리지 > 80% ✓
  ✓ MyPy 0 errors ✓
  ✓ Pylint score > 9.0 ✓

문서화:
  ✓ 모델 명세서 ✓
  ✓ 성능 보고서 ✓
  ✓ 배포 가이드 ✓
  ✓ 트러블슈팅 가이드 ✓

산출물:
  - PHASE_13_3_VALIDATION_REPORT.md
  - DEPLOYMENT_CHECKLIST.md (✓ 100%)
  - model_specifications.json
  - performance_metrics_final.xlsx
```

#### Step 2: 최종 보고 및 승인 (2시간)
```
담당: 모두 (2시간)

□ 보고서 작성
  - Phase 13.3 최종 검증 보고서
  - 모든 성능 지표 정리
  - 이상 사항 및 개선 사항 정리

□ 배포 승인 받기
  - 경영진 검토 (1시간)
  - 기술 담당자 최종 승인 (30분)
  - 배포 일정 확정 (30분)

□ Phase 13.4 준비
  - OpenVINO IR 변환 준비
  - NPU 배포 환경 구축 시작
  - 배포 롤아웃 계획 수립

완료 기준:
  ✓ 모든 검증 완료
  ✓ 배포 승인 획득
  ✓ Phase 13.4 (NPU 배포) 시작 준비 완료
```

---

## 🎯 완료 기준

```
모델 성능:
✓ 6개국 모두 R² >0.84 달성
✓ 6개국 모두 MAPE <10.5% 달성
✓ 예상 기준값과 ±5% 이내 변동

검증 완료:
✓ GPU vs CPU: 성능 동일 (<1e-4 오차)
✓ ONNX vs pkl: 정확도 완벽 (≤1e-5 오차)
✓ 성능 이상치: 모두 조사 완료

최적화 완료:
✓ 추론 시간: <2ms (배치, ONNX)
✓ 메모리: 안정, <500MB
✓ 동시 처리: 100개 요청 가능

배포 준비:
✓ 배포 체크리스트: 100% 완료
✓ 문서화: 완전
✓ 경영진 승인: 획득

상태: 🟢 배포 준비 완료
```

---

## 📊 진도 관리

| Day | 내용 | 완료 기준 | 진도 |
|-----|------|---------|------|
| 1-2 | 데이터 준비 | 6개국 AVM 입력 데이터 | □□ |
| 3-6 | 모델 재훈련 | 6개국 모두 R²>0.84 | □□□□ |
| 7-9 | A/B 테스트 | GPU/CPU/ONNX 검증 완료 | □□□ |
| 10-12 | 최적화 | <2ms 추론 달성 | □□□ |
| 13 | 배포 준비 | 체크리스트 100% | □ |

---

## 🔗 참고 자료

- [Phase 13.2 GPU 트레이너](D:\avm_work\avm_project\scripts\phase13_2_gpu_trainer.py)
- [CODING_STANDARDS.md](D:\avm_work\.claude\CODING_STANDARDS.md)
- [VWorld 데이터 통합](D:\avm_work\VWORLD_DATA_COLLECTION_PLAN.md)
- [OpenVINO 문서](https://docs.openvino.ai/)

---

**상태**: ✅ 준비 완료, 2026-08-14 시작  
**의존성**: VWorld 데이터 + TechDebt 코드 품질 (완료 후)  
**연락처**: eugene1108@gmail.com
