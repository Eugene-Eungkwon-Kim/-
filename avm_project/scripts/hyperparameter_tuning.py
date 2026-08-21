"""
하이퍼파라미터 최적화 모듈
GridSearchCV를 이용한 Random Forest, Gradient Boosting, XGBoost, LightGBM 튜닝
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb
import logging
import json
import pickle
from pathlib import Path
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HyperparameterTuner:
    """하이퍼파라미터 최적화 클래스"""

    def __init__(self, X_train, y_train, X_val, y_val, models_dir='models', output_dir='output'):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.models_dir = Path(models_dir)
        self.output_dir = Path(output_dir)
        self.results = {}
        self.tuned_models = {}

        self.models_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def tune_random_forest(self, verbose=2):
        """Random Forest 하이퍼파라미터 튜닝"""
        logger.info("=" * 60)
        logger.info("Random Forest 튜닝 시작...")
        logger.info("=" * 60)

        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [15, 20, 25],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2']
        }

        model = RandomForestRegressor(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=verbose
        )

        grid_search.fit(self.X_train, self.y_train)

        best_model = grid_search.best_estimator_
        train_r2 = grid_search.best_score_
        val_r2 = best_model.score(self.X_val, self.y_val)

        logger.info(f"✅ Random Forest 튜닝 완료")
        logger.info(f"   최적 파라미터: {grid_search.best_params_}")
        logger.info(f"   훈련 R²: {train_r2:.4f}")
        logger.info(f"   검증 R²: {val_r2:.4f}")

        result = {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': float(train_r2),
            'val_r2': float(val_r2),
            'cv_results': grid_search.cv_results_,
            'timestamp': datetime.now().isoformat()
        }

        self.tuned_models['random_forest'] = best_model
        self.results['random_forest'] = {k: v for k, v in result.items() if k != 'model'}

        return result

    def tune_gradient_boosting(self, verbose=2):
        """Gradient Boosting 하이퍼파라미터 튜닝"""
        logger.info("=" * 60)
        logger.info("Gradient Boosting 튜닝 시작...")
        logger.info("=" * 60)

        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.05, 0.1],
            'max_depth': [3, 4, 5],
            'subsample': [0.7, 0.8, 0.9],
            'min_samples_split': [2, 5, 10]
        }

        model = GradientBoostingRegressor(random_state=42)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=verbose
        )

        grid_search.fit(self.X_train, self.y_train)

        best_model = grid_search.best_estimator_
        train_r2 = grid_search.best_score_
        val_r2 = best_model.score(self.X_val, self.y_val)

        logger.info(f"✅ Gradient Boosting 튜닝 완료")
        logger.info(f"   최적 파라미터: {grid_search.best_params_}")
        logger.info(f"   훈련 R²: {train_r2:.4f}")
        logger.info(f"   검증 R²: {val_r2:.4f}")

        result = {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': float(train_r2),
            'val_r2': float(val_r2),
            'cv_results': grid_search.cv_results_,
            'timestamp': datetime.now().isoformat()
        }

        self.tuned_models['gradient_boosting'] = best_model
        self.results['gradient_boosting'] = {k: v for k, v in result.items() if k != 'model'}

        return result

    def tune_xgboost(self, verbose=2):
        """XGBoost 하이퍼파라미터 튜닝"""
        logger.info("=" * 60)
        logger.info("XGBoost 튜닝 시작...")
        logger.info("=" * 60)

        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.05, 0.1],
            'max_depth': [4, 5, 6],
            'subsample': [0.7, 0.8, 0.9],
            'colsample_bytree': [0.7, 0.8, 0.9]
        }

        model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=verbose
        )

        grid_search.fit(self.X_train, self.y_train)

        best_model = grid_search.best_estimator_
        train_r2 = grid_search.best_score_
        val_r2 = best_model.score(self.X_val, self.y_val)

        logger.info(f"✅ XGBoost 튜닝 완료")
        logger.info(f"   최적 파라미터: {grid_search.best_params_}")
        logger.info(f"   훈련 R²: {train_r2:.4f}")
        logger.info(f"   검증 R²: {val_r2:.4f}")

        result = {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': float(train_r2),
            'val_r2': float(val_r2),
            'cv_results': grid_search.cv_results_,
            'timestamp': datetime.now().isoformat()
        }

        self.tuned_models['xgboost'] = best_model
        self.results['xgboost'] = {k: v for k, v in result.items() if k != 'model'}

        return result

    def tune_lightgbm(self, verbose=2):
        """LightGBM 하이퍼파라미터 튜닝"""
        logger.info("=" * 60)
        logger.info("LightGBM 튜닝 시작...")
        logger.info("=" * 60)

        param_grid = {
            'n_estimators': [100, 200, 300],
            'learning_rate': [0.01, 0.05, 0.1],
            'num_leaves': [20, 31, 50],
            'max_depth': [5, 6, 7],
            'subsample': [0.7, 0.8, 0.9],
            'colsample_bytree': [0.7, 0.8, 0.9]
        }

        model = lgb.LGBMRegressor(random_state=42, n_jobs=-1)
        grid_search = GridSearchCV(
            model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=-1,
            verbose=verbose
        )

        grid_search.fit(self.X_train, self.y_train)

        best_model = grid_search.best_estimator_
        train_r2 = grid_search.best_score_
        val_r2 = best_model.score(self.X_val, self.y_val)

        logger.info(f"✅ LightGBM 튜닝 완료")
        logger.info(f"   최적 파라미터: {grid_search.best_params_}")
        logger.info(f"   훈련 R²: {train_r2:.4f}")
        logger.info(f"   검증 R²: {val_r2:.4f}")

        result = {
            'model': best_model,
            'best_params': grid_search.best_params_,
            'best_train_r2': float(train_r2),
            'val_r2': float(val_r2),
            'cv_results': grid_search.cv_results_,
            'timestamp': datetime.now().isoformat()
        }

        self.tuned_models['lightgbm'] = best_model
        self.results['lightgbm'] = {k: v for k, v in result.items() if k != 'model'}

        return result

    def save_models_and_results(self):
        """튜닝된 모델과 결과 저장"""
        logger.info("\n" + "=" * 60)
        logger.info("모델 및 결과 저장 중...")
        logger.info("=" * 60)

        # 모델 저장
        for model_name, model in self.tuned_models.items():
            model_path = self.models_dir / f"{model_name}_tuned.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"✅ {model_name} 모델 저장: {model_path}")

        # 결과 저장
        results_path = self.output_dir / "hyperparameter_tuning_results.json"

        # cv_results는 numpy 배열을 포함하므로 직렬화 불가능한 부분 제거
        results_clean = {}
        for key, value in self.results.items():
            results_clean[key] = {
                'best_params': value['best_params'],
                'best_train_r2': value['best_train_r2'],
                'val_r2': value['val_r2'],
                'timestamp': value['timestamp']
            }

        with open(results_path, 'w') as f:
            json.dump(results_clean, f, indent=2)

        logger.info(f"✅ 튜닝 결과 저장: {results_path}")

        return results_clean

    def generate_comparison_report(self):
        """모델 비교 리포트 생성"""
        logger.info("\n" + "=" * 60)
        logger.info("모델 비교 리포트 생성 중...")
        logger.info("=" * 60)

        comparison_data = []
        for model_name, results in self.results.items():
            comparison_data.append({
                'Model': model_name,
                'Train R²': f"{results['best_train_r2']:.4f}",
                'Validation R²': f"{results['val_r2']:.4f}",
                'Improvement': f"{(results['val_r2'] - results['best_train_r2']) * 100:.2f}%"
            })

        df_comparison = pd.DataFrame(comparison_data)

        # CSV 저장
        comparison_path = self.output_dir / "model_comparison_tuned.csv"
        df_comparison.to_csv(comparison_path, index=False)
        logger.info(f"✅ 비교 리포트 저장: {comparison_path}")

        # 콘솔 출력
        logger.info("\n📊 모델 성능 비교:")
        logger.info(df_comparison.to_string(index=False))

        return df_comparison


def run_hyperparameter_tuning():
    """하이퍼파라미터 튜닝 메인 실행"""
    logger.info("\n" + "🚀" * 30)
    logger.info("하이퍼파라미터 최적화 프로세스 시작")
    logger.info("🚀" * 30)

    # 데이터 로드
    logger.info("\n데이터 로드 중...")
    try:
        data = pd.read_csv('output/processed_sample_data.csv')
        logger.info(f"✅ 데이터 로드 완료: {len(data)} 행 × {len(data.columns)} 컬럼")
    except FileNotFoundError:
        logger.error("❌ processed_sample_data.csv를 찾을 수 없습니다!")
        return

    # 숫자 컬럼만 사용
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    target_col = 'final_sale_price'
    if target_col in numeric_cols:
        numeric_cols.remove(target_col)

    X = data[numeric_cols].astype(float)
    y = data[target_col].astype(float)

    logger.info(f"사용 특성: {len(numeric_cols)}개")

    # 데이터 분할
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 정규화
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    logger.info(f"훈련 데이터: {len(X_train_scaled)}개")
    logger.info(f"검증 데이터: {len(X_val_scaled)}개")

    # 튜닝 실행
    tuner = HyperparameterTuner(X_train_scaled, y_train, X_val_scaled, y_val)

    tuner.tune_random_forest(verbose=1)
    tuner.tune_gradient_boosting(verbose=1)
    tuner.tune_xgboost(verbose=1)
    tuner.tune_lightgbm(verbose=1)

    # 결과 저장
    tuner.save_models_and_results()
    tuner.generate_comparison_report()

    logger.info("\n" + "✅" * 30)
    logger.info("하이퍼파라미터 최적화 완료!")
    logger.info("✅" * 30)
    logger.info("\n생성된 파일:")
    logger.info("  - models/random_forest_tuned.pkl")
    logger.info("  - models/gradient_boosting_tuned.pkl")
    logger.info("  - models/xgboost_tuned.pkl")
    logger.info("  - models/lightgbm_tuned.pkl")
    logger.info("  - output/hyperparameter_tuning_results.json")
    logger.info("  - output/model_comparison_tuned.csv")


if __name__ == "__main__":
    run_hyperparameter_tuning()
