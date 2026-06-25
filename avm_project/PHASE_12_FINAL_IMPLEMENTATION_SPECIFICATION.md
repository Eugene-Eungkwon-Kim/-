# Phase 12 최종 산출물 생성 - 상세 시행명세서
## Global Market Entry Final Deliverable Implementation

**프로젝트**: Loan4U QC v1.1 Phase 12  
**단계**: 최종 산출물 생성 (Step 1-4)  
**작성일**: 2026-06-25  
**실행기간**: 1주일 (5-7일)  
**예상 시간**: 6-8시간

---

## 🎯 Executive Summary

Phase 12 계획 단계의 완성도 높은 문서 (명세서, WBS, JSON 설정)를 기반으로 **실행 단계의 최종 산출물 3개**를 생성합니다.

### 생성 산출물

```
1️⃣ loan4u_phase12_pipeline.py (통합 Python 파이프라인)
   └─ 기초 데이터 + Phase 12 + 가격검증 통합 (1000+줄)

2️⃣ Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
   └─ 21개 시트, ~10,000행, 8개국 데이터 + 가격검증

3️⃣ Loan4U_Phase12_Final_Report.pdf
   └─ 1페이지 글로벌 요약 리포트
```

---

## 📋 Task 12.F: 통합 Python 파이프라인 구현

**목표**: loan4u_phase12_pipeline.py (1000+줄) 작성  
**기간**: 2-3시간  
**난이도**: 중상  
**선행조건**: 기존 코드 분석 완료 (loan4u_price_crosscheck.py)

### 12.F.1 모듈 구조 설계

```python
loan4u_phase12_pipeline.py
├─ 섹션 1: 임포트 & 설정 (50줄)
│  ├─ openpyxl, pandas, json, pathlib
│  ├─ 상수: DEFAULT_REVIEW_DATE, COUNTRY_CODES, TOLERANCE_MAP
│  └─ 색상/스타일 설정 (UpdateAudit 기준)
│
├─ 섹션 2: 데이터 모델 (30줄)
│  ├─ @dataclass Phase12CountryData
│  ├─ @dataclass AuditResult
│  └─ @dataclass GlobalMetrics
│
├─ 섹션 3: 유틸리티 함수 (100줄)
│  ├─ normalize_text/number
│  ├─ make_property_key
│  ├─ get_header_map, find_header_row
│  ├─ safe_div, format_ratio
│  └─ style_range_basic, autofit_columns
│
├─ 섹션 4: 가격 검증 로직 (150줄)
│  ├─ classify_price_conformity_phase12 (국가별 신뢰도)
│  ├─ classify_correction_result
│  ├─ classify_final_action
│  ├─ detect_real_transaction_applied
│  └─ build_source_status
│
├─ 섹션 5: 기초 시트 확장 (150줄)
│  ├─ process_domestic_sheets (아파트/빌라)
│  ├─ process_raw_sheet
│  └─ process_aipredict_sheet
│
├─ 섹션 6: 국제 데이터 시트 생성 (300줄)
│  ├─ create_country_sheets (for loop)
│  ├─ create_residential_sheet (각국)
│  ├─ create_prediction_sheet (각국)
│  └─ populate_country_data_from_json
│
├─ 섹션 7: 글로벌 통합 시트 (100줄)
│  ├─ create_global_raw_sheet
│  ├─ create_global_predict_sheet
│  └─ create_report_sheet_extended
│
├─ 섹션 8: 검토요약 시트 생성 (150줄)
│  ├─ create_phase12_review_summary
│  ├─ build_country_stats_table
│  └─ build_stat_comment
│
├─ 섹션 9: 최종 포맷팅 (80줄)
│  ├─ apply_header_styles
│  ├─ apply_result_fills (국가별 색상)
│  ├─ apply_workbook_final_formatting
│  └─ set_freeze_panes
│
├─ 섹션 10: PDF 생성 (100줄)
│  ├─ generate_html_template
│  ├─ render_country_summary_table
│  ├─ render_kpi_metrics
│  └─ convert_html_to_pdf
│
├─ 섹션 11: 파이프라인 메인 (150줄)
│  ├─ run_full_pipeline
│  ├─ load_excel_input
│  ├─ load_phase12_json_configs
│  ├─ load_source_csv_optional
│  ├─ execute_generation_steps
│  └─ validate_output
│
└─ 섹션 12: CLI & Main (80줄)
   ├─ parse_args
   ├─ main
   └─ if __name__ == "__main__"
```

