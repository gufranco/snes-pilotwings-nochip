import struct
import unittest
from pathlib import Path
from typing import Any

import lutbuild

ROOT = Path(__file__).resolve().parent


class HeaderTest(unittest.TestCase):
    def test_it_opens_with_the_command_count(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1)})

        self.assertEqual(raw[0], 1)

    def test_each_command_gets_an_entry_in_the_index(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1), 0x00: ((((2,), (8,)),), 1, 1)})

        self.assertEqual(raw[0], 2)

    def test_the_index_names_the_command_byte(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1)})

        self.assertEqual(raw[1], 0x13)

    def test_the_index_carries_the_key_width(self) -> None:
        raw = lutbuild.encode({0x13: ((((1, 2), (9, 8, 7)),), 2, 3)})

        self.assertEqual(raw[2], 2)

    def test_the_answer_width_reaches_past_a_byte(self) -> None:
        wide = tuple(range(764))
        raw = lutbuild.encode({0x0A: ((((1,), wide),), 1, 764)})

        self.assertEqual(struct.unpack_from("<H", raw, lutbuild.HEADER + 2)[0], 764)

    def test_the_index_carries_the_row_count(self) -> None:
        rows = tuple(((one,), (one,)) for one in range(300))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})

        self.assertEqual(struct.unpack_from("<I", raw, lutbuild.HEADER + 4)[0], 300)


class RowsTest(unittest.TestCase):
    def test_the_keys_come_before_the_answers(self) -> None:
        raw = lutbuild.encode({0x13: ((((0x1111,), (0x2222,)),), 1, 1)})
        at = struct.unpack_from("<I", raw, lutbuild.HEADER + 8)[0]

        self.assertEqual(struct.unpack_from("<H", raw, at)[0], 0x1111)

    def test_the_answers_follow_every_key(self) -> None:
        rows = (((1,), (0xAAAA,)), ((2,), (0xBBBB,)))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})
        at = struct.unpack_from("<I", raw, lutbuild.HEADER + 8)[0]

        self.assertEqual(struct.unpack_from("<H", raw, at + 4)[0], 0xAAAA)

    def test_the_keys_are_sorted_so_a_search_can_halve(self) -> None:
        rows = (((5,), (1,)), ((1,), (2,)))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})
        at = struct.unpack_from("<I", raw, lutbuild.HEADER + 8)[0]

        self.assertEqual(struct.unpack_from("<HH", raw, at), (1, 5))


class SliceTest(unittest.TestCase):
    def test_a_short_table_lands_in_one_piece(self) -> None:
        pieces = lutbuild.sliced(b"\x01\x02\x03")

        self.assertEqual(len(pieces), 1)

    def test_a_long_table_is_cut_at_the_bank_border(self) -> None:
        pieces = lutbuild.sliced(bytes(lutbuild.BANK_BYTES + 4))

        self.assertEqual(len(pieces), 2)

    def test_no_piece_is_longer_than_a_bank(self) -> None:
        for piece in lutbuild.sliced(bytes(lutbuild.BANK_BYTES * 3 + 7)):
            self.assertLessEqual(len(piece), lutbuild.BANK_BYTES)


class SourceTest(unittest.TestCase):
    def test_it_names_every_piece(self) -> None:
        text = lutbuild.source(3, first_bank=0x30)

        self.assertEqual(text.count("incbin"), 3)

    def test_each_piece_gets_its_own_bank(self) -> None:
        text = lutbuild.source(2, first_bank=0x30)

        self.assertIn("org $308000", text)
        self.assertIn("org $318000", text)

    def test_it_labels_where_the_table_begins(self) -> None:
        self.assertIn("dsp1_lut:", lutbuild.source(1, first_bank=0x30))


class BankTest(unittest.TestCase):
    def test_pieces_take_consecutive_banks(self) -> None:
        self.assertEqual(lutbuild.banks(3, 0x30), (0x30, 0x31, 0x32))

    def test_the_two_memory_banks_are_stepped_over(self) -> None:
        found = lutbuild.banks(4, 0x7C)

        self.assertEqual(found, (0x7C, 0x7D, 0x80, 0x81))

    def test_no_piece_lands_in_memory(self) -> None:
        for bank in lutbuild.banks(120, 0x30):
            self.assertNotIn(bank, lutbuild.WORK_RAM)


