"""
AVM 모델 개발 - 모델 학습 및 평가 스크립트
Model Development for Automated Valuation Model

Author: AI Assistant
Date: 2026-06-09
"""

import pandas as pd
import numpy as np
import pickle
import logging
from pathlib import Path
from typing import Tuple, Dict, Any
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AVMModelDeveloper:
    """AVM 모델 개발 클래스"""

    def __init__(self, models_dir: str = 'models', output_dir: str = 'output'):
        """
        초기화

        Args:
            models_dir: 모델 저장 디렉토리
            output_dir: 출력 디렉토리
        """
        self.models_dir = Path(models_dir)
        self.output_dir = Path(output_dir)
        self.models = {}
        self.evaluation_results = {}

        # 디렉토리 생성
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_data(self, data: pd.DataFrame,
                    target_col: str,
                    test_size: float = 0.2,
                    random_state: int = 42) -> Tuple[np.ndarray, np.ndarray,
                                                      np.ndarray, np.ndarray]:
        """
        데이터 분할

        Args:
            data: 전체 데이터
            target_col: 타겟 컬럼명
            test_size: 테스트 세트 비율
            random_state: 랜덤 상태

        Returns:
            Tuple: X_train, X_test, y_train, y_test
        """
        X = data.drop(columns=[target_col])
        y = data[target_col]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        logger.info(f"데이터 분할 완료: Train={X_train.shape}, Test={X_test.shape}")
        return X_train, X_test, y_train, y_test

    def train_linear_regression(self, X_train: np.ndarray, y_train: np.ndarray) -> object:
        """
        선형 회귀 모델 학습

        Args:
            X_train: 훈련 특성
            y_train: 훈련 타겟

        Returns:
            학습된 모델
        """
        logger.info("선형 회귀 모델 학습 시작")
        model = LinearRegression()
        model.fit(X_train, y_train)
        self.models['linear_regression'] = model
        logger.info("선형 회귀 모델 학습 완료")
        return model

    def train_decision_tree(self, X_train: np.ndarray, y_train: np.ndarray,
                           max_depth: int = 10) -> object:
        """
        의사결정 트리 모델 학습

        Args:
            X_train: 훈련 특성
            y_train: 훈련 타겟
            max_depth: 최대 깊이

        Returns:
            학습된 모델
        """
        logger.info("의사결정 트리 모델 학습 시작")
        model = DecisionTreeRegressor(max_depth=max_depth, random_state=42)
        model.fit(X_train, y_train)
        self.models['decision_tree'] = model
        logger.info("의사결정 트리 모델 학습 완료")
        return model

    def train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray,
                           n_estimators: int = 100,
                           max_depth: int = 15) -> object:
        """
        랜덤 포레스트 모델 학습

        Args:
            X_train: 훈련 특성
            y_train: 훈련 타겟
            n_estimators: 트리 개수
            max_depth: 최대 깊이

        Returns:
            학습된 모델
        """
        logger.info("랜덤 포레스트 모델 학습 시작")
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        self.models['random_forest'] = model
        logger.info("랜덤 포레스트 모델 학습 완료")
        return model

    def train_gradient_boosting(self, X_train: np.ndarray, y_train: np.ndarray,
                               n_estimators: int = 100,
                               learning_rate: float = 0.1) -> object:
        """
        그래디언트 부스팅 모델 학습

        Args:
            X_train: 훈련 특성
            y_train: 훈련 타겟
            n_estimators: 부스팅 단계 수
            learning_rate: 학습률

        Returns:
            학습된 모델
        """
        logger.info("그래디언트 부스팅 모델 학습 시작")
        model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            random_state=42
        )
        model.fit(X_train, y_train)
        self.models['gradient_boosting'] = model
        logger.info("그래디언트 부스팅 모델 학습 완료")
        return model

    def evaluate_model(self, model: object, X_test: np.ndarray,
                      y_test: np.ndarray, model_name: str) -> Dict[str, float]:
        """
        모델 평가

        Args:
            model: 평가할 모델
            X_test: 테스트 특성
            y_test: 테스트 타겟
            model_name: 모델명

        Returns:
            Dict: 평가 메트릭
        """
        y_pred = model.predict(X_test)

        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        metrics = {
            'model': model_name,
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2)
        }

        self.evaluation_results[model_name] = metrics

        logger.info(f"모델 평가 ({model_name}): RMSE={rmse:.4f}, R²={r2:.4f}")

        return metrics

    def hyperparameter_tuning(self, X_train: np.ndarray, y_train: np.ndarray,
                             model_type: str = 'random_forest',
                             param_grid: Dict = None) -> object:
        """
        하이퍼파라미터 튜닝

        Args:
            X_train: 훈련 특성
            y_train: 훈련 타겟
            model_type: 모델 타입
            param_grid: 파라미터 그리드

        Returns:
            최적화된 모델
        """
        logger.info(f"하이퍼파라미터 튜닝 시작: {model_type}")

        if model_type == 'random_forest':
            base_model = RandomForestRegressor(random_state=42, n_jobs=-1)
            if param_grid is None:
                param_grid = {
                    'n_estimators': [50, 100, 150],
                    'max_depth': [10, 15, 20],
                    'min_samples_split': [2, 5, 10]
                }

        elif model_type == 'gradient_boosting':
            base_model = GradientBoostingRegressor(random_state=42)
            if param_grid is None:
                param_grid = {
                    'n_estimators': [50, 100, 150],
                    'learning_rate': [0.01, 0.05, 0.1],
                    'max_depth': [3, 5, 7]
                }
        else:
            raise ValueError(f"지원하지 않는 모델 타입: {model_type}")

        grid_search = GridSearchCV(
            base_model, param_grid, cv=5, scoring='r2', n_jobs=-1
        )
        grid_search.fit(X_train, y_train)

        logger.info(f"최적 파라미터: {grid_search.best_params_}")
        logger.info(f"최적 CV 점수: {grid_search.best_score_:.4f}")

        self.models[f'{model_type}_tuned'] = grid_search.best_estimator_

        return grid_search.best_estimator_

    def save_model(self, model: object, model_name: str) -> str:
        """
        모델 저장

        Args:
            model: 저장할 모델
            model_name: 모델명

        Returns:
            str: 저장 경로
        """
        model_path = self.models_dir / f'{model_name}.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        logger.info(f"모델 저장 완료: {model_path}")
        return str(model_path)

    def load_model(self, model_name: str) -> object:
        """
        모델 로드

        Args:
            model_name: 모델명

        Returns:
            로드된 모델
        """
        model_path = self.models_dir / f'{model_name}.pkl'
        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        logger.info(f"모델 로드 완료: {model_path}")
        return model

    def save_evaluation_results(self, filename: str = 'evaluation_results.json') -> str:
        """
        평가 결과 저장

        Args:
            filename: 저장 파일명

        Returns:
            str: 저장 경로
        """
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.evaluation_results, f, ensure_ascii=False, indent=2)

        logger.info(f"평가 결과 저장: {output_path}")
        return str(output_path)


