import unittest

import raster


def lookup() -> dict[int, tuple[int, int]]:
    """The reciprocal the part hands back, for the distances measured from it.

    Taken by watching a live `$0a`, so these are the part's own values rather
    than a reading of what its instructions ought to produce. Every entry here
    sits inside the table's own octave, where no folding happens; the folded
    range is measured by `derive.py` rather than guessed at here.
    """
    return {
        -50: (21400, 0),
        -49: (21845, 0),
        -46: (23302, 0),
        -45: (23831, 0),
        -36: (29959, 0),
        -35: (29959, 0),
        50: (21400, 0),
    }


def state(over: dict[int, int] | None = None) -> dict[int, int]:
    """The constants `$02` leaves behind, as measured in the recording."""
    base = {
        raster.HORIZON: 53,
        raster.FIRST_MANTISSA: 24576,
        raster.FIRST_EXPONENT: 3,
        raster.SECOND_MANTISSA: 19440,
        raster.SECOND_EXPONENT: 3,
        raster.MATRIX[0]: 32767,
        raster.MATRIX[1]: 0,
        raster.MATRIX[2]: 0,
        raster.MATRIX[3]: 32767,
    }
    base.update(over or {})
    return base


class Scales(unittest.TestCase):
    def test_a_line_level_with_the_horizon_has_no_scale(self) -> None:
        self.assertIsNone(raster.scales(lookup(), state(), 0))

    def test_a_distance_the_part_was_never_asked_about_has_no_scale(self) -> None:
        self.assertIsNone(raster.scales(lookup(), state(), -9999))

    def test_the_measured_pair_at_the_top_of_the_screen(self) -> None:
        self.assertEqual(raster.scales(lookup(), state(), -50), (-32, -149))

    def test_the_measured_pair_partway_down(self) -> None:
        self.assertEqual(raster.scales(lookup(), state(), -46), (-35, -163))

    def test_another_measured_pair_further_down(self) -> None:
        self.assertEqual(raster.scales(lookup(), state(), -45), (-35, -166))

    def test_two_distances_sharing_a_reciprocal_share_a_scale(self) -> None:
        self.assertEqual(
            raster.scales(lookup(), state(), -36), raster.scales(lookup(), state(), -35)
        )

    def test_a_line_below_the_horizon_is_not_a_mirror_of_one_above(self) -> None:
        below = raster.scales(lookup(), state(), 50)
        above = raster.scales(lookup(), state(), -50)
        assert below is not None and above is not None
        self.assertNotEqual(below, (-above[0], -above[1]))

    def test_the_pair_below_the_horizon_is_two_short_of_the_mirror(self) -> None:
        below = raster.scales(lookup(), state(), 50)
        above = raster.scales(lookup(), state(), -50)
        assert below is not None and above is not None
        self.assertEqual(below, (-above[0] - 2, -above[1] - 2))

    def test_a_shift_from_folding_reaches_both_values(self) -> None:
        flat = raster.scales({-46: (23302, 0)}, state(), -46)
        folded = raster.scales({-46: (23302, -1)}, state(), -46)
        assert flat is not None and folded is not None
        self.assertNotEqual(flat, folded)

    def test_the_second_value_moves_with_the_first_mantissa(self) -> None:
        one = raster.scales(lookup(), state(), -46)
        two = raster.scales(lookup(), state({raster.FIRST_MANTISSA: 12288}), -46)
        assert one is not None and two is not None
        self.assertNotEqual(one[1], two[1])

    def test_an_exponent_large_enough_to_drive_the_shift_negative_has_no_scale(self) -> None:
        self.assertIsNone(raster.scales(lookup(), state({raster.FIRST_EXPONENT: 40}), -50))

    def test_a_second_exponent_large_enough_to_drive_its_shift_negative_has_no_scale(self) -> None:
        self.assertIsNone(raster.scales(lookup(), state({raster.SECOND_EXPONENT: 40}), -50))


class Answer(unittest.TestCase):
    def test_it_sends_four_words_a_scanline(self) -> None:
        self.assertEqual(len(raster.answer(lookup(), state(), -104, 7)), 28)

    def test_the_first_scanline_matches_what_the_part_answered(self) -> None:
        self.assertEqual(raster.answer(lookup(), state(), -104, 1), (-32, 0, 0, -149))

    def test_an_identity_matrix_zeroes_the_two_off_diagonal_words(self) -> None:
        got = raster.answer(lookup(), state(), -104, 1)
        self.assertEqual((got[1], got[2]), (0, 0))

    def test_a_line_with_no_scale_sends_four_noughts(self) -> None:
        self.assertEqual(raster.answer(lookup(), state({raster.HORIZON: 0}), -1, 1), (0, 0, 0, 0))


class Shortfall(unittest.TestCase):
    def test_an_exact_answer_reports_no_wrong_lines(self) -> None:
        self.assertEqual(raster.shortfall((1, 2, 3, 4), (1, 2, 3, 4)), (1, 0))

    def test_a_wrong_line_is_counted_rather_than_hidden(self) -> None:
        self.assertEqual(raster.shortfall((1, 2, 3, 9), (1, 2, 3, 4)), (0, 1))

    def test_it_counts_only_as_far_as_the_shorter_of_the_two(self) -> None:
        self.assertEqual(raster.shortfall((1, 2, 3, 4), (1, 2, 3, 4) * 3), (1, 0))


if __name__ == "__main__":
    unittest.main()