### 12.F.2 핵심 함수 상세 설계

#### 함수 1: classify_price_conformity_phase12()

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
    국가별 시장 특성 + 모델 신뢰도를 반영한 가격 부합성 판정
    
    입력:
      - old_price: 기존 가격
      - new_price: 신규 가격
      - country: 국가코드 (UK, SG, JP, DE, AU, CA, TH, HK)
      - model_version: v1.0, v1.1, v1.2
      - real_transaction_applied: 실거래 반영 여부
      - source_records: 외부 출처 레코드 리스트
    
    로직:
      1. 국가별 편차 허용 범위 결정
         UK/JP: ±5% (보수적)
         SG/DE/HK: ±8% (중간)
         AU/CA/TH: ±10-15% (높은 변동성)
      
      2. 모델 신뢰도 조정
         v1.0: 1.0 (기준)
         v1.1: 0.98
         v1.2: 0.95 (검증 단계)
      
      3. 외부 출처 비교 (있으면 우선)
      4. 없으면 실거래 반영 여부 및 기존가 대비 변동률 판정
      5. 최종 등급 반환: 적정 / 확인필요 / 편차주의 / 추가확인
    
    출력:
      (가격부합성, 편차율, 판정사유)
    """
    
    # 국가별 허용범위 맵
    tolerance_map = {
        "UK": 0.05,
        "JP": 0.05,
        "SG": 0.08,
        "DE": 0.06,
        "AU": 0.10,
        "CA": 0.10,
        "TH": 0.12,
        "HK": 0.08,
    }
    
    # 모델 신뢰도
    model_confidence = {
        "v1.0": 1.0,
        "v1.1": 0.98,
        "v1.2": 0.95,
    }
    
    tolerance = tolerance_map.get(country, 0.10)
    confidence = model_confidence.get(model_version, 0.90)
    adjusted_tolerance = tolerance / confidence
    
    # ... 상세 로직
```

#### 함수 2: create_country_sheets()

```python
def create_country_sheets(
    wb: Workbook,
    country_code: str,
    country_data: Dict[str, Any],
    source_records_by_key: Dict[str, List],
    review_date: str,
) -> Dict[str, int]:
    """
    각 국가별로 2개 시트 생성 및 데이터 입력
    
    생성되는 시트:
      1. {country}_Residential: 부동산 기초 데이터
      2. {country}_Prediction: 예측 결과 + 가격 검증
    
    데이터 흐름:
      country_data (JSON) 
        → 부동산 객체 리스트 추출
        → 각 행에 가격 검증 로직 적용
        → 조건부 서식 적용 (색상)
        → 시트에 입력
    
    반환:
      생성된 시트 정보 딕셔너리
    """
```

#### 함수 3: create_phase12_review_summary()

```python
def create_phase12_review_summary(
    wb: Workbook,
    audit_results: Dict[str, List[AuditResult]],
    country_stats: Dict[str, Dict],
    phase12_metadata: Dict,
    output_path: Path,
) -> None:
    """
    검토요약 시트 생성 (기존 코드 확장)
    
    섹션:
      1. 기본 정보 (입력/출력 파일, 검토일시)
      2. 검토 범위 (8개국, ~10K행)
      3. 국가별 검토 결과 테이블
         - 국가 | 부합율 | 적정건수 | 확인필요 | 편차주의 | 실거래반영율
      4. 글로벌 KPI 통계
      5. 주의사항 (5개항)
    
    스타일:
      - 헤더: 진한 파란색 (1F4E78)
      - 적정: 초록색 (E2F0D9)
      - 확인필요: 황색 (FFF2CC)
      - 편차주의: 빨강색 (F4CCCC)
    """
```

### 12.F.3 입출력 데이터 명세

**입력 파일**:
```
1. Loan4U_QC_v1.1_before_fill.xlsx
   ├─ Report (40×18)
   ├─ 아파트 (997×32)
   ├─ 빌라 (1000×31)
   ├─ RAW (1000×29)
   └─ AIpredict (462×16)

2. Phase 12 JSON 설정 (config/phase12/)
   ├─ countries_strategy.json (8개국 전략)
   ├─ uk_expansion_plan.json
   ├─ singapore_expansion_plan.json
   ├─ japan_expansion_plan.json
   └─ (기타)

3. (선택) 외부 출처 CSV
   ├─ naver_price.csv
   ├─ kb_price.csv
   ├─ reb_price.csv
   └─ asil_price.csv
```

**출력 파일**:
```
1. Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
   ├─ 검토요약 (신규)
   ├─ Report (확장)
   ├─ 아파트 (확장)
   ├─ 빌라 (확장)
   ├─ RAW (확장)
   ├─ AIpredict (확장)
   ├─ UK_Residential, UK_Prediction (신규)
   ├─ SG_Residential, SG_Prediction (신규)
   ├─ JP_Residential, JP_Prediction (신규)
   ├─ DE_Residential, DE_Prediction (신규)
   ├─ AU_Residential, AU_Prediction (신규)
   ├─ CA_Residential, CA_Prediction (신규)
   ├─ TH_Residential, TH_Prediction (신규)
   ├─ HK_Residential, HK_Prediction (신규)
   └─ GlobalAIpredict (신규)
   
   크기: ~300-400MB
   행: ~10,000
   시트: 21개

2. Loan4U_Phase12_Final_Report.pdf
   └─ 1페이지 리포트 (500KB)
```

---

## 📋 Task 12.G: Excel 최종 파일 생성

**목표**: loan4u_phase12_pipeline.py 실행  
**기간**: 1시간  
**난이도**: 낮음 (자동화)

### 12.G.1 실행 명령

```bash
python loan4u_phase12_pipeline.py \
  --input Loan4U_QC_v1.1_before_fill.xlsx \
  --phase12-config config/phase12/countries_strategy.json \
  --uk-config config/phase12/uk_expansion_plan.json \
  --sg-config config/phase12/singapore_expansion_plan.json \
  --jp-config config/phase12/japan_expansion_plan.json \
  --de-config config/phase12/infrastructure_requirements.json \
  --output Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx \
  --source-dir ./optional_sources \
  --review-date "2026-06-25 14:30:00 KST"
```

### 12.G.2 검증 체크리스트

```
✅ 기본 시트 (5개)
   ☐ Report: 40행 × 20열 (글로벌 확장)
   ☐ 아파트: 997행 + 5개 검증 컬럼
   ☐ 빌라: 1000행 + 5개 검증 컬럼
   ☐ RAW: 1000행 + 글로벌 데이터
   ☐ AIpredict: 462행 + 검증 결과

✅ 국가별 시트 (16개)
   ☐ UK_Residential: 200-300행
   ☐ UK_Prediction: 200-300행 + 검증
   ☐ SG_Residential: 150-250행
   ☐ SG_Prediction: 150-250행 + 검증
   ☐ ... (JP, DE, AU, CA, TH, HK)

✅ 글로벌 통합 시트 (3개)
   ☐ GlobalAIpredict: 1500행 (모든 국가)
   ☐ 검토요약: 40행 (KPI + 통계)
   ☐ Report: 확장 (글로벌 KPI)

✅ 스타일링
   ☐ 헤더: 진한 파란색 + 흰글씨
   ☐ 조건부 서식: 적정(초록)/확인필요(황)/편차주의(빨강)
   ☐ 동결창: 헤더 행 고정
   ☐ 컬럼 너비: 자동 조정
   ☐ 필터: 활성화

✅ 데이터 무결성
   ☐ 총 행 수: ~10,000
   ☐ 가격 필드: 통화 형식 (₩, GBP, SGD 등)
   ☐ 백분율: % 형식
   ☐ 날짜: YYYY-MM-DD 형식
   ☐ 합계: 자동 계산 공식

✅ 파일 검증
   ☐ 파일 크기: 300-400MB
   ☐ 파일 열기 가능
   ☐ 손상 없음
   ☐ 인코딩: UTF-8
```

---

## 📋 Task 12.H: PDF 리포트 생성

**목표**: Loan4U_Phase12_Final_Report.pdf 생성  
**기간**: 1-2시간  
**난이도**: 중상 (HTML → PDF)

### 12.H.1 PDF 구성 (1페이지)

```
[페이지 1]

┌─────────────────────────────────────────────────────┐
│                      헤더 (15%)                      │
│  LOAN4U QC v1.1                                     │
│  Phase 12: Global Market Entry & International Exp. │
│  2026-06-25                                         │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  글로벌 KPI (20%)                    │
│  ┌──────────────┬──────────────┬──────────────┐    │
│  │ 투자액       │ 월 수익 목표 │ 활성사용자   │    │
│  │ $1,035K      │ 26.5-40.0억  │ 790-940명    │    │
│  └──────────────┴──────────────┴──────────────┘    │
│  B2B 파트너: 20-28개 | 운영국가: 8개 | ROI: 236배 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│             국가별 진출 현황 (45%)                  │
│  ┌────┬────────┬──────┬────────┬──────────┐        │
│  │ # │ 국가  │우선순위│월수익 │진출시기  │        │
│  ├────┼────────┼──────┼────────┼──────────┤        │
│  │ 1 │ UK    │  1  │4-6천  │M1-3     │        │
│  │ 2 │ SG    │  2  │2.5-4천│M1-3     │        │
│  │ 3 │ JP    │  3  │5-7천  │M1-3     │        │
│  │ 4 │ DE    │  4  │4.5-6천│M2-3     │        │
│  │ 5 │ AU    │  4  │3.5-5천│M2-3     │        │
│  │ 6 │ CA    │  4  │3-4.5천│M2-3     │        │
│  │ 7 │ TH    │  5  │1.5-2.5千│M3-4     │        │
│  │ 8 │ HK    │  5  │2.5-4千│M4-5     │        │
│  └────┴────────┴──────┴────────┴──────────┘        │
│                                                     │
│  📊 월별 누적 수익 추이                             │
│     Month 3: 11.5-16.0억원                         │
│     Month 6: 24.5-36.0억원  → 최종: 26.5-40.0억   │
│  📈 ROI: 92배 (M3) → 236배 (M6)                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│               실행 일정 (15%)                        │
│  Week 1-2: 데이터 수집 → Week 3-4: 모델 개발       │
│  Week 5-6: API 배포 → Week 7-8: 파트너십           │
│  Month 4-6: 추가 국가 확장                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│               재무 분석 (5%)                         │
│  투자: $1.035M | 연간예상: 30-48억원 | 회수: 5-7일 │
└─────────────────────────────────────────────────────┘
```

### 12.H.2 생성 방법

**Option A: HTML → PDF (권장)**

```python
from weasyprint import HTML, CSS
from jinja2 import Template

# 1. HTML 템플릿 생성
html_template = render_phase12_html_template(excel_data, phase12_summary)

# 2. CSS 스타일
css_styles = """
body { font-family: Arial, sans-serif; margin: 20px; }
h1 { color: #1F4E78; font-size: 18pt; }
table { width: 100%; border-collapse: collapse; }
th { background-color: #1F4E78; color: white; }
.metric { color: #2E75B6; font-weight: bold; }
"""

# 3. PDF 변환
HTML(string=html_template).write_pdf(
    output_path,
    stylesheets=[CSS(string=css_styles)]
)
```

**Option B: reportlab (대안)**

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.units import inch

doc = SimpleDocTemplate("output.pdf", pagesize=A4)
elements = []

# 헤더
elements.append(Paragraph("LOAN4U QC v1.1 - Phase 12", style_heading))
elements.append(Spacer(1, 0.2*inch))

# KPI 테이블
elements.append(create_kpi_table(phase12_summary))

# 국가별 테이블
elements.append(create_country_table(country_stats))

# PDF 생성
doc.build(elements)
```

### 12.H.3 콘텐츠 데이터 소스

```python
# Excel → 데이터 추출 → PDF

# 검토요약 시트에서 추출
  • 국가별 통계
  • 가격부합성 집계
  • 총 검토 행 수

# Report 시트에서 추출
  • 글로벌 KPI
  • 월별 누적 지표

# 설정 JSON에서 추출
  • 국가별 수익 목표
  • ROI 계산값
  • 실행 일정
```

---

## 📋 Task 12.I: 통합 검증 및 최종화

**목표**: 완성도 높은 최종 산출물 검증  
**기간**: 1-2시간  
**난이도**: 낮음 (체크리스트)

### 12.I.1 파일 검증

```
✅ Excel 파일 검증
   ☐ 파일 열기 가능 (손상 없음)
   ☐ 모든 21개 시트 존재
   ☐ 데이터 무결성 (NaN, 오류값 없음)
   ☐ 합계 공식 정확성
   ☐ 조건부 서식 적용 확인
   ☐ 파일 크기 합리적 (300-400MB)

✅ PDF 파일 검증
   ☐ 파일 열기 가능
   ☐ 레이아웃 정렬 확인
   ☐ 모든 데이터 표시
   ☐ 색상 및 폰트 정상
   ☐ 인쇄 가능성 확인

✅ 데이터 정확성
   ☐ 국가별 데이터 정렬 확인
   ☐ 가격 계산값 재확인
   ☐ 편차율 계산 검증
   ☐ 환율 변환 확인 (KRW, GBP, JPY 등)

✅ 메타데이터
   ☐ 파일명: 일관성 (YYYYMMDD 포함)
   ☐ 수정 일시: 정확성
   ☐ 작성자: "Claude Code Phase 12"
   ☐ 버전: v1.0 / v1.1 / v1.2 태그
```

### 12.I.2 품질 기준

```
✅ 완성도 지표
   • 데이터 커버리지: 8개국 100%
   • 검증 완료율: 가격부합성 분류 100%
   • 스타일 적용율: 100%
   • 문서화: README 포함

✅ 성능 지표
   • 파일 생성 시간: <5분
   • Excel 열기 시간: <10초
   • PDF 생성 시간: <30초
   • 메모리 사용: <2GB

✅ 접근성 지표
   • 모든 시트 자동필터: ✓
   • 헤더 동결: ✓
   • 컬럼 너비 자동 조정: ✓
   • 색상 구분성: ✓ (색맹 고려)
```

### 12.I.3 Git 커밋 및 문서화

```bash
# 1. 파일 추가
git add loan4u_phase12_pipeline.py
git add Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
git add Loan4U_Phase12_Final_Report.pdf

# 2. 커밋
git commit -m "Complete Phase 12 final deliverables

Generate production-ready files:
- loan4u_phase12_pipeline.py (1000+ lines, unified pipeline)
- Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx (21 sheets, 10K rows)
- Loan4U_Phase12_Final_Report.pdf (1 page executive summary)

Integrated components:
- Base data structure (Loan4U standard)
- Price validation logic (UpdateAudit method)
- Phase 12 international expansion data (8 countries)
- Country-specific tolerance ranges
- Model version confidence adjustment
- Automated review summary generation

Global coverage:
- 8 countries (UK, SG, JP, DE, AU, CA, TH, HK)
- ~10,000 property records
- Price validation & conformity assessment
- 21-sheet integrated workbook

Financial metrics:
- Total investment: $1.035M
- Monthly revenue target: 26.5-40.0억 원
- Expected ROI: 236배 (6 months)
- B2B partners: 20-28 companies

Quality assurance:
- Data integrity verified
- All formatting applied
- PDF report generated
- Production ready

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011nopRNerAzP7vxBfebqeDC"

# 3. 푸시
git push -u origin claude/eloquent-meitner-lqxu9r
```

### 12.I.4 최종 문서화

```markdown
# Phase 12 Final Deliverable - Implementation Report

## Overview
- 완료일: 2026-06-25
- 파일 3개 생성
- 총 개발 시간: 6-8시간
- 품질 평가: Production Ready

## 생성된 파일

### 1. loan4u_phase12_pipeline.py (1000+ 줄)
- 기능: 통합 Python 파이프라인
- 입력: 기초 Excel + Phase 12 JSON + 외부 출처 CSV
- 출력: 최종 Excel + PDF
- 테스트: ✅ 완료

### 2. Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
- 시트: 21개
- 행: ~10,000
- 크기: ~300-400MB
- 데이터: 8개국 + 가격검증 결과
- 스타일: 완전 적용

### 3. Loan4U_Phase12_Final_Report.pdf
- 페이지: 1
- 크기: ~500KB
- 콘텐츠: 글로벌 요약 리포트
- 인쇄 가능: ✅

## 다음 단계
- 최종 리뷰 및 승인 대기
- (선택) 추가 분석 또는 커스터마이징
```

---

## 🎯 Complete Execution Flow

```
Input Files (3가지)
├─ Loan4U_QC_v1.1_before_fill.xlsx
├─ Phase 12 JSON Configs (7개)
└─ Optional Source CSVs

    ↓ (loan4u_phase12_pipeline.py)
    
Processing Steps
├─ 1. Load & Parse Input
├─ 2. Extend Base Sheets
├─ 3. Create Country Sheets (8 countries × 2)
├─ 4. Apply Price Validation (Country-specific)
├─ 5. Generate Review Summary
├─ 6. Apply Formatting
├─ 7. Save Excel
├─ 8. Generate PDF
└─ 9. Validate Output

    ↓

Output Files (2개)
├─ Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
└─ Loan4U_Phase12_Final_Report.pdf

    ↓

Quality Assurance
├─ Data Integrity ✅
├─ File Validation ✅
├─ Format Check ✅
└─ Production Ready ✅
```

---

**준비 완료! 단계별 상세 설계 완성.**
