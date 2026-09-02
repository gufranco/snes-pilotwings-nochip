import struct
import unittest
from pathlib import Path
from typing import override

import commands
import exchanges

ROOT = Path(__file__).resolve().parent

COMMAND_SITE = 0x00000A
ANOTHER_SITE = 0x00001A
ARGUMENT_SITE = 0x000012
ANSWER_SITE = 0x000022


def write(pbpc: int, address: int, byte: int) -> bytes:
    return struct.pack("<IIHBB", 0, pbpc, address, 0, byte)


def read(pbpc: int, address: int, byte: int) -> bytes:
    return struct.pack("<IIHBB", 0, pbpc, address, 1, byte)


def issued(site: int, command: int) -> bytes:
    return write(site, commands.DATA_PORT, command)


def argued(site: int, word: int) -> bytes:
    return write(site, commands.DATA_PORT, word & 0xFF) + write(
        site, commands.DATA_PORT + 1, word >> 8
    )


def answered(site: int, word: int) -> bytes:
    return read(site, commands.DATA_PORT, word & 0xFF) + read(
        site, commands.DATA_PORT + 1, word >> 8
    )


def polled() -> bytes:
    return read(0x000030, exchanges.STATUS_BOUNDARY, 0x80)


def written_trace() -> Path:
    where = ROOT / "build" / "exchanges-test-trace.bin"
    where.parent.mkdir(exist_ok=True)
    where.write_bytes(issued(COMMAND_SITE, 0x13) + argued(ARGUMENT_SITE, 1))
    return where


