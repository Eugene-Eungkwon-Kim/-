"""비교사례 벡터 인덱스 (Milvus).

임베딩 모델(OpenAI 등)이 없는 환경이라 텍스트 임베딩 대신, 구조화된
필드(면적·가격·자산유형·지역·낙찰가율)로 만든 숫자 벡터를 쓴다. 자산유형
·지역 같은 범주형 값은 해시로 0~1 구간에 투영해 결정적으로(같은 입력은
항상 같은 값으로) 인코딩한다 — 근사치이지 정교한 임베딩은 아니다.

`MilvusClient(uri=...)` 는 uri 가 로컬 경로면 서버 없이 파일 하나로
동작하는 Milvus Lite, "http://host:port" 면 실제 Milvus 서버로 붙는다.
이 모듈은 두 경우를 구분하지 않는다 — 같은 코드가 그대로 서버 모드에도
적용된다는 뜻이다(단, 서버 모드 자체는 이 환경에 서버가 없어 실행
검증하지 못했다. Lite 모드로 전체 삽입·검색을 검증했다).
"""

import hashlib
import math
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

FEATURE_DIM = 6
COLLECTION_NAME = "avm_comparables"


def _bucket(text: str) -> float:
    """범주형 문자열을 0~1 사이 실수로 결정적으로 투영한다."""
    digest = hashlib.md5((text or "").encode("utf-8")).hexdigest()
    return (int(digest, 16) % 997) / 997.0


def vectorize(
    land_area: Optional[float], building_area: Optional[float],
    value: Optional[float], property_type: Optional[str],
    address_sido: Optional[str], hammer_rate: Optional[float],
) -> List[float]:
    return [
        math.log1p(land_area or 0.0),
        math.log1p(building_area or 0.0),
        math.log1p(value or 0.0),
        _bucket(property_type or ""),
        _bucket(address_sido or ""),
        float(hammer_rate or 0.0),
    ]


def ensure_collection(client, dimension: int = FEATURE_DIM) -> None:
    if client.has_collection(COLLECTION_NAME):
        return
    client.create_collection(collection_name=COLLECTION_NAME, dimension=dimension)


def build_index(db: Session, client) -> int:
    """SQL DB(Property/Appraisal/Auction/ComparableSale)에서 벡터를 뽑아 색인한다.

    전량 재색인이다 — 기존 컬렉션을 지우고 새로 채운다. 데이터가 적은
    초기 단계에 맞춘 단순한 구현이며, 데이터가 커지면 증분 색인이
    필요하다.
    """
    from app.db.models import Appraisal, Auction, ComparableSale, Property

    ensure_collection(client)
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)
    client.create_collection(collection_name=COLLECTION_NAME, dimension=FEATURE_DIM)

    rows: List[Dict[str, Any]] = []
    next_id = 1

    for prop in db.query(Property).all():
        latest_appr = (
            db.query(Appraisal)
            .filter(Appraisal.property_id == prop.id)
            .order_by(Appraisal.appraisal_date.desc())
            .first()
        )
        if latest_appr is None or not latest_appr.total_value:
            continue
        auction = db.query(Auction).filter(Auction.property_id == prop.id).first()
        hammer_price = float(auction.hammer_price) if auction and auction.hammer_price else None
        appr_value = float(latest_appr.total_value)
        hammer_rate = (hammer_price / appr_value) if hammer_price else None

        rows.append({
            "id": next_id,
            "vector": vectorize(prop.land_area, prop.building_area, appr_value,
                                prop.property_type, prop.address_sido, hammer_rate),
            "source_type": "appraisal",
            "property_type": prop.property_type or "",
            "address": prop.address_full or "",
            "hammer_price": hammer_price or 0.0,
            "hammer_rate": hammer_rate or 0.0,
        })
        next_id += 1

    for sale in db.query(ComparableSale).filter(ComparableSale.case_index > 0).all():
        if not sale.trade_amount:
            continue
        rows.append({
            "id": next_id,
            "vector": vectorize(sale.land_area, sale.building_area, float(sale.trade_amount),
                                sale.property_type, sale.address_sido, None),
            "source_type": "transaction",
            "property_type": sale.property_type or "",
            "address": sale.address_full or "",
            "hammer_price": float(sale.trade_amount),
            "hammer_rate": 0.0,
        })
        next_id += 1

    if rows:
        client.insert(collection_name=COLLECTION_NAME, data=rows)
    return len(rows)


FEATURE_LABELS = ["토지면적", "건물면적", "가격규모", "자산유형", "지역", "낙찰가율"]


def explain_match(query_vector: List[float], case_vector: List[float], top_n: int = 2) -> List[str]:
    """두 벡터의 축별 차이를 계산해, 가장 비슷한 축(=유사도에 가장 크게 기여한
    요인)을 사람이 읽을 문구로 돌려준다. SHAP 같은 모델 내부 설명은 아니지만,
    "왜 이 사례가 뽑혔는가"에 대한 근거를 실제 수치에서 뽑아낸다는 점에서
    이 검색 단계에 한정된 설명(explainability)이다.
    """
    diffs = [abs(q - c) for q, c in zip(query_vector, case_vector)]
    ranked = sorted(zip(FEATURE_LABELS, diffs), key=lambda pair: pair[1])
    return [label for label, _ in ranked[:top_n]]


def search_similar(client, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    if not client.has_collection(COLLECTION_NAME):
        return []
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_vector],
        limit=limit,
        output_fields=["source_type", "property_type", "address", "hammer_price",
                       "hammer_rate", "vector"],
    )
    if not results:
        return []
    hits = results[0]
    return [
        {
            "doc_id": hit["id"],
            "property_type": hit["entity"]["property_type"],
            "address_sido": hit["entity"]["address"],
            "hammer_price": hit["entity"]["hammer_price"],
            "hammer_rate": hit["entity"]["hammer_rate"],
            # L2 거리를 0~1 유사도로 변환(거리 0 -> 유사도 1, 거리가 커질수록 감소).
            "similarity": 1.0 / (1.0 + hit["distance"]),
            "match_reasons": explain_match(query_vector, hit["entity"]["vector"]),
        }
        for hit in hits
    ]
