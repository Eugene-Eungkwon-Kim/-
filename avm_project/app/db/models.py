"""AVM 도메인 SQLAlchemy 모델.

이 모듈은 원래 존재하지 않았다 — app/avm/engine.py 와 app/api/routes.py
가 `from app.db.models import ...` 를 참조하고 있었지만 정작 모델
정의가 없어 앱이 임포트 단계에서부터 죽는 상태였다.

공식 스키마 설계 문서가 없어, 두 파일이 실제로 사용하는 컬럼을 전수
조사해 역산한 초안이다. 운영 DB 마이그레이션 전략은 팀 검토가 필요하다.
"""

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)
    deal_name = Column(String, nullable=False)
    financial_institution = Column(String)
    asset_date = Column(Date)

    properties = relationship("Property", back_populates="deal")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    property_serial = Column(String, unique=True, index=True, nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)

    address_full = Column(String)
    address_sido = Column(String, index=True)
    address_sigungu = Column(String, index=True)
    property_type = Column(String, index=True)
    property_category = Column(String)

    land_area = Column(Float)
    building_area = Column(Float)

    mortgage_amount = Column(Numeric)
    senior_burden_total = Column(Numeric)
    kb_market_price = Column(Numeric)

    deal = relationship("Deal", back_populates="properties")
    appraisals = relationship("Appraisal", back_populates="property")
    auctions = relationship("Auction", back_populates="property")


class Appraisal(Base):
    __tablename__ = "appraisals"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    appraisal_date = Column(Date)
    appraisal_type = Column(String)
    appraiser = Column(String)

    land_value = Column(Numeric)
    building_value = Column(Numeric)
    total_value = Column(Numeric)

    property = relationship("Property", back_populates="appraisals")


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    court = Column(String)
    case_number = Column(String)
    filing_date = Column(Date)
    first_legal_price = Column(Numeric)
    lapse_count = Column(Integer)
    final_result = Column(String)
    hammer_price = Column(Numeric)

    property = relationship("Property", back_populates="auctions")


class ComparableSale(Base):
    """거래사례(정밀 시트) — 감정평가/경매 이력과 무관한 독립 실거래 비교사례.

    `case_index == 0` 은 본건 자신, `> 0` 은 비교사례를 뜻한다(기존 쿼리
    코드의 `case_index > 0` 필터 기준으로 역산).
    """

    __tablename__ = "comparable_sales"

    id = Column(Integer, primary_key=True)
    subject_property_serial = Column(String, index=True)
    case_index = Column(Integer, default=0)
    # 국토부 실거래가 API 수집(app/integrations/db_ingest.py)의 중복 방지 키.
    # 그 외 경로로 입력되는 행은 채우지 않아도 되므로 nullable.
    transaction_key = Column(String, unique=True, index=True, nullable=True)

    address_full = Column(String)
    address_sido = Column(String, index=True)
    address_sigungu = Column(String, index=True)
    property_type = Column(String, index=True)
    use_zone = Column(String)
    structure = Column(String)

    land_area = Column(Float)
    building_area = Column(Float)
    approval_date = Column(Date)

    trade_date = Column(Date)
    trade_amount = Column(Numeric)
    unit_price_py = Column(Float)
    land_price_sqm = Column(Float)
    note = Column(String)
