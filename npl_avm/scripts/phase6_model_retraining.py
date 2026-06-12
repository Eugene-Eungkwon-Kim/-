#!/usr/bin/env python3
"""
Phase 6-2: 모델 재훈련 (개선된 특성 사용)
목표: MAPE 19.56% → 17% 달성 (첫 단계)
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Phase6ModelRetraining:
    """Phase 6 모델 재훈련"""

    def __init__(self):
        logger.info("Loading enhanced data...")

        # 개선된 데이터 로드
        data_path = project_root / 'data' / 'preprocessed_data_with_features_normalized.csv'
        if not data_path.exists():
            logger.error("특성 엔지니어링 데이터 없음. Phase 6-1 먼저 실행하세요.")
            raise FileNotFoundError(data_path)

        self.df = pd.read_csv(data_path)

        # 특성과 목표 분리
        self.X = self.df.drop(['id', 'address_sido', 'address_sigungu',
                                'address_dong', 'address_full', 'reference_date',
                                'approval_date', 'property_type', 'hammer_price',
                                'trade_date', 'trade_amount'],
                               axis=1, errors='ignore')
        self.y = self.df['hammer_price']

        logger.info(f"✅ 데이터 로드: {len(self.df)} rows × {len(self.X)} features")
        logger.info(f"   기존 특성: 9개 → 현재 특성: {len(self.X)} 개")

        # Train-test split
        from sklearn.model_selection import train_test_split
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y, test_size=0.2, random_state=42
        )

        logger.info(f"   Train: {len(self.X_train)}, Test: {len(self.X_test)}")
        self.results = []

    def train_xgboost_v2(self):
        """XGBoost v2 (개선된 특성 사용)"""
        import xgboost as xgb
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        logger.info("\n" + "="*60)
        logger.info("🤖 XGBoost v2 (개선된 특성)")
        logger.info("="*60)

        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.7,
            colsample_bytree=0.8,
            reg_lambda=1.0,
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
        logger.info(f"   Test R²:       {r2_test:.4f}")
        logger.info(f"   RMSE:          ₩{rmse_test:,.0f}")
        logger.info(f"   MAE:           ₩{mae_test:,.0f}")
        logger.info(f"   MAPE:          {mape_test:.2f}%")

        # 개선도 계산
        improvement = 19.56 - mape_test
        logger.info(f"\n📈 개선도:")
        logger.info(f"   이전 MAPE: 19.56%")
        logger.info(f"   현재 MAPE: {mape_test:.2f}%")
        logger.info(f"   개선: {improvement:.2f}% ({'✅ 목표 달성!' if mape_test < 17 else '⚠️ 계속 개선 필요'})")

        # 특성 중요도
        logger.info(f"\n🔍 상위 10개 중요 특성:")
        feature_importance = pd.DataFrame({
            'feature': self.X_train.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        for idx, row in feature_importance.head(10).iterrows():
            logger.info(f"   {row['feature']}: {row['importance']:.4f}")

        result = {
            'model': model,
            'model_name': 'XGBoost v2 (개선된 특성)',
            'r2_train': r2_train,
            'r2_test': r2_test,
            'rmse': rmse_test,
            'mae': mae_test,
            'mape': mape_test,
            'improvement': improvement,
            'y_pred_test': y_pred_test,
            'feature_importance': feature_importance,
        }

        self.results.append(result)
        return result

    def train_lightgbm_v1(self):
        """LightGBM v1 (앙상블용)"""
        try:
            import lightgbm as lgb
            from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

            logger.info("\n" + "="*60)
            logger.info("🤖 LightGBM v1 (앙상블용)")
            logger.info("="*60)

            model = lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=7,
                learning_rate=0.1,
                num_leaves=31,
                random_state=42,
                n_jobs=-1,
                verbose=-1
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
            logger.info(f"   Test R²:       {r2_test:.4f}")
            logger.info(f"   RMSE:          ₩{rmse_test:,.0f}")
            logger.info(f"   MAE:           ₩{mae_test:,.0f}")
            logger.info(f"   MAPE:          {mape_test:.2f}%")

            improvement = 19.56 - mape_test

            result = {
                'model': model,
                'model_name': 'LightGBM v1',
                'r2_train': r2_train,
                'r2_test': r2_test,
                'rmse': rmse_test,
                'mae': mae_test,
                'mape': mape_test,
                'improvement': improvement,
                'y_pred_test': y_pred_test,
            }

            self.results.append(result)
            return result

        except ImportError:
            logger.warning("⚠️ LightGBM not installed, skipping...")
            return None

    def create_ensemble(self):
        """앙상블 모델 생성"""
        if len(self.results) < 2:
            logger.warning("⚠️ 최소 2개 모델 필요, 앙상블 스킵")
            return None

        logger.info("\n" + "="*60)
        logger.info("🤖 Ensemble (XGB 60% + LGB 40%)")
        logger.info("="*60)

        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        xgb_pred = self.results[0]['y_pred_test']
        lgb_pred = self.results[1]['y_pred_test'] if len(self.results) > 1 else None

        if lgb_pred is not None:
            y_pred_ensemble = 0.6 * xgb_pred + 0.4 * lgb_pred
        else:
            y_pred_ensemble = xgb_pred

        r2_ensemble = r2_score(self.y_test, y_pred_ensemble)
        rmse_ensemble = np.sqrt(mean_squared_error(self.y_test, y_pred_ensemble))
        mae_ensemble = mean_absolute_error(self.y_test, y_pred_ensemble)
        mape_ensemble = np.mean(np.abs((self.y_test - y_pred_ensemble) / self.y_test)) * 100

        logger.info(f"\n📊 앙상블 결과:")
        logger.info(f"   R²:            {r2_ensemble:.4f}")
        logger.info(f"   RMSE:          ₩{rmse_ensemble:,.0f}")
        logger.info(f"   MAE:           ₩{mae_ensemble:,.0f}")
        logger.info(f"   MAPE:          {mape_ensemble:.2f}%")

        improvement = 19.56 - mape_ensemble
        logger.info(f"\n📈 개선도: {improvement:.2f}%")

        return {
            'model_name': 'Ensemble (XGB 60% + LGB 40%)',
            'r2': r2_ensemble,
            'rmse': rmse_ensemble,
            'mape': mape_ensemble,
            'improvement': improvement,
        }

    def compare_models(self):
        """모델 비교"""
        logger.info("\n" + "="*60)
        logger.info("📈 모델 비교")
        logger.info("="*60 + "\n")

        comparison_data = []
        for r in self.results:
            comparison_data.append({
                'Model': r['model_name'],
                'Train R²': f"{r['r2_train']:.4f}",
                'Test R²': f"{r['r2_test']:.4f}",
                'RMSE': f"₩{r['rmse']:,.0f}",
                'MAPE': f"{r['mape']:.2f}%",
                'Improvement': f"{r['improvement']:.2f}%",
            })

        comparison_df = pd.DataFrame(comparison_data)
        logger.info(comparison_df.to_string(index=False))

        return comparison_df

    def save_models(self):
        """모델 저장"""
        logger.info("\n💾 모델 저장...")

        models_dir = project_root / 'models'
        models_dir.mkdir(exist_ok=True)

        # XGBoost v2 저장
        best = self.results[0]
        model_path = models_dir / 'advanced_v2.pkl'
        joblib.dump(best['model'], model_path)
        logger.info(f"   ✅ {model_path}")

        # 메타데이터 저장
        import json
        metadata = {
            'model_name': best['model_name'],
            'r2_test': float(best['r2_test']),
            'rmse': float(best['rmse']),
            'mape': float(best['mape']),
            'improvement': float(best['improvement']),
            'total_features': len(self.X_train.columns),
            'created_at': datetime.now().isoformat(),
            'version': 'v2_with_enhanced_features',
        }

        metadata_path = models_dir / 'advanced_v2_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"   ✅ {metadata_path}")

        # 특성 중요도 저장
        importance_path = models_dir / 'feature_importance_v2.csv'
        best['feature_importance'].to_csv(importance_path, index=False)
        logger.info(f"   ✅ {importance_path}")

    def generate_report(self):
        """리포트 생성"""
        report_path = project_root / 'results' / 'phase6_model_retraining_report.txt'
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("Phase 6-2: 모델 재훈련 보고서\n")
            f.write("="*60 + "\n\n")

            f.write(f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"데이터: {len(self.df)} rows × {len(self.X)} features\n")
            f.write(f"훈련셋: {len(self.X_train)}, 테스트셋: {len(self.X_test)}\n\n")

            f.write("모델 비교\n")
            f.write("-"*60 + "\n")
            for r in self.results:
                f.write(f"\n{r['model_name']}\n")
                f.write(f"  Train R²:    {r['r2_train']:.4f}\n")
                f.write(f"  Test R²:     {r['r2_test']:.4f}\n")
                f.write(f"  RMSE:        ₩{r['rmse']:,.0f}\n")
                f.write(f"  MAE:         ₩{r['mae']:,.0f}\n")
                f.write(f"  MAPE:        {r['mape']:.2f}%\n")
                f.write(f"  Improvement: {r['improvement']:.2f}%\n")

            f.write("\n" + "="*60 + "\n")
            f.write("최종 결과\n")
            f.write("="*60 + "\n")
            f.write(f"기존 MAPE:  19.56%\n")
            f.write(f"개선 MAPE:  {self.results[0]['mape']:.2f}%\n")
            f.write(f"개선도:     {self.results[0]['improvement']:.2f}%\n")

            if self.results[0]['mape'] < 17:
                f.write(f"\n✅ 목표 달성! (MAPE < 17%)\n")
            else:
                f.write(f"\n⚠️ 계속 개선 필요 (목표: < 17%, 현재: {self.results[0]['mape']:.2f}%)\n")

        logger.info(f"   ✅ {report_path}")

    def run(self):
        """메인 실행"""
        try:
            logger.info("\n" + "="*60)
            logger.info("🚀 Phase 6-2: 모델 재훈련 시작")
            logger.info("="*60 + "\n")

            # 모델 훈련
            self.train_xgboost_v2()
            self.train_lightgbm_v1()

            # 비교
            self.compare_models()

            # 저장 및 리포트
            self.save_models()
            self.generate_report()

            logger.info("\n" + "="*60)
            logger.info("✅ Phase 6-2 모델 재훈련 완료!")
            logger.info("="*60)

            logger.info("\n📊 성과:")
            logger.info(f"   이전 MAPE: 19.56%")
            logger.info(f"   현재 MAPE: {self.results[0]['mape']:.2f}%")
            logger.info(f"   개선도:    {self.results[0]['improvement']:.2f}%")

            if self.results[0]['mape'] < 17:
                logger.info(f"\n✅ 1단계 목표 달성!")
            else:
                logger.info(f"\n⚠️ 2단계 계속 진행 필요")

        except Exception as e:
            logger.error(f"❌ 에러: {e}")
            raise


def main():
    retrainer = Phase6ModelRetraining()
    retrainer.run()


if __name__ == "__main__":
    main()
