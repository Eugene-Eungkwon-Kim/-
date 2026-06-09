# rtech 기반 AVM Agent 시스템 아키텍처 설계

**목표**: rtech.or.kr 24,197개 단지(10,262,142호) + 다세대/연립/오피스텔 전국 데이터 기반 **자동감정평가 Agent 개발**

**최종 완성 상태**:
- 공동주택 실거래가/시세 DB (25M+ 거래)
- 기존 NPL 감정가 데이터 연동 (2,645개 물건)
- LLM Agent 기반 자연어 감정평가 API

---

## 1. 시스템 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Agent 레이어                          │
│  (Claude API → 자연어 해석 → SQL 생성 → 감정가 추정)        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Unified AVM Engine (Python)                     │
│  • 유사단지 비교법                                           │
│  • 헤도닉 회귀모델                                           │
│  • 시점수정계수 (KB시세, 지가변동률)                         │
│  • 근처 거래 분석                                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Unified DB Layer (PostgreSQL)                   │
│  ┌──────────────────┬──────────────────┬──────────────────┐ │
│  │  NPL 담보물건    │   공동주택 DB     │  다세대/연립     │ │
│  │  (2,645개)       │  (10M+ 호)        │  오피스텔        │ │
│  └──────────────────┴──────────────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Data Ingestion Pipelines                        │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ rtech 크롤러  │ 국토부 API   │  기존 NPL 파서 (7종)     │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 핵심 데이터 구조

### 2.1 확장된 DB 스키마 (현재 → 목표)

#### **현재 (NPL 담보물건 중심)**
```
deals (27개 딜)
  ├── debtors (차주)
  └── properties (2,645개 물건)
      ├── appraisals (감정가)
      └── auctions (경매)
```

#### **목표 (rtech 통합)**
```
─── NPL 영역 (기존) ───────────────────────────
deals
  ├── debtors
  └── properties (2,645개)
      ├── appraisals
      └── auctions

─── rtech 공동주택 영역 (신규) ────────────────
complexes (24,197개 단지)
  ├── complex_meta (단지명, 주소, 건축년도, 동수 등)
  ├── units (10,262,142개 호)
  │   ├── floor, unit_num, exclusive_area, supply_area
  │   ├── official_price (공시가격)
  │   └── kb_market_price (KB시세)
  ├── transactions (실거래가 — 25M+ 거래)
  │   ├── transaction_date, price, seller, buyer
  │   ├── contract_date, report_date
  │   └── verified_flag
  └── prices (시점별 공시가격)
      ├── price_date, official_price
      └── price_per_area

─── 다세대/연립/오피스텔 영역 (신규) ────────
buildings
  ├── building_meta (주소, 용도, 건축년도)
  ├── units (호실)
  │   ├── floor, unit_area, unit_type
  │   └── unit_prices (공시가격)
  └── transactions

─── 통합 비교사례 영역 ──────────────────────
comparable_sales (비교사례 맵핑)
  ├── source_property_id (NPL 물건 또는 다른 자산)
  ├── reference_complex_id (참고 단지)
  ├── reference_unit_id (참고 호실)
  ├── similarity_score (면적, 연식, 입지)
  ├── transaction_price (거래사례가)
  └── transaction_date
```

---

### 2.2 NPL 물건 ↔ rtech 단지 매핑 전략

**핵심 식별자**:
1. **주소 정규화** (현재 주소 → 도로명 + 지번 변환)
   - 예: "경기도 화성시 봉담읍 ~" → rtech 단지코드 자동 매칭

2. **property_type 통합**
   - NPL: "창고", "아파트", "토지", "빌라" → 
   - rtech: "아파트", "다세대", "연립", "오피스텔"
   - Mapping Table 필요

3. **면적/동/호 기반 유사도**
   - 건물면적 (NPL) ↔ 공급면적 (rtech)
   - 편차율 > 20% 제외

**구현**:
```python
# app/db/mapping.py (신규)
class PropertyMapper:
    @staticmethod
    def address_to_complex_id(address_full: str) -> Optional[int]:
        """NPL 주소 → rtech 단지코드 매칭"""
        pass
    
    @staticmethod
    def estimate_area_similarity(npl_area: float, 
                                 unit_area: float) -> float:
        """면적 유사도 (0~1)"""
        pass
```

---

## 3. 데이터 수집 전략

### 3.1 rtech 크롤러 (Phase 1)

**목표**: 24,197개 단지 마스터 + 단지별 호실 구성 수집

