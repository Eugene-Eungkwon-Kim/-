"""저널 재개와 CLI 통합 동작 테스트."""

import json
import unittest
from datetime import datetime
from pathlib import Path

from helpers import TempTreeTestCase
from phonesort.categories import DUPLICATES
from phonesort.journal import JOURNAL_NAME
from phonesort.organizer import Organizer

JAN = datetime(2024, 1, 15, 14, 30, 22)


class JournalTest(TempTreeTestCase):
    def test_journal_records_every_move(self):
        self.src("a.jpg", b"one", JAN)
        self.src("b.jpg", b"two-different", JAN)

        Organizer(self.source, self.dest, log=self.quiet).run()

        lines = (self.dest / JOURNAL_NAME).read_text(encoding="utf-8").strip().splitlines()
        entries = [json.loads(line) for line in lines]
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(entry["action"] == "move" for entry in entries))
        for entry in entries:
            self.assertTrue(Path(entry["destination"]).exists())

    def test_resume_skips_already_processed_sources(self):
        first = self.src("a.jpg", b"one", JAN)
        Organizer(self.source, self.dest, log=self.quiet).run()

        # 같은 경로에 파일이 다시 나타나도 저널에 있으면 건너뛴다
        self.src("a.jpg", b"one", JAN)
        stats = Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual(stats.skipped, 1)
        self.assertEqual(stats.moved, 0)
        self.assertTrue(first.exists(), "건너뛴 파일이 사라졌다")

    def test_no_resume_reprocesses(self):
        self.src("a.jpg", b"one", JAN)
        Organizer(self.source, self.dest, log=self.quiet).run()
        self.src("a.jpg", b"one", JAN)

        stats = Organizer(self.source, self.dest, log=self.quiet, resume=False).run()

        self.assertEqual(stats.skipped, 0)
        # 목적지에 같은 내용이 이미 있으므로 중복으로 처리된다
        self.assertEqual(stats.duplicates, 1)

    def test_truncated_journal_line_is_ignored(self):
        self.src("a.jpg", b"one", JAN)
        Organizer(self.source, self.dest, log=self.quiet).run()
        journal = self.dest / JOURNAL_NAME
        journal.write_text(journal.read_text(encoding="utf-8") + '{"action": "mo',
                           encoding="utf-8")

        self.src("b.jpg", b"two-different", JAN)
        stats = Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual(stats.errors, 0)
        self.assertEqual(stats.moved, 1)

    def test_resume_does_not_promote_a_copy_to_a_second_keeper(self):
        """중복 처리 직전에 끊겨도 사본이 새 보존본으로 올라가면 안 된다.

        저널의 해시를 대조하지 않으면 이미 옮긴 보존본이 이번 목록에 없어
        남은 사본 중 하나가 승격되고, 같은 내용이 목적지에 두 벌 남는다.
        """
        payload = b"identical-payload"
        for name in ("a.jpg", "b.jpg", "c.jpg"):
            self.src(name, payload, JAN)

        class Interrupted(Organizer):
            def _handle_duplicates(self, *args, **kwargs):
                raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            Interrupted(self.source, self.dest, log=self.quiet).run()

        stats = Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual(stats.moved, 0, "사본이 새 보존본으로 승격됐다")
        self.assertEqual(stats.duplicates, 2)
        self.assertEqual(stats.errors, 0)
        kept = [p for p in self.dest.rglob("*")
                if p.is_file() and DUPLICATES not in p.parts
                and p.read_bytes() == payload]
        self.assertEqual(len(kept), 1, "같은 내용이 목적지에 두 벌 남았다")

    def test_resume_ignores_journal_entry_whose_destination_is_gone(self):
        """저널에 있어도 목적지 파일이 사라졌으면 남은 파일을 정상 보존한다."""
        payload = b"identical-payload"
        for name in ("a.jpg", "b.jpg"):
            self.src(name, payload, JAN)

        class Interrupted(Organizer):
            def _handle_duplicates(self, *args, **kwargs):
                raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            Interrupted(self.source, self.dest, log=self.quiet).run()
        for moved in list(self.dest.rglob("*.jpg")):
            moved.unlink()  # 사용자가 결과물을 지운 상황

        stats = Organizer(self.source, self.dest, log=self.quiet).run()

        self.assertEqual(stats.moved, 1, "보존본이 사라졌는데 아무것도 남기지 않았다")
        self.assertEqual(stats.errors, 0)

    def test_dry_run_writes_no_journal(self):
        self.src("a.jpg", b"one", JAN)
        Organizer(self.source, self.dest, dry_run=True, log=self.quiet).run()
        self.assertFalse((self.dest / JOURNAL_NAME).exists())


