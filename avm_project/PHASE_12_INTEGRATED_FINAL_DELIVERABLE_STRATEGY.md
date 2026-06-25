# Phase 12 최종 산출물 통합 전략
## 가격 검증 로직 + 국제 AVM 데이터 + Excel/PDF 생성

**작성일**: 2026-06-25  
**버전**: v1.0 (통합 전략)

---

## 📋 문제 분석: 3개 요소 통합

### 1단계: 기초 데이터 양식 (이미 분석 완료)
```
Loan4U_QC_v1.1_before_fill.xlsx (5개 시트)
├─ Report: 리포트 템플릿 (40행 × 18열)
├─ 아파트: 997행 × 32열
├─ 빌라: 1000행 × 31열
├─ RAW: 원본 데이터 (1000행 × 29열)
└─ AIpredict: 최종 예측 (462행 × 16열)
```

### 2단계: 가격 검증 코드 (새로 분석)
```
loan4u_price_crosscheck.py (1157줄)
├─ UpdateAudit 시트 분석
├─ 가격 편차율 계산
├─ 실거래 반영 판정
├─ 외부 출처 CSV 매칭
├─ 교정 결과 분류
├─ 검토요약 시트 생성
└─ 원본 시트 교정표시
```

### 3단계: Phase 12 국제 확장 데이터 (기존 작성)
```
PHASE_12_DETAILED_SPECIFICATION.md
PHASE_12_WBS_DETAILED.md
phase12_international_expansion_implementation.py
├─ 8개국 진출 계획
├─ 월별 누적 지표
├─ 재무 분석
└─ B2B 파트너 정보
```

---

## 🎯 통합 목표

```
Phase 12 최종 산출물 = 가격 검증 로직 + 기초 데이터 구조 + 국제 AVM 데이터

입력:
  Loan4U_QC_v1.1_before_fill.xlsx (기초 데이터)
  + Phase 12 국제 확장 데이터 (JSON/Python)
  + (선택) 외부 출처 CSV (Naver, KB, REB, ASIL)

처리:
  1. 기초 데이터 구조 확장 (8개국 데이터 추가)
  2. 가격 검증 로직 적용 (국가별, 모델별)
  3. UpdateAudit 방식의 교정 결과 생성
  4. 검토요약 시트 통합
  5. Excel 최종 완성
  6. PDF 리포트 생성

출력:
  Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
  + Loan4U_Phase12_Final_Report.pdf
```

---

## 🔧 상세 구현 전략 (5단계)

### Phase 1: 기초 데이터 확장 (Excel 시트 구조 설계)

#### 신규 Excel 구조
```
Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
├─ 검토요약 (신규, 가격 검증 결과)
│  ├─ 입력/출력 파일 정보
│  ├─ UpdateAudit 검토 결과 집계
│  ├─ 가격 부합성 판정 통계
│  └─ 주의사항 및 운영 가이드
│
├─ Report (기존 -> 확장)
│  ├─ LOAN4U QC GLOBAL REPORT
│  ├─ Phase 12: International Market Entry
│  ├─ 글로벌 KPI (투자액, 월수익, 사용자, 파트너)
│  └─ 국가별 진출 계획 요약
│
├─ 아파트 (국내 기초)
│  └─ 가격 검증 컬럼 추가 (UpdateAudit 방식)
│
├─ 빌라 (국내 기초)
│  └─ 가격 검증 컬럼 추가
│
├─ RAW (국제 데이터 통합)
│  └─ 8개국 × ~1000건 통합 원본 데이터
│
├─ AIpredict (국내 최종 예측)
│  └─ 가격 검증 결과 통합
│
├─ UK_Residential (신규, 영국)
├─ UK_Prediction (신규)
├─ SG_Residential (신규, 싱가포르)
├─ SG_Prediction (신규)
├─ JP_Residential (신규, 일본)
├─ JP_Prediction (신규)
├─ ... (Germany, Australia, Canada, Thailand, Hong Kong)
│
└─ GlobalAIpredict (신규, 국제 통합 예측)
   └─ 8개국 모든 예측 결과 + 가격 검증
```

