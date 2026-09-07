#!/usr/bin/env python3
"""
Phase C Step 0 - Enhanced: D드라이브 데이터 읽기 + Vworld 강화
"""

import pandas as pd
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from vworld_data_collector import VworldDataCollector


def detect_external_drives():
    """외장 드라이브 감지"""
    drives = []

    if os.name == 'nt':
        import string
        for drive in string.ascii_uppercase:
            path = f"{drive}:\\"
            if os.path.exists(path):
                drives.append(path)
    else:
        for mount_point in ['/Volumes', '/media', '/mnt']:
            if os.path.exists(mount_point):
                for item in os.listdir(mount_point):
                    full_path = os.path.join(mount_point, item)
                    if os.path.isdir(full_path):
                        drives.append(full_path)

    return drives


def search_csv_files(root_path: str) -> list:
    """CSV 파일 검색"""
    csv_files = []

    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith('.csv'):
                full_path = os.path.join(root, file)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                csv_files.append((full_path, size_mb))

    return sorted(csv_files, key=lambda x: x[1], reverse=True)


def phase_c_step0_enhanced(
    vworld_api_key: str = os.environ.get("VWORLD_API_KEY", ""),
    manual_path: Optional[str] = None,
    enable_vworld: bool = True
) -> Tuple[pd.DataFrame, str]:
    """
    Phase C Step 0 Enhanced: D드라이브 읽기 + Vworld 강화

    Args:
        vworld_api_key: Vworld API 키
        manual_path: 수동 파일 경로 (자동 감지 스킵)
        enable_vworld: Vworld 강화 활성화 여부

    Returns:
        (강화된 데이터프레임, 저장 경로)
    """

    print("\n" + "="*80)
    print("📂 Phase C - Step 0 Enhanced")
    print("   D드라이브 데이터 읽기 + Vworld 강화")
    print("="*80)

    csv_path = None

    if manual_path and os.path.exists(manual_path):
        csv_path = manual_path
        print(f"\n✅ 수동 경로 사용: {manual_path}")

    else:
        print("\n🔍 외장 드라이브 검색 중...")
        drives = detect_external_drives()

        if drives:
            print(f"   발견된 드라이브: {drives}")

            for drive in drives:
                print(f"\n   📂 {drive} 검색 중...")
                csv_files = search_csv_files(drive)

                if csv_files:
                    print(f"   발견된 CSV 파일: {len(csv_files)}개")

                    for i, (file_path, size) in enumerate(csv_files[:5], 1):
                        print(f"      {i}. {os.path.basename(file_path)} ({size:.1f}MB)")

                    csv_path = csv_files[0][0]
                    print(f"\n   ✅ 선택: {csv_path}")
                    break
        else:
            print("   ⚠️ 외장 드라이브 없음")

    if not csv_path or not os.path.exists(csv_path):
        print(f"\n❌ CSV 파일을 찾을 수 없습니다.")
        print(f"   기본 경로 시도: avm_project/data/raw/real_estate_2024.csv")

        default_path = "avm_project/data/raw/real_estate_2024.csv"
        if os.path.exists(default_path):
            csv_path = default_path
            print(f"   ✅ 기본 파일 사용: {csv_path}")
        else:
            return None, None

    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"\n✅ 파일 로드 완료: {len(df)}행 × {len(df.columns)}컬럼")
    print(f"   파일 경로: {csv_path}")
    print(f"   컬럼: {', '.join(df.columns[:5])}...")

    if enable_vworld and '지역' in df.columns:
        print(f"\n🗺️  Vworld 데이터 강화 중...")

        try:
            collector = VworldDataCollector(vworld_api_key)

            if not collector.validate_api_key():
                print("   ⚠️ Vworld API 키 무효. 강화 스킵.")
            else:
                unique_regions = df['지역'].dropna().unique()
                print(f"   지역 수: {len(unique_regions)}개")

                region_coords = {}
                success_count = 0

                for i, region in enumerate(unique_regions, 1):
                    region_str = str(region).strip()
                    lat, lon = collector.address_to_coordinate(region_str)

                    if lat is not None and lon is not None:
                        region_coords[region] = (lat, lon)
                        success_count += 1

                    if i % 5 == 0 or i == len(unique_regions):
                        print(f"   [{i}/{len(unique_regions)}] {success_count} 성공")

                df['위도'] = df['지역'].map(
                    lambda x: region_coords.get(x, (None, None))[0] if pd.notna(x) else None
                )
                df['경도'] = df['지역'].map(
                    lambda x: region_coords.get(x, (None, None))[1] if pd.notna(x) else None
                )

                print(f"\n   ✅ Vworld 강화 완료: {df['위도'].notna().sum()}행")
                print(f"      추가 컬럼: 위도, 경도")

        except Exception as e:
            print(f"   ⚠️ Vworld 강화 실패: {e}")

    output_path = "avm_project/data/raw/real_estate_2024.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')

    print(f"\n💾 처리된 데이터 저장: {output_path}")
    print(f"   최종 크기: {len(df)}행 × {len(df.columns)}컬럼")

    print("\n" + "="*80)
    print("✅ Phase C - Step 0 Enhanced 완료")
    print("="*80)

    return df, output_path


if __name__ == "__main__":
    df, output_path = phase_c_step0_enhanced()

    if df is not None:
        print(f"\n📊 데이터 요약:")
        print(df.info())
        print(f"\n✅ 다음 단계: Phase C - Step 2 (데이터 검증)")
