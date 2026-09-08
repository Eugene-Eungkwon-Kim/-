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

# 자산유형별로 "근거로 의미 있는" 축의 우선순위. 예: 토지는 건물이 없으므로
# 건물면적 축이 우연히 가깝더라도 근거로 내세우면 감정평가 근거로 부적절하다
# (평가서 분석 에이전트가 이 근거를 그대로 인용하므로 축의 종류 자체가 맞아야 한다).
# 키는 property_type 문자열의 부분일치로 찾는다(수집기별 표기가
# "공장창고"/"상가"처럼 제각각이라 정확히 일치시키기 어렵다).
_TYPE_AXIS_PRIORITY = {
    "토지": ["토지면적", "지역", "가격규모"],
    "공장": ["건물면적", "토지면적", "가격규모"],
    "창고": ["건물면적", "토지면적", "가격규모"],
    "상가": ["건물면적", "토지면적", "가격규모"],
}
_DEFAULT_AXIS_PRIORITY = ["건물면적", "가격규모", "지역"]


def _axis_priority(property_type: Optional[str]) -> List[str]:
    for keyword, priority in _TYPE_AXIS_PRIORITY.items():
        if property_type and keyword in property_type:
            return priority
    return _DEFAULT_AXIS_PRIORITY


def _ranked_axes(
    query_vector: List[float], case_vector: List[float],
    property_type: Optional[str], top_n: int,
) -> List[tuple]:
    """(축 이름, 차이) 를 유형에 맞는 축 우선 + 그 안에서 차이가 작은 순으로 정렬한다."""
    diffs = [abs(q - c) for q, c in zip(query_vector, case_vector)]
    priority = _axis_priority(property_type)
    ranked = sorted(
        zip(FEATURE_LABELS, diffs),
        key=lambda pair: (0 if pair[0] in priority else 1, pair[1]),
    )
    return ranked[:top_n]


def explain_match(
    query_vector: List[float], case_vector: List[float],
    property_type: Optional[str] = None, top_n: int = 2,
) -> List[str]:
    """두 벡터의 축별 차이를 계산해, 근거로 내세울 축(=유사도에 기여한 요인이면서
    이 자산유형에 실제로 의미 있는 축)을 사람이 읽을 문구로 돌려준다. SHAP 같은
    모델 내부 설명은 아니지만, "왜 이 사례가 뽑혔는가"에 대한 근거를 실제
    수치에서 뽑아낸다는 점에서 이 검색 단계에 한정된 설명(explainability)이다.
    """
    return [label for label, _ in _ranked_axes(query_vector, case_vector, property_type, top_n)]


def explain_match_detailed(
    query_vector: List[float], case_vector: List[float],
    property_type: Optional[str] = None, top_n: int = 3,
) -> List[Dict[str, Any]]:
    """explain_match 의 구조화 버전 — 축 이름뿐 아니라 차이값도 그대로 노출한다.

    문자열 근거(match_reasons)를 다시 파싱하지 않고도 프로그램적으로 근거를
    소비할 수 있어야 한다는 요구(평가서 분석 에이전트 연동)에 맞춘 필드다.
    """
    return [
        {"axis": label, "diff": round(diff, 4)}
        for label, diff in _ranked_axes(query_vector, case_vector, property_type, top_n)
    ]


def search_similar(
    client, query_vector: List[float],
    property_type: Optional[str] = None, limit: int = 5,
) -> List[Dict[str, Any]]:
    """비교사례를 검색한다. property_type 이 주어지면 같은 유형을 우선한다 —
    벡터 거리만으로는 자산유형이 다른 사례가 섞여 들어올 수 있는데(예: 대형
    상가와 소형 공장이 가격·면적이 비슷해 가까이 위치), 그런 사례는 감정평가
    근거로 부적절하다. 같은 유형이 limit 에 못 미치면 부족분만 다른 유형으로
    채우고 각 사례에 type_matched 로 표시한다 — 결과를 조용히 숨기지 않는다.
    """
    if not client.has_collection(COLLECTION_NAME):
        return []

    output_fields = ["source_type", "property_type", "address", "hammer_price",
                     "hammer_rate", "vector"]
    hits: List[Dict[str, Any]] = []
    seen_ids = set()

    if property_type:
        same_type = client.search(
            collection_name=COLLECTION_NAME, data=[query_vector], limit=limit,
            filter=f'property_type == "{property_type}"', output_fields=output_fields,
        )
        if same_type:
            hits.extend(same_type[0])
            seen_ids.update(hit["id"] for hit in same_type[0])

    if len(hits) < limit:
        broader = client.search(
            collection_name=COLLECTION_NAME, data=[query_vector], limit=limit,
            output_fields=output_fields,
        )
        if broader:
            for hit in broader[0]:
                if hit["id"] not in seen_ids and len(hits) < limit:
                    hits.append(hit)
                    seen_ids.add(hit["id"])

    return [
        {
            "doc_id": hit["id"],
            "property_type": hit["entity"]["property_type"],
            "address_sido": hit["entity"]["address"],
            "hammer_price": hit["entity"]["hammer_price"],
            "hammer_rate": hit["entity"]["hammer_rate"],
            # L2 거리를 0~1 유사도로 변환(거리 0 -> 유사도 1, 거리가 커질수록 감소).
            "similarity": 1.0 / (1.0 + hit["distance"]),
            "match_reasons": explain_match(query_vector, hit["entity"]["vector"], property_type),
            "evidence": explain_match_detailed(query_vector, hit["entity"]["vector"], property_type),
            "type_matched": (not property_type) or hit["entity"]["property_type"] == property_type,
        }
        for hit in hits
    ]
