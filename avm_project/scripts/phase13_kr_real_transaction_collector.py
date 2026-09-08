#!/usr/bin/env python3
"""
Phase 13.8.KR - Real Korean Land Transaction Data Collector
국토교통부 토지 매매 실거래가 API를 사용해 실제 거래 데이터 수집.

API: 국토교통부 토지 매매 실거래가 정보
문서: https://www.data.go.kr/data/15050159/openapi.do

실행:
    python scripts/phase13_kr_real_transaction_collector.py \
      --api-key '9+Sz4Yn+RoH4...' \
      --output data/raw/KR_real_transactions.csv
"""

import argparse
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# 한국 주요 시도 코드
SIDO_CODES = {
    '11': '서울',
    '26': '부산',
    '27': '대구',
    '28': '인천',
    '29': '광주',
    '30': '대전',
    '31': '울산',
    '36': '경기',
    '37': '강원',
    '38': '충북',
    '39': '충남',
    '40': '전북',
    '41': '전남',
    '42': '경북',
    '43': '경남',
    '44': '제주',
}

# 주요 시도별 구군 코드 (서울, 부산, 경기 등 주요 지역)
GUGUN_CODES = {
    '11110': '종로구',
    '11140': '중구',
    '11170': '용산구',
    '11200': '성동구',
    '11215': '광진구',
    '11230': '동대문구',
    '11260': '중랑구',
    '11305': '성북구',
    '11320': '강북구',
    '11350': '도봉구',
    '11380': '노원구',
    '11410': '은평구',
    '11440': '서대문구',
    '11470': '마포구',
    '11500': '양천구',
    '11530': '강서구',
    '11545': '구로구',
    '11560': '금천구',
    '11590': '영등포구',
    '11620': '동작구',
    '11650': '관악구',
    '11680': '서초구',
    '11710': '강남구',
    '11740': '송파구',
    '11770': '강동구',
    # Busan (major districts)
    '26110': '중구',
    '26140': '서구',
    '26170': '동구',
    '26200': '영도구',
    '26230': '부산진구',
    '26260': '동래구',
    '26290': '남구',
    '26320': '북구',
    '26350': '해운대구',
    '26380': '사하구',
    '26410': '금정구',
    '26440': '강서구',
    # Gyeonggi (major cities)
    '36110': '수원시',
    '36130': '성남시',
    '36170': '의정부시',
    '36200': '광명시',
    '36210': '평촌',  # 안양시
    '36220': '고양시',
    '36250': '부천시',
    '36260': '송탄',  # 평택시
    '36280': '안산시',
}

# 거래 기간 (최근 24개월)
END_MONTH = datetime.now()
START_MONTH = END_MONTH - timedelta(days=730)


