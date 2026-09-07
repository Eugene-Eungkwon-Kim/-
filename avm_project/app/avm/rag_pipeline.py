"""RAG 파이프라인: 유사 사례 검색 + 설명 생성.

이 모듈은 원래 존재하지 않아 routes_rag.py 의 import 가 실패하고
있었다. 그 파일의 헬스체크 코드(`rag.collection`, `rag.client`)를 보면
원래 설계는 Milvus(벡터DB) + OpenAI(임베딩/설명 생성) 조합을 염두에 둔
것으로 보이는데, 이 환경에는 둘 다 구성되어 있지 않다(Milvus 서버 없음,
OPENAI_API_KEY 미제공).

두 서비스가 없어도 API가 죽지 않도록 항상 동작하는 대체 경로를 기본으로
둔다:
  - 검색: 기존 AVM 엔진의 DB 기반 비교사례 검색(engine.estimate)을 재사용
  - 설명: OpenAI 클라이언트가 있으면 자연어 설명을 생성하고, 없으면
    결정적 템플릿 문장으로 대체

Milvus/OpenAI 를 실제로 붙이려면:
  pip install pymilvus openai
  export MILVUS_HOST=... OPENAI_API_KEY=...
그 순간부터 이 클래스가 자동으로 그 경로를 탄다 — 다만 이 환경에는 실제
서비스가 없어 그 경로 자체는 아직 실행 검증하지 못했다는 점을 분명히
해둔다(SQL 대체 경로만 테스트로 검증됨).
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from pymilvus import Collection, connections
    _MILVUS_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경 의존
    _MILVUS_AVAILABLE = False

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - 환경 의존
    _OPENAI_AVAILABLE = False


class RAGPipeline:
    def __init__(self) -> None:
        self.collection = self._init_milvus()
        self.client = self._init_openai()

    def _init_milvus(self):
        host = os.environ.get("MILVUS_HOST")
        if not (_MILVUS_AVAILABLE and host):
            return None
        try:
            connections.connect(
                alias="default", host=host,
                port=os.environ.get("MILVUS_PORT", "19530"),
            )
            return Collection(os.environ.get("MILVUS_COLLECTION", "avm_comparables"))
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

    def process(self, property_info: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        similar_cases = self._retrieve_similar_cases(property_info)
        explanation = self._generate_explanation(property_info, result, similar_cases)
        return {"explanation": explanation, "similar_cases": similar_cases}

    def _retrieve_similar_cases(self, property_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.collection is not None:
            # TODO: Milvus 벡터 검색 — 임베딩 생성 포함, 실 서비스 없어 미검증.
            pass
        return self._retrieve_from_sql(property_info)

    def _retrieve_from_sql(self, property_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """기존 AVM 엔진의 비교사례 검색을 재사용하는 대체 경로."""
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
                # TODO: engine._area_similarity_score 는 비공개 함수라 이 값을
                # 직접 노출하지 않는다 — 공개 인터페이스로 뽑아내는 후속 작업 필요.
                "similarity": 0.5,
            }
            for idx, comp in enumerate(avm_result.comparables)
        ]

    def _generate_explanation(
        self, property_info: Dict[str, Any], result: Dict[str, Any],
        similar_cases: List[Dict[str, Any]],
    ) -> str:
        if self.client is not None:
            try:
                return self._generate_explanation_openai(property_info, result, similar_cases)
            except Exception as e:
                logger.warning(f"[RAG] OpenAI 설명 생성 실패, 템플릿으로 대체: {e}")
        return self._generate_explanation_template(result, similar_cases)

    def _generate_explanation_openai(
        self, property_info: Dict[str, Any], result: Dict[str, Any],
        similar_cases: List[Dict[str, Any]],
    ) -> str:
        # 실 서비스가 없어 이 경로는 아직 실행 검증하지 못했다.
        prompt = (
            f"물건 정보: {property_info}\n"
            f"예상 낙찰가: {result.get('hammer_price')}원 (낙찰가율 {result.get('hammer_rate')})\n"
            f"유사 사례 {len(similar_cases)}건을 참고해 감정평가 근거를 "
            "3문장 이내 한국어로 설명하라."
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
    ) -> str:
        count = len(similar_cases)
        hammer_price = result.get("hammer_price", 0)
        hammer_rate = result.get("hammer_rate", 0.0)
        if count == 0:
            return (
                f"유사 사례를 찾지 못해 모델 단독 추정치({hammer_price:,}원, "
                f"낙찰가율 {hammer_rate:.2f})를 제시합니다. 참고용으로만 활용하세요."
            )
        return (
            f"유사 사례 {count}건을 근거로 예상 낙찰가 {hammer_price:,}원"
            f"(낙찰가율 {hammer_rate:.2f})을 추정했습니다."
        )


_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
