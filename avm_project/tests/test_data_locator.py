import importlib
from pathlib import Path

import pytest

from scripts import data_locator as locator


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AVM_DATA_ROOT", raising=False)
    monkeypatch.delenv("AVM_DATA_PATH", raising=False)


def test_primary_configuration_has_no_filesystem_side_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locator, "is_data_root", lambda _: pytest.fail("import probed the drive"))
    from scripts import avm_paths
    importlib.reload(avm_paths)
    assert avm_paths.DATA_ROOT == locator.CANONICAL_ROOT / locator.LAYER_DIRNAME


def test_noncanonical_windows_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locator.sys, "platform", "win32")
    monkeypatch.setenv("AVM_DATA_ROOT", "D:/loan4u_avm_data")
    with pytest.raises(locator.DataRootNotFoundError, match="NON_CANONICAL"):
        locator.resolve_data_root()


def test_missing_primary_never_uses_injected_legacy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(locator.sys, "platform", "win32")
    monkeypatch.setattr(locator, "CANONICAL_ROOT", tmp_path / "missing" / "loan4u_avm_data")
    with pytest.raises(locator.DataRootNotFoundError, match="PRIMARY_NOT_MOUNTED"):
        locator.resolve_data_root(roots=[tmp_path])


def test_new_environment_wins_and_legacy_layer_still_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    root = str(locator.CANONICAL_ROOT)
    monkeypatch.setenv("AVM_DATA_ROOT", root)
    monkeypatch.setenv("AVM_DATA_PATH", "D:/wrong")
    assert locator.configured_data_root().source == "AVM_DATA_ROOT"
    monkeypatch.delenv("AVM_DATA_ROOT")
    monkeypatch.setenv("AVM_DATA_PATH", str(locator.CANONICAL_ROOT / locator.LAYER_DIRNAME))
    assert locator.configured_data_root().root == locator.CANONICAL_ROOT


def test_empty_explicit_value_is_not_ignored() -> None:
    with pytest.raises(locator.DataRootNotFoundError, match="INVALID_DATA_ROOT"):
        locator.configured_data_root("")


def test_portable_multiple_roots_require_explicit_selection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(locator.sys, "platform", "linux")
    roots = [tmp_path / letter / locator.MARKER_DIRNAME for letter in ("a", "b")]
    for root in roots:
        root.mkdir(parents=True)
        (root / "marker.txt").write_text("synthetic")
    with pytest.raises(locator.DataRootNotFoundError, match="AMBIGUOUS"):
        locator.resolve_data_root(roots=roots)


def test_invalid_explicit_path_does_not_use_scan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(locator.sys, "platform", "linux")
    with pytest.raises(locator.DataRootNotFoundError):
        locator.resolve_data_root(str(tmp_path / "missing"), roots=[tmp_path])


def test_legacy_custom_layer_is_preserved_without_a_drive_probe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(locator.sys, "platform", "linux")
    custom = tmp_path / "custom-layer"
    monkeypatch.setenv("AVM_DATA_PATH", str(custom))
    monkeypatch.setattr(locator, "is_data_root", lambda _: pytest.fail("legacy path was probed"))
    assert locator.configured_vworld_path() == custom


def test_new_root_overrides_legacy_layer_for_vworld(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVM_DATA_ROOT", str(locator.CANONICAL_ROOT))
    monkeypatch.setenv("AVM_DATA_PATH", "D:/invalid-legacy")
    assert locator.configured_vworld_path() == locator.CANONICAL_ROOT / locator.LAYER_DIRNAME


def test_legacy_layer_cannot_escape_windows_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locator.sys, "platform", "win32")
    monkeypatch.setenv("AVM_DATA_PATH", "D:/old-layer")
    with pytest.raises(locator.DataRootNotFoundError, match="NON_CANONICAL"):
        locator.configured_vworld_path()


def test_legacy_windows_custom_layer_stays_inside_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(locator.sys, "platform", "win32")
    custom = locator.CANONICAL_ROOT / "custom-layer"
    monkeypatch.setenv("AVM_DATA_PATH", str(custom))
    assert locator.configured_vworld_path() == custom
