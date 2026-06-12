"""
AVM 프로젝트 자동 오케스트레이션 시스템
Automated AVM Data Collection & Model Retraining Orchestrator
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import traceback
import pandas as pd

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data_collection_handler import KoreanRealEstateDataCollector
from scripts.data_preprocessing import DataPreprocessor
from scripts.model_development import AVMModelDeveloper

# 로깅 설정
log_dir = PROJECT_ROOT / 'logs'
log_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = log_dir / f'avm_orchestration_{timestamp}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AVMOrchestrator:
    """AVM 자동화 오케스트레이션 클래스"""

    def __init__(self, config_path=None):
        self.project_root = PROJECT_ROOT
        self.config_path = config_path or (PROJECT_ROOT / 'config' / 'avm_config.json')
        self.data_dir = PROJECT_ROOT / 'data'
        self.raw_data_dir = self.data_dir / 'raw'
        self.processed_data_dir = self.data_dir / 'processed'
        self.models_dir = PROJECT_ROOT / 'models'
        self.results_dir = PROJECT_ROOT / 'output'

        # 디렉토리 생성
        for d in [self.raw_data_dir, self.processed_data_dir, self.models_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # 설정 로드
        self.config = self._load_config()
        self.api_key = self.config.get('api_key') or os.getenv('DATAGOVKR_API_KEY')

        logger.info(f"AVM Orchestrator initialized - {timestamp}")
        logger.info(f"Project Root: {self.project_root}")
        logger.info(f"Data Directory: {self.data_dir}")

    def _load_config(self):
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Config file not found. Using defaults: {e}")
            return {}

    def collect_data(self, start_date=None, end_date=None):
        """데이터 수집 단계"""
        logger.info("=" * 70)
        logger.info("STEP 1: 데이터 수집 (Data Collection)")
        logger.info("=" * 70)

        try:
            collector = KoreanRealEstateDataCollector(
                api_key=self.api_key,
                output_dir=str(self.raw_data_dir)
            )

            # 기본값: 지난 1개월
            if not start_date or not end_date:
                from datetime import timedelta
                end = datetime.now()
                start = end - timedelta(days=30)
                start_date = start.strftime('%Y%m')
                end_date = end.strftime('%Y%m')

            logger.info(f"Collecting data for period: {start_date} ~ {end_date}")

            df = collector.collect_real_estate_transaction_data(
                start_date=start_date,
                end_date=end_date
            )

            if len(df) > 0:
                logger.info(f"✅ 데이터 수집 완료: {len(df)}개 레코드")
                logger.info(f"   컬럼: {len(df.columns)}개")
                return df
            else:
                logger.warning("⚠️ 수집된 데이터 없음")
                return None

        except Exception as e:
            logger.error(f"❌ 데이터 수집 실패: {e}")
            logger.error(traceback.format_exc())
            return None

    def preprocess_data(self, input_file=None):
        """데이터 전처리 단계"""
        logger.info("=" * 70)
        logger.info("STEP 2: 데이터 전처리 (Preprocessing)")
        logger.info("=" * 70)

        try:
            preprocessor = DataPreprocessor(
                data_dir=str(self.raw_data_dir),
                output_dir=str(self.results_dir)
            )

            # 데이터 로드 - 파일 전체 경로로 직접 로드
            if input_file:
                logger.info(f"Loading data from: {input_file}")
                df = pd.read_csv(input_file)
                preprocessor.raw_data = df
            else:
                # 가장 최근의 CSV 찾기
                csv_files = list(self.raw_data_dir.glob('*.csv'))
                if csv_files:
                    input_file_path = sorted(csv_files)[-1]
                    logger.info(f"Using latest data file: {input_file_path.name}")
                    df = pd.read_csv(input_file_path)
                    preprocessor.raw_data = df
                else:
                    logger.error("❌ 데이터 파일을 찾을 수 없음")
                    return None

            # 데이터 탐색
            logger.info("Exploring data statistics...")
            preprocessor.explore_data()

            # 결측값 처리
            logger.info("Handling missing values...")
            preprocessor.handle_missing_values()

            # 이상값 탐지
            logger.info("Detecting outliers...")
            outlier_info = preprocessor.detect_outliers()
            total_outliers = sum(info['count'] for info in outlier_info.values())
            total_percentage = (total_outliers / len(preprocessor.processed_data)) * 100
            logger.info(f"   Outliers detected: {total_outliers} ({total_percentage:.1f}%)")

            # 정규화
            logger.info("Normalizing data...")
            preprocessor.normalize_data()

            # 피처 엔지니어링
            logger.info("Engineering features...")
            preprocessor.feature_engineering()

            df = preprocessor.processed_data
            logger.info(f"✅ 전처리 완료: {len(df)}개 × {len(df.columns)}개 컬럼")

            # 전처리된 데이터 저장
            output_file = f'processed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            preprocessor.save_processed_data(output_file)
            logger.info(f"   저장 위치: {output_file}")

            return df

        except Exception as e:
            logger.error(f"❌ 데이터 전처리 실패: {e}")
            logger.error(traceback.format_exc())
            return None

    def train_models(self, df):
        """모델 학습 단계"""
        logger.info("=" * 70)
        logger.info("STEP 3: 모델 학습 (Model Training)")
        logger.info("=" * 70)

        try:
            developer = AVMModelDeveloper(
                models_dir=str(self.models_dir),
                output_dir=str(self.results_dir)
            )

            # 데이터 준비 - final_sale_price가 타겟 컬럼 (없으면 마지막 컬럼 사용)
            logger.info("Preparing data for training...")
            target_col = 'final_sale_price' if 'final_sale_price' in df.columns else df.columns[-1]

            # 숫자형 컬럼만 선택 (범주형 변수 제거)
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if target_col not in numeric_cols:
                numeric_cols.append(target_col)

            df_numeric = df[numeric_cols].copy()
            logger.info(f"Using {len(numeric_cols)} numeric columns for modeling")

            X_train, X_test, y_train, y_test = developer.prepare_data(
                df_numeric,
                target_col=target_col,
                test_size=0.2
            )

            logger.info(f"   Training set: {len(X_train)} samples × {X_train.shape[1]} features")
            logger.info(f"   Test set: {len(X_test)} samples")

            results = {}

            # 모델별 학습 및 평가
            models_to_train = [
                ('linear_regression', developer.train_linear_regression),
                ('decision_tree', developer.train_decision_tree),
                ('random_forest', developer.train_random_forest),
                ('gradient_boosting', developer.train_gradient_boosting),
                ('xgboost', developer.train_xgboost),
                ('lightgbm', developer.train_lightgbm),
                ('neural_network', developer.train_neural_network)
            ]

            for model_key, train_func in models_to_train:
                try:
                    logger.info(f"\n  Training {model_key}...")
                    model = train_func(X_train, y_train)

                    # 모델 평가
                    metrics = developer.evaluate_model(model, X_test, y_test, model_key)

                    results[model_key] = {
                        'model': model,
                        'metrics': metrics
                    }
                    logger.info(f"  ✅ {model_key} - R²: {metrics.get('r2', 0):.4f}, RMSE: {metrics.get('rmse', 0):.2f}")
                except Exception as e:
                    logger.error(f"  ❌ {model_key} 학습 실패: {e}")

            if results:
                logger.info(f"\n✅ 모델 학습 완료: {len(results)}개 모델 학습됨")

                # 최고 성능 모델 찾기
                best_model_key = max(results.keys(), key=lambda k: results[k]['metrics'].get('r2', 0))
                best_score = results[best_model_key]['metrics'].get('r2', 0)
                logger.info(f"   최고 성능 모델: {best_model_key} (R²: {best_score:.4f})")

                # 모든 모델 저장
                for model_key, result in results.items():
                    try:
                        developer.save_model(result['model'], f'{model_key}_{timestamp}')
                        logger.info(f"   저장: {model_key}_{timestamp}.pkl")
                    except Exception as e:
                        logger.warning(f"   모델 저장 실패 ({model_key}): {e}")

                return results
            else:
                logger.error("❌ 모든 모델 학습 실패")
                return None

        except Exception as e:
            logger.error(f"❌ 모델 학습 단계 실패: {e}")
            logger.error(traceback.format_exc())
            return None

    def generate_report(self, collection_result, preprocess_result, train_result):
        """자동화 실행 리포트 생성"""
        logger.info("=" * 70)
        logger.info("STEP 4: 리포트 생성 (Report Generation)")
        logger.info("=" * 70)

        report = {
            'timestamp': timestamp,
            'status': 'success' if all([collection_result, preprocess_result, train_result]) else 'partial',
            'data_collection': {
                'status': 'success' if collection_result is not None else 'failed',
                'records': len(collection_result) if collection_result is not None else 0
            },
            'preprocessing': {
                'status': 'success' if preprocess_result is not None else 'failed',
                'samples': len(preprocess_result) if preprocess_result is not None else 0,
                'features': len(preprocess_result.columns) if preprocess_result is not None else 0
            },
            'model_training': {
                'status': 'success' if train_result else 'failed',
                'models_trained': len(train_result) if train_result else 0
            }
        }

        if train_result:
            report['model_training']['results'] = {}
            for model_name, result in train_result.items():
                # 메트릭스를 JSON 직렬화 가능한 형식으로 변환
                metrics = {k: v for k, v in result['metrics'].items() if not callable(v)}
                report['model_training']['results'][model_name] = metrics

        # 리포트 저장
        report_file = self.results_dir / f'orchestration_report_{timestamp}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 리포트 생성: {report_file.name}")
        logger.info(json.dumps(report, indent=2, ensure_ascii=False))

        return report

    def run_full_pipeline(self, start_date=None, end_date=None):
        """전체 파이프라인 실행"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 AVM 자동 오케스트레이션 시작")
        logger.info("=" * 70)

        try:
            # Step 1: 데이터 수집
            collection_result = self.collect_data(start_date, end_date)

            # Step 2: 데이터 전처리
            preprocess_result = self.preprocess_data()

            # Step 3: 모델 학습
            train_result = None
            if preprocess_result is not None:
                train_result = self.train_models(preprocess_result)

            # Step 4: 리포트 생성
            self.generate_report(collection_result, preprocess_result, train_result)

            logger.info("\n" + "=" * 70)
            logger.info("✅ 오케스트레이션 완료")
            logger.info("=" * 70)
            logger.info(f"Log file: {log_file}\n")

            return {
                'status': 'success',
                'log_file': str(log_file)
            }

        except Exception as e:
            logger.error(f"\n❌ 오케스트레이션 실패: {e}")
            logger.error(traceback.format_exc())
            logger.info(f"Log file: {log_file}\n")
            return {
                'status': 'failed',
                'error': str(e),
                'log_file': str(log_file)
            }


def main():
    """메인 함수 - CLI에서 실행 가능"""
    import argparse

    parser = argparse.ArgumentParser(description='AVM 자동 오케스트레이션')
    parser.add_argument('--start-date', help='시작 날짜 (YYYYMM format)', default=None)
    parser.add_argument('--end-date', help='종료 날짜 (YYYYMM format)', default=None)
    parser.add_argument('--config', help='설정 파일 경로', default=None)

    args = parser.parse_args()

    orchestrator = AVMOrchestrator(config_path=args.config)
    result = orchestrator.run_full_pipeline(
        start_date=args.start_date,
        end_date=args.end_date
    )

    sys.exit(0 if result['status'] == 'success' else 1)


if __name__ == '__main__':
    main()
