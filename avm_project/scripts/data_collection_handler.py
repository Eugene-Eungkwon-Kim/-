"""
AVM 프로젝트 - 한국 부동산 데이터 수집 핸들러
Korean Real Estate Data Collection Handler

Author: AI Development Team
Date: 2026-06-09
"""

import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from typing import Dict, List, Optional, Any
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KoreanRealEstateDataCollector:
    """한국 부동산 데이터 수집 클래스"""

    def __init__(self, api_key: Optional[str] = None, output_dir: str = 'avm_project/data/raw'):
        """
        초기화

        Args:
            api_key: Data.go.kr API 키
            output_dir: 데이터 저장 디렉토리
        """
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # API 기본 설정
        self.base_urls = {
            'real_estate_transaction': 'https://apis.data.go.kr/6440000/budongsanservice/searchAPT',
            'jeonse': 'https://apis.data.go.kr/6440000/budongsanservice/searchJeonse',
            'land_price': 'https://apis.data.go.kr/1611000/nsdi/IndvdLandPriceService/getLandPriceInfo',
            'building_info': 'https://apis.data.go.kr/1611000/nsdi/BuildingService/getBuildingList',
        }

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def check_api_key(self) -> bool:
        """API 키 확인"""
        if not self.api_key:
            logger.warning("⚠️ API 키가 설정되지 않았습니다.")
            logger.info("Data.go.kr에서 API 키를 발급받아주세요:")
            logger.info("1. https://www.data.go.kr/ 접속")
            logger.info("2. 회원가입 및 로그인")
            logger.info("3. 원하는 데이터셋 찾기")
            logger.info("4. '활용신청' 클릭")
            logger.info("5. 승인 후 API 키 확인")
            return False
        return True

    def collect_real_estate_transaction_data(self,
                                             start_date: str = '202401',
                                             end_date: str = '202406',
                                             region_code: Optional[str] = None) -> pd.DataFrame:
        """
        부동산 실거래 데이터 수집

        Args:
            start_date: 시작 월 (YYYYMM)
            end_date: 종료 월 (YYYYMM)
            region_code: 지역코드 (선택사항)

        Returns:
            pd.DataFrame: 수집된 데이터
        """
        logger.info("=" * 70)
        logger.info("부동산 실거래 데이터 수집 시작")
        logger.info("=" * 70)

        if not self.check_api_key():
            logger.warning("API 키 없이 진행할 수 없습니다.")
            return pd.DataFrame()

        all_data = []

        try:
            for month in self._get_month_range(start_date, end_date):
                logger.info(f"\n📅 {month} 데이터 수집 중...")

                params = {
                    'serviceKey': self.api_key,
                    'DEAL_YMD': month,
                    'numOfRows': 100,
                    'pageNo': 1,
                    '_returnType': 'json'
                }

                if region_code:
                    params['REGION_CODE'] = region_code

                response = self._make_api_request(self.base_urls['real_estate_transaction'], params)

                if response and 'response' in response:
                    items = response['response'].get('body', {}).get('items', [])
                    all_data.extend(items)
                    logger.info(f"✅ {len(items)}개 거래 정보 수집")

                time.sleep(0.5)  # API 호출 제한 준수

            if all_data:
                df = pd.DataFrame(all_data)
                output_file = self.output_dir / f'real_estate_transaction_{start_date}_{end_date}.csv'
                df.to_csv(output_file, index=False, encoding='utf-8')
                logger.info(f"\n✅ 총 {len(df)}개 데이터 저장: {output_file}")
                return df
            else:
                logger.warning("수집된 데이터가 없습니다.")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")
            return pd.DataFrame()

    def collect_jeonse_data(self,
                           start_date: str = '202401',
                           end_date: str = '202406') -> pd.DataFrame:
        """
        전월세 실거래 데이터 수집

        Args:
            start_date: 시작 월
            end_date: 종료 월

        Returns:
            pd.DataFrame: 수집된 데이터
        """
        logger.info("\n" + "=" * 70)
        logger.info("전월세 실거래 데이터 수집 시작")
        logger.info("=" * 70)

        if not self.check_api_key():
            return pd.DataFrame()

        all_data = []

        try:
            for month in self._get_month_range(start_date, end_date):
                logger.info(f"📅 {month} 전월세 데이터 수집 중...")

                params = {
                    'serviceKey': self.api_key,
                    'DEAL_YMD': month,
                    'numOfRows': 100,
                    'pageNo': 1,
                    '_returnType': 'json'
                }

                response = self._make_api_request(self.base_urls['jeonse'], params)

                if response and 'response' in response:
                    items = response['response'].get('body', {}).get('items', [])
                    all_data.extend(items)
                    logger.info(f"✅ {len(items)}개 전월세 정보 수집")

                time.sleep(0.5)

            if all_data:
                df = pd.DataFrame(all_data)
                output_file = self.output_dir / f'jeonse_data_{start_date}_{end_date}.csv'
                df.to_csv(output_file, index=False, encoding='utf-8')
                logger.info(f"\n✅ 총 {len(df)}개 데이터 저장: {output_file}")
                return df
            else:
                logger.warning("수집된 데이터가 없습니다.")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")
            return pd.DataFrame()

    def collect_land_price_data(self, target_year: str = '2024') -> pd.DataFrame:
        """
        공시지가 데이터 수집

        Args:
            target_year: 대상 연도

        Returns:
            pd.DataFrame: 수집된 데이터
        """
        logger.info("\n" + "=" * 70)
        logger.info("공시지가 데이터 수집 시작")
        logger.info("=" * 70)

        if not self.check_api_key():
            return pd.DataFrame()

        try:
            params = {
                'serviceKey': self.api_key,
                'stdrYear': target_year,
                'numOfRows': 1000,
                'pageNo': 1,
                '_returnType': 'json'
            }

            response = self._make_api_request(self.base_urls['land_price'], params)

            if response and 'response' in response:
                items = response['response'].get('body', {}).get('items', [])
                df = pd.DataFrame(items)

                output_file = self.output_dir / f'land_price_{target_year}.csv'
                df.to_csv(output_file, index=False, encoding='utf-8')
                logger.info(f"✅ 총 {len(df)}개 지가 데이터 저장: {output_file}")
                return df
            else:
                logger.warning("수집된 데이터가 없습니다.")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")
            return pd.DataFrame()

    def generate_data_collection_guide(self) -> str:
        """
        데이터 수집 가이드 생성

        Returns:
            str: 가이드 문서 경로
        """
        guide_content = """
# AVM 프로젝트 - 한국 부동산 데이터 수집 완전 가이드

## 1. Data.go.kr API 설정

### 1.1 회원가입 및 API 키 발급

**단계별 절차:**

1. **웹사이트 접속**
   - URL: https://www.data.go.kr/

2. **회원가입**
   - 일반/기관 회원가입 선택
   - 이메일, 비밀번호, 기본 정보 입력
   - 이메일 인증 완료

3. **데이터셋 검색 및 활용신청**
   - 검색창에서 "부동산" 검색
   - 원하는 데이터셋 클릭
   - "활용신청" 버튼 클릭
   - 활용 목적 입력 후 신청

4. **API 키 확인**
   - 마이페이지 > "나의 API 이용 현황" 접속
   - 승인된 데이터셋 확인
   - "API 키" 버튼 클릭하여 키 복사

5. **개발계정 등록**
   - "개발계정 관리" 메뉴 접속
   - API 키를 개발계정에 등록
   - 인증키 확인 및 저장

### 1.2 API 호출 테스트

**Python 예제:**

```python
import requests

api_key = 'YOUR_API_KEY'
url = 'https://apis.data.go.kr/6440000/budongsanservice/searchAPT'

params = {
    'serviceKey': api_key,
    'DEAL_YMD': '202406',
    'numOfRows': 10,
    '_returnType': 'json'
}

response = requests.get(url, params=params)
print(response.json())
```

## 2. 주요 데이터셋 상세 정보

### 2.1 부동산 실거래 정보

**API 엔드포인트:**
```
https://apis.data.go.kr/6440000/budongsanservice/searchAPT
```

**필수 파라미터:**
- serviceKey (API 키)
- DEAL_YMD (거래월: YYYYMM)

**선택 파라미터:**
- REGION_CODE (지역코드)
- numOfRows (한 페이지 건수, 기본값: 10, 최대: 100)
- pageNo (페이지 번호, 기본값: 1)

**응답 필드:**
- 거래일자, 지역명, 거래가격
- 도로명주소, 아파트명, 층
- 건물면적, 토지면적, 건축년도

**활용 팁:**
- 월별로 데이터 수집 (API 트래픽 관리)
- 지역코드로 특정 지역만 수집 가능
- 100건 단위로 페이징 처리

### 2.2 공시지가 정보

**API 엔드포인트:**
```
https://apis.data.go.kr/1611000/nsdi/IndvdLandPriceService/getLandPriceInfo
```

**필수 파라미터:**
- serviceKey (API 키)
- stdrYear (기준년도)

**응답 필드:**
- 공시년도, 시도, 시군구
- 지번, 지목, 공시지가
- 지가변동률, 면적, 용도지역

**주의사항:**
- 연 1회 공시 (7월경)
- 대량 데이터이므로 페이징 필수
- 메모리 관리에 주의

## 3. 한국부동산원 데이터 수집

### 3.1 웹 스크래핑

**주요 페이지:**
- 주간 아파트 동향: https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60131
- 아파트 가격지수: https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60109
- 오피스 시장: https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60202

**Python BeautifulSoup 예제:**

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

url = 'https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60109'
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# 테이블 파싱
table = soup.find('table')
df = pd.read_html(str(table))[0]

# CSV로 저장
df.to_csv('apartment_price_index.csv', index=False, encoding='utf-8')
```

### 3.2 엑셀 파일 다운로드

**수동 다운로드 프로세스:**

1. 한국부동산원 사이트 접속
2. 원하는 통계 페이지 이동
3. "다운로드" 또는 "엑셀" 버튼 클릭
4. 파일 저장
5. Python으로 읽기

```python
import pandas as pd

# 엑셀 파일 읽기
df = pd.read_excel('apartment_price_index.xlsx')

# CSV로 변환
df.to_csv('apartment_price_index.csv', index=False, encoding='utf-8')
```

## 4. 데이터 통합 및 정제

### 4.1 데이터 병합

```python
import pandas as pd
from glob import glob

# 모든 CSV 파일 로드
csv_files = glob('avm_project/data/raw/*.csv')
dfs = [pd.read_csv(f) for f in csv_files]

# 데이터 병합
combined_df = pd.concat(dfs, ignore_index=True)

# 저장
combined_df.to_csv('avm_project/data/raw/combined_real_estate_data.csv',
                    index=False, encoding='utf-8')
```

### 4.2 데이터 정제

```python
# 결측값 처리
combined_df.fillna(combined_df.mean(), inplace=True)

# 중복값 제거
combined_df.drop_duplicates(inplace=True)

# 데이터 타입 변환
combined_df['거래가격'] = pd.to_numeric(combined_df['거래가격'], errors='coerce')
combined_df['거래일자'] = pd.to_datetime(combined_df['거래일자'], format='%Y%m%d')

# 저장
combined_df.to_csv('avm_project/data/raw/cleaned_real_estate_data.csv',
                    index=False, encoding='utf-8')
```

## 5. 데이터 저장 및 관리

### 5.1 디렉토리 구조

```
avm_project/data/
├── raw/                          # 원본 데이터
│   ├── real_estate_transaction_*.csv
│   ├── jeonse_data_*.csv
│   ├── land_price_*.csv
│   ├── combined_real_estate_data.csv
│   └── cleaned_real_estate_data.csv
├── processed/                     # 전처리된 데이터
│   └── (전처리 결과)
└── metadata.json                  # 데이터 메타정보
```

### 5.2 메타데이터 기록

```json
{
  "data_collection_date": "2026-06-09",
  "sources": [
    {
      "name": "부동산 실거래 정보",
      "period": "202401-202406",
      "records": 50000,
      "columns": ["거래일자", "지역명", "거래가격", ...]
    },
    {
      "name": "공시지가",
      "year": 2024,
      "records": 100000,
      "columns": ["공시년도", "시도", "공시지가", ...]
    }
  ],
  "total_records": 150000,
  "total_size_mb": 45.5
}
```

## 6. API 호출 제한 및 효율성

### 6.1 Rate Limiting

```python
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 사용
session = create_session_with_retries()
response = session.get(url, params=params)
```

### 6.2 배치 처리

```python
import time
from datetime import datetime, timedelta

# 월별 데이터 수집
current_month = datetime(2024, 1, 1)
end_month = datetime(2024, 6, 30)

while current_month <= end_month:
    month_str = current_month.strftime('%Y%m')
    print(f"수집: {month_str}")

    # API 호출
    # ...

    # 다음 달로 이동
    current_month += timedelta(days=32)
    current_month = current_month.replace(day=1)

    # 요청 제한 준수
    time.sleep(1)
```

## 7. 문제 해결

### 7.1 API 호출 오류

| 오류 | 원인 | 해결책 |
|------|------|--------|
| 400 Bad Request | 파라미터 오류 | 파라미터 형식 확인 |
| 401 Unauthorized | API 키 오류 | API 키 재확인 |
| 429 Too Many Requests | 호출 제한 초과 | 요청 간격 증가 |
| 503 Service Unavailable | 서버 오류 | 일시간 후 재시도 |

### 7.2 데이터 품질 문제

```python
# 데이터 검증
def validate_data(df):
    issues = []

    # 필수 컬럼 확인
    required_cols = ['거래일자', '거래가격', '지역명']
    if not all(col in df.columns for col in required_cols):
        issues.append("필수 컬럼 누락")

    # 데이터 타입 확인
    if df['거래가격'].dtype != 'float64':
        issues.append("거래가격 데이터 타입 오류")

    # 범위 확인
    if (df['거래가격'] < 0).any():
        issues.append("음수 거래가격 발견")

    return issues

# 검증 실행
issues = validate_data(df)
if issues:
    print(f"데이터 문제: {issues}")
```

## 8. 다음 단계

1. **자동화 스크립트 개발**
   - 정기적 데이터 수집 (Cron Job 사용)
   - 자동 정제 및 검증

2. **데이터베이스 구축**
   - PostgreSQL 또는 MongoDB에 저장
   - 색인 생성으로 쿼리 최적화

3. **데이터 통합**
   - 여러 소스의 데이터 통합
   - 공통 키(지번, 주소 등)로 조인

4. **AVM 모델 학습**
   - 전처리된 데이터로 모델 훈련
   - 성능 평가 및 개선

---

**작성일:** 2026-06-09
**최종 업데이트:** 2026-06-09
"""

        output_file = self.output_dir / 'DATA_COLLECTION_GUIDE.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(guide_content)

        logger.info(f"✅ 가이드 저장: {output_file}")
        return str(output_file)

    # ========================= Private Methods =========================

    def _make_api_request(self, url: str, params: Dict) -> Optional[Dict]:
        """
        API 요청 처리

        Args:
            url: API 엔드포인트
            params: 요청 파라미터

        Returns:
            Dict: API 응답
        """
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류: {e}")
            return None

    @staticmethod
    def _get_month_range(start_date: str, end_date: str) -> List[str]:
        """
        날짜 범위에서 월 목록 생성

        Args:
            start_date: 시작 월 (YYYYMM)
            end_date: 종료 월 (YYYYMM)

        Returns:
            List[str]: 월 리스트
        """
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, '%Y%m')
        end = datetime.strptime(end_date, '%Y%m')

        months = []
        current = start
        while current <= end:
            months.append(current.strftime('%Y%m'))
            # 다음 달
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return months


