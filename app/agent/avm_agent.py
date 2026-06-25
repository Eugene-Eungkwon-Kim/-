from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np
from anthropic import Anthropic

from app.avm.engine_v2 import AVMEngineV2

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 부동산 감정평가 AI 어시스턴트입니다.
툴로 DB를 조회하고 AVM 엔진으로 추정가를 계산한 후, 물건 정보·평가 결과·비교사례·신뢰도 순서로 답변하세요."""

TOOLS = [
    {
        "name": "search_property_by_address",
        "description": "주소로 NPL 물건 검색",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "검색 주소"},
                "property_type": {"type": "string", "enum": ["아파트", "다세대", "연립", "오피스텔"]},
            },
            "required": ["address"],
        },
    },
    {
        "name": "estimate_avm",
        "description": "물건 ID로 AVM 감정가 추정",
        "input_schema": {
            "type": "object",
            "properties": {"property_id": {"type": "integer"}},
            "required": ["property_id"],
        },
    },
    {
        "name": "find_comparable_sales",
        "description": "지역 최근 거래 비교사례 조회",
        "input_schema": {
            "type": "object",
            "properties": {
                "sido": {"type": "string"},
                "sigungu": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["sido"],
        },
    },
    {
        "name": "analyze_market_trends",
        "description": "시도별 거래 추세 분석",
        "input_schema": {
            "type": "object",
            "properties": {
                "sido": {"type": "string"},
                "months": {"type": "integer"},
            },
            "required": ["sido"],
        },
    },
]


class AVMAgent:
    MODEL = "claude-opus-4-8"

    def __init__(self, api_key: str, db: "Session"):
        self.client = Anthropic(api_key=api_key)
        self.db = db
        self.engine = AVMEngineV2(db)

    def query(self, user_message: str) -> str:
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

        for _ in range(10):
            resp = self.client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if resp.stop_reason == "end_turn":
                return next((b.text for b in resp.content if hasattr(b, "text")), "")

            if resp.stop_reason == "tool_use":
                results = []
                for tc in (b for b in resp.content if b.type == "tool_use"):
                    try:
                        content = json.dumps(self._run_tool(tc.name, tc.input), ensure_ascii=False, default=str)
                        results.append({"type": "tool_result", "tool_use_id": tc.id, "content": content, "is_error": False})
                    except Exception as e:
                        results.append({"type": "tool_result", "tool_use_id": tc.id, "content": str(e), "is_error": True})
                messages += [{"role": "assistant", "content": resp.content}, {"role": "user", "content": results}]

        return "최대 반복 횟수 초과"

    def _run_tool(self, name: str, inp: dict) -> Any:
        from sqlalchemy import select
        from app.db.models import Complex, Property, Transaction

        if name == "search_property_by_address":
            props = self.db.execute(
                select(Property).where(Property.address_full.ilike(f"%{inp['address']}%")).limit(5)
            ).scalars().all()
            return {"count": len(props), "properties": [
                {"id": p.id, "address": p.address_full, "type": p.property_type, "area": p.building_area}
                for p in props
            ]}

        if name == "estimate_avm":
            prop = self.db.get(Property, inp["property_id"])
            if not prop:
                return {"error": "물건을 찾을 수 없습니다"}
            try:
                r = self.engine.estimate(prop)
                return {"property_id": r.property_id, "point_estimate": r.point_estimate,
                        "lower_bound": r.lower_bound, "upper_bound": r.upper_bound,
                        "comparable_count": r.comparable_count}
            except ValueError as e:
                return {"error": str(e)}

        if name == "find_comparable_sales":
            cond = [Complex.address_sido == inp["sido"]]
            if inp.get("sigungu"):
                cond.append(Complex.address_sigungu == inp["sigungu"])
            txs = self.db.execute(
                select(Transaction).join(Complex).where(*cond)
                .order_by(Transaction.report_date.desc()).limit(inp.get("limit", 10))
            ).scalars().all()
            return {"count": len(txs), "sales": [
                {"address": tx.complex.address_full if tx.complex else "",
                 "price": int(tx.price), "date": tx.report_date.isoformat() if tx.report_date else None,
                 "area": tx.exclusive_area}
                for tx in txs
            ]}

        if name == "analyze_market_trends":
            cutoff = date.today() - timedelta(days=30 * inp.get("months", 12))
            txs = self.db.execute(
                select(Transaction).join(Complex)
                .where(Complex.address_sido == inp["sido"], Transaction.report_date >= cutoff)
            ).scalars().all()
            prices = [float(t.price) for t in txs]
            return {"sido": inp["sido"], "transaction_count": len(txs),
                    "avg_price": int(np.mean(prices)) if prices else 0,
                    "max_price": int(np.max(prices)) if prices else 0,
                    "min_price": int(np.min(prices)) if prices else 0}

        raise ValueError(f"Unknown tool: {name}")
