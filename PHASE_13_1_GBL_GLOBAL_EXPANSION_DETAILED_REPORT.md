# Phase 13.1-GBL 상세 보고서
## 8개국 글로벌 확대 (UK/SG/JP/DE/AU/CA/TH/HK)

**작성일**: 2026-07-01
**버전**: 1.0
**우선순위**: 🔵 P3 (Phase 13.1-13.5 완료 후, 델타값 최저)
**선행 조건**: Phase 13.1-13.5 (한국) 전체 완료

---

## Executive Summary

**목표**: 한국(KR)에서 검증된 AVM 파이프라인(합성 데이터 생성 → 학습 → 변환 → 서빙)을 8개 대상국으로 확대하여 글로벌 AVM 시스템 구축

**대상 국가**: UK, SG, JP, DE, AU, CA, TH, HK (8개국)

**기간**: 21일 (3주, Phase 13.5 완료 후 시작)

**성공 기준**: 각 국가별 R² >0.80 (국가별 데이터 성숙도 차이 반영), 국가별 통화/단위 정규화 완료, 8개국 동시 서빙 가능한 API 구조

**핵심 통찰 (KR 파이프라인에서 검증됨)**:
- ✅ 실거래 API 접근이 막히거나 지연되어도, **현실적인 합성 데이터 생성 전략**으로 모델 개발/검증 파이프라인을 선진행할 수 있음 (KR: `generate_kr_realistic_data.py`)
- ✅ 이 세션 환경에서는 정부/공공기관 API(data.go.kr, MOLIT, LH)가 아웃바운드 네트워크 정책으로 차단되는 사례가 확인됨 → 각 국가 API도 동일 이슈 예상, 동일 완화 전략 필요
- ✅ pkl → ONNX → OpenVINO IR 변환 경로가 국가 무관하게 재사용 가능 (`phase13_model_converter.py`는 이미 모델-불가지론적)

---

## 1. 현황 분석

### 1.1 기존 자산 (KR에서 재사용 가능)

```
검증된 파이프라인 (Phase 13 KR):
├── generate_kr_realistic_data.py  → 패턴: 국가별 REGION_CONFIG 딕셔너리 교체로 재사용
├── train_kr_model.py               → 패턴: FEATURE_COLS, TARGET_R2 국가별 조정
├── phase13_model_converter.py      → 그대로 재사용 (모델 포맷 불가지론적)
├── avm_core_engine.py / avm_ensemble_engine.py → country 파라미터화 필요
├── avm_coldstart.py                → 국가별 재학습만 필요
└── tests/test_kr_valuation.py      → 국가별 테스트 템플릿으로 확장
```

### 1.2 국가별 데이터 특성 (CLAUDE.md 기준)

| 국가 | 통화 | Tolerance | 데이터 소스 | 예상 레코드 |
|------|------|-----------|------------|------------|
| UK | GBP | ±5% (엄격) | HM Land Registry | 150,000 |
| SG | SGD | ±8% (중간) | URA API | 120,000 |
| JP | JPY | ±5% (엄격) | REIT-DB | 200,000 |
| DE | EUR | ±8% (중간) | Zillium | 130,000 |
| AU | AUD | ±10% (완화) | RP Data | 110,000 |
| CA | CAD | ±10% (완화) | StatsCan | 140,000 |
| TH | THB | ±15% (최대 완화) | Proppy | 95,000 |
| HK | HKD | ±8% (중간) | Centaline | 105,000 |

### 1.3 네트워크 접근성 사전 평가

**중요**: 이 원격 실행 환경은 아웃바운드 egress 정책으로 특정 도메인을 차단할 수 있음이 이미 확인됨(data.go.kr, MOLIT, LH 모두 403). 8개국 API 실행 전 각 도메인 접근성을 사전 테스트해야 함:

```bash
# 각 국가 API 접근성 사전 테스트 (실제 실행 전 필수)
curl -sS -o /dev/null -w "%{http_code}\n" https://landregistry.data.gov.uk  # UK
curl -sS -o /dev/null -w "%{http_code}\n" https://www.ura.gov.sg           # SG
curl -sS -o /dev/null -w "%{http_code}\n" https://www.reinet.or.jp         # JP
# ... 등
```

접근 차단 시 **KR과 동일한 합성 데이터 전략**으로 즉시 전환.

---

