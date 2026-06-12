#!/usr/bin/env python3
"""
Phase 6-3: 성능 검증
원본 가격으로 MAPE 정확히 계산
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_phase6():
    """Phase 6 성능 검증"""

    logger.info("\n" + "="*60)
    logger.info("🔍 Phase 6: 성능 검증")
    logger.info("="*60)

    # 원본 데이터 로드 (목표변수는 원본 스케일)
    df_original = pd.read_csv(project_root / 'data' / 'preprocessed_data.csv')

    # 특성이 추가된 데이터 로드
    df_features = pd.read_csv(project_root / 'data' / 'preprocessed_data_with_features.csv')

    # 특성 추출
    X_features = df_features.drop(['id', 'address_sido', 'address_sigungu',
                                    'address_dong', 'address_full', 'reference_date',
                                    'approval_date', 'property_type', 'hammer_price'],
                                   axis=1, errors='ignore')

    # 목표변수는 원본 스케일 사용
    y_original = df_original['hammer_price']

    logger.info(f"\n✅ 데이터 로드:")
    logger.info(f"   특성 개수: {len(X_features.columns)}")
    logger.info(f"   샘플 개수: {len(y_original)}")

    # Train-test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X_features, y_original, test_size=0.2, random_state=42
    )

    logger.info(f"   Train: {len(X_train)}, Test: {len(X_test)}")

    # 기존 모델 로드 (Phase 2)
    logger.info(f"\n📊 기존 모델 (Phase 2) 검증:")
    try:
        model_old = joblib.load(project_root / 'models' / 'advanced_best.pkl')

        # Phase 2 데이터 로드
        df_old = pd.read_csv(project_root / 'data' / 'preprocessed_data_normalized.csv')
        X_old = df_old.drop(['id', 'address_sido', 'address_sigungu',
                              'address_dong', 'address_full', 'reference_date',
                              'approval_date', 'property_type', 'hammer_price'],
                             axis=1, errors='ignore')
        y_old = df_old['hammer_price']

        _, X_test_old, _, y_test_old = train_test_split(
            X_old, y_old, test_size=0.2, random_state=42
        )

        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        y_pred_old = model_old.predict(X_test_old)

        # 정규화 역변환 필요 - 하지만 여기서는 상대적 성능만 비교
        logger.info(f"   Train data points: {len(X_test_old)}")

    except Exception as e:
        logger.warning(f"⚠️ Phase 2 모델 로드 실패: {e}")

    # 새로운 모델 로드 (Phase 6)
    logger.info(f"\n🆕 새 모델 (Phase 6) 검증:")
    try:
        model_new = joblib.load(project_root / 'models' / 'advanced_v2.pkl')
        y_pred_new = model_new.predict(X_test)

        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        r2 = r2_score(y_test, y_pred_new)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred_new))
        mae = mean_absolute_error(y_test, y_pred_new)
        mape = np.mean(np.abs((y_test - y_pred_new) / y_test)) * 100

        logger.info(f"   R² Score:        {r2:.4f}")
        logger.info(f"   RMSE:            ₩{rmse:,.0f}")
        logger.info(f"   MAE:             ₩{mae:,.0f}")
        logger.info(f"   MAPE:            {mape:.2f}%")

        logger.info(f"\n📈 개선도:")
        logger.info(f"   이전 MAPE (Phase 2): 19.56%")
        logger.info(f"   현재 MAPE (Phase 6): {mape:.2f}%")

        if mape < 19.56:
            improvement = 19.56 - mape
            logger.info(f"   개선: -{improvement:.2f}% ✅")
        else:
            worsening = mape - 19.56
            logger.info(f"   악화: +{worsening:.2f}% ⚠️")

        # 상세 분석
        logger.info(f"\n🔬 상세 분석:")

        # 절대 오차 분포
        abs_errors = np.abs(y_test - y_pred_new)
        logger.info(f"   절대 오차 통계:")
        logger.info(f"      최소: ₩{abs_errors.min():,.0f}")
        logger.info(f"      중앙: ₩{np.median(abs_errors):,.0f}")
        logger.info(f"      최대: ₩{abs_errors.max():,.0f}")
        logger.info(f"      평균: ₩{abs_errors.mean():,.0f}")

        # 백분위수 오차
        percentiles = [25, 50, 75, 90, 95]
        logger.info(f"   백분위수 절대 오차:")
        for p in percentiles:
            val = np.percentile(abs_errors, p)
            logger.info(f"      p{p}: ₩{val:,.0f}")

        # 예측 정확도 등급
        within_10pct = (np.abs((y_test - y_pred_new) / y_test) <= 0.1).sum()
        within_20pct = (np.abs((y_test - y_pred_new) / y_test) <= 0.2).sum()

        logger.info(f"\n   예측 정확도:")
        logger.info(f"      ±10% 이내: {within_10pct}/{len(y_test)} ({100*within_10pct/len(y_test):.1f}%)")
        logger.info(f"      ±20% 이내: {within_20pct}/{len(y_test)} ({100*within_20pct/len(y_test):.1f}%)")

        # 특성 중요도
        logger.info(f"\n📊 상위 10개 중요 특성:")
        try:
            importance = model_new.feature_importances_
            feature_names = X_features.columns.tolist()

            sorted_idx = np.argsort(importance)[::-1][:10]
            for rank, idx in enumerate(sorted_idx, 1):
                logger.info(f"      {rank}. {feature_names[idx]}: {importance[idx]:.4f}")
        except:
            logger.info("      (특성 중요도 미지원)")

        return {
            'mape': mape,
            'r2': r2,
            'rmse': rmse,
            'mae': mae,
        }

    except Exception as e:
        logger.error(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    logger.info("\n" + "="*60)
    logger.info("🚀 Phase 6-3: 성능 검증 시작")
    logger.info("="*60)

    results = verify_phase6()

    logger.info("\n" + "="*60)
    logger.info("✅ Phase 6 검증 완료!")
    logger.info("="*60)

    # 최종 판정
    if results['mape'] < 17:
        logger.info(f"\n🎉 1단계 목표 달성! MAPE < 17%")
        logger.info(f"   현재: {results['mape']:.2f}%")
    elif results['mape'] < 19.56:
        logger.info(f"\n✅ 개선됨! 계속 진행 필요")
        logger.info(f"   현재: {results['mape']:.2f}%")
    else:
        logger.warning(f"\n⚠️ 목표 미달성. 추가 튜닝 필요")
        logger.info(f"   현재: {results['mape']:.2f}%")


if __name__ == "__main__":
    main()
