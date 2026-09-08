#!/usr/bin/env python3
"""
Loan4U Phase 12 Validation Module
Validates 21-sheet workbook structure, data, and styling.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from openpyxl import load_workbook
from openpyxl.styles import PatternFill


@dataclass
class ValidationResult:
    """Result of validation check"""
    passed: bool
    message: str
    severity: str


@dataclass
class SheetValidation:
    """Validation summary per sheet"""
    sheet_name: str
    has_headers: bool
    header_count: int
    row_count: int
    validation_columns: Dict[str, bool]
    has_colors: bool
    issues: List[ValidationResult]
    numeric_errors: int = 0
    grade_errors: int = 0
    color_mismatches: int = 0


class Phase12Validator:
    """Validate Phase 12 workbook structure and data"""

    EXPECTED_SHEETS = {
        'Report': 'Summary report',
        '아파트': 'Domestic apartments',
        '빌라': 'Domestic villas',
        'UK_Residential': 'UK market',
        'UK_Prediction': 'UK model',
        'SG_Residential': 'Singapore market',
        'SG_Prediction': 'Singapore model',
        'JP_Residential': 'Japan market',
        'JP_Prediction': 'Japan model',
        'DE_Residential': 'Germany market',
        'DE_Prediction': 'Germany model',
        'AU_Residential': 'Australia market',
        'AU_Prediction': 'Australia model',
        'CA_Residential': 'Canada market',
        'CA_Prediction': 'Canada model',
        'TH_Residential': 'Thailand market',
        'TH_Prediction': 'Thailand model',
        'HK_Residential': 'Hong Kong market',
        'HK_Prediction': 'Hong Kong model',
    }

    VALIDATION_COLUMNS = {'가격부합성', '편차율', '최종조치'}
    VALID_GRADES = {'적정', '확인필요', '편차주의', '추가확인'}
    GRADE_COLOR_MAP = {
        '적정': 'C6EFCE', '확인필요': 'FFEB9C',
        '편차주의': 'FFC7CE', '추가확인': 'FF0000'
    }
    GRADE_COLORS = set(GRADE_COLOR_MAP.values())
    PRICE_MIN = 100_000
    PRICE_MAX = 10_000_000_000
    COUNTRIES = {'UK', 'SG', 'JP', 'DE', 'AU', 'CA', 'TH', 'HK', 'KR'}

    def __init__(self, workbook_path: Optional[str] = None) -> None:
        self.workbook_path = Path(workbook_path) if workbook_path else None
        self.results: List[ValidationResult] = []
        self.sheet_validations: List[SheetValidation] = []

    def validate_workbook(self, workbook_path: str) -> Dict[str, Any]:
        """Validate one workbook and return a structured summary dict."""
        path = Path(workbook_path)
        if not path.exists():
            raise FileNotFoundError(f"Workbook not found: {path}")

        self.workbook_path = path
        self.results = []
        self.sheet_validations = []
        passed, counts = self.validate_all()

        wb = load_workbook(path, read_only=True)
        sheet_names = list(wb.sheetnames)
        wb.close()

        return {
            'passed': passed,
            'summary': counts,
            'total_sheets': len(sheet_names),
            'sheet_names': sheet_names,
            'report_sheet_valid': 'Report' in sheet_names and not self._sheet_has_errors('Report'),
            'validation_results': [asdict(r) for r in self.results],
            'sheet_validations': [asdict(s) for s in self.sheet_validations],
        }

    def _sheet_has_errors(self, sheet_name: str) -> bool:
        return any(r.severity == 'error' and sheet_name in r.message for r in self.results)

    def validate_all(self) -> Tuple[bool, Dict[str, int]]:
        """Run complete validation suite."""
        try:
            wb = load_workbook(self.workbook_path)
            self._validate_sheet_structure(wb)
            self._validate_sheet_contents(wb)
            self._validate_styling(wb)
            self._validate_cross_sheet_consistency(wb)
            wb.close()

            return self._summarize_results()
        except Exception as e:
            self.results.append(
                ValidationResult(False, f"Validation failed: {e}", 'error')
            )
            return False, {'errors': 1, 'warnings': 0, 'info': 0}

    def _validate_sheet_structure(self, wb) -> None:
        """Check workbook sheet structure."""
        expected = set(self.EXPECTED_SHEETS.keys())
        actual = set(wb.sheetnames)

        missing = expected - actual
        extra = actual - expected

        if missing:
            self.results.append(
                ValidationResult(
                    False,
                    f"Missing sheets: {', '.join(sorted(missing))}",
                    'error',
                )
            )

        if extra:
            self.results.append(
                ValidationResult(
                    True,
                    f"Extra sheets (ignored): {', '.join(sorted(extra))}",
                    'warning',
                )
            )

        if not missing:
            self.results.append(
                ValidationResult(True, f"All {len(expected)} required sheets present", 'info')
            )

    def _validate_sheet_contents(self, wb) -> None:
        """Check sheet data structure and content."""
        for sheet_name in self.EXPECTED_SHEETS.keys():
            if sheet_name not in wb.sheetnames:
                continue

            ws = wb[sheet_name]
            validation = SheetValidation(
                sheet_name=sheet_name,
                has_headers=ws.max_row > 0,
                header_count=ws.max_column,
                row_count=max(0, ws.max_row - 1),
                validation_columns={},
                has_colors=False,
                issues=[],
            )

            self._check_headers(ws, sheet_name, validation)
            self._check_data_rows(ws, sheet_name, validation)

            self.sheet_validations.append(validation)

    def _check_headers(self, ws, sheet_name: str, validation: SheetValidation) -> None:
        """Validate header row."""
        if ws.max_row < 1:
            validation.issues.append(
                ValidationResult(False, f"{sheet_name}: No header row", 'error')
            )
            return

        headers = set(
            str(ws.cell(1, col).value or '').strip()
            for col in range(1, ws.max_column + 1)
            if ws.cell(1, col).value
        )

        # Check domestic sheets for validation columns
        if sheet_name in ('아파트', '빌라'):
            for col_name in self.VALIDATION_COLUMNS:
                present = col_name in headers
                validation.validation_columns[col_name] = present
                if not present:
                    validation.issues.append(
                        ValidationResult(
                            False,
                            f"{sheet_name}: Missing column '{col_name}'",
                            'error',
                        )
                    )

    def _check_data_rows(self, ws, sheet_name: str, validation: SheetValidation) -> None:
        """Validate data rows."""
        if ws.max_row < 2:
            validation.issues.append(
                ValidationResult(False, f"{sheet_name}: No data rows", 'warning')
            )
            return

        expected_cols = ws.max_column
        empty_count = 0
        numeric_errors = 0
        grade_errors = 0

        for row in range(2, min(ws.max_row + 1, 100)):
            row_has_data = False
            for col in range(1, expected_cols + 1):
                cell = ws.cell(row, col)
                if cell.value is not None:
                    row_has_data = True

            if not row_has_data:
                empty_count += 1
                continue

            numeric_errors, grade_errors = self._validate_row_data(
                ws, row, sheet_name, validation, numeric_errors, grade_errors
            )

        validation.numeric_errors = numeric_errors
        validation.grade_errors = grade_errors

        if empty_count > 0:
            validation.issues.append(
                ValidationResult(True, f"{sheet_name}: {empty_count} empty rows", 'warning')
            )

    def _validate_row_data(self, ws, row: int, sheet_name: str, validation: SheetValidation,
                          numeric_errors: int, grade_errors: int) -> Tuple[int, int]:
        """Validate individual row data types and values."""
        headers = [str(ws.cell(1, col).value or '').strip() for col in range(1, ws.max_column + 1)]

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row, col_idx)
            value = cell.value

            if value is None or value == '':
                continue

            if '가격' in header:
                if not self._is_valid_price(value):
                    numeric_errors += 1

            elif '편차' in header or '율' in header:
                if not self._is_valid_percentage(value):
                    numeric_errors += 1

            elif '부합성' in header:
                if str(value).strip() not in self.VALID_GRADES:
                    grade_errors += 1

        return numeric_errors, grade_errors

    def _is_valid_price(self, value) -> bool:
        """Check if value is valid price."""
        try:
            if isinstance(value, (int, float)):
                price = float(value)
            else:
                text = str(value).replace(',', '').replace('원', '').replace('₩', '')
                price = float(text)
            return self.PRICE_MIN <= price <= self.PRICE_MAX
        except (ValueError, TypeError):
            return False

    def _is_valid_percentage(self, value) -> bool:
        """Check if value is valid percentage."""
        try:
            if isinstance(value, (int, float)):
                return -1.0 <= float(value) <= 1.0
            text = str(value).replace('%', '').strip()
            pct = float(text) / 100
            return -1.0 <= pct <= 1.0
        except (ValueError, TypeError):
            return False

    def _validate_styling(self, wb) -> None:
        """Check color coding on validation columns."""
        domestic_sheets = ('아파트', '빌라')

        for sheet_name in domestic_sheets:
            if sheet_name not in wb.sheetnames:
                continue

            ws = wb[sheet_name]
            grade_col = None

            for col in range(1, ws.max_column + 1):
                if str(ws.cell(1, col).value or '').strip() == '가격부합성':
                    grade_col = col
                    break

            if not grade_col:
                continue

            color_mismatches = self._check_grade_color_consistency(ws, grade_col, sheet_name)

        for country in self.COUNTRIES:
            if country == 'KR':
                continue
            for suffix in ('_Residential', '_Prediction'):
                sheet_name = f"{country}{suffix}"
                if sheet_name not in wb.sheetnames:
                    continue
                ws = wb[sheet_name]
                grade_col = self._find_column(ws, 'Conformity')
                if grade_col:
                    self._check_grade_color_consistency(ws, grade_col, sheet_name)

    def _find_column(self, ws, col_name: str) -> Optional[int]:
        """Find column index by header name."""
        for col in range(1, ws.max_column + 1):
            header = str(ws.cell(1, col).value or '').strip()
            if header == col_name:
                return col
        return None

    def _check_grade_color_consistency(self, ws, grade_col: int, sheet_name: str) -> int:
        """Verify grade values match their cell colors."""
        mismatches = 0
        colored_count = 0

        for row in range(2, min(ws.max_row + 1, 100)):
            grade_cell = ws.cell(row, grade_col)
            grade_value = str(grade_cell.value or '').strip()

            if not grade_value:
                continue

            cell_color = self._get_cell_color(grade_cell)
            expected_color = self.GRADE_COLOR_MAP.get(grade_value)

            if cell_color and expected_color:
                if cell_color.upper() != expected_color.upper():
                    mismatches += 1
                colored_count += 1

        if colored_count > 0:
            self.results.append(
                ValidationResult(
                    True,
                    f"{sheet_name}: {colored_count} grades colored, {mismatches} mismatches",
                    'warning' if mismatches > 0 else 'info',
                )
            )
        return mismatches

    def _get_cell_color(self, cell) -> Optional[str]:
        """Extract RGB color from cell."""
        if not cell.fill or not cell.fill.fgColor:
            return None
        color_str = str(cell.fill.fgColor.rgb or '')
        if color_str and color_str.startswith('FF'):
            return color_str[2:]
        return color_str

    def _validate_cross_sheet_consistency(self, wb) -> None:
        """Validate consistency between related sheets."""
        for country in self.COUNTRIES:
            if country == 'KR':
                continue
            res_name = f"{country}_Residential"
            pred_name = f"{country}_Prediction"

            if res_name not in wb.sheetnames or pred_name not in wb.sheetnames:
                continue

            res_ws = wb[res_name]
            pred_ws = wb[pred_name]

            res_count = max(0, res_ws.max_row - 1)
            pred_count = max(0, pred_ws.max_row - 1)

            if res_count != pred_count:
                self.results.append(
                    ValidationResult(
                        False,
                        f"{res_name} ({res_count} rows) ≠ {pred_name} ({pred_count} rows)",
                        'warning',
                    )
                )

    def _summarize_results(self) -> Tuple[bool, Dict[str, int]]:
        """Summarize validation results."""
        errors = sum(1 for r in self.results if r.severity == 'error')
        warnings = sum(1 for r in self.results if r.severity == 'warning')
        info = sum(1 for r in self.results if r.severity == 'info')

        passed = errors == 0

        return passed, {'errors': errors, 'warnings': warnings, 'info': info}

    def get_report(self) -> str:
        """Generate text report of validation."""
        lines = ['Loan4U Phase 12 Validation Report', '=' * 60, '']

        for result in self.results:
            status = '✓' if result.passed else '✗'
            lines.append(f"{status} [{result.severity.upper()}] {result.message}")

        lines.append('')
        lines.append('Sheet Details:')
        for sv in self.sheet_validations:
            issue_count = len(sv.issues)
            detail_parts = [
                f"{sv.row_count} rows",
                f"{sv.header_count} cols",
                f"{issue_count} issues",
            ]
            if sv.numeric_errors > 0:
                detail_parts.append(f"{sv.numeric_errors} numeric errors")
            if sv.grade_errors > 0:
                detail_parts.append(f"{sv.grade_errors} grade errors")

            lines.append(f"  {sv.sheet_name}: {', '.join(detail_parts)}")

        return '\n'.join(lines)


def main() -> None:
    """Validate Phase 12 workbook."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 12 Workbook Validator')
    parser.add_argument(
        '--workbook',
        default='output/Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx',
        help='Path to workbook to validate',
    )

    args = parser.parse_args()

    validator = Phase12Validator(args.workbook)
    passed, counts = validator.validate_all()

    print(validator.get_report())
    print(f"\nValidation: {'PASSED ✓' if passed else 'FAILED ✗'}")
    print(f"Errors: {counts['errors']}, Warnings: {counts['warnings']}, Info: {counts['info']}")

    exit(0 if passed else 1)


if __name__ == '__main__':
    main()
