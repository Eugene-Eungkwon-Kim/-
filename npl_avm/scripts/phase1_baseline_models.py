#!/usr/bin/env python3
"""
Phase 1: 베이스라인 모델 훈련
목표: Linear Regression, Decision Tree, Random Forest 비교
산출물: 최고 성능 모델 저장
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Phase1BaselineModels:
    """Phase 1 베이스라인 모델 훈련."""

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
        logger.info(f"   특성: {self.X.columns.tolist()}")

        # Train-test split
        from sklearn.model_selection import train_test_split
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y, test_size=0.2, random_state=42
        )

        logger.info(f"   Train: {len(self.X_train)}, Test: {len(self.X_test)}")

        self.results = []

    def evaluate_model(self, model, model_name):
        """모델 평가."""
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        logger.info(f"\n{'='*60}")
        logger.info(f"🤖 {model_name}")
        logger.info(f"{'='*60}")

        try:
            # 훈련
            logger.info(f"[1/3] 훈련 중...")
            model.fit(self.X_train, self.y_train)

            # 예측
            logger.info(f"[2/3] 예측 중...")
            y_pred_train = model.predict(self.X_train)
            y_pred_test = model.predict(self.X_test)

            # 평가
            logger.info(f"[3/3] 평가 중...")
            r2_train = r2_score(self.y_train, y_pred_train)
            r2_test = r2_score(self.y_test, y_pred_test)
            rmse_test = np.sqrt(mean_squared_error(self.y_test, y_pred_test))
            mae_test = mean_absolute_error(self.y_test, y_pred_test)
            mape_test = np.mean(np.abs((self.y_test - y_pred_test) / self.y_test)) * 100

            # Cross-validation
            from sklearn.model_selection import cross_val_score
            cv_scores = cross_val_score(model, self.X_train, self.y_train,
                                        cv=5, scoring='r2')

            # 결과 출력
            logger.info(f"\n📊 결과:")
            logger.info(f"   Train R²:      {r2_train:.4f}")
            logger.info(f"   Test R²:       {r2_test:.4f} {'✅' if r2_test >= 0.75 else '⚠️'}")
            logger.info(f"   RMSE:          ₩{rmse_test:,.0f}")
            logger.info(f"   MAE:           ₩{mae_test:,.0f}")
            logger.info(f"   MAPE:          {mape_test:.2f}%")
            logger.info(f"   CV Score:      {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")

            # 과적합 여부 확인
            overfitting = r2_train - r2_test
            if overfitting > 0.1:
                logger.warning(f"   ⚠️  과적합 감지: {overfitting:.4f}")
            else:
                logger.info(f"   ✅ 과적합 없음: {overfitting:.4f}")

            result = {
                'model': model,
                'model_name': model_name,
                'r2_train': r2_train,
                'r2_test': r2_test,
                'rmse': rmse_test,
                'mae': mae_test,
                'mape': mape_test,
                'cv_score': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'overfitting': overfitting,
                'y_pred_test': y_pred_test,
            }

            self.results.append(result)
            return result

        except Exception as e:
            logger.error(f"Error training {model_name}: {e}")
            raise

    def train_linear_regression(self):
        """Linear Regression 훈련."""
        from sklearn.linear_model import LinearRegression

        model = LinearRegression()
        return self.evaluate_model(model, "Linear Regression")

    def train_decision_tree(self):
        """Decision Tree 훈련."""
        from sklearn.tree import DecisionTreeRegressor

        model = DecisionTreeRegressor(max_depth=10, random_state=42, min_samples_leaf=5)
        return self.evaluate_model(model, "Decision Tree (max_depth=10)")

    def train_random_forest(self):
        """Random Forest 훈련."""
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        return self.evaluate_model(model, "Random Forest (100 trees)")

    def compare_results(self):
        """모든 모델 비교."""
        logger.info(f"\n{'='*60}")
        logger.info(f"📈 모델 비교 결과")
        logger.info(f"{'='*60}\n")

        # DataFrame으로 정렬
        comparison_df = pd.DataFrame([
            {
                'Model': r['model_name'],
                'Train R²': f"{r['r2_train']:.4f}",
                'Test R²': f"{r['r2_test']:.4f}",
                'RMSE': f"₩{r['rmse']:,.0f}",
                'MAPE': f"{r['mape']:.2f}%",
                'CV Score': f"{r['cv_score']:.4f}±{r['cv_std']:.4f}",
                'Overfitting': f"{r['overfitting']:.4f}",
            }
            for r in self.results
        ])

        logger.info(comparison_df.to_string(index=False))

        # 최고 성능 모델
        best = max(self.results, key=lambda x: x['r2_test'])
        logger.info(f"\n{'='*60}")
        logger.info(f"🏆 최고 성능 모델: {best['model_name']}")
        logger.info(f"   Test R²: {best['r2_test']:.4f}")
        logger.info(f"{'='*60}\n")

        return best

    def save_best_model(self, best):
        """최고 성능 모델 저장."""
        models_dir = project_root / 'models'
        models_dir.mkdir(exist_ok=True)

        model_path = models_dir / 'baseline_best.pkl'
        joblib.dump(best['model'], model_path)
        logger.info(f"💾 모델 저장: {model_path}")

        # 메타데이터 저장
        metadata = {
            'model_name': best['model_name'],
            'r2_test': float(best['r2_test']),
            'rmse': float(best['rmse']),
            'mape': float(best['mape']),
            'cv_score': float(best['cv_score']),
            'created_at': datetime.now().isoformat(),
        }

        import json
        metadata_path = models_dir / 'baseline_best_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"📋 메타데이터 저장: {metadata_path}")

        return best

    def generate_report(self, best):
        """리포트 생성."""
        report_path = project_root / 'results' / 'baseline_model_report.txt'
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("Phase 1 베이스라인 모델 훈련 보고서\n")
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
                f.write(f"  CV Score:    {r['cv_score']:.4f}±{r['cv_std']:.4f}\n")
                f.write(f"  Overfitting: {r['overfitting']:.4f}\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write(f"최고 성능 모델: {best['model_name']}\n")
            f.write(f"Test R²: {best['r2_test']:.4f}\n")
            f.write("=" * 60 + "\n")

        logger.info(f"📄 리포트 저장: {report_path}")

    def run(self):
        """메인 실행."""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("🚀 Phase 1 베이스라인 모델 훈련 시작")
            logger.info("=" * 60)

            # 모델 훈련
            self.train_linear_regression()
            self.train_decision_tree()
            self.train_random_forest()

            # 비교 및 최고 모델 선택
            best = self.compare_results()

            # 저장
            self.save_best_model(best)

            # 리포트
            self.generate_report(best)

            logger.info("\n" + "=" * 60)
            logger.info("✅ 베이스라인 모델 훈련 완료!")
            logger.info("=" * 60)
            logger.info("\n📊 다음 단계:")
            logger.info("   → XGBoost 고급 모델 훈련 (선택)")
            logger.info("   → 또는 운영 배포 (현재 모델 사용)")

            return best

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise


def main():
    """메인 함수."""
    trainer = Phase1BaselineModels()
    trainer.run()


if __name__ == "__main__":
    main()
