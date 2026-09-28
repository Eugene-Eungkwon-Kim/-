# 평가서분석 (evaluation-report-analysis)

조직 내부용 평가서 분석 프로젝트입니다. 이 저장소의 다른 프로젝트(모바일 파일 정리 도구, MAARS, AVM)와 마찬가지로 독립적인 하위 프로젝트로 관리합니다.

## 현재 상태 — 1차 버전 (구조 추출·기본 통계)

실제 평가서 샘플이나 구체적인 분석 기준이 아직 없는 상태에서, 있으면 어떤 형태의 평가서 분석에도 필요할 최소 기능부터 만들었습니다: **평가서 파일을 읽어 섹션 구조와 기본 통계를 뽑는 것**.

```bash
pip install -r requirements.txt

python analyze.py 평가서.pdf
python analyze.py 평가서.docx --json 결과.json
```

지원 형식: PDF, DOCX, TXT.

## 아직 안 정해진 것

- **점수화·판정 로직**: 지금은 "섹션이 몇 개, 몇 자짜리인지"만 뽑습니다. 실제로 뭘 기준으로 평가서를 판단해야 하는지(항목별 배점, 통과/보류 기준 등)가 정해지면 `report_analyzer.py`에 추가합니다.
- **실제 평가서 형식**: 섹션 인식은 "1. 제목", "제3장", "IV. 제목" 같은 흔한 패턴만 다룹니다. 실제 샘플을 보면 이 패턴을 그에 맞게 조정해야 할 수 있습니다.
- **스캔 이미지(OCR)**: 지금은 텍스트 레이어가 있는 PDF/DOCX만 지원합니다. 스캔본이 입력이라면 OCR 단계가 추가로 필요합니다.

## 구조

```
evaluation-report-analysis/
├── analyze.py              # CLI 진입점
├── report_analyzer.py      # 텍스트 추출 + 섹션 분리 + 통계 (핵심 로직)
├── requirements.txt        # 런타임 의존성 (pdfplumber, python-docx)
├── requirements-dev.txt    # 테스트 의존성 (pytest, reportlab)
└── tests/
    └── test_report_analyzer.py
```

## 테스트

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q
```