def main():
    """메인 실행 함수"""
    print("\n" + "=" * 70)
    print("AVM 프로젝트 - 한국 부동산 데이터 수집 핸들러")
    print("=" * 70)

    # API 키 설정 (환경변수에서 읽기)
    api_key = os.getenv('DATA_GOK_API_KEY')

    if not api_key:
        print("\n⚠️  API 키가 설정되지 않았습니다.")
        print("다음 방법 중 하나를 선택하세요:")
        print("\n1. 환경변수 설정:")
        print("   export DATA_GOK_API_KEY='your_api_key'")
        print("\n2. 코드에서 직접 설정:")
        print("   collector = KoreanRealEstateDataCollector(api_key='your_api_key')")
        print("\n3. Data.go.kr에서 API 키 발급:")
        print("   https://www.data.go.kr/")
        return

    # 수집기 초기화
    collector = KoreanRealEstateDataCollector(api_key=api_key)

    # 데이터 수집 (API 키가 있을 때만)
    print("\n📊 데이터 수집 옵션:")
    print("1. 부동산 실거래 데이터 수집")
    print("2. 전월세 데이터 수집")
    print("3. 공시지가 데이터 수집")
    print("4. 데이터 수집 가이드 생성")
    print("5. 전체 실행 (모든 데이터 수집)")

    # 가이드 생성 (API 키 없이도 가능)
    print("\n📋 데이터 수집 가이드 생성 중...")
    guide_path = collector.generate_data_collection_guide()
    print(f"✅ 가이드 생성 완료: {guide_path}")

    print("\n" + "=" * 70)
    print("다음 단계:")
    print("1. 생성된 가이드를 참고하여 API 키 발급")
    print("2. 환경변수 또는 코드에 API 키 설정")
    print("3. 데이터 수집 스크립트 실행")
    print("=" * 70)


if __name__ == '__main__':
    main()
