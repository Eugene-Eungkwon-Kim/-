"""파일 정리 실행부.

안전 원칙 두 가지를 지킨다.

1. 중복 파일은 **원본이 목적지로 옮겨진 것을 확인한 뒤에만** 처리한다.
   원본 이동이 실패하면 사본은 손대지 않는다.
2. 중복 파일은 기본적으로 삭제하지 않고 `중복/` 폴더로 격리한다.
   삭제는 `--delete-duplicates` 를 켠 경우에만 한다.
"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from . import hashing
from .categories import DEFAULT_CATEGORIES, DUPLICATES, by_extension
from .dates import file_date
from .journal import JOURNAL_NAME, Journal
from .naming import new_filename

Classifier = Callable[[Path], str]
ClassifierFactory = Callable[[list[Path]], Classifier]


class PathValidationError(ValueError):
    """원본/대상 폴더 조합이 안전하지 않을 때."""


@dataclass
class Stats:
    moved: int = 0
    duplicates: int = 0
    skipped: int = 0
    errors: int = 0
    by_category: dict[str, int] = field(default_factory=dict)

    def count(self, category: str) -> None:
        self.by_category[category] = self.by_category.get(category, 0) + 1


def validate_paths(source: Path, dest: Path) -> None:
    """원본과 대상이 같은 경우를 막는다.

    한쪽이 다른 쪽 하위에 있는 것 자체는 허용한다. 스캔 단계에서 정리 결과물을
    제외하므로 이미 옮긴 파일을 다시 집어오지 않는다.
    """
    if source == dest:
        raise PathValidationError("원본과 대상 폴더가 같을 수 없습니다.")
    if not source.exists():
        raise PathValidationError(f"원본 폴더를 찾을 수 없습니다: {source}")
    if not source.is_dir():
        raise PathValidationError(f"원본이 폴더가 아닙니다: {source}")


def _is_hidden(path: Path, root: Path) -> bool:
    return any(part.startswith(".") for part in path.relative_to(root).parts)


def collect_files(source: Path, dest: Path) -> list[Path]:
    """정리 대상 파일 목록.

    `dest` 아래에 이미 만들어진 결과물은 건너뛴다. 단 원본이 `dest` 안에 있는
    경우(ADB 로 받은 원본 폴더)에는 그 하위는 정상적으로 수집한다.
    """
    # 원본이 대상 안에 있는 경우(ADB 로 받은 폴더)에만 대상 하위를 훑는다.
    # 그 외에는 대상 하위 전체가 이미 정리된 결과물이므로 건너뛴다.
    skip_dest_subtree = not source.is_relative_to(dest)

    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if _is_hidden(path, source):
            continue
        if skip_dest_subtree and path.is_relative_to(dest):
            continue
        files.append(path)
    return files


class Organizer:
    def __init__(
        self,
        source: Path,
        dest: Path,
        *,
        classifier_factory: ClassifierFactory | None = None,
        dry_run: bool = False,
        delete_duplicates: bool = False,
        verify: bool = False,
        resume: bool = True,
        workers: int | None = None,
        log: Callable[[str], None] = print,
    ):
        self.source = source
        self.dest = dest
        self.classifier_factory = classifier_factory or _default_classifier_factory
        self.dry_run = dry_run
        self.delete_duplicates = delete_duplicates
        self.verify = verify
        self.resume = resume
        self.workers = workers
        self.log = log
        self.stats = Stats()
        self.journal = Journal(dest / JOURNAL_NAME, enabled=not dry_run)
        # 이번 실행에서 이미 배정한 대상 경로. 미리보기 모드에서도 이름 충돌을
        # 실제 실행과 똑같이 계산하기 위해 필요하다.
        self._reserved: set[Path] = set()

    # ── 실행 ────────────────────────────────────────────────────────────────

    def run(self) -> Stats:
        validate_paths(self.source, self.dest)

        files = collect_files(self.source, self.dest)
        if self.resume:
            already_done = self.journal.completed_sources()
            if already_done:
                before = len(files)
                files = [f for f in files if str(f) not in already_done]
                self.stats.skipped = before - len(files)
                self.log(f"저널 확인: 이미 처리된 {self.stats.skipped}개 건너뜀")

        classify = self.classifier_factory(files)
        duplicate_of, digests = hashing.plan_duplicates(files, self.workers)

        self.log(f"\n총 {len(files)}개 파일 | 중복 후보 {len(duplicate_of)}개\n")

        with self.journal:
            moved_to = self._move_originals(files, duplicate_of, digests, classify)
            self._handle_duplicates(duplicate_of, digests, moved_to)

        return self.stats

    def _move_originals(self, files: Iterable[Path], duplicate_of: dict[Path, Path],
                        digests: dict[Path, str], classify: Classifier) -> dict[Path, Path]:
        """중복이 아닌 파일을 목적지로 옮기고 원본→대상 매핑을 돌려준다."""
        moved_to: dict[Path, Path] = {}
        for path in files:
            if path in duplicate_of:
                continue  # 원본이 옮겨진 뒤 따로 처리한다
            try:
                category = classify(path)
                target = self._destination_for(path, category)
                if target == path:
                    # 이미 제자리에 있는 파일. 자기 자신을 중복으로 오인해
                    # 삭제하는 일이 없도록 여기서 끊는다.
                    self.stats.skipped += 1
                    continue
                existing = self._existing_identical(target, path)
                if existing is not None:
                    # 목적지에 같은 내용이 이미 있다 — 덮어쓰지 않고 중복으로 돌린다.
                    # 보존본이 이미 디스크에 있으므로 이동 확인은 끝난 셈이다.
                    duplicate_of[path] = existing
                    moved_to[existing] = existing
                    continue

                target = self._reserve(target)
                self.log(f"  [이동] {self._rel(path)}  →  {target.relative_to(self.dest)}")
                if not self.dry_run:
                    self._move(path, target)
                    self.journal.record("move", path, target, digests.get(path))
                moved_to[path] = target
                self.stats.moved += 1
                self.stats.count(category)
            except Exception as exc:
                self.log(f"  [오류] {path.name}: {exc}")
                self.stats.errors += 1
        return moved_to

    def _handle_duplicates(self, duplicate_of: dict[Path, Path], digests: dict[Path, str],
                           moved_to: dict[Path, Path]) -> None:
        """원본 이동이 확인된 중복만 삭제하거나 격리한다."""
        for path, keeper in duplicate_of.items():
            if keeper not in moved_to:
                self.log(f"  [보류] {path.name}: 원본 이동이 확인되지 않아 그대로 둡니다")
                self.stats.errors += 1
                continue
            try:
                if self.delete_duplicates:
                    self.log(f"  [중복삭제] {self._rel(path)}  ←→  {keeper.name}")
                    if not self.dry_run:
                        path.unlink()
                        self.journal.record("duplicate-delete", path, digest=digests.get(path))
                else:
                    target = self._reserve(self.dest / DUPLICATES / path.name)
                    self.log(f"  [중복격리] {self._rel(path)}  →  {target.relative_to(self.dest)}")
                    if not self.dry_run:
                        self._move(path, target)
                        self.journal.record("duplicate-quarantine", path, target, digests.get(path))
                self.stats.duplicates += 1
            except Exception as exc:
                self.log(f"  [오류] {path.name}: {exc}")
                self.stats.errors += 1

    # ── 경로 계산 ───────────────────────────────────────────────────────────

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.source))
        except ValueError:
            return str(path)

    def _destination_for(self, path: Path, category: str) -> Path:
        date = file_date(path)
        folder = self.dest / category / f"{date:%Y}" / f"{date:%m}"
        return folder / new_filename(path, date)

    def _existing_identical(self, target: Path, source: Path) -> Path | None:
        """목적지에 이미 같은 내용의 파일이 있으면 그 경로를 돌려준다."""
        if not target.exists():
            return None
        return target if hashing.same_content(target, source) else None

    def _reserve(self, target: Path) -> Path:
        """실제로 쓸 대상 경로를 확정한다.

        이름이 겹치면 `_1`, `_2` 를 붙인다. 기존 파일도, 이번 실행에서 이미
        배정한 경로도 덮어쓰지 않는다.
        """
        candidate = target
        counter = 1
        while candidate.exists() or candidate in self._reserved:
            candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
            counter += 1
        self._reserved.add(candidate)
        return candidate

    # ── 파일 이동 ───────────────────────────────────────────────────────────

    def _move(self, source: Path, target: Path) -> None:
        expected_size = source.stat().st_size
        expected_digest = hashing.full_digest(source) if self.verify else None

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))

        if not target.exists() or target.stat().st_size != expected_size:
            raise OSError(f"이동 후 검증 실패: {target}")
        if expected_digest is not None and hashing.full_digest(target) != expected_digest:
            raise OSError(f"내용 검증 실패: {target}")

    # ── 뒷정리 ──────────────────────────────────────────────────────────────

    def prune_empty_dirs(self) -> int:
        """원본 아래 남은 빈 폴더를 지운다. 파일이 하나라도 있으면 두고 간다."""
        if self.dry_run:
            return 0
        removed = 0
        for path in sorted(self.source.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                removed += 1
        return removed


def _default_classifier_factory(_files: list[Path]) -> Classifier:
    return lambda path: by_extension(path, DEFAULT_CATEGORIES)
