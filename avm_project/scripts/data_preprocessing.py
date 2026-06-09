"""
AVM 모델 개발 - 데이터 전처리 스크립트
Data Preprocessing for Automated Valuation Model

Author: AI Assistant
Date: 2026-06-09
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import logging
from typing import Tuple, List, Dict
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """데이터 전처리 클래스"""

    def __init__(self, data_dir: str = 'data', output_dir: str = 'output'):
        """
        초기화

        Args:
            data_dir: 데이터 디렉토리 경로
            output_dir: 출력 디렉토리 경로
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.raw_data = None
        self.processed_data = None
        self.metadata = {}

        # 디렉토리 생성
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_data(self, filename: str) -> pd.DataFrame:
        """
        데이터 로드

        Args:
            filename: 파일명

        Returns:
            pd.DataFrame: 로드된 데이터
        """
        try:
            filepath = self.data_dir / filename

            if filename.endswith('.csv'):
                data = pd.read_csv(filepath, encoding='utf-8')
            elif filename.endswith('.xlsx'):
                data = pd.read_excel(filepath)
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {filename}")

            logger.info(f"데이터 로드 완료: {filename} ({data.shape[0]} rows, {data.shape[1]} cols)")
            self.raw_data = data
            return data

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            raise

    def explore_data(self) -> Dict:
        """
        데이터 탐색

        Returns:
            Dict: 데이터 통계 정보
        """
        if self.raw_data is None:
            raise ValueError("먼저 데이터를 로드하세요.")

        stats = {
            'shape': self.raw_data.shape,
            'dtypes': self.raw_data.dtypes.to_dict(),
            'missing_values': self.raw_data.isnull().sum().to_dict(),
            'numeric_stats': self.raw_data.describe().to_dict(),
        }

        logger.info(f"데이터 탐색 완료")
        logger.info(f"Shape: {stats['shape']}")
        logger.info(f"결측값: {stats['missing_values']}")

        return stats

    def handle_missing_values(self, method: str = 'mean') -> pd.DataFrame:
        """
        결측값 처리

        Args:
            method: 처리 방법 ('mean', 'median', 'drop')

        Returns:
            pd.DataFrame: 결측값 처리된 데이터
        """
        data = self.raw_data.copy()

        if method == 'drop':
            data = data.dropna()
            logger.info(f"결측값 행 제거: {data.shape[0]} rows 남음")
        elif method in ['mean', 'median']:
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            imputer = SimpleImputer(strategy=method)
            data[numeric_cols] = imputer.fit_transform(data[numeric_cols])
            logger.info(f"결측값 {method}으로 처리 완료")
        else:
            raise ValueError(f"지원하지 않는 방법: {method}")

        self.processed_data = data
        return data

    def detect_outliers(self, columns: List[str] = None,
                       method: str = 'iqr', threshold: float = 1.5) -> Dict:
        """
        이상값 탐지

        Args:
            columns: 검사할 컬럼 (None이면 모든 숫자형 컬럼)
            method: 탐지 방법 ('iqr', 'zscore')
            threshold: 임계값

        Returns:
            Dict: 이상값 정보
        """
        data = self.processed_data if self.processed_data is not None else self.raw_data

        if columns is None:
            columns = data.select_dtypes(include=[np.number]).columns.tolist()

        outliers = {}

        if method == 'iqr':
            for col in columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - threshold * IQR
                upper = Q3 + threshold * IQR

                outlier_mask = (data[col] < lower) | (data[col] > upper)
                outliers[col] = {
                    'count': outlier_mask.sum(),
                    'percentage': (outlier_mask.sum() / len(data)) * 100
                }

        logger.info(f"이상값 탐지 완료: {len(outliers)} 컬럼 검사")
        return outliers

    def normalize_data(self, columns: List[str] = None,
                      method: str = 'standardize') -> Tuple[pd.DataFrame, Dict]:
        """
        데이터 정규화

        Args:
            columns: 정규화할 컬럼 (None이면 모든 숫자형 컬럼)
            method: 방법 ('standardize', 'minmax')

        Returns:
            Tuple[pd.DataFrame, Dict]: 정규화된 데이터와 스케일러 정보
        """
        data = self.processed_data if self.processed_data is not None else self.raw_data
        data = data.copy()

        if columns is None:
            columns = data.select_dtypes(include=[np.number]).columns.tolist()

        if method == 'standardize':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        else:
            raise ValueError(f"지원하지 않는 방법: {method}")

        data[columns] = scaler.fit_transform(data[columns])

        # 스케일러 정보 저장
        scaler_info = {
            'method': method,
            'columns': columns,
            'mean': scaler.mean_.tolist() if hasattr(scaler, 'mean_') else None,
            'scale': scaler.scale_.tolist() if hasattr(scaler, 'scale_') else None,
        }

        self.processed_data = data
        logger.info(f"데이터 정규화 완료: {method} 방법 사용")

        return data, scaler_info

    def feature_engineering(self, config: Dict = None) -> pd.DataFrame:
        """
        피처 엔지니어링

        Args:
            config: 피처 엔지니어링 설정

        Returns:
            pd.DataFrame: 피처 엔지니어링된 데이터
        """
        data = self.processed_data if self.processed_data is not None else self.raw_data
        data = data.copy()

        logger.info(f"피처 엔지니어링 시작")

        # 숫자형 컬럼에 대한 상호작용 항 생성 (예: 면적 × 가격)
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()

        # 통계적 특성 추가
        if len(numeric_cols) > 0:
            data['numeric_mean'] = data[numeric_cols].mean(axis=1)
            data['numeric_std'] = data[numeric_cols].std(axis=1)
            data['numeric_max'] = data[numeric_cols].max(axis=1)
            data['numeric_min'] = data[numeric_cols].min(axis=1)

        logger.info(f"피처 엔지니어링 완료: {data.shape[1]} 컬럼 (추가 피처 4개)")

        self.processed_data = data
        return data

    def save_processed_data(self, filename: str = 'processed_data.csv') -> str:
        """
        전처리된 데이터 저장

        Args:
            filename: 저장 파일명

        Returns:
            str: 저장된 파일 경로
        """
        if self.processed_data is None:
            raise ValueError("저장할 전처리된 데이터가 없습니다.")

        output_path = self.output_dir / filename
        self.processed_data.to_csv(output_path, index=False, encoding='utf-8')

        logger.info(f"데이터 저장 완료: {output_path}")
        return str(output_path)

    def save_metadata(self, filename: str = 'metadata.json') -> str:
        """
        메타데이터 저장

        Args:
            filename: 저장 파일명

        Returns:
            str: 저장된 파일 경로
        """
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"메타데이터 저장 완료: {output_path}")
        return str(output_path)


def main():
    """메인 실행 함수"""
    logger.info("AVM 데이터 전처리 시작")

    # 전처리기 초기화
    preprocessor = DataPreprocessor(
        data_dir='avm_project/data',
        output_dir='avm_project/output'
    )

    # 예제: CSV 파일 로드 및 전처리
    # (실제 NPL 데이터 파일로 대체 필요)
    try:
        # 데이터 로드 (파일이 있으면)
        # data = preprocessor.load_data('npl_data.csv')

        # 데이터 탐색
        # stats = preprocessor.explore_data()

        # 결측값 처리
        # preprocessor.handle_missing_values(method='mean')

        # 이상값 탐지
        # outliers = preprocessor.detect_outliers(method='iqr')

        # 정규화
        # preprocessor.normalize_data(method='standardize')

        # 피처 엔지니어링
        # preprocessor.feature_engineering()

        # 데이터 저장
        # preprocessor.save_processed_data()

        logger.info("AVM 데이터 전처리 완료")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == '__main__':
    main()
