"""
샘플 데이터 생성 스크립트
Generate sample NPL-like data for AVM model development and testing

Author: AI Assistant
Date: 2026-06-09
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_npl_data(n_samples: int = 500, random_state: int = 42) -> pd.DataFrame:
    """
    NPL 데이터를 모방한 샘플 데이터 생성

    Args:
        n_samples: 생성할 샘플 수
        random_state: 랜덤 상태

    Returns:
        pd.DataFrame: 생성된 샘플 데이터
    """
    np.random.seed(random_state)

    # 기본 부동산 정보
    data = {
        # 기본 정보
        'property_id': np.arange(1, n_samples + 1),
        'property_type': np.random.choice(['APT', 'HOUSE', 'COMMERCIAL'], n_samples),

        # 위치 정보
        'region': np.random.choice(['Seoul', 'Busan', 'Incheon', 'Daegu', 'Daejeon'], n_samples),
        'district': np.random.choice(['Gang', 'Jung', 'Dong', 'Seo', 'Nam'], n_samples),

        # 부동산 특성
        'area_sqm': np.random.uniform(30, 500, n_samples),  # 면적 (m²)
        'year_built': np.random.randint(1980, 2023, n_samples),  # 건축년도
        'floor': np.random.randint(1, 50, n_samples),  # 층수
        'total_floor': np.random.randint(1, 60, n_samples),  # 건물 총 층수

        # 특성 (아파트/주택용)
        'rooms': np.random.randint(1, 6, n_samples),  # 방 개수
        'bathrooms': np.random.randint(1, 4, n_samples),  # 욕실 개수
        'parking': np.random.binomial(1, 0.7, n_samples),  # 주차장 여부

        # 상태
        'condition': np.random.choice(['Good', 'Average', 'Fair', 'Poor'], n_samples),

        # NPL 관련 정보
        'original_price': np.random.uniform(100000000, 3000000000, n_samples),  # 원래 가격
        'appraised_price': np.random.uniform(80000000, 2800000000, n_samples),  # 감정가
        'outstanding_debt': np.random.uniform(50000000, 2000000000, n_samples),  # 미수금

        # 시장 데이터
        'market_price': np.random.uniform(100000000, 3000000000, n_samples),  # 시장 가격
        'transaction_count_1y': np.random.poisson(5, n_samples),  # 1년간 거래 횟수

        # 금융 정보
        'ltv': np.random.uniform(0.5, 1.2, n_samples),  # 담보 대출 비율
        'loan_term_months': np.random.randint(12, 360, n_samples),  # 대출 기간

        # 경매 정보
        'days_on_market': np.random.randint(0, 365, n_samples),  # 판매 기간
        'appraisal_rounds': np.random.randint(1, 5, n_samples),  # 감정 라운드
    }

    df = pd.DataFrame(data)

    # 타겟 변수: 최종 거래가 (realistic valuation)
    # 여러 요소를 바탕으로 계산
    df['final_sale_price'] = (
        df['appraised_price'] * 0.5 +
        df['market_price'] * 0.3 +
        df['appraised_price'] * (1 + 0.001 * (2023 - df['year_built'])) * 0.2 +
        np.random.normal(0, df['appraised_price'] * 0.05, n_samples)  # 노이즈
    )

    # 음수 값 처리
    df['final_sale_price'] = df['final_sale_price'].clip(lower=0)

    # 추가 파생 변수
    df['age_years'] = 2023 - df['year_built']
    df['price_per_sqm'] = df['final_sale_price'] / df['area_sqm']
    df['debt_to_price_ratio'] = df['outstanding_debt'] / df['final_sale_price']
    df['price_variance'] = abs(df['final_sale_price'] - df['appraised_price']) / df['appraised_price']

    logger.info(f"✅ 샘플 데이터 생성 완료: {n_samples} 행, {df.shape[1]} 열")
    logger.info(f"   - 최종 거래가 범위: {df['final_sale_price'].min():,.0f} ~ {df['final_sale_price'].max():,.0f}")
    logger.info(f"   - 평균 거래가: {df['final_sale_price'].mean():,.0f}")

    return df


def main():
    """메인 실행 함수"""
    logger.info("=" * 60)
    logger.info("AVM 샘플 데이터 생성 시작")
    logger.info("=" * 60)

    # 데이터 생성
    df = generate_sample_npl_data(n_samples=500)

    # 저장
    output_dir = Path('avm_project/data/raw')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'sample_npl_data.csv'

    df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"✅ 데이터 저장: {output_path}")

    # 통계 정보 출력
    logger.info("\n📊 데이터 통계:")
    logger.info(f"\n{df.describe().to_string()}")

    logger.info("\n📋 데이터 타입:")
    logger.info(f"\n{df.dtypes.to_string()}")

    logger.info("\n✅ 샘플 데이터 생성 완료!")

    return output_path


if __name__ == '__main__':
    main()
