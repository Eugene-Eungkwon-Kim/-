"""데이터 안전에 관한 테스트 — 이 파일이 깨지면 사용자가 파일을 잃는다."""

import unittest
from datetime import datetime
from pathlib import Path

from helpers import TempTreeTestCase
from phonesort.organizer import Organizer, PathValidationError

JAN = datetime(2024, 1, 15, 14, 30, 22)


class DuplicateSafetyTest(TempTreeTestCase):
    def organize(self, **kwargs):
        organizer = Organizer(self.source, self.dest, log=self.quiet, **kwargs)
        return organizer, organizer.run()

    def test_duplicates_are_quarantined_not_deleted_by_default(self):
        self.src("a/photo.jpg", b"same-content", JAN)
        self.src("b/photo_copy.jpg", b"same-content", JAN)

        _, stats = self.organize()

        self.assertEqual(stats.moved, 1)
        self.assertEqual(stats.duplicates, 1)
        # 사본은 삭제되지 않고 중복/ 으로 격리된다
        quarantined = list((self.dest / "중복").rglob("*"))
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].read_bytes(), b"same-content")

    def test_delete_duplicates_opt_in_removes_copies(self):
        self.src("a/photo.jpg", b"same-content", JAN)
        self.src("b/photo_copy.jpg", b"same-content", JAN)

        _, stats = self.organize(delete_duplicates=True)

        self.assertEqual(stats.moved, 1)
        self.assertEqual(stats.duplicates, 1)
        self.assertFalse((self.dest / "중복").exists())
        # 내용은 정확히 한 벌 살아남는다
        survivors = [p for p in self.dest.rglob("*") if p.is_file() and p.suffix == ".jpg"]
        self.assertEqual(len(survivors), 1)

    def test_duplicate_survives_when_original_move_fails(self):
        """원본 이동이 실패하면 사본은 절대 건드리지 않는다."""
        original = self.src("a/photo.jpg", b"same-content", JAN)
        copy = self.src("b/photo_copy.jpg", b"same-content", JAN)

        class FailingOrganizer(Organizer):
            def _move(self, source: Path, target: Path) -> None:
                if source == original:
                    raise OSError("디스크 가득 참")
                super()._move(source, target)

        organizer = FailingOrganizer(self.source, self.dest, log=self.quiet,
                                     delete_duplicates=True)
        stats = organizer.run()

        self.assertEqual(stats.moved, 0)
        self.assertEqual(stats.duplicates, 0)
        self.assertTrue(original.exists(), "이동 실패한 원본이 사라졌다")
        self.assertTrue(copy.exists(), "원본을 잃은 채로 사본이 삭제되었다")

    def test_three_identical_files_keep_exactly_one(self):
        for name in ("x.jpg", "y.jpg", "z.jpg"):
            self.src(name, b"identical", JAN)

        _, stats = self.organize(delete_duplicates=True)

        self.assertEqual(stats.moved, 1)
        self.assertEqual(stats.duplicates, 2)
        remaining = [p for p in self.dest.rglob("*.jpg") if p.is_file()]
        self.assertEqual(len(remaining), 1)


class DryRunTest(TempTreeTestCase):
    def test_dry_run_changes_nothing(self):
        self.src("a/photo.jpg", b"one", JAN)
        self.src("b/photo.jpg", b"one", JAN)  # 중복
        self.src("c/clip.mp4", b"video-bytes", JAN)
        before = self.snapshot(self.source)

        stats = Organizer(self.source, self.dest, dry_run=True, log=self.quiet,
                          delete_duplicates=True).run()

        self.assertEqual(self.snapshot(self.source), before, "미리보기가 원본을 바꿨다")
        self.assertFalse(self.dest.exists(), "미리보기가 대상 폴더를 만들었다")
        self.assertEqual(stats.moved, 2)
        self.assertEqual(stats.duplicates, 1)


class CollisionTest(TempTreeTestCase):
    def test_different_files_same_name_get_suffixes(self):
        self.src("a/IMG_0001.jpg", b"first", JAN)
        self.src("b/IMG_0001.jpg", b"second-different", JAN)

        stats = Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual(stats.moved, 2)
        self.assertEqual(stats.duplicates, 0)
        names = sorted(p.name for p in (self.dest / "사진" / "2024" / "01").iterdir())
        self.assertEqual(names, ["20240115_143022_IMG_0001.jpg",
                                 "20240115_143022_IMG_0001_1.jpg"])
        contents = {p.read_bytes() for p in (self.dest / "사진" / "2024" / "01").iterdir()}
        self.assertEqual(contents, {b"first", b"second-different"})

    def test_existing_destination_file_is_never_overwritten(self):
        target_dir = self.dest / "사진" / "2024" / "01"
        target_dir.mkdir(parents=True)
        (target_dir / "20240115_143022_IMG_0001.jpg").write_bytes(b"already here")
        self.src("IMG_0001.jpg", b"incoming", JAN)

        Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual((target_dir / "20240115_143022_IMG_0001.jpg").read_bytes(),
                         b"already here")
        self.assertEqual((target_dir / "20240115_143022_IMG_0001_1.jpg").read_bytes(),
                         b"incoming")

    def test_identical_file_already_at_destination_is_not_duplicated(self):
        target_dir = self.dest / "사진" / "2024" / "01"
        target_dir.mkdir(parents=True)
        (target_dir / "20240115_143022_IMG_0001.jpg").write_bytes(b"same")
        self.src("IMG_0001.jpg", b"same", JAN)

        stats = Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual(stats.moved, 0)
        self.assertEqual(stats.duplicates, 1)
        self.assertEqual(len(list(target_dir.iterdir())), 1)


class PathValidationTest(TempTreeTestCase):
    def test_same_source_and_dest_is_rejected(self):
        with self.assertRaises(PathValidationError):
            Organizer(self.source, self.source, log=self.quiet).run()

    def test_missing_source_is_rejected(self):
        with self.assertRaises(PathValidationError):
            Organizer(self.root / "없는폴더", self.dest, log=self.quiet).run()

    def test_dest_inside_source_does_not_reprocess_output(self):
        """`organize.py ~/phone ~/phone/정리결과` 가 결과물을 다시 집어오면 안 된다."""
        nested_dest = self.source / "정리결과"
        self.src("photo.jpg", b"content", JAN)

        first = Organizer(self.source, nested_dest, log=self.quiet).run()
        self.assertEqual(first.moved, 1)

        # 두 번째 실행은 정리된 결과물을 원본으로 착각하지 않아야 한다
        second = Organizer(self.source, nested_dest, log=self.quiet).run()
        self.assertEqual(second.moved, 0)
        self.assertEqual(second.duplicates, 0)
        self.assertEqual(second.errors, 0)

        organized = [p for p in nested_dest.rglob("*.jpg") if p.is_file()]
        self.assertEqual(len(organized), 1)

    def test_source_inside_dest_is_allowed(self):
        """ADB 흐름: dest/raw_from_device 를 원본으로 삼는다."""
        raw = self.dest / "raw_from_device"
        (raw / "DCIM").mkdir(parents=True)
        from helpers import write
        write(raw / "DCIM" / "photo.jpg", b"content", JAN)

        stats = Organizer(raw, self.dest, log=self.quiet).run()

        self.assertEqual(stats.moved, 1)
        self.assertTrue((self.dest / "사진" / "2024" / "01" /
                         "20240115_143022_photo.jpg").exists())


if __name__ == "__main__":
    unittest.main()
