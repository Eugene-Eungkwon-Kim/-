"""국토부 RTMS 계열 실거래 API 공통 처리 — 페이지 순회, 재시도, 해제 거래 판정.

네 수집기(korea_api / _industrial / _commercial / _land)가 각자 들고 있던
"pageNo=1, numOfRows=10000 한 번" 호출을 여기로 모았다. 실제 API는 한 페이지
상한이 있어(data.go.kr 계열 보편 1,000) 거래가 많은 시군구·월은 뒷부분이
조용히 잘렸다 — totalCount 를 보고 페이지를 끝까지 넘긴다.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

PAGE_SIZE = 1000
CANCEL_TAGS = ("해제여부", "cdealType")


def is_cancelled(item: ET.Element) -> bool:
    """해제된 거래(해제여부 'O')는 비교사례로 쓰면 안 된다."""
    for tag in CANCEL_TAGS:
        el = item.find(tag)
        if el is not None and el.text and el.text.strip().upper() == "O":
            return True
    return False


def _safe_error(error: Exception) -> str:
    # 요청 예외 문자열에 serviceKey 가 그대로 실려 로그에 남는다.
    return re.sub(r"(serviceKey=)[^&\s)]+", r"\1***", str(error))


def _page_stats(xml_text: str) -> Tuple[Optional[int], int]:
    """(totalCount, 이 페이지의 item 수). 파싱 불가면 (None, 0) — 오류 판정은 수집기 _parse_xml 몫."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None, 0
    total_text = root.findtext(".//totalCount")
    try:
        total = int(total_text) if total_text else None
    except ValueError:
        total = None
    return total, len(root.findall(".//item"))


def _get_with_retry(session: requests.Session, url: str, params: Dict[str, object],
                    timeout: int, retry: int, label: str, debug: bool) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(retry):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            if debug:
                logger.info(f"[DEBUG] {label} p{params['pageNo']} 원본 응답(앞 2000자):\n{resp.text[:2000]}")
            return resp.text
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"API 오류 (시도 {attempt + 1}/{retry}) [{label}]: {_safe_error(e)}")
            time.sleep(1 * (attempt + 1))
    raise RuntimeError(f"API 최대 재시도 초과: {label}") from last_error


def fetch_all_pages(session: requests.Session, url: str, params: Dict[str, object], *,
                    timeout: int = 30, retry: int = 3, label: str = "",
                    debug: bool = False, page_size: int = PAGE_SIZE) -> List[str]:
    """totalCount 만큼 pageNo 를 넘기며 모든 페이지의 원본 XML 을 모은다."""
    pages: List[str] = []
    fetched = 0
    page = 1
    while True:
        page_params = {**params, "pageNo": page, "numOfRows": page_size}
        text = _get_with_retry(session, url, page_params, timeout, retry, label, debug)
        pages.append(text)
        total, n_items = _page_stats(text)
        fetched += n_items
        if total is None or n_items == 0 or fetched >= total:
            return pages
        page += 1
