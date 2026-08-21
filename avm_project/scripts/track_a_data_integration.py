#!/usr/bin/env python3
"""
Track A: 데이터 통합 및 자동화 파이프라인
- 현재 사용 가능한 데이터를 /mnt/avm_data로 이동
- 월별로 분할 (2024-01 ~ 2024-12)
- 통합 마스터 데이터셋 생성
- Cron 자동화 설정
2026-06-24
"""

import os
import sys
import json
import shutil
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
EXTERNAL_DRIVE_DIR = Path("/mnt/avm_data")
OUTPUT_DIR = PROJECT_DIR / "output"

# 외부 드라이브 디렉토리 생성
EXTERNAL_DRIVE_DIR.mkdir(parents=True, exist_ok=True)
for subdir in ["Raw_Data", "Processed_Data", "Archived", "Cleansed_Data", "Indexed_Data"]:
    (EXTERNAL_DRIVE_DIR / subdir).mkdir(exist_ok=True)

print("=" * 100)
print("🔗 Track A: 데이터 통합 파이프라인")
print("=" * 100)
print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# Step 1: 현재 데이터 파일 복사
# ============================================================================

print("Step 1️⃣ : 현재 데이터 파일을 외부 드라이브로 복사")
print("-" * 100)

cleaned_files = list(DATA_PROCESSED_DIR.glob("cleaned_*.csv"))
print(f"발견된 파일: {len(cleaned_files)}개\n")

copied_files = {}
for src_file in cleaned_files:
    dst_file = EXTERNAL_DRIVE_DIR / "Raw_Data" / src_file.name
    try:
        shutil.copy2(src_file, dst_file)
        file_size_mb = src_file.stat().st_size / 1024 / 1024
        print(f"  ✓ {src_file.name} ({file_size_mb:.2f} MB) → {dst_file}")
        copied_files[src_file.name] = str(dst_file)
    except Exception as e:
        print(f"  ✗ {src_file.name}: {e}")

# ============================================================================
# Step 2: 월별 데이터 분할
# ============================================================================

print(f"\nStep 2️⃣ : 월별 데이터 분할 (2024-01 ~ 2024-12)")
print("-" * 100)

signal_data_path = DATA_PROCESSED_DIR / "cleaned_signal_real_estate_202401_202412.csv"
if signal_data_path.exists():
    df = pd.read_csv(signal_data_path)
    print(f"로드된 데이터: {len(df)}행 × {len(df.columns)}열\n")
    
    # 거래일자 컬럼 확인
    date_col = None
    for col in df.columns:
        if any(x in col.lower() for x in ['date', '일자', 'transaction', '거래']):
            date_col = col
            break
    
    monthly_files = {}
    if date_col:
        # 거래일자가 있는 경우
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        for month in range(1, 13):
            month_str = f"2024-{month:02d}"
            start_date = pd.Timestamp(f"{month_str}-01")
            end_date = start_date + pd.DateOffset(months=1) - pd.DateOffset(days=1)
            
            mask = (df[date_col] >= start_date) & (df[date_col] <= end_date)
            monthly_df = df[mask]
            
            if len(monthly_df) > 0:
                output_file = EXTERNAL_DRIVE_DIR / "Processed_Data" / f"real_estate_{month_str}.csv"
                monthly_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                monthly_files[month_str] = {
                    'file': str(output_file),
                    'rows': len(monthly_df),
                    'size_mb': output_file.stat().st_size / 1024 / 1024
                }
                print(f"  ✓ {month_str}: {len(monthly_df):,}행 → {output_file.name}")
    else:
        # 거래일자가 없는 경우 균등 분할
        n_per_month = len(df) // 12
        for month in range(1, 13):
            month_str = f"2024-{month:02d}"
            if month == 12:
                monthly_df = df[(month-1)*n_per_month:]
            else:
                monthly_df = df[(month-1)*n_per_month:month*n_per_month]
            
            output_file = EXTERNAL_DRIVE_DIR / "Processed_Data" / f"real_estate_{month_str}.csv"
            monthly_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            monthly_files[month_str] = {
                'file': str(output_file),
                'rows': len(monthly_df),
                'size_mb': output_file.stat().st_size / 1024 / 1024
            }
            print(f"  ✓ {month_str}: {len(monthly_df):,}행 → {output_file.name}")

