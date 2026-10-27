import tempfile
import unittest
from pathlib import Path

import derived

ROOT = Path(__file__).resolve().parent


class LeadingTest(unittest.TestCase):
    def test_it_counts_what_the_cartridge_loop_counts(self) -> None:
        for value, want in ((0x0000, 0), (0x0001, 14), (0x4000, 0), (0x8000, 0), (0xFFFF, 15)):
            self.assertEqual(derived.leading(value), want, hex(value))

    def test_no_count_reaches_past_a_byte(self) -> None:
        self.assertLessEqual(max(derived.leading(one) for one in range(0x10000)), 0xFF)

    def test_doubling_that_many_times_never_changes_the_sign(self) -> None:
        for value in (0x0001, 0x1234, 0x7FFF, 0x8001, 0xFFFE, 0xABCD):
            now = value
            for _ in range(derived.leading(value)):
                doubled = (now << 1) & 0xFFFF
                self.assertEqual(now & 0x8000, doubled & 0x8000, hex(value))
                now = doubled

    def test_one_more_doubling_always_would(self) -> None:
        for value in (0x0001, 0x1234, 0x7FFF, 0x8001, 0xFFFE, 0xABCD):
            now = value
            for _ in range(derived.leading(value)):
                now = (now << 1) & 0xFFFF
            self.assertNotEqual(now & 0x8000, (now << 1) & 0x8000, hex(value))

    def test_the_table_has_an_entry_for_every_word(self) -> None:
        raw = derived.counted()

        self.assertEqual(len(raw), 0x10000)
        self.assertEqual(raw[0x0001], 14)
        self.assertEqual(raw[0xFFFF], 15)

    def test_it_lands_in_pieces_no_larger_than_a_bank(self) -> None:
        into = Path(tempfile.mkdtemp())

        wrote = derived.write_bytes(into / "leading.bin", derived.counted())

        self.assertEqual(wrote, 0x10000)
        pieces = sorted(into.glob("leading-*.bin"))
        self.assertEqual([one.stat().st_size for one in pieces], [0x8000, 0x8000])


class SignedTest(unittest.TestCase):
    def test_a_word_below_the_halfway_point_stays_itself(self) -> None:
        self.assertEqual(derived.signed(0x1234), 0x1234)

    def test_a_word_above_it_reads_as_negative(self) -> None:
        self.assertEqual(derived.signed(0xFFFE), -2)


class ReindexTest(unittest.TestCase):
    def test_it_reads_the_pieces_it_wrote_earlier(self) -> None:
        into = ROOT / "build" / "derived-test"
        into.mkdir(parents=True, exist_ok=True)
        values = tuple(0x4000 + k % 0x3FFF for k in range(0x4000))
        derived.write(into / "reciprocal.bin", values)

        self.assertEqual(derived.pieces(into / "reciprocal.bin"), values)

    def test_a_missing_piece_is_reported_rather_than_read_as_short(self) -> None:
        into = ROOT / "build" / "derived-test"
        into.mkdir(parents=True, exist_ok=True)

        with self.assertRaises(FileNotFoundError):
            derived.pieces(into / "nothing.bin")


if __name__ == "__main__":
    unittest.main()
