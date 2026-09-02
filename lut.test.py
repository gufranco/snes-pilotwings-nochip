import struct
import unittest

import exchanges
import lut
import tables


class KernelTest(unittest.TestCase):
    def test_a_kernel_is_built_for_every_table_the_part_carries(self) -> None:
        self.assertEqual(len(lut.KERNELS), len(tables.KNOWN))

    def test_every_kernel_covers_the_whole_input(self) -> None:
        self.assertTrue(all(one.count == lut.FULL_DOMAIN for one in lut.KERNELS))

    def test_a_kernel_names_the_table_it_came_from(self) -> None:
        self.assertEqual({one.name for one in lut.KERNELS}, {one.name for one in tables.KNOWN})

    def test_a_kernel_says_what_it_occupies(self) -> None:
        self.assertEqual(lut.KERNELS[0].size, lut.FULL_DOMAIN * lut.BYTES_PER_ROW)

    def test_a_kernel_names_itself_and_its_size(self) -> None:
        self.assertIn(lut.KERNELS[0].name, repr(lut.KERNELS[0]))


class ExpandTest(unittest.TestCase):
    def test_expanding_gives_a_row_for_every_input(self) -> None:
        found = lut.expand(tables.KNOWN[0], count=256)

        self.assertEqual(len(found), 256)

    def test_the_first_row_is_the_table_s_first_entry(self) -> None:
        table = tables.KNOWN[0]
        found = lut.expand(table, count=256)

        self.assertEqual(found[0], lut.clamped(table.values()[0]))

    def test_a_value_too_large_for_a_row_saturates_rather_than_wrapping(self) -> None:
        self.assertEqual(lut.clamped(32768), lut.HIGHEST)

    def test_a_value_too_small_saturates_the_other_way(self) -> None:
        self.assertEqual(lut.clamped(-40000), lut.LOWEST)

    def test_a_value_that_fits_is_left_alone(self) -> None:
        self.assertEqual(lut.clamped(1234), 1234)

    def test_the_reciprocal_is_the_table_that_needs_it(self) -> None:
        table = next(one for one in tables.KNOWN if one.name == tables.RECIPROCAL)

        self.assertGreater(table.values()[0], lut.HIGHEST)

    def test_the_last_row_is_the_table_s_last_entry(self) -> None:
        table = tables.KNOWN[0]
        found = lut.expand(table, count=256)

        self.assertEqual(found[-1], table.values()[-1])

    def test_a_row_between_two_entries_sits_between_them(self) -> None:
        table = tables.KNOWN[1]
        found = lut.expand(table, count=512)
        low, high = sorted((table.values()[0], table.values()[1]))

        self.assertTrue(low <= found[2] <= high, (low, found[2], high))

    def test_expanding_to_the_table_s_own_length_returns_it(self) -> None:
        table = tables.KNOWN[1]

        self.assertEqual(lut.expand(table, count=table.count), table.values())

    def test_every_row_fits_in_a_signed_word(self) -> None:
        found = lut.expand(tables.KNOWN[2], count=1024)

        self.assertTrue(all(-32768 <= one <= 32767 for one in found))


class BlobTest(unittest.TestCase):
    def test_a_blob_holds_two_bytes_a_row(self) -> None:
        self.assertEqual(len(lut.blob(count=256)), len(tables.KNOWN) * 256 * 2)

    def test_a_blob_reads_back_as_the_rows_that_went_in(self) -> None:
        first = lut.expand(tables.KNOWN[0], count=256)

        self.assertEqual(lut.rows(lut.blob(count=256), 0, 256), first)

    def test_a_negative_row_survives_the_round_trip(self) -> None:
        cosine = next(one for one in tables.KNOWN if one.name == tables.COSINE)
        at = tables.KNOWN.index(cosine)
        wanted = lut.expand(cosine, count=256)

        self.assertEqual(lut.rows(lut.blob(count=256), at, 256), wanted)


class CostTest(unittest.TestCase):
    def test_the_whole_lut_is_four_tables_over_the_whole_input(self) -> None:
        self.assertEqual(lut.cost(), len(tables.KNOWN) * lut.FULL_DOMAIN * 2)

    def test_that_is_well_inside_what_a_flash_cartridge_holds(self) -> None:
        self.assertLess(lut.cost(), lut.CEILING)

    def test_the_image_it_needs_stays_inside_plain_lorom(self) -> None:
        self.assertLessEqual(lut.image_bytes(), lut.LOROM_CEILING)


class CoverageTest(unittest.TestCase):
    def test_every_input_a_command_can_offer_has_a_row(self) -> None:
        self.assertTrue(all(lut.covers(one) for one in (0, 1, 32767, 32768, 65535)))

    def test_nothing_outside_a_sixteen_bit_input_is_claimed(self) -> None:
        self.assertFalse(lut.covers(65536))

    def test_a_negative_index_is_not_claimed_either(self) -> None:
        self.assertFalse(lut.covers(-1))

    def test_the_fallback_is_reported_as_unreachable(self) -> None:
        self.assertEqual(lut.holes(), 0)


