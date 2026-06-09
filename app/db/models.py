from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, Text, Boolean, Numeric, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ─── NPL 영역 (기존) ────────────────────────────────────────

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)
    deal_name = Column(String(100), nullable=False)       # e.g. "IBK 2025-1 Program"
    pool_name = Column(String(50))                         # e.g. "Pool A"
    financial_institution = Column(String(50))             # IBK, KB, MG, 우리FNI 등
    asset_date = Column(Date)                              # 자산확정일
    vintage_year = Column(Integer)
    vintage_quarter = Column(String(10))
    source_file = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    properties = relationship("Property", back_populates="deal")
    debtors = relationship("Debtor", back_populates="deal")


class Debtor(Base):
    __tablename__ = "debtors"

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    debtor_serial = Column(String(50))                     # 차주일련번호
    debtor_name = Column(String(200))                      # 차주명 (마스킹)
    debtor_type = Column(String(20))                       # Regular / 회생
    pool_class = Column(String(10))                        # A, B, C 등

    deal = relationship("Deal", back_populates="debtors")
    properties = relationship("Property", back_populates="debtor")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    debtor_id = Column(Integer, ForeignKey("debtors.id"))

    # 물건 식별
    property_serial = Column(String(50))                   # 물건번호 (R-001-1 등)
    property_index = Column(Integer)                       # 물건 순서

    # 소재지
    address_sido = Column(String(30))                      # 특별/광역시/도
    address_sigungu = Column(String(50))                   # 시/군/구
    address_dong = Column(String(50))                      # 동/리/읍/면
    address_detail = Column(String(300))                   # 나머지 상세
    address_full = Column(String(500))                     # 전체 주소 (조합)

    # 자산 유형
    property_type = Column(String(50))                     # 창고, 아파트, 토지 등
    property_category = Column(String(30))                 # 집합건물/토지건물/토지/기계

    # 면적
    land_area = Column(Float)                              # 대지면적 (㎡)
    building_area = Column(Float)                          # 건물면적 (㎡)
    other_area = Column(String(100))                       # 기타(기계기구 등)

    # 근저당권
    currency = Column(String(10), default="KRW")
    mortgage_amount = Column(Numeric(20, 0))               # 근저당권설정액
    mortgage_rank = Column(String(50))                     # 설정순위
    senior_mortgage_amount = Column(Numeric(20, 0))        # 선순위근저당권설정액

    # 선순위 부담
    has_provisional_seizure = Column(Boolean)              # 가압류/압류/가처분 유무
    provisional_seizure_amount = Column(Numeric(20, 0))
    has_lien = Column(Boolean)                             # 유치권
    lien_amount = Column(Numeric(20, 0))
    small_deposit_housing = Column(Numeric(20, 0))         # 소액보증금(주택)
    small_deposit_commercial = Column(Numeric(20, 0))      # 소액보증금(상가)
    lease_deposit_housing = Column(Numeric(20, 0))         # 임차보증금(주택)
    lease_deposit_commercial = Column(Numeric(20, 0))      # 임차보증금(상가)
    wage_claim = Column(Numeric(20, 0))                    # 임금채권
    current_tax = Column(Numeric(20, 0))                   # 당해세
    tax_claim = Column(Numeric(20, 0))                     # 조세채권
    senior_burden_total = Column(Numeric(20, 0))           # 선순위 합계

    # 시세
    kb_market_price = Column(Numeric(20, 0))               # KB아파트시세
    kb_price_date = Column(Date)

    # [신규] rtech 단지 연결
    complex_id = Column(Integer, ForeignKey("complexes.id"), nullable=True)

    deal = relationship("Deal", back_populates="properties")
    debtor = relationship("Debtor", back_populates="properties")
    appraisals = relationship("Appraisal", back_populates="property")
    auctions = relationship("Auction", back_populates="property")
    rtech_comparables = relationship("RtechComparable", back_populates="npl_property")

    # complex_id 가 있으면 단지 정보도 접근 가능
    complex = relationship("Complex", back_populates="npl_properties", foreign_keys=[complex_id])

    __table_args__ = (
        Index("ix_property_address", "address_sido", "address_sigungu", "address_dong"),
        Index("ix_property_type", "property_type"),
        Index("ix_property_complex", "complex_id"),
    )


class Appraisal(Base):
    __tablename__ = "appraisals"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    appraisal_type = Column(String(20))                    # 구감정가 / 신감정가
    appraisal_date = Column(Date)
    appraiser = Column(String(100))                        # 감정평가기관
    land_value = Column(Numeric(20, 0))                    # 토지감정평가액
    building_value = Column(Numeric(20, 0))                # 건물감정평가액
    machine_value = Column(Numeric(20, 0))                 # 기계평가액
    outside_value = Column(Numeric(20, 0))                 # 제시외
    total_value = Column(Numeric(20, 0))                   # 감정평가액합계
    source_file = Column(String(500))                      # 감정평가서 PDF 경로

    property = relationship("Property", back_populates="appraisals")


