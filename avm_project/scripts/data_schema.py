"""
Data schema definition and validation
데이터 스키마 정의 및 검증
"""

import logging
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ===== 예상 데이터 스키마 =====
EXPECTED_FEATURES = [
    'area_sqm', 'year_built', 'rooms', 'bathrooms', 'parking',
    'floor', 'total_floor', 'condition', 'original_price', 'appraised_price',
    'outstanding_debt', 'market_price', 'transaction_count_1y', 'ltv',
    'loan_term_months', 'days_on_market', 'appraisal_rounds', 'age_years',
    'price_per_sqm', 'debt_to_price_ratio', 'price_variance',
    'numeric_mean', 'numeric_std', 'numeric_max', 'numeric_min'
]

# 데이터 타입 정의
FEATURE_TYPES = {
    # 수치형
    'area_sqm': (float, int),
    'year_built': (int,),
    'rooms': (int,),
    'bathrooms': (int,),
    'parking': (int,),
    'floor': (int,),
    'total_floor': (int,),
    'condition': (int,),
    'original_price': (float, int),
    'appraised_price': (float, int),
    'outstanding_debt': (float, int),
    'market_price': (float, int),
    'transaction_count_1y': (int,),
    'ltv': (float,),
    'loan_term_months': (int,),
    'days_on_market': (int,),
    'appraisal_rounds': (int,),
    'age_years': (int,),
    'price_per_sqm': (float,),
    'debt_to_price_ratio': (float,),
    'price_variance': (float,),
    'numeric_mean': (float, int),
    'numeric_std': (float, int),
    'numeric_max': (float, int),
    'numeric_min': (float, int),
}

# 값 범위 정의
FEATURE_RANGES = {
    'area_sqm': (10, 1000),
    'year_built': (1900, 2026),
    'rooms': (0, 20),
    'bathrooms': (0, 10),
    'parking': (0, 10),
    'floor': (0, 100),
    'total_floor': (1, 100),
    'condition': (1, 10),
    'original_price': (100, 100000),  # 만원 단위
    'appraised_price': (100, 100000),
    'outstanding_debt': (0, 100000),
    'market_price': (100, 100000),
    'transaction_count_1y': (0, 500),
    'ltv': (0, 2),
    'loan_term_months': (1, 600),
    'days_on_market': (0, 3650),
    'appraisal_rounds': (1, 10),
    'age_years': (0, 150),
    'price_per_sqm': (0, 1000000),
    'debt_to_price_ratio': (0, 2),
    'price_variance': (0, 1),
}


