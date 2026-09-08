"""국토교통부 상업업무용 부동산 매매 실거래가 API 클라이언트.

Endpoint: https://apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade

이 서비스 코드(RTMSDataSvcNrgTrade)는 사용자가 직접 준 것이 아니라
웹 검색으로 찾았다 — data.go.kr 공식 카탈로그 페이지
(data.go.kr/data/15126463/openapi.do, "국토교통부_상업업무용 부동산
매매 실거래가 자료")와 실제로 이 서비스명을 URL에 쓰는 제3자 사이트
(landmatching.com/rtmsdatasvcnrgtrade/...) 두 곳에서 교차 확인됐다.
공식 API 문서 페이지 자체(data.go.kr)는 이 샌드박스의 아웃바운드
정책상 직접 열어보지 못했다 — 그래서 정확한 요청 파라미터명·필수값,
응답 필드 태그명은 여전히 미검증이다.

토지(RTMSDataSvcLandTrade 로 추정)는 여러 차례 검색해도 정확한 서비스
코드 문자열을 확인할 소스를 찾지 못해 이번엔 만들지 않았다 — 확인 안
된 문자열을 하드코딩하느니 안 만드는 편이 낫다는 판단을 유지한다.
(참고: data.go.kr/data/15126466/openapi.do, "국토교통부_토지 매매
실거래가 자료" — 데이터셋 자체는 존재를 확인했다.)

필드 태그명은 아파트/연립 API(korea_api.py, 실제 응답으로 검증됨)와
공장/창고 API(korea_api_industrial.py)의 명명 관례를 그대로 확장한
추정이다. 네트워크가 열린 환경에서 처음 실행할 때는 --debug 로 원본
XML을 먼저 확인할 것.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Optional

import requests

from app.integrations.rtms_paging import fetch_all_pages, is_cancelled

logger = logging.getLogger(__name__)


@dataclass
class CommercialTransactionRecord:
    """API 응답 → 파싱된 상업업무용 부동산 거래 레코드."""

    sgg_code: str
    building_name: str
    address_dong: str
    address_jibun: str

    contract_year: int
    contract_month: int
    contract_day: int

    price_manwon: int
    land_area: Optional[float] = None
    building_area: Optional[float] = None

    @property
    def price_won(self) -> int:
        return self.price_manwon * 10000

    @property
    def contract_date(self) -> date:
        try:
            return date(self.contract_year, self.contract_month, self.contract_day)
        except Exception:
            return date(self.contract_year, self.contract_month, 1)

    @property
    def transaction_key(self) -> str:
        import hashlib
        raw = (
            f"commercial|{self.sgg_code}|{self.building_name}|"
            f"{self.contract_year}{self.contract_month:02d}{self.contract_day:02d}|"
            f"{self.price_manwon}"
        )
        return hashlib.md5(raw.encode()).hexdigest()


class KoreaCommercialTradeAPI:
    """국토교통부 상업업무용 부동산 매매 실거래가 API 클라이언트."""

    BASE_URL = "https://apis.data.go.kr/1613000"
    SERVICE = "RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade"

    def __init__(self, api_key: str, timeout: int = 30, retry: int = 3):
        self.api_key = api_key
        self.timeout = timeout
        self.retry = retry
        self.session = requests.Session()

    def fetch(self, sgg_code: str, year: int, month: int,
             debug: bool = False) -> list[CommercialTransactionRecord]:
        params = {"serviceKey": self.api_key, "LAWD_CD": sgg_code, "DEAL_YMD": f"{year}{month:02d}"}
        pages = fetch_all_pages(
            self.session, f"{self.BASE_URL}/{self.SERVICE}", params,
            timeout=self.timeout, retry=self.retry,
            label=f"{sgg_code} {year}-{month:02d} [상업업무용]", debug=debug,
        )
        return [rec for xml in pages for rec in self._parse_xml(xml, sgg_code)]

    def _parse_xml(self, xml_text: str, sgg_code: str) -> list[CommercialTransactionRecord]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise RuntimeError(f"XML 파싱 오류: {e}") from e

        result_code = root.findtext(".//resultCode", "")
        if result_code not in ("00", "000"):
            result_msg = root.findtext(".//resultMsg", "")
            raise RuntimeError(f"API 오류 응답: {result_code} - {result_msg}")

        records = []
        for item in root.findall(".//item"):
            rec = self._parse_item(item, sgg_code)
            if rec:
                records.append(rec)
        return records

    @staticmethod
    def _parse_item(item: ET.Element, sgg_code: str) -> Optional[CommercialTransactionRecord]:
        def text(*tags: str) -> str:
            for tag in tags:
                el = item.find(tag)
                if el is not None and el.text:
                    return el.text.strip()
            return ""

        def int_val(*tags: str) -> int:
            raw = text(*tags).replace(",", "")
            try:
                return int(float(raw)) if raw else 0
            except ValueError:
                return 0

        def float_or_none(*tags: str) -> Optional[float]:
            raw = text(*tags).replace(",", "")
            try:
                return float(raw) if raw else None
            except ValueError:
                return None

        if is_cancelled(item):
            return None

        price = int_val("거래금액", "dealAmount")
        if price <= 0:
            return None

        year_val = int_val("년", "dealYear")
        month_val = int_val("월", "dealMonth")
        day_val = int_val("일", "dealDay") or 1
        if not (year_val and month_val):
            return None

        return CommercialTransactionRecord(
            sgg_code=sgg_code,
            building_name=text("건물명", "buildingName", "물건명", "상호") or "알수없음",
            address_dong=text("법정동", "umdNm"),
            address_jibun=text("지번", "jibun"),
            contract_year=year_val,
            contract_month=month_val,
            contract_day=day_val,
            price_manwon=price,
            land_area=float_or_none("대지면적", "platArea", "부지면적"),
            building_area=float_or_none("건물면적", "buildingArea", "연면적", "totalFloorAr"),
        )