def main():
    """메인 실행 함수"""
    logger.info("AVM 모델 개발 시작")

    # 모델 개발자 초기화
    developer = AVMModelDeveloper(
        models_dir='avm_project/models',
        output_dir='avm_project/output'
    )

    # 예제 코드 (실제 데이터로 대체 필요)
    try:
        # 데이터 로드 및 분할
        # data = pd.read_csv('avm_project/output/processed_data.csv')
        # X_train, X_test, y_train, y_test = developer.prepare_data(data, target_col='price')

        # 모델 학습
        # developer.train_linear_regression(X_train, y_train)
        # developer.train_decision_tree(X_train, y_train)
        # developer.train_random_forest(X_train, y_train)
        # developer.train_gradient_boosting(X_train, y_train)

        # 모델 평가
        # for model_name, model in developer.models.items():
        #     developer.evaluate_model(model, X_test, y_test, model_name)
        #     developer.save_model(model, model_name)

        # 하이퍼파라미터 튜닝
        # best_model = developer.hyperparameter_tuning(X_train, y_train, model_type='random_forest')
        # developer.evaluate_model(best_model, X_test, y_test, 'random_forest_tuned')

        # 결과 저장
        # developer.save_evaluation_results()

        logger.info("AVM 모델 개발 완료")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == '__main__':
    main()
