"""Phase 13.2.2 - GPU-가속 국가별 모델 훈련 엔진

XGBoost (gpu_hist), LightGBM (gpu), Gradient Boosting (CPU)
병렬 훈련 및 성능 추적.

실행:
    python scripts/phase13_2_gpu_trainer.py --country KR --models all
    python scripts/phase13_2_gpu_trainer.py --country all --parallel 3
"""

import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_percentage_error

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

import torch

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class GPUModelTrainer:
    """GPU-가속 모델 훈련 엔진."""

    def __init__(self, country_code: str) -> None:
        """초기화.

        Args:
            country_code: 국가 코드 (e.g., 'KR', 'SG')
        """
        self.country_code = country_code
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.gpu_available = torch.cuda.is_available()

    def train_xgboost_gpu(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict:
        """XGBoost GPU 훈련 (tree_method='gpu_hist').

        Args:
            X_train: 훈련 입력 데이터
            y_train: 훈련 타겟 데이터
            X_test: 테스트 입력 데이터
            y_test: 테스트 타겟 데이터

        Returns:
            모델, R², MAPE 포함 딕셔너리
        """
        if not XGBOOST_AVAILABLE:
            log.warning("XGBoost not installed, skipping GPU training")
            return {'status': 'skipped', 'reason': 'xgboost not available'}

        model = xgb.XGBRegressor(
            tree_method='gpu_hist' if self.gpu_available else 'hist',
            gpu_id=0 if self.gpu_available else -1,
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, verbose=10)

        r2 = model.score(X_test, y_test)
        pred = model.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, pred)

        return {
            'model': model,
            'r2': r2,
            'mape': mape,
            'type': 'xgboost',
            'device': self.device,
        }

    def train_lightgbm_gpu(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict:
        """LightGBM GPU 훈련 (device_type='gpu').

        Args:
            X_train: 훈련 입력 데이터
            y_train: 훈련 타겟 데이터
            X_test: 테스트 입력 데이터
            y_test: 테스트 타겟 데이터

        Returns:
            모델, R², MAPE 포함 딕셔너리
        """
        if not LIGHTGBM_AVAILABLE:
            log.warning("LightGBM not installed, skipping GPU training")
            return {'status': 'skipped', 'reason': 'lightgbm not available'}

        model = lgb.LGBMRegressor(
            device_type='gpu' if self.gpu_available else 'cpu',
            gpu_platform_id=0 if self.gpu_available else None,
            gpu_device_id=0 if self.gpu_available else None,
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, verbose=10)

        r2 = model.score(X_test, y_test)
        pred = model.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, pred)

        return {
            'model': model,
            'r2': r2,
            'mape': mape,
            'type': 'lightgbm',
            'device': self.device,
        }

    def train_gradient_boosting(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict:
        """Gradient Boosting 훈련 (scikit-learn, CPU).

        Args:
            X_train: 훈련 입력 데이터
            y_train: 훈련 타겟 데이터
            X_test: 테스트 입력 데이터
            y_test: 테스트 타겟 데이터

        Returns:
            모델, R², MAPE 포함 딕셔너리
        """
        model = GradientBoostingRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            random_state=42,
        )
        model.fit(X_train, y_train)

        r2 = model.score(X_test, y_test)
        pred = model.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, pred)

        return {
            'model': model,
            'r2': r2,
            'mape': mape,
            'type': 'gradient_boosting',
            'device': 'cpu',
        }

    def train_all(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        max_workers: int = 3,
    ) -> Dict[str, Dict]:
        """3개 모델 병렬 훈련.

        Args:
            X_train: 훈련 입력 데이터
            y_train: 훈련 타겟 데이터
            X_test: 테스트 입력 데이터
            y_test: 테스트 타겟 데이터
            max_workers: 병렬 워커 수

        Returns:
            모델 타입별 훈련 결과 딕셔너리
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.train_xgboost_gpu,
                    X_train,
                    y_train,
                    X_test,
                    y_test,
                ): 'xgboost',
                executor.submit(
                    self.train_lightgbm_gpu,
                    X_train,
                    y_train,
                    X_test,
                    y_test,
                ): 'lightgbm',
                executor.submit(
                    self.train_gradient_boosting,
                    X_train,
                    y_train,
                    X_test,
                    y_test,
                ): 'gradient_boosting',
            }

            for future in as_completed(futures):
                model_type = futures[future]
                try:
                    result = future.result()
                    results[model_type] = result
                    if result.get('status') != 'skipped':
                        log.info(
                            f"{self.country_code}/{model_type}: "
                            f"R²={result['r2']:.4f}, MAPE={result['mape']:.4f}"
                        )
                except Exception as e:
                    log.error(f"{self.country_code}/{model_type} 훈련 오류: {e}")
                    results[model_type] = {'status': 'error', 'error': str(e)}

        return results

    def save_models(
        self,
        results: Dict[str, Dict],
        output_dir: Path,
    ) -> Dict[str, Path]:
        """모델 저장.

        Args:
            results: 훈련 결과 딕셔너리
            output_dir: 저장 디렉토리

        Returns:
            모델 타입별 저장 경로 딕셔너리
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths = {}

        for model_type, result in results.items():
            if result.get('status') in ('skipped', 'error'):
                continue

            model = result['model']
            path = output_dir / f"{model_type}_{self.country_code}.pkl"
            joblib.dump(model, path)
            saved_paths[model_type] = path
            log.info(f"저장: {path}")

        return saved_paths


def train_country(
    country_code: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    output_dir: Path,
) -> Tuple[str, Dict]:
    """국가별 훈련 래퍼.

    Args:
        country_code: 국가 코드
        X_train: 훈련 입력 데이터
        y_train: 훈련 타겟 데이터
        X_test: 테스트 입력 데이터
        y_test: 테스트 타겟 데이터
        output_dir: 저장 디렉토리

    Returns:
        (국가 코드, 훈련 결과)
    """
    log.info(f"[{country_code}] 모델 훈련 시작...")
    trainer = GPUModelTrainer(country_code)
    results = trainer.train_all(X_train, y_train, X_test, y_test)
    trainer.save_models(results, output_dir)
    log.info(f"[{country_code}] 모델 훈련 완료")

    return country_code, results


def main() -> None:
    """메인 실행 함수."""
    log.info("=" * 60)
    log.info("Phase 13.2.2: GPU-가속 모델 훈련")
    log.info("=" * 60)

    # 출력 디렉토리
    output_dir = Path("output/trained_models_gpu")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 예시 데이터 생성 (실제로는 country_configs와 realistic_data_generator 사용)
    log.info("\n테스트 데이터 생성...")
    np.random.seed(42)
    n_train, n_test, n_features = 1000, 200, 5

    X = np.random.randn(n_train + n_test, n_features).astype(np.float32)
    y = np.random.randn(n_train + n_test).astype(np.float32)

    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    log.info(f"훈련 데이터: {X_train.shape}, 테스트 데이터: {X_test.shape}")

    # 단일 국가 훈련 (예: KR)
    log.info("\n[KR] 단일 국가 훈련...")
    train_country('KR', X_train, y_train, X_test, y_test, output_dir)

    log.info("\n✅ GPU-가속 모델 훈련 완료")


if __name__ == '__main__':
    main()
