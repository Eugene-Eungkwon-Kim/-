"""Session 24 live API smoke test for NPL AVM FastAPI."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = PROJECT_ROOT / "results" / "session24_api_live_smoke_20260704.json"
RESULT_MD = PROJECT_ROOT / "results" / "session24_api_live_smoke_20260704.md"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any]


def _request_json(
    base_url: str,
    path: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    query = f"?{urlencode(params)}" if params else ""
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = Request(f"{base_url.rstrip('/')}{path}{query}", data=body, method=method, headers=headers)
    with urlopen(req, timeout=10) as response:
        raw = response.read().decode("utf-8")
        return response.status, json.loads(raw) if raw else None


def _capture(name: str, fn: Any) -> CheckResult:
    try:
        return fn()
    except HTTPError as exc:
        return CheckResult(name, "FAIL", f"HTTP {exc.code}", {"error": str(exc)})
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return CheckResult(name, "FAIL", type(exc).__name__, {"error": str(exc)})


def _schema_for(openapi: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    operation = openapi.get("paths", {}).get(path, {}).get(method, {})
    response = operation.get("responses", {}).get("200", {})
    content = response.get("content", {}).get("application/json", {})
    return content.get("schema", {})


def check_root(base_url: str) -> CheckResult:
    status, data = _request_json(base_url, "/")
    ok = status == 200 and data.get("status") == "ok"
    return CheckResult("root", "PASS" if ok else "FAIL", "root endpoint", {"status": status, "body": data})


def check_openapi(base_url: str) -> CheckResult:
    _, data = _request_json(base_url, "/openapi.json")
    required = ["/", "/api/v1/precedents", "/api/v1/auction-stats", "/api/v1/properties/{property_serial}", "/api/v1/comparable-sales", "/api/v4/health"]
    missing = [path for path in required if not _schema_for(data, path, "get")]
    status = "PASS" if not missing else "FAIL"
    return CheckResult("openapi_response_models", status, "non-empty response schemas", {"missing": missing})


def check_precedents(base_url: str) -> CheckResult:
    params = {"sido": "경기도", "limit": 3}
    status, data = _request_json(base_url, "/api/v1/precedents", params=params)
    ok = status == 200 and data.get("count", 0) > 0 and len(data.get("items", [])) <= 3
    return CheckResult("precedents_utf8", "PASS" if ok else "FAIL", "Korean query precedent search", {"status": status, "count": data.get("count")})


def check_auction_stats(base_url: str) -> CheckResult:
    params = {"property_type": "아파트", "sido": "경기도"}
    status, data = _request_json(base_url, "/api/v1/auction-stats", params=params)
    ok = status == 200 and data.get("property_type") == "아파트" and "stats" in data
    return CheckResult("auction_stats_utf8", "PASS" if ok else "FAIL", "Korean query auction stats", {"status": status, "stats": len(data.get("stats", []))})


def check_estimate_diagnostics(base_url: str) -> CheckResult:
    payload = {"address_sido": "경기도", "address_sigungu": "화성시", "property_type": "아파트", "max_comparables": 3}
    status, data = _request_json(base_url, "/api/v1/avm/estimate", method="POST", payload=payload)
    diagnostics = data.get("diagnostics")
    ok = status == 200 and data.get("comparable_count") == 0 and diagnostics and diagnostics.get("status") == "NO_COMPARABLES"
    evidence = {"status": status, "comparable_count": data.get("comparable_count"), "diagnostics": diagnostics}
    return CheckResult("estimate_empty_diagnostics", "PASS" if ok else "FAIL", "0-comparable diagnostic response", evidence)


def check_rag_health(base_url: str) -> CheckResult:
    status, data = _request_json(base_url, "/api/v4/health")
    has_fields = {"disabled_services", "safe_to_use_for_pricing", "warnings"}.issubset(data)
    ok = status == 200 and has_fields and data.get("safe_to_use_for_pricing") is False
    evidence = {"status": status, "health": data.get("status"), "disabled_services": data.get("disabled_services")}
    return CheckResult("rag_health_degraded_contract", "PASS" if ok else "FAIL", "explicit degraded health contract", evidence)


def run_checks(base_url: str) -> list[CheckResult]:
    checks = [
        ("root", lambda: check_root(base_url)),
        ("openapi_response_models", lambda: check_openapi(base_url)),
        ("precedents_utf8", lambda: check_precedents(base_url)),
        ("auction_stats_utf8", lambda: check_auction_stats(base_url)),
        ("estimate_empty_diagnostics", lambda: check_estimate_diagnostics(base_url)),
        ("rag_health_degraded_contract", lambda: check_rag_health(base_url)),
    ]
    return [_capture(name, fn) for name, fn in checks]


def _write_report(results: list[CheckResult], base_url: str) -> str:
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    overall = "PASS" if all(item.status == "PASS" for item in results) else "FAIL"
    payload = {"base_url": base_url, "created_at": datetime.now().isoformat(), "overall": overall, "checks": [asdict(item) for item in results]}
    RESULT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Session 24 API Live Smoke", "", f"- Base URL: `{base_url}`", f"- Overall: **{overall}**", "", "| Check | Status | Detail |", "|---|---|---|"]
    lines.extend(f"| {item.name} | {item.status} | {item.detail} |" for item in results)
    RESULT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return overall


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    results = run_checks(args.base_url)
    overall = _write_report(results, args.base_url)
    print(f"Session 24 API live smoke: {overall}")
    for item in results:
        print(f"- {item.status}: {item.name} ({item.detail})")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
