#!/usr/bin/env python3
"""
단계 2: 모델 성능 최적화

기능:
  1. 하이퍼파라미터 자동 튜닝 (GridSearchCV)
  2. 기능 선택 (Feature Selection)
  3. 교차검증 기반 성능 평가
  4. 최적 모델 선택 및 저장
  5. 성능 개선율 리포트

실행: python3 scripts/phase4_model_optimization.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeRegressor

import xgboost as xgb
import lightgbm as lgb
import joblib

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "output"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ModelOptimizer:
    """모델 성능 최적화"""

    def __init__(self):
        self.results = {}
        self.baseline_results = {}
        self.optimized_results = {}

    def load_data(self) -> tuple:
        """학습 데이터 로드"""
        print("📥 데이터 로드")

        # 최신 처리 데이터 찾기
        processed_files = list(DATA_DIR.glob("processed/*.csv"))
        if not processed_files:
            print("   ⚠️  처리된 데이터 없음 — 샘플 사용")
            return self._generate_sample_data()

        latest_file = max(processed_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_file)

        # 특성과 타깃 분리
        from feature_schema import SERVING_FEATURES, TARGET

        if TARGET not in df.columns:
            print(f"   ⚠️  타깃 컬럼 '{TARGET}' 없음 — 마지막 컬럼 사용")
            X = df.iloc[:, :-1]
            y = df.iloc[:, -1]
        else:
            feature_cols = [f for f in SERVING_FEATURES if f in df.columns]
            X = df[feature_cols]
            y = df[TARGET]

        print(f"   ✅ 로드: {X.shape[0]:,} × {X.shape[1]} 특성")
        return X, y

    def _generate_sample_data(self) -> tuple:
        """샘플 데이터 생성"""
        np.random.seed(42)
        n_samples = 500
        n_features = 19

        X = np.random.randn(n_samples, n_features)
        y = X @ np.random.randn(n_features) + np.random.randn(n_samples)

        print(f"   ✅ 샘플 생성: {n_samples} × {n_features}")
        return X, y

    def baseline_evaluation(self, X, y) -> Dict:
        """기준선(Baseline) 모델 평가"""
        print(f"\n[Step 1/3] 기준선 모델 평가")
        print(f"{'='*70}")

        models = {
            'LinearRegression': LinearRegression(),
            'DecisionTree': DecisionTreeRegressor(max_depth=10, random_state=42),
            'RandomForest': RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42),
            'GradientBoosting': GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42),
            'XGBoost': xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42),
            'LightGBM': lgb.LGBMRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42),
        }

        for name, model in models.items():
            print(f"\n🔨 {name}")

            # 교차검증
            pipeline = Pipeline([
                ('scaler', MinMaxScaler()),
                ('model', model)
            ])

            cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring='r2')
            print(f"   CV R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

            self.baseline_results[name] = {
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
            }

        return self.baseline_results

    def hyperparameter_tuning(self, X, y) -> Dict:
        """하이퍼파라미터 튜닝"""
        print(f"\n[Step 2/3] 하이퍼파라미터 튜닝")
        print(f"{'='*70}")

        tuning_params = {
            'RandomForest': {
                'model__n_estimators': [50, 100, 150],
                'model__max_depth': [10, 15, 20],
            },
            'GradientBoosting': {
                'model__n_estimators': [50, 100, 150],
                'model__learning_rate': [0.01, 0.1, 0.2],
            },
        }

        for name, params in tuning_params.items():
            print(f"\n🔧 {name} 튜닝")

            if name == 'RandomForest':
                model = RandomForestRegressor(random_state=42, n_jobs=-1)
            else:
                model = GradientBoostingRegressor(random_state=42)

            pipeline = Pipeline([
                ('scaler', MinMaxScaler()),
                ('model', model)
            ])

            grid_search = GridSearchCV(
                pipeline,
                params,
                cv=5,
                scoring='r2',
                n_jobs=-1,
                verbose=0
            )

            print(f"   검색 중... (조합: {np.prod([len(v) for v in params.values()])}개)")
            grid_search.fit(X, y)

            print(f"   최고 R²: {grid_search.best_score_:.4f}")
            print(f"   최적 파라미터: {grid_search.best_params_}")

            self.optimized_results[name] = {
                "best_score": float(grid_search.best_score_),
                "best_params": str(grid_search.best_params_),
                "improvement": float(grid_search.best_score_ - self.baseline_results[name]["cv_mean"]),
            }

        return self.optimized_results

    def feature_selection(self, X, y) -> Dict:
        """기능 선택 (Feature Selection)"""
        print(f"\n[Step 3/3] 기능 선택")
        print(f"{'='*70}")

        # SelectKBest로 상위 특성 선택
        selector = SelectKBest(f_regression, k='all')
        selector.fit(X, y)

        # 특성 중요도 점수
        scores = selector.scores_
        feature_importance = pd.Series(
            scores,
            index=[f"Feature_{i}" for i in range(len(scores))]
        ).sort_values(ascending=False)

        print(f"\n📊 특성 중요도 (상위 10)")
        for i, (feat, score) in enumerate(feature_importance.head(10).items(), 1):
            print(f"   {i}. {feat}: {score:.4f}")

        # 상위 10개 특성만 사용
        top_k = 10
        top_features = feature_importance.head(top_k).index.tolist()

        # numpy array와 DataFrame 모두 지원
        feature_indices = [int(f.split('_')[1]) for f in top_features]
        if isinstance(X, np.ndarray):
            X_selected = X[:, feature_indices]
        else:
            X_selected = X.iloc[:, feature_indices]

        print(f"\n✅ 상위 {top_k}개 특성 선택")

        return {
            "total_features": len(feature_importance),
            "selected_features": top_k,
            "reduction": f"{(1 - top_k/len(feature_importance))*100:.1f}%"
        }

    def generate_report(self) -> Dict:
        """최종 리포트"""
        print(f"\n{'='*70}")
        print(f"📋 성능 최적화 리포트")
        print(f"{'='*70}")

        report = {
            "timestamp": datetime.now().isoformat(),
            "baseline": self.baseline_results,
            "optimized": self.optimized_results,
            "summary": {
                "best_baseline": max(self.baseline_results.items(), key=lambda x: x[1]["cv_mean"])[0],
                "best_baseline_r2": max(v["cv_mean"] for v in self.baseline_results.values()),
                "best_optimized": max(self.optimized_results.items(), key=lambda x: x[1]["best_score"])[0] if self.optimized_results else "N/A",
                "best_optimized_r2": max((v["best_score"] for v in self.optimized_results.values()), default=0),
                "avg_improvement": np.mean([v["improvement"] for v in self.optimized_results.values()]) if self.optimized_results else 0,
            }
        }

        # 저장
        report_file = OUTPUT_DIR / f"model_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 기준선 모델 최고: {report['summary']['best_baseline']} (R²={report['summary']['best_baseline_r2']:.4f})")
        if report['summary']['best_optimized'] != 'N/A':
            print(f"✅ 최적화 모델 최고: {report['summary']['best_optimized']} (R²={report['summary']['best_optimized_r2']:.4f})")
            print(f"✅ 평균 성능 개선: +{report['summary']['avg_improvement']:.4f}")

        print(f"\n📁 리포트: {report_file.name}")

        return report


def run_optimization() -> Dict:
    """전체 최적화 파이프라인"""
    print(f"\n{'='*80}")
    print(f"🚀 단계 2: 모델 성능 최적화")
    print(f"{'='*80}")

    optimizer = ModelOptimizer()

    # 데이터 로드
    X, y = optimizer.load_data()

    # Step 1: 기준선 평가
    optimizer.baseline_evaluation(X, y)

    # Step 2: 하이퍼파라미터 튜닝
    optimizer.hyperparameter_tuning(X, y)

    # Step 3: 기능 선택
    optimizer.feature_selection(X, y)

    # 리포트 생성
    report = optimizer.generate_report()

    print(f"\n{'='*80}")
    print(f"✅ 모델 성능 최적화 완료")
    print(f"{'='*80}")

    return report


if __name__ == "__main__":
    try:
        report = run_optimization()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
