# AVM Agent 시스템 개발 로드맵

**프로젝트**: rtech 기반 자동감정평가 Agent 개발  
**기간**: 2026-06-09 ~ 2026-09-09 (약 13주)  
**목표**: 25M+ 거래 DB + LLM Agent 통합 감정평가 시스템

---

## Week 1-2 : Phase 1 — 아키텍처 정의 & 데이터 모델 설계

### 주 목표
- ARCHITECTURE.md 검토 및 최종 승인
- DB 스키마 설계 완성
- 구현 세부 계획 수립

### 작업 항목

#### 1.1 DB 스키마 설계 (Days 1-3)
```python
# app/db/models.py 확장

# 신규 테이블: complexes (공동주택 단지)
class Complex(Base):
    __tablename__ = "complexes"
    id = Column(Integer, primary_key=True)
    complex_code = Column(String(20), unique=True)  # rtech 단지코드
    complex_name = Column(String(200), nullable=False)
    address_sido = Column(String(30))
    address_sigungu = Column(String(50))
    address_dong = Column(String(50))
    address_jibun = Column(String(100))
    address_roadname = Column(String(100))
    
    # 물리적 특성
    build_year = Column(Integer)
    total_units = Column(Integer)  # 총 호수
    total_area = Column(Float)  # 단지 총 면적
    
    # 메타 정보
    source = Column(String(20))  # 'rtech', 'api', 'manual'
    last_updated = Column(DateTime)
    
    # 관계
    units = relationship("Unit", back_populates="complex")
    transactions = relationship("Transaction", back_populates="complex")

# 신규 테이블: units (호실)
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True)
    complex_id = Column(Integer, ForeignKey("complexes.id"))
    
    # 호실 식별
    unit_code = Column(String(50), unique=True)  # 단지코드-동-호
    dong = Column(String(20))  # 동
    floor = Column(Integer)  # 층
    unit_num = Column(String(20))  # 호수
    
    # 면적
    exclusive_area = Column(Float)  # 전용면적 (㎡)
    supply_area = Column(Float)  # 공급면적 (㎡)
    parking_cnt = Column(Integer)  # 주차대수
    
    # 가격
    official_price_latest = Column(Numeric(20, 0))  # 최신 공시가격
    kb_price_latest = Column(Numeric(20, 0))  # 최신 KB 시세
    
    complex = relationship("Complex", back_populates="units")
    price_history = relationship("PriceHistory", back_populates="unit")
    transactions = relationship("Transaction", back_populates="unit")

# 신규 테이블: transactions (실거래가)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    
    # 거래 식별
    complex_id = Column(Integer, ForeignKey("complexes.id"))
    unit_id = Column(Integer, ForeignKey("units.id"))
    transaction_id = Column(String(50), unique=True)  # API 거래ID
    
    # 거래 일자
    contract_date = Column(Date)  # 계약일
    report_date = Column(Date)  # 신고일
    
    # 거래 정보
    price = Column(Numeric(20, 0), nullable=False)  # 거래가격
    price_per_area = Column(Numeric(15, 2))  # 평방미터당 가격
    seller = Column(String(100))  # 매도인 (마스킹)
    buyer = Column(String(100))  # 매수인 (마스킹)
    real_estate_agent = Column(String(100))  # 중개인
    
    # 데이터 품질
    verified = Column(Boolean, default=False)  # 검증 완료
    is_abnormal = Column(Boolean, default=False)  # 이상거래 플래그
    
    complex = relationship("Complex", back_populates="transactions")
    unit = relationship("Unit", back_populates="transactions")

# 신규 테이블: price_history (공시가격 이력)
class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("units.id"))
    
    price_date = Column(Date)  # 공시 기준일
    official_price = Column(Numeric(20, 0))  # 공시가격
    price_per_area = Column(Numeric(15, 2))  # 평방미터당
    
    __table_args__ = (
        UniqueConstraint('unit_id', 'price_date', name='uq_unit_date'),
    )
    
    unit = relationship("Unit", back_populates="price_history")

# 확장 테이블: comparable_sales (비교사례)
class ComparableSale(Base):
    __tablename__ = "comparable_sales"
    id = Column(Integer, primary_key=True)
    
    # 대상 물건 (NPL)
    npl_property_id = Column(Integer, ForeignKey("properties.id"))
    
    # 비교사례 (rtech)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    
    # 유사도 점수
    similarity_score = Column(Float)  # 0~1
    area_similarity = Column(Float)  # 면적
    location_similarity = Column(Float)  # 입지
    vintage_similarity = Column(Float)  # 연식
    type_similarity = Column(Float)  # 용도
    
    # 가중치
    weight = Column(Float)  # 최종 가중치
    
    npl_property = relationship("Property", back_populates="comparable_sales")
    transaction = relationship("Transaction")
```

**산출물**: 
- models.py 완성본
- ERD (복잡도 다이어그램)
- Schema 마이그레이션 스크립트 작성 시작

#### 1.2 데이터 수집 전략 확정 (Days 2-4)
- [ ] rtech 데이터 수집 방식 최종 결정 (크롤링 vs API vs 하이브리드)
- [ ] 공공API (data.go.kr) 신청서 작성
- [ ] Kakao Map API 신청 (거리 계산용)
- [ ] 필요 API 키 정리

**산출물**:
- API_KEYS.md (API 신청 현황)
- integration_plan.md (수집 방식 상세)

#### 1.3 코드 기본 구조 (Days 3-5)
```python
# 디렉토리 생성
mkdir -p app/integrations
mkdir -p app/ml
mkdir -p app/agent
mkdir -p scripts/migrations
mkdir -p tests

# requirements.txt 업데이트
# + aiohttp, beautifulsoup4, geopy, scikit-learn, anthropic, psycopg2, alembic

# app/config.py 생성 (환경변수 관리)
class Settings:
    database_url: str
    anthropic_api_key: str
    rtech_api_endpoint: str
    korea_api_key: str
    kakao_api_key: str
    
settings = Settings()
```

