"""이동 기록 저널.

수천 개 파일을 옮기다 중단되면 무엇까지 처리했는지 알 수 없다.
처리 직후 한 줄씩 append 해두고, 다시 실행할 때 이미 끝난 파일을 건너뛴다.
"""

import json
from datetime import datetime
from pathlib import Path

JOURNAL_NAME = ".phonesort_journal.jsonl"


class Journal:
    """JSONL 저널. `enabled=False` 면 아무것도 쓰지 않는다(미리보기 모드)."""

    def __init__(self, path: Path, enabled: bool = True):
        self.path = path
        self.enabled = enabled
        self._handle = None

    def completed_sources(self) -> set[str]:
        """이미 처리가 끝난 원본 경로 집합."""
        if not self.path.exists():
            return set()
        done = set()
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue  # 중단 시점에 잘린 마지막 줄
            source = entry.get("source")
            if source:
                done.add(source)
        return done

    def record(self, action: str, source: Path, destination: Path | None = None,
               digest: str | None = None) -> None:
        if not self.enabled:
            return
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8")
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "source": str(source),
        }
        if destination is not None:
            entry["destination"] = str(destination)
        if digest is not None:
            entry["digest"] = digest
        self._handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._handle.flush()

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
