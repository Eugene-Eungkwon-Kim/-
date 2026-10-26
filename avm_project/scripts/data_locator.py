"""Resolve data paths without substituting a legacy drive for the E: primary."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from .exceptions import DataProcessingError
except ImportError:
    from exceptions import DataProcessingError

MARKER_DIRNAME = "loan4u_avm_data"
ENV_VAR = "AVM_DATA_ROOT"
LEGACY_ENV_VAR = "AVM_DATA_PATH"
CANONICAL_ROOT = Path("E:/DATA_ACTIVE/loan4u_avm_data")
LAYER_DIRNAME = "vworld_wfs_multi_layer"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Resolution:
    root: Path
    source: str
    drive: str | None


class DataRootNotFoundError(DataProcessingError):
    pass


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def configured_data_root(explicit: str | None = None) -> Resolution:
    """Resolve configuration only; imports must not probe or create data folders."""
    value = explicit
    source = "arg" if explicit is not None else "canonical"
    if value is None:
        for env_name in (ENV_VAR, LEGACY_ENV_VAR):
            if env_name in os.environ:
                value, source = os.environ[env_name], env_name
                break
    if value is not None and not value.strip():
        raise DataRootNotFoundError(f"INVALID_DATA_ROOT: {source} is empty")
    root = Path(value).expanduser() if value is not None else CANONICAL_ROOT
    if source == LEGACY_ENV_VAR and root.name == LAYER_DIRNAME:
        root = root.parent
    if sys.platform == "win32" and not _same_path(root, CANONICAL_ROOT):
        raise DataRootNotFoundError("BLOCKED_NON_CANONICAL_DATA_ROOT: Windows requires E: primary")
    return Resolution(root, source, root.drive or None)


def candidate_roots(explicit: str | None = None) -> list[Path]:
    if explicit is not None or sys.platform == "win32":
        return [configured_data_root(explicit).root]
    if ENV_VAR in os.environ or LEGACY_ENV_VAR in os.environ:
        return [configured_data_root().root]
    roots = []
    for base in (Path("/Volumes"), Path("/mnt"), Path("/media")):
        if base.is_dir():
            roots.extend(path / MARKER_DIRNAME for path in base.iterdir() if path.is_dir())
    return roots


def configured_vworld_path() -> Path:
    """The legacy variable names the layer folder, not its parent data root."""
    if ENV_VAR in os.environ or LEGACY_ENV_VAR not in os.environ:
        return configured_data_root().root / LAYER_DIRNAME
    value = os.environ[LEGACY_ENV_VAR]
    if not value.strip():
        raise DataRootNotFoundError("INVALID_DATA_ROOT: AVM_DATA_PATH is empty")
    layer = Path(value).expanduser()
    if sys.platform == "win32":
        canonical = os.path.normcase(os.path.abspath(CANONICAL_ROOT))
        normalized = os.path.normcase(os.path.abspath(layer))
        try:
            inside = os.path.commonpath([canonical, normalized]) == canonical
        except ValueError:
            inside = False
        if not inside:
            raise DataRootNotFoundError("BLOCKED_NON_CANONICAL_DATA_ROOT: Windows requires E: primary")
    return layer


def _has_link_component(path: Path) -> bool:
    for item in (path, *path.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            return True
    return False


def is_data_root(path: Path) -> bool:
    try:
        return (path.name == MARKER_DIRNAME and not _has_link_component(path)
                and path.is_dir() and next(path.iterdir(), None) is not None)
    except OSError:
        return False


def resolve_data_root(explicit: str | None = None,
                      roots: Iterable[Path] | None = None) -> Resolution:
    configured = configured_data_root(explicit)
    pinned = explicit is not None or configured.source != "canonical" or sys.platform == "win32"
    if pinned:
        if not is_data_root(configured.root):
            raise DataRootNotFoundError("BLOCKED_E_PRIMARY_NOT_MOUNTED: configured root unavailable")
        LOGGER.info("Data root selected: %s (%s)", configured.root, configured.source)
        return configured
    candidates = [path for path in (roots if roots is not None else candidate_roots()) if is_data_root(path)]
    if not candidates:
        raise DataRootNotFoundError("DATA_ROOT_NOT_FOUND")
    if len(candidates) != 1:
        raise DataRootNotFoundError("AMBIGUOUS_DATA_ROOT: set AVM_DATA_ROOT explicitly")
    return Resolution(candidates[0], "scan", candidates[0].drive or None)
