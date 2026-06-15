"""
Model performance evaluation and comparison
모델 성능 평가 및 비교 분석
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error, r2_score

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """모델 성능 평가"""

    def __init__(self, output_dir: str = 'output'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.evaluation_results = {}

    def evaluate_model(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str,
        cv_scores: np.ndarray = None
    ) -> Dict:
        """
        단일 모델 평가

        Args:
            y_true: 실제값
            y_pred: 예측값
            model_name: 모델명
            cv_scores: 교차검증 점수

        Returns:
            평가 결과 딕셔너리
        """

        # 기본 지표 계산
        r2 = r2_score(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        mape = mean_absolute_percentage_error(y_true, y_pred)

        # 교차검증 점수
        cv_mean = float(cv_scores.mean()) if cv_scores is not None else None
        cv_std = float(cv_scores.std()) if cv_scores is not None else None

        result = {
            'model_name': model_name,
            'r2_score': float(r2),
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape),
            'cv_mean': cv_mean,
            'cv_std': cv_std,
            'predictions_count': len(y_pred),
            'timestamp': datetime.now().isoformat()
        }

        self.evaluation_results[model_name] = result
        logger.info(f"✅ {model_name} 평가 완료: R²={r2:.4f}, RMSE={rmse:.2f}")

        return result

    def generate_evaluation_report(self) -> Dict:
        """평가 리포트 생성"""

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_models': len(self.evaluation_results),
            'models': self.evaluation_results,
            'summary': self._generate_summary()
        }

        # 파일 저장
        report_file = self.output_dir / f'evaluation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 평가 리포트 저장: {report_file}")

        return report

    def _generate_summary(self) -> Dict:
        """평가 요약 생성"""

        if not self.evaluation_results:
            return {}

        r2_scores = [m['r2_score'] for m in self.evaluation_results.values()]
        rmse_scores = [m['rmse'] for m in self.evaluation_results.values()]

        summary = {
            'best_r2_model': max(
                self.evaluation_results.items(),
                key=lambda x: x[1]['r2_score']
            )[0],
            'best_r2_score': max(r2_scores),
            'avg_r2_score': float(np.mean(r2_scores)),
            'best_rmse_model': min(
                self.evaluation_results.items(),
                key=lambda x: x[1]['rmse']
            )[0],
            'best_rmse': min(rmse_scores),
            'avg_rmse': float(np.mean(rmse_scores))
        }

        return summary

    def compare_models(self) -> pd.DataFrame:
        """모델 비교 테이블 생성"""

        df = pd.DataFrame(self.evaluation_results).T
        df = df.sort_values('r2_score', ascending=False)

        # CSV 저장
        csv_file = self.output_dir / f'model_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(csv_file)

        logger.info(f"✅ 모델 비교표 저장: {csv_file}")

        return df

    def plot_comparison(self):
        """모델 비교 시각화"""

        try:
            import matplotlib.pyplot as plt

            df = pd.DataFrame(self.evaluation_results).T
            df = df.sort_values('r2_score', ascending=False)

            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle('Model Performance Comparison')

            # R² 점수
            axes[0, 0].barh(df.index, df['r2_score'])
            axes[0, 0].set_xlabel('R² Score')
            axes[0, 0].set_title('R² Score Comparison')

            # RMSE
            axes[0, 1].barh(df.index, df['rmse'], color='orange')
            axes[0, 1].set_xlabel('RMSE')
            axes[0, 1].set_title('RMSE Comparison')

            # MAE
            axes[1, 0].barh(df.index, df['mae'], color='green')
            axes[1, 0].set_xlabel('MAE')
            axes[1, 0].set_title('MAE Comparison')

            # MAPE
            axes[1, 1].barh(df.index, df['mape'], color='red')
            axes[1, 1].set_xlabel('MAPE')
            axes[1, 1].set_title('MAPE Comparison')

            plt.tight_layout()

            # 저장
            plot_file = self.output_dir / f'model_comparison_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            plt.savefig(plot_file, dpi=100, bbox_inches='tight')

            logger.info(f"✅ 비교 차트 저장: {plot_file}")

            plt.close()

        except ImportError:
            logger.warning("⚠️ matplotlib 설치 필요: pip install matplotlib")


if __name__ == "__main__":
    # 테스트
    evaluator = ModelEvaluator()

    # 샘플 데이터
    y_true = np.array([100000, 200000, 300000, 400000, 500000])
    y_pred = np.array([105000, 195000, 310000, 390000, 510000])
    cv_scores = np.array([0.92, 0.90, 0.91])

    evaluator.evaluate_model(y_true, y_pred, "RandomForest", cv_scores)

    y_true2 = np.array([100000, 200000, 300000, 400000, 500000])
    y_pred2 = np.array([102000, 198000, 302000, 398000, 502000])
    cv_scores2 = np.array([0.94, 0.93, 0.92])

    evaluator.evaluate_model(y_true2, y_pred2, "LightGBM", cv_scores2)

    # 리포트 생성
    report = evaluator.generate_evaluation_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # 비교
    df = evaluator.compare_models()
    print(df)

    # 시각화
    evaluator.plot_comparison()
