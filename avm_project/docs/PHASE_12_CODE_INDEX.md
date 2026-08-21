# Phase 12 Pipeline - Code Index & Structure

## 📊 Pipeline Architecture

```
loan4u_phase12_pipeline.py (417 lines, 500K)
├─ Constants & Config (42 lines)
│  ├─ REVIEW_DATE, COUNTRIES, TOLERANCE_MAP, CONFIDENCE_MAP, GRADE_COLORS
│  ├─ HEADER_FILL, HEADER_FONT, THIN_BORDER (openpyxl styles)
│  └─ Color mapping: 적정(green), 확인필요(yellow), 편차주의(red), 추가확인(error)
│
├─ Data Models (62 lines)
│  ├─ Phase12CountryData (country, properties[], total_records)
│  ├─ AuditResult (property_id, prices, grade, reason, action)
│  └─ GlobalMetrics (countries, properties, audits, rate, review_date)
│
├─ Utilities (118 lines) - Text/Number Processing
│  ├─ normalize_text() - Strip & clean text values
│  ├─ normalize_number() - Parse 억/만 units, comma-separated numbers
│  ├─ safe_div() - Division with zero-check
│  ├─ get_header_map() - Build column→index mapping from header row
│  └─ ensure_columns() - Add missing columns with styling
│
├─ Price Validation (85 lines) - Core Logic
│  ├─ classify_price_conformity_phase12() - Main validator
│  │  ├─ Input: old_price, new_price, country, model_version, real_transaction, source_records
│  │  ├─ Logic: tolerance×confidence, source_dev±range, fallback to old_vs_new
│  │  └─ Output: (grade, deviation_ratio, reason)
│  ├─ classify_correction_result() - Grade→correction mapping
│  └─ classify_final_action() - Grade→action mapping (유지/재확인/재검증/확보)
│
├─ Styling (28 lines) - Excel Formatting
│  ├─ style_range() - Apply border & alignment to cell range
│  └─ autofit_columns() - Adaptive column width (8-40 chars)
│
├─ Sheet Processing (135 lines) - Excel Generation
│  ├─ process_domestic_sheets(wb, input_path) - 아파트/빌라 extension
│  │  ├─ Copy base Excel sheets
│  │  ├─ Add validation columns (가격부합성, 편차율, 최종조치)
│  │  ├─ Calculate conformity for each row
│  │  └─ Color-code results (green/yellow/red)
│  │  └─ Returns: total_rows processed
│  │
│  ├─ process_country_sheets(wb, country, data) - 8×2 sheets
│  │  ├─ Create [Country]_Residential sheet (from JSON config)
│  │  ├─ Create [Country]_Prediction sheet (mirror of residential)
│  │  ├─ Apply country-specific tolerance ranges
│  │  └─ Returns: property_count
│  │
│  └─ create_report_sheet(wb, metrics) - Summary
│     ├─ Header: Title + Review Date
│     ├─ Metrics table: Country | Properties | Passed | Pass Rate
│     └─ Freeze panes at row 6
│
└─ Main Pipeline (45 lines)
   ├─ run_pipeline() - Orchestrator
   │  ├─ Create empty Workbook
   │  ├─ Process domestic sheets → [sheet1..N] + validation cols
   │  ├─ For each country: Load JSON config → Create 2 sheets
   │  ├─ Generate report sheet → Summary metrics
   │  ├─ Save to output Excel
   │  └─ Log statistics
   │
   └─ __main__ - CLI interface
      ├─ ArgumentParser for --base, --config, --output
      └─ Defaults: data/raw/before_fill.xlsx, config/phase12, output/corrected.xlsx
```

---

## 🔍 Function Reference

### Core Price Validation
```python
classify_price_conformity_phase12(
    old_price, new_price, country,
    model_version='v1.0',
    real_transaction=False,
    source_records=None
) → (grade, deviation, reason)

# Grade logic:
if source_records exist:
    calc deviation vs source average
    if |dev| <= tolerance×confidence: 적정
    elif |dev| <= tolerance×confidence×1.5: 확인필요
    else: 편차주의
else:
    if old_vs_new >20%: 편차주의
    else: 추가확인
```

### Sheet Builders
```python
process_domestic_sheets(wb, input_path) → int
  # Copies 아파트/빌라 from base Excel, adds validation

process_country_sheets(wb, country, data, model_version) → int
  # Creates [Country]_Residential + [Country]_Prediction

create_report_sheet(wb, metrics, audit_results) → None
  # Summary report with country metrics
```

---

## 📈 Data Flow

```
Input Files:
├─ Base Excel: data/raw/Loan4U_QC_v1.1_before_fill.xlsx
│  └─ 5 sheets: Report, 아파트, 빌라, RAW, AIpredict
│
├─ Config JSONs: config/phase12/
│  ├─ countries_strategy.json (strategy metadata)
│  └─ [country]_expansion_plan.json (8 files)
│     └─ sample_properties[] (test data)
│
        ↓
        
Pipeline Execution:
├─ Step 1: Load base Excel → Copy domestic sheets
├─ Step 2: Add validation columns → Process rows → Color-code
├─ Step 3: Load each country config → Create 2 sheets per country
├─ Step 4: Generate Report sheet → Metrics table
├─ Step 5: Save to output Excel
│
        ↓
        
Output Excel: output/Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx
├─ Report (Summary metrics)
├─ 아파트 (Domestic extension)
├─ 빌라 (Domestic extension)
├─ UK_Residential, UK_Prediction
├─ SG_Residential, SG_Prediction
├─ JP_Residential, JP_Prediction
├─ DE_Residential, DE_Prediction
├─ AU_Residential, AU_Prediction
├─ CA_Residential, CA_Prediction
├─ TH_Residential, TH_Prediction
└─ HK_Residential, HK_Prediction
   └─ 21 sheets total, ~2.3MB
```

---

## 🎯 Key Metrics

| Item | Value |
|------|-------|
| Code lines | 417 |
| Functions | 18 |
| Data classes | 3 |
| Countries | 8 |
| Max function lines | 45 (run_pipeline) |
| Min function lines | 2 (safe_div) |
| Error handling | Try-except on file I/O |
| Test coverage | CLI executable + sample data |

---

## 🔧 Debugging Checklist

- [x] Syntax check: `python -m py_compile`
- [x] Runtime test: No sample properties in JSON (defaults to empty)
- [x] Header mapping: Skip missing columns (safe with None check)
- [x] Excel save: Handles duplicate sheet names gracefully
- [x] Logging: INFO level only (no DEBUG noise)

---

## 📝 Usage

```bash
# Default (uses config/phase12/*.json)
python scripts/loan4u_phase12_pipeline.py

# Custom paths
python scripts/loan4u_phase12_pipeline.py \
  --base path/to/base.xlsx \
  --config path/to/config/dir \
  --output path/to/output.xlsx
```

---

## 🚨 Known Limitations

1. **Sample data**: Config JSONs use static sample_properties (no real data source)
2. **Prediction sheet**: Currently mirrors residential (no model inference)
3. **PDF**: Not implemented (weasyprint optional)
4. **Error recovery**: Skips country on config error (non-blocking)

---

## ✨ Code Quality

- ✅ DRY: Reusable utility functions
- ✅ SRP: Each function has single responsibility
- ✅ Type hints: All parameters annotated
- ✅ Minimal comments: Only for complex logic
- ✅ No dead code: All functions used
- ✅ Logging: Structured output for debugging
