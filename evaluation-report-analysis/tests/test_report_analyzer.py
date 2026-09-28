import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from report_analyzer import analyze, extract_text, split_sections

SAMPLE = """평가서

1. 개요
이 평가서는 예시입니다.
전체 2줄짜리 설명입니다.

2. 세부 평가
가. 항목 하나
나. 항목 둘

3. 종합 의견
전체적으로 양호합니다.
"""


def test_split_sections_detects_numbered_headings():
    sections = split_sections(SAMPLE)
    assert [s.title for s in sections] == ["1. 개요", "2. 세부 평가", "3. 종합 의견"]


def test_split_sections_keeps_body_under_its_heading():
    sections = split_sections(SAMPLE)
    assert "이 평가서는 예시입니다" in sections[0].body
    assert "가. 항목 하나" in sections[1].body
    assert "전체적으로 양호합니다" in sections[2].body


def test_analyze_counts_and_sections():
    result = analyze(SAMPLE, source="sample.txt")
    assert result.source == "sample.txt"
    assert result.char_count == len(SAMPLE)
    assert result.word_count == len(SAMPLE.split())
    assert result.line_count == len(SAMPLE.splitlines())
    assert len(result.sections) == 3


def test_extract_text_txt(tmp_path):
    p = tmp_path / "r.txt"
    p.write_text(SAMPLE, encoding="utf-8")
    assert extract_text(p) == SAMPLE


def test_extract_text_unsupported_extension(tmp_path):
    p = tmp_path / "r.xyz"
    p.write_text("x", encoding="utf-8")
    try:
        extract_text(p)
        assert False, "ValueError를 기대했지만 발생하지 않음"
    except ValueError:
        pass


def test_extract_text_docx(tmp_path):
    docx = __import__("docx")
    doc = docx.Document()
    doc.add_paragraph("1. 개요")
    doc.add_paragraph("문서 형식 테스트입니다.")
    p = tmp_path / "r.docx"
    doc.save(p)

    text = extract_text(p)
    assert "1. 개요" in text
    assert "문서 형식 테스트입니다." in text


def test_extract_text_pdf(tmp_path):
    from reportlab.pdfgen import canvas

    p = tmp_path / "r.pdf"
    c = canvas.Canvas(str(p))
    c.drawString(100, 750, "1. Overview")
    c.drawString(100, 730, "PDF extraction test.")
    c.save()

    text = extract_text(p)
    assert "1. Overview" in text
    assert "PDF extraction test." in text
