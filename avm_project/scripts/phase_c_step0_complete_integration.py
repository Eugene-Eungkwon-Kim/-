#!/usr/bin/env python3
"""
Phase C Step 0 - Complete Integration
D드라이브 → Vworld → Opinet (완전 자동화)
"""

import pandas as pd
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))


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


def phase_c_step0_complete(
    vworld_api_key: str = "50D9ECCF-3977-37F1-B323-4997BEAAE387",
    opinet_api_key: str = "F260619859",
    manual_path: Optional[str] = None,
    enable_vworld: bool = True,
    enable_opinet: bool = True
) -> Tuple[pd.DataFrame, str]:
    """
    Phase C Step 0 - Complete Integration
    D드라이브 → Vworld → Opinet

    Args:
        vworld_api_key: Vworld API 키
        opinet_api_key: Opinet API 키
        manual_path: 수동 파일 경로
        enable_vworld: Vworld 강화 활성화
        enable_opinet: Opinet 강화 활성화

    Returns:
        (강화된 데이터프레임, 저장 경로)
    """

    print("\n" + "="*80)
    print("📂 Phase C - Step 0 Complete Integration")
    print("   D드라이브 → Vworld → Opinet (완전 자동화)")
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

                    for i, (file_path, size) in enumerate(csv_files[:3], 1):
                        print(f"      {i}. {os.path.basename(file_path)} ({size:.1f}MB)")

                    csv_path = csv_files[0][0]
                    print(f"\n   ✅ 선택: {csv_path}")
                    break
        else:
            print("   ⚠️ 외장 드라이브 없음")

    if not csv_path or not os.path.exists(csv_path):
        default_path = "avm_project/data/raw/real_estate_2024.csv"
        if os.path.exists(default_path):
            csv_path = default_path
            print(f"   ✅ 기본 파일 사용: {csv_path}")
        else:
            return None, None

    # 데이터 로드
    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"\n✅ 파일 로드 완료: {len(df)}행 × {len(df.columns)}컬럼")

    # Step 1: Vworld 강화
    if enable_vworld and '지역' in df.columns:
        print(f"\n🗺️  [Step 1] Vworld 데이터 강화 중...")

        try:
            from vworld_data_collector import VworldDataCollector

            collector = VworldDataCollector(vworld_api_key)

            if collector.validate_api_key():
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

            else:
                print("   ⚠️ Vworld API 키 무효. 스킵.")

        except Exception as e:
            print(f"   ⚠️ Vworld 강화 실패: {e}")

    # Step 2: Opinet 강화
    if enable_opinet and '위도' in df.columns and '경도' in df.columns:
        print(f"\n⛽ [Step 2] Opinet 데이터 강화 중...")

        try:
            from opinet_data_collector import OpimetDataCollector

            collector = OpimetDataCollector(opinet_api_key)

            print(f"   검색 반경: 2000m")

            nearby_stats = []
            success_count = 0

            for i, row in df.iterrows():
                lat = row['위도']
                lon = row['경도']

                if pd.isna(lat) or pd.isna(lon):
                    nearby_stats.append({
                        'nearby_gas_stations': None,
                        'avg_gas_price': None,
                        'min_gas_price': None,
                        'max_gas_price': None,
                        'gas_station_density': None
                    })
                    continue

                try:
                    stats = collector.calculate_nearby_gas_stations(lat, lon)
                    nearby_stats.append({
                        'nearby_gas_stations': stats['nearby_count'],
                        'avg_gas_price': stats['avg_price'],
                        'min_gas_price': stats['min_price'],
                        'max_gas_price': stats['max_price'],
                        'gas_station_density': stats['station_density']
                    })
                    success_count += 1

                    if (i + 1) % 500 == 0 or (i + 1) == len(df):
                        print(f"   [{i+1}/{len(df)}] {success_count} 성공")

                except Exception as e:
                    nearby_stats.append({
                        'nearby_gas_stations': None,
                        'avg_gas_price': None,
                        'min_gas_price': None,
                        'max_gas_price': None,
                        'gas_station_density': None
                    })

            stats_df = pd.DataFrame(nearby_stats)
            df = pd.concat([df, stats_df], axis=1)

            print(f"\n   ✅ Opinet 강화 완료: {success_count}행")
            print(f"      추가 컬럼: 5개 (nearby_gas_stations, avg_gas_price, ...)")

        except Exception as e:
            print(f"   ⚠️ Opinet 강화 실패: {e}")

    # 최종 저장
    output_path = "avm_project/data/raw/real_estate_2024.csv"
    df.to_csv(output_path, index=False, encoding='utf-8')

    print(f"\n" + "="*80)
    print("💾 최종 데이터 저장")
    print("="*80)
    print(f"   파일: {output_path}")
    print(f"   행: {len(df)}")
    print(f"   컬럼: {len(df.columns)}")

    print("\n" + "="*80)
    print("✅ Phase C - Step 0 Complete Integration 완료")
    print("="*80)
    print("\n📊 최종 컬럼 구성:")
    print(f"   기본: 거래금액, 거래일, 면적, 지역, 건축년도, ...")
    print(f"   Vworld: 위도, 경도")
    print(f"   Opinet: nearby_gas_stations, avg_gas_price, min_gas_price, max_gas_price, gas_station_density")
    print(f"\n   총 {len(df.columns)}개 컬럼")

    return df, output_path


if __name__ == "__main__":
    df, output_path = phase_c_step0_complete()

    if df is not None:
        print(f"\n✅ 다음 단계: Phase C - Step 2 (데이터 검증)")