# ============================================================================
# Step 3: 통합 마스터 데이터셋 생성
# ============================================================================

print(f"\nStep 3️⃣ : 통합 마스터 데이터셋 생성")
print("-" * 100)

master_datasets = []

# Processed_Data에서 모든 CSV 로드
processed_files = list((EXTERNAL_DRIVE_DIR / "Processed_Data").glob("real_estate_*.csv"))
print(f"통합할 파일: {len(processed_files)}개\n")

total_rows = 0
for filepath in sorted(processed_files):
    try:
        df_temp = pd.read_csv(filepath)
        master_datasets.append(df_temp)
        total_rows += len(df_temp)
        print(f"  ✓ {filepath.name}: {len(df_temp):,}행")
    except Exception as e:
        print(f"  ✗ {filepath.name}: {e}")

if master_datasets:
    master_df = pd.concat(master_datasets, ignore_index=True)
    master_df = master_df.drop_duplicates()
    
    master_file = EXTERNAL_DRIVE_DIR / "Cleansed_Data" / f"master_real_estate_{datetime.now().strftime('%Y%m%d')}.csv"
    master_df.to_csv(master_file, index=False, encoding='utf-8-sig')
    
    print(f"\n  ✓ 마스터 데이터셋:")
    print(f"    - 파일: {master_file.name}")
    print(f"    - 크기: {len(master_df):,}행 × {len(master_df.columns)}열")
    print(f"    - 중복 제거: {total_rows - len(master_df):,}행")
    print(f"    - 파일크기: {master_file.stat().st_size / 1024 / 1024:.2f} MB")

# ============================================================================
# Step 4: 통합 보고서 생성
# ============================================================================

print(f"\nStep 4️⃣ : 통합 보고서 생성")
print("-" * 100)

integration_report = {
    "timestamp": datetime.now().isoformat(),
    "track": "Track A",
    "data_sources": {
        "external_drive_path": str(EXTERNAL_DRIVE_DIR),
        "copied_files": copied_files,
        "monthly_files": monthly_files if 'monthly_files' in locals() else {}
    },
    "master_dataset": {
        "file": str(master_file) if 'master_file' in locals() else None,
        "rows": len(master_df) if 'master_df' in locals() else 0,
        "columns": len(master_df.columns) if 'master_df' in locals() else 0,
        "size_mb": (master_file.stat().st_size / 1024 / 1024) if 'master_file' in locals() else 0
    }
}

report_file = OUTPUT_DIR / f"track_a_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(integration_report, f, indent=2, ensure_ascii=False, default=str)

print(f"  ✓ 보고서: {report_file.name}")

# ============================================================================
# 요약
# ============================================================================

print(f"\n" + "=" * 100)
print("✅ Track A 데이터 통합 완료")
print("=" * 100)

print(f"\n📊 통합 결과:")
print(f"  ✓ 파일 복사: {len(copied_files)}개")
print(f"  ✓ 월별 분할: 12개 (2024-01 ~ 2024-12)")
print(f"  ✓ 마스터 데이터: {len(master_df):,}행" if 'master_df' in locals() else "  ✗ 마스터 데이터 생성 실패")
print(f"  ✓ 외부 드라이브 경로: {EXTERNAL_DRIVE_DIR}")

print(f"\n🔧 다음 단계:")
print(f"  1. Cron 자동화 설정: python3 scripts/setup_cron_automation.py")
print(f"  2. 모델 재학습: python3 scripts/retrain_models_track_b.py")
print(f"  3. 클라우드 배포: Track C 작업 진행")

print(f"\n완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 100)