## 2. 목표 아키텍처

```
Global AVM System
│
├── Per-Country Pipeline (KR 템플릿 재사용)
│   ├── generate_{country}_realistic_data.py
│   ├── train_{country}_model.py
│   ├── phase13_model_converter.py --country={country}
│   └── output/models_ir/{country}/
│
├── Unified Ensemble Engine (country-aware)
│   ├── avm_core_engine.py (country 파라미터 추가)
│   ├── avm_ensemble_engine.py (country별 모델 디렉토리 라우팅)
│   └── avm_coldstart.py (country별 펀더멘털 모델)
│
├── Currency & Unit Normalization Layer (신규)
│   ├── currency_converter.py (GBP/SGD/JPY/EUR/AUD/CAD/THB/HKD → USD 기준 정규화)
│   ├── unit_converter.py (sqft ↔ sqm, 국가별 면적 단위 통일)
│   └── tolerance_mapper.py (국가별 TOLERANCE_MAP 적용)
│
└── Multi-Country API Service
    ├── POST /api/valuation/{country_code}
    ├── GET /api/countries (지원 국가 목록)
    └── 국가별 모델 자동 라우팅
```

---

## 3. 국가별 우선순위 (2차 델타값 분석)

데이터 성숙도, API 접근성 예상 난이도, 시장 규모를 반영한 우선순위:

```
1순위: SG (싱가포르) - URA API 데이터 품질 높음, 소규모 시장으로 빠른 검증
2순위: HK (홍콩) - Centaline 데이터 신뢰도 높음, SG와 유사한 규모
3순위: UK (영국) - HM Land Registry 공개 데이터셋 존재 (bulk download 가능성)
4순위: AU (호주) - RP Data 상용 API, tolerance 완화로 리스크 낮음
5순위: CA (캐나다) - StatsCan 공식 통계 신뢰도 높으나 지역 편차 큼
6순위: DE (독일) - Zillium 데이터 접근성 불확실
7순위: JP (일본) - REIT-DB 규모 크나 엄격한 tolerance(±5%) 부담
8순위: TH (태국) - Proppy 데이터 성숙도 낮음, tolerance 완화(±15%)로 후순위 배치
```

---

## 4. 리스크 관리

| 리스크 | 확률 | 영향 | 대응책 |
|--------|------|------|--------|
| 8개국 API 모두 네트워크 정책 차단 | 40% | 전체 일정 지연 | KR과 동일한 합성 데이터 전략 즉시 전환 (검증된 폴백) |
| 통화 변동성 (환율 정규화 오류) | 20% | 모델 정확도 저하 | 고정 환율 스냅샷 + 정기 업데이트 스케줄 |
| 국가별 법적/규제 데이터 제약 | 25% | 특정 국가 수집 불가 | 공개 데이터셋/합성 데이터로 대체, 법무 검토 |
| 8개 모델 동시 서빙 리소스 부담 | 15% | API 지연 | 국가별 lazy loading, 캐싱 전략 |

---

## 5. 성공 기준

```
✅ 8개국 각각:
├── 합성 또는 실거래 데이터 10,000+ 레코드
├── R² > 0.80 (국가별 데이터 성숙도 감안, KR 0.84 대비 완화)
├── MAPE < TOLERANCE_MAP[country] 기준
└── ONNX 변환 완료 (OpenVINO IR은 선택)

✅ 통합 시스템:
├── 8개국 통화/단위 정규화 레이어 완성
├── 국가별 API 라우팅 (/api/valuation/{country_code})
└── 통합 테스트 스위트 (국가당 최소 10개 테스트, 총 80+개)
```

---

## 6. 결론

Phase 13.1-GBL은 **한국(KR) 파이프라인에서 검증된 패턴을 재사용**하는 확장 작업으로, 델타값(0.005)은 낮지만(장기 과제) 이미 증명된 아키텍처 덕분에 실행 리스크는 상대적으로 낮습니다. 특히 이번 세션에서 확인된 **정부 API 네트워크 차단 이슈**는 8개국에도 동일하게 적용될 가능성이 높으므로, 처음부터 "합성 데이터 우선 개발 → 실데이터 교체" 전략을 기본값으로 채택합니다.

---

**작성자**: Claude Sonnet 5
**다음 단계**: Phase 13.1-GBL 기술 명세서 & WBS 작성
