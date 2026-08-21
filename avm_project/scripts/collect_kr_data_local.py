"""
로컬 실행 전용 - 한국 부동산 실거래 데이터 수집 스크립트
국토부 실거래가 API (Data.go.kr) → KR_data.csv 생성

실행 방법 (로컬 Windows):
    python collect_kr_data_local.py --api-key YOUR_KEY --months 6 --output KR_data.csv

수집 범위:
    - 아파트 매매 실거래 (RTMSDataSvcAptTradeDev)
    - 지역: 서울(11), 경기(41), 인천(28) - 전국 주요 지역
    - 기간: 최근 N개월
"""

import argparse
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import sys

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger(__name__)

# 국토부 아파트 매매 실거래 API
APT_TRADE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

# 수집 대상 법정동 코드 (시도 코드 앞 2자리)
LAWD_CODES = {
    '서울': ['11110', '11140', '11170', '11200', '11215', '11230',
             '11260', '11290', '11305', '11320', '11350', '11380',
             '11410', '11440', '11470', '11500', '11530', '11545',
             '11560', '11590', '11620', '11650', '11680', '11710', '11740'],
    '경기': ['41110', '41130', '41150', '41170', '41190', '41210',
             '41220', '41250', '41270', '41280', '41290', '41310',
             '41360', '41370', '41390', '41410', '41430', '41450',
             '41460', '41480', '41500', '41550', '41570', '41590'],
    '인천': ['28110', '28140', '28170', '28177', '28185', '28200',
             '28237', '28245', '28260'],
    '부산': ['26110', '26140', '26170', '26200', '26230', '26260',
             '26290', '26320', '26350', '26380', '26410', '26440',
             '26470', '26500', '26530', '26710'],
}

# AVM 모델 필요 컬럼 → API 응답 컬럼 매핑
COLUMN_MAP = {
    '전용면적': 'area_sqm',
    '거래금액': 'new_price',
    '건축년도': 'construction_year',
    '층': 'floor',
    '법정동': 'district',
    '년': 'year',
    '월': 'month',
    '일': 'day',
    '아파트': 'apt_name',
    '지번': 'lot_number',
    '지역코드': 'lawd_cd',
    '도로명': 'road_name',
}


def get_recent_months(n_months: int) -> List[str]:
    """최근 N개월 YYYYMM 리스트."""
    months = []
    now = datetime.now()
    for i in range(1, n_months + 1):
        dt = now - timedelta(days=30 * i)
        months.append(dt.strftime('%Y%m'))
    return months


def fetch_apt_trade(api_key: str, lawd_cd: str, deal_ymd: str, page: int = 1) -> Optional[pd.DataFrame]:
    """아파트 매매 실거래 1페이지 조회."""
    params = {
        'serviceKey': api_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'pageNo': page,
        'numOfRows': 1000,
    }
    try:
        r = requests.get(APT_TRADE_URL, params=params, timeout=30)
        if r.status_code != 200:
            log.warning(f"HTTP {r.status_code}: {lawd_cd} {deal_ymd}")
            return None

        # XML 파싱
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text)

        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text != '00':
            msg = root.findtext('.//resultMsg', '')
            log.warning(f"API Error {result_code.text}: {msg} ({lawd_cd} {deal_ymd})")
            return None

        items = root.findall('.//item')
        if not items:
            return None

        records = []
        for item in items:
            row = {child.tag: (child.text or '').strip() for child in item}
            row['lawd_cd'] = lawd_cd
            records.append(row)

        return pd.DataFrame(records)

    except Exception as e:
        log.warning(f"Fetch error {lawd_cd} {deal_ymd}: {e}")
        return None


def clean_and_map(df: pd.DataFrame) -> pd.DataFrame:
    """API 응답 → AVM 모델 입력 형식 변환."""
    # 컬럼명 매핑
    df = df.rename(columns=COLUMN_MAP)

    # 거래금액: "50,000" → 50000000 (만원 → 원)
    if 'new_price' in df.columns:
        df['new_price'] = (
            df['new_price'].astype(str)
            .str.replace(',', '').str.strip()
            .apply(lambda x: float(x) * 10000 if x.lstrip('-').isdigit() else None)
        )

    # 전용면적: 문자열 → float
    if 'area_sqm' in df.columns:
        df['area_sqm'] = pd.to_numeric(df['area_sqm'], errors='coerce')

    # 건축년도
    if 'construction_year' in df.columns:
        df['construction_year'] = pd.to_numeric(df['construction_year'], errors='coerce')

    # 층
    if 'floor' in df.columns:
        df['floor'] = pd.to_numeric(df['floor'], errors='coerce')

    # 날짜 조합
    for col in ['year', 'month', 'day']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 부동산 유형 (아파트 고정)
    df['property_type'] = 1

    # old_price: 동일 단지 이전 거래가 (없으면 new_price의 95% 추정)
    df['old_price'] = df['new_price'] * 0.95

    # 위도/경도: 법정동 코드 기반 중심좌표 (근사값)
    df['latitude'] = 37.5665    # 추후 Geocoding API로 정밀화
    df['longitude'] = 126.9780

    # 지역코드로 시도 보정
    if 'lawd_cd' in df.columns:
        df['latitude'] = df['lawd_cd'].apply(_estimate_lat)
        df['longitude'] = df['lawd_cd'].apply(_estimate_lng)

    return df.dropna(subset=['area_sqm', 'new_price'])


