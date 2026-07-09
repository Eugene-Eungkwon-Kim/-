# -*- coding: utf-8 -*-
"""
RAG API 라우트: /api/v4 엔드포인트
Session 19 Phase 3.1 - API 통합 (2026-06-26)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from app.avm.engine import estimate_p6
from app.avm.rag_pipeline import get_rag_pipeline
from app.avm.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v4", tags=["rag"])


# ─── Request/Response 스키마 ────────────────────────────
class PropertyRequest(BaseModel):
    """물건 정보 요청"""
    property_type: str = Field(..., description="부동산유형 (주거/상가/토지/산업용)")
    address_sido: str = Field(..., description="시도 (서울/경기도/...)")
    address_sigungu: str = Field(default="", description="시군구")
    appraisal_amount: int = Field(..., description="감정평가가 (원)")
    land_area: Optional[float] = Field(default=None, description="토지면적 (㎡)")
    building_area: Optional[float] = Field(default=None, description="건물면적 (㎡)")


class SimilarCaseResponse(BaseModel):
    """유사 사례"""
    doc_id: int
    property_type: str
    address: str
    hammer_price: int
    hammer_rate: float
    similarity: float


class ConfidenceDetail(BaseModel):
    """신뢰도 상세"""
    score: int = Field(..., description="신뢰도 점수 (0~100)")
    level: str = Field(..., description="신뢰도 레벨 (매우높음/높음/중간/낮음/매우낮음)")
    reasons: List[str] = Field(..., description="신뢰도 판단 근거")


class EstimateWithExplanationResponse(BaseModel):
    """설명 포함 추정가 응답"""
    hammer_price: int = Field(..., description="예상낙찰가 (원)")
    hammer_rate: float = Field(..., description="낙찰가율 (소수점)")
    mape: int = Field(..., description="모델 정확도 (%)")
    confidence: ConfidenceDetail = Field(..., description="신뢰도")
    explanation: str = Field(..., description="감정평가 설명")
    similar_cases: List[SimilarCaseResponse] = Field(..., description="유사 사례")


class HealthResponse(BaseModel):
    """RAG health status."""
    status: str
    services: Dict[str, bool]
    disabled_services: List[str]
    safe_to_use_for_pricing: bool
    warnings: List[str]


# ─── 엔드포인트 ────────────────────────────
@router.post(
    "/estimate-with-explanation",
    response_model=EstimateWithExplanationResponse,
    summary="RAG 설명 포함 낙찰가 추정",
    description="P6 모델 + RAG 파이프라인으로 낙찰가 추정 및 설명 생성",
)
async def estimate_with_explanation(request: PropertyRequest):
    """RAG 설명 포함 낙찰가 추정

    Args:
        request: 물건 정보

    Returns:
        EstimateWithExplanationResponse
    """
    try:
        # 1. P6 모델 예측
        logger.info(
            f"[API] 요청: {request.property_type} {request.address_sido} "
            f"{request.appraisal_amount:,}원"
        )

        result = estimate_p6(
            appraisal_amount=request.appraisal_amount,
            property_type=request.property_type,
            address_sido=request.address_sido,
            land_area=request.land_area,
            building_area=request.building_area,
        )

        if not result:
            logger.error("[API] P6 모델 예측 실패")
            raise HTTPException(status_code=500, detail="P6 모델 예측 실패")

        # 2. 물건 정보 정규화
        property_info = {
            'property_type': request.property_type,
            'address_sido': request.address_sido,
            'address_sigungu': request.address_sigungu,
            'appraisal_amount': request.appraisal_amount,
            'total_area': (request.land_area or 0) + (request.building_area or 0),
        }

        # 3. RAG 설명 생성
        try:
            rag = get_rag_pipeline()
            rag_result = rag.process(property_info, result)
            explanation = rag_result['explanation']
            similar_cases = rag_result['similar_cases']
        except Exception as e:
            logger.warning(f"[API] RAG 처리 오류, 대체 설명 사용: {e}")
            explanation = "[RAG 처리 오류] 기본 설명만 제공됩니다."
            similar_cases = []

        # 4. 신뢰도 계산
        scorer = ConfidenceScorer()
        confidence = scorer.score(
            hammer_rate=result['hammer_rate'],
            similar_cases=similar_cases,
            mape=result['mape'],
            comparables_count=len(similar_cases),
        )

        # 5. 응답 구성
        response_data = {
            'hammer_price': result['hammer_price'],
            'hammer_rate': result['hammer_rate'],
            'mape': result['mape'],
            'confidence': {
                'score': confidence['score'],
                'level': confidence['level'],
                'reasons': confidence['reasons'],
            },
            'explanation': explanation,
            'similar_cases': [
                {
                    'doc_id': case['doc_id'],
                    'property_type': case['property_type'],
                    'address': case['address_sido'],
                    'hammer_price': case['hammer_price'],
                    'hammer_rate': case['hammer_rate'],
                    'similarity': case['similarity'],
                }
                for case in similar_cases[:5]
            ],
        }

        logger.info(
            f"[API] 완료: {result['hammer_price']:,}원, "
            f"신뢰도 {confidence['score']}점 ({confidence['level']})"
        )

        return EstimateWithExplanationResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] 예외 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"내부 오류: {str(e)}")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="헬스 체크",
    description="RAG 파이프라인 및 관련 서비스 상태 확인",
)
async def health_check():
    """헬스 체크

    Returns:
        {
            'status': 'ok' | 'degraded' | 'error',
            'services': {
                'p6_model': bool,
                'milvus': bool,
                'openai': bool,
            }
        }
    """
    health_status = {'services': {}}

    # P6 모델 확인
    try:
        result = estimate_p6(
            appraisal_amount=500_000_000,
            property_type='주거',
            address_sido='서울',
        )
        health_status['services']['p6_model'] = result is not None
    except Exception as e:
        logger.warning(f"[Health] P6 모델 체크 오류: {e}")
        health_status['services']['p6_model'] = False

    # Milvus 확인
    try:
        rag = get_rag_pipeline()
        health_status['services']['milvus'] = rag.collection is not None
    except Exception as e:
        logger.warning(f"[Health] Milvus 체크 오류: {e}")
        health_status['services']['milvus'] = False

    # OpenAI 확인
    try:
        rag = get_rag_pipeline()
        health_status['services']['openai'] = rag.client is not None
    except Exception as e:
        logger.warning(f"[Health] OpenAI 체크 오류: {e}")
        health_status['services']['openai'] = False

    # 종합 상태
    all_ok = all(health_status['services'].values())
    some_ok = any(health_status['services'].values())

    health_status['status'] = 'ok' if all_ok else ('degraded' if some_ok else 'error')
    disabled_services = [
        name for name, enabled in health_status['services'].items() if not enabled
    ]
    health_status['disabled_services'] = disabled_services
    health_status['safe_to_use_for_pricing'] = all_ok
    health_status['warnings'] = [
        f'SERVICE_DISABLED:{name}' for name in disabled_services
    ]

    return HealthResponse(**health_status)
