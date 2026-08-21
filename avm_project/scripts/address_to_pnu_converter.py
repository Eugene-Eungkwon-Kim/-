"""주소 → PNU(부동산고유번호) 변환

Layer 8-10 수집에 필요한 주소 → PNU 변환 함수.
공식 주소 API 또는 정제 로직 활용.

실행:
    python scripts/address_to_pnu_converter.py
"""

import sqlite3
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

DB_PATH = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\db\vworld_wfs_multi_layer.sqlite")
JUSO_KEY = "U01TX0FVVEgyMDI2MDcwOTEzMzM0MzExOTY3OTE="


def convert_address_to_pnu(address: str) -> Optional[str]:
    """주소를 PNU로 변환.

    Args:
        address: 부동산 주소

    Returns:
        19자리 PNU 또는 None
    """
    if not address:
        return None

    try:
        # 공식 주소정보제공 API 호출 (도로명주소 조회)
        url = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
        params = {
            "confmKey": JUSO_KEY,
            "currentPage": "1",
            "countPerPage": "1",
            "keyword": address,
            "resultType": "json",
        }

        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            log.warning(f"  API 응답 오류 {resp.status_code}: {address}")
            return None

        result = resp.json()
        if "results" not in result:
            log.warning(f"  API 응답 형식 오류: {address}")
            return None

        juso_result = result["results"]["juso"]
        if not juso_result or len(juso_result) == 0:
            log.debug(f"  조회 결과 없음: {address}")
            return None

        # 첫 번째 결과 사용
        item = juso_result[0]

        # PNU 필드 추출 (admCd: 행정코드, bnMgtSn: 건물관리번호)
        # 행정코드(5자리) + 산림청구분(1자리) + 시군구(1자리) + 지번(6자리 + 부번 4자리)
        if "admCd" in item and "bdMgtSn" in item:
            pnu = item["admCd"] + item["bdMgtSn"]
            if len(pnu) == 19:
                return pnu
            else:
                log.warning(f"  PNU 길이 불일치 ({len(pnu)}): {pnu}")
                return None

        log.debug(f"  PNU 필드 미포함: {address}")
        return None

    except Exception as e:
        log.warning(f"  변환 실패: {address} - {e}")
        return None


def create_pnu_mapping_table() -> None:
    """주소 → PNU 매핑 테이블 생성."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 매핑 테이블 생성
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS address_pnu_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE NOT NULL,
            pnu TEXT,
            converted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
    log.info("✓ PNU 매핑 테이블 생성 완료")


def convert_layer1_addresses() -> Dict[str, Any]:
    """Layer 1 주소를 PNU로 변환 및 저장.

    Returns:
        변환 통계
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Layer 1 주소 조회
    cursor.execute("SELECT DISTINCT address FROM layer1_search20 WHERE address IS NOT NULL")
    addresses = [row[0] for row in cursor.fetchall()]

    log.info("=" * 60)
    log.info(f"주소→PNU 변환 시작: {len(addresses)}개")
    log.info("=" * 60)

    stats = {"total_converted": 0, "failed": 0, "queries": len(addresses)}

    create_pnu_mapping_table()

    for idx, address in enumerate(addresses, 1):
        try:
            if idx % 50 == 0:
                log.info(f"  진행: {idx}/{len(addresses)}")

            pnu = convert_address_to_pnu(address)

            if pnu:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO address_pnu_mapping
                    (address, pnu)
                    VALUES (?, ?)
                    """,
                    (address, pnu),
                )
                stats["total_converted"] += 1
            else:
                stats["failed"] += 1

        except Exception as e:
            log.warning(f"  {address} 변환 실패: {e}")
            stats["failed"] += 1

    conn.commit()
    log.info(f"\n✓ 변환 완료: {stats['total_converted']}개 성공, {stats['failed']}개 실패")
    conn.close()

    return stats


def get_pnu_for_address(address: str) -> Optional[str]:
    """주어진 주소의 PNU 조회 (캐시).

    Args:
        address: 부동산 주소

    Returns:
        PNU 또는 None
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pnu FROM address_pnu_mapping WHERE address = ?", (address,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def main() -> None:
    """주소→PNU 변환 메인."""
    log.info("\nDay 5: 주소→PNU 변환 시작\n")
    stats = convert_layer1_addresses()
    log.info(f"\n변환율: {stats['total_converted']}/{stats['queries']} ({100*stats['total_converted']/max(stats['queries'],1):.1f}%)")


if __name__ == "__main__":
    main()