class _Exchange:
    def __init__(self, command: int, words: tuple[int, ...], answer: tuple[int, ...]) -> None:
        self.command = command
        self.words = words
        self.answer = answer


class RowsOfTest(unittest.TestCase):
    def test_a_command_that_answers_gets_rows(self) -> None:
        run = (_Exchange(0x13, (1,), (9,)),)

        found = lutbuild.rows_of((run,))

        self.assertIn(0x13, found)

    def test_a_command_that_answers_nothing_is_left_out(self) -> None:
        run = (_Exchange(0x01, (1, 2, 3, 4), ()),)

        self.assertEqual(lutbuild.rows_of((run,)), {})

    def test_the_same_key_twice_is_one_row(self) -> None:
        run = (_Exchange(0x13, (1,), (9,)), _Exchange(0x13, (1,), (9,)))

        rows, _, _ = lutbuild.rows_of((run,))[0x13]

        self.assertEqual(len(rows), 1)

    def test_a_carrier_widens_the_key(self) -> None:
        run = (_Exchange(0x11, (7, 8, 9, 10), ()), _Exchange(0x13, (1, 2, 3), (9, 8, 7)))

        _, key_words, _ = lutbuild.rows_of((run,))[0x13]

        self.assertEqual(key_words, 7)

    def test_the_widths_are_the_widest_seen(self) -> None:
        run = (_Exchange(0x00, (1, 2), (9,)), _Exchange(0x00, (3, 4), (8,)))

        _, key_words, answer_words = lutbuild.rows_of((run,))[0x00]

        self.assertEqual((key_words, answer_words), (2, 1))


class ReportTest(unittest.TestCase):
    def test_it_counts_the_commands(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1)}

        self.assertIn("1 commands", lutbuild.report(built, lutbuild.encode(built))[0])

    def test_it_names_every_command(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1)}

        lines = lutbuild.report(built, lutbuild.encode(built))

        self.assertTrue(any("$13" in one for one in lines))


class BuildTest(unittest.TestCase):
    def test_it_writes_a_piece_and_a_map(self) -> None:
        into = ROOT / "build" / "lutbuild-test"
        real = lutbuild.gather

        def one_row(where: Path = ROOT, say: Any = None) -> dict[int, Any]:
            return {0x13: ((((1,), (9,)),), 1, 1)}

        lutbuild.gather = one_row
        try:
            code = lutbuild.main(("dsp1", str(into)), say=lambda _: None)
        finally:
            lutbuild.gather = real

        self.assertEqual(code, 0)
        self.assertTrue((into / "lut-0.bin").exists())
        self.assertTrue((into / "lut-map.asm").exists())


class GatherTest(unittest.TestCase):
    def test_it_reads_every_region_from_disk(self) -> None:
        into = ROOT / "build" / "gather-test"
        into.mkdir(parents=True, exist_ok=True)
        for region in lutbuild.REGIONS:
            (into / f"trace-{region}.bin").write_bytes(_trace())

        found = lutbuild.gather(into)

        self.assertIn(0x13, found)


def _trace() -> bytes:
    records = [
        (0, 0x1000, 0x8000, 0, 0x13),
        (0, 0x1004, 0x8000, 0, 0x01),
        (0, 0x1004, 0x8001, 0, 0x00),
        (0, 0x1008, 0x8000, 1, 0x09),
        (0, 0x1008, 0x8001, 1, 0x00),
    ]
    return b"".join(struct.pack("<IIHBB", *one) for one in records)


class MainTest(unittest.TestCase):
    def test_with_no_mask_it_says_so(self) -> None:
        said: list[str] = []

        self.assertEqual(lutbuild.main((), say=said.append), 2)

    def test_with_no_mask_it_prints_a_usage_line(self) -> None:
        said: list[str] = []

        lutbuild.main((), say=said.append)

        self.assertTrue(said)


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "lutbuild.py").exists())


if __name__ == "__main__":
    unittest.main()
