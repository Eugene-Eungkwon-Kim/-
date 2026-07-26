"""Verify Session 25B approved-only dry-run artifacts."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
DATE_TAG = "20260704"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def status(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def check_dryrun_summary() -> Check:
    data = read_json(RESULTS_DIR / f"session25b_approved_dryrun_{DATE_TAG}.json")
    summary = data["summary"]
    valid_statuses = {"AWAITING_APPROVAL", "DRYRUN_READY", "NO_MATCHING_APPROVED_QUEUE_ROWS"}
    ok = summary["status"] in valid_statuses and not summary["unknown_crosswalk_ids"] and not summary["unknown_type_rule_ids"]
    return Check("dryrun_summary", status(ok), "valid dry-run status and known rule ids", summary)


def check_no_approval_no_preview() -> Check:
    data = read_json(RESULTS_DIR / f"session25b_approved_dryrun_{DATE_TAG}.json")
    summary = data["summary"]
    no_approved_rules = summary["approved_crosswalks"] == 0 and summary["approved_type_rules"] == 0
    ok = not no_approved_rules or summary["preview_rows"] == 0
    evidence = {
        "no_approved_rules": no_approved_rules,
        "preview_rows": summary["preview_rows"],
    }
    return Check("no_approval_no_preview", status(ok), "empty approval file yields zero preview rows", evidence)


def check_preview_safety() -> Check:
    data = read_json(RESULTS_DIR / f"session25b_approved_dryrun_{DATE_TAG}.json")
    rows = data["preview_rows"]
    unsafe = [
        row for row in rows
        if row.get("customer_safe") is not False or row.get("preview_only") is not True
    ]
    estimate_modifying = [row for row in rows if row.get("would_modify_estimate")]
    evidence = {"preview_rows": len(rows), "unsafe_rows": len(unsafe), "estimate_modifying": len(estimate_modifying)}
    return Check("preview_safety", status(not unsafe and not estimate_modifying), "preview rows stay non-customer and non-mutating", evidence)


def check_session24_smoke() -> Check:
    data = read_json(RESULTS_DIR / "session24_api_live_smoke_20260704.json")
    ok = data.get("overall") == "PASS" and all(item.get("status") == "PASS" for item in data.get("checks", []))
    evidence = {"overall": data.get("overall"), "check_count": len(data.get("checks", []))}
    return Check("session24_smoke", status(ok), "API smoke baseline remains PASS", evidence)


def run_checks() -> list[Check]:
    return [
        check_dryrun_summary(),
        check_no_approval_no_preview(),
        check_preview_safety(),
        check_session24_smoke(),
    ]


def write_reports(checks: list[Check]) -> str:
    overall = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    payload = {
        "created_at": datetime.now().isoformat(),
        "overall": overall,
        "checks": [asdict(check) for check in checks],
    }
    (RESULTS_DIR / f"session25b_dryrun_verifier_{DATE_TAG}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = ["# Session 25B Dry-Run Verifier", "", f"- Overall: **{overall}**", "", "| Check | Status | Detail |", "|---|---|---|"]
    lines.extend(f"| {check.name} | {check.status} | {check.detail} |" for check in checks)
    (RESULTS_DIR / f"session25b_dryrun_verifier_{DATE_TAG}.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return overall


def main() -> int:
    overall = write_reports(run_checks())
    print(f"Session 25B dry-run verifier: {overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
