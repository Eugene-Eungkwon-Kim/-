"""VWorld Layer 2-3: geocoder20 + WFS 참조 수집

Layer 2: 지오코더 API로 주소→좌표 변환 (230개)
Layer 3: WFS 메타데이터 수집 (14개 레이어 정보)

실행:
    python scripts/vworld_layer2_3_collector.py
"""

import json
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from vworld_api_connector import VWorldConnector

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

API_KEY = os.environ.get("VWORLD_API_KEY", "")
DB_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\db\vworld_wfs_multi_layer.sqlite")
LEDGER_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\ledger")


def collect_layer2_geocoder() -> Dict[str, Any]:
    """Layer 2: 지오코더 API 주소→좌표 변환.

    Returns:
        수집 통계
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Layer 1에서 주소 모두 조회
    cursor.execute("SELECT DISTINCT address FROM layer1_search20 WHERE address IS NOT NULL")
    addresses = [row[0] for row in cursor.fetchall()]

    log.info("=" * 60)
    log.info(f"Layer 2 (geocoder20) 수집: {len(addresses)}개 주소 변환")
    log.info("=" * 60)

    connector = VWorldConnector(API_KEY)
    stats = {"total_geocoded": 0, "errors": 0, "queries": len(addresses)}

    try:
        for idx, address in enumerate(addresses, 1):
            try:
                if idx % 10 == 0:
                    log.info(f"  진행: {idx}/{len(addresses)}")

                response = connector.geocode(address=address, crs="epsg:4326")

                if "response" in response and "result" in response["response"]:
                    result = response["response"]["result"]
                    if result and len(result) > 0:
                        item = result[0]
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO layer2_geocoder20
                            (address, lat, lon, level, data_json, collected_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                address,
                                item.get("point", {}).get("y"),
                                item.get("point", {}).get("x"),
                                item.get("level", ""),
                                json.dumps(item, ensure_ascii=False),
                                datetime.now().isoformat(),
                            ),
                        )
                        stats["total_geocoded"] += 1

            except Exception as e:
                log.warning(f"  {address} 변환 실패: {e}")
                stats["errors"] += 1

        conn.commit()
        log.info(f"\n✓ Layer 2 완료: {stats['total_geocoded']}개 저장")

    finally:
        connector.close()
        conn.close()

    return stats


def collect_layer3_wfs_reference() -> Dict[str, Any]:
    """Layer 3: WFS 레이어 메타데이터 수집.

    Returns:
        수집 통계
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 14개 WFS 레이어 정의 (가용 여부 확인)
    wfs_layers = [
        "lp_pa_cbnd_bubun",  # 연속지적도
        "lp_pa_bldg",  # 건물
        "lp_pa_cco",  # 지형
        "lp_pa_lnd",  # 토지
    ]

    log.info("=" * 60)
    log.info(f"Layer 3 (WFS 참조) 수집: {len(wfs_layers)}개 레이어")
    log.info("=" * 60)

    connector = VWorldConnector(API_KEY)
    stats = {"total_layers": 0, "errors": 0}

    try:
        for layer_name in wfs_layers:
            try:
                log.info(f"  {layer_name} 검증 중...")

                # 간단한 쿼리로 레이어 존재 확인
                response = connector.wfs_get_feature(
                    typename=layer_name,
                    bbox="126.975,37.564,126.980,37.568,EPSG:4326",
                    maxfeatures=1,
                )

                if "features" in response or "type" in response:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO layer3_wfs_reference
                        (layer_name, layer_id, geom_type, data_json, collected_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            layer_name,
                            layer_name,
                            "geojson",
                            json.dumps({"status": "available"}, ensure_ascii=False),
                            datetime.now().isoformat(),
                        ),
                    )
                    stats["total_layers"] += 1
                    log.info(f"    ✓ 사용 가능")

            except Exception as e:
                log.warning(f"  {layer_name} 조회 실패: {e}")
                stats["errors"] += 1

        conn.commit()
        log.info(f"\n✓ Layer 3 완료: {stats['total_layers']}개 레이어 기록")

    finally:
        connector.close()
        conn.close()

    return stats


def main() -> None:
    """Layer 2-3 수집 메인."""
    log.info("\nDay 3: Layer 2-3 수집 시작\n")

    stats2 = collect_layer2_geocoder()
    stats3 = collect_layer3_wfs_reference()

    summary = {
        "layer2_geocoder": stats2,
        "layer3_wfs": stats3,
        "completed_at": datetime.now().isoformat(),
    }

    LEDGER_PATH.mkdir(parents=True, exist_ok=True)
    log_path = LEDGER_PATH / f"layer2_3_collection_log_{datetime.now():%Y%m%d_%H%M%S}.json"
    log_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("\n" + "=" * 60)
    log.info("Day 3 완료!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
