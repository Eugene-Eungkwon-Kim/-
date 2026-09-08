"""국토교통부 공장 및 창고 등 부동산 매매 실거래가 API 클라이언트.

Endpoint (사용자 확인): https://apis.data.go.kr/1613000/RTMSDataSvcInduTrade
인증키: DATAGOVKR_DECODING_KEY (긴 base64 "일반 인증키(Decoding)" 형식 —
korea_api.py 가 쓰는 짧은 UUID 형식 DATAGOVKR_API_KEY 와는 다른 키다).

주의 — 필드 태그명은 미검증이다:
    이 API의 실제 응답을 이 환경에서 한 번도 받아보지 못했다(샌드박스가
    apis.data.go.kr 아웃바운드를 정책상 차단한다). 아래 태그명은 같은
    RTMSDataSvc* 계열인 아파트/연립 API(korea_api.py, 실제 응답으로
    검증됨)의 명명 관례 — 년/월/일 또는 dealYear/dealMonth/dealDay,
    거래금액/dealAmount, 법정동/umdNm, 지번/jibun — 를 그대로 확장한
    추정이다. 실제로 다를 수 있는 항목(대지면적/건물면적 계열)은 후보를
    여러 개 시도하고, 전부 실패하면 예외를 던지지 않고 조용히 건너뛴다
    (잘못된 추정 때문에 전체 수집이 죽지 않도록).

    네트워크가 열린 환경에서 처음 실행할 때는 반드시 `debug=True` 로
    실행해 원본 XML을 확인하고, 실제 태그명과 다르면 TAG_CANDIDATES 를
    고쳐야 한다.
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
class IndustrialTransactionRecord:
    """API 응답 → 파싱된 공장/창고 거래 레코드."""

    sgg_code: str
    building_name: str
    address_dong: str
    address_jibun: str

    contract_year: int
    contract_month: int
    contract_day: int

    price_manwon: int
    land_area: Optional[float] = None       # 대지면적(㎡), 확인 안 되면 None
    building_area: Optional[float] = None   # 건물면적(㎡), 확인 안 되면 None

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
            f"industrial|{self.sgg_code}|{self.building_name}|"
            f"{self.contract_year}{self.contract_month:02d}{self.contract_day:02d}|"
            f"{self.price_manwon}"
        )
        return hashlib.md5(raw.encode()).hexdigest()


class KoreaIndustrialTradeAPI:
    """국토교통부 공장 및 창고 등 부동산 매매 실거래가 API 클라이언트."""

    BASE_URL = "https://apis.data.go.kr/1613000"
    SERVICE = "RTMSDataSvcInduTrade/getRTMSDataSvcInduTrade"

    def __init__(self, api_key: str, timeout: int = 30, retry: int = 3):
        self.api_key = api_key
        self.timeout = timeout
        self.retry = retry
        self.session = requests.Session()

    def fetch(self, sgg_code: str, year: int, month: int,
             debug: bool = False) -> list[IndustrialTransactionRecord]:
        params = {"serviceKey": self.api_key, "LAWD_CD": sgg_code, "DEAL_YMD": f"{year}{month:02d}"}
        pages = fetch_all_pages(
            self.session, f"{self.BASE_URL}/{self.SERVICE}", params,
            timeout=self.timeout, retry=self.retry,
            label=f"{sgg_code} {year}-{month:02d} [공장/창고]", debug=debug,
        )
        return [rec for xml in pages for rec in self._parse_xml(xml, sgg_code)]

    def _parse_xml(self, xml_text: str, sgg_code: str) -> list[IndustrialTransactionRecord]:
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
    def _parse_item(item: ET.Element, sgg_code: str) -> Optional[IndustrialTransactionRecord]:
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

        return IndustrialTransactionRecord(
            sgg_code=sgg_code,
            building_name=text("건물명", "buildingName", "물건명") or "알수없음",
            address_dong=text("법정동", "umdNm"),
            address_jibun=text("지번", "jibun"),
            contract_year=year_val,
            contract_month=month_val,
            contract_day=day_val,
            price_manwon=price,
            # 태그명 미검증 — 후보를 여러 개 시도하고 전부 없으면 None.
            land_area=float_or_none("대지면적", "platArea", "부지면적"),
            building_area=float_or_none("건물면적", "buildingArea", "연면적", "totalFloorAr"),
        )