**산출물**:
- 기본 디렉토리 구조
- requirements.txt 업데이트
- config.py 작성

#### 1.4 팀 협업 설정 (Days 1-2)
- [ ] Git 브랜치 전략 (main / develop / feature/*) 수립
- [ ] PR 검토 체크리스트 작성
- [ ] 코드 스타일 가이드 확정 (Black, isort)
- [ ] 주간 회의 일정 확정 (목 10:00)

**산출물**:
- CONTRIBUTING.md (기여 가이드)
- .pre-commit-config.yaml (Linter 자동화)

---

## Week 3-4 : Phase 2 — rtech 데이터 수집

### 주 목표
- 24,197개 단지 마스터 데이터 수집 완료
- 1차 100만 호 호실 정보 적재

### 작업 항목

#### 2.1 rtech 크롤러 개발 (Days 1-5)

```python
# app/integrations/rtech_crawler.py

import aiohttp
import asyncio
from bs4 import BeautifulSoup

class RtechCrawler:
    """rtech.or.kr 크롤러"""
    
    BASE_URL = "https://www.rtech.or.kr/portal"
    
    async def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def fetch_complex_masters(self) -> List[ComplexMaster]:
        """
        전체 24,197개 단지 마스터 수집
        
        Strategy:
        1. 시도별 검색 페이지 순회
        2. 시군구별 단지 목록 파싱
        3. 단지코드, 단지명, 주소 추출
        
        Expected: 24,197 complexes in ~2-3시간
        """
        
        complexes = []
        sido_list = ['서울시', '부산시', '대구시', ...]  # 17개 시도
        
        for sido in sido_list:
            page = 1
            while True:
                url = f"{self.BASE_URL}/search/selectComplex.do?sido={sido}&pageNo={page}"
                try:
                    async with self.session.get(url, headers=self.headers) as resp:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 단지 목록 추출
                        complex_rows = soup.find_all('tr', class_='list-item')
                        
                        if not complex_rows:
                            break  # 마지막 페이지
                        
                        for row in complex_rows:
                            complex_data = {
                                'code': row.find('td', class_='code').text.strip(),
                                'name': row.find('td', class_='name').text.strip(),
                                'address': row.find('td', class_='address').text.strip(),
                                'build_year': int(row.find('td', class_='year').text.strip()),
                                'units': int(row.find('td', class_='units').text.strip())
                            }
                            complexes.append(complex_data)
                        
                        page += 1
                        await asyncio.sleep(0.5)  # Rate limit
                        
                except Exception as e:
                    print(f"Error fetching {sido} page {page}: {e}")
                    continue
        
        return complexes
    
    async def fetch_complex_units(self, complex_code: str) -> List[UnitMeta]:
        """
        단지별 호실 정보 수집
        
        Expected output per complex:
        {
            'unit_code': '단지코드-동-호',
            'dong': '101동',
            'floor': 3,
            'unit_num': '303',
            'exclusive_area': 84.92,
            'supply_area': 127.0,
            'parking': 1
        }
        """
        pass
    
    async def fetch_recent_transactions(self, complex_code: str, 
                                       months: int = 12) -> List[Transaction]:
        """
        최근 N개월 거래 정보 수집
        
        Note: 실제로는 공공API 활용 권장
        """
        pass

# 사용 예시
async def main():
    async with aiohttp.ClientSession() as session:
        crawler = RtechCrawler(session)
        complexes = await crawler.fetch_complex_masters()
        print(f"수집된 단지: {len(complexes)}")
        
        # DB에 저장
        db_manager.ingest_complexes(complexes)

if __name__ == "__main__":
    asyncio.run(main())
```

**체크리스트**:
- [ ] 크롤러 코드 작성
- [ ] Rate limiting 구현 (0.5초 간격)
- [ ] 에러 처리 및 재시도 로직
- [ ] 로깅 설정
- [ ] 단위 테스트 5개 이상

**산출물**:
- rtech_crawler.py 완성
- tests/test_rtech_crawler.py (주요 함수 테스트)
- 수집 성능 리포트 (초당 처리 건수)

#### 2.2 공공API 통합 (Days 3-5)

```python
# app/integrations/korea_api.py

import requests
import pandas as pd
from datetime import date, timedelta

class KoreaLandAPI:
    """
    국토부 실거래가 공개 API
    
    Rate Limit: 월 100만 건
    Update: 매월 15일경 이전달 데이터 공개
    """
    
    BASE_URL = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def fetch_apt_transactions(self, sgg_code: str, 
                               year: int, month: int) -> pd.DataFrame:
        """
        아파트 실거래가 조회
        
        Args:
            sgg_code: 시군구 코드 (예: 11110 = 서울 종로구)
            year, month: 거래 년월
        
        Returns:
            DataFrame with columns:
            ['거래금액', '건축년도', '도로명', '아파트', '층', '전용면적', 
             '지번', '지역코드', '년', '월', '일']
        """
        
        params = {
            'serviceKey': self.api_key,
            'LAWD_CD': sgg_code,
            'DEAL_YMD': f"{year}{month:02d}",
            'pageNo': 1,
            'numOfRows': 100000  # 최대
        }
        
        url = f"{self.BASE_URL}/DownloadTrade.NewAPIComponent"
        
        try:
            response = requests.get(url, params=params)
            # XML 파싱 후 DataFrame 변환
            df = self._parse_response(response)
            return df
        except Exception as e:
            print(f"API 오류: {e}")
            return pd.DataFrame()
    
    def fetch_multi_transactions(self, sgg_code: str, 
                                  year: int, month: int) -> pd.DataFrame:
        """다세대 실거래가 조회"""
        pass
    
    def fetch_office_transactions(self, sgg_code: str, 
                                   year: int, month: int) -> pd.DataFrame:
        """오피스텔 실거래가 조회"""
        pass
    
    def fetch_official_prices(self, sgg_code: str, 
                              year: int) -> pd.DataFrame:
        """공시가격 조회 (연 2회)"""
        pass

# 월별 자동 수집 스크립트
# scripts/fetch_korea_api.py

def fetch_all_regions_transactions(api_key: str, year: int, month: int):
    """
    전국 모든 시군구 거래 수집
    
    시군구 코드 245개 × 3 용도 = ~735 API 호출
    한 번에 100만 건 처리 가능
    """
    
    api = KoreaLandAPI(api_key)
    sgg_codes = load_sgg_codes()  # 245개 시군구
    
    for sgg_code in sgg_codes:
        for property_type in ['아파트', '다세대', '오피스텔']:
            df = api.fetch_apt_transactions(sgg_code, year, month)
            db.ingest_transactions(df, property_type)
            
            # DB 저장 후 1초 대기 (API 레이트 리밋)
            time.sleep(1)
    
    print(f"✓ {year}-{month} 데이터 적재 완료")
```

**체크리스트**:
- [ ] 공공API 키 발급 (2-3주 소요)
- [ ] API 문서 분석 및 매핑
- [ ] 시군구 코드 마스터 데이터 구축 (245개)
- [ ] 파싱 로직 작성 및 테스트
- [ ] 배치 스크립트 작성

**산출물**:
- korea_api.py 완성
- sgg_codes.json (시군구 코드 마스터)
- fetch_korea_api.py (월별 자동 수집 스크립트)

#### 2.3 데이터 검증 및 저장 (Days 4-6)

```python
# app/db/validators.py

class ComplexValidator:
    @staticmethod
    def validate_address(address: str, code: str) -> bool:
        """주소 정규화 및 검증"""
        pass
    
    @staticmethod
    def validate_area(total_area: float, unit_count: int) -> bool:
        """호당 평균면적 합리성 (최소 30㎡, 최대 500㎡)"""
        avg_area = total_area / unit_count if unit_count > 0 else 0
        return 30 <= avg_area <= 500

class TransactionValidator:
    @staticmethod
    def detect_abnormal_price(unit_price: float, 
                             complex_avg: float, 
                             z_score_threshold: float = 3.0) -> bool:
        """Z-score 기반 이상거래 탐지"""
        pass
    
    @staticmethod
    def validate_date_sequence(contract_date, report_date) -> bool:
        """계약일 ≤ 신고일 검증"""
        return contract_date <= report_date

# app/db/ingest.py 확장

def ingest_complexes(complexes: List[dict]):
    """단지 마스터 적재"""
    session = get_db_session()
    
    for complex_data in complexes:
        # 검증
        if not ComplexValidator.validate_address(
            complex_data['address'], complex_data['code']
        ):
            continue
        
        # DB 저장
        complex_obj = Complex(
            complex_code=complex_data['code'],
            complex_name=complex_data['name'],
            # ...
        )
        session.add(complex_obj)
    
    session.commit()
    print(f"✓ {len(complexes)} 단지 적재")

def ingest_transactions(transactions: pd.DataFrame, 
                       property_type: str):
    """거래 데이터 적재"""
    
    session = get_db_session()
    
    for _, row in transactions.iterrows():
        # 검증
        if TransactionValidator.detect_abnormal_price(
            float(row['거래금액']) / float(row['전용면적']),
            complex_avg=0  # 계산 필요
        ):
            continue
        
        # 주소 → complex_id 매핑
        complex_id = map_address_to_complex(row['도로명'])
        if not complex_id:
            continue
        
        # DB 저장
        transaction = Transaction(
            complex_id=complex_id,
            price=int(row['거래금액']),
            contract_date=parse_date(row['거래일']),
            # ...
        )
        session.add(transaction)
    
    session.commit()
    print(f"✓ {len(transactions)} 거래 적재")
```

**체크리스트**:
- [ ] Validator 클래스 작성
- [ ] 이상거래 탐지 알고리즘 구현
- [ ] ingest 함수 통합 및 테스트
- [ ] 데이터 품질 리포트 생성 (적재율, 검증율)

**산출물**:
- validators.py 완성
- 1차 데이터 적재 완료 (100만 호)
- QA 리포트 (적재율 95% 이상)

---

## Week 5 : Phase 2 마무리 & DB 최적화

### 5.1 인덱싱 및 성능 최적화

```python
# app/db/models.py 에 Index 추가

class Complex(Base):
    __table_args__ = (
        Index('idx_complex_code', 'complex_code'),
        Index('idx_complex_location', 'address_sido', 'address_sigungu'),
    )

class Transaction(Base):
    __table_args__ = (
        Index('idx_transaction_complex', 'complex_id'),
        Index('idx_transaction_date', 'report_date'),
        Index('idx_transaction_price', 'price'),
    )

class Unit(Base):
    __table_args__ = (
        Index('idx_unit_complex', 'complex_id'),
        Index('idx_unit_area', 'exclusive_area'),
    )
```

**체크리스트**:
- [ ] 조회 성능 벤치마크 (쿼리 실행 시간)
- [ ] 인덱스 추가 및 ANALYZE 실행
- [ ] 쿼리 최적화 (JOIN, GROUP BY)

### 5.2 Data Quality Dashboard (선택사항)

```python
# scripts/data_quality_report.py

def generate_quality_report():
    """데이터 품질 대시보드"""
    
    report = {
        'complexes': {
            'total': db.count_complexes(),
            'with_transactions': db.count_complexes_with_transactions(),
            'coverage_pct': db.count_complexes_with_transactions() / db.count_complexes() * 100
        },
        'transactions': {
            'total': db.count_transactions(),
            'abnormal': db.count_abnormal_transactions(),
            'verified': db.count_verified_transactions()
        },
        'temporal_coverage': {
            'earliest_date': db.get_earliest_transaction_date(),
            'latest_date': db.get_latest_transaction_date(),
            'months_covered': ...
        }
    }
    
    # HTML 리포트 생성
    generate_html_report(report)
```

**산출물**:
- data_quality_report.html
- performance_metrics.csv

---

## Week 6-7 : Phase 3 — NPL-rtech 데이터 통합

### 주 목표
- 기존 NPL 물건 2,645개 ↔ rtech 단지 매핑
- 비교사례 자동 추출

### 작업 항목

#### 3.1 주소 정규화 & 단지 매핑

```python
# app/db/mapping.py (신규)

import geopy
from geopy.geocoders import Nominatim

class PropertyMapper:
    """NPL 물건 ↔ rtech 단지 매핑"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="avm_mapper")
        self.address_cache = {}
    
    @staticmethod
    def normalize_address(address: str) -> str:
        """주소 정규화
        
        예: "경기도 화성시 봉담읍 가는길 12" 
            → "경기도 화성시 봉담읍"
        """
        parts = address.split()
        # 시도 + 시군구 + 동/읍/면 까지만 추출
        if len(parts) >= 3:
            return " ".join(parts[:3])
        return address
    
    def address_to_complex_id(self, npl_address: str) -> Optional[int]:
        """
        NPL 주소 → rtech 단지코드 매핑
        
        Strategy:
        1. 주소 정규화
        2. Exact match (주소로 DB 검색)
        3. Fuzzy match (유사도 > 80%)
        4. Geocoding (위도/경도 거리 < 100m)
        """
        
        # 1. Exact match
        normalized = self.normalize_address(npl_address)
        exact_match = db.query(Complex).filter(
            Complex.address_full.ilike(f"%{normalized}%")
        ).first()
        
        if exact_match:
            return exact_match.id
        
        # 2. Fuzzy match (difflib)
        from difflib import SequenceMatcher
        candidates = db.query(Complex).filter(
            Complex.address_sido == normalized.split()[0]
        ).all()
        
        best_match = None
        best_ratio = 0
        
        for candidate in candidates:
            ratio = SequenceMatcher(
                None, 
                normalized, 
                candidate.address_full
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
        
        if best_match and best_ratio > 0.8:
            return best_match.id
        
        # 3. Geocoding (느리므로 마지막)
        # ...
        
        return None
    
    def estimate_area_similarity(self, npl_area: float,
                                 unit_area: float,
                                 tolerance: float = 0.2) -> bool:
        """면적 유사도 검증
        
        오차율 > 20% 제외
        """
        if unit_area == 0:
            return False
        
        error_rate = abs(npl_area - unit_area) / unit_area
        return error_rate <= tolerance

# 사용 예시
def map_npl_to_rtech():
    """
    모든 NPL 물건에 rtech 단지 매핑
    
    Expected: 2,645 NPL 물건 중 ~80% (2,100개) 매핑 성공
    """
    
    mapper = PropertyMapper()
    npl_properties = db.query(Property).all()
    
    mapped_count = 0
    unmapped_count = 0
    
    for npl_prop in npl_properties:
        complex_id = mapper.address_to_complex_id(npl_prop.address_full)
        
        if complex_id:
            # NPL Property에 complex_id 저장
            npl_prop.complex_id = complex_id
            db.update(npl_prop)
            mapped_count += 1
        else:
            unmapped_count += 1
    
    print(f"매핑 성공: {mapped_count}/{len(npl_properties)} ({mapped_count/len(npl_properties)*100:.1f}%)")
    print(f"매핑 실패: {unmapped_count}")

# 스크립트 실행
# python scripts/map_npl_to_rtech.py
```

**체크리스트**:
- [ ] 정규화 로직 작성 및 테스트
- [ ] 매핑 함수 작성
- [ ] 전체 NPL 2,645개 매핑
- [ ] 매핑 정확도 검증 (샘플 100개 수동 확인)

**산출물**:
- mapping.py 완성
- mapping_results.csv (매핑 성공률 리포트)

#### 3.2 비교사례 자동 추출

```python
# app/avm/comparable_extraction.py (신규)

class ComparableExtractor:
    """NPL 물건 ↔ 비교사례 자동 매칭"""
    
    def extract_comparables(self, npl_property: Property, 
                           radius_km: float = 2.0,
                           lookback_months: int = 12) -> List[ComparableSale]:
        """
        NPL 물건의 비교사례 추출
        
        Matching 기준:
        1. 같은 단지 거래 (우선순위 높음)
        2. 인접 단지 거래 (거리 < 2km)
        3. 면적 유사도 > 70%
        4. 최근 12개월 거래
        5. 이상거래 제외
        """
        
        comparables = []
        
        # 1. 같은 단지 거래
        if npl_property.complex_id:
            same_complex = db.query(Transaction).filter(
                Transaction.complex_id == npl_property.complex_id,
                Transaction.report_date >= date.today() - timedelta(days=365),
                Transaction.is_abnormal == False
            ).all()
            
            for trans in same_complex:
                comp = ComparableSale(
                    npl_property_id=npl_property.id,
                    transaction_id=trans.id,
                    similarity_score=0.95,  # 같은 단지
                    weight=0.95
                )
                comparables.append(comp)
        
        # 2. 인접 단지 거래
        nearby_units = db.query(Unit).filter(
            # 거리 < radius_km
        ).all()
        
        for unit in nearby_units:
            # 면적 유사도 계산
            area_sim = self._calc_area_similarity(
                npl_property.building_area,
                unit.exclusive_area
            )
            
            if area_sim > 0.7:
                # 해당 호실의 최근 거래 조회
                recent_trans = db.query(Transaction).filter(
                    Transaction.unit_id == unit.id,
                    Transaction.report_date >= date.today() - timedelta(days=365)
                ).order_by(Transaction.report_date.desc()).first()
                
                if recent_trans:
                    comp = ComparableSale(
                        npl_property_id=npl_property.id,
                        transaction_id=recent_trans.id,
                        similarity_score=area_sim * 0.8,  # 인접 단지
                        weight=area_sim * 0.8
                    )
                    comparables.append(comp)
        
        return comparables
    
    def _calc_area_similarity(self, area1: float, 
                             area2: float) -> float:
        """면적 유사도 (0~1)"""
        if area2 == 0:
            return 0
        
        ratio = area1 / area2
        if ratio > 1:
            ratio = 1 / ratio
        
        return max(0, ratio - 0.1)  # 0~1 정규화

# 스크립트
# scripts/extract_comparables.py

def extract_all_comparables():
    """모든 NPL 물건 비교사례 추출"""
    
    extractor = ComparableExtractor()
    npl_props = db.query(Property).filter(
        Property.property_type.in_(['아파트', '다세대', '연립', '오피스텔'])
    ).all()
    
    total_comparables = 0
    
    for npl_prop in npl_props:
        comparables = extractor.extract_comparables(npl_prop)
        
        for comp in comparables:
            db.add(comp)
        
        total_comparables += len(comparables)
    
    db.commit()
    
    print(f"✓ 비교사례 {total_comparables}개 추출 완료")
    print(f"✓ 물건당 평균 {total_comparables/len(npl_props):.1f}개")
```

**체크리스트**:
- [ ] 추출 로직 작성
- [ ] 비교사례 테이블 데이터 저장
- [ ] 물건당 평균 비교사례 수 확인 (목표: 5개 이상)

**산출물**:
- comparable_extraction.py 완성
- comparable_stats.csv (물건별 비교사례 통계)

---

## Week 8-9 : Phase 4 — AVM Engine v2 개발

### 주 목표
- 확장된 AVM 로직 구현
- 신뢰도 범위 추정

### 작업 항목

#### 4.1 AVM Engine v2 구현

```python
# app/avm/engine_v2.py (신규)

from app.avm.comparable_extraction import ComparableExtractor
import numpy as np
from datetime import date, timedelta

class AVMEngineV2:
    """
    확장된 감정평가 엔진
    
    특징:
    - 다중 거래사례 기반
    - 시점수정계수 적용
    - 신뢰도 범위 추정
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.extractor = ComparableExtractor()
    
    def estimate(self, npl_property: Property,
                confidence_level: float = 0.85) -> AVMResult:
        """
        AVM 감정가 추정
        
        Output:
        {
            'point_estimate': 3500000,
            'lower_bound': 3200000,  # 보수적
            'upper_bound': 3800000,  # 낙관적
            'confidence_level': 0.85,
            'comparable_count': 8,
            'method': 'weighted_avg + time_adjustment'
        }
        """
        
        # Step 1: 비교사례 추출
        comparables = self.extractor.extract_comparables(npl_property)
        
        if len(comparables) < 1:
            raise ValueError("비교사례 부족 (최소 1개 필요)")
        
        # Step 2: 이상치 제거
        prices = [
            trans.price for trans in 
            [comp.transaction for comp in comparables]
        ]
        
        filtered_prices = self._remove_outliers(prices)
        
        if len(filtered_prices) == 0:
            # 이상치 제거 후 0개인 경우, 원본 사용
            filtered_prices = prices
        
        # Step 3: 시점수정계수 적용
        adjusted_prices = []
        
        for comparable in comparables:
            trans = comparable.transaction
            time_adjustment = self._calc_time_adjustment(
                trans.report_date,
                npl_property.address_sido
            )
            
            adjusted_price = trans.price * (1 + time_adjustment)
            adjusted_prices.append(adjusted_price)
        
        # Step 4: 가중평균
        weights = np.array([c.weight for c in comparables])
        weights = weights / weights.sum()  # 정규화
        
        point_estimate = np.dot(adjusted_prices, weights)
        
        # Step 5: 신뢰도 범위
        std_dev = np.std(adjusted_prices)
        z_score = 1.96  # 95% 신뢰도
        
        lower_bound = point_estimate - z_score * std_dev / np.sqrt(len(adjusted_prices))
        upper_bound = point_estimate + z_score * std_dev / np.sqrt(len(adjusted_prices))
        
        # Step 6: 결과 반환
        return AVMResult(
            property_id=npl_property.id,
            point_estimate=int(point_estimate),
            lower_bound=int(lower_bound),
            upper_bound=int(upper_bound),
            confidence_level=confidence_level,
            comparable_count=len(comparables),
            comparable_details=[
                {
                    'transaction_id': c.transaction_id,
                    'price': c.transaction.price,
                    'address': f"{c.transaction.complex.address_full}",
                    'date': c.transaction.report_date.isoformat(),
                    'similarity': c.similarity_score,
                    'weight': float(c.weight)
                }
                for c in comparables[:5]  # Top 5만 반환
            ],
            method='weighted_avg + time_adjustment',
            estimated_at=datetime.utcnow()
        )
    
    def _remove_outliers(self, prices: List[float],
                         iqr_multiplier: float = 1.5) -> List[float]:
        """
        IQR 기반 이상치 제거
        """
        prices_array = np.array(prices)
        q1 = np.percentile(prices_array, 25)
        q3 = np.percentile(prices_array, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr
        
        filtered = [p for p in prices 
                   if lower_bound <= p <= upper_bound]
        
        return filtered
    
    def _calc_time_adjustment(self, transaction_date: date,
                             sido: str) -> float:
        """
        시점수정계수 계산
        
        구성:
        - KB 시세변화율 (80%)
        - 지가변동률 (20%)
        """
        
        # 1. KB 시세변화율 조회 (매월 업데이트 필요)
        kb_rate = self._get_kb_price_change(sido, transaction_date)
        
        # 2. 지가변동률 조회 (공시지가 기반)
        land_rate = self._get_land_price_change(sido, transaction_date)
        
        # 가중평균
        adjustment = 0.8 * kb_rate + 0.2 * land_rate
        
        return adjustment
    
    def _get_kb_price_change(self, sido: str, 
                            from_date: date) -> float:
        """KB 시세변화율 조회
        
        Note: KB 부동산에서 월별 공개 데이터 활용
        """
        # DB에서 조회 또는 외부 API 호출
        # 임시로 0.02 (2% 상승) 반환
        return 0.02
    
    def _get_land_price_change(self, sido: str, 
                              from_date: date) -> float:
        """지가변동률 조회
        
        Note: 국토부 공시지가 기반
        """
        # DB에서 조회
        # 임시로 0.01 (1% 상승) 반환
        return 0.01

# Pydantic 모델
from pydantic import BaseModel

class AVMResult(BaseModel):
    property_id: int
    point_estimate: int
    lower_bound: int
    upper_bound: int
    confidence_level: float
    comparable_count: int
    comparable_details: List[dict]
    method: str
    estimated_at: datetime
```

**체크리스트**:
- [ ] AVMEngineV2 코드 작성
- [ ] 단위 테스트 10개 이상 (estimate, outlier removal, time adjustment)
- [ ] 샘플 물건 10개로 수동 검증

**산출물**:
- engine_v2.py 완성
- tests/test_engine_v2.py
- Sample AVM Report (10개 물건)

#### 4.2 API 통합

```python
# app/api/routes.py (확장)

from fastapi import APIRouter, HTTPException
from app.avm.engine_v2 import AVMEngineV2, AVMResult

router = APIRouter(prefix="/api/v2", tags=["AVM"])

@router.post("/avm/estimate", response_model=AVMResult)
async def estimate_avm(property_id: int,
                       db: Session = Depends(get_db)):
    """
    물건의 감정평가가 추정
    
    Example:
    POST /api/v2/avm/estimate?property_id=123
    
    Response:
    {
        "point_estimate": 3500000,
        "lower_bound": 3200000,
        "upper_bound": 3800000,
        ...
    }
    """
    
    try:
        npl_property = db.query(Property).filter(
            Property.id == property_id
        ).first()
        
        if not npl_property:
            raise HTTPException(status_code=404, detail="Property not found")
        
        engine = AVMEngineV2(db)
        result = engine.estimate(npl_property)
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**산출물**:
- routes.py 업데이트
- API 문서 (Swagger)

---

## Week 10 : Phase 5 — 헤도닉 회귀모델 (선택사항)

### 10.1 특성가격모형 구현

```python
# app/ml/hedonic.py (신규)

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import numpy as np

class HedhonicPriceModel:
    """
    특성가격모형 (Hedonic Price Model)
    
    종속변수: log(거래가)
    설명변수:
    - 건물 특성: 면적, 층수, 건축년도
    - 입지 특성: 역세권, 학군, 상업지구 거리
    - 시장 특성: 선행 지수, 대출금리
    """
    
    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.feature_names = None
    
    def extract_features(self, unit: Unit, 
                        complex: Complex) -> np.ndarray:
        """호실 정보 → 특성 벡터"""
        
        features = {
            # 건물 특성
            'area': unit.exclusive_area,
            'floor': unit.floor,
            'year': complex.build_year,
            
            # 입지 특성
            'parking': unit.parking_cnt,
            'complex_size': complex.total_units,
            
            # 시간 특성 (거래 시점)
            'month': 1,  # placeholder
        }
        
        return np.array(list(features.values()))
    
    def fit(self, transactions: List[Transaction]):
        """모델 학습"""
        
        X = []
        y = []
        
        for trans in transactions:
            features = self.extract_features(
                trans.unit,
                trans.complex
            )
            
            X.append(features)
            y.append(np.log(trans.price))  # 로그 변환
        
        X = np.array(X)
        y = np.array(y)
        
        # 스케일링
        X_scaled = self.scaler.fit_transform(X)
        
        # 학습
        self.model.fit(X_scaled, y)
        
        print(f"✓ 헤도닉 모델 학습 완료 (샘플: {len(transactions)})")
    
    def predict(self, unit: Unit, complex: Complex) -> float:
        """감정가 추정"""
        
        features = self.extract_features(unit, complex)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        log_price = self.model.predict(features_scaled)[0]
        price = np.exp(log_price)
        
        return price
    
    def feature_importance(self) -> dict:
        """특성 중요도"""
        
        importances = self.model.feature_importances_
        
        return {
            name: importance
            for name, importance in 
            zip(self.feature_names, importances)
        }

# 학습 스크립트
# scripts/train_hedonic_model.py

def train_hedonic_model():
    """헤도닉 모델 학습"""
    
    db = get_db_session()
    
    # 거래 데이터 수집 (최소 10만 건)
    transactions = db.query(Transaction).filter(
        Transaction.is_abnormal == False,
        Transaction.verified == True
    ).limit(100000).all()
    
    if len(transactions) < 10000:
        print("⚠ 거래 데이터 부족 (최소 10,000건)")
        return
    
    # 모델 학습
    model = HedhonicPriceModel()
    model.fit(transactions)
    
    # 모델 저장
    import pickle
    with open('data/hedonic_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("✓ 헤도닉 모델 저장 완료")
```

**체크리스트**:
- [ ] 모델 구현
- [ ] 10만 건 이상 거래로 학습
- [ ] Feature importance 분석
- [ ] 예측 정확도 평가 (R²)

---

## Week 11-12 : Phase 6 — LLM Agent 개발

### 주 목표
- Claude API 통합
- Tool Use 기반 자동화 Agent 개발

### 작업 항목

#### 11.1 Agent 아키텍처

```python
# app/agent/avm_agent.py (신규)

from anthropic import Anthropic
import json
from app.avm.engine_v2 import AVMEngineV2

class AVMAgent:
    """
    Claude 기반 자동감정평가 Agent
    
    사용자 질의 해석 → DB 검색 → AVM 추정 → 자연어 설명
    """
    
    def __init__(self, api_key: str, db_session):
        self.client = Anthropic()
        self.db = db_session
        self.engine = AVMEngineV2(db_session)
        self.model = "claude-3-5-sonnet-20241022"
        
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[dict]:
        """Tool definitions"""
        
        return [
            {
                "name": "search_property_by_address",
                "description": "주소로 물건 검색. 예: '경기도 화성시 봉담읍 아파트'",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "검색 주소 (시도/시군구/동)"
                        },
                        "property_type": {
                            "type": "string",
                            "description": "물건 유형 (아파트, 다세대, 연립, 오피스텔)",
                            "enum": ["아파트", "다세대", "연립", "오피스텔"]
                        }
                    },
                    "required": ["address"]
                }
            },
            {
                "name": "estimate_avm",
                "description": "물건의 감정평가가 추정",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "property_id": {
                            "type": "integer",
                            "description": "물건 ID"
                        }
                    },
                    "required": ["property_id"]
                }
            },
            {
                "name": "find_comparable_sales",
                "description": "특정 지역의 비교사례 조회",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sido": {"type": "string"},
                        "sigungu": {"type": "string"},
                        "limit": {
                            "type": "integer",
                            "description": "반환 결과 개수 (기본 10개)"
                        }
                    },
                    "required": ["sido", "sigungu"]
                }
            },
            {
                "name": "analyze_market_trends",
                "description": "특정 지역 거래 추세 분석",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sido": {"type": "string"},
                        "months": {
                            "type": "integer",
                            "description": "분석 기간 (개월)"
                        }
                    },
                    "required": ["sido"]
                }
            }
        ]
    
    def query(self, user_message: str) -> str:
        """
        사용자 질의 처리
        
        예시:
        - "경기도 화성시 아파트 감정가 알려줘"
        - "서울시 강남구 최근 거래 추세"
        - "이 건물의 비교사례 찾아줄래?"
        """
        
        messages = [{"role": "user", "content": user_message}]
        
        system_prompt = """
        당신은 부동산 감정평가 AI 어시스턴트입니다.
        사용자의 부동산 관련 질의에 정확하고 친절하게 답변하세요.
        
        Available tools를 활용하여 DB에서 데이터를 조회하고,
        감정평가 엔진으로 추정가를 계산한 후,
        사용자 친화적인 설명과 함께 답변하세요.
        
        답변 형식:
        1. 물건 정보 요약
        2. 감정평가 결과 (추정가 범위)
        3. 주요 비교사례
        4. 신뢰도 평가
        """
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=self.tools,
                messages=messages
            )
            
            # Stop condition
            if response.stop_reason == "end_turn":
                final_response = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        final_response = block.text
                        break
                
                return final_response
            
            # Tool use handling
            if response.stop_reason == "tool_use":
                # 모든 tool calls 수집
                tool_calls = [
                    block for block in response.content 
                    if block.type == "tool_use"
                ]
                
                # 각 tool call 실행
                tool_results = []
                
                for tool_call in tool_calls:
                    try:
                        result = self._execute_tool(
                            tool_call.name,
                            tool_call.input
                        )
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False, indent=2),
                            "is_error": False
                        })
                    
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
                
                # Messages 업데이트
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
        
        return "최대 반복 횟수 초과"
    
    def _execute_tool(self, tool_name: str, 
                     tool_input: dict) -> Any:
        """Tool 실행"""
        
        if tool_name == "search_property_by_address":
            properties = self.db.query(Property).filter(
                Property.address_full.ilike(f"%{tool_input['address']}%")
            ).limit(5).all()
            
            return {
                "count": len(properties),
                "properties": [
                    {
                        "id": p.id,
                        "address": p.address_full,
                        "type": p.property_type,
                        "area": p.building_area
                    }
                    for p in properties
                ]
            }
        
        elif tool_name == "estimate_avm":
            try:
                npl_prop = self.db.query(Property).filter(
                    Property.id == tool_input['property_id']
                ).first()
                
                if not npl_prop:
                    return {"error": "물건을 찾을 수 없습니다"}
                
                result = self.engine.estimate(npl_prop)
                
                return {
                    "property_id": result.property_id,
                    "point_estimate": result.point_estimate,
                    "lower_bound": result.lower_bound,
                    "upper_bound": result.upper_bound,
                    "confidence": result.confidence_level,
                    "comparables": len(result.comparable_details)
                }
            
            except ValueError as e:
                return {"error": str(e)}
        
        elif tool_name == "find_comparable_sales":
            transactions = self.db.query(Transaction).filter(
                Transaction.complex.has(
                    Complex.address_sido == tool_input['sido']
                )
            ).order_by(
                Transaction.report_date.desc()
            ).limit(
                tool_input.get('limit', 10)
            ).all()
            
            return {
                "count": len(transactions),
                "sales": [
                    {
                        "address": t.complex.address_full,
                        "price": int(t.price),
                        "date": t.report_date.isoformat(),
                        "area": t.unit.exclusive_area
                    }
                    for t in transactions
                ]
            }
        
        elif tool_name == "analyze_market_trends":
            from datetime import timedelta
            
            months = tool_input.get('months', 12)
            start_date = date.today() - timedelta(days=30*months)
            
            transactions = self.db.query(Transaction).filter(
                Transaction.complex.has(
                    Complex.address_sido == tool_input['sido']
                ),
                Transaction.report_date >= start_date
            ).all()
            
            prices = [t.price for t in transactions]
            
            return {
                "sido": tool_input['sido'],
                "period_months": months,
                "transaction_count": len(transactions),
                "avg_price": int(np.mean(prices)) if prices else 0,
                "price_trend": "상승" if len(prices) > 1 else "데이터 부족"
            }
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
```

**체크리스트**:
- [ ] Agent 코드 작성
- [ ] Tool 정의 및 구현
- [ ] 5가지 샘플 질의로 테스트
- [ ] 응답 품질 평가

**산출물**:
- avm_agent.py 완성
- Sample queries & responses

#### 11.2 Agent API 엔드포인트

```python
# app/api/routes.py (신규 라우터)

from app.agent.avm_agent import AVMAgent

router_agent = APIRouter(prefix="/api/v2/agent", tags=["Agent"])

@router_agent.post("/query")
async def agent_query(request: AgentQueryRequest,
                      db: Session = Depends(get_db)):
    """
    자연어 기반 감정평가 조회
    
    Example:
    POST /api/v2/agent/query
    {
        "query": "경기도 화성시 봉담읍 아파트 감정가 추정해줄래?"
    }
    
    Response:
    {
        "response": "화성시 봉담읍 아파트의 감정가는...",
        "estimated_price": 3500000,
        "confidence": 0.85
    }
    """
    
    try:
        agent = AVMAgent(settings.ANTHROPIC_API_KEY, db)
        response = agent.query(request.query)
        
        return {
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500)
```

**산출물**:
- routes_agent.py 추가
- API 문서 업데이트

---

## Week 13 : Phase 6 마무리 & 프로덕션 준비

### 13.1 종합 테스트

```python
# tests/test_avm_agent.py

import pytest

class TestAVMAgent:
    
    @pytest.fixture
    def agent(self, db_session):
        return AVMAgent(API_KEY, db_session)
    
    def test_search_property(self, agent):
        """물건 검색 테스트"""
        response = agent._execute_tool(
            "search_property_by_address",
            {"address": "경기도 화성시"}
        )
        assert response['count'] > 0
    
    def test_estimate_avm(self, agent):
        """감정평가 테스트"""
        response = agent._execute_tool(
            "estimate_avm",
            {"property_id": 1}
        )
        assert 'point_estimate' in response
    
    def test_full_query(self, agent):
        """전체 쿼리 테스트"""
        result = agent.query("경기도 화성시 아파트 감정가는?")
        assert len(result) > 0
```

**체크리스트**:
- [ ] 종합 테스트 실행
- [ ] 성능 벤치마크 (응답시간)
- [ ] 에러 핸들링 검증

### 13.2 배포 준비

```bash
# Docker 이미지 빌드
docker build -t avm-agent:latest .

# PostgreSQL 마이그레이션
alembic upgrade head

# 프로덕션 환경 설정
export ANTHROPIC_API_KEY=sk-...
export DATABASE_URL=postgresql://...

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**산출물**:
- Dockerfile
- docker-compose.yml
- .env.example
- deployment guide

### 13.3 성능 & 품질 지표

| 지표 | 목표 | 실제 |
|------|------|------|
| DB 규모 | 25M+ 거래 | ? |
| AVM 정확도 | MAPE < 10% | ? |
| API 응답시간 | < 100ms | ? |
| Agent 정확도 | > 95% | ? |

---

## 리소스 할당

| Phase | 주차 | 개발 | QA | 기타 |
|-------|------|------|----|----|
| 1 | 1-2 | 2 | 0.5 | 0.5 (기획) |
| 2 | 3-5 | 3 | 1 | 0.5 (API 신청) |
| 3 | 6-7 | 2 | 0.5 | 0.5 (검증) |
| 4 | 8-9 | 2 | 0.5 | - |
| 5 | 10 | 1 | 0.5 | - |
| 6 | 11-13 | 2 | 1 | 1 (배포) |
| **합계** | **13** | **12 PD** | **4 QA** | **3 기타** |

---

## 위험 관리

| 위험 | 확률 | 영향 | 대응 |
|------|------|------|------|
| rtech 크롤링 차단 | 중 | 높음 | 공공API 우선 추진 |
| API 한도 초과 | 중 | 중 | 월 분산 + 캐싱 |
| 주소 매핑 실패 | 중 | 중 | 지오코딩 + 수동 검증 |
| 거래 이상치 | 낮음 | 낮음 | IQR 제거 |
| Claude API 비용 | 낮음 | 중 | Rate limiting |

---

## 성공 기준

- [x] ARCHITECTURE.md 작성 완료
- [ ] Phase 2: 1차 100만 호 적재
- [ ] Phase 3: NPL 2,100개(80%) 매핑 성공
- [ ] Phase 4: AVM 엔진 v2 완성
- [ ] Phase 6: 자연어 Agent 정상 작동
- [ ] 5가지 샘플 쿼리 성공

---

**작성일**: 2026-06-09  
**최종 수정**: -  
**상태**: Draft (검토 대기)
