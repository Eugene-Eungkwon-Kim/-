#!/usr/bin/env python3
"""
실제 부동산 데이터 로더 (Track A 데이터 소스)
LG 외장하드 데이터 + API 보강 통합 파이프라인
2026-06-24
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
SCHEMA_FILE = PROJECT_DIR / "models" / "feature_schema.json"
EXTERNAL_DRIVE = Path("/mnt/avm_data")  # LG 외장하드
OUTPUT_DIR = PROJECT_DIR / "data" / "real"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 현재 feature schema 로드
schema = json.load(open(SCHEMA_FILE))
REQUIRED_FEATURES = schema["features"]
TARGET_COLUMN = schema["target"]

print("=" * 80)
print("🏗️  실제 부동산 데이터 로더 (Track A)")
print("=" * 80)
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\n필수 컬럼 (schema): {REQUIRED_FEATURES}")
print(f"타겟: {TARGET_COLUMN}")

class RealEstateDataLoader:
    """LG 외장하드 + API 기반 부동산 데이터 로더"""

    def __init__(self, schema_features: List[str], target_col: str):
        self.required_features = schema_features
        self.target = target_col
        self.all_features = schema_features + [target_col]
        self.df = None

    def load_from_external_drive(self) -> Optional[pd.DataFrame]:
        """LG 외장하드에서 건축물관리대장/VWorld 데이터 로드"""
        print("\n" + "-" * 80)
        print("1️⃣  LG 외장하드 데이터 수집")
        print("-" * 80)

        if not EXTERNAL_DRIVE.exists():
            logger.warning(f"외장하드 경로 없음: {EXTERNAL_DRIVE}")
            return None

        raw_dir = EXTERNAL_DRIVE / "Raw_Data"
        processed_dir = EXTERNAL_DRIVE / "Processed_Data"

        dfs = []

        # Processed_Data 우선 확인 (품질이 높음)
        if processed_dir.exists():
            csv_files = list(processed_dir.glob("*.csv"))
            if csv_files:
                print(f"   Processed_Data 폴더 발견 ({len(csv_files)}개 파일)")
                for csv_file in csv_files:
                    try:
                        df_temp = pd.read_csv(csv_file, encoding='utf-8-sig')
                        print(f"   ✓ {csv_file.name}: {len(df_temp)}행 × {len(df_temp.columns)}컬럼")
                        dfs.append(df_temp)
                    except Exception as e:
                        logger.error(f"   ✗ {csv_file.name} 로드 실패: {e}")

        # Raw_Data 확인 (전처리 필요)
        if raw_dir.exists():
            csv_files = list(raw_dir.glob("*.csv"))
            if csv_files:
                print(f"   Raw_Data 폴더 발견 ({len(csv_files)}개 파일)")
                for csv_file in csv_files:
                    try:
                        df_temp = pd.read_csv(csv_file, encoding='utf-8-sig')
                        print(f"   ✓ {csv_file.name}: {len(df_temp)}행 × {len(df_temp.columns)}컬럼")
                        dfs.append(df_temp)
                    except Exception as e:
                        logger.error(f"   ✗ {csv_file.name} 로드 실패: {e}")

        if not dfs:
            logger.warning("외장하드에서 데이터 파일을 찾을 수 없음")
            return None

        # 데이터 통합
        df_combined = pd.concat(dfs, ignore_index=True)
        print(f"\n   📊 통합 결과: {len(df_combined)}행 × {len(df_combined.columns)}컬럼")
        return df_combined

    def load_synthetic_fallback(self) -> pd.DataFrame:
        """API 또는 외장하드 데이터 부족 시 합성 데이터로 대체"""
        print("\n" + "-" * 80)
        print("2️⃣  합성 데이터 폴백 (외장하드 데이터 부족)")
        print("-" * 80)

        # 기존의 검증된 synthetic 데이터 사용
        existing_data = PROJECT_DIR / "data" / "processed" / "cleaned_real_estate_combined_20260617.csv"

        if existing_data.exists():
            df = pd.read_csv(existing_data)
            print(f"   ✓ 기존 데이터 사용: {len(df)}행 × {len(df.columns)}컬럼")
            print(f"   ⚠️  이 데이터는 신호가 약함 (R² 목표 미달성)")
            print(f"   💡 LG 외장하드 데이터 준비 후 재학습 필요")
            return df
        else:
            logger.error(f"폴백 데이터도 없음: {existing_data}")
            raise FileNotFoundError("사용 가능한 데이터 없음")

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """현재 schema와 데이터 맞춤도 검증"""
        print("\n" + "-" * 80)
        print("3️⃣  Schema 검증")
        print("-" * 80)

        df_cols = set(df.columns)
        required_cols = set(self.required_features + [self.target])

        missing_cols = required_cols - df_cols
        if missing_cols:
            print(f"   ❌ 부족한 컬럼: {missing_cols}")

            # 자동 매핑 시도
            print(f"   🔄 자동 컬럼 매핑 시도...")
            fuzzy_mapped = self._fuzzy_match_columns(df_cols, required_cols)
            if fuzzy_mapped:
                print(f"   ✓ 매핑 성공: {fuzzy_mapped}")
                df = df.rename(columns=fuzzy_mapped)
            else:
                print(f"   ⚠️  매핑 실패 - 수동 검토 필요")
        else:
            print(f"   ✅ Schema 완전 일치")

        self.df = df[self.required_features + [self.target]].copy()
        return True

    def _fuzzy_match_columns(self, actual_cols: set, required_cols: set) -> Dict[str, str]:
        """유사한 컬럼명 자동 매핑"""
        mapping = {}

        # 한글 컬럼명 매핑 예시
        korean_to_english = {
            '면적': 'area_sqm',
            '건축년도': 'year_built',
            '층수': 'floor_number',
            '가격': 'market_price',
            '실거래가': 'market_price',
            '거래금액': 'market_price',
            '부채': 'outstanding_debt',
        }

        for actual in actual_cols:
            if actual in required_cols:
                continue
            for korean, english in korean_to_english.items():
                if korean.lower() in actual.lower() or actual.lower() in korean.lower():
                    if english in required_cols:
                        mapping[actual] = english
                        break

        return mapping

    def clean_and_prepare(self) -> pd.DataFrame:
        """데이터 정제 및 준비"""
        print("\n" + "-" * 80)
        print("4️⃣  데이터 정제")
        print("-" * 80)

        df = self.df.copy()

        # 결측치 처리
        missing_pct = (df.isnull().sum() / len(df) * 100)
        if missing_pct.max() > 0:
            print(f"   결측치 감지:")
            for col in missing_pct[missing_pct > 0].index:
                print(f"     - {col}: {missing_pct[col]:.1f}%")
                df[col].fillna(df[col].median(), inplace=True)

        # 이상치 제거
        Q1 = df[self.target].quantile(0.25)
        Q3 = df[self.target].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = ((df[self.target] < lower_bound) | (df[self.target] > upper_bound)).sum()
        if outliers > 0:
            print(f"   이상치 {outliers}개 제거 (IQR 방식)")
            df = df[(df[self.target] >= lower_bound) & (df[self.target] <= upper_bound)]

        # 데이터 타입 정규화
        for col in self.required_features + [self.target]:
            df[col] = df[col].astype(float)

        print(f"   ✅ 최종: {len(df)}행 × {len(df.columns)}컬럼")
        print(f"   타겟 범위: {df[self.target].min():.0f} ~ {df[self.target].max():.0f}")

        return df

    def analyze_signal(self, df: pd.DataFrame) -> None:
        """Feature-Target 상관 분석 (신호 감지)"""
        print("\n" + "-" * 80)
        print("5️⃣  신호 분석 (Feature-Target 상관계수)")
        print("-" * 80)

        correlations = {}
        for feature in self.required_features:
            corr = df[feature].corr(df[self.target])
            correlations[feature] = corr

        sorted_corr = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)

        print(f"\n   상위 5개 강한 상관:")
        for i, (feat, corr) in enumerate(sorted_corr[:5], 1):
            strength = "✅ 강함" if abs(corr) > 0.3 else "⚠️  약함" if abs(corr) > 0.1 else "❌ 매우약함"
            print(f"   {i}. {feat:20s}: {corr:+.4f}  {strength}")

        max_corr = max(abs(c) for _, c in sorted_corr)
        if max_corr < 0.1:
            print(f"\n   ⚠️  경고: 최대 상관 {max_corr:.4f} - 데이터 신호가 매우 약함")
            print(f"   💡 LG 외장하드의 실제 부동산 데이터와 비교 필요")
        elif max_corr < 0.5:
            print(f"\n   ⚠️  주의: 최대 상관 {max_corr:.4f} - 부동산 데이터치고 약함")
        else:
            print(f"\n   ✅ 양호: 최대 상관 {max_corr:.4f} - 정상 부동산 데이터")

        # JSON 저장
        corr_json = OUTPUT_DIR / "correlation_analysis.json"
        json.dump(correlations, open(corr_json, 'w'), indent=2, ensure_ascii=False)
        print(f"\n   📄 저장: {corr_json.name}")

    def run(self) -> pd.DataFrame:
        """전체 파이프라인 실행"""
        # 1. 외장하드 시도
        df = self.load_from_external_drive()

        # 2. 실패 시 폴백
        if df is None:
            df = self.load_synthetic_fallback()

        # 3. Schema 검증
        self.validate_schema(df)

        # 4. 정제
        df = self.clean_and_prepare()

        # 5. 신호 분석
        self.analyze_signal(df)

        # 6. 저장
        output_path = OUTPUT_DIR / f"real_estate_data_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(output_path, index=False)

        print("\n" + "=" * 80)
        print(f"✅ 데이터 로드 완료")
        print(f"   저장 위치: {output_path.name}")
        print(f"   행 수: {len(df)}")
        print(f"   컬럼: {len(df.columns)}")
        print("=" * 80)

        return df

if __name__ == "__main__":
    loader = RealEstateDataLoader(REQUIRED_FEATURES, TARGET_COLUMN)
    df_real = loader.run()
