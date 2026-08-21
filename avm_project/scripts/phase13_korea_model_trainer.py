#!/usr/bin/env python3
"""
Phase 13.8.KR - Korea-Specific Model Training Pipeline
한국 부동산 시장 특화 모델 학습 및 지역별 분석.

구성:
  - 전국 통합 모델 (Nationwide)
  - 지역별 모델 (Seoul, Busan, Gyeonggi, etc.)
  - 실시간 시장 성능 추적

실행:
    python scripts/phase13_korea_model_trainer.py --mode nationwide
    python scripts/phase13_korea_model_trainer.py --mode regional
    python scripts/phase13_korea_model_trainer.py --mode all
"""

import json
import logging
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent))
from phase13_brazil_model_trainer import build_stacking_model, evaluate

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

TARGET_COL = 'price_local'
LEAK_PATTERNS = ('price_local', 'indexed_price')
KOREA_TOLERANCE = 0.12  # ±12% (시장 변동성)
KOREA_MAPE_TARGET = 0.11  # 목표 11% MAPE

# 한국 지역 설정
KOREA_REGIONS = {
    'Seoul': 0.40,
    'Busan': 0.15,
    'Daegu': 0.08,
    'Incheon': 0.08,
    'Daejeon': 0.05,
    'Gwangju': 0.04,
    'Ulsan': 0.04,
    'Gyeonggi': 0.10,
    'Kangwon': 0.02,
    'Chungbuk': 0.02,
}

# 한국 시장 특성
KOREA_MARKET = {
    'currency': 'KRW',
    'price_per_m2': 2_727_272,  # 평당 900만원 기준
    'tolerance': KOREA_TOLERANCE,
    'mape_target': KOREA_MAPE_TARGET,
}


