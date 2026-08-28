"""이름 정리 / 해싱 / 분류 / 날짜 추출 단위 테스트."""

import unittest
from datetime import datetime
from pathlib import Path

from helpers import TempTreeTestCase, make_mp4, write
from phonesort import hashing, naming
from phonesort.categories import iphone_category, live_photo_keys
from phonesort.dates import video_date
from phonesort.naming import new_filename, safe_name

JAN = datetime(2024, 1, 15, 14, 30, 22)


class NamingTest(unittest.TestCase):
    def test_illegal_characters_are_replaced(self):
        self.assertEqual(safe_name('my:photo*name?'), "my_photo_name")

    def test_whitespace_collapses(self):
        self.assertEqual(safe_name("  a   b  "), "a_b")

    def test_empty_name_gets_placeholder(self):
        self.assertEqual(safe_name("///"), "unnamed")

    def test_timestamp_prefix_is_added(self):
        self.assertEqual(new_filename(Path("IMG_0001.JPG"), JAN),
                         "20240115_143022_IMG_0001.jpg")

    def test_already_dated_name_is_left_alone(self):
        self.assertEqual(new_filename(Path("20240115_143022_IMG_0001.jpg"), JAN),
                         "20240115_143022_IMG_0001.jpg")

    def test_date_only_prefix_is_left_alone(self):
        self.assertEqual(new_filename(Path("20240115_vacation.jpg"), JAN),
                         "20240115_vacation.jpg")

    def test_rerun_is_idempotent_for_img_names(self):
        """정리된 폴더를 다시 정리해도 접두사가 중첩되지 않는다."""
        once = new_filename(Path("IMG_0001.jpg"), JAN)
        twice = new_filename(Path(once), datetime(2025, 6, 1, 9, 0, 0))
        self.assertEqual(once, twice)

    def test_long_name_is_cut_to_filesystem_limit(self):
        result = new_filename(Path("x" * 300 + ".jpg"), JAN)
        self.assertLessEqual(len(result.encode()), naming.MAX_NAME_BYTES)
        self.assertTrue(result.startswith("20240115_143022_"))
        self.assertTrue(result.endswith(".jpg"))

    def test_long_korean_name_is_cut_on_a_character_boundary(self):
        """한글은 글자당 3바이트라 85자만 넘어도 상한에 걸린다."""
        result = new_filename(Path("가" * 200 + ".jpg"), JAN)
        self.assertLessEqual(len(result.encode()), naming.MAX_NAME_BYTES)
        self.assertNotIn("�", result, "글자 중간에서 잘렸다")
        self.assertEqual(result, result.encode().decode("utf-8"))

    def test_truncation_is_idempotent(self):
        once = new_filename(Path("가" * 200 + ".jpg"), JAN)
        twice = new_filename(Path(once), datetime(2025, 6, 1, 9, 0, 0))
        self.assertEqual(once, twice)

    def test_short_name_is_untouched(self):
        self.assertEqual(new_filename(Path("IMG_0001.JPG"), JAN),
                         "20240115_143022_IMG_0001.jpg")