class SitesTest(unittest.TestCase):
    def test_a_counter_that_only_touches_the_low_half_issued_a_command(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + argued(ARGUMENT_SITE, 0x1234)

        self.assertEqual(exchanges.issuing(trace), {COMMAND_SITE: 0x06})

    def test_a_counter_that_touches_both_halves_wrote_an_argument(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + argued(ARGUMENT_SITE, 0x1234)

        self.assertNotIn(ARGUMENT_SITE, exchanges.issuing(trace))

    def test_a_counter_that_only_reads_issued_nothing(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + answered(ANSWER_SITE, 0x0001)

        self.assertNotIn(ANSWER_SITE, exchanges.issuing(trace))

    def test_a_status_access_says_nothing_about_who_issued_what(self) -> None:
        trace = polled() + issued(COMMAND_SITE, 0x06)

        self.assertEqual(exchanges.issuing(trace), {COMMAND_SITE: 0x06})

    def test_a_counter_writing_two_different_bytes_is_not_a_command_site(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + issued(COMMAND_SITE, 0x13)

        self.assertNotIn(COMMAND_SITE, exchanges.issuing(trace))

    def test_a_trace_with_nothing_in_it_names_no_site(self) -> None:
        self.assertEqual(exchanges.issuing(b""), {})


class CutTest(unittest.TestCase):
    def test_an_exchange_runs_from_one_command_to_the_next(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 0x1111)
            + answered(ANSWER_SITE, 0x2222)
            + issued(ANOTHER_SITE, 0x13)
            + argued(ARGUMENT_SITE, 0x3333)
            + answered(ANSWER_SITE, 0x4444)
        )

        self.assertEqual(len(exchanges.taken(trace)), 2)

    def test_the_command_of_an_exchange_is_the_byte_its_site_wrote(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + argued(ARGUMENT_SITE, 0x1111)

        self.assertEqual(exchanges.taken(trace)[0].command, 0x06)

    def test_the_arguments_are_the_words_written_before_the_next_command(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 0x1111)
            + argued(ARGUMENT_SITE, 0x2222)
            + issued(ANOTHER_SITE, 0x13)
        )

        self.assertEqual(exchanges.taken(trace)[0].words, (0x1111, 0x2222))

    def test_a_read_in_the_middle_does_not_end_the_exchange(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x0A)
            + argued(ARGUMENT_SITE, 0x1111)
            + answered(ANSWER_SITE, 0x2222)
            + argued(ARGUMENT_SITE, 0x3333)
            + issued(ANOTHER_SITE, 0x13)
        )

        self.assertEqual(exchanges.taken(trace)[0].words, (0x1111, 0x3333))

    def test_that_is_the_shape_the_old_rule_could_not_read(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x0A)
            + argued(ARGUMENT_SITE, 0x1111)
            + answered(ANSWER_SITE, 0x2222)
            + argued(ARGUMENT_SITE, 0x3333)
            + issued(ANOTHER_SITE, 0x13)
        )

        self.assertEqual(len(exchanges.taken(trace)), 2)

    def test_the_answer_words_are_kept_with_the_exchange(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + answered(ANSWER_SITE, 0x2222)

        self.assertEqual(exchanges.taken(trace)[0].answer, (0x2222,))

    def test_a_status_poll_belongs_to_no_exchange(self) -> None:
        trace = issued(COMMAND_SITE, 0x06) + polled() + argued(ARGUMENT_SITE, 0x1111)

        self.assertEqual(exchanges.taken(trace)[0].words, (0x1111,))

    def test_anything_before_the_first_command_is_not_an_exchange(self) -> None:
        trace = argued(ARGUMENT_SITE, 0x9999) + issued(COMMAND_SITE, 0x06)

        self.assertEqual(len(exchanges.taken(trace)), 1)

    def test_an_exchange_names_the_site_that_issued_it(self) -> None:
        trace = issued(COMMAND_SITE, 0x06)

        self.assertEqual(exchanges.taken(trace)[0].site, COMMAND_SITE)

    def test_a_trace_with_no_command_yields_no_exchange(self) -> None:
        self.assertEqual(exchanges.taken(argued(ARGUMENT_SITE, 1)), ())


class CensusTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.trace = (
            issued(COMMAND_SITE, 0x13)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(COMMAND_SITE, 0x13)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(COMMAND_SITE, 0x13)
            + argued(ARGUMENT_SITE, 2)
            + answered(ANSWER_SITE, 8)
            + issued(ANOTHER_SITE, 0x00)
            + argued(ARGUMENT_SITE, 7)
            + argued(ARGUMENT_SITE, 8)
            + answered(ANSWER_SITE, 5)
        )

    def test_every_command_is_counted(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertEqual(set(taken.commands), {0x13, 0x00})

    def test_a_repeated_argument_set_counts_once_as_distinct(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertEqual(taken.distinct(0x13), 2)

    def test_a_repeated_argument_set_still_counts_as_traffic(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertEqual(taken.issued(0x13), 3)

    def test_a_command_never_issued_has_no_traffic(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertEqual(taken.issued(0x99), 0)

    def test_a_command_never_issued_has_no_argument_sets(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertEqual(taken.distinct(0x99), 0)

    def test_the_share_of_traffic_is_reported_per_command(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertAlmostEqual(taken.share(0x13), 0.75)

    def test_an_empty_census_has_no_share_for_anything(self) -> None:
        taken = exchanges.census(b"")

        self.assertEqual(taken.share(0x00), 0.0)

    def test_the_total_counts_every_exchange(self) -> None:
        self.assertEqual(exchanges.census(self.trace).total, 4)

    def test_the_sites_that_issue_a_command_are_reported(self) -> None:
        taken = exchanges.census(self.trace)

        self.assertEqual(taken.sites(0x13), (COMMAND_SITE,))

    def test_a_command_never_issued_has_no_sites(self) -> None:
        self.assertEqual(exchanges.census(self.trace).sites(0x99), ())

    def test_the_census_names_what_it_counted(self) -> None:
        self.assertIn("2 commands", repr(exchanges.census(self.trace)))

    def test_an_exchange_names_its_command(self) -> None:
        self.assertIn("$13", repr(exchanges.taken(self.trace)[0]))


class SpanTest(unittest.TestCase):
    def test_a_command_never_issued_has_no_spans(self) -> None:
        self.assertEqual(exchanges.spans(exchanges.census(b""), 0x13), ())

    def test_a_position_reports_the_ends_it_was_given(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x13)
            + argued(ARGUMENT_SITE, 10)
            + issued(ANOTHER_SITE, 0x13)
            + argued(ARGUMENT_SITE, 40)
        )
        found = exchanges.spans(exchanges.census(trace), 0x13)

        self.assertEqual((found[0].lowest, found[0].highest), (10, 40))

    def test_a_position_reports_how_many_values_it_saw(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x13)
            + argued(ARGUMENT_SITE, 10)
            + issued(ANOTHER_SITE, 0x13)
            + argued(ARGUMENT_SITE, 40)
        )
        found = exchanges.spans(exchanges.census(trace), 0x13)

        self.assertEqual(found[0].distinct, 2)

    def test_the_width_counts_both_ends(self) -> None:
        self.assertEqual(exchanges.Span(0, 10, 40, 2).width, 31)

    def test_the_bits_are_what_an_index_into_that_width_needs(self) -> None:
        self.assertEqual(exchanges.Span(0, 0, 255, 256).bits, 8)

    def test_a_single_value_still_needs_a_bit(self) -> None:
        self.assertEqual(exchanges.Span(0, 7, 7, 1).bits, 1)

    def test_a_position_filling_its_range_is_dense(self) -> None:
        self.assertTrue(exchanges.Span(0, 0, 9, 10).dense)

    def test_a_position_scattered_through_a_wide_range_is_not(self) -> None:
        self.assertFalse(exchanges.Span(0, 0, 65535, 12).dense)

    def test_every_position_of_a_command_is_reported(self) -> None:
        trace = issued(COMMAND_SITE, 0x00) + argued(ARGUMENT_SITE, 7) + argued(ARGUMENT_SITE, 8)

        self.assertEqual(len(exchanges.spans(exchanges.census(trace), 0x00)), 2)

    def test_the_index_adds_the_bits_of_every_position(self) -> None:
        trace = issued(COMMAND_SITE, 0x00) + argued(ARGUMENT_SITE, 7) + argued(ARGUMENT_SITE, 8)

        self.assertEqual(exchanges.index_bits(exchanges.census(trace), 0x00), 2)

    def test_a_command_never_issued_needs_no_index(self) -> None:
        self.assertEqual(exchanges.index_bits(exchanges.census(b""), 0x99), 0)

    def test_a_position_no_set_reached_is_left_out(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x13)
            + argued(ARGUMENT_SITE, 5)
            + argued(ARGUMENT_SITE, 6)
            + issued(ANOTHER_SITE, 0x13)
            + argued(ARGUMENT_SITE, 5)
        )
        found = exchanges.spans(exchanges.census(trace), 0x13)

        self.assertEqual([one.position for one in found], [0, 1])

    def test_a_span_names_the_position_and_its_ends(self) -> None:
        self.assertIn("10..40", repr(exchanges.Span(0, 10, 40, 2)))


class ReadingTest(unittest.TestCase):
    def test_a_command_whose_arguments_decide_it_is_pure(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x28)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(ANOTHER_SITE, 0x28)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
        )

        self.assertTrue(exchanges.readings((exchanges.taken(trace),), 0x28).pure)

    def test_a_command_answering_two_ways_for_one_set_is_not(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 8)
        )

        self.assertFalse(exchanges.readings((exchanges.taken(trace),), 0x06).pure)

    def test_a_carrier_that_settles_it_is_found(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x02)
            + argued(ARGUMENT_SITE, 100)
            + answered(ANSWER_SITE, 1)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(COMMAND_SITE, 0x02)
            + argued(ARGUMENT_SITE, 200)
            + answered(ANSWER_SITE, 1)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 8)
        )

        self.assertEqual(exchanges.readings((exchanges.taken(trace),), 0x06).carrier, 0x02)

    def test_a_command_settled_by_a_carrier_is_tabulatable(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x02)
            + argued(ARGUMENT_SITE, 100)
            + answered(ANSWER_SITE, 1)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(COMMAND_SITE, 0x02)
            + argued(ARGUMENT_SITE, 200)
            + answered(ANSWER_SITE, 1)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 8)
        )

        self.assertTrue(exchanges.readings((exchanges.taken(trace),), 0x06).tabulatable)

    def test_a_command_nothing_settles_says_so(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 8)
            + issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 7)
        )

        self.assertFalse(exchanges.readings((exchanges.taken(trace),), 0x06).tabulatable)

    def test_a_command_carrying_its_own_state_is_allowed_to(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(ANOTHER_SITE, 0x06)
            + argued(ARGUMENT_SITE, 2)
            + answered(ANSWER_SITE, 8)
            + issued(COMMAND_SITE, 0x06)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 7)
        )

        self.assertEqual(exchanges.readings((exchanges.taken(trace),), 0x06).carrier, 0x06)

    def test_a_pure_command_reports_a_row_per_set(self) -> None:
        trace = (
            issued(COMMAND_SITE, 0x28)
            + argued(ARGUMENT_SITE, 1)
            + answered(ANSWER_SITE, 9)
            + issued(ANOTHER_SITE, 0x28)
            + argued(ARGUMENT_SITE, 2)
            + answered(ANSWER_SITE, 8)
        )

        self.assertEqual(exchanges.readings((exchanges.taken(trace),), 0x28).rows, 2)

    def test_a_command_with_no_answer_is_pure_over_nothing(self) -> None:
        self.assertEqual(exchanges.readings(((),), 0x99).rows, 0)

    def test_the_reading_names_what_it_is_keyed_on(self) -> None:
        self.assertIn("arguments", repr(exchanges.Reading(0x06, None, 3, 0)))

    def test_a_keyed_reading_names_the_carrier(self) -> None:
        self.assertIn("$02", repr(exchanges.Reading(0x06, 0x02, 3, 0)))


