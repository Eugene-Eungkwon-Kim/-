"""app/db, app/avm/comparator, app/avm/confidence_scorer, app/avm/rag_pipeline 검증.

이 다섯 모듈은 원래 존재하지 않아 `app.main` 이 임포트 단계에서부터
죽는 상태였다(누락: app.db.database, app.db.models, app.avm.comparator,
app.avm.rag_pipeline, app.avm.confidence_scorer). engine.py/routes.py 의
실제 쿼리·컬럼 사용을 전수 조사해 역산한 스키마이므로, 이 테스트가
깨지면 그 역산이 실제 사용 패턴과 어긋난 것이다.
"""

import importlib
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.avm.comparator import compare
from app.avm.confidence_scorer import ConfidenceScorer


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    """임시 SQLite 파일에 바인딩된 세션과, 그 세션을 만든 database 모듈을 준다."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test_avm.sqlite'}")
    import app.db.database as database_module
    importlib.reload(database_module)  # DATABASE_URL 재평가
    database_module.init_db()
    session = database_module.SessionLocal()
    try:
        yield session, database_module
    finally:
        session.close()


def _seed_one_comparable(session):
    from app.db.models import Appraisal, Auction, Deal, Property

    deal = Deal(deal_name="테스트딜", financial_institution="OO은행")
    session.add(deal)
    session.flush()

    prop = Property(
        property_serial="P-001", deal_id=deal.id,
        address_full="서울 강남구 역삼동 1", address_sido="서울",
        address_sigungu="강남구", property_type="주거",
        land_area=100.0, building_area=80.0,
    )
    session.add(prop)
    session.flush()

    session.add(Appraisal(property_id=prop.id, appraisal_date=date(2026, 1, 1),
                          total_value=500_000_000))
    session.add(Auction(property_id=prop.id, hammer_price=350_000_000, final_result="낙찰"))
    session.commit()


class TestAppBoots:
    """가장 기본적인 회귀 방지: app.main 이 임포트조차 안 되던 상태였다."""

    def test_main_module_imports(self):
        import app.main  # noqa: F401 — 임포트 자체가 검증 대상

    def test_health_endpoint_reports_disabled_services_without_crashing(self):
        from fastapi.testclient import TestClient
        import app.main as m

        with TestClient(m.app) as client:
            r = client.get("/api/v4/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "degraded", "error")
        assert set(body["services"]) == {"p6_model", "milvus", "openai"}


class TestDbLayerAndComparableSearch:
    def test_init_db_creates_all_tables(self, db_session):
        _, database_module = db_session
        from sqlalchemy import inspect
        tables = set(inspect(database_module.engine).get_table_names())
        assert tables == {"deals", "properties", "appraisals", "auctions", "comparable_sales"}

    def test_estimate_returns_no_comparables_diagnostics_on_empty_db(self, db_session):
        session, _ = db_session
        from app.avm import engine as avm

        result = avm.estimate(db=session, address_sido="서울", address_sigungu="강남구",
                               property_type="주거")

        assert result.comparable_count == 0
        assert result.diagnostics["status"] == "NO_COMPARABLES"
        assert result.diagnostics["reason_codes"] == ["NO_SIDO_MATCH"]

    def test_estimate_finds_seeded_comparable(self, db_session):
        session, _ = db_session
        from app.avm import engine as avm

        _seed_one_comparable(session)

        result = avm.estimate(db=session, address_sido="서울", address_sigungu="강남구",
                               property_type="주거", land_area=95.0, building_area=78.0)

        assert result.comparable_count == 1
        assert result.comparables[0].property_serial == "P-001"
        assert result.comparables[0].hammer_rate == pytest.approx(0.7)


class TestRagPipelineSqlFallback:
    """Milvus 색인이 비어 있을 때(OpenAI 는 이 환경에 항상 없음) 타는 경로."""

    def test_pipeline_reports_openai_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "unused_milvus.db"))
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        assert pipeline.client is None

    def test_process_falls_back_to_sql_when_vector_index_empty(
        self, db_session, monkeypatch, tmp_path,
    ):
        session, database_module = db_session
        _seed_one_comparable(session)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "empty_milvus.db"))

        # rag_pipeline._retrieve_from_sql 는 자체 세션을 새로 여므로, 이 테스트가
        # 재바인딩해 둔 SessionLocal(임시 DB)을 그대로 쓰게 된다.
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        result = pipeline.process(
            {"address_sido": "서울", "address_sigungu": "강남구", "property_type": "주거",
             "land_area": 95.0, "building_area": 78.0},
            {"hammer_price": 350_000_000, "hammer_rate": 0.7},
        )

        assert len(result["similar_cases"]) == 1
        assert result["similar_cases"][0]["hammer_price"] == 350_000_000
        assert "350,000,000" in result["explanation"]

    def test_process_returns_safe_defaults_when_no_comparables(self, db_session, monkeypatch, tmp_path):
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "empty_milvus2.db"))
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        result = pipeline.process(
            {"address_sido": "부산", "address_sigungu": "해운대구", "property_type": "상가"},
            {"hammer_price": 100_000_000, "hammer_rate": 0.6},
        )

        assert result["similar_cases"] == []
        assert "유사 사례를 찾지 못해" in result["explanation"]


class TestRagPipelineVectorIndex:
    """Milvus Lite(임베디드, 서버 불필요)에 실제로 색인·검색하는 경로."""

    def test_rebuild_index_and_search_returns_real_similarity(
        self, db_session, monkeypatch, tmp_path,
    ):
        session, database_module = db_session
        _seed_one_comparable(session)
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "milvus_lite.db"))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        assert pipeline.collection is not None, "Milvus Lite 클라이언트 초기화 실패"

        indexed = pipeline.rebuild_index(session)
        assert indexed == 1

        result = pipeline.process(
            {"address_sido": "서울", "address_sigungu": "강남구", "property_type": "주거",
             "land_area": 95.0, "building_area": 78.0, "appraisal_amount": 500_000_000},
            {"hammer_price": 350_000_000, "hammer_rate": 0.7},
        )

        assert len(result["similar_cases"]) == 1
        case = result["similar_cases"][0]
        assert case["hammer_price"] == pytest.approx(350_000_000)
        # 하드코딩된 0.5 가 아니라 실제 거리 기반 계산값이어야 한다.
        assert 0.0 < case["similarity"] <= 1.0
        assert "match_reasons" in case and len(case["match_reasons"]) > 0
        assert any(reason in result["explanation"] for reason in case["match_reasons"])

    def test_search_on_empty_index_returns_empty_list(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "fresh_milvus.db"))
        from app.avm.vector_index import search_similar
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        assert search_similar(pipeline.collection, [0.0] * 6) == []


class TestConfidenceScorer:
    def test_no_comparables_yields_low_score(self):
        scorer = ConfidenceScorer()
        result = scorer.score(hammer_rate=0.7, similar_cases=[], mape=10, comparables_count=0)
        assert result["score"] <= 60
        assert "유사 사례를 찾지 못함" in result["reasons"]

    def test_many_high_similarity_cases_yield_high_score(self):
        scorer = ConfidenceScorer()
        cases = [{"similarity": 0.9} for _ in range(5)]
        result = scorer.score(hammer_rate=0.7, similar_cases=cases, mape=5, comparables_count=5)
        assert result["score"] >= 80
        assert result["level"] in ("높음", "매우높음")

    def test_out_of_range_hammer_rate_is_penalized(self):
        scorer = ConfidenceScorer()
        cases = [{"similarity": 0.9} for _ in range(5)]
        result = scorer.score(hammer_rate=2.5, similar_cases=cases, mape=5, comparables_count=5)
        assert any("통상 범위를 벗어남" in reason for reason in result["reasons"])


class TestComparator:
    def test_compare_returns_position_and_country_benchmarks(self):
        result = compare(500_000_000, "주거")
        assert isinstance(result.position, str)
        assert "KR" in result.comparisons
        assert len(result.comparisons) >= 5


class TestDbIngest:
    """국토부 실거래가 수집(scripts/fetch_transactions_parallel.py)이 참조하는
    app.integrations.db_ingest / sgg_codes 검증.

    이 환경은 apis.data.go.kr 로의 아웃바운드가 조직 정책으로 차단되어
    있어(egress 403) 실제 API 호출까지는 이 테스트로 검증할 수 없다.
    KoreaLandAPI.TransactionRecord 를 직접 만들어 '응답을 받은 뒤' 단계만
    검증한다.
    """

    def test_sgg_code_lookup_roundtrip(self):
        from app.integrations.sgg_codes import SGG_CODES, sido_of, sigungu_of

        code = SGG_CODES["서울 강남구"]
        assert code == "11680"
        assert sido_of(code) == "서울"
        assert sigungu_of(code) == "강남구"
        assert sido_of("99999") == ""  # 모르는 코드는 조용히 빈 문자열

    def test_bulk_ingest_inserts_and_deduplicates(self, db_session):
        session, _ = db_session
        from app.integrations.db_ingest import bulk_ingest_transactions
        from app.db.models import ComparableSale
        from app.integrations.korea_api import TransactionRecord

        record = TransactionRecord(
            sgg_code="11680", property_type="아파트", complex_name="테스트아파트",
            address_dong="역삼동", address_jibun="1", contract_year=2025,
            contract_month=12, contract_day=1, price_manwon=50000,
            exclusive_area=84.5, floor=10,
        )

        first = bulk_ingest_transactions(session, [record])
        assert first == {"inserted": 1, "skipped": 0, "errors": 0}

        second = bulk_ingest_transactions(session, [record])
        assert second == {"inserted": 0, "skipped": 1, "errors": 0}, "같은 거래가 중복 적재됐다"

        rows = session.query(ComparableSale).all()
        assert len(rows) == 1
        assert rows[0].address_sido == "서울"
        assert rows[0].address_sigungu == "강남구"
        assert rows[0].trade_amount == 500_000_000  # 5억(만원 -> 원 변환)
