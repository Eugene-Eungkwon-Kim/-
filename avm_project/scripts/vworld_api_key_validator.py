"""VWorld/data.go.kr API 키 실제 검증

각 API에 실제 요청을 보내 키 유효성과 응답 상태를 확인한다.
결과는 ledger에 JSON으로 기록한다.

실행:
    python scripts/vworld_api_key_validator.py
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VWORLD_KEY = os.environ.get("VWORLD_API_KEY", "")
DATA_GO_KR_KEY = os.environ.get("DATAGOVKR_API_KEY", "")
JUSO_KEY_PROVIDE = os.environ.get("JUSO_API_KEY_PROVIDE", "")
JUSO_KEY_INFO = os.environ.get("JUSO_API_KEY_INFO", "")

LEDGER_DIR = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\ledger")
TIMEOUT = 15


def check_vworld_search() -> Dict:
    """VWorld 검색 API 2.0 키 검증."""
    url = "https://api.vworld.kr/req/search"
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "query": "서울특별시 종로구",
        "type": "address",
        "category": "road",
        "format": "json",
        "key": VWORLD_KEY,
    }
    return _probe("vworld_search20", url, params)


def check_vworld_geocoder() -> Dict:
    """VWorld 지오코더 API 2.0 키 검증."""
    url = "https://api.vworld.kr/req/address"
    params = {
        "service": "address",
        "request": "getcoord",
        "version": "2.0",
        "crs": "epsg:4326",
        "address": "서울특별시 종로구 세종대로 209",
        "type": "road",
        "format": "json",
        "key": VWORLD_KEY,
    }
    return _probe("vworld_geocoder20", url, params)


def check_vworld_wfs() -> Dict:
    """VWorld WFS API 키 검증 (연속지적도 레이어)."""
    url = "https://api.vworld.kr/req/wfs"
    params = {
        "service": "WFS",
        "request": "GetFeature",
        "version": "2.0.0",
        "typename": "lp_pa_cbnd_bubun",
        "bbox": "126.975,37.564,126.980,37.568,EPSG:4326",
        "srsname": "EPSG:4326",
        "output": "application/json",
        "maxfeatures": "5",
        "key": VWORLD_KEY,
        "domain": "localhost",
    }
    return _probe("vworld_wfs_cadastral", url, params)


def check_juso_api() -> Dict:
    """주소 정보제공 API 키 검증 (도로명주소)."""
    url = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
    params = {
        "confmKey": JUSO_KEY_PROVIDE,
        "currentPage": "1",
        "countPerPage": "5",
        "keyword": "세종대로 209",
        "resultType": "json",
    }
    return _probe("juso_addrlink", url, params)


def check_data_go_kr_apt_trade() -> Dict:
    """data.go.kr 아파트 실거래가 API 키 검증."""
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {
        "serviceKey": DATA_GO_KR_KEY,
        "LAWD_CD": "11110",
        "DEAL_YMD": "202606",
        "pageNo": "1",
        "numOfRows": "5",
    }
    return _probe("datagokr_apt_trade", url, params)


def _probe(name: str, url: str, params: Dict) -> Dict:
    """단일 API 요청 및 결과 판정.

    Args:
        name: API 식별자
        url: 요청 URL
        params: 쿼리 파라미터

    Returns:
        상태, HTTP 코드, 응답 요약 포함 딕셔너리
    """
    result = {"name": name, "url": url, "checked_at": datetime.now().isoformat()}
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        result["http_status"] = resp.status_code
        body = resp.text[:500]
        result["body_preview"] = body

        # 키/승인 오류 패턴 판정
        error_markers = [
            "INVALID_KEY", "UNREGISTERED_KEY", "SERVICE_KEY_IS_NOT_REGISTERED",
            "E0001", "INCORRECT_KEY", "SERVICE ERROR", "DENIED",
        ]
        if resp.status_code == 200 and not any(m in body.upper() for m in error_markers):
            result["status"] = "OK"
        else:
            result["status"] = "ERROR"
    except requests.RequestException as e:
        result["status"] = "NETWORK_ERROR"
        result["error"] = str(e)

    log.info(f"[{result['status']}] {name} (HTTP {result.get('http_status', 'N/A')})")
    return result


def main() -> None:
    """모든 API 키 검증 실행 및 ledger 기록."""
    log.info("=" * 60)
    log.info("API 키 실제 검증 시작")
    log.info("=" * 60)

    checks = [
        check_vworld_search(),
        check_vworld_geocoder(),
        check_vworld_wfs(),
        check_juso_api(),
        check_data_go_kr_apt_trade(),
    ]

    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LEDGER_DIR / f"api_key_validation_{datetime.now():%Y%m%d_%H%M%S}.json"
    out_path.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for c in checks if c["status"] == "OK")
    log.info(f"\n결과: {ok}/{len(checks)} OK")
    log.info(f"기록: {out_path}")


if __name__ == "__main__":
    main()
