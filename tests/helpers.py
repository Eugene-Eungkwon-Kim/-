"""테스트용 가짜 휴대폰 폴더 생성 도구."""

import os
import struct
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

QUICKTIME_EPOCH = datetime(1904, 1, 1)


def write(path: Path, content: bytes | str = b"data", mtime: datetime | None = None) -> Path:
    """파일 하나를 만들고 필요하면 수정 시각을 지정한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode()
    path.write_bytes(content)
    if mtime is not None:
        stamp = mtime.timestamp()
        os.utime(path, (stamp, stamp))
    return path


def box(box_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), box_type) + payload


def _udta_text_atom(fourcc: bytes, text: str) -> bytes:
    return box(fourcc, struct.pack(">HH", len(text), 0) + text.encode())


def make_mp4(created: datetime, udta_text: str | None = None,
             decoy_atom: tuple[bytes, str] | None = None) -> bytes:
    """mvhd(그리고 선택적으로 udta 날짜 문자열)를 담은 최소 MP4 바이트열.

    `decoy_atom` 은 `©day` 가 아닌 다른 udta 하위 박스(예: 댓글)에 날짜처럼
    보이는 문자열을 넣어, 날짜 파싱이 `©day` 박스만 보는지 확인할 때 쓴다.
    """
    seconds = int((created - QUICKTIME_EPOCH).total_seconds())
    mvhd_payload = (
        bytes(4)                       # version 0 + flags
        + struct.pack(">I", seconds)   # creation_time
        + struct.pack(">I", seconds)   # modification_time
        + struct.pack(">I", 1000)      # timescale
        + struct.pack(">I", 0)         # duration
    )
    children = box(b"mvhd", mvhd_payload)
    udta_children = b""
    if decoy_atom is not None:
        fourcc, text = decoy_atom
        udta_children += _udta_text_atom(fourcc, text)
    if udta_text is not None:
        udta_children += _udta_text_atom(b"\xa9day", udta_text)
    if udta_children:
        children += box(b"udta", udta_children)
    return box(b"ftyp", b"qt  \x00\x00\x02\x00") + box(b"moov", children)


class TempTreeTestCase(unittest.TestCase):
    """임시 원본/대상 폴더를 준비하는 베이스 클래스."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "phone"
        self.dest = self.root / "out"
        self.source.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def src(self, relative: str, content: bytes | str = b"data",
            mtime: datetime | None = None) -> Path:
        return write(self.source / relative, content, mtime)

    def snapshot(self, root: Path) -> set[tuple[str, int]]:
        """폴더 상태를 (상대경로, 크기) 집합으로 찍어둔다."""
        return {
            (str(p.relative_to(root)), p.stat().st_size)
            for p in root.rglob("*")
            if p.is_file()
        }

    def dest_files(self) -> set[str]:
        if not self.dest.exists():
            return set()
        return {
            str(p.relative_to(self.dest))
            for p in self.dest.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        }

    def quiet(self, *_args, **_kwargs) -> None:
        """Organizer 로그를 삼킨다."""