class DataSchema:
    """데이터 스키마 관리"""

    @staticmethod
    def get_expected_features() -> List[str]:
        """예상 필드 목록"""
        return EXPECTED_FEATURES

    @staticmethod
    def validate_features(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        필드 존재 여부 검증

        Args:
            df: 데이터프레임

        Returns:
            (검증 결과, 누락된 필드 리스트)
        """
        missing_features = set(EXPECTED_FEATURES) - set(df.columns)

        if missing_features:
            logger.warning(f"⚠️ 누락된 필드: {missing_features}")
            return False, sorted(list(missing_features))

        logger.info("✅ 모든 필드 존재")
        return True, []

    @staticmethod
    def validate_types(df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        데이터 타입 검증

        Args:
            df: 데이터프레임

        Returns:
            (검증 결과, 타입 오류 정보)
        """
        type_errors = {}

        for feature, expected_types in FEATURE_TYPES.items():
            if feature not in df.columns:
                continue

            col = df[feature]
            actual_type = col.dtype

            # numpy 타입을 Python 타입으로 변환
            if not np.issubdtype(actual_type, np.number):
                if actual_type != 'object':
                    type_errors[feature] = f"Expected numeric, got {actual_type}"

        if type_errors:
            logger.warning(f"⚠️ 타입 오류: {type_errors}")
            return False, type_errors

        logger.info("✅ 모든 필드 타입 검증 완료")
        return True, {}

    @staticmethod
    def validate_ranges(df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        값 범위 검증

        Args:
            df: 데이터프레임

        Returns:
            (검증 결과, 범위 오류 정보)
        """
        range_errors = {}

        for feature, (min_val, max_val) in FEATURE_RANGES.items():
            if feature not in df.columns:
                continue

            col = df[feature]

            # 범위 벗어난 값 확인
            out_of_range = (col < min_val) | (col > max_val)
            out_of_range_count = out_of_range.sum()

            if out_of_range_count > 0:
                range_errors[feature] = {
                    'expected_range': (min_val, max_val),
                    'out_of_range_count': int(out_of_range_count),
                    'percentage': float(out_of_range_count / len(col) * 100)
                }

        if range_errors:
            logger.warning(f"⚠️ 범위 오류: {range_errors}")
            return False, range_errors

        logger.info("✅ 모든 필드 값 범위 검증 완료")
        return True, {}

    @staticmethod
    def validate_missing_values(df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        결측치 검증

        Args:
            df: 데이터프레임

        Returns:
            (검증 결과, 결측치 정보)
        """
        missing_info = {}

        for feature in EXPECTED_FEATURES:
            if feature not in df.columns:
                continue

            missing_count = df[feature].isnull().sum()

            if missing_count > 0:
                missing_info[feature] = {
                    'missing_count': int(missing_count),
                    'percentage': float(missing_count / len(df) * 100)
                }

        if missing_info:
            logger.warning(f"⚠️ 결측치 발견: {missing_info}")
            return False, missing_info

        logger.info("✅ 결측치 없음")
        return True, {}

    @staticmethod
    def validate_duplicates(df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        중복값 검증

        Args:
            df: 데이터프레임

        Returns:
            (검증 결과, 중복값 정보)
        """
        duplicate_info = {}

        # 전체 중복 행 확인
        duplicate_rows = df.duplicated().sum()

        if duplicate_rows > 0:
            duplicate_info['total_duplicates'] = int(duplicate_rows)
            duplicate_info['percentage'] = float(duplicate_rows / len(df) * 100)
            logger.warning(f"⚠️ 중복행 발견: {duplicate_rows}개")
            return False, duplicate_info

        logger.info("✅ 중복값 없음")
        return True, {}

    @staticmethod
    def full_validation(df: pd.DataFrame) -> Dict:
        """
        전체 검증 수행

        Args:
            df: 데이터프레임

        Returns:
            검증 결과 종합 리포트
        """
        logger.info("=" * 70)
        logger.info("📋 데이터 스키마 검증 시작")
        logger.info("=" * 70)

        results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'validations': {}
        }

        # 각 검증 수행
        feature_valid, feature_errors = DataSchema.validate_features(df)
        results['validations']['features'] = {
            'valid': feature_valid,
            'errors': feature_errors
        }

        type_valid, type_errors = DataSchema.validate_types(df)
        results['validations']['types'] = {
            'valid': type_valid,
            'errors': type_errors
        }

        range_valid, range_errors = DataSchema.validate_ranges(df)
        results['validations']['ranges'] = {
            'valid': range_valid,
            'errors': range_errors
        }

        missing_valid, missing_info = DataSchema.validate_missing_values(df)
        results['validations']['missing_values'] = {
            'valid': missing_valid,
            'info': missing_info
        }

        duplicate_valid, duplicate_info = DataSchema.validate_duplicates(df)
        results['validations']['duplicates'] = {
            'valid': duplicate_valid,
            'info': duplicate_info
        }

        # 종합 결과
        all_valid = all(v['valid'] for v in results['validations'].values())
        results['all_valid'] = all_valid

        logger.info("=" * 70)
        if all_valid:
            logger.info("✅ 모든 검증 통과")
        else:
            logger.warning("❌ 검증 실패")
        logger.info("=" * 70)

        return results