def _estimate_lat(lawd_cd: str) -> float:
    """법정동 코드 앞 2자리로 위도 추정."""
    region = lawd_cd[:2]
    coords = {
        '11': 37.5665, '41': 37.2750, '28': 37.4563,
        '26': 35.1796, '30': 36.3504, '27': 35.8714,
        '29': 35.1595, '36': 36.6400, '45': 35.8200,
        '47': 36.5760, '48': 35.2300, '46': 35.1600,
        '42': 37.8813, '43': 36.6357, '44': 36.7910,
        '50': 33.4996,
    }
    return coords.get(region, 37.5665)


def _estimate_lng(lawd_cd: str) -> float:
    """법정동 코드 앞 2자리로 경도 추정."""
    region = lawd_cd[:2]
    coords = {
        '11': 126.9780, '41': 127.0095, '28': 126.7052,
        '26': 129.0756, '30': 127.3845, '27': 128.6014,
        '29': 126.8526, '36': 127.2890, '45': 127.1080,
        '47': 128.5055, '48': 128.6811, '46': 126.8526,
        '42': 128.0000, '43': 127.4896, '44': 126.4540,
        '50': 126.5312,
    }
    return coords.get(region, 126.9780)


def collect_all(api_key: str, n_months: int = 6, regions: List[str] = None,
                delay: float = 0.3) -> pd.DataFrame:
    """전체 데이터 수집."""
    if regions is None:
        regions = list(LAWD_CODES.keys())

    months = get_recent_months(n_months)
    all_dfs = []
    total = sum(len(LAWD_CODES[r]) for r in regions if r in LAWD_CODES) * len(months)
    done = 0

    log.info(f"수집 시작: {len(regions)}개 지역 × {len(months)}개월 = {total}개 요청")

    for region in regions:
        codes = LAWD_CODES.get(region, [])
        for lawd_cd in codes:
            for ym in months:
                df = fetch_apt_trade(api_key, lawd_cd, ym)
                if df is not None and len(df) > 0:
                    all_dfs.append(df)
                done += 1
                if done % 20 == 0:
                    log.info(f"진도: {done}/{total} ({done/total*100:.0f}%) | 누적: {sum(len(d) for d in all_dfs):,}건")
                time.sleep(delay)

    if not all_dfs:
        log.error("수집된 데이터 없음")
        return pd.DataFrame()

    raw = pd.concat(all_dfs, ignore_index=True)
    log.info(f"원시 데이터: {len(raw):,}건")

    cleaned = clean_and_map(raw)
    log.info(f"정제 완료: {len(cleaned):,}건 (결측 제거 후)")

    return cleaned


def main():
    parser = argparse.ArgumentParser(description='KR 부동산 실거래 데이터 수집')
    parser.add_argument('--api-key', required=True, help='Data.go.kr 서비스 키')
    parser.add_argument('--months', type=int, default=6, help='수집 기간(개월수, 기본 6)')
    parser.add_argument('--regions', nargs='+',
                        choices=['서울', '경기', '인천', '부산'],
                        default=['서울', '경기'],
                        help='수집 지역 (기본: 서울 경기)')
    parser.add_argument('--output', default='KR_data.csv', help='출력 파일명')
    parser.add_argument('--delay', type=float, default=0.3, help='요청 간격(초, 기본 0.3)')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("KR 부동산 실거래 데이터 수집")
    log.info(f"  지역: {args.regions}")
    log.info(f"  기간: 최근 {args.months}개월")
    log.info(f"  출력: {args.output}")
    log.info("=" * 60)

    df = collect_all(
        api_key=args.api_key,
        n_months=args.months,
        regions=args.regions,
        delay=args.delay,
    )

    if df.empty:
        log.error("데이터 없음 - API 키와 네트워크 확인 필요")
        sys.exit(1)

    output_path = Path(args.output)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    log.info(f"\n✅ 저장 완료: {output_path} ({len(df):,}행 × {len(df.columns)}컬럼)")

    # 기본 통계
    if 'new_price' in df.columns:
        log.info(f"  평균 거래가: {df['new_price'].mean():,.0f}원")
        log.info(f"  평균 면적: {df['area_sqm'].mean():.1f}㎡")
        log.info(f"  기간: {df.get('year', pd.Series([0])).min()}-{df.get('month', pd.Series([0])).max()}")

    print(f"\n다음 단계:")
    print(f"  이 파일({output_path})을 avm_project/data/raw/KR_data.csv 로 업로드하세요.")


if __name__ == '__main__':
    main()