**URL 분석**:
```
https://www.rtech.or.kr/portal/main/indexPage.do
  ├── 단지 검색: /search/selectComplex.do
  ├── 단지 상세: /showcomplex/selectShowComplex.do?complexNo={ID}
  └── 실거래: /contract/selectContractList.do?complexNo={ID}
```

**수집 데이터**:
- complexNo (단지코드)
- complexName (단지명)
- address (시도/시군구/동)
- buildYear (건축년도)
- complexUnit (총 호수)
- unitInfo (동/호별 면적)
- official_price (공시가격)

**구현**:
```python
# app/integrations/rtech_crawler.py (신규)
class RtechCrawler:
    async def fetch_complex_masters(self) -> List[ComplexMeta]:
        """전체 24,197개 단지 수집"""
        
    async def fetch_complex_units(self, complex_id: str) -> List[Unit]:
        """단지별 호실 정보 수집"""
        
    async def fetch_transactions(self, complex_id: str, 
                                 start_date: date, 
                                 end_date: date) -> List[Transaction]:
        """실거래가 수집"""
```

**제약**:
- rtech는 크롤링 금지 약관 검토 필수
- **권장**: 공공 API(data.go.kr) 활용이 더 안정적

---

### 3.2 공공 데이터 API 연동 (Phase 2) — **권장**

**국토부 실거래가 공개 API** (data.go.kr)

| API | 설명 | 수집 주기 |
|-----|------|---------|
| 아파트 실거래 | 아파트 거래 데이터 | 월별 |
| 다세대/연립 실거래 | 다세대/연립 거래 | 월별 |
| 오피스텔 실거래 | 오피스텔 거래 | 월별 |
| 공동주택 공시가격 | 아파트/다세대/연립/오피스텔 | 연 2회 |

**구현**:
```python
# app/integrations/korea_api.py (신규)
class KoreaLandAPI:
    def __init__(self, api_key: str):
        self.base_url = "http://openapi.molit.go.kr"
        
    def fetch_apt_transactions(self, sgg_code: str, 
                               year: int, month: int):
        """아파트 실거래가 조회 (최대 100만 건)"""
        
    def fetch_multi_transactions(self, sgg_code: str, 
                                 year: int, month: int):
        """다세대/연립 실거래가 조회"""
        
    def fetch_office_transactions(self, sgg_code: str, 
                                  year: int, month: int):
        """오피스텔 실거래가 조회"""
        
    def fetch_official_prices(self, complex_code: str, 
                              year: int):
        """공시가격 조회"""
```

**API 신청**: 
- 담당: 한국부동산원 / 국토부
- 기간: 1-2주 소요
- 최대 처리: 월 1,000만 건 가능

---

### 3.3 기존 NPL 파서 유지

**현재 구현** (변경 없음):
- IBK, IBK_ALLOC, KB, DGB, SH, HANA 파서 작동
- 월 1회 신규 딜 추가 적재

**신규 추가** (필요시):
- MG, 우리FNI, JBB, NH 파서 구현

---

## 4. 데이터 흐름 및 변환

### 4.1 수집 → DB 저장

```python
# 파이프라인 구조 (Phase별)

─── Phase 1: rtech 크롤러 ─────────────────────
Raw HTML
  ↓
RtechCrawler.fetch_complex_masters()
  ↓
ComplexMeta (dataclass)
  ↓
ingest_complexes() → complexes 테이블

─── Phase 2: 공공 API ─────────────────────────
API JSON Response
  ↓
KoreaLandAPI.fetch_apt_transactions()
  ↓
TransactionDTO (dataclass)
  ↓
ingest_transactions() → transactions 테이블

─── Phase 3: 통합 처리 ──────────────────────
Properties (NPL) + Complexes (rtech)
  ↓
PropertyMapper.address_to_complex_id()
  ↓
ComparableSales (유사 거래사례 매칭)
  ↓
AVM Engine (비교가 산정)
```

---

### 4.2 데이터 품질 관리

```python
# app/validators/ (신규)

class ComplexValidator:
    @staticmethod
    def validate_address(address: str) -> bool:
        """주소 정규화 후 시도/시군구 확인"""
        
    @staticmethod
    def validate_area(total_area: float, 
                      unit_count: int) -> bool:
        """호당 평균면적 합리성 검증"""

class TransactionValidator:
    @staticmethod
    def detect_abnormal_price(unit_price: float, 
                              complex_avg: float, 
                              percentile: float = 95) -> bool:
        """이상거래 탐지 (상위 5% 제거)"""
        
    @staticmethod
    def validate_date_sequence(contract_date, 
                               report_date) -> bool:
        """계약 ≤ 신고 시간 검증"""
```

---

## 5. AVM 엔진 고도화

