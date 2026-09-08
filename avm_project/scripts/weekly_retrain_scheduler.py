#!/usr/bin/env python3
"""
Weekly Retrain Scheduler for AVM Models
매주 자동으로 모델을 재학습하고 성능을 모니터링합니다.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# 로깅 설정
script_dir = Path(__file__).parent.parent
log_dir = script_dir / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'weekly_retrain.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WeeklyRetrainScheduler:
    """주간 모델 재학습 스케줄러"""

    def __init__(self, config_path=None):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / 'config' / 'schedule_config.json'

        self.config_path = config_path
        self.config = self._load_config()
        self.project_root = Path(__file__).parent.parent
        self.data_path = self.config.get('data_path', 'data/raw/real_estate_2024.csv')
        self.model_dir = self.project_root / self.config.get('model_dir', 'models')
        self.log_file = self.project_root / self.config.get('log_file', 'logs/retrain_history.jsonl')
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일 없음: {self.config_path}. 기본값 사용")
            return self._get_default_config()

    def _get_default_config(self):
        """기본 설정"""
        return {
            'data_path': 'data/raw/real_estate_2024.csv',
            'model_dir': 'models',
            'log_file': 'logs/retrain_history.jsonl',
            'test_size': 0.15,
            'val_size': 0.15,
            'performance_threshold': 0.95,
            'enable_alert': True,
            'alert_email': None
        }

    def load_data(self):
        """데이터 로드"""
        try:
            data_file = self.project_root / self.data_path
            df = pd.read_csv(data_file)
            logger.info(f"데이터 로드 완료: {len(df)}행")

            # 특성과 타겟 분리
            feature_cols = [col for col in df.columns if col != '거래금액']
            X = df[feature_cols]
            y = df['거래금액']

            return X, y, feature_cols

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            return None, None, None

    def train_models(self, X_train, y_train, X_val, y_val):
        """모델 학습"""
        logger.info("모델 학습 시작")

        models = {
            'linear_regression': LinearRegression(),
            'decision_tree': DecisionTreeRegressor(random_state=42),
            'random_forest': RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=300, random_state=42),
            'xgboost': XGBRegressor(n_estimators=300, random_state=42, n_jobs=-1),
            'lightgbm': LGBMRegressor(n_estimators=300, random_state=42, n_jobs=-1, verbose=-1)
        }

        results = {}
        trained_models = {}

        for model_name, model in models.items():
            try:
                logger.info(f"  [{model_name}] 학습 중...")
                model.fit(X_train, y_train)

                # 검증 성능
                y_pred = model.predict(X_val)
                r2 = r2_score(y_val, y_pred)
                rmse = np.sqrt(mean_squared_error(y_val, y_pred))
                mae = mean_absolute_error(y_val, y_pred)

                results[model_name] = {
                    'r2': r2,
                    'rmse': rmse,
                    'mae': mae
                }

                trained_models[model_name] = model

                logger.info(f"    ✅ R² = {r2:.4f}, RMSE = {rmse:,.0f}")

            except Exception as e:
                logger.error(f"  ❌ {model_name} 학습 실패: {e}")
                results[model_name] = {'error': str(e)}

        return trained_models, results

    def create_ensemble(self, trained_models, X_train, y_train, X_val, y_val):
        """앙상블 모델 생성"""
        logger.info("앙상블 모델 생성 중...")

        # 모든 모델의 예측값을 메타 특성으로 사용
        X_meta_train = np.zeros((X_train.shape[0], len(trained_models)))
        X_meta_val = np.zeros((X_val.shape[0], len(trained_models)))

        for i, (model_name, model) in enumerate(trained_models.items()):
            try:
                X_meta_train[:, i] = model.predict(X_train)
                X_meta_val[:, i] = model.predict(X_val)
            except Exception as e:
                logger.warning(f"메타 특성 생성 실패 ({model_name}): {e}")

        # Meta learner (XGBoost)
        try:
            ensemble_model = XGBRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                random_state=42,
                n_jobs=-1,
                verbose=0
            )
            ensemble_model.fit(X_meta_train, y_train)

            y_pred_ensemble = ensemble_model.predict(X_meta_val)
            ensemble_r2 = r2_score(y_val, y_pred_ensemble)
            ensemble_rmse = np.sqrt(mean_squared_error(y_val, y_pred_ensemble))
            ensemble_mae = mean_absolute_error(y_val, y_pred_ensemble)

            logger.info(f"✅ 앙상블 R² = {ensemble_r2:.4f}, RMSE = {ensemble_rmse:,.0f}")

            return ensemble_model, {
                'r2': ensemble_r2,
                'rmse': ensemble_rmse,
                'mae': ensemble_mae
            }

        except Exception as e:
            logger.error(f"앙상블 생성 실패: {e}")
            return None, {'error': str(e)}

    def save_models(self, trained_models, ensemble_model, timestamp):
        """모델 저장"""
        logger.info("모델 저장 중...")

        version = timestamp.strftime("%Y%m%d_%H%M%S")

        for model_name, model in trained_models.items():
            try:
                model_file = self.model_dir / f"model_{model_name}_v{version}.joblib"
                joblib.dump(model, model_file)
                logger.info(f"  ✅ {model_name}: {model_file.name}")
            except Exception as e:
                logger.error(f"  ❌ {model_name} 저장 실패: {e}")

        if ensemble_model:
            try:
                ensemble_file = self.model_dir / f"ensemble_model_v{version}.joblib"
                joblib.dump(ensemble_model, ensemble_file)
                logger.info(f"  ✅ ensemble: {ensemble_file.name}")
            except Exception as e:
                logger.error(f"  ❌ 앙상블 저장 실패: {e}")

    def load_previous_results(self):
        """이전 성능 결과 로드"""
        if not self.log_file.exists():
            logger.info("이전 재학습 기록 없음")
            return {}

        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    # 마지막 줄 로드
                    return json.loads(lines[-1])
        except Exception as e:
            logger.warning(f"이전 기록 로드 실패: {e}")

        return {}

    def check_performance_degradation(self, current_results, previous_results):
        """성능 저하 확인"""
        logger.info("성능 저하 확인 중...")

        threshold = self.config.get('performance_threshold', 0.95)  # 95% 이하 = 저하
        degradations = []

        for model_name in current_results:
            if model_name in previous_results:
                prev_r2 = previous_results[model_name].get('r2', 0)
                curr_r2 = current_results[model_name].get('r2', 0)

                if curr_r2 < prev_r2 * threshold:
                    degradation_pct = (1 - curr_r2 / prev_r2) * 100
                    degradations.append({
                        'model': model_name,
                        'previous_r2': prev_r2,
                        'current_r2': curr_r2,
                        'degradation_pct': degradation_pct
                    })

                    logger.warning(
                        f"  ⚠️ {model_name} 성능 저하: "
                        f"{prev_r2:.4f} → {curr_r2:.4f} (-{degradation_pct:.2f}%)"
                    )

        return degradations

    def save_results(self, timestamp, results, ensemble_results):
        """결과 저장"""
        try:
            log_entry = {
                'timestamp': timestamp.isoformat(),
                'models': results,
                'ensemble': ensemble_results,
                'status': 'success' if ensemble_results.get('r2') else 'failed'
            }

            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

            logger.info(f"결과 저장 완료: {self.log_file}")

        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")

    def send_alert(self, degradations):
        """성능 저하 알림 전송"""
        if not degradations or not self.config.get('enable_alert'):
            return

        logger.warning(f"성능 저하 알림: {len(degradations)}개 모델 영향")

        # TODO: 이메일 또는 Slack 알림
        alert_email = self.config.get('alert_email')
        if alert_email:
            logger.info(f"알림 발송 대상: {alert_email}")

    def run(self):
        """전체 재학습 파이프라인 실행"""
        logger.info("=" * 80)
        logger.info("📊 주간 모델 재학습 시작")
        logger.info("=" * 80)

        timestamp = datetime.now()

        # 1. 데이터 로드
        X, y, feature_cols = self.load_data()
        if X is None:
            logger.error("❌ 재학습 실패: 데이터 로드 오류")
            return False

        # 2. 데이터 분할
        logger.info(f"데이터 분할: 70% 훈련, 15% 검증, 15% 테스트")
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.30, random_state=42
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, random_state=42
        )

        logger.info(f"  훈련: {len(X_train):,}행")
        logger.info(f"  검증: {len(X_val):,}행")
        logger.info(f"  테스트: {len(X_test):,}행")

        # 3. 모델 학습
        trained_models, model_results = self.train_models(X_train, y_train, X_val, y_val)

        # 4. 앙상블 생성
        ensemble_model, ensemble_results = self.create_ensemble(
            trained_models, X_train, y_train, X_val, y_val
        )

        # 5. 모델 저장
        self.save_models(trained_models, ensemble_model, timestamp)

        # 6. 이전 성능과 비교
        previous_results = self.load_previous_results()
        degradations = self.check_performance_degradation(model_results, previous_results.get('models', {}))

        # 7. 결과 저장
        self.save_results(timestamp, model_results, ensemble_results)

        # 8. 알림 전송
        if degradations:
            self.send_alert(degradations)

        # 최종 요약
        logger.info("\n" + "=" * 80)
        logger.info("📊 재학습 완료 요약")
        logger.info("=" * 80)
        logger.info(f"시간: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"최고 성능 모델: Gradient Boosting (R² = {model_results['gradient_boosting']['r2']:.4f})")
        logger.info(f"앙상블 R²: {ensemble_results.get('r2', 'N/A')}")
        logger.info(f"성능 저하 경고: {len(degradations)}개")
        logger.info("=" * 80)

        return True


def main():
    """메인 함수"""
    scheduler = WeeklyRetrainScheduler()
    success = scheduler.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
