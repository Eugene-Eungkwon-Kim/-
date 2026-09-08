"""
모델 튜닝 완료 후 결과 정리 및 API 업데이트
"""

import subprocess
import os
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def finalize_tuning():
    """튜닝 완료 후 처리"""
    logger.info("\n" + "=" * 60)
    logger.info("모델 튜닝 최종화 시작")
    logger.info("=" * 60)

    output_dir = Path('output')

    # 생성된 파일 확인
    files_to_check = [
        'hyperparameter_tuning_results.json',
        'model_comparison_tuned.csv'
    ]

    logger.info("\n생성된 파일 확인 중...")
    for file in files_to_check:
        file_path = output_dir / file
        if file_path.exists():
            size = file_path.stat().st_size
            logger.info(f"✅ {file}: {size:,} bytes")
        else:
            logger.warning(f"⏳ {file}: 아직 생성 전")

    # 모델 파일 확인
    logger.info("\n튜닝된 모델 확인 중...")
    models_dir = Path('models')
    tuned_models = list(models_dir.glob('*_tuned.pkl'))

    if tuned_models:
        logger.info(f"✅ {len(tuned_models)}개 튜닝된 모델 발견:")
        for model_file in tuned_models:
            logger.info(f"   - {model_file.name}")

    # 결과 파일이 생성되었는지 확인
    results_file = output_dir / 'hyperparameter_tuning_results.json'
    if results_file.exists():
        with open(results_file, 'r') as f:
            results = json.load(f)

        logger.info("\n📊 모델 성능 요약:")
        logger.info(f"{'모델':<20} {'훈련 R²':<12} {'검증 R²':<12}")
        logger.info("-" * 44)

        for model_name, data in results.items():
            train_r2 = data['best_train_r2']
            val_r2 = data['val_r2']
            logger.info(f"{model_name:<20} {train_r2:.4f}        {val_r2:.4f}")

    logger.info("\n" + "=" * 60)
    logger.info("모델 튜닝 완료!")
    logger.info("=" * 60)
    logger.info("\n다음 단계:")
    logger.info("1. 배포된 Cloud Run API 확인")
    logger.info("2. 튜닝된 모델로 새 이미지 빌드")
    logger.info("3. API 업데이트")
    logger.info("4. OPTION 3 (실제 데이터) 준비")


if __name__ == "__main__":
    finalize_tuning()
