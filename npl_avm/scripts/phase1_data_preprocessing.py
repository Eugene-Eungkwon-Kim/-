#!/usr/bin/env python3
"""
Phase 1: 데이터 전처리 스크립트
목표: 원본 데이터 → 모델 학습용 데이터
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
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

from app.db.database import SessionLocal
from app.db.models import ComparableSale, Property


class Phase1DataPreprocessor:
    """Phase 1 데이터 전처리 클래스."""

    def __init__(self):
        """초기화."""
        self.db = SessionLocal()
        self.df = None
        logger.info("DataPreprocessor initialized")

    def load_data(self):
        """DB에서 데이터 로드."""
        logger.info("\n[Step 1/5] 데이터 로드 중...")

        try:
            # ComparableSale 데이터 로드
            comparables = self.db.query(ComparableSale).all()

            data = []
            for cs in comparables:
                # 필수 필드가 있는지 확인
                if cs.trade_amount and cs.land_area:
                    data.append({
                        'id': cs.id,
                        'address_sido': cs.address_sido,
                        'address_sigungu': cs.address_sigungu,
                        'address_dong': cs.address_dong,
                        'address_full': cs.address_full,
                        'hammer_price': float(cs.trade_amount),  # Numeric → float
                        'reference_date': cs.trade_date,
                        'property_type': cs.property_type,
                        'land_area_sqm': cs.land_area,
                        'building_area_sqm': cs.building_area,
                        'unit_price_py': cs.unit_price_py,
                        'land_price_sqm': cs.land_price_sqm,
                        'approval_date': cs.approval_date,
                    })

            self.df = pd.DataFrame(data)
            logger.info(f"✅ 로드 완료: {len(self.df)} rows × {len(self.df.columns)} columns")
            logger.info(f"   컬럼: {self.df.columns.tolist()}")

            # 기본 통계
            if len(self.df) > 0:
                logger.info(f"   거래가 범위: ₩{self.df['hammer_price'].min():.0f} ~ ₩{self.df['hammer_price'].max():.0f}")
                logger.info(f"   면적 범위: {self.df['land_area_sqm'].min():.0f} ~ {self.df['land_area_sqm'].max():.0f} ㎡")

            return self.df

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def handle_missing_values(self):
        """결측치 처리."""
        logger.info("\n[Step 2/5] 결측치 처리 중...")

        initial_missing = self.df.isnull().sum().sum()

        # 수치형 컬럼 결측치 처리
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if self.df[col].isnull().sum() > 0:
                median_val = self.df[col].median()
                self.df[col].fillna(median_val, inplace=True)
                logger.info(f"   {col:20s}: {self.df[col].isnull().sum()} → 0 (중앙값: {median_val:.0f})")

        # 범주형 컬럼 결측치 처리
        categorical_cols = self.df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if self.df[col].isnull().sum() > 0:
                mode_val = self.df[col].mode()[0] if len(self.df[col].mode()) > 0 else 'Unknown'
                self.df[col].fillna(mode_val, inplace=True)
                logger.info(f"   {col:20s}: {self.df[col].isnull().sum()} → 0 (최빈값: {mode_val})")

        final_missing = self.df.isnull().sum().sum()
        logger.info(f"✅ 결측치 처리 완료: {initial_missing} → {final_missing}")

        return self.df

    def remove_outliers(self):
        """이상치 제거 (IQR 방식)."""
        logger.info("\n[Step 3/5] 이상치 제거 중...")

        initial_len = len(self.df)
        outlier_cols = ['hammer_price', 'area_sqm']

        for col in outlier_cols:
            if col in self.df.columns:
                Q1 = self.df[col].quantile(0.25)
                Q3 = self.df[col].quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                outliers_count = len(self.df[
                    (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
                ])

                self.df = self.df[
                    (self.df[col] >= lower_bound) & (self.df[col] <= upper_bound)
                ]

                logger.info(f"   {col:20s}: {outliers_count:4d} rows removed")

        removed = initial_len - len(self.df)
        logger.info(f"✅ 이상치 제거 완료: {initial_len} → {len(self.df)} (-{removed})")

        return self.df

    def engineer_features(self):
        """특성 엔지니어링."""
        logger.info("\n[Step 4/5] 특성 엔지니어링 중...")

        # 1. 거래 경과 기간
        self.df['reference_date'] = pd.to_datetime(self.df['reference_date'])
        self.df['days_since_transaction'] = (
            datetime.now() - self.df['reference_date']
        ).dt.days
        logger.info("   ✓ days_since_transaction (거래 경과 일수)")

        # 2. 승인 연도 (approval_date에서)
        self.df['approval_date'] = pd.to_datetime(self.df['approval_date'])
        current_year = datetime.now().year
        self.df['building_age'] = current_year - self.df['approval_date'].dt.year
        self.df.loc[self.df['building_age'] < 0, 'building_age'] = 0
        logger.info("   ✓ building_age (건물 나이)")

        # 3. 단가 (㎡당 가격)
        self.df['price_per_sqm'] = self.df['hammer_price'] / self.df['land_area_sqm'].replace(0, np.nan)
        logger.info("   ✓ price_per_sqm (㎡당 거래가)")

        # 4. 건축연도가 최근인지 여부
        self.df['is_new'] = (self.df['approval_date'].dt.year >= 2020).astype(int)
        logger.info("   ✓ is_new (최근 건축 여부)")

        # 5. 부동산 유형 (숫자로 인코딩)
        property_type_map = {
            'Apartment': 1,
            'House': 2,
            'Commercial': 3,
            'Industrial': 4,
            'Land': 5,
            'Other': 0,
            '아파트': 1,
            '다세대': 2,
            '연립': 2,
            '오피스텔': 3,
        }
        self.df['property_type_code'] = self.df['property_type'].map(property_type_map).fillna(0).astype(int)
        logger.info("   ✓ property_type_code (부동산 유형 코드)")

        logger.info(f"✅ 특성 엔지니어링 완료: {len(self.df.columns)} 컬럼")

        return self.df

    def normalize_features(self):
        """특성 정규화."""
        logger.info("\n[Step 5/5] 특성 정규화 중...")

        from sklearn.preprocessing import StandardScaler

        numeric_cols = [
            'land_area_sqm', 'building_area_sqm',
            'days_since_transaction', 'building_age',
            'price_per_sqm', 'unit_price_py', 'land_price_sqm'
        ]

        # 실제 수치형 컬럼만 정규화
        cols_to_normalize = [col for col in numeric_cols if col in self.df.columns]

        # NaN 값 채우기
        for col in cols_to_normalize:
            self.df[col] = self.df[col].fillna(self.df[col].median())

        scaler = StandardScaler()
        normalized = scaler.fit_transform(self.df[cols_to_normalize])

        self.df_normalized = self.df.copy()
        self.df_normalized[cols_to_normalize] = normalized

        # 스케일러 저장
        import pickle
        models_dir = project_root / 'models'
        models_dir.mkdir(exist_ok=True)

        with open(models_dir / 'scaler.pkl', 'wb') as f:
            pickle.dump(scaler, f)

        logger.info(f"✅ 정규화 완료: {len(cols_to_normalize)} 컬럼")
        logger.info(f"   스케일러 저장: models/scaler.pkl")

        return self.df_normalized

    def validate_data(self):
        """데이터 검증."""
        logger.info("\n[검증] 데이터 품질 확인 중...")

        try:
            # 1. 최소 행 수
            assert len(self.df) >= 100, f"데이터 부족: {len(self.df)} < 100"
            logger.info(f"   ✓ 행 수: {len(self.df)} >= 100")

            # 2. 결측치 없음
            assert self.df.isnull().sum().sum() == 0, "결측치 존재"
            logger.info("   ✓ 결측치: 0")

            # 3. 가격 범위
            assert (self.df['hammer_price'] > 0).all(), "음수 가격 존재"
            assert (self.df['hammer_price'] < 1e11).all(), "비현실적 가격 존재"
            logger.info(f"   ✓ 가격 범위: ₩{self.df['hammer_price'].min():.0f} ~ ₩{self.df['hammer_price'].max():.0f}")

            # 4. 면적 범위
            assert (self.df['land_area_sqm'] > 0).all(), "음수 면적 존재"
            logger.info(f"   ✓ 면적 범위: {self.df['land_area_sqm'].min():.0f} ~ {self.df['land_area_sqm'].max():.0f} ㎡")

            logger.info("\n✅ 모든 검증 통과!")
            return True

        except AssertionError as e:
            logger.error(f"검증 실패: {e}")
            raise

    def save_data(self):
        """데이터 저장."""
        logger.info("\n[저장] 데이터 저장 중...")

        data_dir = project_root / 'data'
        data_dir.mkdir(exist_ok=True)

        # 정규화되지 않은 데이터 (원본 스케일)
        csv_path = data_dir / 'preprocessed_data.csv'
        self.df.to_csv(csv_path, index=False)
        logger.info(f"   ✓ {csv_path}")

        # 정규화된 데이터 (모델 훈련용)
        csv_normalized_path = data_dir / 'preprocessed_data_normalized.csv'
        self.df_normalized.to_csv(csv_normalized_path, index=False)
        logger.info(f"   ✓ {csv_normalized_path}")

        # 통계 정보
        stats_path = data_dir / 'data_statistics.txt'
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("데이터 전처리 통계\n")
            f.write("=" * 60 + "\n\n")

            f.write("데이터 정보\n")
            f.write("-" * 60 + "\n")
            f.write(f"행 수: {len(self.df)}\n")
            f.write(f"열 수: {len(self.df.columns)}\n")
            f.write(f"생성 날짜: {datetime.now()}\n\n")

            f.write("컬럼 정보\n")
            f.write("-" * 60 + "\n")
            f.write(self.df.describe().to_string())
            f.write("\n\n")

            f.write("컬럼 목록\n")
            f.write("-" * 60 + "\n")
            for col in self.df.columns:
                f.write(f"  - {col}: {self.df[col].dtype}\n")

        logger.info(f"   ✓ {stats_path}")

        logger.info("\n✅ 데이터 저장 완료!")

    def run(self):
        """메인 실행."""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("🚀 Phase 1 데이터 전처리 시작")
            logger.info("=" * 60)

            self.load_data()
            self.handle_missing_values()
            self.remove_outliers()
            self.engineer_features()
            self.normalize_features()
            self.validate_data()
            self.save_data()

            logger.info("\n" + "=" * 60)
            logger.info("✅ 데이터 전처리 완료!")
            logger.info("=" * 60)
            logger.info("\n📊 다음 단계:")
            logger.info("   → scripts/phase1_baseline_models.py 실행")
            logger.info("   → 베이스라인 모델 훈련 시작")

            return self.df

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            self.db.close()


def main():
    """메인 함수."""
    preprocessor = Phase1DataPreprocessor()
    preprocessor.run()


if __name__ == "__main__":
    main()
