"""RAG 파이프라인: 벡터 검색 기반 유사 사례 조회 + 설명 생성.

이 모듈은 원래 존재하지 않아 routes_rag.py 의 import 가 실패하고
있었다. 그 파일의 헬스체크 코드(`rag.collection`, `rag.client`)를 보면
원래 설계는 Milvus(벡터DB) + OpenAI(임베딩/설명 생성) 조합을 염두에 둔
것으로 보인다.

OpenAI 는 이 환경에 키가 없어 여전히 대체 경로(템플릿 설명)를 쓰지만,
Milvus 는 `pymilvus[milvus_lite]` 로 서버 없이 파일 하나로 동작하는
Milvus Lite 를 실제로 붙였다 — `MilvusClient(uri=...)` 는 uri 가 로컬
경로면 Lite, "http://host:port" 면 실제 서버로 동일한 코드가 그대로
접속하므로, 나중에 진짜 서버로 옮겨도 이 파일을 고칠 필요가 없다.

Milvus 색인이 비어 있거나(초기 상태) 접속에 실패하면, 기존 AVM 엔진의
DB 기반 비교사례 검색으로 조용히 대체한다 — 벡터 색인은 `rebuild_index()`
로 채운다(자동 색인은 하지 않는다. 데이터가 바뀔 때마다 전량 재색인하는
연산 비용을 API 요청 경로에 두지 않기 위해서다).
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from pymilvus import MilvusClient
    _MILVUS_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경 의존
    _MILVUS_AVAILABLE = False

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경 의존
    _OPENAI_AVAILABLE = False

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # avm_project/
_DEFAULT_MILVUS_LITE_PATH = _PROJECT_ROOT / "data" / "milvus_lite.db"


class RAGPipeline:
    def __init__(self) -> None:
        self.collection = self._init_milvus()
        self.client = self._init_openai()

    def _init_milvus(self):
        if not _MILVUS_AVAILABLE:
            return None
        uri = os.environ.get("MILVUS_URI", str(_DEFAULT_MILVUS_LITE_PATH))
        try:
            if not uri.startswith("http"):
                Path(uri).parent.mkdir(parents=True, exist_ok=True)
            return MilvusClient(uri=uri)
        except Exception as e:
            logger.warning(f"[RAG] Milvus 연결 실패, DB 기반 검색으로 대체: {e}")
            return None

    def _init_openai(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not (_OPENAI_AVAILABLE and api_key):
            return None
        try:
            return OpenAI(api_key=api_key)
        except Exception as e:
            logger.warning(f"[RAG] OpenAI 클라이언트 초기화 실패, 템플릿 설명으로 대체: {e}")
            return None

    def rebuild_index(self, db) -> int:
        """SQL DB 내용으로 벡터 색인을 전량 재구성한다. 색인된 건수를 돌려준다."""
        if self.collection is None:
            raise RuntimeError("Milvus 클라이언트가 초기화되지 않았습니다")
        from app.avm.vector_index import build_index
        return build_index(db, self.collection)

    def process(self, property_info: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        similar_cases = self._retrieve_similar_cases(property_info)
        excluded_reason = self._excluded_reason(property_info, similar_cases)
        explanation = self._generate_explanation(property_info, result, similar_cases, excluded_reason)
        return {
            "explanation": explanation,
            "similar_cases": similar_cases,
            "excluded_reason": excluded_reason,
        }

    @staticmethod
    def _excluded_reason(property_info: Dict[str, Any], similar_cases: List[Dict[str, Any]]) -> Optional[str]:
        """유형이 다른 사례가 근거에 섞여 있으면, 감정평가 근거로 그대로 쓰지 않도록
        조용히 넘기지 않고 이유를 명시한다."""
        query_type = property_info.get("property_type")
        if not query_type or not similar_cases:
            return None
        mismatched = [c for c in similar_cases if not c.get("type_matched", True)]
        if not mismatched:
            return None
        return (
            f"동일 유형({query_type}) 사례가 부족해 다른 유형 {len(mismatched)}건이 "
            "포함됨 — 해당 사례는 근거로 참고만 할 것"
        )

    def _retrieve_similar_cases(self, property_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.collection is not None:
            try:
                cases = self._retrieve_from_vector_index(property_info)
                if cases:
                    return cases
            except Exception as e:
                logger.warning(f"[RAG] 벡터 검색 실패, DB 기반 검색으로 대체: {e}")
        return self._retrieve_from_sql(property_info)

    def _retrieve_from_vector_index(self, property_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        from app.avm.vector_index import search_similar, vectorize

        query_vector = vectorize(
            property_info.get("land_area"), property_info.get("building_area"),
            property_info.get("appraisal_amount"), property_info.get("property_type"),
            property_info.get("address_sido"), None,
        )
        return search_similar(
            self.collection, query_vector,
            property_type=property_info.get("property_type"), limit=5,
        )

    def _retrieve_from_sql(self, property_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """벡터 색인이 없거나 실패했을 때의 대체 경로 — DB 비교사례 검색 재사용."""
        try:
            from app.avm import engine as avm
            from app.db.database import SessionLocal
        except Exception as e:
            logger.warning(f"[RAG] 엔진/DB 모듈 로드 실패: {e}")
            return []

        db = SessionLocal()
        try:
            avm_result = avm.estimate(
                db=db,
                address_sido=property_info.get("address_sido", ""),
                address_sigungu=property_info.get("address_sigungu", ""),
                property_type=property_info.get("property_type", ""),
                land_area=property_info.get("land_area"),
                building_area=property_info.get("building_area"),
                max_comparables=5,
            )
        except Exception as e:
            logger.warning(f"[RAG] 비교사례 조회 실패: {e}")
            return []
        finally:
            db.close()

        return [
            {
                "doc_id": idx,
                "property_type": comp.property_type,
                # 응답 스키마가 이 키를 'address' 로 노출한다(routes_rag.py) —
                # Comparable 에는 시도 단위 필드가 따로 없어 전체 주소를 담는다.
                "address_sido": comp.address,
                "hammer_price": comp.hammer_price or comp.appraisal_value,
                "hammer_rate": comp.hammer_rate or 0.0,
                # engine._area_similarity_score 는 비공개 함수라 직접 노출하지
                # 않는다. 벡터 검색 경로와 달리 이 대체 경로는 근거 축 설명을
                # 만들지 않는다 — match_reasons/evidence 는 벡터 검색 결과에서만 나온다.
                "similarity": 0.5,
                # 이 경로는 이미 engine.avm.estimate() 가 property_type 으로
                # 필터링한 결과만 준다(app/avm/engine.py Property.property_type
                # ilike 조건) — 그래서 항상 True.
                "type_matched": True,
            }
            for idx, comp in enumerate(avm_result.comparables)
        ]

    def _generate_explanation(
        self, property_info: Dict[str, Any], result: Dict[str, Any],
        similar_cases: List[Dict[str, Any]], excluded_reason: Optional[str] = None,
    ) -> str:
        if self.client is not None:
            try:
                return self._generate_explanation_openai(
                    property_info, result, similar_cases, excluded_reason,
                )
            except Exception as e:
                logger.warning(f"[RAG] OpenAI 설명 생성 실패, 템플릿으로 대체: {e}")
        return self._generate_explanation_template(result, similar_cases, excluded_reason)

    def _generate_explanation_openai(
        self, property_info: Dict[str, Any], result: Dict[str, Any],
        similar_cases: List[Dict[str, Any]], excluded_reason: Optional[str] = None,
    ) -> str:
        # 실 서비스(OPENAI_API_KEY)가 없어 이 경로는 아직 실행 검증하지 못했다.
        caveat = f"\n주의: {excluded_reason}" if excluded_reason else ""
        prompt = (
            f"물건 정보: {property_info}\n"
            f"예상 낙찰가: {result.get('hammer_price')}원 (낙찰가율 {result.get('hammer_rate')})\n"
            f"유사 사례 {len(similar_cases)}건을 참고해 감정평가 근거를 "
            f"3문장 이내 한국어로 설명하라.{caveat}"
        )
        response = self.client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            timeout=15,
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _generate_explanation_template(
        result: Dict[str, Any], similar_cases: List[Dict[str, Any]],
        excluded_reason: Optional[str] = None,
    ) -> str:
        count = len(similar_cases)
        hammer_price = result.get("hammer_price", 0)
        hammer_rate = result.get("hammer_rate", 0.0)
        if count == 0:
            return (
                f"유사 사례를 찾지 못해 모델 단독 추정치({hammer_price:,}원, "
                f"낙찰가율 {hammer_rate:.2f})를 제시합니다. 참고용으로만 활용하세요."
            )
        base = (
            f"유사 사례 {count}건을 근거로 예상 낙찰가 {hammer_price:,}원"
            f"(낙찰가율 {hammer_rate:.2f})을 추정했습니다."
        )
        top_reasons = similar_cases[0].get("match_reasons")
        if top_reasons:
            base += f" 가장 유사한 사례는 {', '.join(top_reasons)} 기준으로 근접했습니다."
        if excluded_reason:
            base += f" ※ {excluded_reason}."
        return base


_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