class KoreaModelTrainer:
    """한국 부동산 모델 학습기"""

    def __init__(self, data_file: str = 'data/raw/KR_raw.csv') -> None:
        self.data_file = Path(data_file)
        self.models_dir = Path('output/models/korea')
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}

    def load_korea_data(self) -> pd.DataFrame:
        """한국 데이터 로드"""
        if not self.data_file.exists():
            log.error(f"❌ Data file not found: {self.data_file}")
            raise FileNotFoundError(str(self.data_file))

        df = pd.read_csv(self.data_file)
        log.info(f"✅ Loaded Korean data: {len(df):,} properties, {len(df.columns)} features")
        return df

    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """학습용 데이터 준비"""
        y = df[TARGET_COL].to_numpy(dtype=np.float64)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if not any(p in c for p in LEAK_PATTERNS)]
        X = df[feature_cols].fillna(0.0).to_numpy(dtype=np.float64)

        log.info(f"📊 Training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y, feature_cols

    def train_nationwide_model(self, df: pd.DataFrame) -> Dict:
        """전국 통합 모델 학습"""
        log.info("\n" + "=" * 70)
        log.info("Training Nationwide Model (전국 통합)")
        log.info("=" * 70)

        X, y, feature_cols = self.prepare_training_data(df)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 모델 학습
        t0 = time.time()
        model = build_stacking_model()
        model.fit(X_train, y_train)
        elapsed = time.time() - t0

        # 평가
        metrics = evaluate(model, X_train, y_train, X_test, y_test)

        # 저장
        model_path = self.models_dir / 'KR_nationwide_v1.0.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        metadata = {
            'model_id': 'KR_nationwide_v1.0',
            'scope': 'nationwide',
            'n_samples': len(df),
            'n_features': len(feature_cols),
            'feature_columns': feature_cols,
            'performance': metrics,
            'mape_target': KOREA_MAPE_TARGET,
            'target_met': metrics['test_mape'] < KOREA_MAPE_TARGET,
            'training_sec': round(elapsed, 1),
            'model_size_mb': round(model_path.stat().st_size / 1024 / 1024, 2),
            'created_date': datetime.now().isoformat(),
        }

        with open(self.models_dir / 'KR_nationwide_v1.0_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        log.info(f"\n✅ Nationwide Model Training Complete:")
        log.info(f"  MAPE: {metrics['test_mape']:.2%} (target: {KOREA_MAPE_TARGET:.0%})")
        log.info(f"  R²: {metrics['test_r2']:.4f}")
        log.info(f"  Training time: {elapsed:.1f}s")

        self.results['nationwide'] = metadata
        return metadata

    def train_regional_models(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """지역별 모델 학습 (Seoul, Busan, Gyeonggi, etc.)"""
        log.info("\n" + "=" * 70)
        log.info("Training Regional Models (지역별 모델)")
        log.info("=" * 70)

        regional_results = {}

        for region in ['Seoul', 'Busan', 'Gyeonggi', 'Daegu', 'Incheon']:
            df_region = df[df['region'] == region]
            if len(df_region) < 100:
                log.warning(f"⚠️  {region}: Insufficient data ({len(df_region)} < 100)")
                continue

            log.info(f"\n📍 {region} ({len(df_region):,} properties)")

            X, y, feature_cols = self.prepare_training_data(df_region)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # 모델 학습
            t0 = time.time()
            model = build_stacking_model()
            model.fit(X_train, y_train)
            elapsed = time.time() - t0

            # 평가
            metrics = evaluate(model, X_train, y_train, X_test, y_test)

            # 저장
            model_path = self.models_dir / f'KR_{region.lower()}_v1.0.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            metadata = {
                'model_id': f'KR_{region.lower()}_v1.0',
                'scope': 'regional',
                'region': region,
                'n_samples': len(df_region),
                'n_features': len(feature_cols),
                'performance': metrics,
                'target_met': metrics['test_mape'] < KOREA_MAPE_TARGET,
                'training_sec': round(elapsed, 1),
                'model_size_mb': round(model_path.stat().st_size / 1024 / 1024, 2),
            }

            with open(self.models_dir / f'KR_{region.lower()}_v1.0_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            log.info(f"  MAPE: {metrics['test_mape']:.2%} {'✅' if metadata['target_met'] else '⚠️'}")
            log.info(f"  R²: {metrics['test_r2']:.4f}")

            regional_results[region] = metadata

        self.results['regional'] = regional_results
        return regional_results

    def generate_performance_report(self) -> None:
        """모델 성능 리포트 생성"""
        log.info("\n" + "=" * 70)
        log.info("Korea Model Performance Report")
        log.info("=" * 70)

        report = f"""
╔════════════════════════════════════════════════════════════╗
║     한국 부동산 모델 성능 리포트 (Korea AVM Report)        ║
╚════════════════════════════════════════════════════════════╝

📊 전국 통합 모델 (Nationwide)
┌──────────────┬──────────┬────────────┐
│   지표      │   값    │   상태     │
├──────────────┼──────────┼────────────┤
│   MAPE      │ {self.results['nationwide']['performance']['test_mape']:.2%}  │ {'✅ PASS' if self.results['nationwide']['target_met'] else '⚠️ REVIEW'} │
│   R²        │ {self.results['nationwide']['performance']['test_r2']:.4f}  │        │
│   샘플 수   │ {self.results['nationwide']['n_samples']:,}  │        │
│   특성 수   │  {self.results['nationwide']['n_features']:,}   │        │
│ 학습 시간   │ {self.results['nationwide']['training_sec']}s  │        │
│ 모델 크기   │ {self.results['nationwide']['model_size_mb']:.1f}MB │        │
└──────────────┴──────────┴────────────┘

🏙️ 지역별 모델 성능 (Regional Models)
┌─────────────┬────────┬────────┬──────────┐
│   지역     │ MAPE  │  R²   │  상태   │
├─────────────┼────────┼────────┼──────────┤
"""

        for region, meta in self.results.get('regional', {}).items():
            status = '✅' if meta['target_met'] else '⚠️'
            mape = meta['performance']['test_mape']
            r2 = meta['performance']['test_r2']
            report += f"│ {region:11} │ {mape:6.2%} │ {r2:6.4f} │ {status}      │\n"

        report += f"""└─────────────┴────────┴────────┴──────────┘

📈 시장 분석 (Market Analysis)
• 전국 평균 MAPE: {self.results['nationwide']['performance']['test_mape']:.2%}
• 목표 MAPE: {KOREA_MAPE_TARGET:.0%}
• 달성도: {'✅ 목표 달성' if self.results['nationwide']['target_met'] else '🔄 개선 필요'}
• 총 학습 데이터: {self.results['nationwide']['n_samples']:,}개
• 모델 개수: {1 + len(self.results.get('regional', {}))}개 (전국 + 지역별)

🎯 다음 단계 (Next Steps)
1. Phase 14.KR: CI/CD 자동화 (월간 재학습)
2. Phase 14.1.KR: INT8 양자화 (모바일 최적화)
3. Phase 14.2.KR: 모바일 앱 배포 (iOS/Android)

생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 파일로 저장
        report_path = self.models_dir / 'KR_performance_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        log.info(report)
        log.info(f"✅ Report saved: {report_path}")

    def run_all(self) -> Dict:
        """전체 파이프라인 실행"""
        log.info("🇰🇷 Starting Korea-Specific Model Training Pipeline")

        # 데이터 로드
        df = self.load_korea_data()

        # 전국 모델 학습
        self.train_nationwide_model(df)

        # 지역별 모델 학습
        self.train_regional_models(df)

        # 성능 리포트 생성
        self.generate_performance_report()

        return self.results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.8.KR Korea Model Training')
    parser.add_argument('--mode', choices=['nationwide', 'regional', 'all'], default='all')
    parser.add_argument('--data', default='data/raw/KR_raw.csv')
    args = parser.parse_args()

    trainer = KoreaModelTrainer(args.data)

    if args.mode in ['nationwide', 'all']:
        df = trainer.load_korea_data()
        trainer.train_nationwide_model(df)

    if args.mode in ['regional', 'all']:
        df = trainer.load_korea_data()
        trainer.train_regional_models(df)

    if args.mode == 'all':
        trainer.generate_performance_report()

    exit(0)


if __name__ == '__main__':
    main()
