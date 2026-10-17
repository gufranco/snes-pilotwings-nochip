import struct
import unittest
from pathlib import Path
from typing import Any

import complete
import exchanges
import hardware
import lutbuild

ROOT = Path(__file__).resolve().parent


ENTRY = lutbuild.HEADER + lutbuild.COMMAND_MAP


class HeaderTest(unittest.TestCase):
    def test_the_map_names_the_entry_that_answers_a_command(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1), 0x00: ((((2,), (8,)),), 1, 1)})

        self.assertEqual(raw[lutbuild.HEADER + 0x00], 0)
        self.assertEqual(raw[lutbuild.HEADER + 0x13], 1)

    def test_the_map_says_nothing_answers_a_command_the_table_lacks(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1)})

        self.assertEqual(raw[lutbuild.HEADER + 0x06], lutbuild.NO_ENTRY)

    def test_the_entry_says_where_the_answers_begin(self) -> None:
        rows = (((1,), (0xAAAA,)), ((2,), (0xBBBB,)))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})

        at = struct.unpack_from("<I", raw, ENTRY + 8)[0]
        answers = struct.unpack_from("<I", raw, ENTRY + 12)[0]
        self.assertEqual(answers, at + 4)
        self.assertEqual(struct.unpack_from("<H", raw, answers)[0], 0xAAAA)

    def test_an_odd_header_that_would_split_a_word_across_banks_is_refused(self) -> None:
        # Arrange
        held = lutbuild.HEADER
        lutbuild.HEADER = 1
        self.addCleanup(setattr, lutbuild, "HEADER", held)
        tables = {0x13: ((((1,), (9,)),), 1, 1)}

        # Act
        attempt = lambda: lutbuild.encode(tables)  # noqa: E731

        # Assert
        self.assertRaises(lutbuild.Uneven, attempt)

    def test_the_rows_begin_on_an_even_offset(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1)})

        self.assertEqual(struct.unpack_from("<I", raw, ENTRY + 8)[0] % 2, 0)

    def test_it_opens_with_the_command_count(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1)})

        self.assertEqual(raw[0], 1)

    def test_each_command_gets_an_entry_in_the_index(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1), 0x00: ((((2,), (8,)),), 1, 1)})

        self.assertEqual(raw[0], 2)

    def test_the_index_names_the_command_byte(self) -> None:
        raw = lutbuild.encode({0x13: ((((1,), (9,)),), 1, 1)})

        self.assertEqual(raw[ENTRY], 0x13)

    def test_the_index_carries_the_key_width(self) -> None:
        raw = lutbuild.encode({0x13: ((((1, 2), (9, 8, 7)),), 2, 3)})

        self.assertEqual(raw[ENTRY + 1], 2)

    def test_the_answer_width_reaches_past_a_byte(self) -> None:
        wide = tuple(range(764))
        raw = lutbuild.encode({0x0A: ((((1,), wide),), 1, 764)})

        self.assertEqual(struct.unpack_from("<H", raw, ENTRY + 2)[0], 764)

    def test_the_index_carries_the_row_count(self) -> None:
        rows = tuple(((one,), (one,)) for one in range(300))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})

        self.assertEqual(struct.unpack_from("<I", raw, ENTRY + 4)[0], 300)


class RowsTest(unittest.TestCase):
    def test_the_keys_come_before_the_answers(self) -> None:
        raw = lutbuild.encode({0x13: ((((0x1111,), (0x2222,)),), 1, 1)})
        at = struct.unpack_from("<I", raw, ENTRY + 8)[0]

        self.assertEqual(struct.unpack_from("<H", raw, at)[0], 0x1111)

    def test_the_answers_follow_every_key(self) -> None:
        rows = (((1,), (0xAAAA,)), ((2,), (0xBBBB,)))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})
        at = struct.unpack_from("<I", raw, ENTRY + 8)[0]

        self.assertEqual(struct.unpack_from("<H", raw, at + 4)[0], 0xAAAA)

    def test_the_keys_are_sorted_so_a_search_can_halve(self) -> None:
        rows = (((5,), (1,)), ((1,), (2,)))
        raw = lutbuild.encode({0x13: (rows, 1, 1)})
        at = struct.unpack_from("<I", raw, ENTRY + 8)[0]

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
        run = (_Exchange(0x0C, (1, 2), (9,)), _Exchange(0x0C, (3, 4), (8,)))

        _, key_words, answer_words = lutbuild.rows_of((run,))[0x0C]

        self.assertEqual((key_words, answer_words), (2, 1))

    def test_a_command_with_its_own_arithmetic_gets_no_rows(self) -> None:
        run = (_Exchange(0x00, (1, 2), (9,)),)

        self.assertEqual(lutbuild.rows_of((run,)), {})


