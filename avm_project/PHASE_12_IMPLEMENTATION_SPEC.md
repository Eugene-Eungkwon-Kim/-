# Phase 12 Implementation Spec - Concise Edition

## Deliverables
1. `loan4u_phase12_pipeline.py` - Unified pipeline (500-700 lines)
2. `Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx` - 21 sheets
3. `Loan4U_Phase12_Final_Report.pdf` - 1 page summary

---

## Core Architecture

### Data Flow
```
Input: base_excel + json_configs → Process → Output: xlsx + pdf
```

### Module Structure
```python
# 1. Data Models (dataclass)
Phase12CountryData, AuditResult, GlobalMetrics

# 2. Utilities  
normalize_text/number, make_property_key, style_range, autofit_columns

# 3. Price Validation
classify_price_conformity_phase12(old_price, new_price, country) → (grade, deviation, reason)
classify_correction_result(grade) → result_class
classify_final_action(grade, model_confidence) → action

# 4. Sheet Processing
process_domestic_sheets(wb, base_data)  # 아파트, 빌라 확장
process_country_sheets(wb, country_code, country_data)  # 8개국 × 2 sheets

# 5. Integration & Output
create_report_sheet(wb, audit_results)
apply_formatting(wb)
generate_pdf(xlsx_path) → pdf_path
```

---

## Key Functions

### Price Validation Logic
```python
def classify_price_conformity_phase12(
    old_price: float,
    new_price: float, 
    country: str,
    model_confidence: float = 1.0,
    real_transaction: bool = False
) -> tuple[str, float, str]:
    """
    Returns: (conformity_grade, deviation_ratio, reason)
    Grades: 적정 | 확인필요 | 편차주의 | 추가확인
    
    Logic:
    - tolerance = TOLERANCE_MAP[country]  # ±5~15% by country
    - confidence_factor = model_confidence  # v1.0=1.0, v1.1=0.98, v1.2=0.95
    - adjusted_tolerance = tolerance * confidence_factor
    - deviation = abs(new_price - old_price) / old_price
    
    if deviation <= adjusted_tolerance: 적정
    elif deviation <= adjusted_tolerance * 1.5: 확인필요
    elif real_transaction: 편차주의
    else: 추가확인
    """
```

### Sheet Creation
```python
def process_domestic_sheets(wb, base_excel_path, output_excel_path):
    """Extend 아파트, 빌라 sheets with price validation results"""
    # Read base sheets → Apply validation → Write extended sheets

def process_country_sheets(wb, country_code, json_config):
    """Create Residential + Prediction sheets for each country"""
    # 8 countries × 2 sheets = 16 new sheets
    # Data source: json_config[country_code]

def create_report_sheet(wb, audit_results, countries_stats):
    """Summary sheet with KPI metrics and audit summary"""
```

### Workbook Output
```python
def apply_formatting(wb):
    """Apply header styles, colors, freeze panes"""
    # Header: bold, background color
    # Result cells: conditional color by grade (적정=green, 편차주의=red, etc)
    # Freeze panes: row 1

def generate_pdf(xlsx_path, pdf_path):
    """Convert xlsx summary to PDF report"""
    # HTML template → weasyprint/reportlab → pdf_path
```

---

## Constants & Configuration

```python
TOLERANCE_MAP = {
    'UK': 0.05, 'JP': 0.05, 'SG': 0.08, 'DE': 0.08,
    'HK': 0.08, 'AU': 0.10, 'CA': 0.10, 'TH': 0.15
}

CONFIDENCE_MAP = {
    'v1.0': 1.0,
    'v1.1': 0.98,
    'v1.2': 0.95
}

GRADE_COLORS = {
    '적정': 'C6EFCE',           # Green
    '확인필요': 'FFEB9C',       # Yellow
    '편차주의': 'FFC7CE',       # Light Red
    '추가확인': 'FF0000'        # Red
}

COUNTRIES = ['UK', 'SG', 'JP', 'DE', 'AU', 'CA', 'TH', 'HK']
```

---

## Input/Output Specs

### Input
- `base_excel`: Loan4U_QC_v1.1_before_fill.xlsx (5 sheets)
- `json_configs`: countries_strategy.json + country_*.json files
- Optional: country_data.csv files for external data

### Output
- `result_xlsx`: 21 sheets (5 domestic + 8×2 country + 1 global + 1 report)
- `result_pdf`: 1-page summary report with metrics table

---

## Execution Flow

```
1. Load base_excel → read 5 sheets
2. Load json configs → parse country data
3. Process domestic sheets → apply validation
4. Create country sheets (8 × 2) → populate from json
5. Create report sheet → aggregate metrics
6. Apply formatting → colors, styles
7. Save xlsx
8. Generate pdf from xlsx
9. Output summary
```

---

## Time Estimate: 2-3 hours for 500-700 lines
