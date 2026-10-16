import os
from pathlib import Path

from drive_audit import find_duplicates as fd


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _scan(*roots: Path, include_system: bool = False) -> fd.ScanResult:
    args = fd.parse_args([str(r) for r in roots] + (["--include-system"] if include_system else []))
    result = fd.ScanResult()
    for root in fd.normalize_roots(args.roots):
        fd.scan_root(root, fd.build_options(args), result)
    return result


def test_normalize_roots_drops_missing_and_nested(tmp_path: Path) -> None:
    (tmp_path / "a" / "b").mkdir(parents=True)
    roots = fd.normalize_roots([str(tmp_path / "a" / "b"), str(tmp_path / "a"), str(tmp_path / "nope")])
    assert roots == [str(tmp_path / "a")]


def test_identical_content_across_drives_is_grouped(tmp_path: Path) -> None:
    payload = os.urandom(200_000)
    _write(tmp_path / "C" / "photos" / "x.jpg", payload)
    _write(tmp_path / "E" / "backup" / "x (1).jpg", payload)
    _write(tmp_path / "E" / "empty.txt", b"")
    result = _scan(tmp_path / "C", tmp_path / "E")
    groups = fd.find_duplicates(result.entries, result)
    assert len(groups) == 1
    assert groups[0].wasted == 200_000
    assert {Path(f.root).name for f in groups[0].files} == {"C", "E"}


def test_same_size_and_prefix_but_different_tail_is_not_duplicate(tmp_path: Path) -> None:
    prefix = os.urandom(fd.PARTIAL_BYTES)
    _write(tmp_path / "C" / "a.bin", prefix + os.urandom(1000))
    _write(tmp_path / "C" / "b.bin", prefix + os.urandom(1000))
    result = _scan(tmp_path / "C")
    assert fd.find_duplicates(result.entries, result) == []


def test_system_and_cache_folders_are_skipped_only_where_expected(tmp_path: Path) -> None:
    drive = tmp_path / "C"
    _write(drive / "Windows" / "sys.dll", b"x")
    _write(drive / "Users" / "me" / "AppData" / "cache.bin", b"x")
    _write(drive / "proj" / "windows" / "build.txt", b"x")
    names = {Path(e.path).name for e in _scan(drive).entries}
    assert names == {"build.txt"}
    assert len(_scan(drive, include_system=True).entries) == 3


def test_copy_roots_stops_below_scan_root(tmp_path: Path) -> None:
    d = fd.FileEntry(str(tmp_path / "D" / "avm_project" / "data" / "a.csv"), 1, 0, str(tmp_path / "D"))
    e = fd.FileEntry(str(tmp_path / "E" / "avm_project" / "data" / "a.csv"), 1, 0, str(tmp_path / "E"))
    c = fd.FileEntry(str(tmp_path / "C" / "Users" / "AVM" / "data" / "a.csv"), 1, 0, str(tmp_path / "C"))
    assert fd.copy_roots(d, e) == (str(tmp_path / "D" / "avm_project"), str(tmp_path / "E" / "avm_project"))
    assert fd.copy_roots(c, e) == (str(tmp_path / "C" / "Users" / "AVM"), str(tmp_path / "E" / "avm_project"))


def test_main_writes_reports_and_exit_codes(tmp_path: Path) -> None:
    payload = os.urandom(5000)
    _write(tmp_path / "C" / "AVM" / "README.md", payload)
    _write(tmp_path / "E" / "avm_project" / "README.md", payload)
    out = tmp_path / "out"
    assert fd.main([str(tmp_path / "C"), str(tmp_path / "E"), "--out", str(out)]) == 0
    assert {p.name for p in out.iterdir()} == {
        "report.md", "duplicates.csv", "copied_folders.csv", "git_repos.csv", "summary.json"}
    assert "avm_project" in (out / "copied_folders.csv").read_text(encoding="utf-8-sig")
    assert fd.main([str(tmp_path / "missing")]) == 1
