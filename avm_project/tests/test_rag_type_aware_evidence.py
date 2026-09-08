"""app/avm/vector_index.py 의 자산유형 인지 근거·검색(A3, 2026-09-08) 검증.

목적: 평가서 분석 에이전트가 evidence 를 그대로 인용하므로, "벡터 거리상
가장 가까운 축"이 아니라 "그 자산유형에 실제로 의미 있는 축"이 근거로
나와야 한다(토지에 건물면적 근거를 대면 안 됨). 같은 이유로 검색 결과에
다른 유형이 섞이면 조용히 넘기지 않고 type_matched/excluded_reason 으로
드러나야 한다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.avm.vector_index import (
    FEATURE_LABELS, explain_match, explain_match_detailed, search_similar,
)


class TestAxisPriorityByPropertyType:
    """FEATURE_LABELS = [토지면적, 건물면적, 가격규모, 자산유형, 지역, 낙찰가율]."""

    # 원시 diff 로는 건물면적(0.01)이 토지면적(0.05)보다 작다 — 유형을
    # 모르면 "건물면적"이 1순위로 뽑히는데, 토지는 건물이 없으니 부적절하다.
    QUERY = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    CASE = [0.05, 0.01, 0.5, 0.9, 0.9, 0.9]

    def test_raw_ranking_without_type_picks_smallest_diff(self):
        assert explain_match(self.QUERY, self.CASE, property_type=None, top_n=1) == ["건물면적"]

    def test_land_query_prioritizes_land_axis_over_smaller_building_diff(self):
        result = explain_match(self.QUERY, self.CASE, property_type="토지", top_n=2)
        assert result == ["토지면적", "가격규모"]
        assert "건물면적" not in result

    def test_building_type_query_prioritizes_building_axis(self):
        for ptype in ("공장창고", "상가", "공장"):
            result = explain_match(self.QUERY, self.CASE, property_type=ptype, top_n=1)
            assert result == ["건물면적"], f"{ptype} 는 건물면적이 1순위여야 한다"

    def test_unknown_type_falls_back_to_default_priority(self):
        result = explain_match(self.QUERY, self.CASE, property_type="주거", top_n=1)
        assert result == ["건물면적"]  # 기본 우선순위도 건물면적이 최상위

    def test_explain_match_detailed_exposes_diff_values(self):
        detail = explain_match_detailed(self.QUERY, self.CASE, property_type="토지", top_n=2)
        assert detail[0] == {"axis": "토지면적", "diff": 0.05}
        assert detail[1] == {"axis": "가격규모", "diff": 0.5}

    def test_all_feature_labels_are_valid_axis_names(self):
        detail = explain_match_detailed(self.QUERY, self.CASE, property_type=None, top_n=6)
        assert {d["axis"] for d in detail} == set(FEATURE_LABELS)


class FakeMilvusClient:
    """실제 Milvus Lite 대신 property_type 필터만 흉내내는 가짜 클라이언트."""

    def __init__(self, rows: list) -> None:
        self.rows = rows  # [{"id": int, "vector": [...], "property_type": str, ...}]

    def has_collection(self, name: str) -> bool:
        return True

    def search(self, collection_name, data, limit, output_fields, filter: str = ""):
        rows = self.rows
        if filter:
            wanted = filter.split('"')[1]
            rows = [r for r in rows if r["property_type"] == wanted]
        hits = [
            {"id": r["id"], "distance": 0.1 * i, "entity": {k: r[k] for k in output_fields}}
            for i, r in enumerate(rows[:limit])
        ]
        return [hits]


def _row(id_, ptype):
    return {
        "id": id_, "vector": [0.0] * 6, "property_type": ptype,
        "source_type": "transaction", "address": "서울", "hammer_price": 100, "hammer_rate": 0.5,
    }


class TestSearchSimilarTypeFiltering:
    def test_prefers_same_type_when_enough_available(self):
        client = FakeMilvusClient([_row(1, "토지"), _row(2, "토지"), _row(3, "상가")])

        results = search_similar(client, [0.0] * 6, property_type="토지", limit=2)

        assert [r["doc_id"] for r in results] == [1, 2]
        assert all(r["type_matched"] for r in results)

    def test_fills_remainder_with_other_types_and_marks_them(self):
        client = FakeMilvusClient([_row(1, "토지"), _row(2, "상가"), _row(3, "공장창고")])

        results = search_similar(client, [0.0] * 6, property_type="토지", limit=3)

        assert len(results) == 3
        by_id = {r["doc_id"]: r for r in results}
        assert by_id[1]["type_matched"] is True
        assert by_id[2]["type_matched"] is False
        assert by_id[3]["type_matched"] is False

    def test_no_property_type_means_everything_matches(self):
        client = FakeMilvusClient([_row(1, "토지"), _row(2, "상가")])

        results = search_similar(client, [0.0] * 6, property_type=None, limit=2)

        assert all(r["type_matched"] for r in results)

    def test_does_not_duplicate_same_type_hit_in_broader_pass(self):
        client = FakeMilvusClient([_row(1, "토지")])

        results = search_similar(client, [0.0] * 6, property_type="토지", limit=5)

        assert [r["doc_id"] for r in results] == [1]


class TestRagPipelineExcludedReason:
    def test_excluded_reason_set_when_types_mixed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "unused.db"))
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        cases = [
            {"doc_id": 1, "type_matched": True},
            {"doc_id": 2, "type_matched": False},
        ]
        reason = pipeline._excluded_reason({"property_type": "토지"}, cases)

        assert reason is not None
        assert "토지" in reason and "1건" in reason

    def test_no_excluded_reason_when_all_matched(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "unused2.db"))
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        cases = [{"doc_id": 1, "type_matched": True}]

        assert pipeline._excluded_reason({"property_type": "토지"}, cases) is None

    def test_excluded_reason_appears_in_template_explanation(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("MILVUS_URI", str(tmp_path / "unused3.db"))
        from app.avm.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        text = pipeline._generate_explanation_template(
            {"hammer_price": 100, "hammer_rate": 0.5},
            [{"match_reasons": ["토지면적"]}],
            excluded_reason="동일 유형(토지) 사례가 부족해 다른 유형 1건이 포함됨",
        )

        assert "다른 유형 1건" in text
