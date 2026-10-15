import unittest
from pathlib import Path

import raster

ROOT = Path(__file__).resolve().parent


def _table(value: int = 0x4000) -> tuple[int, ...]:
    return (value,) * 0x4000


def _state(**named: int) -> dict[int, int]:
    found = {
        raster.STEP: 0,
        raster.HORIZON: 0,
        raster.FIRST_MANTISSA: 0,
        raster.FIRST_EXPONENT: 0,
        raster.SECOND_MANTISSA: 0,
        raster.SECOND_EXPONENT: 0,
    }
    found.update(dict.fromkeys(raster.MATRIX, 0))
    for name, value in named.items():
        found[getattr(raster, name.upper())] = value
    return found


class Signed(unittest.TestCase):
    def test_a_word_below_the_halfway_point_stays_itself(self) -> None:
        self.assertEqual(raster.signed(0x1234), 0x1234)

    def test_a_word_above_it_reads_as_negative(self) -> None:
        self.assertEqual(raster.signed(0xFFFE), -2)


class Product(unittest.TestCase):
    def test_a_half_against_a_half_is_a_quarter(self) -> None:
        self.assertEqual(raster.product(0x4000, 0x4000), 0x2000)

    def test_it_keeps_the_sign(self) -> None:
        self.assertEqual(raster.product(-0x4000, 0x4000), -0x2000)

    def test_it_rounds_down_rather_than_towards_nought(self) -> None:
        self.assertEqual(raster.product(-1, 3), -1)

    def test_nought_against_anything_is_nought(self) -> None:
        self.assertEqual(raster.product(0, 0x7FFF), 0)


class Normalise(unittest.TestCase):
    def test_a_value_already_in_range_is_left_alone(self) -> None:
        self.assertEqual(raster.normalise(0x4000), (0x4000, 0))

    def test_it_doubles_until_the_top_two_bits_differ(self) -> None:
        self.assertEqual(raster.normalise(0x2000), (0x4000, 1))

    def test_a_negative_value_normalises_the_same_way(self) -> None:
        self.assertEqual(raster.normalise(-48), (-48 << 9, 9))

    def test_the_most_negative_word_is_already_normalised(self) -> None:
        self.assertEqual(raster.normalise(-0x8000), (-0x8000, 0))

    def test_nought_is_answered_untouched_so_the_loop_ends(self) -> None:
        self.assertEqual(raster.normalise(0), (0, 0))


class Reciprocal(unittest.TestCase):
    def test_it_reads_the_entry_the_magnitude_names(self) -> None:
        table = list(_table())
        table[0x10] = 1234

        self.assertEqual(raster.reciprocal(0x4010, 9, table)[0], 1234)

    def test_a_negative_input_answers_the_entry_negated(self) -> None:
        table = list(_table())
        table[0x10] = 1234

        self.assertEqual(raster.reciprocal(-0x4010, 9, table)[0], -1234)

    def test_the_most_negative_word_reads_the_highest_entry(self) -> None:
        table = list(_table())
        table[-1] = 999

        self.assertEqual(raster.reciprocal(-0x8000, 0, table)[0], -999)

    def test_the_exponent_is_the_doubling_count_less_six(self) -> None:
        self.assertEqual(raster.reciprocal(0x4000, 9, _table())[1], 3)

    def test_a_distance_of_nought_takes_the_part_own_answer(self) -> None:
        self.assertEqual(raster.reciprocal(0, 0, _table()), raster.ON_NOUGHT)


class Scaled(unittest.TestCase):
    def test_a_shift_of_one_halves_the_normalised_value(self) -> None:
        self.assertEqual(raster.scaled(0x4000, 14), 0x2000)

    def test_it_shifts_arithmetically_so_a_negative_stays_negative(self) -> None:
        self.assertEqual(raster.scaled(-0x4000, 14), -0x2000)

    def test_an_exponent_that_lands_exactly_hands_the_value_back(self) -> None:
        self.assertEqual(raster.scaled(0x4000, 15), 0x4000)

    def test_an_exponent_above_that_clamps_high(self) -> None:
        self.assertEqual(raster.scaled(0x4000, 16), raster.CLAMP_HIGH)

    def test_a_negative_value_clamps_one_short_of_the_lowest_word(self) -> None:
        self.assertEqual(raster.scaled(-0x8000, 16), raster.CLAMP_LOW)

    def test_a_shift_past_the_table_gives_nought_rather_than_a_sign_fill(self) -> None:
        self.assertEqual(raster.scaled(-0x4000, -1), 0)

    def test_the_normalise_inside_it_is_paid_back_by_the_shift(self) -> None:
        self.assertEqual(raster.scaled(0x2000, 15), 0x2000)


class Scanline(unittest.TestCase):
    def test_the_second_scale_carries_the_first_chain_mantissa(self) -> None:
        state = _state(
            step=0,
            horizon=0x4000,
            first_mantissa=0x7FFF,
            first_exponent=15,
            second_mantissa=0x4000,
            second_exponent=15,
        )

        near, far = raster.scanline(state, 0, _table(0x4000))

        self.assertEqual(far, raster.scaled(raster.product(0x4000, near), 30))

    def test_the_line_moves_the_distance_through_the_step(self) -> None:
        state = _state(step=0x7FFF, horizon=0, first_mantissa=0x4000, first_exponent=3)

        self.assertNotEqual(
            raster.scanline(state, 1, _table())[0],
            raster.scanline(state, 40, _table())[0],
        )


class Answer(unittest.TestCase):
    def test_it_gives_four_words_a_scanline(self) -> None:
        found = raster.answer(_state(), 0, 7, _table())

        self.assertEqual(len(found), 28)

    def test_the_first_group_belongs_to_the_line_the_argument_names(self) -> None:
        state = _state(step=0x7FFF, horizon=0, first_mantissa=0x4000, first_exponent=15)
        state[raster.MATRIX[0]] = 0x7FFF

        whole = raster.answer(state, 40, 2, _table())
        one = raster.answer(state, 40, 1, _table())

        self.assertEqual(whole[:4], one)

    def test_every_word_is_a_word(self) -> None:
        state = _state(first_mantissa=0x7FFF, first_exponent=15)
        state[raster.MATRIX[0]] = -0x7FFF

        self.assertTrue(all(0 <= one < 0x10000 for one in raster.answer(state, -5, 4, _table())))


class Shortfall(unittest.TestCase):
    def test_two_streams_that_agree_have_nothing_wrong(self) -> None:
        self.assertEqual(raster.shortfall((1, 2, 3, 4), (1, 2, 3, 4)), (1, 0))

    def test_one_word_out_makes_the_whole_scanline_wrong(self) -> None:
        self.assertEqual(raster.shortfall((1, 2, 3, 4), (1, 2, 3, 5)), (0, 1))

    def test_it_counts_every_scanline(self) -> None:
        self.assertEqual(raster.shortfall((0,) * 8, (0,) * 8), (2, 0))

    def test_it_stops_at_the_shorter_of_the_two(self) -> None:
        self.assertEqual(raster.shortfall((0,) * 4, (0,) * 12), (1, 0))


class File(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "raster.py").exists())


if __name__ == "__main__":
    unittest.main()
