#!/usr/bin/env python3
"""
Phase 6-4-A: 고급 특성 엔지니어링
목표: 비선형, 상호작용, 클러스터 기반 특성 추가로 모델 성능 향상
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    logger.info("\n" + "="*60)
    logger.info("Phase 6-4-A: 고급 특성 엔지니어링")
    logger.info("="*60)

    # 데이터 로드
    df_original = pd.read_csv(project_root / 'data' / 'preprocessed_data.csv')
    df_features = pd.read_csv(project_root / 'data' / 'preprocessed_data_with_features.csv')

    logger.info(f"\n데이터 로드: {len(df_features)} rows")

    # 기존 15개 특성 읽기
    with open(project_root / 'models' / 'advanced_v2_final_features.txt', 'r') as f:
        feature_list = [line.strip() for line in f.readlines()]

    X_features = df_features[feature_list].copy()
    y_original = df_original['hammer_price']

    logger.info(f"\n[1/4] 비선형 특성 추가...")

    # 1. 비선형 상호작용 특성
    if 'location_score' in X_features.columns:
        X_features['location_score_sq'] = X_features['location_score'] ** 2
        logger.info("   ✓ location_score_sq (지역 점수 제곱)")

    if 'location_score' in X_features.columns and 'building_area_sqm' in X_features.columns:
        X_features['location_area_geometric'] = np.sqrt(
            X_features['location_score'] * X_features['building_area_sqm'] / 100 + 1
        )
        logger.info("   ✓ location_area_geometric (위치×면적 기하평균)")

    if 'price_per_sqm' in X_features.columns:
        X_features['price_per_sqm_sqrt'] = np.sqrt(X_features['price_per_sqm'] + 1)
        logger.info("   ✓ price_per_sqm_sqrt (제곱미터 가격 제곱근)")

    logger.info(f"\n[2/4] 클러스터 기반 특성 추가...")

    # 2. K-Means 클러스터링 (K=5)
    cluster_features = ['location_score', 'building_area_sqm', 'unit_price_py']
    cluster_features = [f for f in cluster_features if f in X_features.columns]

    if len(cluster_features) >= 2:
        X_cluster = X_features[cluster_features].fillna(0)
        scaler_cluster = StandardScaler()
        X_cluster_scaled = scaler_cluster.fit_transform(X_cluster)

        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        X_features['cluster_id'] = kmeans.fit_predict(X_cluster_scaled)

        # 클러스터별 평균 가격
        cluster_avg_price = y_original.groupby(X_features['cluster_id']).mean()
        X_features['cluster_avg_price'] = X_features['cluster_id'].map(cluster_avg_price)

        logger.info("   ✓ cluster_id (K-Means 클러스터, K=5)")
        logger.info("   ✓ cluster_avg_price (클러스터별 평균 가격)")

        # 클러스터별 가격 범위
        cluster_std = y_original.groupby(X_features['cluster_id']).std()
        X_features['cluster_price_std'] = X_features['cluster_id'].map(cluster_std)
        logger.info("   ✓ cluster_price_std (클러스터별 표준편차)")

    logger.info(f"\n[3/4] 이상치 감지 특성 추가...")

    # 3. 이상치 감지
    for location in df_features['address_sigungu'].unique():
        if pd.isna(location):
            continue
        location_mask = df_features['address_sigungu'] == location
        location_prices = y_original[location_mask]

        if len(location_prices) > 2:
            q1 = location_prices.quantile(0.25)
            q3 = location_prices.quantile(0.75)
            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

    # 전체 데이터 기반 사분위수
    q1 = y_original.quantile(0.25)
    q3 = y_original.quantile(0.75)

    X_features['price_quartile'] = pd.qcut(y_original, q=4, labels=[0, 1, 2, 3], duplicates='drop').astype(int)
    logger.info("   ✓ price_quartile (전체 가격 사분위수, 0-3)")

    # 지역별 상대 위치
    X_features['location_quartile'] = 0
    for location in df_features['address_sigungu'].unique():
        if pd.isna(location):
            continue
        location_mask = df_features['address_sigungu'] == location
        if location_mask.sum() > 3:  # 최소 4개 이상만 사분위수 계산
            location_prices = y_original[location_mask]
            try:
                location_quartile = pd.qcut(location_prices, q=4, labels=[0, 1, 2, 3], duplicates='drop')
                X_features.loc[location_mask, 'location_quartile'] = location_quartile.astype(int).values
            except:
                # 사분위수 나누기 실패 시 상대 순위로 대체
                rank_values = location_prices.rank(pct=True)
                X_features.loc[location_mask, 'location_quartile'] = (rank_values * 3).astype(int).values
        else:
            # 샘플이 적으면 전체 기준으로 할당
            X_features.loc[location_mask, 'location_quartile'] = X_features.loc[location_mask, 'price_quartile']

    logger.info("   ✓ location_quartile (지역별 상대 위치, 0-3)")

    logger.info(f"\n[4/4] 추가 상호작용 특성...")

    # 4. 추가 상호작용
    if 'is_gangnam' in X_features.columns and 'is_modern' in X_features.columns:
        X_features['gangnam_modern'] = X_features['is_gangnam'] * X_features['is_modern']
        logger.info("   ✓ gangnam_modern (강남×모던)")

    if 'location_score' in X_features.columns and 'is_premium' in X_features.columns:
        X_features['location_premium'] = X_features['location_score'] * X_features['is_premium'] / 100
        logger.info("   ✓ location_premium (위치점수×프리미엄)")

    # 기존 특성 + 신규 특성 합계
    logger.info(f"\n특성 통계:")
    logger.info(f"   기존: {len(feature_list)}개")
    logger.info(f"   신규: {len(X_features.columns) - len(feature_list)}개")
    logger.info(f"   합계: {len(X_features.columns)}개")

    # 결과 저장
    logger.info(f"\n결과 저장...")

    X_features.to_csv(project_root / 'data' / 'preprocessed_data_advanced_features.csv', index=False)
    logger.info(f"   ✓ preprocessed_data_advanced_features.csv")

    # 특성 목록 저장
    with open(project_root / 'models' / 'advanced_features_list.txt', 'w') as f:
        for feat in X_features.columns:
            f.write(f"{feat}\n")

    logger.info(f"   ✓ advanced_features_list.txt")

    logger.info(f"\n" + "="*60)
    logger.info(f"✅ Phase 6-4-A 완료!")
    logger.info(f"="*60)

    return X_features


if __name__ == "__main__":
    main()
