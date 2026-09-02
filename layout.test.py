import unittest
from pathlib import Path

import layout

ROOT = Path(__file__).resolve().parent


def image(*parts: bytes) -> bytes:
    return b"".join(parts)


def written_image() -> Path:
    where = ROOT / "build" / "layout-test-image.bin"
    where.parent.mkdir(exist_ok=True)
    where.write_bytes(image(bytes([1]), b"\xff" * 1024))
    return where


class RunsTest(unittest.TestCase):
    def test_an_image_of_nothing_but_code_has_no_free_run(self) -> None:
        self.assertEqual(layout.runs(bytes(range(64)), least=8), ())

    def test_a_run_of_the_filler_is_found(self) -> None:
        found = layout.runs(image(bytes([1]), b"\xff" * 32, bytes([2])), least=8)

        self.assertEqual(found, ((1, 33),))

    def test_a_run_shorter_than_the_floor_is_not_worth_reporting(self) -> None:
        self.assertEqual(layout.runs(image(bytes([1]), b"\xff" * 4, bytes([2])), least=8), ())

    def test_a_run_reaching_the_end_of_the_image_is_found(self) -> None:
        found = layout.runs(image(bytes([1]), b"\xff" * 32), least=8)

        self.assertEqual(found, ((1, 33),))

    def test_the_other_filler_is_found_too(self) -> None:
        found = layout.runs(image(bytes([1]), b"\x00" * 32, bytes([2])), least=8)

        self.assertEqual(found, ((1, 33),))

    def test_two_fillers_meeting_are_two_runs_rather_than_one(self) -> None:
        found = layout.runs(image(b"\xff" * 16, b"\x00" * 16), least=8)

        self.assertEqual(len(found), 2)

    def test_a_caller_may_name_the_filler_it_means(self) -> None:
        found = layout.runs(image(b"\xff" * 32), least=8, fillers=(0x00,))

        self.assertEqual(found, ())


class FreeTest(unittest.TestCase):
    def test_the_free_bytes_are_the_runs_added_up(self) -> None:
        rom = image(bytes([1]), b"\xff" * 32, bytes([2]), b"\x00" * 16)

        self.assertEqual(layout.free(rom, least=8), 48)

    def test_an_image_with_no_run_has_nothing_free(self) -> None:
        self.assertEqual(layout.free(bytes(range(64)), least=8), 0)

    def test_the_largest_run_is_the_one_a_blob_has_to_fit_in(self) -> None:
        rom = image(bytes([1]), b"\xff" * 32, bytes([2]), b"\x00" * 48)

        self.assertEqual(layout.largest(rom, least=8), 48)

    def test_an_image_with_no_run_has_no_largest(self) -> None:
        self.assertEqual(layout.largest(bytes(range(64)), least=8), 0)


class FitsTest(unittest.TestCase):
    def test_a_blob_smaller_than_a_run_fits_in_one_piece(self) -> None:
        rom = image(bytes([1]), b"\xff" * 64)

        self.assertTrue(layout.fits(rom, 32, least=8))

    def test_a_blob_larger_than_every_run_does_not(self) -> None:
        rom = image(bytes([1]), b"\xff" * 16, bytes([2]), b"\x00" * 16)

        self.assertFalse(layout.fits(rom, 32, least=8))

    def test_a_blob_the_size_of_a_run_still_fits(self) -> None:
        rom = image(bytes([1]), b"\xff" * 32)

        self.assertTrue(layout.fits(rom, 32, least=8))

    def test_a_blob_larger_than_one_run_may_still_fit_across_several(self) -> None:
        rom = image(bytes([1]), b"\xff" * 16, bytes([2]), b"\x00" * 16)

        self.assertTrue(layout.spread(rom, 32, least=8))

    def test_a_blob_larger_than_everything_free_fits_nowhere(self) -> None:
        rom = image(bytes([1]), b"\xff" * 16)

        self.assertFalse(layout.spread(rom, 64, least=8))


class GrowsTest(unittest.TestCase):
    def test_an_image_with_room_does_not_need_to_grow(self) -> None:
        rom = image(bytes([1]), b"\xff" * 64)

        self.assertFalse(layout.must_grow(rom, 32, least=8))

    def test_an_image_without_room_does(self) -> None:
        rom = image(bytes([1]), b"\xff" * 16)

        self.assertTrue(layout.must_grow(rom, 64, least=8))


class ReportTest(unittest.TestCase):
    def test_the_report_says_how_much_is_free(self) -> None:
        said = "\n".join(layout.report(image(bytes([1]), b"\xff" * 64), 32, least=8))

        self.assertIn("free", said)

    def test_the_report_says_whether_the_image_has_to_grow(self) -> None:
        said = "\n".join(layout.report(image(bytes([1]), b"\xff" * 64), 32, least=8))

        self.assertIn("does not have to grow", said)

    def test_the_report_says_so_when_it_does(self) -> None:
        said = "\n".join(layout.report(image(bytes([1]), b"\xff" * 16), 64, least=8))

        self.assertIn("has to grow", said)

    def test_the_report_names_the_largest_run(self) -> None:
        said = "\n".join(layout.report(image(bytes([1]), b"\xff" * 64), 32, least=8))

        self.assertIn("largest", said)


class MainTest(unittest.TestCase):
    def test_running_it_with_no_image_says_how_to_use_it(self) -> None:
        said: list[str] = []

        self.assertEqual(layout.main((), say=said.append), 2)

    def test_that_usage_line_names_the_command(self) -> None:
        said: list[str] = []

        layout.main((), say=said.append)

        self.assertIn("layout.py", said[0])

    def test_a_run_over_an_image_exits_zero(self) -> None:
        said: list[str] = []

        self.assertEqual(layout.main((str(written_image()), "32"), say=said.append), 0)

    def test_a_run_prints_what_it_found(self) -> None:
        said: list[str] = []

        layout.main((str(written_image()), "32"), say=said.append)

        self.assertTrue(any("free" in one for one in said))


if __name__ == "__main__":
    unittest.main()
