"""Build Session 25A dry-run comparable coverage diagnostics."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "npl_avm.db"
RESULTS_DIR = PROJECT_ROOT / "results"
CONFIG_DIR = PROJECT_ROOT / "config"
DATE_TAG = "20260704"


@dataclass(frozen=True)
class Group:
    sido: str
    sigungu: str
    property_type: str
    count: int


@dataclass(frozen=True)
class Diagnostic:
    sido: str
    sigungu: str
    property_type: str
    property_type_class: str
    property_group_count: int
    reason_codes: list[str]
    probe_counts: dict[str, int]


@dataclass(frozen=True)
class CrosswalkCandidate:
    rule_id: str
    query_sido: str
    query_sigungu: str
    candidate_sido: str
    candidate_sigungu: str
    evidence_property_count: int
    evidence_comparable_count: int
    match_basis: str
    review_status: str
    customer_safe: bool


@dataclass(frozen=True)
class TypeCandidate:
    rule_id: str
    raw_property_type: str
    property_type_class: str
    source_count: int
    risk_flags: list[str]
    review_status: str
    customer_safe: bool


@dataclass(frozen=True)
class QueueRow:
    queue_id: str
    query_sido: str
    query_sigungu: str
    query_property_type: str
    candidate_source: str
    candidate_sido: str
    candidate_sigungu: str
    candidate_property_type: str
    district_rule_id: str
    type_rule_id: str
    evidence_count: int
    risk_flags: list[str]
    review_status: str
    customer_safe: bool


def classify_type(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return "OTHER"
    if any(token in text for token in ["아파트형공장", "지식산업센터"]):
        return "KNOWLEDGE_INDUSTRIAL_CENTER"
    if "오피스텔(주거)" in text:
        return "OFFICETEL_RESIDENTIAL"
    if "오피스텔" in text:
        return "OFFICETEL_NON_RESIDENTIAL"
    if any(token in text for token in ["다세대", "다가구", "연립", "도시형생활주택"]):
        return "MULTIFAMILY"
    if "아파트" in text:
        return "RESIDENTIAL_APARTMENT"
    if any(token in text for token in ["공장", "제조", "창고"]):
        return "FACTORY"
    if any(token in text for token in ["근린", "상가", "업무시설", "숙박시설", "위락시설"]):
        return "RETAIL"
    if _contains_land_token(text):
        return "LAND"
    return "OTHER"


def _contains_land_token(text: str) -> bool:
    tokens = [part.strip() for part in re.split(r"[\s,./·]+", text) if part.strip()]
    return any(token in {"대", "답", "전", "임야", "도로", "창고용지"} for token in tokens)


def normalize_sigungu(value: str | None) -> str:
    text = re.sub(r"\s+", "", value or "")
    return re.sub(r"(특례시|자치구|시|군|구)$", "", text)


def fetch_groups(conn: sqlite3.Connection, table: str, limit: int) -> list[Group]:
    if table == "properties":
        sql = (
            "select address_sido, address_sigungu, property_type, count(1) "
            "from properties where address_sido is not null and address_sigungu is not null "
            "and property_type is not null group by 1,2,3 order by 4 desc limit ?"
        )
    else:
        sql = (
            "select address_sido, address_sigungu, property_type, count(1) "
            "from comparable_sales where case_index > 0 and address_sido is not null "
            "and address_sigungu is not null and property_type is not null "
            "group by 1,2,3 order by 4 desc limit ?"
        )
    return [Group(*row) for row in conn.execute(sql, (limit,)).fetchall()]


def fetch_appraisal_groups(conn: sqlite3.Connection, limit: int) -> list[Group]:
    rows = conn.execute(
        "with latest as ("
        "select property_id, max(appraisal_date) as max_date from appraisals group by property_id"
        ") "
        "select p.address_sido, p.address_sigungu, p.property_type, count(distinct p.id) "
        "from properties p join latest l on l.property_id = p.id "
        "join appraisals a on a.property_id = p.id and a.appraisal_date = l.max_date "
        "where a.total_value is not null and a.total_value > 0 "
        "and p.address_sido is not null and p.address_sigungu is not null "
        "and p.property_type is not null group by 1,2,3 order by 4 desc limit ?",
        (limit,),
    ).fetchall()
    return [Group(*row) for row in rows]


def build_diagnostics(conn: sqlite3.Connection, groups: list[Group]) -> list[Diagnostic]:
    return [_diagnose_group(conn, group) for group in groups]


def _diagnose_group(conn: sqlite3.Connection, group: Group) -> Diagnostic:
    counts = {
        "sido_count": _scalar(conn, "select count(1) from properties where address_sido = ?", (group.sido,)),
        "sigungu_count": _scalar(
            conn,
            "select count(1) from properties where address_sido = ? and address_sigungu = ?",
            (group.sido, group.sigungu),
        ),
        "property_type_count": _property_type_count(conn, group),
        "appraisal_candidate_count": _appraisal_count(conn, group),
        "transaction_candidate_count": _transaction_count(conn, group),
    }
    return Diagnostic(
        sido=group.sido,
        sigungu=group.sigungu,
        property_type=group.property_type,
        property_type_class=classify_type(group.property_type),
        property_group_count=group.count,
        reason_codes=_reason_codes(counts),
        probe_counts=counts,
    )


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def _property_type_count(conn: sqlite3.Connection, group: Group) -> int:
    return _scalar(
        conn,
        "select count(1) from properties where address_sido = ? and address_sigungu = ? "
        "and property_type like ?",
        (group.sido, group.sigungu, f"%{group.property_type}%"),
    )


def _appraisal_count(conn: sqlite3.Connection, group: Group) -> int:
    return _scalar(
        conn,
        "with latest as ("
        "select property_id, max(appraisal_date) as max_date from appraisals group by property_id"
        ") "
        "select count(distinct p.id) from properties p join appraisals a on a.property_id = p.id "
        "join latest l on l.property_id = p.id and a.appraisal_date = l.max_date "
        "where p.address_sido = ? and p.address_sigungu = ? and p.property_type like ? "
        "and a.total_value is not null and a.total_value > 0",
        (group.sido, group.sigungu, f"%{group.property_type}%"),
    )


def _transaction_count(conn: sqlite3.Connection, group: Group) -> int:
    return _scalar(
        conn,
        "select count(1) from comparable_sales where address_sido = ? and address_sigungu like ? "
        "and property_type like ? and trade_amount is not null and trade_amount > 0 and case_index > 0",
        (group.sido, f"%{group.sigungu}%", f"%{group.property_type}%"),
    )


def _reason_codes(counts: dict[str, int]) -> list[str]:
    if counts["sido_count"] == 0:
        return ["NO_SIDO_MATCH"]
    if counts["sigungu_count"] == 0:
        return ["NO_SIGUNGU_MATCH"]
    if counts["property_type_count"] == 0:
        return ["NO_PROPERTY_TYPE_MATCH"]
    if counts["appraisal_candidate_count"] == 0 and counts["transaction_candidate_count"] == 0:
        return ["NO_SOURCE_BACKED_COMPARABLES"]
    return ["HAS_SOURCE_BACKED_COMPARABLES"]


def build_crosswalks(property_groups: list[Group], comparable_groups: list[Group]) -> list[CrosswalkCandidate]:
    candidates: list[CrosswalkCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    property_counts = _sigungu_counts(property_groups)
    comparable_counts = _sigungu_counts(comparable_groups)
    for (sido, query_sigungu), property_count in property_counts.items():
        for (cand_sido, cand_sigungu), comp_count in comparable_counts.items():
            if sido != cand_sido or query_sigungu == cand_sigungu:
                continue
            if not _is_sigungu_candidate(query_sigungu, cand_sigungu):
                continue
            key = (sido, query_sigungu, cand_sigungu)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(_crosswalk_candidate(len(candidates) + 1, key, property_count, comp_count))
    return candidates


def _sigungu_counts(groups: list[Group]) -> dict[tuple[str, str], int]:
    counts: Counter[tuple[str, str]] = Counter()
    for group in groups:
        counts[(group.sido, group.sigungu)] += group.count
    return dict(counts)


def _is_sigungu_candidate(query: str, candidate: str) -> bool:
    q_norm = normalize_sigungu(query)
    c_norm = normalize_sigungu(candidate)
    return len(q_norm) >= 2 and len(c_norm) >= 2 and (
        c_norm.startswith(q_norm) or q_norm.startswith(c_norm)
    )


def _crosswalk_candidate(
    index: int,
    key: tuple[str, str, str],
    property_count: int,
    comparable_count: int,
) -> CrosswalkCandidate:
    sido, query_sigungu, cand_sigungu = key
    return CrosswalkCandidate(
        rule_id=f"DW-{index:04d}",
        query_sido=sido,
        query_sigungu=query_sigungu,
        candidate_sido=sido,
        candidate_sigungu=cand_sigungu,
        evidence_property_count=property_count,
        evidence_comparable_count=comparable_count,
        match_basis="normalized_sigungu_prefix",
        review_status="NEEDS_REVIEW",
        customer_safe=False,
    )


def build_type_candidates(groups: list[Group]) -> list[TypeCandidate]:
    by_type: Counter[str] = Counter()
    for group in groups:
        by_type[group.property_type] += group.count
    return [_type_candidate(index, raw, count) for index, (raw, count) in enumerate(by_type.items(), 1)]


def _type_candidate(index: int, raw: str, count: int) -> TypeCandidate:
    klass = classify_type(raw)
    flags = []
    if "아파트" in raw and klass != "RESIDENTIAL_APARTMENT":
        flags.append("APARTMENT_SUBSTRING_NOT_RESIDENTIAL")
    if klass == "OTHER":
        flags.append("TYPE_CLASS_OTHER")
    return TypeCandidate(
        rule_id=f"TW-{index:04d}",
        raw_property_type=raw,
        property_type_class=klass,
        source_count=count,
        risk_flags=flags,
        review_status="NEEDS_REVIEW",
        customer_safe=False,
    )


def build_queue(
    diagnostics: list[Diagnostic],
    crosswalks: list[CrosswalkCandidate],
    type_candidates: list[TypeCandidate],
    appraisal_groups: list[Group],
    comparable_groups: list[Group],
) -> list[QueueRow]:
    type_rule_map = {item.raw_property_type: item.rule_id for item in type_candidates}
    crosswalk_map = {(item.query_sido, item.query_sigungu, item.candidate_sigungu): item.rule_id for item in crosswalks}
    source_groups = [("appraisal", group) for group in appraisal_groups] + [("transaction", group) for group in comparable_groups]
    rows: list[QueueRow] = []
    for diagnostic in diagnostics:
        if "NO_SOURCE_BACKED_COMPARABLES" not in diagnostic.reason_codes:
            continue
        rows.extend(_queue_rows_for_diagnostic(diagnostic, source_groups, crosswalk_map, type_rule_map, len(rows)))
    return rows


def _queue_rows_for_diagnostic(
    diagnostic: Diagnostic,
    source_groups: list[tuple[str, Group]],
    crosswalk_map: dict[tuple[str, str, str], str],
    type_rule_map: dict[str, str],
    offset: int,
) -> list[QueueRow]:
    rows: list[QueueRow] = []
    for source, group in source_groups:
        if group.sido != diagnostic.sido or classify_type(group.property_type) != diagnostic.property_type_class:
            continue
        rule_id = crosswalk_map.get((diagnostic.sido, diagnostic.sigungu, group.sigungu))
        if not rule_id:
            continue
        rows.append(_queue_row(offset + len(rows) + 1, diagnostic, source, group, rule_id, type_rule_map))
    return rows[:20]


def _queue_row(
    index: int,
    diagnostic: Diagnostic,
    source: str,
    group: Group,
    district_rule_id: str,
    type_rule_map: dict[str, str],
) -> QueueRow:
    flags = ["DRY_RUN_ONLY", "DISTRICT_CROSSWALK_REVIEW_REQUIRED"]
    if "아파트" in diagnostic.property_type and classify_type(group.property_type) != "RESIDENTIAL_APARTMENT":
        flags.append("APARTMENT_SUBSTRING_BLOCKED")
    return QueueRow(
        queue_id=f"CQ-{index:04d}",
        query_sido=diagnostic.sido,
        query_sigungu=diagnostic.sigungu,
        query_property_type=diagnostic.property_type,
        candidate_source=source,
        candidate_sido=group.sido,
        candidate_sigungu=group.sigungu,
        candidate_property_type=group.property_type,
        district_rule_id=district_rule_id,
        type_rule_id=type_rule_map.get(group.property_type, "TW-UNKNOWN"),
        evidence_count=group.count,
        risk_flags=flags,
        review_status="NEEDS_REVIEW",
        customer_safe=False,
    )


def write_outputs(payload: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
    _write_json(RESULTS_DIR / f"session25_coverage_diagnostic_{DATE_TAG}.json", payload["diagnostic_report"])
    _write_json(CONFIG_DIR / "session25_sigungu_crosswalk_candidates.json", payload["crosswalks"])
    _write_json(CONFIG_DIR / "session25_property_type_taxonomy_candidates.json", payload["type_candidates"])
    _write_json(RESULTS_DIR / f"session25_comparable_candidate_queue_{DATE_TAG}.json", payload["queue"])
    _write_queue_csv(RESULTS_DIR / f"session25_comparable_candidate_queue_{DATE_TAG}.csv", payload["queue"])
    _write_markdown_reports(payload)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_queue_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown_reports(payload: dict[str, Any]) -> None:
    _write_diagnostic_md(payload)
    _write_crosswalk_md(payload["crosswalks"])
    _write_type_md(payload["type_candidates"])


def _write_diagnostic_md(payload: dict[str, Any]) -> None:
    report = payload["diagnostic_report"]
    lines = [
        "# Session 25A Coverage Diagnostic",
        "",
        f"- Overall groups: {report['summary']['diagnosed_groups']}",
        f"- Queue rows: {len(payload['queue'])}",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in report["summary"]["reason_counts"].items())
    lines.append("")
    lines.append("## Top Diagnostics")
    lines.append("")
    lines.append("| Sido | Sigungu | Type | Class | Reason |")
    lines.append("|---|---|---|---|---|")
    for item in report["diagnostics"][:20]:
        lines.append(
            f"| {item['sido']} | {item['sigungu']} | {item['property_type']} | "
            f"{item['property_type_class']} | {','.join(item['reason_codes'])} |"
        )
    (RESULTS_DIR / f"session25_coverage_diagnostic_{DATE_TAG}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_crosswalk_md(rows: list[dict[str, Any]]) -> None:
    lines = ["# Session 25A Sigungu Crosswalk Candidates", "", "| Rule | Query | Candidate | Evidence | Status |", "|---|---|---|---:|---|"]
    for row in rows[:80]:
        lines.append(
            f"| {row['rule_id']} | {row['query_sigungu']} | {row['candidate_sigungu']} | "
            f"{row['evidence_comparable_count']} | {row['review_status']} |"
        )
    (RESULTS_DIR / f"session25_sigungu_crosswalk_report_{DATE_TAG}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_type_md(rows: list[dict[str, Any]]) -> None:
    lines = ["# Session 25A Property Type Taxonomy Candidates", "", "| Rule | Raw Type | Class | Flags |", "|---|---|---|---|"]
    for row in rows[:120]:
        lines.append(
            f"| {row['rule_id']} | {row['raw_property_type']} | {row['property_type_class']} | "
            f"{','.join(row['risk_flags'])} |"
        )
    (RESULTS_DIR / f"session25_property_type_taxonomy_report_{DATE_TAG}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_payload(limit: int) -> dict[str, Any]:
    with sqlite3.connect(DB_PATH) as conn:
        property_groups = fetch_groups(conn, "properties", limit)
        comparable_groups = fetch_groups(conn, "comparable_sales", limit * 3)
        appraisal_groups = fetch_appraisal_groups(conn, limit * 3)
        diagnostics = build_diagnostics(conn, property_groups)
    crosswalks = build_crosswalks(property_groups, comparable_groups + appraisal_groups)
    type_candidates = build_type_candidates(property_groups + comparable_groups + appraisal_groups)
    queue = build_queue(diagnostics, crosswalks, type_candidates, appraisal_groups, comparable_groups)
    return _payload(diagnostics, crosswalks, type_candidates, queue, limit)


def _payload(
    diagnostics: list[Diagnostic],
    crosswalks: list[CrosswalkCandidate],
    type_candidates: list[TypeCandidate],
    queue: list[QueueRow],
    limit: int,
) -> dict[str, Any]:
    reason_counts = Counter(code for item in diagnostics for code in item.reason_codes)
    diagnostic_report = {
        "created_at": datetime.now().isoformat(),
        "db_path": str(DB_PATH),
        "limit": limit,
        "summary": {
            "diagnosed_groups": len(diagnostics),
            "reason_counts": dict(reason_counts),
            "crosswalk_candidates": len(crosswalks),
            "type_candidates": len(type_candidates),
            "queue_rows": len(queue),
            "customer_safe_true": sum(1 for row in queue if row.customer_safe),
        },
        "diagnostics": [asdict(item) for item in diagnostics],
    }
    return {
        "diagnostic_report": diagnostic_report,
        "crosswalks": [asdict(item) for item in crosswalks],
        "type_candidates": [asdict(item) for item in type_candidates],
        "queue": [asdict(item) for item in queue],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()
    payload = build_payload(args.limit)
    write_outputs(payload)
    summary = payload["diagnostic_report"]["summary"]
    print(
        "Session 25A coverage diagnostic complete: "
        f"groups={summary['diagnosed_groups']} queue={summary['queue_rows']} "
        f"customer_safe_true={summary['customer_safe_true']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
