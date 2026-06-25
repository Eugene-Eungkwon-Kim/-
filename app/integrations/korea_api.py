import hashlib
import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class TransactionRecord:
    sgg_code: str
    property_type: str
    complex_name: str
    address_dong: str
    address_jibun: str
    contract_year: int
    contract_month: int
    contract_day: int
    price_manwon: int
    exclusive_area: float
    floor: int
    build_year: Optional[int] = None
    seller_type: Optional[str] = None
    buyer_type: Optional[str] = None

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
    def price_per_area(self) -> float:
        return self.price_won / self.exclusive_area if self.exclusive_area > 0 else 0.0

    @property
    def transaction_key(self) -> str:
        raw = (f"{self.sgg_code}|{self.property_type}|{self.complex_name}|"
               f"{self.exclusive_area}|{self.contract_year}{self.contract_month:02d}"
               f"{self.contract_day:02d}|{self.price_manwon}")
        return hashlib.md5(raw.encode()).hexdigest()


class KoreaLandAPI:
    BASE_URL = "http://apis.data.go.kr/1613000"
    SERVICES = {
        "아파트":   "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
        "다세대":   "RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
        "연립":     "RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
        "오피스텔": "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
    }

    def __init__(self, api_key: str, timeout: int = 30, retry: int = 3):
        self.api_key = api_key
        self.timeout = timeout
        self.retry = retry
        self.session = requests.Session()

    def fetch_apt_transactions(self, sgg_code: str, year: int, month: int) -> list[TransactionRecord]:
        return self._fetch(sgg_code, year, month, "아파트")

    def fetch_multi_transactions(self, sgg_code: str, year: int, month: int) -> list[TransactionRecord]:
        return self._fetch(sgg_code, year, month, "다세대")

    def fetch_office_transactions(self, sgg_code: str, year: int, month: int) -> list[TransactionRecord]:
        return self._fetch(sgg_code, year, month, "오피스텔")

    def fetch_all_types(self, sgg_code: str, year: int, month: int) -> list[TransactionRecord]:
        results = []
        for ptype in ["아파트", "다세대", "오피스텔"]:
            try:
                results.extend(self._fetch(sgg_code, year, month, ptype))
                time.sleep(0.2)
            except Exception as e:
                logger.warning(f"[{ptype}] {sgg_code} {year}-{month:02d}: {e}")
        return results

    def _fetch(self, sgg_code: str, year: int, month: int, property_type: str) -> list[TransactionRecord]:
        service = self.SERVICES.get(property_type)
        if not service:
            raise ValueError(f"지원하지 않는 property_type: {property_type}")

        # serviceKey를 URL에 직접 포함 — requests의 이중 인코딩 방지
        url = f"{self.BASE_URL}/{service}?serviceKey={urllib.parse.quote(self.api_key, safe='')}"
        params = {"LAWD_CD": sgg_code, "DEAL_YMD": f"{year}{month:02d}", "pageNo": 1, "numOfRows": 10000}

        for attempt in range(self.retry):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return self._parse_xml(resp.text, sgg_code, property_type)
            except requests.RequestException as e:
                logger.warning(f"API 오류 (시도 {attempt+1}/{self.retry}): {e}")
                time.sleep(attempt + 1)

        logger.error(f"API 재시도 초과: {sgg_code} {year}-{month:02d} [{property_type}]")
        return []

    def _parse_xml(self, xml_text: str, sgg_code: str, property_type: str) -> list[TransactionRecord]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"XML 파싱 오류: {e}")
            return []

        if root.findtext(".//resultCode", "") != "00":
            logger.warning(f"API 오류: {root.findtext('.//resultMsg', '')}")
            return []

        records = []
        for item in root.findall(".//item"):
            try:
                rec = self._parse_item(item, sgg_code, property_type)
                if rec:
                    records.append(rec)
            except Exception:
                continue
        return records

    def _parse_item(self, item: ET.Element, sgg_code: str, property_type: str) -> Optional[TransactionRecord]:
        def t(tag: str) -> str:
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        def i(tag: str) -> int:
            try:
                return int(float(t(tag).replace(",", "")))
            except (ValueError, TypeError):
                return 0

        def f(tag: str) -> float:
            try:
                return float(t(tag).replace(",", ""))
            except (ValueError, TypeError):
                return 0.0

        price = i("거래금액") or i("dealAmount")
        area = f("전용면적") or f("excluUseAr")
        year_val = i("년") or i("dealYear")
        month_val = i("월") or i("dealMonth")

        if not (price > 0 and area > 0 and year_val and month_val):
            return None

        build_year = i("건축년도") or i("buildYear") or None

        return TransactionRecord(
            sgg_code=sgg_code,
            property_type=property_type,
            complex_name=(t("아파트") or t("aptNm") or t("연립다세대") or
                          t("mhouseNm") or t("단지명") or t("offiNm") or "알수없음"),
            address_dong=t("법정동") or t("umdNm"),
            address_jibun=t("지번") or t("jibun"),
            contract_year=year_val,
            contract_month=month_val,
            contract_day=i("일") or i("dealDay"),
            price_manwon=price,
            exclusive_area=area,
            floor=i("층") or i("floor"),
            build_year=build_year if build_year != 0 else None,
            seller_type=t("매도자구분") or t("slerGbn") or None,
            buyer_type=t("매수자구분") or t("buyerGbn") or None,
        )
