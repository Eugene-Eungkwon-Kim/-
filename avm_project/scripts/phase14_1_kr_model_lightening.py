#!/usr/bin/env python3
"""
Phase 14.1.KR - Model Lightening (StackingRegressor → Single LightGBM)

목표: 4배 크기 축소(75MB → ~19MB)를 달성하기 위해
5개 기본 모델 + Ridge 스태킹 대신 단일 LightGBM으로 재학습.
정확도-크기 트레이드오프를 실측으로 검증.

실행:
    python scripts/phase14_1_kr_model_lightening.py \
      --data data/raw/KR_raw.csv \
      --output output/models/korea/lightened
"""

import json
import logging
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'price_local'
LEAK_PATTERNS = ('price_local', 'indexed_price')
KOREA_MAPE_TARGET = 0.11


class LightweightModelTrainer:
    """단일 LightGBM 모델로 경량화."""

    def __init__(self, data_file: str = 'data/raw/KR_raw.csv') -> None:
        self.data_file = Path(data_file)
        self.results = []

    def load_data(self) -> pd.DataFrame:
        """데이터 로드."""
        df = pd.read_csv(self.data_file)
        log.info(f"✅ Loaded: {len(df):,} rows, {len(df.columns)} cols")
        return df

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """특성 준비 (현재 스태킹과 동일 전처리)."""
        y = df[TARGET_COL].to_numpy(dtype=np.float64)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if not any(p in c for p in LEAK_PATTERNS)]
        X = df[feature_cols].fillna(0.0).to_numpy(dtype=np.float64)
        return X, y, feature_cols

    def slice_region(self, df: pd.DataFrame, region: Optional[str]) -> pd.DataFrame:
        """지역 슬라이싱."""
        return df if region is None else df[df['region'] == region]

    def train_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int,
        max_depth: int,
        learning_rate: float = 0.05,
    ) -> lgb.LGBMRegressor:
        """LightGBM 학습."""
        model = lgb.LGBMRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.8,
            num_leaves=31,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        model.fit(X_train, y_train)
        return model

    def evaluate_model(
        self,
        model: lgb.LGBMRegressor,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict[str, float]:
        """평가."""
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)
        return {
            'train_mape': float(mean_absolute_percentage_error(y_train, train_pred)),
            'test_mape': float(mean_absolute_percentage_error(y_test, test_pred)),
            'train_r2': float(r2_score(y_train, train_pred)),
            'test_r2': float(r2_score(y_test, test_pred)),
        }

    def train_variant(
        self,
        model_name: str,
        region: Optional[str],
        df: pd.DataFrame,
        n_estimators: int,
        max_depth: int,
    ) -> Dict:
        """단일 변형 학습."""
        df_scope = self.slice_region(df, region)
        X, y, feature_cols = self.prepare_features(df_scope)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 학습
        t0 = time.time()
        model = self.train_model(X_train, y_train, n_estimators, max_depth)
        elapsed = time.time() - t0

        # 평가
        metrics = self.evaluate_model(model, X_train, y_train, X_test, y_test)

        # 크기
        pkl_path_temp = Path(f'/tmp/{model_name}.pkl')
        with open(pkl_path_temp, 'wb') as f:
            pickle.dump(model, f)
        pkl_mb = pkl_path_temp.stat().st_size / 1024 / 1024
        pkl_path_temp.unlink()

        region_str = region or 'nationwide'
        log.info(
            f"  {model_name:30} {pkl_mb:6.1f}MB | "
            f"MAPE {metrics['test_mape']:.4f} R² {metrics['test_r2']:.4f} | "
            f"{elapsed:.1f}s {'✅' if metrics['test_mape'] < KOREA_MAPE_TARGET else '⚠️'}"
        )

        return {
            'model_name': model_name,
            'region': region_str,
            'hyperparams': {'n_estimators': n_estimators, 'max_depth': max_depth},
            'n_samples': len(df_scope),
            'pkl_mb': round(pkl_mb, 2),
            'metrics': metrics,
            'meets_target': metrics['test_mape'] < KOREA_MAPE_TARGET,
            'training_sec': round(elapsed, 1),
            'feature_cols': feature_cols,
            'model': model,
        }

    def compare_nationwide(self, df: pd.DataFrame) -> None:
        """전국 모델 비교."""
        log.info("\n" + "=" * 80)
        log.info("Nationwide Model Variants (전국 모델 비교)")
        log.info("=" * 80)

        variants = [
            ('LightGBM-300-8', 300, 8),
            ('LightGBM-200-7', 200, 7),
            ('LightGBM-100-6', 100, 6),
            ('LightGBM-50-5', 50, 5),
            ('LightGBM-50-4', 50, 4),
        ]

        for name, n_est, depth in variants:
            result = self.train_variant(name, None, df, n_est, depth)
            self.results.append(result)

    def compare_regional(self, df: pd.DataFrame) -> None:
        """지역 모델 비교 (Seoul만)."""
        log.info("\n" + "=" * 80)
        log.info("Regional Model Variant (Seoul, 경량화 후보)")
        log.info("=" * 80)

        result = self.train_variant('LightGBM-100-6-Seoul', 'Seoul', df, 100, 6)
        self.results.append(result)

    def print_summary(self) -> None:
        """요약 출력."""
        log.info("\n" + "=" * 80)
        log.info("Model Size & Accuracy Trade-off Summary")
        log.info("=" * 80)
        log.info(
            f"{'Model':<30} {'Size':>7} {'MAPE':>8} {'R²':>7} "
            f"{'Meets Target':>12} {'vs Stacking':>12}"
        )
        log.info("-" * 80)

        stacking_size = 75.9  # Current nationwide stacking size
        stacking_mape = 0.8361  # Current nationwide MAPE

        for r in self.results:
            size_mb = r['pkl_mb']
            mape = r['metrics']['test_mape']
            r2 = r['metrics']['test_r2']
            meets = "✅" if r['meets_target'] else "❌"
            reduction = f"{stacking_size / size_mb:.2f}x" if size_mb else "?"
            mape_delta = f"{(mape - stacking_mape) * 100:+.1f}%" if stacking_mape else "?"

            log.info(
                f"{r['model_name']:<30} {size_mb:>6.1f}MB "
                f"{mape:>8.4f} {r2:>7.4f} {meets:>12} "
                f"{reduction:>8} {mape_delta:>8}"
            )

        log.info("-" * 80)
        log.info("\n🎯 목표 달성 조건:")
        log.info("  1. MAPE < 11% (한국 시장 목표) → ✅ 달성한 모델 수")
        log.info("  2. 크기 4배 이상 축소 (75MB → 19MB 이하)")
        log.info(
            f"\n💡 평가: 단일 LightGBM은 스태킹 대비 "
            f"{max(r['pkl_mb'] for r in self.results):.1f}~{min(r['pkl_mb'] for r in self.results):.1f}MB, "
            f"4배 목표는 {f'달성 가능' if min(r['pkl_mb'] for r in self.results) <= 19 else '어려움'}"
        )

    def run(self) -> None:
        """전체 파이프라인."""
        log.info("🇰🇷 Phase 14.1.KR Model Lightening (경량화 비교)")
        df = self.load_data()

        self.compare_nationwide(df)
        self.compare_regional(df)

        self.print_summary()

        # JSON 리포트
        report = {
            'timestamp': datetime.now().isoformat(),
            'objective': 'Compare StackingRegressor vs Single LightGBM for size reduction',
            'current_stacking': {
                'pkl_mb': 75.9,
                'mape': 0.8361,
                'r2': 0.404,
                'n_estimators': '5 base + Ridge meta',
            },
            'target': '4x reduction (75MB → 19MB) while keeping MAPE < 11%',
            'variants': self.results,
        }
        report_path = Path('output/models/korea/lightening_report.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        log.info(f"\n✅ Report: {report_path}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Phase 14.1.KR Model Lightening')
    parser.add_argument('--data', default='data/raw/KR_raw.csv')
    args = parser.parse_args()

    trainer = LightweightModelTrainer(args.data)
    trainer.run()
