#!/usr/bin/env python3
"""여러 드라이브(C:, D:, E: 등)에 걸친 중복 파일 · 통째로 복사된 폴더 · git 저장소 사본 조사.

읽기 전용 — 어떤 파일도 삭제하거나 수정하지 않는다.

사용 예 (Windows PowerShell):
  python drive_audit\\find_duplicates.py C:\\ D:\\ E:\\
  python drive_audit\\find_duplicates.py C:\\Users\\eungk E:\\ --out C:\\drive_report
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path

PARTIAL_BYTES = 64 * 1024
CHUNK_BYTES = 1024 * 1024
PROGRESS_EVERY = 50_000
MAX_GROUP_FOR_TREES = 20
# 클라우드 전용(OneDrive 등) 파일은 읽는 순간 다운로드되므로 해시하지 않는다.
CLOUD_ONLY_ATTRS = 0x1000 | 0x40000 | 0x400000
LINK_REPARSE_TAGS = {0xA0000003, 0xA000000C}
TOP_LEVEL_EXCLUDES = {
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "recovery", "perflogs",
    "msocache", "$winreagent", "$windows.~bt", "$windows.~ws",
}
ANYWHERE_EXCLUDES = {
    "appdata", "node_modules", "__pycache__", ".venv", "venv", ".git",
    ".pytest_cache", ".mypy_cache",
}


@dataclass(frozen=True)
class FileEntry:
    path: str
    size: int
    mtime: float
    root: str


@dataclass
class DupGroup:
    digest: str
    size: int
    files: list[FileEntry]

    @property
    def wasted(self) -> int:
        return self.size * (len(self.files) - 1)


@dataclass
class TreePair:
    a: str
    b: str
    files: int = 0
    bytes: int = 0
    total_a: int = 0
    total_b: int = 0


@dataclass
class ScanResult:
    entries: list[FileEntry] = field(default_factory=list)
    dir_files: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    repos: list[str] = field(default_factory=list)
    errors: int = 0
    skipped_dirs: int = 0
    cloud_only: int = 0


@dataclass(frozen=True)
class ScanOptions:
    min_size: int
    top_excludes: frozenset[str]
    any_excludes: frozenset[str]


# ── 경로 유틸 ───────────────────────────────────────────────────────────────

def _key(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _is_under(path: str, root: str) -> bool:
    p, r = _key(path), _key(root).rstrip("\\/")
    return p == r or p.startswith(r + os.sep)


def normalize_roots(raw: list[str]) -> list[str]:
    roots: list[str] = []
    for item in raw:
        if len(item) == 2 and item[1] == ":":
            item += "\\"
        path = os.path.abspath(item)
        if not os.path.isdir(path):
            print(f"[경고] 폴더를 찾을 수 없어 건너뜀: {item}", file=sys.stderr)
            continue
        roots.append(path)
    roots.sort(key=lambda r: len(_key(r)))
    kept: list[str] = []
    for root in roots:
        if not any(_is_under(root, k) for k in kept):
            kept.append(root)
    return kept


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


# ── 1단계: 스캔 ─────────────────────────────────────────────────────────────

def _is_link(entry: os.DirEntry) -> bool:
    if entry.is_symlink():
        return True
    is_junction = getattr(entry, "is_junction", None)
    if is_junction is not None:
        return is_junction()
    # Python 3.11 이하: 'Documents and Settings' 같은 정션을 따라가면 같은 폴더를 두 번 세게 된다.
    return getattr(entry.stat(follow_symlinks=False), "st_reparse_tag", 0) in LINK_REPARSE_TAGS


def _record_file(entry: os.DirEntry, root: str, opts: ScanOptions, result: ScanResult) -> None:
    st = entry.stat(follow_symlinks=False)
    if st.st_size < opts.min_size:
        return
    if getattr(st, "st_file_attributes", 0) & CLOUD_ONLY_ATTRS:
        result.cloud_only += 1
        return
    result.entries.append(FileEntry(entry.path, st.st_size, st.st_mtime, root))
    result.dir_files[_key(os.path.dirname(entry.path))] += 1
    if len(result.entries) % PROGRESS_EVERY == 0:
        print(f"  … {len(result.entries):,}개 파일 수집", file=sys.stderr)


def _is_excluded(entry: os.DirEntry, parent: str, root: str, opts: ScanOptions) -> bool:
    name = entry.name.lower()
    if name in opts.any_excludes:
        return True
    return _key(parent) == _key(root) and name in opts.top_excludes


def _visit(entry: os.DirEntry, parent: str, root: str, opts: ScanOptions,
           result: ScanResult, stack: list[str]) -> None:
    if entry.name.lower() == ".git":
        result.repos.append(parent)
    if _is_link(entry):
        return
    if entry.is_dir(follow_symlinks=False):
        if _is_excluded(entry, parent, root, opts):
            result.skipped_dirs += 1
        else:
            stack.append(entry.path)
    elif entry.is_file(follow_symlinks=False):
        _record_file(entry, root, opts, result)


def scan_root(root: str, opts: ScanOptions, result: ScanResult) -> None:
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                children = list(it)
        except OSError:
            result.errors += 1
            continue
        for entry in children:
            try:
                _visit(entry, current, root, opts, result, stack)
            except OSError:
                result.errors += 1


# ── 2단계: 중복 판정 (크기 → 앞부분 해시 → 전체 해시) ─────────────────────

def hash_file(path: str, limit: int | None = None) -> str | None:
    digest = hashlib.blake2b(digest_size=20)
    remaining = limit
    try:
        with open(path, "rb") as fh:
            while remaining is None or remaining > 0:
                want = CHUNK_BYTES if remaining is None else min(CHUNK_BYTES, remaining)
                chunk = fh.read(want)
                if not chunk:
                    break
                digest.update(chunk)
                if remaining is not None:
                    remaining -= len(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _regroup(groups: list[list[FileEntry]], limit: int | None, label: str,
             result: ScanResult) -> list[tuple[str, list[FileEntry]]]:
    total = sum(len(g) for g in groups)
    done, out = 0, []
    for group in groups:
        by_hash: dict[str, list[FileEntry]] = defaultdict(list)
        for entry in group:
            digest = hash_file(entry.path, limit)
            if digest is None:
                result.errors += 1
            else:
                by_hash[digest].append(entry)
        out.extend((d, files) for d, files in by_hash.items() if len(files) > 1)
        done += len(group)
        if done // PROGRESS_EVERY != (done - len(group)) // PROGRESS_EVERY:
            print(f"  … {label} {done:,}/{total:,}", file=sys.stderr)
    return out


def find_duplicates(entries: list[FileEntry], result: ScanResult) -> list[DupGroup]:
    by_size: dict[int, list[FileEntry]] = defaultdict(list)
    for entry in entries:
        by_size[entry.size].append(entry)
    candidates = [g for g in by_size.values() if len(g) > 1]
    small = [g for g in candidates if g[0].size <= PARTIAL_BYTES]
    large = [g for g in candidates if g[0].size > PARTIAL_BYTES]
    print(f"\n중복 후보: {sum(len(g) for g in candidates):,}개 파일 (같은 크기)", file=sys.stderr)
    partial = [files for _, files in _regroup(large, PARTIAL_BYTES, "앞부분 해시", result)]
    final = _regroup(small + partial, None, "전체 해시", result)
    groups = [DupGroup(d, files[0].size, files) for d, files in final]
    return sorted(groups, key=lambda g: g.wasted, reverse=True)


# ── 3단계: 통째로 복사된 폴더 찾기 ─────────────────────────────────────────

def copy_roots(fa: FileEntry, fb: FileEntry) -> tuple[str, str]:
    """두 동일 파일의 경로에서 공통 꼬리(하위 경로)를 떼어 복사본의 최상위 폴더 쌍을 구한다."""
    pa, pb = Path(fa.path).parts, Path(fb.path).parts
    # 검색 루트 바로 아래 폴더까지만 거슬러 올라간다 — D:\avm_project ↔ E:\avm_project 가 D:\ ↔ E:\ 로 뭉개지지 않게.
    floor_a, floor_b = len(Path(fa.root).parts) + 1, len(Path(fb.root).parts) + 1
    n = 0
    while (len(pa) - n - 1 >= floor_a and len(pb) - n - 1 >= floor_b
           and _key(pa[-1 - n]) == _key(pb[-1 - n])):
        n += 1
    depth = max(n, 1) - 1
    return str(Path(fa.path).parents[depth]), str(Path(fb.path).parents[depth])


def _subtree_files(root: str, dir_files: dict[str, int]) -> int:
    base = _key(root).rstrip("\\/")
    prefix = base + os.sep
    return sum(n for d, n in dir_files.items() if d == base or d.startswith(prefix))


def find_copied_trees(groups: list[DupGroup], result: ScanResult, top: int) -> list[TreePair]:
    pairs: dict[tuple[str, str], TreePair] = {}
    for group in groups:
        if len(group.files) > MAX_GROUP_FOR_TREES:
            continue
        for fa, fb in combinations(group.files, 2):
            ra, rb = copy_roots(fa, fb)
            if _key(ra) > _key(rb):
                ra, rb = rb, ra
            pair = pairs.setdefault((_key(ra), _key(rb)), TreePair(ra, rb))
            pair.files += 1
            pair.bytes += group.size
    ranked = sorted(pairs.values(), key=lambda p: p.bytes, reverse=True)[:top]
    for pair in ranked:
        pair.total_a = _subtree_files(pair.a, result.dir_files)
        pair.total_b = _subtree_files(pair.b, result.dir_files)
    return ranked


# ── 4단계: git 저장소 사본 비교 ────────────────────────────────────────────

def _git(repo: str, *args: str) -> str | None:
    # 외장하드는 소유자가 달라 git이 'dubious ownership'으로 거부하므로 safe.directory를 연다.
    cmd = ["git", "-c", "safe.directory=*", "-C", repo, *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                              encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def repo_info(repo: str) -> dict[str, str]:
    log = (_git(repo, "log", "-1", "--format=%h|%ci|%s") or "").split("|", 2)
    head, date, subject = (log + ["", "", ""])[:3]
    first_commits = (_git(repo, "rev-list", "--max-parents=0", "HEAD") or "").splitlines()
    status = _git(repo, "status", "--porcelain")
    return {
        "path": repo,
        "remote": _git(repo, "remote", "get-url", "origin") or "",
        "project_id": first_commits[0][:12] if first_commits else "",
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "?",
        "head": head,
        "date": date,
        "subject": subject,
        "uncommitted": "?" if status is None else str(len(status.splitlines())),
    }


def group_repos(repos: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    by_project: dict[str, list[dict[str, str]]] = defaultdict(list)
    for info in repos:
        by_project[info["project_id"] or info["remote"] or info["path"]].append(info)
    groups = [sorted(g, key=lambda r: r["date"], reverse=True) for g in by_project.values()]
    return sorted(groups, key=len, reverse=True)


# ── 5단계: 결과 저장 ───────────────────────────────────────────────────────

def drive_combos(groups: list[DupGroup]) -> dict[str, list[int]]:
    combos: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for group in groups:
        roots = sorted({f.root for f in group.files})
        label = " ↔ ".join(roots) if len(roots) > 1 else f"{roots[0]} 내부"
        combos[label][0] += len(group.files) - 1
        combos[label][1] += group.wasted
    return dict(sorted(combos.items(), key=lambda kv: kv[1][1], reverse=True))


def write_duplicates_csv(path: Path, groups: list[DupGroup]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["그룹", "크기(bytes)", "그룹_낭비용량(bytes)", "검색루트", "경로", "수정일시", "해시"])
        for i, group in enumerate(groups, 1):
            for f in sorted(group.files, key=lambda e: e.mtime):
                mtime = datetime.fromtimestamp(f.mtime).isoformat(timespec="seconds")
                writer.writerow([i, group.size, group.wasted, f.root, f.path, mtime, group.digest])


def write_trees_csv(path: Path, trees: list[TreePair]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["폴더A", "폴더B", "공유파일수", "공유용량(bytes)", "A_전체파일수", "B_전체파일수"])
        for t in trees:
            writer.writerow([t.a, t.b, t.files, t.bytes, t.total_a, t.total_b])


def write_repos_csv(path: Path, repo_groups: list[list[dict[str, str]]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        fields = ["group", "path", "remote", "project_id", "branch", "head", "date", "subject", "uncommitted"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for i, group in enumerate(repo_groups, 1):
            for info in group:
                writer.writerow({"group": i, **info})


# ── 보고서 (report.md) ─────────────────────────────────────────────────────

def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _coverage(shared: int, total: int) -> str:
    return f"{min(shared / total, 1):.0%}" if total else "-"


def _summary_lines(roots: list[str], result: ScanResult, groups: list[DupGroup]) -> list[str]:
    return [
        "# 드라이브 중복 파일 조사 보고서", "",
        f"- 실행일시: {datetime.now():%Y-%m-%d %H:%M}",
        f"- 검색 위치: {', '.join(roots)}",
        "- 읽기 전용 조사입니다. 어떤 파일도 삭제·이동하지 않았습니다.", "",
        "## 1. 요약", "",
        "| 항목 | 값 |", "|---|---|",
        f"| 검사한 파일 | {len(result.entries):,}개 |",
        f"| 중복 그룹 (같은 내용 파일 묶음) | {len(groups):,}개 |",
        f"| 정리 가능한 사본 | {sum(len(g.files) - 1 for g in groups):,}개 |",
        f"| 회수 가능 용량 | {human(sum(g.wasted for g in groups))} |",
        f"| 발견한 git 저장소 | {len(result.repos)}개 |",
        f"| 제외한 시스템·캐시 폴더 | {result.skipped_dirs:,}개 |",
        f"| 클라우드 전용 파일 (검사 안 함) | {result.cloud_only:,}개 |",
        f"| 읽기 오류 (권한 등) | {result.errors:,}건 |", "",
    ]


def _combo_lines(groups: list[DupGroup]) -> list[str]:
    lines = ["## 2. 위치 조합별 중복", "", "| 위치 | 정리 가능한 사본 | 용량 |", "|---|---:|---:|"]
    for label, (count, size) in drive_combos(groups).items():
        lines.append(f"| {_cell(label)} | {count:,}개 | {human(size)} |")
    return lines + [""]


def _tree_lines(trees: list[TreePair]) -> list[str]:
    lines = [
        "## 3. 통째로 복사된 것으로 보이는 폴더", "",
        "같은 하위 경로에 같은 내용의 파일이 있는 폴더 쌍입니다. "
        "겹침 비율이 100%에 가까운 쪽이 다른 쪽의 사본일 가능성이 큽니다.", "",
        "| 폴더 A | 폴더 B | 공유 파일 | 공유 용량 | A 겹침 | B 겹침 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for t in trees:
        b = "(같은 폴더 안 사본)" if _key(t.a) == _key(t.b) else f"`{t.b}`"
        lines.append(f"| `{t.a}` | {b} | {t.files:,} | {human(t.bytes)} | "
                     f"{_coverage(t.files, t.total_a)} | {_coverage(t.files, t.total_b)} |")
    return lines + [""]


def _repo_group_lines(index: int, group: list[dict[str, str]]) -> list[str]:
    first = group[0]
    name = first["remote"] or (f"첫 커밋 {first['project_id']}" if first["project_id"] else first["path"])
    lines = [f"### 4.{index} {name} — 사본 {len(group)}개", "",
             "| | 경로 | 브랜치 | 최신 커밋 | 커밋 일시 | 미커밋 변경 |", "|---|---|---|---|---|---:|"]
    for j, r in enumerate(group):
        mark = "★" if j == 0 and len(group) > 1 else ""
        commit = _cell(f"{r['head']} {r['subject'][:50]}")
        lines.append(f"| {mark} | `{r['path']}` | {r['branch']} | {commit} | {r['date'][:16]} | {r['uncommitted']} |")
    return lines + [""]


def _repo_lines(repo_groups: list[list[dict[str, str]]]) -> list[str]:
    lines = ["## 4. git 저장소 사본", ""]
    if not repo_groups:
        return lines + ["발견된 git 저장소가 없습니다.", ""]
    if all(not r["head"] for g in repo_groups for r in g):
        lines += ["> git을 실행할 수 없어 커밋 정보를 읽지 못했습니다. git 설치 후 다시 실행하세요.", ""]
    lines += ["첫 커밋이 같은 저장소끼리 묶고 최근 커밋 순으로 정렬했습니다. ★ = 가장 최신 사본. "
              "미커밋 변경이 있는 사본은 정리 전에 반드시 확인하세요.", ""]
    for i, group in enumerate(repo_groups, 1):
        lines += _repo_group_lines(i, group)
    return lines


def _group_lines(groups: list[DupGroup], top: int) -> list[str]:
    lines = [f"## 5. 용량이 큰 중복 파일 TOP {top}", "",
             "| # | 파일 크기 | 사본 수 | 낭비 용량 | 위치 (오래된 것부터) |", "|---:|---:|---:|---:|---|"]
    for i, g in enumerate(groups[:top], 1):
        paths = "<br>".join(f"`{f.path}`" for f in sorted(g.files, key=lambda e: e.mtime))
        lines.append(f"| {i} | {human(g.size)} | {len(g.files)} | {human(g.wasted)} | {paths} |")
    return lines + [
        "", "## 6. 상세 파일", "",
        "- `duplicates.csv` — 모든 중복 그룹과 경로 (엑셀에서 바로 열림)",
        "- `copied_folders.csv` — 복사된 폴더 쌍",
        "- `git_repos.csv` — git 저장소 사본 정보",
        "- `summary.json` — 요약 수치", "",
    ]


def write_outputs(out: Path, roots: list[str], result: ScanResult, groups: list[DupGroup],
                  trees: list[TreePair], repo_groups: list[list[dict[str, str]]], top: int) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    write_duplicates_csv(out / "duplicates.csv", groups)
    write_trees_csv(out / "copied_folders.csv", trees)
    write_repos_csv(out / "git_repos.csv", repo_groups)
    lines = (_summary_lines(roots, result, groups) + _combo_lines(groups) + _tree_lines(trees)
             + _repo_lines(repo_groups) + _group_lines(groups, top))
    report = out / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "roots": roots, "files_scanned": len(result.entries), "duplicate_groups": len(groups),
        "reclaimable_bytes": sum(g.wasted for g in groups), "git_repos": len(result.repos),
        "errors": result.errors, "cloud_only_skipped": result.cloud_only,
        "by_location": {k: {"copies": c, "bytes": b} for k, (c, b) in drive_combos(groups).items()},
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


# ── 메인 ──────────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="여러 드라이브의 중복 파일 · 복사된 폴더 · git 저장소 사본 조사 (읽기 전용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n  python drive_audit\\find_duplicates.py C:\\ D:\\ E:\\\n"
               "  python drive_audit\\find_duplicates.py C:\\Users\\eungk E:\\ --out C:\\drive_report",
    )
    parser.add_argument("roots", nargs="+", help="검색할 드라이브나 폴더 (예: C:\\ D:\\ E:\\)")
    parser.add_argument("--out", help="결과 폴더 (기본: ./drive_audit_report_날짜_시각)")
    parser.add_argument("--min-size", type=int, default=1, help="이 크기(bytes) 미만 파일 무시 (기본 1 = 빈 파일만 제외)")
    parser.add_argument("--exclude", action="append", default=[], metavar="폴더이름",
                        help="추가로 제외할 폴더 이름 (여러 번 지정 가능)")
    parser.add_argument("--include-system", action="store_true",
                        help="기본 제외 폴더(Windows, AppData, node_modules, .git 등)도 검사")
    parser.add_argument("--top", type=int, default=30, help="보고서 표 항목 수 (기본 30)")
    return parser.parse_args(argv)


def build_options(args: argparse.Namespace) -> ScanOptions:
    extra = {name.lower() for name in args.exclude}
    top = set() if args.include_system else TOP_LEVEL_EXCLUDES
    anywhere = set() if args.include_system else ANYWHERE_EXCLUDES
    return ScanOptions(args.min_size, frozenset(top), frozenset(anywhere | extra))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots = normalize_roots(args.roots)
    if not roots:
        print("오류: 검색할 수 있는 폴더가 없습니다.", file=sys.stderr)
        return 1
    opts, result = build_options(args), ScanResult()
    for root in roots:
        print(f"스캔: {root}", file=sys.stderr)
        scan_root(root, opts, result)
    print(f"수집 완료: {len(result.entries):,}개 파일", file=sys.stderr)
    groups = find_duplicates(result.entries, result)
    trees = find_copied_trees(groups, result, args.top)
    print(f"git 저장소 {len(result.repos)}개 정보 수집 중", file=sys.stderr)
    repo_groups = group_repos([repo_info(r) for r in result.repos])
    out = Path(args.out or f"drive_audit_report_{datetime.now():%Y%m%d_%H%M}").resolve()
    report = write_outputs(out, roots, result, groups, trees, repo_groups, args.top)
    wasted = sum(g.wasted for g in groups)
    print(f"\n완료: 중복 그룹 {len(groups):,}개 | 회수 가능 {human(wasted)} | 오류 {result.errors:,}건")
    print(f"보고서: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
