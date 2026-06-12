#!/usr/bin/env python3
"""
Phase 2: 고급 모델 훈련 (XGBoost)
목표: R² > 0.85 달성
산출물: 최적화된 XGBoost 모델
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Phase2AdvancedModels:
    """Phase 2 고급 모델 훈련."""

    def __init__(self):
        """초기화."""
        logger.info("Loading preprocessed data...")

        # 전처리된 데이터 로드
        data_path = project_root / 'data' / 'preprocessed_data_normalized.csv'
        self.df = pd.read_csv(data_path)

        # 특성(X)과 목표(y) 분리
        self.X = self.df.drop(['id', 'address_sido', 'address_sigungu',
                                'address_dong', 'address_full', 'reference_date',
                                'approval_date', 'property_type', 'hammer_price'],
                               axis=1, errors='ignore')
        self.y = self.df['hammer_price']

        logger.info(f"✅ 데이터 로드: {len(self.df)} rows × {len(self.X)} features")

        # Train-test split
        from sklearn.model_selection import train_test_split
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y, test_size=0.2, random_state=42
        )

        logger.info(f"   Train: {len(self.X_train)}, Test: {len(self.X_test)}\n")

        self.results = []

    def train_xgboost_baseline(self):
        """XGBoost 기본 모델 (최소 하이퍼파라미터)."""
        import xgboost as xgb
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        logger.info("=" * 60)
        logger.info("🤖 XGBoost (Baseline)")
        logger.info("=" * 60)

        model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )

        logger.info("[1/3] 훈련 중...")
        model.fit(self.X_train, self.y_train)

        logger.info("[2/3] 예측 중...")
        y_pred_train = model.predict(self.X_train)
        y_pred_test = model.predict(self.X_test)

        logger.info("[3/3] 평가 중...")
        r2_train = r2_score(self.y_train, y_pred_train)
        r2_test = r2_score(self.y_test, y_pred_test)
        rmse_test = np.sqrt(mean_squared_error(self.y_test, y_pred_test))
        mae_test = mean_absolute_error(self.y_test, y_pred_test)
        mape_test = np.mean(np.abs((self.y_test - y_pred_test) / self.y_test)) * 100

        logger.info(f"\n📊 결과:")
        logger.info(f"   Train R²:      {r2_train:.4f}")
        logger.info(f"   Test R²:       {r2_test:.4f} {'✅' if r2_test >= 0.85 else '⚠️'}")
        logger.info(f"   RMSE:          ₩{rmse_test:,.0f}")
        logger.info(f"   MAE:           ₩{mae_test:,.0f}")
        logger.info(f"   MAPE:          {mape_test:.2f}%")

        result = {
            'model': model,
            'model_name': 'XGBoost (Baseline)',
            'r2_train': r2_train,
            'r2_test': r2_test,
            'rmse': rmse_test,
            'mae': mae_test,
            'mape': mape_test,
            'y_pred_test': y_pred_test,
        }

        self.results.append(result)
        return result

    def train_xgboost_tuned(self):
        """XGBoost 튜닝 모델 (최적화된 하이퍼파라미터)."""
        import xgboost as xgb
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        from sklearn.model_selection import cross_val_score

        logger.info("\n" + "=" * 60)
        logger.info("🤖 XGBoost (Tuned - GridSearch)")
        logger.info("=" * 60)

        logger.info("[1/4] 그리드 서치 수행 중...")

        # 그리드 서치
        from sklearn.model_selection import GridSearchCV

        param_grid = {
            'max_depth': [5, 6, 7],
            'learning_rate': [0.05, 0.1],
            'subsample': [0.7, 0.8, 0.9],
            'colsample_bytree': [0.7, 0.8],
            'reg_lambda': [0.5, 1.0, 2.0],
        }

        base_model = xgb.XGBRegressor(
            n_estimators=100,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )

        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=3,
            scoring='r2',
            n_jobs=-1,
            verbose=0
        )

        grid_search.fit(self.X_train, self.y_train)

        logger.info(f"✅ 그리드 서치 완료")
        logger.info(f"   최고 CV 점수: {grid_search.best_score_:.4f}")
        logger.info(f"   최적 파라미터:")
        for key, value in grid_search.best_params_.items():
            logger.info(f"     - {key}: {value}")

        model = grid_search.best_estimator_

        logger.info("\n[2/3] 최적 모델로 예측 중...")
        y_pred_train = model.predict(self.X_train)
        y_pred_test = model.predict(self.X_test)

        logger.info("[3/3] 평가 중...")
        r2_train = r2_score(self.y_train, y_pred_train)
        r2_test = r2_score(self.y_test, y_pred_test)
        rmse_test = np.sqrt(mean_squared_error(self.y_test, y_pred_test))
        mae_test = mean_absolute_error(self.y_test, y_pred_test)
        mape_test = np.mean(np.abs((self.y_test - y_pred_test) / self.y_test)) * 100

        logger.info(f"\n📊 결과:")
        logger.info(f"   Train R²:      {r2_train:.4f}")
        logger.info(f"   Test R²:       {r2_test:.4f} {'✅' if r2_test >= 0.85 else '⚠️'}")
        logger.info(f"   RMSE:          ₩{rmse_test:,.0f}")
        logger.info(f"   MAE:           ₩{mae_test:,.0f}")
        logger.info(f"   MAPE:          {mape_test:.2f}%")

        result = {
            'model': model,
            'model_name': 'XGBoost (Tuned)',
            'r2_train': r2_train,
            'r2_test': r2_test,
            'rmse': rmse_test,
            'mae': mae_test,
            'mape': mape_test,
            'y_pred_test': y_pred_test,
            'best_params': grid_search.best_params_,
        }

        self.results.append(result)
        return result

    def compare_results(self):
        """모델 비교."""
        logger.info(f"\n{'='*60}")
        logger.info(f"📈 XGBoost 모델 비교")
        logger.info(f"{'='*60}\n")

        # DataFrame으로 정렬
        comparison_df = pd.DataFrame([
            {
                'Model': r['model_name'],
                'Train R²': f"{r['r2_train']:.4f}",
                'Test R²': f"{r['r2_test']:.4f}",
                'RMSE': f"₩{r['rmse']:,.0f}",
                'MAE': f"₩{r['mae']:,.0f}",
                'MAPE': f"{r['mape']:.2f}%",
            }
            for r in self.results
        ])

        logger.info(comparison_df.to_string(index=False))

        # 최고 성능 모델
        best = max(self.results, key=lambda x: x['r2_test'])
        logger.info(f"\n{'='*60}")
        logger.info(f"🏆 최고 성능 모델: {best['model_name']}")
        logger.info(f"   Test R²: {best['r2_test']:.4f}")
        if best['r2_test'] >= 0.85:
            logger.info(f"   ✅ 목표 달성!")
        else:
            logger.info(f"   ⚠️  목표 미달 (목표: 0.85)")
        logger.info(f"{'='*60}\n")

        return best

    def save_best_model(self, best):
        """최고 성능 모델 저장."""
        models_dir = project_root / 'models'
        models_dir.mkdir(exist_ok=True)

        model_path = models_dir / 'advanced_best.pkl'
        joblib.dump(best['model'], model_path)
        logger.info(f"💾 모델 저장: {model_path}")

        # 메타데이터 저장
        metadata = {
            'model_name': best['model_name'],
            'r2_test': float(best['r2_test']),
            'rmse': float(best['rmse']),
            'mape': float(best['mape']),
            'created_at': datetime.now().isoformat(),
        }

        if 'best_params' in best:
            metadata['best_params'] = best['best_params']

        import json
        metadata_path = models_dir / 'advanced_best_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"📋 메타데이터 저장: {metadata_path}")

        return best

    def generate_report(self, best):
        """리포트 생성."""
        report_path = project_root / 'results' / 'advanced_model_report.txt'
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("Phase 2 고급 모델 훈련 보고서\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"데이터: {len(self.df)} rows × {len(self.X)} features\n")
            f.write(f"훈련셋: {len(self.X_train)}, 테스트셋: {len(self.X_test)}\n\n")

            f.write("모델 비교\n")
            f.write("-" * 60 + "\n")
            for r in self.results:
                f.write(f"\n{r['model_name']}\n")
                f.write(f"  Train R²:    {r['r2_train']:.4f}\n")
                f.write(f"  Test R²:     {r['r2_test']:.4f}\n")
                f.write(f"  RMSE:        ₩{r['rmse']:,.0f}\n")
                f.write(f"  MAE:         ₩{r['mae']:,.0f}\n")
                f.write(f"  MAPE:        {r['mape']:.2f}%\n")
                if 'best_params' in r:
                    f.write(f"  Best Params: {r['best_params']}\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write(f"최고 성능 모델: {best['model_name']}\n")
            f.write(f"Test R²: {best['r2_test']:.4f}\n")
            if best['r2_test'] >= 0.85:
                f.write("상태: ✅ 목표 달성!\n")
            else:
                f.write(f"상태: ⚠️  목표 미달 (차이: {0.85 - best['r2_test']:.4f})\n")
            f.write("=" * 60 + "\n")

        logger.info(f"📄 리포트 저장: {report_path}")

    def run(self):
        """메인 실행."""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("🚀 Phase 2 고급 모델 훈련 시작 (XGBoost)")
            logger.info("=" * 60 + "\n")

            # 모델 훈련
            self.train_xgboost_baseline()
            self.train_xgboost_tuned()

            # 비교 및 최고 모델 선택
            best = self.compare_results()

            # 저장
            self.save_best_model(best)

            # 리포트
            self.generate_report(best)

            # 최종 결과
            logger.info("\n" + "=" * 60)
            logger.info("✅ Phase 2 고급 모델 훈련 완료!")
            logger.info("=" * 60)

            if best['r2_test'] >= 0.85:
                logger.info("\n🎉 목표 달성! R² > 0.85 성공!")
                logger.info("   → Phase 3 (테스트 & QA) 진행 준비")
            else:
                logger.info(f"\n⚠️  목표 미달 (R² {best['r2_test']:.4f})")
                logger.info("   → 추가 튜닝 또는 LightGBM 고려")

            return best

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise


def main():
    """메인 함수."""
    trainer = Phase2AdvancedModels()
    trainer.run()


if __name__ == "__main__":
    main()
