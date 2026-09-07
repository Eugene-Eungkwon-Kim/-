#!/usr/bin/env python3
"""
Data.go.kr 실거래 데이터 수집 실행 스크립트
"""

import os
import sys
from pathlib import Path

# 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'scripts'))

from data_collection_handler import KoreanRealEstateDataCollector

# API 키
API_KEY = os.environ.get("DATAGOVKR_API_KEY", "")

def main():
    print("=" * 70)
    print("🚀 Data.go.kr 실거래 데이터 수집 시작")
    print("=" * 70)

    # 수집기 초기화
    collector = KoreanRealEstateDataCollector(
        api_key=API_KEY,
        output_dir='avm_project/data/raw'
    )

    # 실거래 데이터 수집 (2024년 1월~6월)
    print("\n📊 단계 1: 실거래 거래 데이터 수집 중...")
    df_transactions = collector.collect_real_estate_transaction_data(
        start_date='202401',
        end_date='202406'
    )

    if not df_transactions.empty:
        print(f"\n✅ 수집 완료!")
        print(f"   행: {len(df_transactions)}")
        print(f"   컬럼: {list(df_transactions.columns)}")
        return df_transactions
    else:
        print("\n⚠️ 데이터 수집 실패. 다시 시도하세요.")
        return None

if __name__ == "__main__":
    df = main()
