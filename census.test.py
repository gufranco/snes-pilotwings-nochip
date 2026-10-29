import struct
import unittest
from pathlib import Path
from typing import override

import census
import script

ROOT = Path(__file__).resolve().parent


def record(frame: int, address: int, is_read: int, byte: int) -> bytes:
    return struct.pack("<IIHBB", frame, 0, address, is_read, byte)


def written(command: int, words: tuple[int, ...]) -> bytes:
    out = record(0, census.DATA_PORT, 0, command)
    for word in words:
        out += record(0, census.DATA_PORT, 0, word & 0xFF)
        out += record(0, census.DATA_PORT + 1, 0, word >> 8)
    return out


def answered(words: int = 1) -> bytes:
    out = b""
    for _ in range(words):
        out += record(0, census.DATA_PORT, 1, 0x00)
        out += record(0, census.DATA_PORT + 1, 1, 0x00)
    return out


def polled() -> bytes:
    return record(0, census.STATUS_BOUNDARY, 1, 0x80) + record(
        0, census.STATUS_BOUNDARY + 1, 1, 0x80
    )


class ReadTest(unittest.TestCase):
    def test_a_trace_with_nothing_in_it_yields_no_exchange(self) -> None:
        self.assertEqual(list(census.exchanges(b"")), [])

    def test_one_command_followed_by_a_read_is_one_exchange(self) -> None:
        trace = written(0x00, (0x1234, 0x5678)) + answered() + written(0x01, ()) + answered()

        self.assertEqual(len(list(census.exchanges(trace))), 2)

    def test_the_command_byte_is_the_first_thing_written(self) -> None:
        trace = written(0x06, (0x1111,)) + answered() + written(0x01, ()) + answered()

        self.assertEqual(next(iter(census.exchanges(trace))).command, 0x06)

    def test_the_argument_words_are_recovered_little_endian(self) -> None:
        trace = written(0x00, (0x1234, 0x5678)) + answered() + written(0x01, ()) + answered()

        self.assertEqual(next(iter(census.exchanges(trace))).words, (0x1234, 0x5678))

    def test_an_access_to_the_status_register_is_not_part_of_the_exchange(self) -> None:
        trace = polled() + written(0x00, (0x1234,)) + answered() + written(0x01, ()) + answered()

        self.assertEqual(next(iter(census.exchanges(trace))).words, (0x1234,))

    def test_a_poll_in_the_middle_of_a_run_does_not_end_the_exchange(self) -> None:
        trace = (
            written(0x00, (0x1234,))
            + polled()
            + record(0, census.DATA_PORT, 0, 0x78)
            + record(0, census.DATA_PORT + 1, 0, 0x56)
            + answered()
        )

        self.assertEqual(next(iter(census.exchanges(trace))).words, (0x1234, 0x5678))

    def test_the_high_byte_of_an_argument_word_is_kept(self) -> None:
        trace = written(0x00, (0xFF00,)) + answered()

        self.assertEqual(next(iter(census.exchanges(trace))).words, (0xFF00,))

    def test_a_command_never_followed_by_a_read_is_not_counted(self) -> None:
        self.assertEqual(list(census.exchanges(written(0x00, (1,)))), [])


class CensusTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.trace = (
            written(0x13, (1,))
            + answered()
            + written(0x13, (1,))
            + answered()
            + written(0x13, (2,))
            + answered()
            + written(0x00, (7, 8))
            + answered()
            + written(0x01, ())
            + answered()
        )

    def test_every_command_the_trace_used_is_counted(self) -> None:
        taken = census.taken(self.trace)

        self.assertEqual(set(taken.commands), {0x13, 0x00, 0x01})

    def test_a_repeated_argument_set_is_counted_once_as_distinct(self) -> None:
        taken = census.taken(self.trace)

        self.assertEqual(taken.distinct(0x13), 2)

    def test_a_repeated_argument_set_is_still_counted_twice_as_traffic(self) -> None:
        taken = census.taken(self.trace)

        self.assertEqual(taken.exchanges(0x13), 3)

    def test_the_total_counts_every_exchange(self) -> None:
        taken = census.taken(self.trace)

        self.assertEqual(taken.total, 5)

    def test_a_command_the_trace_never_used_has_no_traffic(self) -> None:
        taken = census.taken(self.trace)

        self.assertEqual(taken.exchanges(0x99), 0)

    def test_the_share_of_traffic_is_reported_per_command(self) -> None:
        taken = census.taken(self.trace)

        self.assertAlmostEqual(taken.share(0x13), 0.6)

    def test_a_command_with_no_traffic_has_no_share(self) -> None:
        taken = census.taken(self.trace)

        self.assertEqual(taken.share(0x99), 0.0)

    def test_an_empty_census_has_no_share_for_anything(self) -> None:
        taken = census.taken(b"")

        self.assertEqual(taken.share(0x00), 0.0)


