"""중복 판정을 위한 해싱.

전체 파일을 무조건 해싱하면 128GB 백업은 128GB를 전부 읽어야 한다.
3단계로 좁혀 실제 읽는 양을 크게 줄인다.

  1. 파일 크기로 그룹핑 — 크기가 유일한 파일은 아예 해싱하지 않는다
  2. 같은 크기끼리만 앞/뒤 일부 블록으로 부분 해시
  3. 부분 해시까지 같은 것만 전체 해시

해시 알고리즘은 blake2b. 암호학적 서명이 아니라 동일성 판정 용도이며
md5보다 빠르고 충돌 저항도 강하다.
"""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BLOCK_SIZE = 1 << 16  # 64KB
PARTIAL_SIZE = 1 << 16  # 앞/뒤에서 각각 읽을 크기
DIGEST_SIZE = 16  # blake2b 출력 32자 hex


def default_workers() -> int:
    """해싱은 I/O 바운드라 코어 수보다 넉넉하게 잡는다."""
    return min(8, (os.cpu_count() or 4) * 2)


def _new_hasher():
    return hashlib.blake2b(digest_size=DIGEST_SIZE)


def full_digest(path: Path) -> str:
    """파일 전체 내용의 해시."""
    h = _new_hasher()
    with path.open("rb") as f:
        while chunk := f.read(BLOCK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def partial_digest(path: Path) -> str:
    """앞부분 + 뒷부분 + 크기만으로 만든 저비용 해시.

    다르면 확실히 다른 파일이다. 같다고 동일 파일은 아니므로 전체 해시로 확인한다.
    """
    size = path.stat().st_size
    h = _new_hasher()
    h.update(str(size).encode())
    with path.open("rb") as f:
        h.update(f.read(PARTIAL_SIZE))
        if size > PARTIAL_SIZE * 2:
            f.seek(-PARTIAL_SIZE, os.SEEK_END)
            h.update(f.read(PARTIAL_SIZE))
    return h.hexdigest()


def _map_parallel(fn, paths, workers):
    """경로별로 fn을 병렬 실행한다. 실패한 경로는 결과에서 빠진다."""
    if not paths:
        return {}
    if workers <= 1 or len(paths) == 1:
        results = {}
        for p in paths:
            try:
                results[p] = fn(p)
            except OSError:
                pass
        return results

    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for path, value in zip(paths, pool.map(_safe(fn), paths)):
            if value is not None:
                results[path] = value
    return results


def _safe(fn):
    def wrapper(path):
        try:
            return fn(path)
        except OSError:
            return None

    return wrapper


def _group_by(paths, key_of):
    groups: dict = {}
    for path in paths:
        groups.setdefault(key_of[path], []).append(path)
    return groups


def plan_duplicates(paths: list[Path], workers: int | None = None):
    """중복 파일을 찾아 (중복→원본 매핑, 경로→해시) 를 돌려준다.

    같은 내용의 파일이 여러 개면 정렬 순서상 첫 번째를 원본으로 삼고
    나머지를 중복으로 표시한다. 해시는 실제로 계산한 파일에 대해서만 담긴다.
    """
    if workers is None:
        workers = default_workers()

    sizes = {}
    for path in paths:
        try:
            sizes[path] = path.stat().st_size
        except OSError:
            continue

    # 1단계: 크기가 겹치는 파일만 후보로 남긴다
    candidates = [p for group in _group_by(list(sizes), sizes).values() if len(group) > 1 for p in group]

    # 2단계: 부분 해시로 후보를 더 좁힌다
    partials = _map_parallel(partial_digest, candidates, workers)
    narrowed = [p for group in _group_by(list(partials), partials).values() if len(group) > 1 for p in group]

    # 3단계: 남은 것만 전체 해시
    digests = _map_parallel(full_digest, narrowed, workers)

    duplicate_of: dict[Path, Path] = {}
    for group in _group_by(list(digests), digests).values():
        if len(group) < 2:
            continue
        keeper, *rest = sorted(group)
        for path in rest:
            duplicate_of[path] = keeper

    return duplicate_of, digests


def same_content(a: Path, b: Path) -> bool:
    """두 파일의 내용이 같은지 확인한다. 크기가 다르면 읽지 않는다."""
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
    except OSError:
        return False
    return full_digest(a) == full_digest(b)
