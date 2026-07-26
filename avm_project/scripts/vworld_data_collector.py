#!/usr/bin/env python3
"""
Vworld API를 이용한 부동산 지리정보 데이터 수집
Korean GIS Data Collection via Vworld API
"""

import requests
import pandas as pd
import json
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VworldDataCollector:
    """Vworld API를 통한 부동산 지리정보 데이터 수집"""

    def __init__(self, api_key: str):
        """
        Vworld 데이터 수집기 초기화

        Args:
            api_key: Vworld 개발키
        """
        self.api_key = api_key
        self.base_url = "http://api.vworld.kr/req/data"
        self.address_url = "https://api.vworld.kr/req/address"
        self.session = requests.Session()
        self.rate_limit = 0.3
        self.timeout = 10

    def address_to_coordinate(self, address: str) -> Tuple[Optional[float], Optional[float]]:
        """
        주소를 좌표로 변환 (지오코딩)

        Args:
            address: 주소 (예: "서울시 강남구 테헤란로 427")

        Returns:
            (위도, 경도) 튜플 또는 (None, None)
        """
        try:
            params = {
                'service': 'address',
                'request': 'getcoord',
                'crs': 'EPSG:4326',
                'address': address,
                'format': 'json',
                'errorMessage': 'true',
                'key': self.api_key
            }

            response = self.session.get(
                self.address_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            if data.get('response', {}).get('status') == '200':
                coords = data['response']['result']['point']['coordinates']
                return float(coords[1]), float(coords[0])
            else:
                logger.debug(f"주소 변환 실패: {address}")
                return None, None

        except Exception as e:
            logger.debug(f"지오코딩 오류 ({address}): {e}")
            return None, None

        finally:
            time.sleep(self.rate_limit)

    def get_building_info(self, x: float, y: float) -> Dict:
        """
        좌표 근처 건물 정보 조회

        Args:
            x: 경도 (longitude)
            y: 위도 (latitude)

        Returns:
            건물 정보 딕셔너리
        """
        try:
            params = {
                'service': 'data',
                'request': 'GetFeature',
                'data': 'LT_C_LFAN_B',
                'bbox': f'{x},{y},{x+0.01},{y+0.01}',
                'format': 'json',
                'key': self.api_key
            }

            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.debug(f"건물 정보 조회 오류: {e}")
            return {}

        finally:
            time.sleep(self.rate_limit)

    def enrich_real_estate_data(
        self,
        csv_path: str,
        output_path: str,
        region_column: str = '지역'
    ) -> pd.DataFrame:
        """
        기존 부동산 데이터를 Vworld 정보로 강화

        Args:
            csv_path: 입력 CSV 파일 경로
            output_path: 출력 CSV 파일 경로
            region_column: 지역 정보가 있는 컬럼명

        Returns:
            강화된 데이터프레임
        """
        print("\n" + "="*80)
        print("🗺️  Vworld를 이용한 부동산 데이터 강화")
        print("="*80)

        df = pd.read_csv(csv_path)
        print(f"\n✅ 데이터 로드: {len(df)}행 × {len(df.columns)}컬럼")

        if region_column not in df.columns:
            print(f"\n❌ 오류: '{region_column}' 컬럼 없음")
            return df

        print(f"\n🔄 지역명 → 좌표 변환 중...")

        unique_regions = df[region_column].dropna().unique()
        print(f"   고유 지역: {len(unique_regions)}개")

        region_coords = {}
        success_count = 0

        for i, region in enumerate(unique_regions, 1):
            region_str = str(region).strip()

            lat, lon = self.address_to_coordinate(region_str)

            if lat is not None and lon is not None:
                region_coords[region] = (lat, lon)
                success_count += 1
                status = "✅"
            else:
                status = "⚠️"

            if i % 5 == 0 or i == len(unique_regions):
                print(f"   [{i}/{len(unique_regions)}] {status} {region_str}")

        df['위도'] = df[region_column].map(
            lambda x: region_coords.get(x, (None, None))[0] if pd.notna(x) else None
        )
        df['경도'] = df[region_column].map(
            lambda x: region_coords.get(x, (None, None))[1] if pd.notna(x) else None
        )

        print(f"\n✅ 좌표 변환 완료:")
        print(f"   성공: {success_count}/{len(unique_regions)}")
        print(f"   데이터에 추가된 행: {df['위도'].notna().sum()}")

        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n💾 저장 완료: {output_path}")
        print(f"   최종 컬럼: {len(df.columns)} ({', '.join(df.columns[-2:])} 추가)")

        return df

    def validate_api_key(self) -> bool:
        """
        API 키 유효성 확인

        Returns:
            True if valid, False otherwise
        """
        try:
            result = self.address_to_coordinate("서울시")
            return result[0] is not None
        except Exception:
            return False

    def test_collection(self) -> bool:
        """
        데이터 수집 테스트

        Returns:
            테스트 성공 여부
        """
        print("\n" + "="*80)
        print("🧪 Vworld API 테스트")
        print("="*80)

        # 1. API 키 검증
        print("\n1️⃣ API 키 검증 중...")
        if self.validate_api_key():
            print("   ✅ API 키 유효")
        else:
            print("   ❌ API 키 무효")
            return False

        # 2. 주소 변환 테스트
        print("\n2️⃣ 주소 변환 테스트")
        test_addresses = [
            "서울시 강남구",
            "부산시 해운대구",
            "대구시 중구",
            "인천시 남동구",
        ]

        success = 0
        for addr in test_addresses:
            lat, lon = self.address_to_coordinate(addr)
            if lat and lon:
                print(f"   ✅ {addr}: ({lat:.4f}, {lon:.4f})")
                success += 1
            else:
                print(f"   ❌ {addr}")

        print(f"\n   성공율: {success}/{len(test_addresses)}")

        return success >= 3


def main():
    """메인 실행 함수"""

    api_key = "50D9ECCF-3977-37F1-B323-4997BEAAE387"

    collector = VworldDataCollector(api_key)

    print("="*80)
    print("✅ Vworld 데이터 수집 시작")
    print("="*80)

    if not collector.test_collection():
        print("\n❌ API 테스트 실패. 종료합니다.")
        return False

    input_file = "avm_project/data/raw/real_estate_2024.csv"
    output_file = "avm_project/data/raw/real_estate_2024_vworld_enriched.csv"

    if not Path(input_file).exists():
        print(f"\n⚠️ 입력 파일 없음: {input_file}")
        print("Phase D-1을 먼저 완료하세요.")
        return False

    try:
        enriched_df = collector.enrich_real_estate_data(input_file, output_file)

        print("\n" + "="*80)
        print("📊 강화 결과 요약")
        print("="*80)
        print(f"\n원본 데이터:")
        print(f"   파일: {input_file}")
        print(f"   행: {len(enriched_df)}")
        print(f"   컬럼: {len(enriched_df.columns)-2} → {len(enriched_df.columns)}")

        print(f"\n강화된 데이터:")
        print(f"   파일: {output_file}")
        print(f"   위도 있는 행: {enriched_df['위도'].notna().sum()}")
        print(f"   경도 있는 행: {enriched_df['경도'].notna().sum()}")

        print("\n✅ Vworld 데이터 수집 완료")
        return True

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
