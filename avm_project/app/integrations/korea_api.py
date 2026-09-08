"""
국토부 실거래가 공개 API 클라이언트

API 신청: https://www.data.go.kr/
관련 API:
  - 아파트매매 실거래자료 (국토교통부_아파트매매 실거래자료)
  - 연립다세대 매매 실거래자료
  - 오피스텔 매매 신고 조회

사용방법:
    api = KoreaLandAPI(api_key="YOUR_API_KEY")
    df = api.fetch_apt_transactions(sgg_code="41590", year=2026, month=5)
"""

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Optional

import requests

from app.integrations.rtms_paging import fetch_all_pages, is_cancelled

logger = logging.getLogger(__name__)


@dataclass
class TransactionRecord:
    """API 응답 → 파싱된 거래 레코드"""
    sgg_code: str
    property_type: str          # 아파트 / 다세대 / 연립 / 오피스텔

    # 단지 정보
    complex_name: str
    address_dong: str
    address_jibun: str

    # 거래 일자
    contract_year: int
    contract_month: int
    contract_day: int

    # 거래 정보
    price_manwon: int           # 거래금액(만원)
    exclusive_area: float       # 전용면적
    floor: int

    # 선택
    build_year: Optional[int] = None
    seller_type: Optional[str] = None
    buyer_type: Optional[str] = None

    @property
    def price_won(self) -> int:
        """거래금액 (원 단위)"""
        return self.price_manwon * 10000

    @property
    def contract_date(self) -> date:
        """계약일 (date 객체)"""
        try:
            return date(self.contract_year, self.contract_month, self.contract_day)
        except Exception:
            return date(self.contract_year, self.contract_month, 1)

    @property
    def price_per_area(self) -> float:
        """전용㎡당 가격 (원)"""
        if self.exclusive_area and self.exclusive_area > 0:
            return self.price_won / self.exclusive_area
        return 0.0

    @property
    def transaction_key(self) -> str:
        """중복 방지 고유 키 (해시)"""
        raw = (
            f"{self.sgg_code}|{self.property_type}|{self.complex_name}|"
            f"{self.exclusive_area}|{self.contract_year}{self.contract_month:02d}{self.contract_day:02d}|"
            f"{self.price_manwon}"
        )
        return hashlib.md5(raw.encode()).hexdigest()


