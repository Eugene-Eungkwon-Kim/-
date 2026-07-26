"""VWorld Rev.4 multi-layer collector control plane."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCHEMA_VERSION = "2026-07-07.rev4-control-plane.v2"
REV4_LAYER_IDS = (
    "search20",
    "geocoder20",
    "wms_wfs20_reference",
    "continuous_cadastral_map",
    "building_by_use",
    "gis_building_general",
    "gis_building_integrated",
    "land_characteristics",
    "land_use_plan",
    "apart_housing_price",
    "individual_house_price",
    "land_right_register_list",
    "land_price_change_region_wms",
    "land_price_change_usage_wms",
)
DIR_NAMES = ("raw", "ledger", "db", "exports", "tmp")
SECRET_TOKENS = ("key=", "api_key=", "apikey=", "servicekey=", "service_key=")
SAMPLE_ADDRESS = "서울특별시 중구 세종대로 110"
SAMPLE_BBOX = "126.976,37.565,126.979,37.568"
MAX_RESPONSE_BYTES = 200_000
ERROR_STATUSES = {"http_error", "network_error"}


@dataclass(frozen=True)
class LayerSpec:
    layer_id: str
    api_kind: str
    endpoint: str
    typename_or_layer: str = ""
    request_mode: str = "probe"
    mart_table: str = ""
    probe_status: str = "pending"
    notes: str = ""
    required_params: list[str] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def root_paths(root: Path) -> dict[str, Path]:
    return {
        "registry": root / "ledger" / "endpoint_registry.seed.json",
        "probe": root / "ledger" / "endpoint_probe_latest.json",
        "dryrun_probe": root / "ledger" / "endpoint_probe_dryrun.json",
        "qa": root / "ledger" / "qa_summary_latest.json",
        "reference": root / "raw" / "wms_wfs20_reference" / "reference_snapshot.json",
    }


def layer_specs() -> list[LayerSpec]:
    return [
        LayerSpec("search20", "search20", "https://api.vworld.kr/req/search", request_mode="query", mart_table="feature_address_spine", required_params=["service", "request", "query", "type", "key"]),
        LayerSpec("geocoder20", "geocoder20", "https://api.vworld.kr/req/address", request_mode="address", mart_table="feature_geocoder_point", notes="derived coordinates only; no bulk raw payload storage", required_params=["service", "request", "address", "type", "key"]),
        LayerSpec("wms_wfs20_reference", "reference_contract", "https://www.vworld.kr/dev/v4dv_wmsguide2_s001.do", request_mode="snapshot", probe_status="reference_only", required_params=["reference_url"]),
        LayerSpec("continuous_cadastral_map", "generic_wfs", "https://api.vworld.kr/req/wfs", "lp_pa_cbnd_bonbun,lp_pa_cbnd_bubun", "bbox_tile", "mart_cadastral_parcel_feature", required_params=["service", "request", "typename", "bbox", "key"]),
        LayerSpec("building_by_use", "ned_wfs_candidate", "probe_required", request_mode="pnu_or_bbox", mart_table="mart_building_use_feature", notes="fallback to lt_c_bldginfo usage columns"),
        LayerSpec("gis_building_general", "ned_wfs_candidate", "probe_required", "lt_c_bldginfo", "bbox_tile", "mart_gis_building_general_feature", notes="generic WFS fallback available"),
        LayerSpec("gis_building_integrated", "ned_wfs_candidate", "probe_required", request_mode="bbox_or_building_id", mart_table="mart_gis_building_integrated_feature"),
        LayerSpec("land_characteristics", "ned_wfs_candidate", "probe_required", request_mode="pnu_or_bbox", mart_table="mart_land_characteristics_feature", notes="fallback generic soil/land layers"),
        LayerSpec("land_use_plan", "generic_wfs", "https://api.vworld.kr/req/wfs", "lt_c_lhblpn", "bbox_tile", "mart_land_use_plan_feature", required_params=["service", "request", "typename", "bbox", "key"]),
        LayerSpec("apart_housing_price", "ned_wfs", "https://api.vworld.kr/ned/wfs/getApartHousingPriceWFS", "dt_d166", "pnu_or_bbox", "mart_apart_housing_price_feature", required_params=["typename", "bbox", "key"]),
        LayerSpec("individual_house_price", "ned_wfs_candidate", "https://api.vworld.kr/ned/wfs/getIndvdHousingPriceWFS", "dt_d165", "pnu_or_bbox", "mart_individual_house_price_feature", notes="candidate until runtime probe confirms contract"),
        LayerSpec("land_right_register_list", "ned_list_candidate", "probe_required", request_mode="pnu_or_unit", mart_table="mart_land_right_register_feature"),
        LayerSpec("land_price_change_region_wms", "wms_candidate", "https://api.vworld.kr/req/wms", request_mode="wms_tile", mart_table="mart_land_price_change_region", notes="image_only unless GetFeatureInfo succeeds"),
        LayerSpec("land_price_change_usage_wms", "wms_candidate", "https://api.vworld.kr/req/wms", request_mode="wms_tile", mart_table="mart_land_price_change_usage", notes="usage dimension added; image_only unless GetFeatureInfo succeeds"),
    ]


def registry_payload(profile: str) -> dict[str, Any]:
    specs = [asdict(item) for item in layer_specs()]
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "generated_at": utc_now(),
        "layer_count": len(specs),
        "secret_persisted": False,
        "layers": specs,
    }


def ensure_root_layout(root: Path) -> None:
    for name in DIR_NAMES:
        (root / name).mkdir(parents=True, exist_ok=True)
    for layer_id in REV4_LAYER_IDS:
        (root / "raw" / layer_id).mkdir(parents=True, exist_ok=True)


def write_reference_snapshot(root: Path, profile: str) -> dict[str, Any]:
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "created_at": utc_now(),
        "reference_urls": reference_urls(),
        "capture_mode": "static_reference_contract_seed",
    }
    snapshot["snapshot_hash"] = sha256_text(json.dumps(snapshot, sort_keys=True))
    write_json(root_paths(root)["reference"], snapshot)
    return snapshot


def reference_urls() -> list[str]:
    return [
        "https://www.vworld.kr/dev/v4dv_search2_s001.do",
        "https://www.vworld.kr/dev/v4dv_geocoderguide2_s001.do",
        "https://www.vworld.kr/dev/v4dv_wmsguide2_s001.do",
        "https://www.vworld.kr/dev/v4dv_2ddataguide2_s001.do",
    ]


def command_init_registry(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ensure_root_layout(root)
    payload = registry_payload(args.profile)
    reference = write_reference_snapshot(root, args.profile)
    if args.write:
        write_json(root_paths(root)["registry"], payload)
    print(json.dumps(_init_result(root, payload, reference, args.write), ensure_ascii=False, indent=2))
    return 0


def _init_result(root: Path, payload: dict[str, Any], reference: dict[str, Any], wrote: bool) -> dict[str, Any]:
    return {
        "status": "INIT_REGISTRY_WRITTEN" if wrote else "INIT_REGISTRY_DRY_RUN",
        "root": str(root),
        "layer_count": payload["layer_count"],
        "registry": str(root_paths(root)["registry"]),
        "reference_hash": reference["snapshot_hash"],
        "secret_persisted": False,
    }


def load_registry(root: Path) -> dict[str, Any]:
    path = root_paths(root)["registry"]
    if not path.exists():
        raise FileNotFoundError(f"Registry not found: {path}")
    return load_json(path)


def dry_run_probe_status(layer: dict[str, Any]) -> str:
    if layer["api_kind"] == "reference_contract":
        return "reference_only"
    if layer["endpoint"] == "probe_required":
        return "blocked_endpoint_contract"
    if "candidate" in layer["api_kind"]:
        return "blocked_runtime_key"
    return "ready_for_runtime_probe"


def command_probe_endpoints(args: argparse.Namespace) -> int:
    root = Path(args.root)
    registry = load_registry(root)
    payload = build_probe_payload(root, registry, args)
    if args.write:
        write_json(probe_output_path(root, args.dry_run), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["summary"]["terminal_errors"] == 0 else 1


def build_probe_payload(root: Path, registry: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if args.dry_run:
        rows = [_probe_row(layer, True) for layer in registry["layers"]]
        return _probe_payload(root, rows, "dry_run")
    runtime_key = read_runtime_key(args)
    if not runtime_key:
        return waiting_runtime_key_payload(root, registry)
    rows = live_probe_rows(registry["layers"], runtime_key, args)
    return _probe_payload(root, rows, "live_probe")


def probe_output_path(root: Path, dry_run: bool) -> Path:
    paths = root_paths(root)
    return paths["dryrun_probe"] if dry_run else paths["probe"]


def read_runtime_key(args: argparse.Namespace) -> str:
    if args.key_prompt:
        return getpass.getpass("VWorld API key: ").strip()
    if args.key_stdin:
        return sys.stdin.readline().strip()
    return ""


def waiting_runtime_key_payload(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    rows = [_waiting_key_row(layer) for layer in registry["layers"]]
    return _probe_payload(root, rows, "WAITING_RUNTIME_KEY")


def _waiting_key_row(layer: dict[str, Any]) -> dict[str, Any]:
    row = _probe_row(layer, True)
    if row["probe_status"] == "ready_for_runtime_probe":
        row["probe_status"] = "waiting_runtime_key"
    return row


def _probe_row(layer: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    status = dry_run_probe_status(layer) if dry_run else "live_probe_not_implemented"
    return {
        "layer_id": layer["layer_id"],
        "api_kind": layer["api_kind"],
        "endpoint": layer["endpoint"],
        "probe_status": status,
        "feature_count": 0,
        "secret_persisted": False,
    }


def _probe_payload(root: Path, rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    counts = _count_by(rows, "probe_status")
    terminal_errors = sum(1 for row in rows if row["probe_status"] in ERROR_STATUSES)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "root": str(root),
        "mode": mode,
        "summary": {"layer_count": len(rows), "terminal_errors": terminal_errors, "status_counts": counts},
        "probes": rows,
    }


def live_probe_rows(layers: list[dict[str, Any]], runtime_key: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    selected = selected_layer_ids(args.layers)
    rows: list[dict[str, Any]] = []
    for layer in layers:
        rows.append(_live_or_skipped_row(layer, selected, runtime_key, args.timeout))
    return rows


def selected_layer_ids(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()} if value else set()


def _live_or_skipped_row(
    layer: dict[str, Any],
    selected: set[str],
    runtime_key: str,
    timeout: float,
) -> dict[str, Any]:
    if selected and layer["layer_id"] not in selected:
        return _skipped_row(layer)
    return live_probe_row(layer, runtime_key, timeout)


def _skipped_row(layer: dict[str, Any]) -> dict[str, Any]:
    row = _probe_row(layer, True)
    row["probe_status"] = "skipped_by_layer_filter"
    return row


def live_probe_row(layer: dict[str, Any], runtime_key: str, timeout: float) -> dict[str, Any]:
    request_spec = build_live_request(layer, runtime_key)
    if not request_spec["callable"]:
        return non_callable_live_row(layer, request_spec["reason"])
    return execute_live_probe(layer, request_spec, timeout)


def non_callable_live_row(layer: dict[str, Any], reason: str) -> dict[str, Any]:
    row = _probe_row(layer, True)
    row["probe_status"] = reason
    row["live_callable"] = False
    return row


def build_live_request(layer: dict[str, Any], runtime_key: str) -> dict[str, Any]:
    if layer["api_kind"] == "reference_contract":
        return {"callable": False, "reason": "reference_only"}
    if layer["endpoint"] == "probe_required":
        return {"callable": False, "reason": "blocked_endpoint_contract"}
    params = sample_params(layer, runtime_key)
    if not params:
        return {"callable": False, "reason": "blocked_endpoint_contract"}
    return {"callable": True, "url": layer["endpoint"], "params": params}


def sample_params(layer: dict[str, Any], runtime_key: str) -> dict[str, str]:
    api_kind = layer["api_kind"]
    if api_kind == "search20":
        return search_params(runtime_key)
    if api_kind == "geocoder20":
        return geocoder_params(runtime_key)
    if api_kind in {"generic_wfs", "ned_wfs"} or layer["layer_id"] == "individual_house_price":
        return wfs_params(layer, runtime_key)
    return {}


def search_params(runtime_key: str) -> dict[str, str]:
    return {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "format": "json",
        "errorFormat": "json",
        "size": "1",
        "page": "1",
        "query": SAMPLE_ADDRESS,
        "type": "ADDRESS",
        "category": "PARCEL",
        "key": runtime_key,
    }


def geocoder_params(runtime_key: str) -> dict[str, str]:
    return {
        "service": "address",
        "request": "getCoord",
        "version": "2.0",
        "crs": "EPSG:4326",
        "address": SAMPLE_ADDRESS,
        "refine": "true",
        "simple": "false",
        "format": "json",
        "errorFormat": "json",
        "type": "ROAD",
        "key": runtime_key,
    }


def wfs_params(layer: dict[str, Any], runtime_key: str) -> dict[str, str]:
    typename = first_typename(layer.get("typename_or_layer", ""))
    if not typename:
        return {}
    return {
        "service": "WFS",
        "request": "GetFeature",
        "version": "2.0.0",
        "typename": typename,
        "bbox": SAMPLE_BBOX,
        "maxfeatures": "1",
        "srsname": "EPSG:4326",
        "output": "json",
        "key": runtime_key,
    }


def first_typename(value: str) -> str:
    return value.split(",")[0].strip() if value else ""


def execute_live_probe(layer: dict[str, Any], request_spec: dict[str, Any], timeout: float) -> dict[str, Any]:
    started = utc_now()
    try:
        return _execute_live_probe(layer, request_spec, timeout, started)
    except HTTPError as exc:
        return error_probe_row(layer, "http_error", started, exc.code, str(exc))
    except (URLError, TimeoutError, OSError) as exc:
        return error_probe_row(layer, "network_error", started, None, str(exc))


def _execute_live_probe(layer: dict[str, Any], request_spec: dict[str, Any], timeout: float, started: str) -> dict[str, Any]:
    url = f"{request_spec['url']}?{urlencode(request_spec['params'])}"
    with urlopen(Request(url, headers={"Accept": "*/*"}), timeout=timeout) as response:
        body = response.read(MAX_RESPONSE_BYTES)
        status = response.status
    return success_probe_row(layer, request_spec, started, status, body)


def success_probe_row(
    layer: dict[str, Any],
    request_spec: dict[str, Any],
    started: str,
    http_status: int,
    body: bytes,
) -> dict[str, Any]:
    text = body[:4096].decode("utf-8", errors="replace")
    return {
        "layer_id": layer["layer_id"],
        "api_kind": layer["api_kind"],
        "probe_status": classify_response(http_status, text, len(body)),
        "http_status": http_status,
        "started_at": started,
        "finished_at": utc_now(),
        "byte_length": len(body),
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "request": safe_request_metadata(request_spec),
        "secret_persisted": False,
    }


def classify_response(http_status: int, text: str, byte_length: int) -> str:
    lowered = text.lower()
    if http_status >= 400:
        return "http_error"
    if byte_length == 0:
        return "empty_response"
    if "incorrect_key" in lowered or "invalid_key" in lowered:
        return "invalid_key"
    if "exception" in lowered or "error" in lowered:
        return "api_error_response"
    if "total\" : 0" in lowered or "total\":0" in lowered:
        return "no_features"
    return "ok"


def safe_request_metadata(request_spec: dict[str, Any]) -> dict[str, Any]:
    params = {key: value for key, value in request_spec["params"].items() if key.lower() != "key"}
    return {"endpoint": request_spec["url"], "params_without_secret": params, "credential_redacted": True}


def error_probe_row(
    layer: dict[str, Any],
    status: str,
    started: str,
    http_status: int | None,
    message: str,
) -> dict[str, Any]:
    return {
        "layer_id": layer["layer_id"],
        "api_kind": layer["api_kind"],
        "probe_status": status,
        "http_status": http_status,
        "started_at": started,
        "finished_at": utc_now(),
        "error_text_redacted": message[:300],
        "secret_persisted": False,
    }


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row[key])
        counts[value] = counts.get(value, 0) + 1
    return counts


def command_qa(args: argparse.Namespace) -> int:
    root = Path(args.root)
    registry = load_registry(root)
    probe = load_probe_summary(root)
    payload = qa_payload(root, registry, probe)
    if args.write:
        write_json(root_paths(root)["qa"], payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["overall"] == "PASS" else 1


def qa_payload(root: Path, registry: dict[str, Any], probe: dict[str, Any] | None) -> dict[str, Any]:
    checks = [
        _check_layer_count(registry),
        _check_unique_layers(registry),
        _check_secret_free(root),
        _check_probe_exists(probe),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "root": str(root),
        "overall": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "checks": checks,
    }


def _check_layer_count(registry: dict[str, Any]) -> dict[str, Any]:
    count = int(registry.get("layer_count", 0))
    return {"name": "layer_count_14", "status": "PASS" if count == 14 else "FAIL", "value": count}


def _check_unique_layers(registry: dict[str, Any]) -> dict[str, Any]:
    ids = [item["layer_id"] for item in registry.get("layers", [])]
    return {"name": "unique_layer_ids", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL", "value": len(set(ids))}


def _check_secret_free(root: Path) -> dict[str, Any]:
    paths = root_paths(root)
    files = [paths["registry"], paths["probe"], paths["dryrun_probe"], paths["reference"]]
    matches = [str(path) for path in files if path.exists() and _has_secret_token(path.read_text(encoding="utf-8"))]
    return {"name": "secret_literal_scan", "status": "PASS" if not matches else "FAIL", "matches": matches}


def _has_secret_token(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in SECRET_TOKENS)


def _check_probe_exists(probe: dict[str, Any] | None) -> dict[str, Any]:
    status = "PASS" if probe and probe.get("summary", {}).get("layer_count") == 14 else "FAIL"
    return {"name": "probe_summary_exists", "status": status}


def load_probe_summary(root: Path) -> dict[str, Any] | None:
    paths = root_paths(root)
    for key in ("probe", "dryrun_probe"):
        if paths[key].exists():
            return load_json(paths[key])
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VWorld Rev.4 multi-layer collector control plane")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_init_parser(subparsers)
    _add_probe_parser(subparsers)
    _add_qa_parser(subparsers)
    return parser


def _add_init_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("init-registry")
    parser.add_argument("--root", required=True)
    parser.add_argument("--profile", default="rev4")
    parser.add_argument("--write", action="store_true")
    parser.set_defaults(func=command_init_registry)


def _add_probe_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("probe-endpoints")
    parser.add_argument("--root", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--key-prompt", action="store_true")
    parser.add_argument("--key-stdin", action="store_true")
    parser.add_argument("--layers", default="")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.set_defaults(func=command_probe_endpoints)


def _add_qa_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("qa")
    parser.add_argument("--root", required=True)
    parser.add_argument("--write", action="store_true")
    parser.set_defaults(func=command_qa)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
