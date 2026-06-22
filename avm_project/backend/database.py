"""
데이터베이스 및 데이터 로딩 모듈
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent.parent
AVM_PROJECT = PROJECT_ROOT / "avm_project"
DATA_DIR = AVM_PROJECT / "data" / "raw"
LOGS_DIR = AVM_PROJECT / "logs"


class DatabaseManager:
    """데이터베이스 관리자"""

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.loaded = False
        self._load_data()

    def _load_data(self) -> None:
        """부동산 데이터 로드"""
        try:
            csv_path = DATA_DIR / "real_estate_2024.csv"

            if not csv_path.exists():
                logger.warning(f"데이터 파일 없음: {csv_path}")
                # 테스트 데이터 생성
                self._create_sample_data()
                return

            self.data = pd.read_csv(csv_path)
            self.loaded = True
            logger.info(f"데이터 로드 완료: {len(self.data)}행, {len(self.data.columns)}컬럼")

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            self._create_sample_data()

    def _create_sample_data(self) -> None:
        """샘플 데이터 생성"""
        np.random.seed(42)
        n_rows = 5000

        self.data = pd.DataFrame({
            '거래금액': np.random.randint(100000000, 500000000, n_rows),
            '거래일': pd.date_range('2020-01-01', periods=n_rows, freq='D'),
            '면적': np.random.uniform(10, 300, n_rows),
            '지역': np.random.choice(['강남구', '서초구', '송파구', '강서구'], n_rows),
            '건축년도': np.random.randint(1980, 2025, n_rows),
            '층수': np.random.randint(1, 50, n_rows),
            '방_개수': np.random.randint(1, 5, n_rows),
            '욕실_개수': np.random.randint(1, 3, n_rows),
            '엘리베이터': np.random.choice([0, 1], n_rows),
            '주차장': np.random.choice([0, 1], n_rows),
            '위도': np.random.uniform(37.0, 37.6, n_rows),
            '경도': np.random.uniform(126.7, 127.2, n_rows),
            'nearby_gas_stations': np.random.randint(0, 10, n_rows),
            'avg_gas_price': np.random.randint(1500, 1700, n_rows),
            'min_gas_price': np.random.randint(1400, 1600, n_rows),
            'max_gas_price': np.random.randint(1600, 1800, n_rows),
            'gas_station_density': np.random.uniform(0, 1, n_rows),
        })

        self.loaded = True
        logger.info("샘플 데이터 생성 완료")

    def get_data(self) -> Optional[pd.DataFrame]:
        """데이터 조회"""
        if not self.loaded:
            self._load_data()
        return self.data

    def get_summary_statistics(self) -> Dict[str, Any]:
        """요약 통계"""
        if not self.loaded or self.data is None:
            return {}

        try:
            return {
                'total_rows': len(self.data),
                'total_columns': len(self.data.columns),
                'memory_usage': f"{self.data.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
                'missing_values': int(self.data.isnull().sum().sum()),
                'missing_percentage': (self.data.isnull().sum().sum() / (len(self.data) * len(self.data.columns))) * 100,
            }
        except Exception as e:
            logger.error(f"통계 계산 실패: {e}")
            return {}

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """데이터 품질 메트릭"""
        if not self.loaded or self.data is None:
            return {}

        try:
            total_cells = len(self.data) * len(self.data.columns)
            missing = self.data.isnull().sum().sum()
            missing_pct = (missing / total_cells) * 100

            # 아웃라이어 감지 (IQR 방법)
            outliers = 0
            for col in self.data.select_dtypes(include=[np.number]).columns:
                Q1 = self.data[col].quantile(0.25)
                Q3 = self.data[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers += ((self.data[col] < (Q1 - 1.5 * IQR)) | (self.data[col] > (Q3 + 1.5 * IQR))).sum()

            outlier_pct = (outliers / total_cells) * 100
            quality_score = 1 - (missing_pct + outlier_pct) / 100

            return {
                'total_rows': len(self.data),
                'missing_values': int(missing),
                'missing_percentage': round(missing_pct, 2),
                'outliers': int(outliers),
                'outlier_percentage': round(outlier_pct, 2),
                'quality_score': round(quality_score, 4),
                'status': 'excellent' if quality_score > 0.99 else 'good' if quality_score > 0.95 else 'fair',
            }
        except Exception as e:
            logger.error(f"데이터 품질 계산 실패: {e}")
            return {}

    def get_price_distribution(self, bins: int = 5) -> List[Dict[str, Any]]:
        """거래금액 분포"""
        if not self.loaded or self.data is None:
            return []

        try:
            # '거래금액' 컬럼 찾기
            price_col = None
            for col in self.data.columns:
                if '거래' in col or '가격' in col or '금액' in col:
                    price_col = col
                    break

            if price_col is None and '거래금액' in self.data.columns:
                price_col = '거래금액'

            if price_col is None:
                logger.warning("가격 컬럼을 찾을 수 없음")
                return []

            # 구간별 분포
            min_price = self.data[price_col].min()
            max_price = self.data[price_col].max()
            bin_edges = np.linspace(min_price, max_price, bins + 1)

            distribution = []
            for i in range(len(bin_edges) - 1):
                start = bin_edges[i]
                end = bin_edges[i + 1]
                count = ((self.data[price_col] >= start) & (self.data[price_col] < end)).sum()

                range_label = f"{int(start/100000000)}-{int(end/100000000)}억"
                distribution.append({
                    'range': range_label,
                    'count': int(count),
                    'percentage': round((count / len(self.data)) * 100, 1)
                })

            return distribution

        except Exception as e:
            logger.error(f"가격 분포 계산 실패: {e}")
            return []

    def get_region_distribution(self) -> List[Dict[str, Any]]:
        """지역별 분포"""
        if not self.loaded or self.data is None:
            return []

        try:
            # '지역' 컬럼 찾기
            region_col = None
            for col in self.data.columns:
                if '지역' in col or '구' in col:
                    region_col = col
                    break

            if region_col is None:
                logger.warning("지역 컬럼을 찾을 수 없음")
                return []

            distribution = self.data[region_col].value_counts().head(5).to_dict()

            result = []
            for region, count in distribution.items():
                result.append({
                    'name': str(region),
                    'value': int(count),
                    'percentage': round((count / len(self.data)) * 100, 1)
                })

            return result

        except Exception as e:
            logger.error(f"지역 분포 계산 실패: {e}")
            return []

    def get_column_info(self) -> List[Dict[str, Any]]:
        """컬럼 정보"""
        if not self.loaded or self.data is None:
            return []

        try:
            columns_info = []
            for col in self.data.columns:
                columns_info.append({
                    'name': col,
                    'type': str(self.data[col].dtype),
                    'non_null_count': int(self.data[col].notna().sum()),
                    'null_count': int(self.data[col].isna().sum()),
                })

            return columns_info

        except Exception as e:
            logger.error(f"컬럼 정보 조회 실패: {e}")
            return []


class RetrainingHistoryManager:
    """재학습 이력 관리"""

    def __init__(self):
        self.history_file = LOGS_DIR / "retrain_history.jsonl"

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """최신 재학습 결과 조회"""
        try:
            if not self.history_file.exists():
                return None

            import json
            with open(self.history_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    return json.loads(lines[-1])
            return None

        except Exception as e:
            logger.error(f"최신 결과 조회 실패: {e}")
            return None

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """재학습 이력 조회"""
        try:
            if not self.history_file.exists():
                return []

            import json
            history = []
            with open(self.history_file, 'r') as f:
                for line in f:
                    history.append(json.loads(line))

            return history[-limit:]

        except Exception as e:
            logger.error(f"이력 조회 실패: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """재학습 통계"""
        try:
            history = self.get_history(limit=100)
            if not history:
                return {}

            r2_scores = [h.get('ensemble', {}).get('r2', 0) for h in history]

            return {
                'total_trainings': len(history),
                'average_r2': round(np.mean(r2_scores), 4),
                'max_r2': round(np.max(r2_scores), 4),
                'min_r2': round(np.min(r2_scores), 4),
                'last_training': history[-1].get('timestamp') if history else None,
            }

        except Exception as e:
            logger.error(f"통계 계산 실패: {e}")
            return {}


# 전역 인스턴스
db_manager = DatabaseManager()
history_manager = RetrainingHistoryManager()
