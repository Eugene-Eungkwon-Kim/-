"""
데이터 전처리 파이프라인 테스트
Test data preprocessing pipeline

Author: AI Assistant
Date: 2026-06-09
"""

import sys
sys.path.insert(0, '/home/user/-')

from avm_project.scripts.data_preprocessing import DataPreprocessor
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("AVM 데이터 전처리 파이프라인 테스트 시작")
    logger.info("=" * 70)

    try:
        # 1. 전처리기 초기화
        logger.info("\n[Step 1] 전처리기 초기화")
        preprocessor = DataPreprocessor(
            data_dir='avm_project/data',
            output_dir='avm_project/output'
        )
        logger.info("✅ 전처리기 초기화 완료")

        # 2. 데이터 로드
        logger.info("\n[Step 2] 샘플 데이터 로드")
        data = preprocessor.load_data('raw/sample_npl_data.csv')
        logger.info(f"✅ 데이터 로드 완료: {data.shape}")

        # 3. 데이터 탐색
        logger.info("\n[Step 3] 데이터 탐색 (EDA)")
        stats = preprocessor.explore_data()
        logger.info(f"✅ 데이터 탐색 완료")
        logger.info(f"   - Shape: {stats['shape']}")
        logger.info(f"   - 결측값 개수: {sum(stats['missing_values'].values())}")

        # 4. 결측값 처리
        logger.info("\n[Step 4] 결측값 처리")
        preprocessor.handle_missing_values(method='mean')
        logger.info("✅ 결측값 처리 완료")

        # 5. 이상값 탐지
        logger.info("\n[Step 5] 이상값 탐지 (IQR 방법)")
        outliers = preprocessor.detect_outliers(method='iqr', threshold=1.5)
        logger.info("✅ 이상값 탐지 완료")
        total_outliers = sum(v['count'] for v in outliers.values())
        logger.info(f"   - 탐지된 이상값 개수: {total_outliers}")
        for col, info in list(outliers.items())[:3]:
            logger.info(f"   - {col}: {info['count']} ({info['percentage']:.2f}%)")

        # 6. 데이터 정규화
        logger.info("\n[Step 6] 데이터 정규화 (StandardScaler)")
        numeric_cols = preprocessor.processed_data.select_dtypes(
            include=['number']
        ).columns.tolist()[:5]  # 처음 5개 컬럼만
        data_normalized, scaler_info = preprocessor.normalize_data(
            columns=numeric_cols,
            method='standardize'
        )
        logger.info("✅ 데이터 정규화 완료")
        logger.info(f"   - 정규화된 컬럼 수: {len(scaler_info['columns'])}")

        # 7. 피처 엔지니어링
        logger.info("\n[Step 7] 피처 엔지니어링")
        data_engineered = preprocessor.feature_engineering()
        logger.info("✅ 피처 엔지니어링 완료")
        logger.info(f"   - 총 컬럼 수: {data_engineered.shape[1]}")

        # 8. 전처리된 데이터 저장
        logger.info("\n[Step 8] 전처리된 데이터 저장")
        output_path = preprocessor.save_processed_data(
            filename='processed_sample_data.csv'
        )
        logger.info(f"✅ 데이터 저장 완료: {output_path}")

        # 최종 통계
        logger.info("\n" + "=" * 70)
        logger.info("📊 전처리 완료 통계")
        logger.info("=" * 70)
        logger.info(f"원본 데이터 형태: {data.shape}")
        logger.info(f"전처리 데이터 형태: {preprocessor.processed_data.shape}")
        logger.info(f"추가된 피처 수: {preprocessor.processed_data.shape[1] - data.shape[1]}")
        logger.info(f"저장 위치: {output_path}")

        logger.info("\n✅ 모든 테스트 완료!")
        return True

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
