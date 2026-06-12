#!/usr/bin/env python3
"""
모델 검증 스크립트
Phase 4: CI/CD 파이프라인 내 모델 성능 검증
"""

import sys
import os
import joblib
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수에서 기준값 읽기
REQUIRED_R2_SCORE = float(os.getenv('REQUIRED_R2_SCORE', '0.85'))
REQUIRED_RMSE = float(os.getenv('REQUIRED_RMSE', '1000000000'))


def load_model_and_data():
    """모델과 데이터 로드."""
    logger.info("Loading model and data...")

    # 모델 로드
    model_path = project_root / 'models' / 'advanced_best.pkl'
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = joblib.load(model_path)
    logger.info(f"✅ Model loaded: {model_path}")

    # 데이터 로드
    data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_path}")

    df = pd.read_csv(data_path)
    logger.info(f"✅ Data loaded: {len(df)} samples, {len(df.columns)} features")

    # 특성과 목표 분리
    X = df.drop(['id', 'address_sido', 'address_sigungu', 'address_dong',
                 'address_full', 'reference_date', 'approval_date',
                 'property_type', 'hammer_price'],
                axis=1, errors='ignore')
    y = df['hammer_price']

    return model, X, y


def validate_model(model, X, y):
    """모델 성능 검증."""
    logger.info("\n" + "=" * 60)
    logger.info("🔍 Model Validation")
    logger.info("=" * 60)

    # Train-test split
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 예측
    logger.info("[1/3] Making predictions...")
    y_pred = model.predict(X_test)

    # 메트릭 계산
    logger.info("[2/3] Computing metrics...")
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    # 결과 출력
    logger.info(f"\n[3/3] Results:")
    logger.info(f"   R² Score:        {r2:.4f}")
    logger.info(f"   RMSE:            ₩{rmse:,.0f}")
    logger.info(f"   MAE:             ₩{mae:,.0f}")
    logger.info(f"   MAPE:            {mape:.2f}%")

    # 검증
    logger.info(f"\n🔍 Validation against thresholds:")
    logger.info(f"   R² >= {REQUIRED_R2_SCORE}: {r2:.4f} {'✅ PASS' if r2 >= REQUIRED_R2_SCORE else '❌ FAIL'}")
    logger.info(f"   RMSE < {REQUIRED_RMSE:,.0f}: {rmse:,.0f} {'✅ PASS' if rmse < REQUIRED_RMSE else '❌ FAIL'}")

    # 검증 결과
    validation_passed = r2 >= REQUIRED_R2_SCORE and rmse < REQUIRED_RMSE

    if validation_passed:
        logger.info(f"\n✅ All validations PASSED")
    else:
        logger.error(f"\n❌ Some validations FAILED")
        if r2 < REQUIRED_R2_SCORE:
            logger.error(f"   R² {r2:.4f} < {REQUIRED_R2_SCORE}")
        if rmse >= REQUIRED_RMSE:
            logger.error(f"   RMSE {rmse:,.0f} >= {REQUIRED_RMSE:,.0f}")

    return {
        'r2_score': float(r2),
        'rmse': float(rmse),
        'mae': float(mae),
        'mape': float(mape),
        'validation_passed': validation_passed,
        'timestamp': datetime.now().isoformat(),
    }


def save_report(results):
    """검증 리포트 저장."""
    logger.info("\n" + "=" * 60)
    logger.info("💾 Saving validation report...")
    logger.info("=" * 60)

    report_path = project_root / 'model_validation_report.json'
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"✅ Report saved: {report_path}")


def main():
    """메인 실행."""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("🚀 Model Validation Started")
        logger.info("=" * 60)

        # 모델과 데이터 로드
        model, X, y = load_model_and_data()

        # 모델 검증
        results = validate_model(model, X, y)

        # 리포트 저장
        save_report(results)

        # 최종 결과
        logger.info("\n" + "=" * 60)
        if results['validation_passed']:
            logger.info("✅ Model Validation PASSED")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("❌ Model Validation FAILED")
            logger.error("=" * 60)
            return 1

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