class KoreaLandAPI:
    """
    국토부 실거래가 공개 API 클라이언트

    지원 데이터:
    - 아파트 매매 (APT)
    - 다세대/연립 매매 (MULTI)
    - 오피스텔 매매 (OFFICETEL)
    """

    BASE_URL = "https://apis.data.go.kr/1613000"

    # 각 용도별 서비스명
    SERVICES = {
        "아파트":   "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
        "다세대":   "RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
        "연립":     "RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",    # 다세대와 동일 엔드포인트 (용도코드 분리)
        "오피스텔": "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
    }

    def __init__(self, api_key: str, timeout: int = 30, retry: int = 3):
        self.api_key = api_key
        self.timeout = timeout
        self.retry = retry
        self.session = requests.Session()

    @staticmethod
    def _safe_error(error: Exception) -> str:
        """요청 예외 문자열에 포함될 수 있는 serviceKey를 로그에서 제거한다."""
        return re.sub(r"(serviceKey=)[^&\s)]+", r"\1***", str(error))

    # ─── 공개 메서드 ──────────────────────────────────────────

    def fetch_apt_transactions(self, sgg_code: str, year: int, month: int
                               ) -> list[TransactionRecord]:
        """아파트 실거래가 조회"""
        return self._fetch(sgg_code, year, month, "아파트")

    def fetch_multi_transactions(self, sgg_code: str, year: int, month: int
                                 ) -> list[TransactionRecord]:
        """다세대/연립 실거래가 조회"""
        return self._fetch(sgg_code, year, month, "다세대")

    def fetch_office_transactions(self, sgg_code: str, year: int, month: int
                                  ) -> list[TransactionRecord]:
        """오피스텔 실거래가 조회"""
        return self._fetch(sgg_code, year, month, "오피스텔")

    def fetch_all_types(self, sgg_code: str, year: int, month: int
                        ) -> list[TransactionRecord]:
        """전 용도 실거래가 통합 조회"""
        results = []
        for ptype in ["아파트", "다세대", "오피스텔"]:
            try:
                records = self._fetch(sgg_code, year, month, ptype)
                results.extend(records)
                time.sleep(0.2)
            except Exception as e:
                logger.warning(f"[{ptype}] {sgg_code} {year}-{month:02d} 조회 실패: {e}")
        return results

    # ─── 내부 메서드 ──────────────────────────────────────────

    def _fetch(self, sgg_code: str, year: int, month: int,
               property_type: str) -> list[TransactionRecord]:
        """API 호출 + XML 파싱"""

        service = self.SERVICES.get(property_type)
        if not service:
            raise ValueError(f"지원하지 않는 property_type: {property_type}")

        params = {"serviceKey": self.api_key, "LAWD_CD": sgg_code, "DEAL_YMD": f"{year}{month:02d}"}
        pages = fetch_all_pages(
            self.session, f"{self.BASE_URL}/{service}", params,
            timeout=self.timeout, retry=self.retry,
            label=f"{sgg_code} {year}-{month:02d} [{property_type}]",
        )
        records = [rec for xml in pages for rec in self._parse_xml(xml, sgg_code, property_type)]
        logger.debug(f"[API] {property_type} {sgg_code} {year}-{month:02d}: {len(records)}건")
        return records

    def _parse_xml(self, xml_text: str, sgg_code: str,
                   property_type: str) -> list[TransactionRecord]:
        """XML 응답 파싱 → TransactionRecord 리스트"""

        records = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise RuntimeError(f"XML 파싱 오류: {e}") from e

        # 응답 코드 확인
        result_code = root.findtext(".//resultCode", "")
        if result_code not in ("00", "000"):
            result_msg = root.findtext(".//resultMsg", "")
            raise RuntimeError(f"API 오류 응답: {result_code} - {result_msg}")

        items = root.findall(".//item")

        for item in items:
            try:
                rec = self._parse_item(item, sgg_code, property_type)
                if rec:
                    records.append(rec)
            except Exception as e:
                logger.debug(f"item 파싱 오류: {e}")
                continue

        return records

    def _parse_item(self, item: ET.Element, sgg_code: str,
                    property_type: str) -> Optional[TransactionRecord]:
        """단일 item → TransactionRecord"""

        def text(tag: str, default: str = "") -> str:
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else default

        def int_val(tag: str, default: int = 0) -> int:
            val = text(tag).replace(",", "").strip()
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default

        def float_val(tag: str, default: float = 0.0) -> float:
            val = text(tag).replace(",", "").strip()
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        if is_cancelled(item):
            return None

        # 거래금액 파싱 (필수)
        price_str = text("거래금액", text("dealAmount"))
        price = int(price_str.replace(",", "").strip()) if price_str else 0
        if price <= 0:
            return None

        # 전용면적 (필수)
        area = float_val("전용면적") or float_val("excluUseAr")
        if area <= 0:
            return None

        # 단지명
        complex_name = (
            text("아파트") or text("aptNm") or
            text("연립다세대") or text("mhouseNm") or
            text("단지명") or text("offiNm") or "알수없음"
        )

        # 주소
        address_dong = text("법정동") or text("umdNm") or ""
        address_jibun = text("지번") or text("jibun") or ""

        # 거래 일자
        year_val = int_val("년") or int_val("dealYear")
        month_val = int_val("월") or int_val("dealMonth")
        day_val = int_val("일") or int_val("dealDay")

        if not (year_val and month_val):
            return None

        # 층
        floor_val = int_val("층") or int_val("floor")

        # 건축년도
        build_year = int_val("건축년도") or int_val("buildYear") or None
        if build_year == 0:
            build_year = None

        # 매도/매수인 구분
        seller_type = text("매도자구분") or text("slerGbn") or None
        buyer_type = text("매수자구분") or text("buyerGbn") or None

        return TransactionRecord(
            sgg_code=sgg_code,
            property_type=property_type,
            complex_name=complex_name,
            address_dong=address_dong,
            address_jibun=address_jibun,
            contract_year=year_val,
            contract_month=month_val,
            contract_day=day_val,
            price_manwon=price,
            exclusive_area=area,
            floor=floor_val,
            build_year=build_year,
            seller_type=seller_type,
            buyer_type=buyer_type,
        )