### 5.1 현재 AVM 로직 (Engine v1)

```python
# app/avm/engine.py (현재)

class AVMEngine:
    def estimate(self, target: Property) -> AVMResult:
        """
        1. 유사 물건 검색 (면적 기반)
        2. 근처 거래사례 조회
        3. 가중평균 추정가 산출
        """
```

**문제점**:
- 비교사례 부족 (NPL DB만 사용)
- 시점수정계수 미적용
- 입지 유사도 계산 단순

---

### 5.2 확장된 AVM 로직 (Engine v2 — Phase 4)

```python
# app/avm/engine_v2.py (신규)

class AVMEngineV2:
    """
    통합 감정평가 엔진
    """
    
    def estimate(self, target: Property) -> AVMResult:
        """
        [Step 1] 데이터 정제
        - 주소 정규화
        - 면적 검증
        
        [Step 2] 비교사례 수집
        - 같은 단지 실거래 (정확도 ★★★★★)
        - 인접 단지 실거래 (정확도 ★★★★)
        - 근처 다세대/연립 (정확도 ★★★)
        
        [Step 3] 유사도 점수 산출
        similarity = 
            0.4 × (면적 유사도) +
            0.3 × (입지 유사도 — 거리기반) +
            0.2 × (연식 유사도) +
            0.1 × (용도 유사도)
        
        [Step 4] 거래사례 선정
        - similarity > 0.7 & 최근 6개월 데이터
        - 이상거래 제거 (상위/하위 5%)
        
        [Step 5] 시점수정계수 적용
        time_adjustment = KB_시세변화율 + 지가변동률
        adjusted_price = comparable_price × (1 + time_adjustment)
        
        [Step 6] 가중평균 추정가 산출
        avm_price = sum(price_i × weight_i) / sum(weight_i)
        
        [Step 7] 신뢰도 범위 반환
        - lower_bound (보수적)
        - point_estimate (최적)
        - upper_bound (낙관적)
        """
        
        # 구현 로직...
        return AVMResult(
            estimated_price=estimate,
            lower_bound=lower,
            upper_bound=upper,
            confidence_level=0.85,
            comparable_count=len(comparables),
            methodology="헤도닉 회귀 + 시점수정"
        )
    
    def _find_comparables(self, target: Property, 
                         radius_km: float = 2.0) -> List[Transaction]:
        """거리 기반 유사 거래 검색"""
        
    def _calculate_similarity(self, target: Property,
                             comparable: Transaction) -> float:
        """다중 유사도 점수 계산"""
        
    def _apply_time_adjustment(self, base_price: float,
                              transaction_date: date) -> float:
        """시점수정계수 적용 (KB시세 + 지가변동률)"""
```

---

### 5.3 Hedonic 회귀모델 (Phase 5)

```python
# app/ml/hedonic.py (신규)

from sklearn.ensemble import GradientBoostingRegressor

class HedhonicModel:
    """
    특성가격모형 (Hedonic Price Model)
    종속변수: log(거래가)
    설명변수: 면적, 층, 연식, 용적률, 건폐율, 입지점수 등
    """
    
    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5
        )
        
    def extract_features(self, unit: Unit) -> np.ndarray:
        """호실 정보 → 특성 벡터"""
        
    def fit(self, transactions: List[Transaction]):
        """학습"""
        
    def predict(self, target: Property) -> float:
        """감정가 추정"""
```

---

## 6. LLM Agent 레이어 (Phase 6)

### 6.1 Agent 아키텍처

