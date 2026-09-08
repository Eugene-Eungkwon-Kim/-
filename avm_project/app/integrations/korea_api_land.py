"""국토교통부 토지 매매 실거래가 API 클라이언트.

Endpoint(후보): https://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade

서비스 코드는 **미확정 후보**다. 데이터셋 자체("국토교통부_토지 매매
실거래가 자료", data.go.kr/data/15126466/openapi.do)는 존재가 확인됐지만
정확한 서비스명 문자열은 이 샌드박스(apis.data.go.kr·data.go.kr 아웃바운드
차단)에서 열어볼 수 없었다. 위 값은 같은 계열의 확정된 서비스명 규칙
(RTMSDataSvcAptTradeDev / RTMSDataSvcInduTrade[사용자 확인] /
RTMSDataSvcNrgTrade[웹 교차확인])에서 유추한 것이다. 틀렸다면 API가 오류
응답을 주므로 잘못된 데이터가 조용히 들어올 위험은 없다 — 첫 실행 전에
data.go.kr 마이페이지 → 활용신청 내역에서 서비스명을 확인해 SERVICE 상수를
맞추고, --debug 로 원본 XML을 확인할 것.

토지는 건물이 없어 건물면적 대신 거래면적(대지), 지목, 용도지역, 지분거래
여부가 핵심 필드다. 해제된 거래(해제여부 'O')는 비교사례로 쓰면 안 되므로
파싱 단계에서 버린다. 필드 태그명은 국문/영문 후보를 모두 시도한다.
"""

import hashlib
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Optional

import requests

from app.integrations.rtms_paging import fetch_all_pages, is_cancelled

logger = logging.getLogger(__name__)


@dataclass
class LandTransactionRecord:
    """API 응답 → 파싱된 토지 거래 레코드."""

    sgg_code: str
    address_dong: str
    address_jibun: str
    land_category: str
    use_zone: str

    contract_year: int
    contract_month: int
    contract_day: int

    price_manwon: int
    land_area: Optional[float] = None
    share_deal: str = ""

    @property
    def price_won(self) -> int:
        return self.price_manwon * 10000

    @property
    def contract_date(self) -> date:
        try:
            return date(self.contract_year, self.contract_month, self.contract_day)
        except ValueError:
            return date(self.contract_year, self.contract_month, 1)

    @property
    def transaction_key(self) -> str:
        raw = (
            f"land|{self.sgg_code}|{self.address_dong}|{self.address_jibun}|"
            f"{self.contract_year}{self.contract_month:02d}{self.contract_day:02d}|"
            f"{self.price_manwon}|{self.land_area}"
        )
        return hashlib.md5(raw.encode()).hexdigest()


class KoreaLandTradeAPI:
    """국토교통부 토지 매매 실거래가 API 클라이언트."""

    BASE_URL = "https://apis.data.go.kr/1613000"
    # 미확정 후보 — 모듈 docstring 참고.
    SERVICE = "RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade"

    def __init__(self, api_key: str, timeout: int = 30, retry: int = 3) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.retry = retry
        self.session = requests.Session()

    def fetch(self, sgg_code: str, year: int, month: int,
              debug: bool = False) -> list[LandTransactionRecord]:
        params = {"serviceKey": self.api_key, "LAWD_CD": sgg_code, "DEAL_YMD": f"{year}{month:02d}"}
        pages = fetch_all_pages(
            self.session, f"{self.BASE_URL}/{self.SERVICE}", params,
            timeout=self.timeout, retry=self.retry,
            label=f"{sgg_code} {year}-{month:02d} [토지]", debug=debug,
        )
        return [rec for xml in pages for rec in self._parse_xml(xml, sgg_code)]

    def _parse_xml(self, xml_text: str, sgg_code: str) -> list[LandTransactionRecord]:
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
    def _parse_item(item: ET.Element, sgg_code: str) -> Optional[LandTransactionRecord]:
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

        return LandTransactionRecord(
            sgg_code=sgg_code,
            address_dong=text("법정동", "umdNm"),
            address_jibun=text("지번", "jibun"),
            land_category=text("지목", "jimok"),
            use_zone=text("용도지역", "landUse"),
            contract_year=year_val,
            contract_month=month_val,
            contract_day=day_val,
            price_manwon=price,
            land_area=float_or_none("거래면적", "dealArea", "면적", "대지면적"),
            share_deal=text("지분거래구분", "shareDealingType"),
        )
