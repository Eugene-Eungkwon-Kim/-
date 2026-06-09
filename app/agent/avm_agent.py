from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Dict, List

import numpy as np
from anthropic import Anthropic

from app.avm.engine_v2 import AVMEngineV2

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
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


class AVMAgent:
    """
    Claude 기반 자동감정평가 Agent

    Tool Use 패턴으로 DB 검색 → AVM 추정 → 자연어 설명 자동화
    """

    MODEL = "claude-opus-4-8"

    def __init__(self, api_key: str, db: "Session"):
        self.client = Anthropic(api_key=api_key)
        self.db = db
        self.engine = AVMEngineV2(db)
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_property_by_address",
                "description": "주소로 NPL 물건 또는 단지 검색. 예: '경기도 화성시 봉담읍 아파트'",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "검색 주소 (시도/시군구/동 포함)",
                        },
                        "property_type": {
                            "type": "string",
                            "description": "물건 유형",
                            "enum": ["아파트", "다세대", "연립", "오피스텔"],
                        },
                    },
                    "required": ["address"],
                },
            },
            {
                "name": "estimate_avm",
                "description": "물건 ID로 감정평가가(AVM) 추정",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "property_id": {
                            "type": "integer",
                            "description": "NPL 물건 ID",
                        }
                    },
                    "required": ["property_id"],
                },
            },
            {
                "name": "find_comparable_sales",
                "description": "특정 지역의 최근 거래 비교사례 조회",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sido": {"type": "string", "description": "시도명"},
                        "sigungu": {"type": "string", "description": "시군구명"},
                        "limit": {
                            "type": "integer",
                            "description": "반환 건수 (기본 10)",
                        },
                    },
                    "required": ["sido"],
                },
            },
            {
                "name": "analyze_market_trends",
                "description": "특정 시도의 거래 추세 분석",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sido": {"type": "string", "description": "시도명"},
                        "months": {
                            "type": "integer",
                            "description": "분석 기간(개월), 기본 12",
                        },
                    },
                    "required": ["sido"],
                },
            },
        ]

    def query(self, user_message: str) -> str:
        """사용자 질의 처리 (Tool Use 루프)"""
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        for _ in range(10):
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_calls = [b for b in response.content if b.type == "tool_use"]
                tool_results = []

                for tc in tool_calls:
                    try:
                        result = self._execute_tool(tc.name, tc.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tc.id,
                                "content": json.dumps(
                                    result, ensure_ascii=False, default=str
                                ),
                                "is_error": False,
                            }
                        )
                    except Exception as exc:
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tc.id,
                                "content": f"Error: {exc}",
                                "is_error": True,
                            }
                        )

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

        return "최대 반복 횟수 초과"

    def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        from sqlalchemy import select
        from app.db.models import Complex, Property, Transaction

        if tool_name == "search_property_by_address":
            address = tool_input["address"]
            stmt = (
                select(Property)
                .where(Property.address_full.ilike(f"%{address}%"))
                .limit(5)
            )
            props = self.db.execute(stmt).scalars().all()
            return {
                "count": len(props),
                "properties": [
                    {
                        "id": p.id,
                        "address": p.address_full,
                        "type": p.property_type,
                        "area": p.building_area,
                    }
                    for p in props
                ],
            }

        elif tool_name == "estimate_avm":
            prop_id = tool_input["property_id"]
            prop = self.db.get(Property, prop_id)
            if not prop:
                return {"error": "물건을 찾을 수 없습니다"}
            try:
                result = self.engine.estimate(prop)
                return {
                    "property_id": result.property_id,
                    "point_estimate": result.point_estimate,
                    "lower_bound": result.lower_bound,
                    "upper_bound": result.upper_bound,
                    "confidence": result.confidence_level,
                    "comparable_count": result.comparable_count,
                }
            except ValueError as exc:
                return {"error": str(exc)}

        elif tool_name == "find_comparable_sales":
            sido = tool_input["sido"]
            sigungu = tool_input.get("sigungu", "")
            limit = tool_input.get("limit", 10)

            cond = [Complex.address_sido == sido]
            if sigungu:
                cond.append(Complex.address_sigungu == sigungu)

            stmt = (
                select(Transaction)
                .join(Complex, Transaction.complex_id == Complex.id)
                .where(*cond)
                .order_by(Transaction.report_date.desc())
                .limit(limit)
            )
            txs = self.db.execute(stmt).scalars().all()
            return {
                "count": len(txs),
                "sales": [
                    {
                        "address": tx.complex.address_full if tx.complex else "",
                        "price": int(tx.price),
                        "date": tx.report_date.isoformat() if tx.report_date else None,
                        "area": tx.exclusive_area,
                    }
                    for tx in txs
                ],
            }

        elif tool_name == "analyze_market_trends":
            sido = tool_input["sido"]
            months = tool_input.get("months", 12)
            cutoff = date.today() - timedelta(days=30 * months)

            stmt = (
                select(Transaction)
                .join(Complex, Transaction.complex_id == Complex.id)
                .where(
                    Complex.address_sido == sido,
                    Transaction.report_date >= cutoff,
                )
            )
            txs = self.db.execute(stmt).scalars().all()
            prices = [float(t.price) for t in txs]
            return {
                "sido": sido,
                "period_months": months,
                "transaction_count": len(txs),
                "avg_price": int(np.mean(prices)) if prices else 0,
                "max_price": int(np.max(prices)) if prices else 0,
                "min_price": int(np.min(prices)) if prices else 0,
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