class AppraisalComparable(Base):
    """감정평가서 PDF에서 추출한 비교사례 (기존 comparable_sales → 이름 변경)"""
    __tablename__ = "appraisal_comparables"

    id = Column(Integer, primary_key=True)
    source_file = Column(String(500))                        # 출처 파일
    subject_property_serial = Column(String(100))            # 본건 물건번호
    case_index = Column(Integer)                             # 1~N번째 사례

    # 소재지
    address_full = Column(String(500))
    address_sido = Column(String(30))
    address_sigungu = Column(String(50))
    address_dong = Column(String(50))

    # 물건 정보
    property_type = Column(String(50))
    use_zone = Column(String(50))
    land_area = Column(Float)
    building_area = Column(Float)
    structure = Column(String(50))
    approval_date = Column(Date)

    # 거래 정보
    trade_amount = Column(Numeric(20, 0))
    trade_date = Column(Date)
    unit_price_py = Column(Float)
    land_price_sqm = Column(Float)
    note = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_appr_comp_address", "address_sido", "address_sigungu"),
        Index("ix_appr_comp_type", "property_type"),
    )


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    is_filed = Column(Boolean)
    court = Column(String(100))
    creditor = Column(String(100))
    case_number = Column(String(100))
    filing_date = Column(Date)
    demand_deadline = Column(Date)
    claim_amount = Column(Numeric(20, 0))

    first_legal_price = Column(Numeric(20, 0))
    first_auction_date = Column(Date)
    lapse_count = Column(Integer)
    final_result = Column(String(30))
    final_auction_date = Column(Date)
    next_auction_date = Column(Date)
    hammer_price = Column(Numeric(20, 0))
    final_min_bid = Column(Numeric(20, 0))
    next_min_bid = Column(Numeric(20, 0))

    property = relationship("Property", back_populates="auctions")


class ComparableSale(Base):
    """거래사례 - 정밀 시트에서 추출한 실거래 비교사례"""
    __tablename__ = "comparable_sales"

    id = Column(Integer, primary_key=True)
    source_file = Column(String(500))
    subject_property_serial = Column(String(100))
    case_index = Column(Integer)

    address_full = Column(String(500))
    address_sido = Column(String(30))
    address_sigungu = Column(String(50))
    address_dong = Column(String(50))

    property_type = Column(String(50))
    use_zone = Column(String(50))
    land_area = Column(Float)
    building_area = Column(Float)
    structure = Column(String(50))
    approval_date = Column(Date)

    trade_amount = Column(Numeric(20, 0))
    trade_date = Column(Date)
    unit_price_py = Column(Float)
    land_price_sqm = Column(Float)
    note = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_comp_address", "address_sido", "address_sigungu"),
        Index("ix_comp_type", "property_type"),
    )


# ─── rtech 공동주택 영역 (신규) ─────────────────────────────

class Complex(Base):
    """공동주택 단지 마스터 (rtech / 국토부 공공API)"""
    __tablename__ = "complexes"

    id = Column(Integer, primary_key=True)
    complex_code = Column(String(30), unique=True)           # rtech 단지코드 (없으면 자동생성)
    complex_name = Column(String(200), nullable=False)
    property_type = Column(String(20), default="아파트")     # 아파트/다세대/연립/오피스텔

    # 주소
    address_sido = Column(String(30))
    address_sigungu = Column(String(50))
    address_dong = Column(String(50))
    address_jibun = Column(String(150))
    address_roadname = Column(String(200))
    address_full = Column(String(400))

    # 물리적 특성
    build_year = Column(Integer)
    total_units = Column(Integer)                            # 총 호수
    total_area = Column(Float)                               # 단지 총 면적 (㎡)
    floor_count = Column(Integer)                            # 최고 층수

    # 출처 및 갱신
    source = Column(String(20), default="api")               # rtech / api / manual
    last_updated = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    units = relationship("Unit", back_populates="complex", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="complex")
    npl_properties = relationship("Property", back_populates="complex",
                                  foreign_keys="Property.complex_id")

    __table_args__ = (
        Index("ix_complex_code", "complex_code"),
        Index("ix_complex_location", "address_sido", "address_sigungu"),
        Index("ix_complex_dong", "address_sido", "address_sigungu", "address_dong"),
        Index("ix_complex_type", "property_type"),
        Index("ix_complex_name", "complex_name"),
    )


