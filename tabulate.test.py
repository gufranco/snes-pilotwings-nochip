import unittest
from typing import override

import hardware
import script
import tabulate


class SizeTest(unittest.TestCase):
    def test_one_input_word_needs_a_row_per_value_of_it(self) -> None:
        self.assertEqual(tabulate.entries_for(1), 65536)

    def test_two_input_words_need_the_square_of_that(self) -> None:
        self.assertEqual(tabulate.entries_for(2), 65536 * 65536)

    def test_a_table_is_its_rows_times_the_width_of_an_answer(self) -> None:
        self.assertEqual(tabulate.bytes_for(1, out=1), 65536 * 2)

    def test_a_wider_answer_makes_a_proportionally_larger_table(self) -> None:
        self.assertEqual(tabulate.bytes_for(1, out=4), tabulate.bytes_for(1, out=1) * 4)


class StorableTest(unittest.TestCase):
    def test_a_single_input_command_can_have_every_answer_stored(self) -> None:
        self.assertTrue(tabulate.storable(1))

    def test_a_two_input_command_cannot(self) -> None:
        self.assertFalse(tabulate.storable(2))

    def test_the_line_sits_between_one_input_word_and_two(self) -> None:
        self.assertNotEqual(tabulate.storable(1), tabulate.storable(2))

    def test_a_table_claiming_more_than_half_the_image_is_refused(self) -> None:
        self.assertFalse(tabulate.storable(1, out=tabulate.CARTRIDGE_BUDGET))

    def test_a_wide_enough_answer_puts_even_one_input_word_out_of_reach(self) -> None:
        self.assertFalse(tabulate.storable(1, out=100))


class BudgetTest(unittest.TestCase):
    def test_the_game_has_to_keep_fitting_in_the_image(self) -> None:
        self.assertEqual(tabulate.free(), tabulate.CARTRIDGE_BUDGET - tabulate.GAME_BYTES)

    def test_the_budget_is_the_ninety_six_megabit_ceiling(self) -> None:
        self.assertEqual(tabulate.CARTRIDGE_BUDGET, 96 * 1024 * 1024 // 8)

    def test_a_table_over_one_sixteen_bit_input_is_a_hundred_and_thirty_kilobytes(self) -> None:
        self.assertEqual(tabulate.kernel_bytes(), 131072)

    def test_the_image_has_room_for_many_such_tables(self) -> None:
        self.assertGreater(tabulate.kernel_tables(), 64)

    def test_a_smaller_image_has_room_for_fewer(self) -> None:
        self.assertLess(
            tabulate.kernel_tables(budget=tabulate.CARTRIDGE_BUDGET // 2),
            tabulate.kernel_tables(),
        )

    def test_a_wider_answer_costs_room(self) -> None:
        self.assertLess(tabulate.kernel_tables(out=2), tabulate.kernel_tables(out=1))


class ShapeTest(unittest.TestCase):
    def test_a_command_that_answers_reports_what_it_takes(self) -> None:
        shape = tabulate.Shape(0x00, 2, 1)

        self.assertTrue(shape.answers)

    def test_a_command_that_never_answers_says_so(self) -> None:
        shape = tabulate.Shape(0x02, None, 0)

        self.assertFalse(shape.answers)

    def test_the_repr_of_an_answering_command_names_both_widths(self) -> None:
        self.assertIn("2 in, 1 out", repr(tabulate.Shape(0x00, 2, 1)))

    def test_the_repr_of_a_silent_command_says_it_answers_nothing(self) -> None:
        self.assertIn("answers nothing", repr(tabulate.Shape(0x02, None, 0)))


class ConstantsTest(unittest.TestCase):
    def test_the_window_address_names_the_data_port_rather_than_the_status(self) -> None:
        self.assertEqual(tabulate.DATA & 1, 0)

    def test_the_idle_word_is_the_padding_a_short_answer_leaves(self) -> None:
        self.assertEqual(tabulate.IDLE_WORD, 0x8080)

    def test_the_probe_fits_in_a_word(self) -> None:
        self.assertLessEqual(tabulate.PROBE, 0xFFFF)


class FakePart:
    def __init__(self, takes: int, gives: int) -> None:
        self.takes = takes
        self.gives = gives
        self.written = -1
        self.read = 0

    def write_bus(self, address: int, value: int) -> None:
        self.written += 1

    def read_bus(self, address: int) -> int:
        words_in = self.written // 2
        self.read += 1
        word = (self.read - 1) // 2
        if words_in > self.takes:
            return 0x80
        if words_in < self.takes:
            return 0x12 if word < 1 else 0x80
        return 0x12 if word < self.gives else 0x80


class AgainstAStandInTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.real = tabulate.chip

    @override
    def tearDown(self) -> None:
        tabulate.chip = self.real

    def stand_in(self, takes: int, gives: int = 1) -> None:
        tabulate.chip = lambda model=tabulate.MODEL: FakePart(takes, gives)

    def test_the_part_is_built_through_the_model_this_project_pins(self) -> None:
        class Loaded:
            @staticmethod
            def Chip(model: str) -> str:
                return f"built {model}"

        real = hardware.load
        hardware.load = lambda package: Loaded()
        try:
            built = tabulate.chip()
        finally:
            hardware.load = real

        self.assertEqual(built, f"built {tabulate.MODEL}")

    def test_a_command_taking_two_words_is_measured_as_taking_two(self) -> None:
        self.stand_in(2)

        self.assertEqual(tabulate.shape_of(0x00).writes, 2)

    def test_a_command_taking_one_word_is_measured_as_taking_one(self) -> None:
        self.stand_in(1)

        self.assertEqual(tabulate.shape_of(0x27).writes, 1)

    def test_the_answer_width_is_counted_too(self) -> None:
        self.stand_in(2, gives=3)

        self.assertEqual(tabulate.shape_of(0x00).reads, 3)

    def test_a_part_that_never_answers_reports_nothing_taken(self) -> None:
        self.stand_in(99)

        self.assertIsNone(tabulate.shape_of(0x02).writes)

    def test_a_part_silent_from_the_first_word_reports_nothing_taken(self) -> None:
        self.stand_in(0, gives=0)

        self.assertIsNone(tabulate.shape_of(0x02).writes)

    def test_an_exchange_returns_two_bytes_for_each_word_read(self) -> None:
        self.stand_in(2)

        self.assertEqual(len(tabulate.ask(0x00, (1, 2), reads=3)), 6)

    def test_a_part_answering_the_same_way_twice_reads_as_deterministic(self) -> None:
        self.stand_in(2)

        self.assertTrue(tabulate.deterministic())

    def test_a_sweep_covers_every_command_byte(self) -> None:
        self.stand_in(1)

        self.assertEqual([one.command for one in tabulate.sweep()], list(range(256)))


script.entry(__name__, unittest.main)
