#!/usr/bin/env python3
"""
Loan4U Phase 12 PDF Report Generator
Converts Excel workbook metrics to professional PDF summary.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openpyxl import load_workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas


@dataclass
class CountryMetric:
    """Country validation metrics"""
    country: str
    total_properties: int
    passed_validation: int
    pass_rate: float


@dataclass
class ReportMetrics:
    """Global report metrics"""
    review_date: str
    total_sheets: int
    total_records: int
    countries: List[str]
    country_metrics: List[CountryMetric]


class Phase12PDFGenerator:
    """Generate Phase 12 validation report PDF"""

    COLORS = {
        '적정': (198, 239, 206),
        '확인필요': (255, 235, 156),
        '편차주의': (255, 199, 206),
        '추가확인': (255, 0, 0),
    }

    def __init__(self, output_path: str) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_from_excel(self, excel_path: str, output_pdf: str) -> bool:
        """Generate PDF report from Excel workbook."""
        try:
            wb = load_workbook(excel_path)
            if 'Report' not in wb.sheetnames:
                return False

            metrics = self._extract_metrics(wb)
            self._create_pdf_report(metrics, output_pdf)
            wb.close()
            return True
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return False

    def _extract_metrics(self, wb) -> ReportMetrics:
        """Extract metrics from Report sheet."""
        ws = wb['Report']

        review_date = str(ws['A2'].value or datetime.now().strftime("%Y-%m-%d"))
        total_sheets = len(wb.sheetnames)
        total_records = 0

        country_metrics = []
        for row in range(6, ws.max_row + 1):
            country = ws.cell(row, 1).value
            props = ws.cell(row, 2).value
            passed = ws.cell(row, 3).value

            if country and props:
                total_records += int(props or 0)
                rate = float(passed or 0) / int(props) if props > 0 else 0
                country_metrics.append(
                    CountryMetric(country, int(props), int(passed or 0), rate)
                )

        countries = [m.country for m in country_metrics]

        return ReportMetrics(
            review_date=review_date,
            total_sheets=total_sheets,
            total_records=total_records,
            countries=countries,
            country_metrics=country_metrics,
        )

    def _create_pdf_report(self, metrics: ReportMetrics, output_pdf: str) -> None:
        """Create PDF document with metrics and styling."""
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=12,
            alignment=1,
        )

        story = []

        # Title
        title = Paragraph("Loan4U Phase 12 Global Validation Report", title_style)
        story.append(title)

        # Review date
        date_text = Paragraph(
            f"<b>Review Date:</b> {metrics.review_date}",
            styles['Normal'],
        )
        story.append(date_text)
        story.append(Spacer(1, 0.2 * inch))

        # Summary section
        summary_text = (
            f"<b>Summary:</b> {metrics.total_sheets} sheets, "
            f"{metrics.total_records} properties validated across "
            f"{len(metrics.countries)} countries"
        )
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        # Metrics table
        table_data = self._build_metrics_table(metrics.country_metrics)
        table = Table(table_data, colWidths=[1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        table.setStyle(self._get_table_style())
        story.append(table)

        story.append(Spacer(1, 0.3 * inch))

        # Footer
        footer_text = (
            f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Policy: .claude/EXECUTION_POLICY.md</i>"
        )
        story.append(Paragraph(footer_text, styles['Normal']))

        doc.build(story)

    def _build_metrics_table(self, metrics: List[CountryMetric]) -> List[List[str]]:
        """Build table data structure for metrics."""
        data = [['Country', 'Properties', 'Passed', 'Pass Rate']]

        for m in metrics:
            pass_rate = f"{m.pass_rate:.1%}"
            data.append([m.country, str(m.total_properties), str(m.passed_validation), pass_rate])

        return data

    def _get_table_style(self) -> TableStyle:
        """Return styled table formatting."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E78')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
        ])


def main() -> None:
    """Generate PDF from Phase 12 output Excel."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 12 PDF Report Generator')
    parser.add_argument(
        '--excel',
        default='output/Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx',
        help='Input Excel workbook path',
    )
    parser.add_argument(
        '--output',
        default='output/Loan4U_Phase12_Final_Report.pdf',
        help='Output PDF path',
    )

    args = parser.parse_args()

    generator = Phase12PDFGenerator(args.output)
    success = generator.generate_from_excel(args.excel, args.output)

    if success:
        print(f"✓ PDF generated: {args.output}")
    else:
        print(f"✗ PDF generation failed")
        exit(1)


if __name__ == '__main__':
    main()
