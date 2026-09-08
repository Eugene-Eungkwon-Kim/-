#!/usr/bin/env python3
"""
Opinet API를 이용한 주유소 정보 및 가격 데이터 수집
Korean Gas Station Price Information via Opinet API
"""

import os
import sys
import requests
import pandas as pd
import json
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.integrations.http_client import (  # noqa: E402
    AuthFetchError,
    SchemaFetchError,
    TransientFetchError,
    get_json_with_retry,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpimetDataCollector:
    """Opinet API를 통한 주유소 정보 및 가격 데이터 수집"""

    def __init__(self, api_key: str):
        """
        Opinet 데이터 수집기 초기화

        Args:
            api_key: Opinet 개발키
        """
        self.api_key = api_key
        self.base_url = "http://www.opinet.co.kr/api/aroundAll.do"
        self.price_url = "http://www.opinet.co.kr/api/avgSido.do"
        self.session = requests.Session()
        self.rate_limit = 0.5
        self.timeout = 10
        # 스키마 오류(응답 구조 변경 등)로 건너뛴 좌표 수 — 인증 오류와 달리
        # 실행을 막지는 않지만, 끝에 검토가 필요하다고 알려야 한다.
        self.schema_error_count = 0

    def get_nearby_gas_stations(
        self,
        latitude: float,
        longitude: float,
        radius: int = 2000
    ) -> List[Dict]:
        """
        좌표 주변 주유소 정보 조회

        Args:
            latitude: 위도
            longitude: 경도
            radius: 검색 반경 (미터, 1000/2000/5000)

        Returns:
            주유소 정보 리스트

        Raises:
            AuthFetchError: 인증/쿼터 오류. 재시도로 해결되지 않으므로
                호출자가 전체 실행을 중단해야 한다.
        """
        params = {
            'code': 'F',
            'out': 'json',
            'lat': latitude,
            'lon': longitude,
            'radius': radius,
            'apikey': self.api_key
        }

        try:
            data = get_json_with_retry(
                self.session, self.base_url, params=params, timeout=self.timeout
            )
        except AuthFetchError:
            raise  # 재시도로 해결 안 됨 — 호출자가 전체 실행을 멈춰야 한다
        except TransientFetchError as e:
            logger.warning(f"주유소 조회 실패(일시적 오류 소진): {e}")
            return []
        except SchemaFetchError as e:
            logger.warning(f"주유소 조회 실패(응답 구조 오류, 검토 필요): {e}")
            self.schema_error_count += 1
            return []
        finally:
            time.sleep(self.rate_limit)

        if 'result' in data and data['result']:
            return data['result']
        return []

    def calculate_nearby_gas_stations(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 2000
    ) -> Dict:
        """
        주변 주유소 통계 계산

        Args:
            latitude: 위도
            longitude: 경도
            radius_meters: 검색 반경

        Returns:
            주유소 통계 정보
        """
        stations = self.get_nearby_gas_stations(latitude, longitude, radius_meters)

        if not stations:
            return {
                'nearby_count': 0,
                'avg_price': None,
                'min_price': None,
                'max_price': None,
                'station_density': None
            }

        prices = []
        for station in stations:
            try:
                price = float(station.get('price', 0))
                if price > 0:
                    prices.append(price)
            except (ValueError, TypeError):
                pass

        result = {
            'nearby_count': len(stations),
            'avg_price': sum(prices) / len(prices) if prices else None,
            'min_price': min(prices) if prices else None,
            'max_price': max(prices) if prices else None,
            'station_density': len(stations) / (3.14159 * (radius_meters/1000)**2) if radius_meters > 0 else 0
        }

        return result

    def enrich_real_estate_data(
        self,
        csv_path: str,
        output_path: str,
        lat_column: str = '위도',
        lon_column: str = '경도'
    ) -> pd.DataFrame:
        """
        부동산 데이터를 주유소 정보로 강화

        Args:
            csv_path: 입력 CSV 파일 경로
            output_path: 출력 CSV 파일 경로
            lat_column: 위도 컬럼명
            lon_column: 경도 컬럼명

        Returns:
            강화된 데이터프레임
        """
        print("\n" + "="*80)
        print("⛽ Opinet를 이용한 부동산 데이터 강화")
        print("="*80)

        df = pd.read_csv(csv_path)
        print(f"\n✅ 데이터 로드: {len(df)}행 × {len(df.columns)}컬럼")

        if lat_column not in df.columns or lon_column not in df.columns:
            print(f"\n⚠️ 위도/경도 컬럼 필요: {lat_column}, {lon_column}")
            return df

        print(f"\n🔍 주유소 정보 수집 중...")
        print(f"   검색 반경: 2000m")

        nearby_stats = []
        success_count = 0

        for i, row in df.iterrows():
            lat = row[lat_column]
            lon = row[lon_column]

            if pd.isna(lat) or pd.isna(lon):
                nearby_stats.append({
                    'nearby_gas_stations': None,
                    'avg_gas_price': None,
                    'min_gas_price': None,
                    'max_gas_price': None,
                    'gas_station_density': None
                })
                continue

            # AuthFetchError(인증/쿼터 오류)는 여기서 잡지 않는다 — 재시도로
            # 해결되지 않으므로 나머지 행을 계속 조회해봐야 의미가 없고,
            # 호출자가 전체 실행을 즉시 중단할 수 있게 그대로 전파한다.
            stats = self.calculate_nearby_gas_stations(lat, lon)
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

        stats_df = pd.DataFrame(nearby_stats)
        df = pd.concat([df, stats_df], axis=1)

        print(f"\n✅ Opinet 강화 완료:")
        print(f"   수집된 행: {success_count}/{len(df)}")
        print(f"   추가 컬럼: 5개")
        if self.schema_error_count:
            print(f"   ⚠️ 검토 필요(응답 구조 오류로 건너뜀): {self.schema_error_count}건")

        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n💾 저장 완료: {output_path}")
        print(f"   최종 크기: {len(df)}행 × {len(df.columns)}컬럼")

        return df

    def validate_api_key(self) -> bool:
        """API 키 유효성 확인"""
        try:
            stations = self.get_nearby_gas_stations(37.5, 127.0, 1000)
            return len(stations) > 0
        except Exception:
            return False

    def test_collection(self) -> bool:
        """데이터 수집 테스트"""
        print("\n" + "="*80)
        print("🧪 Opinet API 테스트")
        print("="*80)

        print("\n1️⃣ API 키 검증 중...")
        if self.validate_api_key():
            print("   ✅ API 키 유효")
        else:
            print("   ⚠️ API 키 검증 실패 (네트워크 문제일 수 있음)")

        print("\n2️⃣ 주유소 조회 테스트")
        test_coords = [
            (37.4979, 127.0276, "서울 강남"),
            (35.1796, 129.0756, "부산"),
            (35.8703, 128.5905, "대구"),
        ]

        success = 0
        for lat, lon, name in test_coords:
            stations = self.get_nearby_gas_stations(lat, lon)
            if stations:
                print(f"   ✅ {name}: {len(stations)}개 주유소")
                success += 1
            else:
                print(f"   ⚠️ {name}: 조회 결과 없음")

        return success >= 1


def main():
    """메인 실행 함수"""

    api_key = os.environ.get("OPINET_API_KEY")
    if not api_key:
        print("❌ 오류: 환경변수 OPINET_API_KEY 가 설정되어 있지 않습니다.")
        return 1

    collector = OpimetDataCollector(api_key)

    print("="*80)
    print("✅ Opinet 데이터 수집 시작")
    print("="*80)

    try:
        if not collector.test_collection():
            print("\n⚠️ 테스트 실패. 계속 진행합니다.")

        input_file = "avm_project/data/raw/real_estate_2024.csv"
        output_file = "avm_project/data/raw/real_estate_2024_opinet_enriched.csv"

        if not Path(input_file).exists():
            print(f"\n❌ 입력 파일 없음: {input_file}")
            return 1

        enriched_df = collector.enrich_real_estate_data(input_file, output_file)

        print("\n" + "="*80)
        print("📊 강화 결과 요약")
        print("="*80)
        print(f"\n강화된 데이터:")
        print(f"   행: {len(enriched_df)}")
        print(f"   컬럼: {len(enriched_df.columns)}")
        print(f"   주유소 정보 있는 행: {enriched_df['nearby_gas_stations'].notna().sum()}")

        print("\n✅ Opinet 데이터 수집 완료")
        if collector.schema_error_count:
            return 3  # 응답 구조 오류 있었음 — 검토 필요 (CLAUDE.md 종료코드 규약)
        return 0

    except AuthFetchError as e:
        print(f"\n❌ 인증/쿼터 오류: {e}")
        print("재시도로 해결되지 않습니다 — API 키 또는 호출량 한도를 확인하세요.")
        return 2

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
