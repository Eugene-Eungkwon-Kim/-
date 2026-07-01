# Phase 13.1-GBL WBS (Work Breakdown Structure)
## 8개국 글로벌 확대

**기간**: 21일 (3주, Phase 13.5 완료 후 시작)
**전략**: KR 파이프라인 템플릿 복제 + 병렬화 (1국가 = KR 대비 약 40% 공수, 재사용 덕분)

---

## 1. 전체 작업 분해

```
Phase 13.1-GBL (21일 × 6h = 126시간)
│
├─ 1. 공통 인프라 구축 (Week 1, 30h)
│  ├─ 1.1 통화 정규화 레이어 (currency_converter.py) (4h)
│  ├─ 1.2 단위 정규화 레이어 (unit_converter.py) (3h)
│  ├─ 1.3 EnsembleEngine country 파라미터화 (6h)
│  ├─ 1.4 API 서비스 multi-country 라우팅 (6h)
│  ├─ 1.5 config/exchange_rates.json + country configs (3h)
│  ├─ 1.6 국가별 API 접근성 사전 테스트 (8개국) (4h)
│  └─ 1.7 공통 인프라 통합 테스트 (4h)
│
├─ 2. 1차 국가 그룹 (SG, HK) - 검증 그룹 (Week 2 전반, 24h)
│  ├─ 2.1 SG REGION_CONFIG + 데이터 생성 (4h)
│  ├─ 2.2 SG 모델 학습 + 검증 (R²>0.80) (4h)
│  ├─ 2.3 SG ONNX 변환 + 테스트 (10개+) (4h)
│  ├─ 2.4 HK REGION_CONFIG + 데이터 생성 (4h)
│  ├─ 2.5 HK 모델 학습 + 검증 (4h)
│  └─ 2.6 HK ONNX 변환 + 테스트 (4h)
│
├─ 3. 2차 국가 그룹 (UK, AU) - 중간 우선순위 (Week 2 후반, 24h)
│  ├─ 3.1 UK 데이터 소스 확인 (HM Land Registry 접근성) (4h)
│  ├─ 3.2 UK 파이프라인 실행 (실데이터 또는 합성) (8h)
│  ├─ 3.3 AU 데이터 소스 확인 (RP Data 접근성) (4h)
│  └─ 3.4 AU 파이프라인 실행 (8h)
│
├─ 4. 3차 국가 그룹 (CA, DE) - Week 3 전반 (24h)
│  ├─ 4.1 CA 파이프라인 실행 (StatsCan) (12h)
│  └─ 4.2 DE 파이프라인 실행 (Zillium) (12h)
│
├─ 5. 4차 국가 그룹 (JP, TH) - Week 3 후반 (24h)
│  ├─ 5.1 JP 파이프라인 실행 (엄격 tolerance ±5%) (12h)
│  └─ 5.2 TH 파이프라인 실행 (완화 tolerance ±15%) (12h)
│
└─ 6. 통합 & QA (Week 3 마지막, 6h)
   ├─ 6.1 8개국 통합 테스트 스위트 실행 (80+ 테스트) (3h)
   ├─ 6.2 국가 간 일관성 검증 (통화/단위 변환) (2h)
   └─ 6.3 최종 보고서 작성 (1h)
```

---

## 2. 주간 실행 계획

### Week 1: 공통 인프라 (선행 필수)

```
Day 1-2: 통화/단위 정규화 레이어
  ├─ currency_converter.py + exchange_rates.json
  └─ unit_converter.py (sqft/sqm 등)

Day 3-4: Country-Aware 엔진 확장
  ├─ EnsembleEngine(country_code=...) 파라미터화
  ├─ 디렉토리 구조 변경 (models_ir/{country}/)
  └─ API 라우팅 (/api/valuation/{country_code})

Day 5: 네트워크 접근성 사전 테스트
  ├─ 8개국 API 도메인 curl 테스트
  ├─ 차단된 도메인 목록 확정
  └─ 국가별 "실데이터 vs 합성데이터" 전략 확정

Day 6-7: 공통 인프라 통합 테스트 + 버퍼
```

### Week 2: 1차+2차 국가 그룹

```
Day 1-2: SG (싱가포르) - 최우선 검증 국가
  산출물: xgboost_SG.onnx, lightgbm_SG.onnx, 10+ 테스트 통과

Day 3-4: HK (홍콩)
  산출물: xgboost_HK.onnx, lightgbm_HK.onnx, 10+ 테스트 통과

Day 5-7: UK, AU (실데이터 접근성에 따라 순서 조정 가능)
  산출물: 국가별 모델 + 테스트
```

### Week 3: 3차+4차 국가 그룹 + 통합

```
Day 1-3: CA, DE
Day 4-6: JP, TH
Day 7: 8개국 통합 테스트 + 최종 보고서
```

---

## 3. 병렬화 전략

```
국가별 파이프라인은 서로 독립적 (모델 학습이 서로 참조하지 않음)
→ 최대 4개 국가 동시 개발 가능 (에이전트 병렬화 시)

순차 개발 시: 21일
병렬 개발 시 (4국가 동시): 약 10-12일로 단축 가능
  (단, 공통 인프라 Week 1은 순차 필수 — 모든 국가가 의존)
```

---

## 4. 성공 기준 체크리스트

```
✅ 공통 인프라
├─ 통화 정규화 8개국 지원
├─ 단위 정규화 (sqft/sqm) 지원
├─ Country-aware EnsembleEngine 동작
└─ /api/valuation/{country_code} 라우팅 동작

✅ 국가별 (8개 모두)
├─ 데이터 10,000+ 레코드 (실데이터 또는 합성)
├─ R² > 0.80
├─ MAPE < TOLERANCE_MAP[country]
├─ ONNX 변환 완료
└─ 10+ 국가별 테스트 통과

✅ 통합
├─ 80+ 테스트 전체 통과
├─ 국가 간 통화 변환 일관성 검증
└─ 최종 보고서 작성

└─→ 글로벌 AVM 시스템 운영 준비 완료
```

---

## 5. 리소스 산정

| 작업군 | 예상시간 |
|--------|---------|
| 공통 인프라 | 30h |
| SG+HK (검증 그룹) | 24h |
| UK+AU | 24h |
| CA+DE | 24h |
| JP+TH | 24h |
| 통합 & QA | 6h |
| **TOTAL** | **132h (약 21일 × 6.3h)** |

---

**WBS 완성**
**시작 조건**: Phase 13.5 완료 후 (2026-08-06 이후 예상)
**병렬화 시 단축 가능**: 21일 → 10-12일
