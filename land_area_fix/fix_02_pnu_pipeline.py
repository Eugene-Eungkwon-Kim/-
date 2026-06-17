"""
2순위: PNU 없음 2,988건 해결 — 주소/좌표 → PNU 파이프라인
- 충전소(KGS 1,457): 좌표 → VWorld 연속지적도 API
- 주유소(MOTIE 852, OPINET 679): 지번주소 → JUSO API → PNU 19자리 조립

사전 준비:
  pip install requests psycopg2-binary python-dotenv

환경 변수 (.env):
  DB_DSN=postgresql://user:pass@host:5432/dbname
  JUSO_API_KEY=행안부_도로명주소_API_키
  VWORLD_API_KEY=VWorld_API_키
"""

import os
import time
import logging
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_DSN        = os.environ["DB_DSN"]
JUSO_KEY      = os.environ["JUSO_API_KEY"]
VWORLD_KEY    = os.environ["VWORLD_API_KEY"]
JUSO_URL      = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
VWORLD_URL    = "https://api.vworld.kr/req/data"

RETRY_DELAYS  = [2, 4, 8, 16]   # 초


# ──────────────────────────────────────────────
# PNU 조립 헬퍼
# ──────────────────────────────────────────────

def build_pnu(adm_cd: str, mt_yn: str, main_no: str, sub_no: str) -> str:
    """행안부 JUSO 응답 필드로 PNU 19자리 조립."""
    mt = "1" if str(mt_yn) == "1" else "0"
    main = str(main_no).zfill(4)
    sub  = str(sub_no).zfill(4)
    return f"{adm_cd}{mt}{main}{sub}"   # 10 + 1 + 4 + 4 = 19


# ──────────────────────────────────────────────
# JUSO API (도로명/지번주소 → PNU)
# ──────────────────────────────────────────────

def juso_to_pnu(address: str) -> str | None:
    params = {
        "confmKey": JUSO_KEY,
        "currentPage": 1,
        "countPerPage": 1,
        "keyword": address,
        "resultType": "json",
        "hstryYn": "Y",
        "addrDetails": "Y",
    }
    for delay in [0] + RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(JUSO_URL, params=params, timeout=10)
            r.raise_for_status()
            data = r.json().get("results", {})
            common = data.get("common", {})
            if common.get("errorCode") != "0":
                log.warning("JUSO error %s: %s", common.get("errorCode"), address)
                return None
            juso_list = data.get("juso", [])
            if not juso_list:
                return None
            j = juso_list[0]
            pnu = build_pnu(j["admCd"], j["mtYn"], j["lnbrMnnm"], j["lnbrSlno"])
            return pnu
        except requests.RequestException as e:
            log.warning("JUSO request error (%s): %s", address, e)
    return None


# ──────────────────────────────────────────────
# VWorld API (좌표 → PNU, 충전소 전용)
# ──────────────────────────────────────────────

def coord_to_pnu(lon: float, lat: float) -> str | None:
    params = {
        "service": "data",
        "request": "GetFeature",
        "data": "LP_PA_CBND_BUBUN",           # 연속지적도 부번
        "key": VWORLD_KEY,
        "geometry": "true",
        "attribute": "true",
        "geomFilter": f"POINT({lon} {lat})",
        "crs": "EPSG:4326",
        "format": "json",
        "size": 1,
    }
    for delay in [0] + RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(VWORLD_URL, params=params, timeout=10)
            r.raise_for_status()
            result = r.json().get("response", {})
            if result.get("status") != "OK":
                return None
            features = result.get("result", {}).get("featureCollection", {}).get("features", [])
            if not features:
                return None
            return features[0].get("properties", {}).get("pnu")
        except requests.RequestException as e:
            log.warning("VWorld error (%.6f,%.6f): %s", lon, lat, e)
    return None


# ──────────────────────────────────────────────
# DB 조회 및 PNU 저장
# ──────────────────────────────────────────────

FETCH_NO_PNU_SQL = """
    SELECT e.energy_site_id, e.site_name, e.site_category, e.source_provider,
           e.road_address, e.jibun_address,
           e.longitude, e.latitude
    FROM energy_site e
    LEFT JOIN energy_site_land_area_summary s ON e.energy_site_id = s.energy_site_id
    WHERE (e.pnu IS NULL OR e.pnu = '')
      AND s.value_status = 'NO_PNU'
    ORDER BY e.source_provider, e.energy_site_id
"""

UPSERT_PNU_SQL = """
    UPDATE energy_site
    SET pnu = %s, pnu_source = %s, pnu_updated_at = NOW()
    WHERE energy_site_id = %s AND (pnu IS NULL OR pnu = '')
"""


def run_pipeline():
    conn = psycopg2.connect(DB_DSN)
    cur  = conn.cursor()

    cur.execute(FETCH_NO_PNU_SQL)
    rows = cur.fetchall()
    log.info("PNU 없음 대상: %d건", len(rows))

    success = fail = skip = 0

    for (site_id, name, category, provider, road_addr, jibun_addr, lon, lat) in rows:
        pnu    = None
        source = None

        # 1. 좌표 우선 (충전소 KGS)
        if category == "CHARGING_STATION" and lon and lat:
            pnu = coord_to_pnu(float(lon), float(lat))
            if pnu:
                source = "VWORLD_COORD"

        # 2. 지번주소 → JUSO
        if not pnu and jibun_addr:
            pnu = juso_to_pnu(jibun_addr)
            if pnu:
                source = "JUSO_JIBUN"

        # 3. 도로명주소 → JUSO (폴백)
        if not pnu and road_addr:
            pnu = juso_to_pnu(road_addr)
            if pnu:
                source = "JUSO_ROAD"

        if pnu:
            cur.execute(UPSERT_PNU_SQL, (pnu, source, site_id))
            success += 1
            log.debug("✅ %s → PNU %s (%s)", site_id, pnu, source)
        else:
            fail += 1
            log.warning("❌ PNU 미확보: %s [%s] %s", site_id, provider, name)

        # 진행 상황 중간 커밋 (500건 단위)
        if (success + fail) % 500 == 0:
            conn.commit()
            log.info("진행 %d / %d (성공 %d, 실패 %d)", success + fail, len(rows), success, fail)

    conn.commit()
    cur.close()
    conn.close()
    log.info("=== 완료: 성공 %d, 실패 %d, 건너뜀 %d / 전체 %d ===", success, fail, skip, len(rows))


if __name__ == "__main__":
    run_pipeline()
