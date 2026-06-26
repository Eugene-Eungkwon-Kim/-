#!/usr/bin/env python3
"""
Loan4U Phase 12 Validation Module
Validates 21-sheet workbook structure, data, and styling.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from openpyxl import load_workbook
from openpyxl.styles import PatternFill


@dataclass
class ValidationResult:
    """Result of validation check"""
    passed: bool
    message: str
    severity: str  # 'error', 'warning', 'info'


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
    GRADE_COLORS = {'C6EFCE', 'FFEB9C', 'FFC7CE', 'FF0000'}

    def __init__(self, workbook_path: str) -> None:
        self.workbook_path = Path(workbook_path)
        self.results: List[ValidationResult] = []
        self.sheet_validations: List[SheetValidation] = []

    def validate_all(self) -> Tuple[bool, Dict[str, int]]:
        """Run complete validation suite."""
        try:
            wb = load_workbook(self.workbook_path)
            self._validate_sheet_structure(wb)
            self._validate_sheet_contents(wb)
            self._validate_styling(wb)
            wb.close()

            return self._summarize_results()
        except Exception as e:
            self.results.append(
                ValidationResult(False, f"Validation failed: {e}", 'error')
            )
            return False, {'errors': 1}

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

        for row in range(2, min(ws.max_row + 1, 100)):
            row_has_data = False
            for col in range(1, expected_cols + 1):
                cell = ws.cell(row, col)
                if cell.value is not None:
                    row_has_data = True
                    break
            if not row_has_data:
                empty_count += 1

        if empty_count > 0:
            validation.issues.append(
                ValidationResult(
                    True,
                    f"{sheet_name}: {empty_count} empty rows detected",
                    'warning',
                )
            )

    def _validate_styling(self, wb) -> None:
        """Check color coding on validation columns."""
        for sheet_name in ('아파트', '빌라'):
            if sheet_name not in wb.sheetnames:
                continue

            ws = wb[sheet_name]
            grade_col = None

            # Find 가격부합성 column
            for col in range(1, ws.max_column + 1):
                if str(ws.cell(1, col).value or '').strip() == '가격부합성':
                    grade_col = col
                    break

            if not grade_col:
                continue

            colored_count = 0
            for row in range(2, min(ws.max_row + 1, 100)):
                cell = ws.cell(row, grade_col)
                if cell.fill and cell.fill.fgColor:
                    color = str(cell.fill.fgColor.rgb or '')
                    if color.upper() in self.GRADE_COLORS:
                        colored_count += 1

            if colored_count > 0:
                self.results.append(
                    ValidationResult(
                        True,
                        f"{sheet_name}: {colored_count} cells with grade colors",
                        'info',
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
        lines = ['Loan4U Phase 12 Validation Report', '=' * 40, '']

        for result in self.results:
            status = '✓' if result.passed else '✗'
            lines.append(f"{status} [{result.severity.upper()}] {result.message}")

        lines.append('')
        lines.append('Sheet Details:')
        for sv in self.sheet_validations:
            issue_count = len(sv.issues)
            lines.append(
                f"  {sv.sheet_name}: {sv.row_count} rows, "
                f"{sv.header_count} cols, {issue_count} issues"
            )

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
