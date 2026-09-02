import unittest

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
