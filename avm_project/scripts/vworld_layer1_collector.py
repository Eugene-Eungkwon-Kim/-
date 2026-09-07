"""VWorld Layer 1: search20 (검색 API 2.0) 데이터 수집

목표: 10,000개 부동산 객체를 검색 API로 수집하여 SQLite에 저장.
쿼리: 서울 주요 지역별 검색 (종로구, 강남구, 서초구, 송파구, 마포구 등)

실행:
    python scripts/vworld_layer1_collector.py
"""

import json
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from vworld_api_connector import VWorldConnector

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

API_KEY = os.environ.get("VWORLD_API_KEY", "")
DB_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\db\vworld_wfs_multi_layer.sqlite")
LEDGER_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\ledger")


def get_search_queries() -> List[str]:
    """검색 쿼리 목록 생성.

    서울 주요 지역별로 검색 쿼리 생성.
    각 구별 1-2개 쿼리로 충분한 데이터 확보 예상.

    Returns:
        검색 쿼리 리스트 (약 50개 → 10,000+ 결과 기대)
    """
    queries = [
        "서울 종로구",
        "서울 종로구 세종대로",
        "서울 강남구",
        "서울 강남구 테헤란로",
        "서울 서초구",
        "서울 서초구 강남대로",
        "서울 송파구",
        "서울 송파구 올림픽로",
        "서울 마포구",
        "서울 마포구 홍익로",
        "서울 영등포구",
        "서울 영등포구 여의도로",
        "서울 동대문구",
        "서울 동대문구 동대문로",
        "서울 중구",
        "서울 중구 을지로",
        "서울 용산구",
        "서울 용산구 한강대로",
        "서울 강동구",
        "서울 강동구 올림픽로",
        "서울 성동구",
        "서울 성동구 왕십리로",
        "서울 광진구",
        "서울 광진구 능동로",
        "서울 노원구",
        "서울 노원구 동부간선도로",
    ]
    return queries


def collect_layer1() -> Dict[str, Any]:
    """Layer 1 데이터 수집 메인 함수.

    Returns:
        수집 통계 (수집 개수, 오류 개수, 소요 시간 등)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stats = {
        "total_collected": 0,
        "total_errors": 0,
        "started_at": datetime.now().isoformat(),
        "queries": len(get_search_queries()),
        "results_per_query": [],
    }

    connector = VWorldConnector(API_KEY)

    try:
        log.info("=" * 60)
        log.info("VWorld Layer 1 (search20) 수집 시작")
        log.info("=" * 60)

        for query_idx, query in enumerate(get_search_queries(), 1):
            try:
                log.info(f"\n[{query_idx}/{len(get_search_queries())}] 검색: {query}")

                response = connector.search(query=query, type="address", category="road")

                # 결과 파싱 및 저장
                if "response" in response and "result" in response["response"]:
                    results = response["response"]["result"]["items"]
                    inserted = 0

                    for item in results:
                        try:
                            # address가 dict인 경우 문자열로 변환
                            addr = item.get("address", "")
                            if isinstance(addr, dict):
                                addr = addr.get("full", "") or addr.get("name", "")

                            point = item.get("point", {})
                            lat = point.get("y") if isinstance(point, dict) else None
                            lon = point.get("x") if isinstance(point, dict) else None

                            cursor.execute(
                                """
                                INSERT OR IGNORE INTO layer1_search20
                                (api_id, name, address, lat, lon, data_json, collected_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    item.get("id", ""),
                                    item.get("name", ""),
                                    addr,
                                    lat,
                                    lon,
                                    json.dumps(item, ensure_ascii=False),
                                    datetime.now().isoformat(),
                                ),
                            )
                            inserted += 1
                        except Exception as e:
                            log.warning(f"아이템 삽입 실패: {e}")
                            stats["total_errors"] += 1

                    conn.commit()
                    stats["total_collected"] += inserted
                    stats["results_per_query"].append(
                        {"query": query, "count": inserted}
                    )
                    log.info(f"  → {inserted}개 저장 완료")

                else:
                    log.warning(f"  → 결과 없음")

            except Exception as e:
                log.error(f"쿼리 실패: {e}")
                stats["total_errors"] += 1

        log.info("\n" + "=" * 60)
        log.info(f"수집 완료: {stats['total_collected']}개 저장, {stats['total_errors']}개 오류")
        log.info("=" * 60)

    finally:
        connector.close()
        conn.close()

    stats["ended_at"] = datetime.now().isoformat()

    # 통계 저장
    LEDGER_PATH.mkdir(parents=True, exist_ok=True)
    log_path = LEDGER_PATH / f"layer1_collection_log_{datetime.now():%Y%m%d_%H%M%S}.json"
    log_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"통계: {log_path}")

    return stats


if __name__ == "__main__":
    collect_layer1()