class ChosenTest(unittest.TestCase):
    def test_what_fits_is_kept(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1)}

        self.assertEqual(lutbuild.chosen(built, {0x13: 100}, 1000), built)

    def test_what_does_not_fit_is_left_out(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1)}

        self.assertEqual(lutbuild.chosen(built, {0x13: 100}, 1), {})

    def test_the_busier_command_wins_the_room(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1), 0x28: ((((2,), (8,)),), 1, 1)}

        kept = lutbuild.chosen(built, {0x13: 1, 0x28: 100}, 4)

        self.assertEqual(list(kept), [0x28])


class WeighedTest(unittest.TestCase):
    def test_it_counts_the_answering_calls(self) -> None:
        run = (_Exchange(0x13, (1,), (9,)), _Exchange(0x13, (2,), (8,)))

        self.assertEqual(lutbuild.weighed((run,)), {0x13: 2})

    def test_a_call_with_no_answer_is_not_counted(self) -> None:
        run = (_Exchange(0x01, (1,), ()),)

        self.assertEqual(lutbuild.weighed((run,)), {})


class SizedTest(unittest.TestCase):
    def test_it_is_the_rows_times_the_words_in_each(self) -> None:
        self.assertEqual(lutbuild.sized(((None, None), (None, None)), 3, 2), 20)


class ReportTest(unittest.TestCase):
    def test_it_counts_the_commands(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1)}

        self.assertIn("1 commands", lutbuild.report(built, lutbuild.encode(built))[0])

    def test_it_names_every_command(self) -> None:
        built = {0x13: ((((1,), (9,)),), 1, 1)}

        lines = lutbuild.report(built, lutbuild.encode(built))

        self.assertTrue(any("$13" in one for one in lines))


class AxesTest(unittest.TestCase):
    def _built(self, keys: tuple[tuple[int, ...], ...], words: int) -> dict[int, Any]:
        return {0x13: (tuple((key, (0,)) for key in keys), words, 1)}

    def test_a_whole_product_is_found(self) -> None:
        keys = tuple((one, two) for one in (5, 9) for two in (1, 2, 3))

        found = lutbuild.axes(self._built(keys, 2))

        self.assertEqual(found, {0x13: ((5, 9), (1, 2, 3))})

    def test_a_set_with_a_combination_missing_is_not(self) -> None:
        keys = tuple((one, two) for one in (5, 9) for two in (1, 2, 3))[:-1]

        self.assertEqual(lutbuild.axes(self._built(keys, 2)), {})

    def test_a_command_with_no_rows_is_skipped(self) -> None:
        self.assertEqual(lutbuild.axes({0x13: ((), 2, 1)}), {})

    def test_a_stride_is_what_one_step_of_that_word_covers(self) -> None:
        self.assertEqual(lutbuild.strides(((5, 9), (1, 2, 3), (7,))), (3, 1, 1))

    def test_the_strides_of_one_word_are_one(self) -> None:
        self.assertEqual(lutbuild.strides(((5, 9, 11),)), (1,))

    def test_the_row_a_stride_names_is_the_row_the_key_sorts_to(self) -> None:
        values = ((5, 9), (1, 2, 3))
        keys = sorted(one for one in ((a, b) for a in values[0] for b in values[1]))

        for row, key in enumerate(keys):
            got = sum(
                values[at].index(word) * covered
                for at, (word, covered) in enumerate(
                    zip(key, lutbuild.strides(values), strict=True)
                )
            )
            self.assertEqual(got, row, key)

    def test_the_source_names_every_command_it_found(self) -> None:
        text = lutbuild.axes_source({0x13: ((5, 9), (1, 2, 3))})

        self.assertIn("lut_axes_dispatch:", text)
        self.assertIn("cmp.w #$0013", text)
        self.assertIn("jmp lut_axes_13", text)
        self.assertIn("lut_axes_13:", text)

    def test_it_compares_every_value_a_key_word_takes(self) -> None:
        text = lutbuild.axes_source({0x13: ((5, 9), (1, 2, 3))})

        for value in (5, 9, 1, 2, 3):
            self.assertIn(f"cmp.w #${value:04X}", text)

    def test_a_value_is_worth_its_position_times_the_stride(self) -> None:
        text = lutbuild.axes_source({0x13: ((5, 9), (1, 2, 3))})

        self.assertIn("adc.w #$0003", text)
        self.assertIn("adc.w #$0002", text)
        self.assertIn("adc.w #$0001", text)

    def test_the_first_value_of_a_word_adds_nothing(self) -> None:
        text = lutbuild.axes_source({0x13: ((5, 9),)})

        self.assertIn("adc.w #$0001", text)
        self.assertNotIn("adc.w #$0000", text)

    def test_a_value_no_row_carries_falls_to_the_search(self) -> None:
        text = lutbuild.axes_source({0x13: ((5, 9), (1, 2, 3))})

        self.assertIn("jmp lut_axes_none", text)
        self.assertIn("jml lut_find", text)

    def test_every_branch_it_writes_is_a_short_one(self) -> None:
        text = lutbuild.axes_source({0x13: (tuple(range(40)),)})

        rows = text.splitlines()
        for at, line in enumerate(rows):
            if not line.strip().startswith(("bne .", "beq .")):
                continue
            target = line.split()[1] + ":"
            landing = next(k for k, one in enumerate(rows) if one.startswith(target))
            self.assertLess(abs(landing - at) * 3, 120, line)

    def test_the_source_is_placed_where_the_assembly_expects(self) -> None:
        self.assertIn(f"org ${lutbuild.AXES_BANK:02X}8000", lutbuild.axes_source({}))