class PruneTest(TempTreeTestCase):
    def test_empty_dirs_are_removed_only_when_asked(self):
        self.src("DCIM/100APPLE/a.jpg", b"one", JAN)

        organizer = Organizer(self.source, self.dest, log=self.quiet)
        organizer.run()
        self.assertTrue((self.source / "DCIM" / "100APPLE").exists())

        removed = organizer.prune_empty_dirs()
        self.assertEqual(removed, 2)
        self.assertFalse((self.source / "DCIM").exists())

    def test_dirs_with_files_are_kept(self):
        self.src("DCIM/keep.txt", b"x", JAN)
        organizer = Organizer(self.source, self.dest, log=self.quiet, dry_run=True)
        organizer.run()
        self.assertEqual(organizer.prune_empty_dirs(), 0)
        self.assertTrue((self.source / "DCIM").exists())


class CliTest(TempTreeTestCase):
    def run_cli(self, module, argv):
        import io
        import contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = module.main(argv)
        return code, buffer.getvalue()

    def test_organize_cli_end_to_end(self):
        import organize
        self.src("DCIM/IMG_0001.jpg", b"photo", JAN)
        self.src("Music/song.mp3", b"audio", JAN)

        code, output = self.run_cli(organize, [str(self.source), str(self.dest)])

        self.assertEqual(code, 0)
        self.assertIn("이동 2개", output)
        self.assertEqual(self.dest_files(), {
            "사진/2024/01/20240115_143022_IMG_0001.jpg",
            "음악/2024/01/20240115_143022_song.mp3",
        })

    def test_organize_cli_rejects_same_folder(self):
        import organize
        code, output = self.run_cli(organize, [str(self.source), str(self.source)])
        self.assertEqual(code, 1)
        self.assertIn("같을 수 없습니다", output)

    def test_iphone_cli_separates_live_photos(self):
        import iphone_migrate
        self.src("100APPLE/IMG_0001.HEIC", b"still", JAN)
        self.src("100APPLE/IMG_0001.MOV", b"motion", JAN)
        self.src("100APPLE/IMG_E0002.HEIC", b"edited", JAN)

        code, _ = self.run_cli(iphone_migrate, [str(self.source), str(self.dest)])

        self.assertEqual(code, 0)
        self.assertEqual(self.dest_files(), {
            "라이브포토/2024/01/20240115_143022_IMG_0001.heic",
            "라이브포토/2024/01/20240115_143022_IMG_0001.mov",
            "편집본/2024/01/20240115_143022_IMG_E0002.heic",
            "iphone_migration_report.json",
        })

    def test_iphone_cli_writes_report(self):
        import iphone_migrate
        self.src("IMG_0001.HEIC", b"still", JAN)

        self.run_cli(iphone_migrate, [str(self.source), str(self.dest)])

        report = json.loads((self.dest / "iphone_migration_report.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(report["이동"], 1)
        self.assertEqual(report["기기"], "iPhone")
        self.assertEqual(report["카테고리별"], {"사진": 1})

    def test_migrate_cli_local_source(self):
        import migrate
        self.src("Download/doc.pdf", b"pdf", JAN)

        code, _ = self.run_cli(migrate, ["--source", str(self.source), str(self.dest)])

        self.assertEqual(code, 0)
        self.assertIn("문서/2024/01/20240115_143022_doc.pdf", self.dest_files())

    def test_dry_run_cli_leaves_source_untouched(self):
        import organize
        self.src("DCIM/IMG_0001.jpg", b"photo", JAN)
        before = self.snapshot(self.source)

        code, output = self.run_cli(
            organize, [str(self.source), str(self.dest), "--dry-run"])

        self.assertEqual(code, 0)
        self.assertIn("미리보기", output)
        self.assertEqual(self.snapshot(self.source), before)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
