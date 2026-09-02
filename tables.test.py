import math
import struct
import unittest
from pathlib import Path

import tables

ROOT = Path(__file__).resolve().parent


def image_of(words: dict[int, list[int]]) -> bytes:
    table = [0] * tables.TABLE_WORDS
    for at, run in words.items():
        table[at : at + len(run)] = run
    program = bytes(tables.PROGRAM_WORDS * tables.PROGRAM_BYTES_PER_WORD)
    return program + struct.pack(f">{tables.TABLE_WORDS}H", *(one & 0xFFFF for one in table))


def sine(count: int = 128) -> list[int]:
    return [round(math.sin(math.pi * k / 128) * 32767) for k in range(count)]


def cosine(count: int = 128) -> list[int]:
    return [round(math.cos(math.pi * k / 128) * 32767) for k in range(count)]


def written_image() -> Path:
    where = ROOT / "build" / "tables-test-image.bin"
    where.parent.mkdir(exist_ok=True)
    where.write_bytes(image_of({300: sine()}))
    return where


class WordsTest(unittest.TestCase):
    def test_an_image_is_read_as_program_then_table(self) -> None:
        self.assertEqual(len(tables.words(image_of({}))), tables.TABLE_WORDS)

    def test_a_table_word_is_read_big_endian(self) -> None:
        self.assertEqual(tables.words(image_of({0: [0x1234]}))[0], 0x1234)

    def test_an_image_of_the_wrong_length_is_refused(self) -> None:
        with self.assertRaises(tables.WrongShape):
            tables.words(b"\x00" * 16)


class KnownTest(unittest.TestCase):
    def test_the_part_is_expected_to_carry_four_numeric_tables(self) -> None:
        self.assertEqual(len(tables.KNOWN), 4)

    def test_every_known_table_names_itself(self) -> None:
        self.assertTrue(all(one.name for one in tables.KNOWN))

    def test_every_known_table_says_how_it_is_computed(self) -> None:
        self.assertTrue(all(one.formula for one in tables.KNOWN))

    def test_a_known_table_generates_the_values_it_describes(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.SINE)

        self.assertEqual(list(found.values()), sine())

    def test_the_reciprocal_is_the_one_the_part_indexes_from_128(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.RECIPROCAL)

        self.assertEqual(found.values()[0], 32768)


class FindTest(unittest.TestCase):
    def test_a_table_the_image_carries_is_found_at_its_offset(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.SINE)

        self.assertEqual(tables.find(tables.words(image_of({300: sine()})), found), 300)

    def test_a_table_the_image_does_not_carry_is_not_found(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.SINE)

        self.assertIsNone(tables.find(tables.words(image_of({})), found))

    def test_a_table_off_by_one_unit_is_still_found(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.SINE)
        nudged = [one - 1 for one in sine()]

        self.assertEqual(tables.find(tables.words(image_of({300: nudged})), found), 300)

    def test_a_table_off_by_more_than_the_tolerance_is_not_found(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.SINE)
        wrong = [one + 40 for one in sine()]

        self.assertIsNone(tables.find(tables.words(image_of({300: wrong})), found))

    def test_a_signed_table_is_read_as_signed(self) -> None:
        found = next(one for one in tables.KNOWN if one.name == tables.COSINE)

        self.assertEqual(tables.find(tables.words(image_of({400: cosine()})), found), 400)


class CarriedTest(unittest.TestCase):
    def test_an_image_carrying_nothing_carries_nothing(self) -> None:
        self.assertEqual(tables.carried(image_of({})), {})

    def test_an_image_carrying_a_table_reports_where_it_sits(self) -> None:
        found = tables.carried(image_of({100: sine(), 400: cosine()}))

        self.assertEqual(found, {tables.SINE: 100, tables.COSINE: 400})

    def test_a_table_moved_is_still_the_same_table(self) -> None:
        first = tables.carried(image_of({300: sine()}))
        moved = tables.carried(image_of({302: sine()}))

        self.assertEqual(set(first), set(moved))

    def test_two_images_agreeing_on_content_and_not_on_place_are_said_to(self) -> None:
        first = tables.carried(image_of({300: sine()}))
        moved = tables.carried(image_of({302: sine()}))

        self.assertNotEqual(first, moved)


class CostTest(unittest.TestCase):
    def test_the_tables_cost_what_their_words_cost(self) -> None:
        self.assertEqual(tables.table_bytes(), sum(one.count for one in tables.KNOWN) * 2)

    def test_that_is_far_less_than_one_table_over_a_whole_input(self) -> None:
        self.assertLess(tables.table_bytes(), tables.WHOLE_INPUT_BYTES)


class ReportTest(unittest.TestCase):
    def test_the_report_names_a_table_the_image_carries(self) -> None:
        said = "\n".join(tables.report(image_of({300: sine()})))

        self.assertIn(tables.SINE, said)

    def test_the_report_says_where_it_sits(self) -> None:
        said = "\n".join(tables.report(image_of({300: sine()})))

        self.assertIn("300", said)

    def test_the_report_says_when_a_table_is_absent(self) -> None:
        said = "\n".join(tables.report(image_of({})))

        self.assertIn("not carried", said)

    def test_the_report_ends_with_what_the_tables_cost(self) -> None:
        said = "\n".join(tables.report(image_of({300: sine()})))

        self.assertIn("bytes", said)


class MainTest(unittest.TestCase):
    def test_running_it_with_no_image_says_how_to_use_it(self) -> None:
        said: list[str] = []

        self.assertEqual(tables.main((), say=said.append), 2)

    def test_that_usage_line_names_the_command(self) -> None:
        said: list[str] = []

        tables.main((), say=said.append)

        self.assertIn("tables.py", said[0])

    def test_a_run_over_an_image_exits_zero(self) -> None:
        said: list[str] = []

        self.assertEqual(tables.main((str(written_image()),), say=said.append), 0)

    def test_a_run_prints_the_report(self) -> None:
        said: list[str] = []

        tables.main((str(written_image()),), say=said.append)

        self.assertTrue(any(tables.SINE in one for one in said))


class FileTest(unittest.TestCase):
    def test_an_image_on_disk_is_read_the_same_as_one_in_hand(self) -> None:
        where = written_image()

        self.assertEqual(tables.read(where), tables.carried(where.read_bytes()))


class TableReprTest(unittest.TestCase):
    def test_a_table_names_itself_and_its_formula(self) -> None:
        self.assertIn(tables.SINE, repr(tables.KNOWN[1]))


if __name__ == "__main__":
    unittest.main()
