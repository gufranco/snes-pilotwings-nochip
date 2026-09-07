import unittest
from typing import override

import attitude


class SignedTest(unittest.TestCase):
    def test_a_word_below_the_halfway_mark_is_itself(self) -> None:
        self.assertEqual(attitude.signed(0x7FFF), 32767)

    def test_a_word_above_it_is_negative(self) -> None:
        self.assertEqual(attitude.signed(0x8000), -32768)
        self.assertEqual(attitude.signed(0xFFFF), -1)


class ProductTest(unittest.TestCase):
    def test_it_floors_rather_than_truncating_toward_nought(self) -> None:
        self.assertEqual(attitude.product(-32767, 32767), 0x8001)
        self.assertEqual(attitude.product(32767, 32767), 0x7FFE)

    def test_multiplying_by_one_takes_one_off_a_positive_value(self) -> None:
        self.assertEqual(attitude.product(0x1234, attitude.ONE), 0x1233)

    def test_multiplying_by_one_leaves_a_negative_value_alone(self) -> None:
        self.assertEqual(attitude.product(-0x1234, attitude.ONE), (-0x1234) & 0xFFFF)

    def test_the_most_negative_value_negated_multiplies_as_a_positive_one(self) -> None:
        most = attitude.signed(0x8000)

        self.assertEqual(attitude.product(0x1234, -most), 0x1234)


class CosineTest(unittest.TestCase):
    def test_it_reads_the_table_everywhere_but_half_a_turn(self) -> None:
        table = [0x1111] * 0x10000

        self.assertEqual(attitude.cosine_of(table, 0x0000), 0x1111)
        self.assertEqual(attitude.cosine_of(table, 0x7FFF), 0x1111)

    def test_half_a_turn_holds_what_the_table_cannot(self) -> None:
        table = [0x8001] * 0x10000

        self.assertEqual(attitude.cosine_of(table, attitude.HALF_TURN), 0x8000)


class MatrixTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.sine = [0x0000] * 0x10000
        self.cosine = [0x7FFF] * 0x10000

    def test_it_answers_all_nine_cells(self) -> None:
        got = attitude.matrix(self.sine, self.cosine, 0, 0)

        self.assertEqual(sorted(got), sorted(attitude.CELLS.values()))

    def test_the_third_cell_of_the_first_row_is_always_nought(self) -> None:
        got = attitude.matrix(self.sine, self.cosine, 0x1234, 0x5678)

        self.assertEqual(got[attitude.CELLS["row0col2"]], 0x0000)

    def test_a_matrix_with_no_rotation_at_all(self) -> None:
        got = attitude.matrix(self.sine, self.cosine, 0, 0)

        self.assertEqual(got[attitude.CELLS["row0col0"]], 0x7FFE)
        self.assertEqual(got[attitude.CELLS["row0col1"]], 0x0000)
        self.assertEqual(got[attitude.CELLS["row1col2"]], 0x0000)
        self.assertEqual(got[attitude.CELLS["row2col2"]], 0x7FFE)

    def test_the_cross_terms_multiply_the_two_angles_together(self) -> None:
        sine = list(self.sine)
        cosine = list(self.cosine)
        sine[0x0001] = 0x4000
        cosine[0x0002] = 0x2000

        got = attitude.matrix(sine, cosine, 0x0001, 0x0002)

        self.assertEqual(got[attitude.CELLS["row1col1"]], attitude.product(0x7FFF, 0x2000))
        self.assertEqual(got[attitude.CELLS["row2col1"]], attitude.product(0x4000, -0x2000))


if __name__ == "__main__":
    unittest.main()
