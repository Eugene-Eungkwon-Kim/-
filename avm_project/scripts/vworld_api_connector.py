"""VWorld API 공통 연결 모듈

모든 14개 API 레이어 수집을 위한 통일된 HTTP 클라이언트.
재시도, 에러 처리, 로깅 포함.

실행:
    from vworld_api_connector import VWorldConnector
    conn = VWorldConnector(api_key="YOUR_KEY")
    data = conn.search(query="서울", type="address")
"""

import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import requests

log = logging.getLogger(__name__)


class VWorldConnector:
    """VWorld API 통합 클라이언트.

    모든 VWorld API 엔드포인트에 대한 통일된 인터페이스 제공.
    HTTP 연결 풀, 재시도, 타임아웃 처리 포함.
    """

    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3) -> None:
        """초기화.

        Args:
            api_key: VWorld API 키
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def search(
        self,
        query: str,
        type: str = "address",
        category: str = "road",
        format: str = "json",
    ) -> Dict[str, Any]:
        """검색 API 2.0 (Layer 1).

        Args:
            query: 검색어 (예: "서울특별시 종로구")
            type: 검색 타입 (address/point)
            category: 카테고리 (road/parcel)
            format: 응답 포맷 (json/xml)

        Returns:
            API 응답 (JSON 파싱됨)
        """
        url = "https://api.vworld.kr/req/search"
        params = {
            "service": "search",
            "request": "search",
            "version": "2.0",
            "query": query,
            "type": type,
            "category": category,
            "format": format,
            "key": self.api_key,
        }
        return self._request("GET", url, params)

    def geocode(self, address: str, crs: str = "epsg:4326") -> Dict[str, Any]:
        """지오코더 API 2.0 (Layer 2).

        주소 → 좌표 변환.

        Args:
            address: 주소 문자열
            crs: 좌표계 (epsg:4326/epsg:3857)

        Returns:
            API 응답
        """
        url = "https://api.vworld.kr/req/address"
        params = {
            "service": "address",
            "request": "getcoord",
            "version": "2.0",
            "crs": crs,
            "address": address,
            "type": "road",
            "format": "json",
            "key": self.api_key,
        }
        return self._request("GET", url, params)

    def wfs_get_feature(
        self,
        typename: str,
        bbox: str,
        maxfeatures: int = 1000,
        srsname: str = "EPSG:4326",
    ) -> Dict[str, Any]:
        """WFS GetFeature (Layer 3-7, 건물/토지 정보).

        Args:
            typename: WFS 피처 타입
            bbox: 바운딩박스 (minx,miny,maxx,maxy,crs)
            maxfeatures: 최대 결과 수
            srsname: 좌표 참조계

        Returns:
            GeoJSON 형식 응답
        """
        url = "https://api.vworld.kr/req/wfs"
        params = {
            "service": "WFS",
            "request": "GetFeature",
            "version": "2.0.0",
            "typename": typename,
            "bbox": bbox,
            "srsname": srsname,
            "output": "application/json",
            "maxfeatures": maxfeatures,
            "key": self.api_key,
            "domain": "localhost",
        }
        return self._request("GET", url, params)

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """HTTP 요청 (재시도 + 에러 처리 포함).

        Args:
            method: HTTP 메서드 (GET/POST)
            url: 요청 URL
            params: 쿼리 파라미터
            json_data: JSON 바디

        Returns:
            파싱된 JSON 응답

        Raises:
            requests.RequestException: 재시도 실패 후
        """
        for attempt in range(self.max_retries):
            try:
                resp = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                return resp.json()

            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    log.warning(f"재시도 {attempt + 1}/{self.max_retries}: {e} (대기 {wait}초)")
                    time.sleep(wait)
                else:
                    log.error(f"최종 실패: {e}")
                    raise

    def close(self) -> None:
        """연결 종료."""
        self.session.close()

    def __enter__(self):
        """Context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager."""
        self.close()
