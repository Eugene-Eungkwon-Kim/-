"""Session 25B approved-only dry-run preview builder."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
RESULTS_DIR = PROJECT_ROOT / "results"
DATE_TAG = "20260704"


@dataclass(frozen=True)
class DryRunSummary:
    status: str
    approved_crosswalks: int
    approved_type_rules: int
    unknown_crosswalk_ids: list[str]
    unknown_type_rule_ids: list[str]
    queue_rows: int
    preview_rows: int
    customer_safe_true: int


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def known_ids(rows: list[dict[str, Any]], key: str) -> set[str]:
    return {str(row[key]) for row in rows}


def select_preview_rows(
    queue: list[dict[str, Any]],
    approved_crosswalks: set[str],
    approved_types: set[str],
) -> list[dict[str, Any]]:
    rows = []
    for row in queue:
        if row["district_rule_id"] not in approved_crosswalks:
            continue
        if row["type_rule_id"] not in approved_types:
            continue
        preview = dict(row)
        preview["preview_only"] = True
        preview["customer_safe"] = False
        preview["would_modify_estimate"] = False
        rows.append(preview)
    return rows


def build_review_packet(
    approved: dict[str, Any],
    crosswalks: list[dict[str, Any]],
    queue: list[dict[str, Any]],
    type_rules: list[dict[str, Any]],
) -> None:
    lines = [
        "# Session 25B Candidate Review Packet",
        "",
        f"- Approval status: `{approved.get('status')}`",
        f"- Approved crosswalks: {len(approved.get('approved_crosswalk_rule_ids', []))}",
        f"- Approved type rules: {len(approved.get('approved_type_rule_ids', []))}",
        "- Customer-safe candidates before approval: 0",
        "",
        "## Crosswalk Candidates",
        "",
        "| Rule | Query | Candidate | Evidence | Status |",
        "|---|---|---|---:|---|",
    ]
    for row in crosswalks:
        lines.append(
            f"| {row['rule_id']} | {row['query_sigungu']} | {row['candidate_sigungu']} | "
            f"{row['evidence_comparable_count']} | {row['review_status']} |"
        )
    lines.extend(["", "## Candidate Queue", "", "| Queue | Query | Candidate | Rules | Evidence |", "|---|---|---|---|---:|"])
    for row in queue:
        lines.append(
            f"| {row['queue_id']} | {row['query_sigungu']} {row['query_property_type']} | "
            f"{row['candidate_sigungu']} {row['candidate_property_type']} | "
            f"{row['district_rule_id']} / {row['type_rule_id']} | {row['evidence_count']} |"
        )
    lines.extend(["", "## Key Type Rules", "", "| Rule | Raw Type | Class | Flags |", "|---|---|---|---|"])
    for row in _key_type_rules(type_rules):
        lines.append(
            f"| {row['rule_id']} | {row['raw_property_type']} | {row['property_type_class']} | "
            f"{','.join(row['risk_flags'])} |"
        )
    path = RESULTS_DIR / f"session25b_candidate_review_packet_{DATE_TAG}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _key_type_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = {"아파트", "아파트형공장", "공장", "창고", "창고용지"}
    return [row for row in rows if row["raw_property_type"] in wanted]


def build_payload() -> dict[str, Any]:
    approved = read_json(CONFIG_DIR / "session25b_approved_rules.json")
    crosswalks = read_json(CONFIG_DIR / "session25_sigungu_crosswalk_candidates.json")
    type_rules = read_json(CONFIG_DIR / "session25_property_type_taxonomy_candidates.json")
    queue = read_json(RESULTS_DIR / f"session25_comparable_candidate_queue_{DATE_TAG}.json")
    approved_crosswalks = set(approved.get("approved_crosswalk_rule_ids", []))
    approved_types = set(approved.get("approved_type_rule_ids", []))
    unknown_crosswalks = sorted(approved_crosswalks - known_ids(crosswalks, "rule_id"))
    unknown_types = sorted(approved_types - known_ids(type_rules, "rule_id"))
    preview_rows = select_preview_rows(queue, approved_crosswalks, approved_types)
    status = _status(approved_crosswalks, approved_types, unknown_crosswalks, unknown_types, preview_rows)
    summary = DryRunSummary(
        status=status,
        approved_crosswalks=len(approved_crosswalks),
        approved_type_rules=len(approved_types),
        unknown_crosswalk_ids=unknown_crosswalks,
        unknown_type_rule_ids=unknown_types,
        queue_rows=len(queue),
        preview_rows=len(preview_rows),
        customer_safe_true=sum(1 for row in preview_rows if row["customer_safe"]),
    )
    build_review_packet(approved, crosswalks, queue, type_rules)
    return {
        "created_at": datetime.now().isoformat(),
        "summary": asdict(summary),
        "preview_rows": preview_rows,
    }


def _status(
    approved_crosswalks: set[str],
    approved_types: set[str],
    unknown_crosswalks: list[str],
    unknown_types: list[str],
    preview_rows: list[dict[str, Any]],
) -> str:
    if unknown_crosswalks or unknown_types:
        return "INVALID_APPROVAL_RULES"
    if not approved_crosswalks and not approved_types:
        return "AWAITING_APPROVAL"
    if preview_rows:
        return "DRYRUN_READY"
    return "NO_MATCHING_APPROVED_QUEUE_ROWS"


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Session 25B Approved Dry-Run",
        "",
        f"- Status: **{summary['status']}**",
        f"- Approved crosswalks: {summary['approved_crosswalks']}",
        f"- Approved type rules: {summary['approved_type_rules']}",
        f"- Queue rows: {summary['queue_rows']}",
        f"- Preview rows: {summary['preview_rows']}",
        f"- Customer-safe true: {summary['customer_safe_true']}",
        "",
        "No estimator or API code was modified.",
    ]
    (RESULTS_DIR / f"session25b_approved_dryrun_{DATE_TAG}.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    RESULTS_DIR.mkdir(exist_ok=True)
    payload = build_payload()
    write_json(RESULTS_DIR / f"session25b_approved_dryrun_{DATE_TAG}.json", payload)
    write_markdown(payload)
    summary = payload["summary"]
    print(
        "Session 25B approved dry-run: "
        f"{summary['status']} preview_rows={summary['preview_rows']}"
    )
    return 0 if summary["status"] != "INVALID_APPROVAL_RULES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
