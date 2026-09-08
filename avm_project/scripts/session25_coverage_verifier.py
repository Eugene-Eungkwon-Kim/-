"""Verify Session 25A comparable coverage dry-run artifacts."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
CONFIG_DIR = PROJECT_ROOT / "config"
DATE_TAG = "20260704"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def check_diagnostic() -> Check:
    path = RESULTS_DIR / f"session25_coverage_diagnostic_{DATE_TAG}.json"
    data = read_json(path)
    diagnostics = data.get("diagnostics", [])
    target = [
        item for item in diagnostics
        if item.get("sido") == "경기도"
        and item.get("sigungu") == "화성시"
        and item.get("property_type") == "아파트"
    ]
    ok = len(diagnostics) >= 30 and target and target[0]["probe_counts"]["appraisal_candidate_count"] == 0
    evidence = {
        "diagnosed_groups": len(diagnostics),
        "reason_counts": data.get("summary", {}).get("reason_counts"),
        "hwaseong_apartment": target[0] if target else None,
    }
    return Check("diagnostic_batch", pass_fail(bool(ok)), "30+ groups and target 0-source case", evidence)


def check_crosswalks() -> Check:
    rows = read_json(CONFIG_DIR / "session25_sigungu_crosswalk_candidates.json")
    all_review = all(row["review_status"] == "NEEDS_REVIEW" and not row["customer_safe"] for row in rows)
    has_hwaseong = any(
        row["query_sigungu"] == "화성시" and row["candidate_sigungu"] in {"화성만세구", "화성효행구"}
        for row in rows
    )
    bad_short = any(row["candidate_sigungu"] in {"동구"} and row["query_sigungu"] == "동래구" for row in rows)
    evidence = {"count": len(rows), "has_hwaseong": has_hwaseong, "bad_short_prefix": bad_short}
    return Check("district_crosswalks", pass_fail(all_review and has_hwaseong and not bad_short), "review-only district candidates", evidence)


def check_taxonomy() -> Check:
    rows = read_json(CONFIG_DIR / "session25_property_type_taxonomy_candidates.json")
    by_raw = {row["raw_property_type"]: row for row in rows}
    apt_factory = by_raw.get("아파트형공장")
    apt = by_raw.get("아파트")
    ok = (
        apt_factory is not None
        and apt_factory["property_type_class"] == "KNOWLEDGE_INDUSTRIAL_CENTER"
        and "APARTMENT_SUBSTRING_NOT_RESIDENTIAL" in apt_factory["risk_flags"]
        and apt is not None
        and apt["property_type_class"] == "RESIDENTIAL_APARTMENT"
        and all(not row["customer_safe"] for row in rows)
    )
    evidence = {"count": len(rows), "apartment": apt, "apartment_factory": apt_factory}
    return Check("type_taxonomy", pass_fail(ok), "apartment substring separated", evidence)


def check_queue() -> Check:
    rows = read_json(RESULTS_DIR / f"session25_comparable_candidate_queue_{DATE_TAG}.json")
    customer_safe_true = [row for row in rows if row["customer_safe"]]
    false_promotion = [
        row for row in rows
        if row["query_property_type"] == "아파트" and row["candidate_property_type"] == "아파트형공장"
    ]
    all_review = all(row["review_status"] == "NEEDS_REVIEW" for row in rows)
    evidence = {
        "count": len(rows),
        "customer_safe_true": len(customer_safe_true),
        "false_promotion": len(false_promotion),
    }
    return Check("candidate_queue", pass_fail(all_review and not customer_safe_true and not false_promotion), "dry-run queue safety", evidence)


def check_session24_smoke() -> Check:
    data = read_json(RESULTS_DIR / "session24_api_live_smoke_20260704.json")
    ok = data.get("overall") == "PASS" and all(item.get("status") == "PASS" for item in data.get("checks", []))
    evidence = {"overall": data.get("overall"), "check_count": len(data.get("checks", []))}
    return Check("session24_smoke_baseline", pass_fail(ok), "prior API smoke remains PASS", evidence)


def run_checks() -> list[Check]:
    return [
        check_diagnostic(),
        check_crosswalks(),
        check_taxonomy(),
        check_queue(),
        check_session24_smoke(),
    ]


def write_reports(checks: list[Check]) -> str:
    overall = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    payload = {
        "created_at": datetime.now().isoformat(),
        "overall": overall,
        "checks": [asdict(check) for check in checks],
    }
    json_path = RESULTS_DIR / f"session25_coverage_verifier_{DATE_TAG}.json"
    md_path = RESULTS_DIR / f"session25_coverage_verifier_{DATE_TAG}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Session 25A Coverage Verifier", "", f"- Overall: **{overall}**", "", "| Check | Status | Detail |", "|---|---|---|"]
    lines.extend(f"| {check.name} | {check.status} | {check.detail} |" for check in checks)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return overall


def main() -> int:
    checks = run_checks()
    overall = write_reports(checks)
    print(f"Session 25A coverage verifier: {overall}")
    for check in checks:
        print(f"- {check.status}: {check.name} ({check.detail})")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
