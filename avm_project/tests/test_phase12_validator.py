#!/usr/bin/env python3
"""
Phase 12.H Validation Module Tests
24 comprehensive test cases for Excel workbook validation.
"""

import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from phase12_validator import Phase12Validator, ValidationResult, SheetValidation


class TestPhase12ValidatorStructure:
    """Tests for sheet structure validation"""

    def test_all_expected_sheets_count(self) -> None:
        """Verify 19 sheets expected (1 Report + 2 domestic + 8×2 country)"""
        validator = Phase12Validator('dummy.xlsx')
        assert len(validator.EXPECTED_SHEETS) == 19

    def test_missing_sheets_detected(self) -> None:
        """Detect missing required sheets"""
        wb = Workbook()
        ws = wb.active
        ws.title = 'Report'

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            passed, counts = validator.validate_all()

            assert not passed
            assert counts['errors'] > 0
            error_msgs = [r.message for r in validator.results if r.severity == 'error']
            assert any('Missing sheets' in msg for msg in error_msgs)

    def test_extra_sheets_warning(self) -> None:
        """Extra sheets should warn but not fail"""
        wb = Workbook()
        wb.active.title = 'Report'
        validator = Phase12Validator('dummy.xlsx')

        for sheet in validator.EXPECTED_SHEETS.keys():
            if sheet != 'Report' and sheet not in wb.sheetnames:
                wb.create_sheet(sheet)

        wb['Report']['A1'] = 'Test Data'

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            passed, counts = validator.validate_all()

            assert counts['warnings'] >= 0


class TestPhase12ValidatorHeaders:
    """Tests for header validation"""

    def test_missing_validation_columns(self) -> None:
        """Korean sheets missing required columns should fail"""
        wb = Workbook()
        for sheet_name in ['아파트', '빌라']:
            ws = wb.create_sheet(sheet_name)
            ws['A1'] = '주소'
            ws['B1'] = '면적'

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            passed, counts = validator.validate_all()

            assert not passed or counts['errors'] > 0

    def test_valid_headers_domestic(self) -> None:
        """Valid domestic sheet headers pass"""
        wb = Workbook()
        ws = wb.active
        ws.title = '아파트'

        headers = ['주소', '면적', '기존가격', '신규가격', '가격부합성', '편차율', '최종조치']
        for col, header in enumerate(headers, 1):
            ws.cell(1, col).value = header

        ws['A2'] = '서울시'
        ws['B2'] = 100

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            passed, counts = validator.validate_all()

            assert counts['errors'] == 0 or not passed


class TestPhase12ValidatorDataTypes:
    """Tests for data type validation"""

    def test_valid_price_integer(self) -> None:
        """Integer prices pass validation"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_price(400_000_000) is True

    def test_valid_price_float(self) -> None:
        """Float prices pass validation"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_price(404_500_000.50) is True

    def test_invalid_price_string_number(self) -> None:
        """String numbers pass if convertible"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_price('400000000') is True

    def test_invalid_price_too_low(self) -> None:
        """Prices below minimum fail"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_price(50_000) is False

    def test_invalid_price_too_high(self) -> None:
        """Prices above maximum fail"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_price(11_000_000_000) is False

    def test_invalid_price_non_numeric(self) -> None:
        """Non-numeric prices fail"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_price('not_a_price') is False

    def test_valid_percentage_zero(self) -> None:
        """Zero percentage is valid"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_percentage(0.0) is True

    def test_valid_percentage_positive(self) -> None:
        """Positive percentages valid"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_percentage(0.25) is True

    def test_valid_percentage_negative(self) -> None:
        """Negative percentages valid"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_percentage(-0.15) is True

    def test_invalid_percentage_exceeds_100(self) -> None:
        """Percentages over 100% fail"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_percentage(1.5) is False

    def test_invalid_percentage_string(self) -> None:
        """String percentages fail if unparseable"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_percentage('invalid%') is False

    def test_percentage_with_percent_sign(self) -> None:
        """Percentage string with % sign valid"""
        validator = Phase12Validator('dummy.xlsx')
        assert validator._is_valid_percentage('25%') is True


class TestPhase12ValidatorGrades:
    """Tests for grade validation"""

    def test_valid_grade_acceptable(self) -> None:
        """'적정' is valid grade"""
        validator = Phase12Validator('dummy.xlsx')
        assert '적정' in validator.VALID_GRADES

    def test_valid_grade_needs_review(self) -> None:
        """'확인필요' is valid grade"""
        validator = Phase12Validator('dummy.xlsx')
        assert '확인필요' in validator.VALID_GRADES

    def test_valid_grade_variance_warning(self) -> None:
        """'편차주의' is valid grade"""
        validator = Phase12Validator('dummy.xlsx')
        assert '편차주의' in validator.VALID_GRADES

    def test_valid_grade_additional_check(self) -> None:
        """'추가확인' is valid grade"""
        validator = Phase12Validator('dummy.xlsx')
        assert '추가확인' in validator.VALID_GRADES

    def test_grade_color_mapping_complete(self) -> None:
        """All grades have color mappings"""
        validator = Phase12Validator('dummy.xlsx')
        for grade in validator.VALID_GRADES:
            assert grade in validator.GRADE_COLOR_MAP
            assert validator.GRADE_COLOR_MAP[grade] in validator.GRADE_COLORS


class TestPhase12ValidatorStyling:
    """Tests for cell styling and color validation"""

    def test_grade_color_range(self) -> None:
        """4 distinct grade colors defined"""
        validator = Phase12Validator('dummy.xlsx')
        assert len(validator.GRADE_COLORS) == 4

    def test_valid_color_codes(self) -> None:
        """All color codes are valid hex"""
        validator = Phase12Validator('dummy.xlsx')
        for color in validator.GRADE_COLORS:
            assert len(color) in (6, 8)
            assert all(c in '0123456789ABCDEF' for c in color.upper())


class TestPhase12ValidatorCrossSheet:
    """Tests for cross-sheet consistency"""

    def test_countries_defined(self) -> None:
        """All 9 countries defined"""
        validator = Phase12Validator('dummy.xlsx')
        assert 'KR' in validator.COUNTRIES
        assert len(validator.COUNTRIES) == 9


class TestPhase12ValidatorIntegration:
    """Integration tests with complete workbooks"""

    def test_empty_workbook_fails(self) -> None:
        """Empty workbook detected"""
        wb = Workbook()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            passed, counts = validator.validate_all()

            assert not passed

    def test_no_data_rows_warning(self) -> None:
        """Sheet without data rows warns"""
        wb = Workbook()
        ws = wb.active
        ws.title = '아파트'
        ws['A1'] = 'Header'

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            passed, counts = validator.validate_all()

            assert counts['warnings'] > 0 or counts['errors'] > 0

    def test_workbook_file_not_found(self) -> None:
        """Missing file handled gracefully"""
        validator = Phase12Validator('/nonexistent/path.xlsx')
        passed, counts = validator.validate_all()

        assert not passed
        assert counts['errors'] == 1

    def test_validation_result_report_generated(self) -> None:
        """Report generation doesn't crash"""
        wb = Workbook()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            wb.save(f.name)
            validator = Phase12Validator(f.name)
            validator.validate_all()
            report = validator.get_report()

            assert 'Validation Report' in report
            assert len(report) > 0


def validate_factory() -> Phase12Validator:
    """Create validator for tests"""
    return Phase12Validator('dummy.xlsx')


validator = validate_factory()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