class KoreanTransactionCollector:
    """국토교통부 API에서 토지 거래 데이터 수집."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = 'http://openapi.molit.go.kr/openapi/service/rest/RTMSOBJSvc/getRTMSDataSvcLandTrade'
        self.data = []

    def fetch_gugun_data(
        self,
        sido_code: str,
        gugun_code: str,
        year_month: str,
    ) -> List[Dict]:
        """
        특정 구군의 특정 월 거래 데이터 조회.

        Args:
            sido_code: 시도 코드
            gugun_code: 구군 코드
            year_month: 조회 연월 (YYYYMM)

        Returns:
            거래 레코드 리스트
        """
        params = {
            'serviceKey': self.api_key,
            'LAWD_CD': gugun_code,
            'DEAL_YM': year_month,
            'numOfRows': '100',
            'pageNo': '1',
        }

        try:
            url = f"{self.base_url}?{urlencode(params)}"
            response = urlopen(url, timeout=10)
            content = response.read().decode('utf-8')

            # XML 파싱 (간단한 정규식 기반)
            import re

            records = []
            items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)

            for item in items:
                record = {}
                fields = {
                    'dealAmount': '거래금액',
                    'area': '거래면적',
                    'dealDate': '계약일자',
                    'dealTime': '계약시간',
                    'bjdCode': '법정동코드',
                    'bjdName': '법정동명',
                    'regTradeName': '지역명',
                }

                for xml_tag, korean_name in fields.items():
                    match = re.search(f'<{xml_tag}>(.*?)</{xml_tag}>', item)
                    if match:
                        record[korean_name] = match.group(1)

                if record:
                    record['시도'] = SIDO_CODES.get(sido_code, '알수없음')
                    record['연월'] = year_month
                    records.append(record)

            return records

        except Exception as e:
            log.warning(f"⚠️  Failed to fetch {gugun_code}/{year_month}: {e}")
            return []

    def collect_data(self) -> None:
        """모든 주요 지역의 거래 데이터 수집."""
        log.info("🇰🇷 국토교통부 토지 거래 데이터 수집 시작")

        # 서울 구군만 우선 수집 (프로토타입)
        sido_code = '11'
        seoul_gugun_codes = [
            '11110', '11140', '11170', '11200', '11215', '11230',
            '11260', '11305', '11320', '11350', '11380', '11410',
            '11440', '11470', '11500', '11530', '11545', '11560',
            '11590', '11620', '11650', '11680', '11710', '11740', '11770',
        ]

        total_records = 0

        for gugun_code in seoul_gugun_codes:
            gugun_name = GUGUN_CODES.get(gugun_code, '알수없음')

            # 최근 12개월 데이터 수집
            current = START_MONTH
            while current <= END_MONTH:
                year_month = current.strftime('%Y%m')

                records = self.fetch_gugun_data(sido_code, gugun_code, year_month)
                self.data.extend(records)
                total_records += len(records)

                if records:
                    log.info(f"  {gugun_name} {year_month}: {len(records)} 건")

                current += timedelta(days=32)
                time.sleep(0.5)  # API 레이트 리미팅

        log.info(f"\n✅ 수집 완료: 총 {total_records}건")

    def process_data(self) -> pd.DataFrame:
        """수집한 데이터 전처리."""
        if not self.data:
            log.warning("⚠️  No data collected")
            return pd.DataFrame()

        df = pd.DataFrame(self.data)

        # 데이터 정제
        # 거래금액: 숫자로 변환 (단위: 원)
        if '거래금액' in df.columns:
            df['거래금액'] = pd.to_numeric(df['거래금액'], errors='coerce')

        # 거래면적: 숫자로 변환 (단위: ㎡)
        if '거래면적' in df.columns:
            df['거래면적'] = pd.to_numeric(df['거래면적'], errors='coerce')

        # 결측값 제거
        df = df.dropna(subset=['거래금액', '거래면적'])

        # 이상치 제거 (금액과 면적이 0 이상)
        df = df[(df['거래금액'] > 0) & (df['거래면적'] > 0)]

        # 평당 가격 계산 (㎡당 가격)
        df['평당가격'] = (df['거래금액'] / df['거래면적']).astype(int)

        return df

    def save_data(self, output_path: Path) -> None:
        """데이터를 CSV로 저장."""
        df = self.process_data()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        log.info(f"\n✅ 데이터 저장: {output_path}")
        log.info(f"  행 수: {len(df):,}")
        log.info(f"  열 수: {len(df.columns)}")
        log.info(f"\n📊 통계:")
        log.info(f"  거래금액 평균: {df['거래금액'].mean():,.0f}원")
        log.info(f"  거래금액 범위: {df['거래금액'].min():,.0f}~{df['거래금액'].max():,.0f}원")
        log.info(f"  거래면적 평균: {df['거래면적'].mean():,.1f}㎡")
        log.info(f"  평당 가격 평균: {df['평당가격'].mean():,.0f}원/㎡")


def main() -> None:
    parser = argparse.ArgumentParser(description='국토교통부 토지 거래 데이터 수집')
    parser.add_argument('--api-key', required=True, help='국토교통부 API 인증키')
    parser.add_argument('--output', default='data/raw/KR_real_transactions.csv')
    args = parser.parse_args()

    collector = KoreanTransactionCollector(args.api_key)
    collector.collect_data()
    collector.save_data(Path(args.output))


if __name__ == '__main__':
    main()
