"""Phase 13.2.3 - 하이퍼파라미터 튜닝 (GridSearchCV, GPU 가속)

XGBoost/LightGBM GPU 기반 하이퍼파라미터 최적화.
5-fold cross-validation, GridSearchCV.

실행:
    python scripts/phase13_2_hyperparameter_tuning.py --country KR
    python scripts/phase13_2_hyperparameter_tuning.py --country all
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from sklearn.model_selection import GridSearchCV
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


class HyperparameterTuner:
    """하이퍼파라미터 튜닝 엔진."""

    def __init__(self, country_code: str, n_jobs: int = -1) -> None:
        """초기화.

        Args:
            country_code: 국가 코드
            n_jobs: 병렬 작업 수 (-1: 최대)
        """
        self.country_code = country_code
        self.n_jobs = n_jobs
        self.gpu_available = torch.cuda.is_available()

    def tune_xgboost_gpu(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """XGBoost GPU 하이퍼파라미터 튜닝.

        Args:
            X_train: 훈련 데이터
            y_train: 타겟 데이터

        Returns:
            최적 파라미터, 최적 점수, CV 결과
        """
        if not XGBOOST_AVAILABLE:
            log.warning("XGBoost not installed")
            return {'status': 'skipped'}

        param_grid = {
            'max_depth': [5, 6, 7],
            'learning_rate': [0.03, 0.05, 0.07],
            'subsample': [0.7, 0.8, 0.9],
        }

        base_model = xgb.XGBRegressor(
            tree_method='gpu_hist' if self.gpu_available else 'hist',
            gpu_id=0 if self.gpu_available else -1,
            n_estimators=500,
            random_state=42,
        )

        grid = GridSearchCV(
            base_model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=self.n_jobs,
        )

        grid.fit(X_train, y_train)

        return {
            'best_params': grid.best_params_,
            'best_score': float(grid.best_score_),
            'cv_results': {
                'mean_test_score': [float(x) for x in grid.cv_results_['mean_test_score']],
                'std_test_score': [float(x) for x in grid.cv_results_['std_test_score']],
            },
            'n_iter': len(grid.cv_results_['params']),
        }

    def tune_lightgbm_gpu(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict:
        """LightGBM GPU 하이퍼파라미터 튜닝.

        Args:
            X_train: 훈련 데이터
            y_train: 타겟 데이터

        Returns:
            최적 파라미터, 최적 점수, CV 결과
        """
        if not LIGHTGBM_AVAILABLE:
            log.warning("LightGBM not installed")
            return {'status': 'skipped'}

        param_grid = {
            'max_depth': [5, 6, 7],
            'learning_rate': [0.03, 0.05, 0.07],
            'num_leaves': [25, 31, 40],
        }

        base_model = lgb.LGBMRegressor(
            device_type='gpu' if self.gpu_available else 'cpu',
            gpu_platform_id=0 if self.gpu_available else None,
            gpu_device_id=0 if self.gpu_available else None,
            n_estimators=500,
            random_state=42,
        )

        grid = GridSearchCV(
            base_model,
            param_grid,
            cv=5,
            scoring='r2',
            n_jobs=self.n_jobs,
        )

        grid.fit(X_train, y_train)

        return {
            'best_params': grid.best_params_,
            'best_score': float(grid.best_score_),
            'cv_results': {
                'mean_test_score': [float(x) for x in grid.cv_results_['mean_test_score']],
                'std_test_score': [float(x) for x in grid.cv_results_['std_test_score']],
            },
            'n_iter': len(grid.cv_results_['params']),
        }

    def tune_all(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> Dict[str, Dict]:
        """모든 모델 하이퍼파라미터 튜닝.

        Args:
            X_train: 훈련 데이터
            y_train: 타겟 데이터

        Returns:
            모델별 튜닝 결과
        """
        results = {}

        log.info(f"[{self.country_code}] XGBoost 하이퍼파라미터 튜닝...")
        results['xgboost'] = self.tune_xgboost_gpu(X_train, y_train)

        log.info(f"[{self.country_code}] LightGBM 하이퍼파라미터 튜닝...")
        results['lightgbm'] = self.tune_lightgbm_gpu(X_train, y_train)

        return results

    def save_results(
        self,
        results: Dict[str, Dict],
        output_dir: Path,
    ) -> Path:
        """튜닝 결과 저장.

        Args:
            results: 튜닝 결과
            output_dir: 저장 디렉토리

        Returns:
            저장 경로
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        save_path = output_dir / f"tuning_results_{self.country_code}.json"

        with open(save_path, 'w') as f:
            json.dump(results, f, indent=2)

        log.info(f"저장: {save_path}")
        return save_path


def generate_tuning_report(results: Dict[str, Dict], country_code: str) -> str:
    """튜닝 결과 보고서 생성.

    Args:
        results: 튜닝 결과
        country_code: 국가 코드

    Returns:
        보고서 텍스트
    """
    report = f"# 하이퍼파라미터 튜닝 결과 ({country_code})\n\n"

    for model_type, result in results.items():
        report += f"## {model_type.upper()}\n\n"

        if result.get('status') == 'skipped':
            report += f"상태: 건너뜀 (라이브러리 미설치)\n\n"
            continue

        report += f"최적 파라미터:\n"
        for key, value in result.get('best_params', {}).items():
            report += f"- {key}: {value}\n"

        report += f"\n최적 점수 (R²): {result.get('best_score', 0):.4f}\n"
        report += f"평가된 조합 수: {result.get('n_iter', 0)}\n\n"

    return report


def main() -> None:
    """메인 실행 함수."""
    log.info("=" * 60)
    log.info("Phase 13.2.3: 하이퍼파라미터 튜닝")
    log.info("=" * 60)

    # 테스트 데이터 생성
    log.info("\n테스트 데이터 생성...")
    np.random.seed(42)
    n_samples, n_features = 500, 5

    X_train = np.random.randn(n_samples, n_features).astype(np.float32)
    y_train = np.random.randn(n_samples).astype(np.float32)

    log.info(f"데이터 크기: {X_train.shape}")

    # KR 국가 튜닝
    log.info("\n[KR] 하이퍼파라미터 튜닝...")
    tuner = HyperparameterTuner('KR', n_jobs=1)
    results = tuner.tune_all(X_train, y_train)

    # 결과 저장
    output_dir = Path("output/hyperparameter_tuning_results")
    tuner.save_results(results, output_dir)

    # 보고서 생성
    report = generate_tuning_report(results, 'KR')
    print("\n" + report)

    log.info("✅ 하이퍼파라미터 튜닝 완료")


if __name__ == '__main__':
    main()