```python
# app/agent/avm_agent.py (신규)

from anthropic import Anthropic

class AVMAgent:
    """
    Claude API 기반 자동감정평가 Agent
    
    사용자 자연어 질의 → SQL 생성 → 감정평가 → 답변
    """
    
    def __init__(self, api_key: str, db_session):
        self.client = Anthropic()
        self.db = db_session
        self.avm_engine = AVMEngineV2(db_session)
        
        # Tool definitions
        self.tools = [
            {
                "name": "search_property",
                "description": "주소로 물건 검색",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "property_type": {"type": "string"}
                    }
                }
            },
            {
                "name": "estimate_avm",
                "description": "물건의 감정평가가 추정",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "integer"}
                    }
                }
            },
            {
                "name": "find_comparables",
                "description": "비교사례 조회",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "integer"},
                        "radius_km": {"type": "number"}
                    }
                }
            },
            {
                "name": "analyze_transaction_trends",
                "description": "특정 지역 거래 추세 분석",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sido": {"type": "string"},
                        "sigungu": {"type": "string"},
                        "months": {"type": "integer"}
                    }
                }
            }
        ]
    
    def query(self, user_message: str) -> str:
        """
        사용자 질의 처리 (Tool Use 패턴)
        
        예시 질의:
        - "경기도 화성시 봉담읍 아파트 시세 알려줘"
        - "이 건물의 감정가 추정해줄래?"
        - "주변 거래 사례 있어?"
        """
        
        messages = [{"role": "user", "content": user_message}]
        
        while True:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                tools=self.tools,
                messages=messages
            )
            
            # Stop condition
            if response.stop_reason == "end_turn":
                return response.content[0].text
            
            # Tool use handling
            if response.stop_reason == "tool_use":
                tool_calls = [
                    block for block in response.content 
                    if block.type == "tool_use"
                ]
                
                # Process each tool call
                tool_results = []
                for tool_call in tool_calls:
                    result = self._handle_tool_call(
                        tool_call.name,
                        tool_call.input
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": str(result)
                    })
                
                # Add assistant response + tool results to messages
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
    
    def _handle_tool_call(self, tool_name: str, 
                         tool_input: dict) -> Any:
        """Tool call 실행"""
        if tool_name == "search_property":
            return self.db.query_property_by_address(
                tool_input["address"]
            )
        elif tool_name == "estimate_avm":
            prop = self.db.get_property(tool_input["property_id"])
            return self.avm_engine.estimate(prop)
        elif tool_name == "find_comparables":
            prop = self.db.get_property(tool_input["property_id"])
            return self.avm_engine._find_comparables(
                prop,
                tool_input.get("radius_km", 2.0)
            )
        # ...
```

### 6.2 Agent 통합 API

```python
# app/api/routes.py (확장)

@router.post("/api/v2/agent/query")
async def agent_query(request: AgentQueryRequest):
    """
    자연어 기반 감정평가 조회
    
    Request:
    {
        "query": "경기도 화성시 아파트 3,300만원 시세 알려줘"
    }
    
    Response:
    {
        "query": "...",
        "response": "화성시 봉담읍 아파트는...",
        "estimated_price": 35000000,
        "confidence": 0.85,
        "comparables": [...]
    }
    """
    agent = AVMAgent(settings.ANTHROPIC_API_KEY, db)
    response = agent.query(request.query)
    return {"response": response}
```

---

## 7. 단계별 구현 로드맵 (Phase 1 ~ 6)

| Phase | 기간 | 목표 | 산출물 |
|-------|------|------|--------|
| **1. 아키텍처 설계** | 1주 | 전체 구조 정의 | ARCHITECTURE.md (본 문서) |
| **2. rtech 데이터 수집** | 2-3주 | 24,197개 단지 마스터 크롤 | RtechCrawler + 100만 호 DB |
| **3. 공공API 연동** | 2주 | 국토부 실거래 API 통합 | KoreaLandAPI + 25M 거래 DB |
| **4. AVM 엔진 v2** | 2주 | 확장된 감정평가 로직 | AVMEngineV2 + 신뢰도 범위 |
| **5. 헤도닉 모델** | 2주 | ML 기반 고도화 | HedhonicModel (GBM) |
| **6. LLM Agent** | 2주 | Claude API 통합 | AVMAgent + Tool Use 자동화 |

**Total: 11-13주 (3개월)**

---

## 8. 기술 스택

### 현재
```
Python 3.12
FastAPI 0.100+
SQLAlchemy 2.0
SQLite (→ PostgreSQL)
```

### 추가
```
# 크롤링
aiohttp>=3.9
beautifulsoup4>=4.12
selenium>=4.0 (필요시)

# 공공API
requests>=2.31
pandas>=2.0 (데이터 전처리)

# 지리 정보
geopy>=2.3
shapely>=2.0

# ML
scikit-learn>=1.3
numpy>=1.24

# LLM Agent
anthropic>=0.7

# 데이터베이스
psycopg2-binary>=2.9 (PostgreSQL)
alembic>=1.12 (마이그레이션)
```

---

## 9. 파일 구조 (확장안)

