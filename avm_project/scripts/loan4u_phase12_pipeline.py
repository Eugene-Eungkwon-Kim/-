#!/usr/bin/env python3
"""
Loan4U Phase 12 Global Pipeline
Unified Excel/PDF generation with price validation across 8 countries.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Constants
REVIEW_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
COUNTRIES = ['UK', 'SG', 'JP', 'DE', 'AU', 'CA', 'TH', 'HK']
TOLERANCE_MAP = {
    'UK': 0.05, 'JP': 0.05, 'SG': 0.08, 'DE': 0.08,
    'HK': 0.08, 'AU': 0.10, 'CA': 0.10, 'TH': 0.15
}
CONFIDENCE_MAP = {'v1.0': 1.0, 'v1.1': 0.98, 'v1.2': 0.95}
GRADE_COLORS = {
    '적정': 'C6EFCE', '확인필요': 'FFEB9C',
    '편차주의': 'FFC7CE', '추가확인': 'FF0000'
}

HEADER_FILL = PatternFill(fill_type="solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)
THIN_BORDER = Border(left=Side(style="thin", color="D9D9D9"),
                     right=Side(style="thin", color="D9D9D9"),
                     top=Side(style="thin", color="D9D9D9"),
                     bottom=Side(style="thin", color="D9D9D9"))


@dataclass
class Phase12CountryData:
    country: str
    properties: List[Dict[str, Any]]
    total_records: int = 0

    def __post_init__(self):
        self.total_records = len(self.properties)


@dataclass
class AuditResult:
    property_id: str
    old_price: Optional[float]
    new_price: Optional[float]
    deviation_ratio: Optional[float]
    conformity_grade: str
    reason: str
    final_action: str


@dataclass
class GlobalMetrics:
    countries: List[str]
    total_properties: int
    audit_count: int = 0
    passed_audit: int = 0
    audit_rate: float = 0.0
    review_date: str = REVIEW_DATE


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_number(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and str(value) == 'nan'):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(',', '').replace('원', '').replace('₩', '')
    if '억' in text:
        try:
            return float(text.replace('억', '').replace('원', '').strip()) * 100_000_000
        except:
            pass
    if '만' in text:
        try:
            return float(text.replace('만', '').replace('원', '').strip()) * 10_000
        except:
            pass
    try:
        return float(text)
    except:
        return None


def safe_div(num: Optional[float], denom: Optional[float]) -> Optional[float]:
    return num / denom if num and denom and denom != 0 else None


def get_header_map(ws, header_row: int = 1) -> Dict[str, int]:
    header_map = {}
    for col in range(1, ws.max_column + 1):
        val = normalize_text(ws.cell(header_row, col).value)
        if val and val not in header_map:
            header_map[val] = col
    return header_map


def ensure_columns(ws, columns: List[str], header_row: int = 1) -> Dict[str, int]:
    header_map = get_header_map(ws, header_row)
    next_col = ws.max_column + 1

    for col_name in columns:
        if col_name not in header_map:
            cell = ws.cell(header_row, next_col)
            cell.value = col_name
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = THIN_BORDER
            header_map[col_name] = next_col
            next_col += 1

    return header_map


def classify_price_conformity_phase12(
    old_price: Optional[float],
    new_price: Optional[float],
    country: str,
    model_version: str = 'v1.0',
    real_transaction: bool = False,
    source_records: Optional[List[Dict]] = None
) -> Tuple[str, Optional[float], str]:
    if new_price is None:
        return '추가확인', None, 'Missing new price'

    tolerance = TOLERANCE_MAP.get(country, 0.10)
    confidence = CONFIDENCE_MAP.get(model_version, 1.0)
    adjusted_tolerance = tolerance * confidence

    if old_price and old_price != 0:
        deviation = (new_price - old_price) / old_price
    else:
        deviation = None

    if source_records:
        prices = [r.get('price') for r in source_records if r.get('price')]
        if prices:
            avg_price = sum(prices) / len(prices)
            source_dev = (new_price - avg_price) / avg_price if avg_price else None
            if source_dev is None:
                return '추가확인', None, 'Source calculation failed'

            abs_dev = abs(source_dev)
            if abs_dev <= adjusted_tolerance:
                return '적정', source_dev, f'Within {country} tolerance'
            elif abs_dev <= adjusted_tolerance * 1.5:
                return '확인필요', source_dev, 'Needs verification'
            else:
                return '편차주의', source_dev, f'Exceeds {country} tolerance'

    if real_transaction and deviation:
        return ('편차주의', deviation, '>20% change') if abs(deviation) > 0.20 else ('적정', deviation, 'Real transaction')

    if deviation and abs(deviation) > 0.20:
        return '편차주의', deviation, '>20% change'

    return '추가확인', deviation, 'Insufficient info'


def classify_correction_result(grade: str, real_transaction: bool) -> str:
    if grade == '적정':
        return '실거래 기반 업데이트' if real_transaction else '출처 기반 적정'
    return '추가확인' if grade == '확인필요' else '편차주의' if grade == '편차주의' else '추가확인'


def classify_final_action(grade: str) -> str:
    actions = {'적정': '유지', '확인필요': '원자료 재확인', '편차주의': '가격 재검증 필요', '추가확인': '추가 자료 확보'}
    return actions.get(grade, '검토필요')


def style_range(ws, min_row: int, max_row: int, min_col: int, max_col: int) -> None:
    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row, col)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical='center', wrap_text=True)


def autofit_columns(ws, min_w: int = 8, max_w: int = 40) -> None:
    for col in range(1, ws.max_column + 1):
        max_len = max((len(str(ws.cell(r, col).value or '')) for r in range(1, min(ws.max_row, 500))), default=0)
        ws.column_dimensions[get_column_letter(col)].width = max(min_w, min(max_len + 2, max_w))


def process_domestic_sheets(wb, input_path: str) -> int:
    """Process domestic sheets from base Excel. Returns row count."""
    try:
        base_wb = load_workbook(input_path)
    except (FileNotFoundError, Exception) as e:
        log.warning(f"Cannot load base Excel: {e}")
        return 0

    total_rows = 0
    for sheet_name in ['아파트', '빌라']:
        if sheet_name not in base_wb.sheetnames:
            continue

        src_ws = base_wb[sheet_name]
        if src_ws.max_row < 2:
            continue

        header_map = get_header_map(src_ws)
        dst_ws = wb.create_sheet(sheet_name)

        # Copy headers
        for col in range(1, src_ws.max_column + 1):
            dst_ws.cell(1, col).value = src_ws.cell(1, col).value
            dst_ws.cell(1, col).fill = HEADER_FILL
            dst_ws.cell(1, col).font = HEADER_FONT

        new_cols = ensure_columns(dst_ws, ['가격부합성', '편차율', '최종조치'], header_row=1)

        # Process rows
        old_col = header_map.get('기존가격')
        new_col = header_map.get('신규가격')

        for row in range(2, src_ws.max_row + 1):
            for col in range(1, src_ws.max_column + 1):
                dst_ws.cell(row, col).value = src_ws.cell(row, col).value

            old_p = normalize_number(src_ws.cell(row, old_col).value) if old_col else None
            new_p = normalize_number(src_ws.cell(row, new_col).value) if new_col else None

            grade, dev, _ = classify_price_conformity_phase12(old_p, new_p, 'KR')

            dst_ws.cell(row, new_cols['가격부합성']).value = grade
            if dev:
                dst_ws.cell(row, new_cols['편차율']).value = f"{dev:.2%}"
            dst_ws.cell(row, new_cols['최종조치']).value = classify_final_action(grade)

            fill = PatternFill(fill_type="solid", fgColor=GRADE_COLORS.get(grade, "FFFFFF"))
            dst_ws.cell(row, new_cols['가격부합성']).fill = fill
            total_rows += 1

        style_range(dst_ws, 2, dst_ws.max_row, 1, dst_ws.max_column)
        autofit_columns(dst_ws)

    base_wb.close()
    return total_rows


def process_country_sheets(wb, country: str, country_data: Phase12CountryData, model_version: str = 'v1.0') -> int:
    """Create country sheets. Returns property count."""
    if not country_data.properties:
        return 0

    headers = ['Property_ID', 'Address', 'Area', 'Old_Price', 'New_Price', 'Conformity', 'Deviation', 'Action']

    # Residential sheet
    res_name = f"{country}_Residential"
    res_ws = wb.create_sheet(res_name)

    for col, header in enumerate(headers, 1):
        cell = res_ws.cell(1, col)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = THIN_BORDER

    for row, prop in enumerate(country_data.properties, 2):
        old_p = normalize_number(prop.get('old_price'))
        new_p = normalize_number(prop.get('new_price'))
        grade, dev, _ = classify_price_conformity_phase12(old_p, new_p, country, model_version)

        res_ws.cell(row, 1).value = prop.get('property_id')
        res_ws.cell(row, 2).value = prop.get('address')
        res_ws.cell(row, 3).value = prop.get('area')
        res_ws.cell(row, 4).value = old_p
        res_ws.cell(row, 5).value = new_p
        res_ws.cell(row, 6).value = grade
        if dev:
            res_ws.cell(row, 7).value = f"{dev:.2%}"
        res_ws.cell(row, 8).value = classify_final_action(grade)

        fill = PatternFill(fill_type="solid", fgColor=GRADE_COLORS.get(grade))
        res_ws.cell(row, 6).fill = fill

    style_range(res_ws, 2, res_ws.max_row, 1, len(headers))
    autofit_columns(res_ws)
    res_ws.freeze_panes = res_ws.cell(2, 1).coordinate

    # Prediction sheet (copy)
    pred_name = f"{country}_Prediction"
    pred_ws = wb.create_sheet(pred_name)

    for col, header in enumerate(headers, 1):
        cell = pred_ws.cell(1, col)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT

    for row in range(2, res_ws.max_row + 1):
        for col in range(1, len(headers) + 1):
            pred_ws.cell(row, col).value = res_ws.cell(row, col).value
            pred_ws.cell(row, col).border = THIN_BORDER

    autofit_columns(pred_ws)
    pred_ws.freeze_panes = pred_ws.cell(2, 1).coordinate

    return len(country_data.properties)


def create_report_sheet(wb, metrics: GlobalMetrics, audit_results: List[AuditResult]) -> None:
    ws = wb.create_sheet("Report", 0)

    ws['A1'] = "Loan4U Phase 12 Global Validation Report"
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:H1')

    ws['A2'] = f"Review Date: {metrics.review_date}"
    ws.merge_cells('A2:H2')

    ws['A4'] = "Country Metrics"
    ws['A4'].font = Font(bold=True)

    headers = ['Country', 'Properties', 'Passed', 'Pass Rate']
    for col, header in enumerate(headers, 1):
        ws.cell(5, col).value = header
        ws.cell(5, col).fill = HEADER_FILL
        ws.cell(5, col).font = HEADER_FONT

    row = 6
    for country in metrics.countries:
        count = sum(1 for a in audit_results if a.property_id.startswith(country))
        passed = sum(1 for a in audit_results if a.property_id.startswith(country) and a.conformity_grade == '적정')

        ws.cell(row, 1).value = country
        ws.cell(row, 2).value = count
        ws.cell(row, 3).value = passed
        if count > 0:
            ws.cell(row, 4).value = f"{passed/count:.1%}"

        row += 1

    autofit_columns(ws)
    ws.freeze_panes = 'A6'


def run_pipeline(base_excel: str, config_dir: str, output_excel: str) -> None:
    """Main pipeline execution."""
    log.info("Starting Phase 12 pipeline...")

    wb = Workbook()
    wb.remove(wb.active)

    # Process domestic
    log.info("Processing domestic sheets...")
    dom_rows = process_domestic_sheets(wb, base_excel)

    # Process countries
    log.info(f"Processing {len(COUNTRIES)} countries...")
    config_path = Path(config_dir)
    total_props = 0
    metrics = GlobalMetrics(countries=COUNTRIES, total_properties=0)

    for country in COUNTRIES:
        try:
            config_file = config_path / f'{country.lower()}_expansion_plan.json'
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)

                props = config.get('sample_properties', [])
                country_data = Phase12CountryData(country=country, properties=props)
                count = process_country_sheets(wb, country, country_data)
                total_props += count
                log.info(f"  {country}: {count} properties")
        except Exception as e:
            log.warning(f"  {country}: {e}")

    metrics.total_properties = dom_rows + total_props
    metrics.audit_count = total_props

    # Report
    log.info("Creating report sheet...")
    create_report_sheet(wb, metrics, [])

    # Save
    wb.save(output_excel)
    log.info(f"✓ Saved: {output_excel} ({len(wb.sheetnames)} sheets, {metrics.total_properties} records)")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Loan4U Phase 12 Pipeline')
    parser.add_argument('--base', default='data/raw/Loan4U_QC_v1.1_before_fill.xlsx')
    parser.add_argument('--config', default='config/phase12')
    parser.add_argument('--output', default='output/Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx')

    args = parser.parse_args()
    run_pipeline(args.base, args.config, args.output)
