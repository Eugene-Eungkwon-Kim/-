#!/usr/bin/env python3
"""평가서 분석 CLI — PDF/DOCX/TXT 평가서에서 구조와 기본 통계를 뽑는다.

1차 버전: 실제 평가서 샘플·분석 기준이 아직 없어, 텍스트 추출과 섹션 분리,
기본 통계까지만 다룬다. 점수화·항목별 판정 같은 도메인 로직은 실제 평가서
형식이 정해진 뒤에 추가한다.

사용 예:
  python analyze.py report.pdf
  python analyze.py report.docx --json out.json
"""

import argparse
import json
import sys
from pathlib import Path

from report_analyzer import analyze, extract_text


def main() -> int:
    parser = argparse.ArgumentParser(description="평가서 분석 (PDF/DOCX/TXT)")
    parser.add_argument("report", help="분석할 평가서 파일 경로")
    parser.add_argument("--json", help="분석 결과를 저장할 JSON 파일 경로")
    args = parser.parse_args()

    path = Path(args.report)
    if not path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {path}")
        return 1

    try:
        text = extract_text(path)
    except ValueError as e:
        print(f"오류: {e}")
        return 1

    result = analyze(text, source=str(path))

    print(f"파일: {result.source}")
    print(f"글자 수: {result.char_count:,}  단어 수: {result.word_count:,}  줄 수: {result.line_count:,}")
    print(f"감지된 섹션: {len(result.sections)}개")
    for section in result.sections:
        preview = section.body.strip().replace("\n", " ")[:60]
        line = f"  - {section.title}"
        if preview:
            line += f"  ({preview}...)"
        print(line)

    if args.json:
        payload = {
            "source": result.source,
            "char_count": result.char_count,
            "word_count": result.word_count,
            "line_count": result.line_count,
            "sections": [
                {"title": s.title, "start_line": s.start_line, "body": s.body.strip()}
                for s in result.sections
            ],
        }
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nJSON 저장: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