#### UpdateAudit 방식 컬럼 추가
```
기존 시트(아파트/빌라/RAW)에 추가될 컬럼:
  • 교정결과 (실거래 기반 업데이트 / 출처 기반 적정 / 추가확인 / 편차주의)
  • 가격부합성 (적정 / 확인필요 / 편차주의 / 추가확인)
  • 가격편차율 (%)
  • 외부출처검토 (네이버 / REB / 아실 / KB)
  • 출처URL
  • 최종조치 (유지 / 원자료 재확인 / 가격 재검증 필요 / 추가 자료 확보)
  • 검토일시
```

---

### Phase 2: 가격 검증 로직 통합

#### 수정할 조건들 (국제 확장 맞춤화)

```python
# 기본 검증 기준 (기존)
외부 출처 평균 대비:
  ±5% 이내       → 적정
  ±10% 이내      → 확인필요
  ±10% 초과      → 편차주의

# 국제 확장용 추가 기준
국가별 시장 특성:
  UK:      ±5-8% (보수적 감정)
  SG:      ±8-12% (높은 변동성)
  JP:      ±5-8% (안정적 시장)
  DE:      ±6-10% (중간 수준)
  AU:      ±8-15% (높은 변동성)
  CA:      ±8-15% (지역별 편차)
  TH:      ±10-15% (새로운 시장)
  HK:      ±8-12% (높은 밀도)

모델 버전별 신뢰도:
  v1.0:    기준값 (100%)
  v1.1:    개선된 모델 (95-100%)
  v1.2:    Phase 12 모델 (90-95%)
```

#### 검증 로직 흐름 (Phase 12 확장)

```python
def classify_price_conformity_phase12(
    old_price: Optional[float],
    new_price: Optional[float],
    country: str,
    model_version: str,
    real_transaction_applied: bool,
    source_records: Optional[List[PriceSourceRecord]] = None,
) -> Tuple[str, Optional[float], str]:
    """
    Phase 12 국제 데이터용 가격 부합성 판정
    
    기준:
    1. 국가별 시장 특성 반영
    2. 모델 버전별 신뢰도 조정
    3. 실거래 반영 여부 판단
    4. 외부 출처 편차 계산
    """
    
    # 국가별 편차 허용 범위
    tolerance_map = {
        "UK": 0.05,
        "SG": 0.08,
        "JP": 0.05,
        "DE": 0.06,
        "AU": 0.08,
        "CA": 0.08,
        "TH": 0.10,
        "HK": 0.08,
    }
    
    tolerance = tolerance_map.get(country, 0.10)
    
    # 모델 신뢰도 조정
    model_confidence = {
        "v1.0": 1.0,
        "v1.1": 0.98,
        "v1.2": 0.95,  # Phase 12는 검증 단계
    }
    
    confidence = model_confidence.get(model_version, 0.90)
    adjusted_tolerance = tolerance / confidence
    
    # 외부 출처가 있으면 먼저 비교
    if source_records:
        source_prices = [r.deal_price for r in source_records 
                        if r.deal_price and r.deal_price > 0]
        if source_prices:
            avg_source = sum(source_prices) / len(source_prices)
            deviation_ratio = (new_price - avg_source) / avg_source
            
            abs_dev = abs(deviation_ratio)
            if abs_dev <= adjusted_tolerance * 0.5:
                return "적정", deviation_ratio, f"외부 출처 기준 ±{adjusted_tolerance*100:.1f}% 이내"
            if abs_dev <= adjusted_tolerance:
                return "확인필요", deviation_ratio, f"외부 출처 기준 ±{adjusted_tolerance*100:.1f}% 이내"
            return "편차주의", deviation_ratio, f"외부 출처 기준 ±{adjusted_tolerance*100:.1f}% 초과"
    
    # 외부 출처 없을 때: 실거래 반영 여부로 판정
    if real_transaction_applied:
        internal_dev = (new_price - old_price) / old_price if old_price else 0
        if abs(internal_dev) <= adjusted_tolerance:
            return "적정", internal_dev, f"{country} 실거래 반영 ({model_version})"
        return "편차주의", internal_dev, f"{country} 실거래 반영이나 편차 {abs(internal_dev)*100:.1f}%"
    
    return "추가확인", None, f"{country} 외부 출처 미확보 및 실거래 반영 불명"
```

