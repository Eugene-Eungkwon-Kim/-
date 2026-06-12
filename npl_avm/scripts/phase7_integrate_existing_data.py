#!/usr/bin/env python3
"""
Phase B-2: 기존 데이터 통합 스크립트
목표: RTMS (158K) + 경기도 (206K) + 서울 (?) = 통합 마트 생성

입력:
  1. loan4u_rtms_comparable_mart.duckdb (RTMS 마트, 158,780건)
  2. data_go_kr_filedata_sidecar.duckdb (경기도 아파트, 206,058건)

출력:
  rtms_extended_v2.duckdb (통합, ~360K건)
"""

import sys
from pathlib import Path
import logging
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
RTMS_PATH = r"D:\loan4u_avm_data\loan4u_working_db\db\loan4u_rtms_comparable_mart.duckdb"
PUBLIC_PATH = r"D:\loan4u_avm_data\data_go_kr\filedata\db\data_go_kr_filedata_sidecar.duckdb"
OUTPUT_PATH = project_root / "data" / "rtms_extended_v2.duckdb"


def main():
    logger.info("="*70)
    logger.info("PHASE B-2: 기존 데이터 통합")
    logger.info("="*70)

    # 1. RTMS 마트 로드
    logger.info("\n[1/5] RTMS 마트 로드 (158K)")
    rtms_con = duckdb.connect(RTMS_PATH, read_only=True)
    rtms_df = rtms_con.execute("SELECT * FROM rtms_comparable_mart").fetchdf()
    logger.info(f"  로드됨: {len(rtms_df):,} 건, 컬럼: {list(rtms_df.columns)[:10]}")

    # 2. 경기도 아파트 로드
    logger.info("\n[2/5] 경기도 아파트 거래 로드 (206K)")
    public_con = duckdb.connect(PUBLIC_PATH, read_only=True)
    gyeonggi_df = public_con.execute(
        "SELECT * FROM gyeonggi_transaction_observations WHERE asset_type_hint = 'APT'"
    ).fetchdf()
    logger.info(f"  로드됨: {len(gyeonggi_df):,} 건, 컬럼: {list(gyeonggi_df.columns)[:10]}")

    # 3. 경기도 데이터 정규화
    logger.info("\n[3/5] 경기도 데이터 정규화")
    gyeonggi_df['source'] = 'DATA_GO_KR_GYEONGGI'

    # contract_ym이 있으면 deal_ym으로 변환, 없으면 NULL
    if 'contract_ym' in gyeonggi_df.columns:
        gyeonggi_df['deal_ym'] = gyeonggi_df['contract_ym'].fillna(0).astype(int)
    else:
        gyeonggi_df['deal_ym'] = np.nan

    # 필수 컬럼만 선택 (RTMS와 호환)
    required_cols = ['complex_or_building_name', 'exclusive_area_sqm', 'trade_amount_text', 'source']
    available_cols = [c for c in required_cols if c in gyeonggi_df.columns]
    gyeonggi_subset = gyeonggi_df[available_cols + ['deal_ym', 'address_text']].copy()

    logger.info(f"  정규화 완료: {len(gyeonggi_subset):,} 건")
    logger.info(f"  deal_ym 채우기 완료: {gyeonggi_subset['deal_ym'].notna().sum():,} 건")

    # 4. 통합 (중복 제거)
    logger.info("\n[4/5] 데이터 통합 (중복 제거)")

    # RTMS: source 추가
    rtms_df['source'] = 'RTMS_ORIGINAL'
    rtms_df['address_text'] = rtms_df.get('jibun', '')
    rtms_df['complex_or_building_name'] = rtms_df.get('complex_name_norm', '')

    # 공통 컬럼만 추출
    common_cols = ['complex_or_building_name', 'deal_ym', 'address_text', 'source']
    rtms_merged = rtms_df[[c for c in common_cols if c in rtms_df.columns]].copy()
    gyeonggi_merged = gyeonggi_subset[common_cols].copy()

    # concat
    combined = pd.concat([rtms_merged, gyeonggi_merged], ignore_index=True)

    # 중복 제거 (단지명 + 월 + 주소)
    before = len(combined)
    combined_dedup = combined.drop_duplicates(
        subset=['complex_or_building_name', 'deal_ym', 'address_text'],
        keep='first'
    )
    after = len(combined_dedup)

    logger.info(f"  RTMS: {len(rtms_merged):,}")
    logger.info(f"  경기도: {len(gyeonggi_merged):,}")
    logger.info(f"  합계: {before:,}")
    logger.info(f"  중복 제거 후: {after:,} (제거됨: {before - after:,})")

    # 5. DuckDB로 저장
    logger.info("\n[5/5] DuckDB로 저장")
    output_con = duckdb.connect(str(OUTPUT_PATH))
    output_con.register("temp_combined", combined_dedup)
    output_con.execute("CREATE TABLE rtms_extended AS SELECT * FROM temp_combined")
    output_con.close()

    logger.info(f"  저장 완료: {OUTPUT_PATH}")

    # 6. 검증
    logger.info("\n[검증]")
    verify_con = duckdb.connect(str(OUTPUT_PATH), read_only=True)
    verify_result = verify_con.execute("SELECT COUNT(*) FROM rtms_extended").fetchone()
    logger.info(f"  최종 행 수: {verify_result[0]:,}")

    by_source = verify_con.execute(
        "SELECT source, COUNT(*) FROM rtms_extended GROUP BY 1"
    ).fetchall()
    for src, cnt in by_source:
        logger.info(f"    - {src}: {cnt:,}")

    verify_con.close()

    logger.info("\n" + "="*70)
    logger.info("✅ Phase B-2 완료!")
    logger.info("="*70)
    logger.info(f"\n다음: Phase B-3 성과 측정")
    logger.info(f"  - T1 MAPE 재측정")
    logger.info(f"  - ±3% 달성률 재측정")


if __name__ == "__main__":
    main()
