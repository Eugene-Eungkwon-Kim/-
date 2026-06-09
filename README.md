# NPL AVM 시스템

NPL(부실채권) 담보자산 자동평가모델(AVM) — DB 구축 + REST API

## 프로젝트 구조

```
avm_project/
├── app/
│   ├── main.py                  FastAPI 앱 진입점
│   ├── db/
│   │   ├── models.py            SQLAlchemy ORM 모델
│   │   ├── database.py          DB 연결/세션
│   │   └── ingest.py            파싱데이터 → DB 저장
│   ├── parsers/
│   │   ├── base_parser.py       파서 기반 클래스 + 데이터클래스
│   │   ├── ibk_parser.py        IBK Data Disk 파서
│   │   └── loader.py            금융기관 자동감지 + 파일탐색
│   ├── avm/
│   │   └── engine.py            AVM 추정 엔진 + 낙찰가율 통계
│   └── api/
│       └── routes.py            FastAPI 라우터 (4개 엔드포인트)
├── scripts/
│   ├── ingest_all.py            전체 데이터 DB 적재 스크립트
│   └── run_server.bat           서버 실행 배치파일
├── data/
│   └── npl_avm.db               SQLite DB (자동 생성)
└── requirements.txt
```

## DB 테이블 구조

| 테이블 | 내용 |
|--------|------|
| deals | 딜 정보 (IBK 2025-1, KB 2025-3Q 등) |
| debtors | 차주 정보 |
| properties | 담보물건 (주소, 면적, 근저당, 선순위부담) |
| appraisals | 감정평가 이력 (감정가, 기관, 일자) |
| auctions | 경매 이력 (낙찰가, 유찰회수, 결과) |

## 설치 및 실행

```bash
# 패키지 설치
pip install -r requirements.txt

# IBK 데이터 DB 적재
python scripts/ingest_all.py --institution IBK

# 전체 적재
python scripts/ingest_all.py

# API 서버 실행
scripts\run_server.bat
# 또는
uvicorn app.main:app --reload --port 8000
```

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/v1/avm/estimate | AVM 감정가 추정 |
| GET | /api/v1/precedents | 유사 물건 전례 조회 |
| GET | /api/v1/auction-stats | 낙찰가율 통계 |
| GET | /api/v1/properties/{serial} | 물건 상세 조회 |

Swagger UI: http://localhost:8000/docs

## AVM 추정 요청 예시

```json
POST /api/v1/avm/estimate
{
  "address_sido": "경기도",
  "address_sigungu": "화성시",
  "property_type": "창고",
  "land_area": 10000,
  "building_area": 8000
}
```

## 파서 추가 방법 (금융기관별)

1. `app/parsers/` 에 `kb_parser.py` 등 추가 (IBKParser 참고)
2. `app/parsers/loader.py` 의 `PARSER_MAP` 에 등록

## 향후 개발 계획

- [ ] KB, MG, 우리FNI 파서 추가
- [ ] PDF 감정평가서 OCR 파싱 (비교사례 추출)
- [ ] 헤도닉 회귀모델 고도화 (sklearn)
- [ ] 시점수정계수 적용 (지가변동률, KB시세변화)
- [ ] PostgreSQL 이관 (운영 환경)
- [ ] 인증 (API Key)