---

### Phase 3: 국가별 데이터 시트 생성

#### 각 국가 시트 구조 (2개 시트/국가)

```
예시: 영국 (UK)

[UK_Residential] - 부동산 기초 데이터
┌─────────────────────────────────────────────────────┐
│ 번호 | 지역 | 우편코드 | 주소 | 부동산유형 | 거래가 │
│  1  | Westminster | SW1A 1AA | ... | Apartment | 780,000 GBP │
│  2  | Kensington | SW7 2AA  | ... | House | 1,200,000 GBP │
│ ... │                                                  │
└─────────────────────────────────────────────────────┘

+ 추가 컬럼:
  • 면적 (sqm)
  • 건축년도 (Build_year)
  • MAARS예측가 (GBP)
  • 신뢰도 (%)
  • 모델버전

[UK_Prediction] - 예측 결과 + 가격 검증
┌──────────────────────────────────────────────────┐
│ 번호 | 주소 | 부동산유형 | 거래가 | 예측가 | 편차율 │
│  1  | ... | Apartment | 780,000 | 750,000 | -3.8% │
│  2  | ... | House | 1,200,000 | 1,180,000 | -1.7% │
│ ... │                                             │
└──────────────────────────────────────────────────┘

+ 가격 검증 컬럼:
  • 교정결과
  • 가격부합성
  • 가격편차율
  • 최종조치
  • 검토메모
```

---

### Phase 4: 검토요약 시트 통합

#### 검토요약 시트 구조 (기존 + 확장)

```
[검토요약] - 가격 검증 종합 보고

Section 1: 기본 정보
  • 입력 파일: Loan4U_QC_v1.1_before_fill.xlsx
  • 출력 파일: Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
  • 검토일시: 2026-06-25 XX:XX:XX
  • 국제 확장: Phase 12 (8개국)

Section 2: 검토 범위
  • UpdateAudit 시트: ✓ 존재
  • 원본 데이터 시트: 아파트 / 빌라 / RAW / AIpredict
  • 국제 데이터: UK / SG / JP / DE / AU / CA / TH / HK
  • 총 검토 행 수: ~10,000행

Section 3: 국가별 검토 결과 (테이블)
  ┌────────┬──────┬────────┬────────┬──────────┬──────────┐
  │ 국가   │ 부합 │ 적정 │ 확인필요 │ 편차주의 │ 실거래반영│
  ├────────┼──────┼────────┼────────┼──────────┼──────────┤
  │ UK     │  95% │ 200건 │  50건 │   10건  │   85%    │
  │ SG     │  92% │ 150건 │  48건 │   12건  │   78%    │
  │ JP     │  94% │ 180건 │  55건 │   15건  │   82%    │
  │ ... (DE, AU, CA, TH, HK)                            │
  │ 합계   │  93% │ 1200건│ 350건│   100건 │   80%    │
  └────────┴──────┴────────┴────────┴──────────┴──────────┘

Section 4: 주의사항
  1. Phase 12 데이터는 검증 단계 데이터입니다
  2. 모델 버전별 신뢰도 차이를 고려하세요
  3. 외부 출처는 선택사항입니다 (CSV 입력 시 자동 반영)
  4. 편차주의 항목은 원자료 재확인 필요
  5. 최종 가격 확정은 사람의 검토를 거쳐야 합니다
```

---

### Phase 5: Excel 생성 및 PDF 리포트

#### Excel 파일 생성 Python 코드

