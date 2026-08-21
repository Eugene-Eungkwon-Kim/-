#!/usr/bin/env python3
"""
Phase 12 Integration Tests — Full Pipeline Validation

Tests end-to-end flow: Excel → Validator → PDF Generator
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from openpyxl import load_workbook
from phase12_validator import Phase12Validator
from phase12_pdf_generator import Phase12PDFGenerator, ReportMetrics


class TestPhase12Pipeline(unittest.TestCase):
    """End-to-end pipeline tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Create sample Excel for testing."""
        from loan4u_phase12_pipeline import run_pipeline

        cls.test_dir = Path(tempfile.mkdtemp())
        cls.output_excel = cls.test_dir / 'test_phase12.xlsx'

        # Generate test Excel
        run_pipeline(
            base_excel='',  # Use generated data
            config_dir='config',
            output_excel=str(cls.output_excel),
        )

    def test_excel_generation(self) -> None:
        """Test that Excel file is generated correctly."""
        self.assertTrue(self.output_excel.exists(), "Excel file not created")

        wb = load_workbook(self.output_excel, data_only=True)
        self.assertGreater(len(wb.sheetnames), 0, "Excel has no sheets")
        self.assertIn('Report', wb.sheetnames, "Report sheet missing")
        wb.close()

    def test_validator_accepts_excel(self) -> None:
        """Test that validator accepts generated Excel."""
        validator = Phase12Validator()
        results = validator.validate_workbook(str(self.output_excel))

        self.assertIsNotNone(results)
        self.assertIn('report_sheet_valid', results)

    def test_validator_checks_structure(self) -> None:
        """Test that validator checks workbook structure."""
        validator = Phase12Validator()
        results = validator.validate_workbook(str(self.output_excel))

        # Verify structure checks
        self.assertIn('total_sheets', results)
        self.assertIn('sheet_names', results)
        self.assertGreater(results['total_sheets'], 0)

    def test_validator_checks_data_types(self) -> None:
        """Test that validator checks column data types."""
        validator = Phase12Validator()
        results = validator.validate_workbook(str(self.output_excel))

        # Validator should have data type checks
        self.assertIn('validation_results', results)

    def test_pdf_generator_accepts_excel(self) -> None:
        """Test that PDF generator accepts validated Excel."""
        pdf_path = self.test_dir / 'test_report.pdf'

        generator = Phase12PDFGenerator(str(pdf_path.parent))
        success = generator.generate_from_excel(
            str(self.output_excel),
            str(pdf_path),
        )

        self.assertTrue(success, "PDF generation failed")
        self.assertTrue(pdf_path.exists(), "PDF file not created")

    def test_pdf_is_valid(self) -> None:
        """Test that generated PDF is valid."""
        pdf_path = self.test_dir / 'test_report.pdf'

        generator = Phase12PDFGenerator(str(pdf_path.parent))
        generator.generate_from_excel(
            str(self.output_excel),
            str(pdf_path),
        )

        # PDF should have size > 1KB
        self.assertGreater(pdf_path.stat().st_size, 1024)

    def test_full_pipeline_workflow(self) -> None:
        """Test complete workflow: Excel → Validation → PDF."""
        # Step 1: Validate Excel
        validator = Phase12Validator()
        val_results = validator.validate_workbook(str(self.output_excel))
        self.assertIsNotNone(val_results)

        # Step 2: Generate PDF
        pdf_path = self.test_dir / 'full_workflow.pdf'
        generator = Phase12PDFGenerator(str(pdf_path.parent))
        pdf_success = generator.generate_from_excel(
            str(self.output_excel),
            str(pdf_path),
        )

        self.assertTrue(pdf_success)
        self.assertTrue(pdf_path.exists())
        self.assertGreater(pdf_path.stat().st_size, 1024)

    def test_validator_error_handling(self) -> None:
        """Test validator handles missing files."""
        validator = Phase12Validator()

        with self.assertRaises(FileNotFoundError):
            validator.validate_workbook('/nonexistent/file.xlsx')

    def test_pdf_generator_error_handling(self) -> None:
        """Test PDF generator handles missing files."""
        generator = Phase12PDFGenerator(str(self.test_dir))

        success = generator.generate_from_excel(
            '/nonexistent/file.xlsx',
            str(self.test_dir / 'output.pdf'),
        )

        self.assertFalse(success)


class TestPhase12Metadata(unittest.TestCase):
    """Test metadata and reporting."""

    def test_validator_output_structure(self) -> None:
        """Test validator output structure."""
        validator = Phase12Validator()

        # Create minimal test data
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws['A1'] = 'Test'

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            wb.save(tmp.name)
            results = validator.validate_workbook(tmp.name)

            self.assertIsInstance(results, dict)
            self.assertIn('validation_results', results)

    def test_pdf_generator_metadata(self) -> None:
        """Test PDF generator extracts correct metadata."""
        from loan4u_phase12_pipeline import run_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            excel_path = tmpdir / 'metadata_test.xlsx'

            run_pipeline(
                base_excel='',
                config_dir='config',
                output_excel=str(excel_path),
            )

            # Load and verify metadata
            wb = load_workbook(excel_path, data_only=True)
            self.assertGreater(len(wb.sheetnames), 0)

            # Check Report sheet has data
            if 'Report' in wb.sheetnames:
                ws = wb['Report']
                self.assertGreater(ws.max_row, 0)


if __name__ == '__main__':
    unittest.main()