class HashingTest(TempTreeTestCase):
    def test_unique_sizes_are_never_hashed(self):
        paths = [self.src("a.bin", b"1"), self.src("b.bin", b"22"), self.src("c.bin", b"333")]

        duplicate_of, digests = hashing.plan_duplicates(paths)

        self.assertEqual(duplicate_of, {})
        self.assertEqual(digests, {}, "크기가 유일한 파일을 해싱했다")

    def test_same_size_different_content_stops_at_partial_hash(self):
        """크기가 같아도 앞부분이 다르면 전체 해시까지 가지 않는다."""
        paths = [self.src("a.bin", b"aaaa"), self.src("b.bin", b"bbbb")]

        duplicate_of, digests = hashing.plan_duplicates(paths)

        self.assertEqual(duplicate_of, {})
        self.assertEqual(digests, {}, "부분 해시로 갈렸는데 전체 해시를 계산했다")

    def test_full_hash_runs_only_when_partial_hash_collides(self):
        """앞뒤가 같고 가운데만 다르면 전체 해시로 확인해야 한다."""
        head = b"H" * hashing.PARTIAL_SIZE
        tail = b"T" * hashing.PARTIAL_SIZE
        left = self.src("left.bin", head + b"A" * 4096 + tail)
        right = self.src("right.bin", head + b"B" * 4096 + tail)

        duplicate_of, digests = hashing.plan_duplicates([left, right])

        self.assertEqual(duplicate_of, {})
        self.assertEqual(len(digests), 2, "부분 해시가 같으면 전체 해시로 확인해야 한다")

    def test_duplicates_are_grouped_under_one_keeper(self):
        first = self.src("a.bin", b"same")
        second = self.src("b.bin", b"same")
        third = self.src("c.bin", b"same")

        duplicate_of, _ = hashing.plan_duplicates([first, second, third])

        self.assertEqual(len(duplicate_of), 2)
        self.assertEqual(set(duplicate_of.values()), {first})

    def test_large_file_partial_hash_distinguishes_tails(self):
        head = b"x" * (hashing.PARTIAL_SIZE * 3)
        left = self.src("left.bin", head + b"AAAA")
        right = self.src("right.bin", head + b"BBBB")

        duplicate_of, _ = hashing.plan_duplicates([left, right])

        self.assertEqual(duplicate_of, {})

    def test_same_content_helper(self):
        a = self.src("a.bin", b"hello")
        b = self.src("b.bin", b"hello")
        c = self.src("c.bin", b"world!")
        self.assertTrue(hashing.same_content(a, b))
        self.assertFalse(hashing.same_content(a, c))


class IPhoneCategoryTest(TempTreeTestCase):
    def classify(self, names: list[str]) -> dict[str, str]:
        paths = [write(self.source / name) for name in names]
        keys = live_photo_keys(paths)
        return {p.name: iphone_category(p, keys) for p in paths}

    def test_live_photo_pair_stays_together(self):
        result = self.classify(["100APPLE/IMG_0001.HEIC", "100APPLE/IMG_0001.MOV"])
        self.assertEqual(result["IMG_0001.HEIC"], "라이브포토")
        self.assertEqual(result["IMG_0001.MOV"], "라이브포토")

    def test_same_name_in_different_folders_is_not_a_pair(self):
        result = self.classify(["100APPLE/IMG_0001.HEIC", "Download/IMG_0001.MOV"])
        self.assertEqual(result["IMG_0001.HEIC"], "사진")
        self.assertEqual(result["IMG_0001.MOV"], "동영상")

    def test_edited_file_is_not_a_timelapse(self):
        result = self.classify(["IMG_E1234.HEIC", "IMG_E5678.MOV"])
        self.assertEqual(result["IMG_E1234.HEIC"], "편집본")
        self.assertEqual(result["IMG_E5678.MOV"], "편집본")

    def test_slomo_and_timelapse_patterns(self):
        result = self.classify(["IMG_SloMo_01.mov", "TimeLapse_beach.mp4", "IMG_9999.mov",
                                "slow motion dive.mov"])
        self.assertEqual(result["IMG_SloMo_01.mov"], "슬로모션")
        self.assertEqual(result["slow motion dive.mov"], "슬로모션")
        self.assertEqual(result["TimeLapse_beach.mp4"], "타임랩스")
        self.assertEqual(result["IMG_9999.mov"], "동영상")

    def test_word_slow_alone_is_not_a_slomo(self):
        """`slow` 만으로 잡으면 평범한 영상까지 슬로모션으로 끌려온다."""
        result = self.classify(["Slow Cooker Recipe.mp4", "slowdance.mov"])
        self.assertEqual(result["Slow Cooker Recipe.mp4"], "동영상")
        self.assertEqual(result["slowdance.mov"], "동영상")

    def test_documents_and_unknown_extensions(self):
        result = self.classify(["notes.pages", "mystery.xyz"])
        self.assertEqual(result["notes.pages"], "문서")
        self.assertEqual(result["mystery.xyz"], "기타")