```python
# 기존 loan4u_price_crosscheck.py를 확장한 Phase 12 버전

def run_phase12_pipeline(
    input_path: Path,
    phase12_data: Dict[str, Any],  # JSON 형식의 Phase 12 데이터
    output_path: Path,
    source_dir: Optional[Path] = None,
    review_date: Optional[str] = None,
) -> None:
    """
    Phase 12 국제 확장 + 가격 검증 통합 파이프라인
    
    입력:
      1. 기초 데이터 Excel (Loan4U_QC_v1.1_before_fill.xlsx)
      2. Phase 12 JSON 데이터 (countries_strategy.json 등)
      3. 외부 출처 CSV (선택)
    
    처리:
      1. 기초 Excel 로드
      2. Phase 12 국가별 데이터 추가
      3. UpdateAudit 방식 가격 검증
      4. 국가별 신뢰도 조정
      5. 검토요약 시트 생성
      6. 스타일링 및 최종 포맷
    
    출력:
      Loan4U_QC_v1.1_Phase12_Global_Corrected_YYYYMMDD.xlsx
    """
    
    print("[1/8] 기초 Excel 로드")
    wb = load_workbook(input_path)
    
    print("[2/8] Phase 12 JSON 데이터 로드")
    # countries_strategy.json, uk_expansion_plan.json 등
    
    print("[3/8] 외부 출처 CSV 로드")
    source_records = load_source_csv(source_dir)
    
    print("[4/8] 국가별 데이터 시트 생성")
    for country_code, country_data in phase12_data.items():
        create_country_sheets(wb, country_code, country_data)
    
    print("[5/8] UpdateAudit 방식 가격 검증 (국내)")
    process_domestic_audit(wb, source_records, review_date)
    
    print("[6/8] 국제 데이터 가격 검증 (국가별 신뢰도 적용)")
    process_international_audit(wb, phase12_data, source_records, review_date)
    
    print("[7/8] 검토요약 시트 생성 (Phase 12 확장)")
    create_phase12_review_summary(wb, phase12_data, output_path, review_date)
    
    print("[8/8] 최종 스타일 적용 및 저장")
    apply_workbook_final_formatting(wb)
    wb.save(output_path)
    
    print(f"✅ 완료: {output_path}")
```

#### PDF 리포트 생성

```python
def generate_phase12_pdf_report(
    excel_path: Path,
    output_pdf_path: Path,
    phase12_summary: Dict[str, Any],
) -> None:
    """
    Phase 12 최종 리포트 PDF 생성 (1페이지)
    
    섹션:
      1. 헤더 (LOAN4U QC v1.1 - Phase 12)
      2. 글로벌 KPI (투자, 수익, 사용자, 파트너)
      3. 국가별 진출 현황 (테이블 + 차트)
      4. 실행 일정 (Gantt)
      5. 가격 검증 결과 요약
      6. 재무 분석 (ROI)
    """
    
    # HTML 템플릿 생성 후 weasyprint로 PDF 변환
    html_content = render_phase12_html_template(phase12_summary)
    
    # weasyprint를 사용하여 PDF 생성
    from weasyprint import HTML, CSS
    HTML(string=html_content).write_pdf(output_pdf_path)
```

---

## 📊 최종 산출물 규모

### Excel 파일
```
Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx

시트 수: 21개
├─ 검토요약 (신규)
├─ Report (확장)
├─ 아파트 (확장)
├─ 빌라 (확장)
├─ RAW (확장)
├─ AIpredict (확장)
├─ UK_Residential, UK_Prediction
├─ SG_Residential, SG_Prediction
├─ JP_Residential, JP_Prediction
├─ DE_Residential, DE_Prediction
├─ AU_Residential, AU_Prediction
├─ CA_Residential, CA_Prediction
├─ TH_Residential, TH_Prediction
├─ HK_Residential, HK_Prediction
└─ GlobalAIpredict (신규)

크기: ~300-400MB
행 수: ~10,000행
컬럼 수: 평균 20-25개/시트

포함 데이터:
  • 국내: 아파트(997) + 빌라(1000) + RAW(1000) = 2,997개
  • 국제: 8개국 × 200-550개 = ~3,000개
  • 총 부동산: ~6,000개
  • 가격 검증: 각 부동산별
```