class Unit(Base):
    """호실 정보 (동/호/전용면적)"""
    __tablename__ = "units"

    id = Column(Integer, primary_key=True)
    complex_id = Column(Integer, ForeignKey("complexes.id"), nullable=False)

    unit_code = Column(String(60), unique=True)              # {complex_code}-{dong}-{unit_num}
    dong = Column(String(20))
    floor = Column(Integer)
    unit_num = Column(String(20))

    exclusive_area = Column(Float)                           # 전용면적 (㎡)
    supply_area = Column(Float)                              # 공급면적 (㎡)
    parking_cnt = Column(Integer, default=1)

    official_price_latest = Column(Numeric(20, 0))           # 최신 공시가격
    kb_price_latest = Column(Numeric(20, 0))                 # 최신 KB 시세

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    complex = relationship("Complex", back_populates="units")
    price_history = relationship("PriceHistory", back_populates="unit",
                                 cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="unit")

    __table_args__ = (
        Index("ix_unit_complex", "complex_id"),
        Index("ix_unit_area", "exclusive_area"),
    )


class Transaction(Base):
    """실거래 정보 (국토부 공공API)"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    complex_id = Column(Integer, ForeignKey("complexes.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"))        # 호실 매핑 가능 시

    # 중복 방지 키
    transaction_key = Column(String(100), unique=True)       # hash(sgg+단지+면적+날짜+가격)

    # 거래 일자
    contract_year = Column(Integer)
    contract_month = Column(Integer)
    contract_day = Column(Integer)
    contract_date = Column(Date)
    report_date = Column(Date)

    # 거래 정보
    price = Column(Numeric(20, 0), nullable=False)           # 거래가격 (원)
    price_per_area = Column(Numeric(15, 2))                  # 전용㎡당 가격
    exclusive_area = Column(Float)                           # 거래 당시 전용면적
    floor = Column(Integer)

    seller_type = Column(String(20))                         # 매도인 구분 (개인/법인 등)
    buyer_type = Column(String(20))                          # 매수인 구분

    sgg_code = Column(String(10))                            # 시군구 코드
    property_type = Column(String(20))                       # 아파트/다세대/연립/오피스텔

    verified = Column(Boolean, default=False)
    is_abnormal = Column(Boolean, default=False)             # IQR 이상거래 플래그

    created_at = Column(DateTime, default=datetime.utcnow)

    complex = relationship("Complex", back_populates="transactions")
    unit = relationship("Unit", back_populates="transactions")

    __table_args__ = (
        Index("ix_transaction_complex", "complex_id"),
        Index("ix_transaction_date", "report_date"),
        Index("ix_transaction_contract", "contract_year", "contract_month"),
        Index("ix_transaction_price", "price"),
        Index("ix_transaction_type", "property_type"),
        Index("ix_transaction_sgg", "sgg_code"),
        Index("ix_transaction_area", "exclusive_area"),
    )


class PriceHistory(Base):
    """공시가격 이력 (연 2회 — 1월 1일, 4월 30일 기준)"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    price_date = Column(Date, nullable=False)                # 공시 기준일
    official_price = Column(Numeric(20, 0), nullable=False)
    price_per_area = Column(Numeric(15, 2))

    created_at = Column(DateTime, default=datetime.utcnow)

    unit = relationship("Unit", back_populates="price_history")

    __table_args__ = (
        UniqueConstraint("unit_id", "price_date", name="uq_unit_price_date"),
        Index("ix_price_hist_unit", "unit_id"),
        Index("ix_price_hist_date", "price_date"),
    )


class RtechComparable(Base):
    """NPL 물건 ↔ rtech 실거래 비교사례 매핑"""
    __tablename__ = "rtech_comparables"

    id = Column(Integer, primary_key=True)
    npl_property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)

    # 유사도 세부 점수 (0~1)
    similarity_score = Column(Float)                         # 종합
    area_similarity = Column(Float)                          # 면적
    location_similarity = Column(Float)                      # 입지 (거리 기반)
    vintage_similarity = Column(Float)                       # 연식 (건축년도)
    type_similarity = Column(Float)                          # 용도

    weight = Column(Float)                                   # 최종 가중치 (정규화)

    created_at = Column(DateTime, default=datetime.utcnow)

    npl_property = relationship("Property", back_populates="rtech_comparables")
    transaction = relationship("Transaction")

    __table_args__ = (
        UniqueConstraint("npl_property_id", "transaction_id", name="uq_rtech_comparable"),
        Index("ix_rtech_comp_property", "npl_property_id"),
        Index("ix_rtech_comp_score", "similarity_score"),
    )


class PriceIndex(Base):
    """시점수정계수 캐시 (KB 시세지수, 지가변동률)"""
    __tablename__ = "price_indices"

    id = Column(Integer, primary_key=True)
    index_type = Column(String(20), nullable=False)          # kb_apt / land
    sido = Column(String(30), nullable=False)
    ref_date = Column(Date, nullable=False)                  # 기준일 (월별)
    index_value = Column(Float, nullable=False)              # 지수 (기준=100)
    mom_change = Column(Float)                               # 전월 대비 변화율
    yoy_change = Column(Float)                               # 전년동월 대비 변화율

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("index_type", "sido", "ref_date", name="uq_price_index"),
        Index("ix_price_index_lookup", "index_type", "sido", "ref_date"),
    )
