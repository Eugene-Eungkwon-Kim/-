"""평가서 텍스트 추출과 구조 분석 — 형식 무관 공통 로직.

PDF/DOCX/TXT 각각에서 텍스트를 뽑아내고, 그 텍스트에서 섹션(장/절) 구조와
기본 통계를 뽑는다. 실제 평가서 샘플이나 분석 기준이 아직 없어, 이 모듈은
"숫자로 시작하는 제목 줄을 경계로 섹션을 나눈다"는 흔한 패턴 하나만 다루는
1차 버전이다 — 실제 샘플이 생기면 이 패턴 인식과 통계 항목을 그에 맞게
넓힌다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# "1. 제목", "1) 제목", "제3장", "제5절", "IV. 제목" 형태의 제목 줄만 인식한다.
# 짧은 줄(80자 미만)만 대상으로 해, 본문 중 우연히 숫자로 시작하는 문장이
# 제목으로 오인되는 걸 줄인다.
SECTION_PATTERN = re.compile(
    r"^\s*(?:제?\s*\d+\s*[장절조항]|\d+[.)]\s*\S|[IVXLCDM]+\.\s*\S)"
)
MAX_TITLE_LENGTH = 80


@dataclass
class Section:
    title: str
    start_line: int
    body: str = ""


@dataclass
class ReportAnalysis:
    source: str
    char_count: int
    word_count: int
    line_count: int
    sections: list[Section] = field(default_factory=list)


def extract_text(path: Path) -> str:
    """파일 확장자에 따라 텍스트를 추출한다."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    raise ValueError(f"지원하지 않는 형식: {suffix} (.pdf, .docx, .txt만 지원)")


def _extract_pdf(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_docx(path: Path) -> str:
    import docx

    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def split_sections(text: str) -> list[Section]:
    """제목처럼 보이는 줄을 기준으로 텍스트를 섹션으로 나눈다.

    첫 제목 줄 이전의 텍스트(표지·머리말 등)는 아직 별도로 다루지 않고
    건너뛴다 — 실제 평가서 형식을 보고 필요할 때 추가한다.
    """
    lines = text.splitlines()
    sections: list[Section] = []
    current: Section | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and len(stripped) < MAX_TITLE_LENGTH and SECTION_PATTERN.match(stripped):
            if current is not None:
                sections.append(current)
            current = Section(title=stripped, start_line=i)
        elif current is not None:
            current.body += line + "\n"

    if current is not None:
        sections.append(current)

    return sections


def analyze(text: str, source: str = "") -> ReportAnalysis:
    """텍스트에서 기본 통계와 섹션 구조를 뽑는다."""
    return ReportAnalysis(
        source=source,
        char_count=len(text),
        word_count=len(text.split()),
        line_count=len(text.splitlines()),
        sections=split_sections(text),
    )