### PDF 리포트
```
Loan4U_Phase12_Final_Report.pdf

페이지: 1
크기: ~500KB
포함:
  1. 제목/헤더
  2. 글로벌 KPI (4개 지표)
  3. 국가별 진출 현황 (테이블)
  4. 월별 누적 지표 (차트)
  5. 재무 분석 (ROI 표)
  6. 실행 일정 (타임라인)
```

---

## 🔄 실행 흐름도

```
입력 데이터
├─ Loan4U_QC_v1.1_before_fill.xlsx (기초)
├─ countries_strategy.json (Phase 12)
├─ uk_expansion_plan.json
├─ singapore_expansion_plan.json
├─ japan_expansion_plan.json
├─ (외부 출처 CSV - 선택)
│  ├─ naver_price.csv
│  ├─ kb_price.csv
│  ├─ reb_price.csv
│  └─ asil_price.csv
└─ b2b_partnerships.json

      ↓ (Python 처리)
      
[통합 파이프라인]
├─ Step 1: Excel 로드
├─ Step 2: JSON 데이터 파싱
├─ Step 3: 외부 CSV 로드
├─ Step 4: 국가별 시트 생성
├─ Step 5: 가격 검증 (국가별 신뢰도)
├─ Step 6: 검토요약 생성
├─ Step 7: 스타일링
├─ Step 8: Excel 저장
└─ Step 9: PDF 생성

      ↓

출력 파일
├─ Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
│  ├─ 21개 시트
│  ├─ ~10,000행 데이터
│  └─ 가격 검증 완료
└─ Loan4U_Phase12_Final_Report.pdf
   └─ 1페이지 리포트
```

---

## 💡 핵심 가치

### 1. 일관성
- 기초 데이터 구조 유지 (Loan4U 표준)
- 가격 검증 로직 동일 적용 (국내 + 국제)
- UpdateAudit 방식 통일

### 2. 확장성
- 새로운 국가 추가 용이
- 모델 버전 관리 명확
- 외부 출처 자동 통합

### 3. 신뢰성
- 국가별 시장 특성 반영
- 모델 버전별 신뢰도 조정
- 자동화 + 사람의 검토

### 4. 운영성
- 단일 Python 파일 실행
- 자동 리포트 생성
- 추적 가능한 감사 로그

---

## 🚀 다음 단계

### 즉시 (Week 1)
```
☐ Python 통합 파일 작성 (loan4u_phase12_pipeline.py)
☐ 국가별 샘플 데이터 준비
☐ 외부 출처 CSV 형식 정의
```

### 단기 (Week 2)
```
☐ Excel 파일 생성 및 검증
☐ PDF 리포트 생성
☐ 스타일링 완료
```

### 최종 (Week 3)
```
☐ 전체 통합 테스트
☐ 품질 검증
☐ 최종 산출물 배포
```

---

## 📌 사용자 의사결정 필요

```
1️⃣ 외부 출처 데이터 범위
   ☐ 국내만 (기존 UpdateAudit)
   ☐ 국내 + 국제 (CSV 형식)
   ☐ 모두 포함하지 않음

2️⃣ PDF 리포트 형식
   ☐ 1페이지 (권장)
   ☐ 2-3페이지 (상세)
   ☐ 필요 없음

3️⃣ 스타일링 선호도
   ☐ 기존 Loan4U 스타일 유지
   ☐ Phase 12 새 스타일
   ☐ 혼합형

4️⃣ 우선순위
   ☐ Excel 먼저
   ☐ PDF 먼저
   ☐ 동시 진행
```

---

**준비 완료!**

"**시작**" 명령으로 Python 통합 파일 작성을 시작할 수 있습니다.