class TierTest(unittest.TestCase):
    def test_a_command_asking_for_little_is_answered_in_line(self) -> None:
        self.assertEqual(exchanges.tier_of(0x13, 3), exchanges.INLINE)

    def test_the_multiply_is_computed_however_little_it_asks_for(self) -> None:
        self.assertEqual(exchanges.tier_of(exchanges.MULTIPLY, 1), exchanges.COMPUTED)

    def test_a_command_asking_for_a_lot_gets_a_table(self) -> None:
        self.assertEqual(exchanges.tier_of(0x06, 3000), exchanges.TABLE)

    def test_the_boundary_of_the_inline_chain_is_where_it_is_stated(self) -> None:
        self.assertEqual(exchanges.tier_of(0x06, exchanges.INLINE_LIMIT), exchanges.INLINE)

    def test_one_past_that_boundary_is_a_table(self) -> None:
        self.assertEqual(exchanges.tier_of(0x06, exchanges.INLINE_LIMIT + 1), exchanges.TABLE)


class ReportTest(unittest.TestCase):
    def test_a_census_of_nothing_still_reports(self) -> None:
        said = "\n".join(exchanges.report(exchanges.census(b"")))

        self.assertIn("exchanges", said)

    def test_the_report_opens_with_the_totals(self) -> None:
        taken = exchanges.census(issued(COMMAND_SITE, 0x13) + argued(ARGUMENT_SITE, 1))

        self.assertIn("exchanges", exchanges.report(taken)[0])

    def test_the_report_names_the_command_it_counted(self) -> None:
        taken = exchanges.census(issued(COMMAND_SITE, 0x13) + argued(ARGUMENT_SITE, 1))

        self.assertIn("$13", "\n".join(exchanges.report(taken)))

    def test_the_report_says_how_to_answer_it(self) -> None:
        taken = exchanges.census(issued(COMMAND_SITE, 0x13) + argued(ARGUMENT_SITE, 1))

        self.assertIn(exchanges.INLINE, "\n".join(exchanges.report(taken)))