class ExifDateTest(TempTreeTestCase):
    """Pillow 가 있을 때만 의미가 있는 테스트."""

    def setUp(self):
        super().setUp()
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow 미설치")
        self.Image = Image

    def write_jpeg(self, name: str, *, original: str | None, edited: str | None) -> Path:
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        image = self.Image.new("RGB", (8, 8), "red")
        exif = image.getexif()
        if edited is not None:
            exif[0x0132] = edited  # DateTime (IFD0)
        if original is not None:
            exif.get_ifd(0x8769)[0x9003] = original  # DateTimeOriginal (Exif SubIFD)
        image.save(path, exif=exif)
        return path

    def test_datetime_original_wins_over_datetime(self):
        """DateTimeOriginal 은 Exif 서브 IFD 안에 있어 최상위만 봐서는 못 찾는다."""
        from phonesort.dates import exif_date
        path = self.write_jpeg("a.jpg", original="2024:03:15 10:30:00",
                               edited="2020:01:01 00:00:00")
        self.assertEqual(exif_date(path), datetime(2024, 3, 15, 10, 30, 0))

    def test_falls_back_to_datetime_when_original_missing(self):
        from phonesort.dates import exif_date
        path = self.write_jpeg("b.jpg", original=None, edited="2020:01:01 00:00:00")
        self.assertEqual(exif_date(path), datetime(2020, 1, 1, 0, 0, 0))

    def test_no_exif_returns_none(self):
        from phonesort.dates import exif_date
        path = self.write_jpeg("c.jpg", original=None, edited=None)
        self.assertIsNone(exif_date(path))

    def test_blank_exif_date_is_rejected(self):
        from phonesort.dates import exif_date
        path = self.write_jpeg("d.jpg", original="0000:00:00 00:00:00", edited=None)
        self.assertIsNone(exif_date(path))

    def test_exif_date_drives_folder_choice(self):
        from phonesort.dates import file_date
        path = self.write_jpeg("e.jpg", original="2024:03:15 10:30:00", edited=None)
        import os
        stamp = datetime(2026, 5, 5).timestamp()
        os.utime(path, (stamp, stamp))
        self.assertEqual(file_date(path), datetime(2024, 3, 15, 10, 30, 0))


class VideoDateTest(TempTreeTestCase):
    def test_mvhd_creation_time_is_read(self):
        created = datetime(2023, 7, 4, 18, 45, 30)
        path = self.src("clip.mp4", make_mp4(created))
        self.assertEqual(video_date(path), created)

    def test_udta_date_takes_precedence(self):
        path = self.src("clip.mov", make_mp4(datetime(2023, 7, 4, 18, 45, 30),
                                             udta_text="2021-12-25T08:15:00+0900"))
        self.assertEqual(video_date(path), datetime(2021, 12, 25, 8, 15, 0))

    def test_zero_creation_time_is_rejected(self):
        from helpers import QUICKTIME_EPOCH
        path = self.src("clip.mp4", make_mp4(QUICKTIME_EPOCH))
        self.assertIsNone(video_date(path))

    def test_garbage_file_returns_none(self):
        path = self.src("broken.mp4", b"not a real container at all")
        self.assertIsNone(video_date(path))

    def test_video_date_drives_folder_choice(self):
        """mtime 이 엉뚱해도 컨테이너 촬영일로 분류된다."""
        from phonesort.dates import file_date
        created = datetime(2022, 3, 9, 11, 0, 0)
        path = self.src("clip.mp4", make_mp4(created), mtime=datetime(2026, 1, 1))
        self.assertEqual(file_date(path), created)


if __name__ == "__main__":
    unittest.main()
