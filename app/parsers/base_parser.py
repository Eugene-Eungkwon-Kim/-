from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
import re


@dataclass
class PropertyRecord:
    # 물건 식별
    property_serial: str = ""
    property_index: Optional[int] = None

    # 소재지
    address_sido: str = ""
    address_sigungu: str = ""
    address_dong: str = ""
    address_detail: str = ""

    # 자산 유형
    property_type: str = ""
    property_category: str = ""  # 집합건물/토지건물/토지/기계

    # 면적
    land_area: Optional[float] = None
    building_area: Optional[float] = None

    # 근저당권
    currency: str = "KRW"
    mortgage_amount: Optional[Decimal] = None
    mortgage_rank: str = ""
    senior_mortgage_amount: Optional[Decimal] = None

    # 선순위 부담
    has_provisional_seizure: Optional[bool] = None
    provisional_seizure_amount: Optional[Decimal] = None
    has_lien: Optional[bool] = None
    lien_amount: Optional[Decimal] = None
    small_deposit_housing: Optional[Decimal] = None
    small_deposit_commercial: Optional[Decimal] = None
    lease_deposit_housing: Optional[Decimal] = None
    lease_deposit_commercial: Optional[Decimal] = None
    wage_claim: Optional[Decimal] = None
    current_tax: Optional[Decimal] = None
    tax_claim: Optional[Decimal] = None
    senior_burden_total: Optional[Decimal] = None

    # 시세
    kb_market_price: Optional[Decimal] = None
    kb_price_date: Optional[date] = None

    # 감정평가
    appraisal_type: str = ""
    appraisal_date: Optional[date] = None
    appraiser: str = ""
    land_value: Optional[Decimal] = None
    building_value: Optional[Decimal] = None
    machine_value: Optional[Decimal] = None
    outside_value: Optional[Decimal] = None
    total_value: Optional[Decimal] = None

    # 경매
    is_filed: Optional[bool] = None
    court: str = ""
    creditor: str = ""
    case_number: str = ""
    filing_date: Optional[date] = None
    demand_deadline: Optional[date] = None
    claim_amount: Optional[Decimal] = None
    first_legal_price: Optional[Decimal] = None
    first_auction_date: Optional[date] = None
    lapse_count: Optional[int] = None
    final_result: str = ""
    final_auction_date: Optional[date] = None
    next_auction_date: Optional[date] = None
    hammer_price: Optional[Decimal] = None
    final_min_bid: Optional[Decimal] = None
    next_min_bid: Optional[Decimal] = None


@dataclass
class DebtorRecord:
    debtor_serial: str = ""
    debtor_name: str = ""
    debtor_type: str = "Regular"
    pool_class: str = "A"
    properties: list = field(default_factory=list)


@dataclass
class DealRecord:
    deal_name: str = ""
    pool_name: str = ""
    financial_institution: str = ""
    asset_date: Optional[date] = None
    source_file: str = ""
    debtors: list = field(default_factory=list)


class BaseParser(ABC):
    """금융기관별 Data Disk 파서 기반 클래스"""

    PROPERTY_TYPE_MAP = {
        "아파트": "집합건물",
        "오피스텔": "집합건물",
        "상가": "집합건물",
        "근린상가": "집합건물",
        "집합건물": "집합건물",
        "단독주택": "토지건물",
        "다가구": "토지건물",
        "공장": "토지건물",
        "창고": "토지건물",
        "빌딩": "토지건물",
        "근린생활": "토지건물",
        "토지": "토지",
        "대지": "토지",
        "임야": "토지",
        "전": "토지",
        "답": "토지",
        "기계": "기계기구",
        "설비": "기계기구",
    }

    @abstractmethod
    def parse(self, file_path: str) -> DealRecord:
        pass

    def _clean_amount(self, value) -> Optional[Decimal]:
        if value is None:
            return None
        s = str(value).replace(",", "").replace(" ", "").strip()
        if s in ("", "-", "N/A", "추후제공", "nan"):
            return None
        try:
            return Decimal(s)
        except Exception:
            return None

    def _clean_float(self, value) -> Optional[float]:
        if value is None:
            return None
        s = str(value).replace(",", "").strip()
        if s in ("", "-", "N/A", "추후제공", "nan"):
            return None
        try:
            return float(s)
        except Exception:
            return None

    def _clean_date(self, value) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        s = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                from datetime import datetime
                return datetime.strptime(s[:10], fmt).date()
            except Exception:
                continue
        return None

    def _infer_category(self, property_type: str) -> str:
        for keyword, category in self.PROPERTY_TYPE_MAP.items():
            if keyword in property_type:
                return category
        return "토지건물"