class ReportTest(unittest.TestCase):
    def test_the_report_says_what_the_lut_costs(self) -> None:
        self.assertIn("bytes", "\n".join(lut.report()))

    def test_the_report_says_no_input_can_miss(self) -> None:
        self.assertIn("no input", "\n".join(lut.report()))

    def test_the_report_names_every_kernel(self) -> None:
        said = "\n".join(lut.report())

        self.assertTrue(all(one.name in said for one in lut.KERNELS))


def recording(command: int, sets: list[tuple[int, ...]]) -> exchanges.Census:
    out = b""
    for at, words in enumerate(sets):
        site = 0x10 + (at % 2)
        out += struct.pack("<IIHBB", 0, site, exchanges.DATA_PORT, 0, command)
        for word in words:
            out += struct.pack("<IIHBB", 0, 0x40, exchanges.DATA_PORT, 0, word & 0xFF)
            out += struct.pack("<IIHBB", 0, 0x40, exchanges.DATA_PORT + 1, 0, word >> 8)
    return exchanges.census(out)


class PlanTest(unittest.TestCase):
    def test_a_narrow_range_is_answered_over_the_range(self) -> None:
        census = recording(0x13, [(1,), (2,), (3,)])

        self.assertEqual(lut.plan(census, 0x13).why, lut.ON_RANGE)

    def test_that_choice_says_no_input_inside_it_can_miss(self) -> None:
        census = recording(0x13, [(1,), (2,), (3,)])

        self.assertTrue(lut.plan(census, 0x13).complete)

    def test_a_range_too_wide_for_the_budget_falls_back_to_the_set(self) -> None:
        census = recording(0x13, [(0,), (65535,), (1000,)])

        self.assertEqual(lut.plan(census, 0x13, budget=1024).why, lut.ON_SET)

    def test_that_choice_says_an_unseen_argument_misses(self) -> None:
        census = recording(0x13, [(0,), (65535,), (1000,)])

        self.assertFalse(lut.plan(census, 0x13, budget=1024).complete)

    def test_the_range_is_preferred_even_when_it_costs_more(self) -> None:
        census = recording(0x13, [(0,), (255,)])

        self.assertEqual(lut.plan(census, 0x13).rows, 256)

    def test_a_wider_answer_costs_more_rows_worth_of_bytes(self) -> None:
        census = recording(0x13, [(0,), (255,)])

        self.assertEqual(lut.plan(census, 0x13, out=4).bytes_, 256 * 4 * lut.BYTES_PER_ROW)

    def test_a_command_with_no_arguments_still_gets_a_row(self) -> None:
        census = recording(0x80, [()])

        self.assertEqual(lut.plan(census, 0x80).rows, 1)

    def test_every_command_the_recording_saw_gets_a_choice(self) -> None:
        census = recording(0x13, [(1,), (2,)])

        self.assertEqual(len(lut.planned(census)), len(census.commands))

    def test_the_plan_adds_up_what_the_choices_cost(self) -> None:
        census = recording(0x13, [(1,), (2,)])
        choices = lut.planned(census)

        self.assertEqual(lut.planned_bytes(choices), sum(one.bytes_ for one in choices))

    def test_a_wider_answer_is_taken_from_the_widths_given(self) -> None:
        census = recording(0x13, [(0,), (255,)])

        self.assertEqual(lut.planned(census, widths={0x13: 4})[0].bytes_, 256 * 4 * 2)

    def test_a_budget_too_small_for_the_wider_table_keeps_the_set(self) -> None:
        census = recording(0x13, [(0,), (65535,)])

        self.assertFalse(lut.planned(census, budget=64)[0].complete)

    def test_a_budget_that_covers_it_takes_the_wider_table(self) -> None:
        census = recording(0x13, [(0,), (255,)])

        self.assertTrue(lut.planned(census, budget=4096)[0].complete)

    def test_the_plan_never_costs_more_than_the_budget(self) -> None:
        census = recording(0x13, [(0,), (65535,)])

        self.assertLessEqual(lut.planned_bytes(lut.planned(census, budget=4096)), 4096)

    def test_a_choice_names_the_command_and_its_size(self) -> None:
        census = recording(0x13, [(1,), (2,)])

        self.assertIn("$13", repr(lut.plan(census, 0x13)))


def run_of(
    pairs: list[tuple[int, tuple[int, ...], tuple[int, ...]]],
) -> tuple[exchanges.Exchange, ...]:
    return tuple(
        exchanges.Exchange(0x10, command, words, answer) for command, words, answer in pairs
    )