class BuildTest(unittest.TestCase):
    def test_it_writes_a_piece_and_a_map(self) -> None:
        into = ROOT / "build" / "lutbuild-test"
        real = lutbuild.gather

        def one_row(where: Path = ROOT, say: Any = None, mask: str = "") -> dict[int, Any]:
            return {0x13: ((((1,), (9,)),), 1, 1)}

        lutbuild.gather = one_row
        try:
            code = lutbuild.main(("dsp1", str(into)), say=lambda _: None)
        finally:
            lutbuild.gather = real

        self.assertEqual(code, 0)
        self.assertTrue((into / "lut-0.bin").exists())
        self.assertTrue((into / "lut-map.asm").exists())
        self.assertTrue((into / "lut-axes.asm").exists())


class MaskTest(unittest.TestCase):
    def test_the_mask_named_on_the_command_line_is_the_one_the_table_is_completed_with(
        self,
    ) -> None:
        # Arrange
        into = ROOT / "build" / "lutbuild-mask-test"
        asked: list[str] = []

        def one_row(where: Path = ROOT, say: Any = None, mask: str = "") -> dict[int, Any]:
            asked.append(mask)
            return {0x13: ((((1,), (9,)),), 1, 1)}

        self.addCleanup(setattr, lutbuild, "gather", lutbuild.gather)
        lutbuild.gather = one_row

        # Act
        lutbuild.main(("dsp1b", str(into)), say=lambda _: None)

        # Assert
        self.assertEqual(asked, ["dsp1b"])

    def test_completing_a_table_asks_the_part_for_that_mask(self) -> None:
        # Arrange
        named: list[str] = []
        real = complete.filled

        def record(
            command: int, keys: Any, answers: int, have: Any, mask: str = "", say: Any = None
        ) -> Any:
            named.append(mask)
            return dict(have)

        self.addCleanup(setattr, complete, "filled", real)
        complete.filled = record
        runs = (exchanges.taken(_trace()),)
        built = lutbuild.rows_of(runs)

        # Act
        lutbuild.completed(built, runs, mask="dsp1b")

        # Assert
        self.assertEqual(named, ["dsp1b"])


class _Loaded:
    def Chip(self, _mask: str) -> object:
        return object()


class GatherTest(unittest.TestCase):
    def test_it_reads_every_region_from_disk(self) -> None:
        # Arrange
        into = ROOT / "build" / "gather-test"
        into.mkdir(parents=True, exist_ok=True)
        for region in lutbuild.REGIONS:
            (into / f"trace-{region}.bin").write_bytes(_trace())
        self.addCleanup(setattr, hardware, "load", hardware.load)
        hardware.load = lambda package: _Loaded()

        # Act
        found = lutbuild.gather(into)

        # Assert
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
