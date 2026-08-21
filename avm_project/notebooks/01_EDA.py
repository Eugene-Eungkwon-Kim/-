"""
01_EDA.py - 탐색적 데이터 분석 (Exploratory Data Analysis)
AVM Sample Data Exploratory Analysis

Author: AI Assistant
Date: 2026-06-09
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/user/-')

from avm_project.scripts.data_preprocessing import DataPreprocessor

# 데이터 로드
preprocessor = DataPreprocessor(
    data_dir='avm_project/data',
    output_dir='avm_project/output'
)
raw_data = preprocessor.load_data('raw/sample_npl_data.csv')

# 기본 통계
print("\n" + "="*70)
print("📊 AVM 샘플 데이터 탐색적 분석 (EDA)")
print("="*70)

print("\n1️⃣ 데이터 기본 정보")
print("-" * 70)
print(f"Shape: {raw_data.shape}")
print(f"Memory Usage: {raw_data.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
print(f"\nData Types:\n{raw_data.dtypes}")

print("\n2️⃣ 결측값 분석")
print("-" * 70)
missing = raw_data.isnull().sum()
if missing.sum() == 0:
    print("✅ 결측값 없음")
else:
    print(missing[missing > 0])

print("\n3️⃣ 수치형 데이터 통계")
print("-" * 70)
print(raw_data.describe().T[['count', 'mean', 'std', 'min', 'max']])

print("\n4️⃣ 범주형 데이터 분포")
print("-" * 70)
for col in raw_data.select_dtypes(include='object').columns:
    print(f"\n{col}:")
    print(raw_data[col].value_counts().head(5))

print("\n5️⃣ 타겟 변수 (final_sale_price) 분석")
print("-" * 70)
print(f"최솟값: ₩{raw_data['final_sale_price'].min():,.0f}")
print(f"최댓값: ₩{raw_data['final_sale_price'].max():,.0f}")
print(f"평균: ₩{raw_data['final_sale_price'].mean():,.0f}")
print(f"중앙값: ₩{raw_data['final_sale_price'].median():,.0f}")
print(f"표준편차: ₩{raw_data['final_sale_price'].std():,.0f}")

print("\n6️⃣ 상관관계 분석 (top 5)")
print("-" * 70)
numeric_data = raw_data.select_dtypes(include=[np.number])
correlations = numeric_data.corr()['final_sale_price'].sort_values(ascending=False)
print(correlations.head(10).to_string())

print("\n7️⃣ 이상값 감지 (IQR 방법)")
print("-" * 70)
preprocessor.explore_data()
outliers = preprocessor.detect_outliers(method='iqr', threshold=1.5)
print(f"총 이상값 개수: {sum(v['count'] for v in outliers.values())}")
for col, info in list(outliers.items())[:5]:
    if info['count'] > 0:
        print(f"  {col}: {info['count']} ({info['percentage']:.2f}%)")

print("\n✅ EDA 분석 완료")
print("="*70)
