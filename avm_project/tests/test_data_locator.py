"""scripts/data_locator.py 검증.

실제 외장하드는 이 환경에 연결할 수 없으므로, 전부 `tmp_path` 밑에
`loan4u_avm_data`라는 이름의 디렉터리를 만들어 "드라이브"를 흉내낸다.
"""

import importlib
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from data_locator import (
    MARKER_DIRNAME, candidate_roots, is_data_root, resolve_data_root,
)
from exceptions import DataRootNotFoundError


def _make_root(base: Path, *, with_content: bool = True) -> Path:
    data_root = base / MARKER_DIRNAME
    data_root.mkdir(parents=True)
    if with_content:
        (data_root / "placeholder.txt").write_text("x")
    return data_root


class TestResolveDataRootPriority:
    def test_explicit_arg_wins_over_env(self, tmp_path, monkeypatch):
        arg_root = _make_root(tmp_path / "arg")
        env_root = _make_root(tmp_path / "env")
        monkeypatch.setenv("AVM_DATA_ROOT", str(env_root))

        result = resolve_data_root(explicit=str(arg_root))

        assert result.root == arg_root
        assert result.source == "arg"

    def test_env_wins_over_scan(self, tmp_path, monkeypatch):
        env_root = _make_root(tmp_path / "env")
        scan_root = _make_root(tmp_path / "E")
        monkeypatch.setenv("AVM_DATA_ROOT", str(env_root))

        result = resolve_data_root(roots=[scan_root.parent])

        assert result.root == env_root
        assert result.source == "env"

    def test_invalid_env_value_raises_without_falling_back_to_scan(self, tmp_path, monkeypatch):
        not_a_data_root = tmp_path / "typo_dir"
        not_a_data_root.mkdir()
        scan_root = _make_root(tmp_path / "E")
        monkeypatch.setenv("AVM_DATA_ROOT", str(not_a_data_root))

        with pytest.raises(DataRootNotFoundError):
            resolve_data_root(roots=[scan_root.parent])

    def test_invalid_explicit_arg_raises(self, tmp_path):
        not_a_data_root = tmp_path / "typo_dir"
        not_a_data_root.mkdir()

        with pytest.raises(DataRootNotFoundError):
            resolve_data_root(explicit=str(not_a_data_root))


class TestScan:
    def test_scan_finds_single_candidate(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AVM_DATA_ROOT", raising=False)
        drive_e = tmp_path / "E"
        found = _make_root(drive_e)

        result = resolve_data_root(roots=[drive_e])

        assert result.root == found
        assert result.source == "scan"
        assert result.drive == "E"

    def test_multiple_candidates_pick_newest_and_warn(self, tmp_path, monkeypatch, caplog):
        monkeypatch.delenv("AVM_DATA_ROOT", raising=False)
        older = _make_root(tmp_path / "E")
        newer = _make_root(tmp_path / "F")
        os_set_mtime_older = older.stat().st_mtime - 3600
        import os
        os.utime(older, (os_set_mtime_older, os_set_mtime_older))

        with caplog.at_level(logging.WARNING):
            result = resolve_data_root(roots=[older.parent, newer.parent])

        assert result.root == newer
        assert "무시" in caplog.text

    def test_empty_marker_dir_excluded(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AVM_DATA_ROOT", raising=False)
        drive_e = tmp_path / "E"
        _make_root(drive_e, with_content=False)

        with pytest.raises(DataRootNotFoundError):
            resolve_data_root(roots=[drive_e])

    def test_not_found_lists_tried_roots_in_message(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AVM_DATA_ROOT", raising=False)
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(DataRootNotFoundError, match=str(empty)):
            resolve_data_root(roots=[empty])


class TestCandidateRoots:
    def test_explicit_overrides_platform_scan(self):
        assert candidate_roots("/custom/path") == [Path("/custom/path")]

    def test_windows_scans_d_through_z_excluding_c(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")

        roots = candidate_roots()

        letters = {str(r)[0] for r in roots}
        assert "C" not in letters
        assert {"D", "E", "Z"} <= letters

    def test_is_data_root_rejects_wrong_name(self, tmp_path):
        other = tmp_path / "not_the_marker"
        other.mkdir()
        assert is_data_root(other) is False


class TestAvmPathsCompat:
    def test_avm_data_path_env_skips_scan(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AVM_DATA_PATH", str(tmp_path / "explicit_vworld"))
        monkeypatch.delenv("AVM_DATA_ROOT", raising=False)

        import avm_paths
        importlib.reload(avm_paths)

        assert avm_paths.DATA_ROOT == tmp_path / "explicit_vworld"

    def test_no_env_falls_back_to_legacy_default_without_raising(self, monkeypatch):
        monkeypatch.delenv("AVM_DATA_PATH", raising=False)
        monkeypatch.delenv("AVM_DATA_ROOT", raising=False)

        import avm_paths
        importlib.reload(avm_paths)  # must not raise even if no drive is found

        assert avm_paths.DATA_ROOT is not None

    def test_import_never_raises_with_bogus_env(self, monkeypatch):
        monkeypatch.setenv("AVM_DATA_ROOT", "/definitely/not/a/data/root")

        import avm_paths
        importlib.reload(avm_paths)  # falls back to legacy default, no exception