class MainTest(unittest.TestCase):
    def test_running_it_with_no_recording_says_how_to_use_it(self) -> None:
        said: list[str] = []

        self.assertEqual(exchanges.main((), say=said.append), 2)

    def test_that_usage_line_names_the_command(self) -> None:
        said: list[str] = []

        exchanges.main((), say=said.append)

        self.assertIn("exchanges.py", said[0])

    def test_a_run_over_a_recording_exits_zero(self) -> None:
        said: list[str] = []

        self.assertEqual(exchanges.main((str(written_trace()),), say=said.append), 0)

    def test_a_run_prints_the_report(self) -> None:
        said: list[str] = []

        exchanges.main((str(written_trace()),), say=said.append)

        self.assertTrue(any("$13" in one for one in said))


class FileTest(unittest.TestCase):
    def test_a_recording_on_disk_is_read_the_same_as_one_in_hand(self) -> None:
        where = written_trace()

        self.assertEqual(exchanges.read(where).total, exchanges.census(where.read_bytes()).total)

    def test_the_stored_answers_cost_a_row_each(self) -> None:
        taken = exchanges.census(issued(COMMAND_SITE, 0x13) + argued(ARGUMENT_SITE, 1))

        self.assertEqual(taken.table_bytes(), exchanges.ANSWER_BYTES)


if __name__ == "__main__":
    unittest.main()
