"""
AVM 프로젝트 - 한국 부동산 데이터 수집 가이드 및 스크립트
Data Collection Guide from Data.go.kr and Korean Real Estate Board

Author: AI Development Team
Date: 2026-06-09
"""

# ============================================================
# 1. DATA.GO.KR 부동산 관련 데이터셋
# ============================================================

DATA_GOK_DATASETS = {
    "1. 국토교통부 부동산 실거래 데이터": {
        "dataset_id": "16048670",
        "name": "부동산 실거래 정보",
        "provider": "국토교통부",
        "description": "전국의 부동산(주택/토지/상업용) 실거래 정보",
        "data_type": "월별/지역별 실거래 데이터",
        "format": ["CSV", "XML", "JSON"],
        "fields": [
            "거래일자",
            "지역코드",
            "지역명",
            "거래가격",
            "도로명주소",
            "지번주소",
            "아파트명",
            "층",
            "건물면적",
            "토지면적",
            "건축년도"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/6440000/budongsanservice/searchAPT",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=16048670"
    },

    "2. 국토교통부 아파트 매매 현황": {
        "dataset_id": "15094143",
        "name": "아파트 매매 현황",
        "provider": "국토교통부",
        "description": "전국 아파트 매매 가격 및 거래량 현황",
        "data_type": "월별 통계",
        "format": ["CSV", "Excel"],
        "fields": [
            "연월",
            "지역",
            "아파트명",
            "평균가격",
            "거래량",
            "전월대비_가격변화율",
            "전년대비_가격변화율"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/1613000/AptBizTrend/status",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15094143"
    },

    "3. 국토교통부 전월세 실거래 정보": {
        "dataset_id": "16049552",
        "name": "전월세 실거래 정보",
        "provider": "국토교통부",
        "description": "전국의 전월세 실거래 정보",
        "data_type": "월별 실거래 데이터",
        "format": ["CSV", "XML"],
        "fields": [
            "계약일자",
            "법정동",
            "주택유형",
            "보증금",
            "월세",
            "건물면적",
            "건축년도",
            "계약기간",
            "건물용도"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/6440000/budongsanservice/searchJeonse",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=16049552"
    },

    "4. 공시지가(개별공시지가) 정보": {
        "dataset_id": "15012018",
        "name": "공시지가 정보",
        "provider": "국토교통부",
        "description": "전국 토지의 공시지가 정보",
        "data_type": "연 1회 공시 데이터",
        "format": ["CSV", "Excel"],
        "fields": [
            "공시년도",
            "시도",
            "시군구",
            "지번",
            "지목",
            "공시지가",
            "지가변동률",
            "면적",
            "용도지역"
        ],
        "update_frequency": "연 1회 (7월)",
        "api_endpoint": "https://apis.data.go.kr/1611000/nsdi/IndvdLandPriceService/getLandPriceInfo",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15012018"
    },

    "5. 표준지 공시지가": {
        "dataset_id": "15012017",
        "name": "표준지 공시지가",
        "provider": "국토교통부",
        "description": "전국 표준지의 공시지가",
        "data_type": "연 1회 공시 데이터",
        "format": ["CSV", "Excel"],
        "fields": [
            "공시년도",
            "시도",
            "시군구",
            "지번",
            "표준지공시지가",
            "지가변동률",
            "용도지역",
            "지목"
        ],
        "update_frequency": "연 1회",
        "api_endpoint": "https://apis.data.go.kr/1611000/nsdi/StandarLandPriceService",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15012017"
    },

    "6. 건축물 정보 및 통계": {
        "dataset_id": "15100575",
        "name": "건축물 정보",
        "provider": "국토교통부",
        "description": "전국 건축물의 기본 정보 및 통계",
        "data_type": "건축물 정보",
        "format": ["CSV", "Excel"],
        "fields": [
            "건축물번호",
            "건물용도",
            "건축면적",
            "연면적",
            "건축년도",
            "시도",
            "시군구",
            "도로명주소",
            "주용도_코드",
            "부용도_코드"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/1611000/nsdi/BuildingService/",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15100575"
    },

    "7. 주택가격동향조사": {
        "dataset_id": "15100569",
        "name": "주택가격동향조사",
        "provider": "국토교통부",
        "description": "매월 조사되는 주택가격 동향",
        "data_type": "월별 조사 데이터",
        "format": ["CSV", "Excel"],
        "fields": [
            "조사년월",
            "지역",
            "주택유형",
            "평균가격",
            "전월대비_변화",
            "전년동월대비_변화",
            "거래량",
            "전세_평균가격",
            "월세_평균가격"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/1613000/HousePrcTrendService/",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15100569"
    },

    "8. 토지이용규제정보시스템": {
        "dataset_id": "15057649",
        "name": "토지이용규제 정보",
        "provider": "국토교통부",
        "description": "토지의 이용규제 및 지목 정보",
        "data_type": "공간 데이터",
        "format": ["CSV", "GeoJSON"],
        "fields": [
            "고유번호",
            "토지명",
            "규제기관",
            "규제내용",
            "위도",
            "경도",
            "면적",
            "지목",
            "용도지역"
        ],
        "update_frequency": "수시 업데이트",
        "api_endpoint": "https://apis.data.go.kr/1611000/nsdi/LandUseRestrictionService/",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15057649"
    },

    "9. 지가변동률": {
        "dataset_id": "15012019",
        "name": "지가변동률 정보",
        "provider": "국토교통부",
        "description": "지역별 지가변동률 통계",
        "data_type": "월별/분기별 통계",
        "format": ["CSV", "Excel"],
        "fields": [
            "년월",
            "지역",
            "주택_변동률",
            "토지_변동률",
            "상업용_변동률",
            "산업용_변동률"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/1611000/nsdi/",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15012019"
    },

    "10. 건설기성 통계": {
        "dataset_id": "15004181",
        "name": "건설기성 통계",
        "provider": "통계청",
        "description": "월별 건설기성 현황",
        "data_type": "월별 통계",
        "format": ["CSV", "Excel"],
        "fields": [
            "년월",
            "용도",
            "공사금액",
            "기성금액",
            "기성률",
            "지역"
        ],
        "update_frequency": "월 1회",
        "api_endpoint": "https://apis.data.go.kr/B552015/ConstructionCost/",
        "documentation": "https://www.data.go.kr/tcs/dss/selectApiDetailView.do?publicDataPk=15004181"
    }
}

# ============================================================
# 2. 한국부동산원 데이터 및 API
# ============================================================

KOREAN_REAL_ESTATE_BOARD_DATA = {
    "1. 주간 아파트 동향": {
        "name": "Weekly Apartment Market Trends",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60131",
        "description": "주간 단위의 전국 아파트 시장 동향",
        "data_type": "주간 리포트",
        "format": "PDF, Excel",
        "fields": [
            "전국 아파트 평균가격",
            "지역별 가격",
            "거래량",
            "전주대비 변화",
            "분석 및 전망"
        ],
        "update_frequency": "주 1회 (목요일)",
        "note": "자동 수집을 위해서는 웹 스크래핑 필요"
    },

    "2. 월간 부동산 시장 리포트": {
        "name": "Monthly Real Estate Market Report",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60131",
        "description": "월별 부동산 시장 종합 분석",
        "data_type": "월간 리포트",
        "format": "PDF",
        "fields": [
            "주택 시장 현황",
            "상업용 부동산",
            "오피스 시장",
            "물류 시장",
            "시장 전망"
        ],
        "update_frequency": "월 1회",
        "note": "PDF 형식으로 제공, 텍스트 추출 필요"
    },

    "3. 아파트 가격지수": {
        "name": "Apartment Price Index",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60109",
        "description": "기준시점 대비 아파트 가격 변화율",
        "data_type": "월별 지수",
        "format": "CSV, Excel",
        "fields": [
            "기준월",
            "전국",
            "서울",
            "경기",
            "인천",
            "지방",
            "전월대비_지수",
            "전년동월대비_지수"
        ],
        "update_frequency": "월 1회",
        "note": "웹사이트에서 엑셀 다운로드 가능"
    },

    "4. 오피스 시장 통계": {
        "name": "Office Market Statistics",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60202",
        "description": "전국 오피스 시장의 공급, 수요 현황",
        "data_type": "분기별 통계",
        "format": "Excel",
        "fields": [
            "지역",
            "공급면적",
            "임차면적",
            "공실면적",
            "평균임차료",
            "공실률"
        ],
        "update_frequency": "분기 1회",
        "note": "구글 API를 통한 자동 수집 가능"
    },

    "5. 물류시설 시장 현황": {
        "name": "Logistics Facility Market",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60301",
        "description": "전국 물류시설의 시장 현황",
        "data_type": "분기별 통계",
        "format": "Excel",
        "fields": [
            "지역",
            "신규공급",
            "평균임차료",
            "공실률",
            "평균임차료_전분기대비"
        ],
        "update_frequency": "분기 1회",
        "note": ""
    },

    "6. 주택시장 심리지수": {
        "name": "Housing Market Sentiment Index",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60401",
        "description": "소비자의 부동산 시장 심리 지수",
        "data_type": "월별 지수",
        "format": "Excel",
        "fields": [
            "년월",
            "심리지수_종합",
            "구입희망지수",
            "전망지수",
            "지역별_심리지수"
        ],
        "update_frequency": "월 1회",
        "note": "5점 만점 척도 조사"
    },

    "7. 전월세 시장 분석": {
        "name": "Jeonse & Monthly Rent Market",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60501",
        "description": "전월세 시장의 현황 및 분석",
        "data_type": "월별 분석",
        "format": "PDF, Excel",
        "fields": [
            "전세_평균가격",
            "월세_평균가격",
            "전세전환율",
            "지역별_현황",
            "규모별_현황"
        ],
        "update_frequency": "월 1회",
        "note": ""
    },

    "8. 상가(소매용) 시장": {
        "name": "Commercial Retail Market",
        "source": "한국부동산원",
        "url": "https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60602",
        "description": "전국 상가 소매용 시장 현황",
        "data_type": "분기별 통계",
        "format": "Excel",
        "fields": [
            "지역",
            "평균임차료",
            "공급면적",
            "거래량",
            "지가",
            "변화율"
        ],
        "update_frequency": "분기 1회",
        "note": ""
    }
}

# ============================================================
# 3. 추가 공공 데이터 소스
# ============================================================

ADDITIONAL_SOURCES = {
    "통계청": {
        "name": "Korean Statistical Information Service",
        "url": "https://kostat.go.kr/",
        "datasets": [
            "주택통계",
            "건설통계",
            "소비자동향조사",
            "경기동향지수"
        ]
    },

    "KB금융그룹 경영연구소": {
        "name": "KB Financial Group Research Institute",
        "url": "https://nresearch.kbfg.com/",
        "datasets": [
            "주택가격동향",
            "매매/전세 가격지수",
            "부동산시장 리포트"
        ]
    },

    "현대경제연구원": {
        "name": "Hyundai Economic Research Institute",
        "url": "https://www.hri.co.kr/",
        "datasets": [
            "부동산 시장 분석",
            "지역경제 분석"
        ]
    },

    "한국감정원": {
        "name": "Korea Appraisal Board",
        "url": "https://www.k-apt.go.kr/",
        "datasets": [
            "아파트가격동향",
            "감정평가 통계"
        ]
    },

    "공공데이터 API 포털": {
        "name": "Public Data API Portal",
        "url": "https://www.data.go.kr/",
        "registration_required": True,
        "api_key_needed": True
    }
}

# ============================================================
# 4. 데이터 수집 우선순위
# ============================================================

COLLECTION_PRIORITY = {
    "Phase 1 - 필수 데이터 (즉시 수집)": [
        "국토교통부 부동산 실거래 데이터",
        "부동산 실거래 정보",
        "주택가격동향조사",
        "아파트 가격지수"
    ],

    "Phase 2 - 보조 데이터 (1주일 내 수집)": [
        "공시지가 정보",
        "건축물 정보",
        "전월세 실거래 정보",
        "한국부동산원 아파트 시장 리포트"
    ],

    "Phase 3 - 확장 데이터 (2-3주 내 수집)": [
        "오피스 시장 통계",
        "물류시설 시장",
        "상가 시장 정보",
        "지가변동률",
        "건설기성 통계"
    ],

    "Phase 4 - 심화 분석 (1달 후)": [
        "토지이용규제 정보",
        "주택시장 심리지수",
        "통계청 주택통계",
        "금융기관 시장 리포트"
    ]
}

# ============================================================
# 5. API 요청 필수 정보
# ============================================================

API_REQUIREMENTS = {
    "공공데이터포털 (Data.go.kr) API": {
        "registration": {
            "url": "https://www.data.go.kr/user/mypage/myApiUseList.do",
            "steps": [
                "1. data.go.kr 회원가입",
                "2. API 승인 신청",
                "3. API 키 발급 (승인까지 1-2시간)",
                "4. 개발계정에서 키 등록"
            ],
            "required_info": {
                "service_key": "공공데이터포털 API 키",
                "service_name": "서비스명",
                "return_type": "JSON 또는 XML"
            }
        },

        "rate_limit": {
            "requests_per_second": 10,
            "daily_limit": 10000,
            "monthly_limit": "unlimited"
        },

        "authentication": {
            "method": "Query Parameter",
            "parameter_name": "serviceKey",
            "example_url": "https://apis.data.go.kr/6440000/budongsanservice/searchAPT?serviceKey=YOUR_API_KEY&..."
        }
    },

    "한국부동산원": {
        "registration": "회원가입 불필요 - 웹 스크래핑 또는 직접 다운로드",
        "rate_limit": "일반적인 웹 접속 제한 준수 (과도한 크롤링 금지)",
        "note": "robots.txt 확인 및 서버 부하 고려"
    }
}

print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                   AVM 프로젝트 - 한국 부동산 데이터 수집                          ║
║                  Korean Real Estate Data Collection Guide                      ║
╚════════════════════════════════════════════════════════════════════════════════╝

📊 데이터 소스 요약:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Data.go.kr (공공데이터포털)
   • 총 10개 주요 데이터셋
   • 국토교통부, 통계청, 지자체 데이터
   • API 및 파일 다운로드 방식 지원
   • 가장 신뢰할 수 있는 정부 공식 데이터

✅ 한국부동산원 (Korean Real Estate Board)
   • 8개 전문 리포트 및 지수
   • 주간/월간/분기별 시장 동향
   • 전문적인 시장 분석 제공
   • 웹 스크래핑 또는 수동 다운로드

✅ 추가 공공 데이터
   • 통계청
   • KB금융 연구소
   • 현대경제연구원
   • 한국감정원

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 다음 단계:
   1. Data.go.kr에 회원가입 및 API 키 발급
   2. 데이터 수집 스크립트 작성
   3. 데이터 정제 및 통합
   4. 데이터베이스 저장
   5. AVM 모델 학습에 활용

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