class TableTest(unittest.TestCase):
    def test_a_command_with_no_row_makes_an_empty_table(self) -> None:
        self.assertEqual(lut.table(((),), 0x13, None).rows, 0)

    def test_a_row_is_kept_for_every_key_the_run_held(self) -> None:
        run = run_of([(0x13, (1,), (9,)), (0x13, (2,), (8,))])

        self.assertEqual(lut.table((run,), 0x13, None).rows, 2)

    def test_the_same_key_twice_is_one_row(self) -> None:
        run = run_of([(0x13, (1,), (9,)), (0x13, (1,), (9,))])

        self.assertEqual(lut.table((run,), 0x13, None).rows, 1)

    def test_the_keys_come_out_sorted_for_a_binary_search(self) -> None:
        run = run_of([(0x13, (5,), (9,)), (0x13, (1,), (8,))])

        self.assertEqual(lut.table((run,), 0x13, None).keys, ((1,), (5,)))

    def test_the_answer_stays_with_its_key_through_the_sort(self) -> None:
        run = run_of([(0x13, (5,), (9,)), (0x13, (1,), (8,))])

        self.assertEqual(lut.table((run,), 0x13, None).answers, ((8,), (9,)))

    def test_a_carrier_widens_the_key(self) -> None:
        run = run_of([(0x02, (7,), (1,)), (0x13, (1,), (9,))])

        self.assertEqual(lut.table((run,), 0x13, 0x02).keys, ((1, 7),))

    def test_a_carrier_never_seen_leaves_the_key_narrow(self) -> None:
        run = run_of([(0x13, (1,), (9,))])

        self.assertEqual(lut.table((run,), 0x13, 0x02).keys, ((1,),))

    def test_a_short_key_is_padded_to_the_widest(self) -> None:
        run = run_of([(0x13, (1,), (9,)), (0x13, (2, 3), (8,))])
        built = lut.table((run,), 0x13, None)

        self.assertEqual(built.key_words, 2)

    def test_a_short_answer_is_padded_too(self) -> None:
        run = run_of([(0x13, (1,), (9,)), (0x13, (2,), (8, 7))])

        self.assertEqual(lut.table((run,), 0x13, None).answer_words, 2)

    def test_the_size_counts_keys_and_answers(self) -> None:
        run = run_of([(0x13, (1,), (9,)), (0x13, (2,), (8,))])
        built = lut.table((run,), 0x13, None)

        self.assertEqual(built.size, 2 * (1 + 1) * lut.KEY_WORD_BYTES)

    def test_a_table_names_its_command_and_size(self) -> None:
        run = run_of([(0x13, (1,), (9,))])

        self.assertIn("$13", repr(lut.table((run,), 0x13, None)))


class EncodeTest(unittest.TestCase):
    def test_the_encoding_opens_with_the_row_count(self) -> None:
        run = run_of([(0x13, (1,), (9,)), (0x13, (2,), (8,))])
        raw = lut.encode(lut.table((run,), 0x13, None))

        self.assertEqual(struct.unpack(">I", raw[:4])[0], 2)

    def test_it_then_says_how_wide_a_key_and_an_answer_are(self) -> None:
        run = run_of([(0x13, (1,), (9,))])
        raw = lut.encode(lut.table((run,), 0x13, None))

        self.assertEqual(struct.unpack(">HH", raw[4:8]), (1, 1))

    def test_a_width_past_a_byte_survives(self) -> None:
        run = run_of([(0x0A, (1,), tuple(range(300)))])
        raw = lut.encode(lut.table((run,), 0x0A, None))

        self.assertEqual(struct.unpack(">H", raw[6:8])[0], 300)

    def test_a_count_past_sixteen_bits_survives(self) -> None:
        run = run_of([(0x13, (one // 256, one % 256), (1,)) for one in range(70000)])
        raw = lut.encode(lut.table((run,), 0x13, None))

        self.assertEqual(struct.unpack(">I", raw[:4])[0], 70000)

    def test_the_keys_follow_in_order(self) -> None:
        run = run_of([(0x13, (5,), (9,)), (0x13, (1,), (8,))])
        raw = lut.encode(lut.table((run,), 0x13, None))

        self.assertEqual(struct.unpack(">HH", raw[8:12]), (1, 5))

    def test_the_answers_follow_the_keys(self) -> None:
        run = run_of([(0x13, (5,), (9,)), (0x13, (1,), (8,))])
        raw = lut.encode(lut.table((run,), 0x13, None))

        self.assertEqual(struct.unpack(">HH", raw[12:16]), (8, 9))

    def test_an_empty_table_still_encodes_a_header(self) -> None:
        self.assertEqual(len(lut.encode(lut.table(((),), 0x13, None))), 8)


class MainTest(unittest.TestCase):
    def test_running_it_prints_the_report(self) -> None:
        said: list[str] = []

        self.assertEqual(lut.main((), say=said.append), 0)

    def test_that_report_names_the_cost(self) -> None:
        said: list[str] = []

        lut.main((), say=said.append)

        self.assertTrue(any("bytes" in one for one in said))


if __name__ == "__main__":
    unittest.main()