```
avm_project/
├── ARCHITECTURE.md                 (본 문서)
├── ROADMAP.md                      (상세 일정)
├── requirements.txt
├── app/
│   ├── main.py
│   ├── config.py (신규)
│   ├── db/
│   │   ├── models.py (확장)
│   │   ├── database.py
│   │   ├── ingest.py
│   │   ├── validators.py (신규)
│   │   └── mapping.py (신규)
│   ├── integrations/ (신규)
│   │   ├── rtech_crawler.py
│   │   ├── korea_api.py
│   │   └── __init__.py
│   ├── avm/
│   │   ├── engine.py (기존)
│   │   ├── engine_v2.py (신규)
│   │   └── __init__.py
│   ├── ml/ (신규)
│   │   ├── hedonic.py
│   │   └── __init__.py
│   ├── agent/ (신규)
│   │   ├── avm_agent.py
│   │   └── __init__.py
│   ├── parsers/
│   │   └── ... (기존)
│   └── api/
│       ├── routes.py (확장)
│       └── __init__.py
├── scripts/
│   ├── ingest_all.py (기존)
│   ├── migrate_to_postgres.py (신규)
│   ├── crawl_rtech.py (신규)
│   ├── fetch_korea_api.py (신규)
│   └── train_hedonic_model.py (신규)
├── data/
│   ├── npl_avm.db (SQLite)
│   └── config/
│       ├── mapping.yaml (NPL ↔ rtech 매핑)
│       └── feature_engineering.yaml
└── tests/ (신규)
    ├── test_rtech_crawler.py
    ├── test_korea_api.py
    ├── test_avm_engine_v2.py
    ├── test_avm_agent.py
    └── __init__.py
```

---

## 10. 주요 의사결정 항목

### 10.1 데이터 수집 방식

**선택지**:
1. **rtech 크롤링** (빠르지만 약관 위험)
2. **공공 API** (안정적, 공식 데이터)
3. **하이브리드** (rtech 단지 마스터 + API 거래 데이터)

**권장**: **하이브리드** (Option 3)
- rtech: 단지코드/단지명/주소 (한 번만 수집)
- API: 거래/시세 (월 1회 자동 갱신)

### 10.2 DB: SQLite vs PostgreSQL

**현재**: SQLite (개발 편의)
**목표**: PostgreSQL (운영 환경)

**마이그레이션 시기**: Phase 3 말 (데이터 1,000만 건 도달 시)

**절차**:
```python
# scripts/migrate_to_postgres.py
# 1. SQLite → 스키마 추출
# 2. PostgreSQL 테이블 생성
# 3. 데이터 마이그레이션 (Pandas bulk insert)
```

### 10.3 AVM 알고리즘: 단순 vs 복잡

**초기 (Phase 4)**: 비교법 + 시점수정계수
```
추정가 = Σ(비교사례가 × 가중치) × 시점수정
```

**고도화 (Phase 5)**: 헤도닉 + GBM
```
추정가 = 헤도닉계수 + ML 모델 보정
```

**Phase 6**: Agent 기반 자동화
```
사용자: "OO 아파트 평가해줄래?"
Agent: DB 검색 → AVM 추정 → 근거 설명
```

---

## 11. 성공 지표

| 지표 | 목표 | 검증 방법 |
|------|------|---------|
| **DB 규모** | 25M+ 거래 | 공공API 적재 건수 |
| **AVM 정확도** | MAPE < 10% | 실제 낙찰가와 비교 |
| **처리 속도** | < 100ms | API 응답시간 |
| **Agent 정확도** | 자연어 해석율 > 95% | 10개 샘플 테스트 |
| **커버리지** | 전국 95% 단지 | 마스터 데이터 확인 |

---

## 12. 위험 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| rtech 크롤링 차단 | Phase 2 지연 | 공공API 우선 추진 |
| 공공API 한도 초과 | 데이터 갱신 불가 | 월 인수분해 + 캐싱 |
| 주소 정규화 실패 | NPL-rtech 매핑 정확도 ↓ | 지오코딩 + 수동 검증 |
| 거래 이상치 | AVM 오류 | IQR 기반 자동 제거 |

---

## 13. 참고 자료

### 13.1 공공 데이터 포털
- **data.go.kr** — 아파트/다세대/연립/오피스텔 실거래
- **K-루시스** (kland.kict.or.kr) — 토지 정보
- **국가공간정보포털** (nsdi.go.kr) — 지번/도로명

### 13.2 외부 API
- **Kakao Map API** — 거리/입지 계산
- **OpenWeather API** — (선택) 환경 요소

### 13.3 참고 논문
- Rosen, S. (1974). "Hedonic Prices and Implicit Markets"
- 주택 가격 추정의 국내 사례 연구

---

## 14. 다음 단계

1. **Phase 1 검토** (본 문서)
   - 아키텍처 리뷰 회의
   - 주요 의사결정 확정

2. **Phase 2 시작** (1주 후)
   - rtech 크롤러 개발 + 테스트
   - 공공API 신청 진행

3. **주간 진도 보고**
   - 매주 목요일 전체 검토
   - 블로커 항목 우선 처리

---

**문서 작성일**: 2026-06-09  
**최종 수정**: -  
**상태**: Draft (검토 대기)