class SizingTest(unittest.TestCase):
    def test_a_table_row_holds_one_answer(self) -> None:
        self.assertEqual(census.table_bytes(1), census.ANSWER_BYTES)

    def test_a_table_is_a_row_per_distinct_set(self) -> None:
        self.assertEqual(census.table_bytes(100), 100 * census.ANSWER_BYTES)

    def test_the_whole_observed_set_is_sized_from_the_census(self) -> None:
        trace = written(0x13, (1,)) + answered() + written(0x01, ()) + answered()

        self.assertEqual(census.taken(trace).table_bytes(), census.ANSWER_BYTES * 2)


class ReprTest(unittest.TestCase):
    def test_an_exchange_names_its_command(self) -> None:
        self.assertIn("$06", repr(census.Exchange(0x06, (1, 2))))

    def test_a_census_names_how_much_it_counted(self) -> None:
        taken = census.taken(written(0x13, (1,)) + answered())

        self.assertIn("1 commands", repr(taken))


class FileTest(unittest.TestCase):
    def test_a_recording_on_disk_is_read_the_same_as_one_in_hand(self) -> None:
        trace = written(0x13, (1,)) + answered()
        where = ROOT / "build" / "census-test-trace.bin"
        where.parent.mkdir(exist_ok=True)
        where.write_bytes(trace)

        self.assertEqual(census.read(where).total, census.taken(trace).total)


class ReportTest(unittest.TestCase):
    def test_the_report_names_every_command_counted(self) -> None:
        taken = census.taken(written(0x13, (1,)) + answered() + written(0x06, (2,)) + answered())

        said = "\n".join(census.report(taken))

        self.assertIn("$13", said)

    def test_the_report_says_how_to_answer_each_one(self) -> None:
        taken = census.taken(written(0x13, (1,)) + answered())

        said = "\n".join(census.report(taken))

        self.assertIn(census.INLINE, said)

    def test_the_report_opens_with_the_totals(self) -> None:
        taken = census.taken(written(0x13, (1,)) + answered())

        self.assertIn("exchanges", census.report(taken)[0])


class MainTest(unittest.TestCase):
    def test_running_it_with_no_recording_says_how_to_use_it(self) -> None:
        said: list[str] = []

        code = census.main((), say=said.append)

        self.assertEqual(code, 2)

    def test_that_usage_line_names_the_command(self) -> None:
        said: list[str] = []

        census.main((), say=said.append)

        self.assertIn("census.py", said[0])

    def test_a_run_over_a_recording_exits_zero(self) -> None:
        where = ROOT / "build" / "census-main-trace.bin"
        where.parent.mkdir(exist_ok=True)
        where.write_bytes(written(0x13, (1,)) + answered())
        said: list[str] = []

        code = census.main((str(where),), say=said.append)

        self.assertEqual(code, 0)

    def test_a_run_prints_the_report(self) -> None:
        where = ROOT / "build" / "census-main-trace.bin"
        where.parent.mkdir(exist_ok=True)
        where.write_bytes(written(0x13, (1,)) + answered())
        said: list[str] = []

        census.main((str(where),), say=said.append)

        self.assertTrue(any("$13" in one for one in said))


class TierTest(unittest.TestCase):
    def test_a_command_varying_barely_is_an_inline_chain(self) -> None:
        self.assertEqual(census.tier_of(0x13, 3), census.INLINE)

    def test_the_multiply_is_computed_rather_than_stored(self) -> None:
        self.assertEqual(census.tier_of(census.MULTIPLY, 13775), census.COMPUTED)

    def test_a_command_varying_a_lot_gets_a_table(self) -> None:
        self.assertEqual(census.tier_of(0x06, 2995), census.TABLE)

    def test_the_boundary_of_the_inline_chain_is_where_it_is_stated(self) -> None:
        self.assertEqual(census.tier_of(0x06, census.INLINE_LIMIT), census.INLINE)

    def test_one_past_that_boundary_is_a_table(self) -> None:
        self.assertEqual(census.tier_of(0x06, census.INLINE_LIMIT + 1), census.TABLE)


script.entry(__name__, unittest.main)
