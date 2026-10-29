import unittest

import parameter
import script


class Slots(unittest.TestCase):
    def test_the_two_arguments_that_never_vary_are_named(self) -> None:
        self.assertEqual(parameter.FIXED, {3: 32, 4: 256})

    def test_every_group_keys_on_arguments_that_exist(self) -> None:
        for slots, _ in parameter.GROUPS.values():
            for slot in slots:
                self.assertIn(slot, range(parameter.WORDS))

    def test_no_group_keys_on_an_argument_that_never_varies(self) -> None:
        for slots, _ in parameter.GROUPS.values():
            self.assertFalse(set(slots) & set(parameter.FIXED))

    def test_every_group_names_cells_the_part_has(self) -> None:
        for _, cells in parameter.GROUPS.values():
            for cell in cells:
                self.assertIn(cell, parameter.CELLS)

    def test_the_matrix_group_stores_only_the_two_words_that_are_not_repeats(self) -> None:
        _, cells = parameter.GROUPS["matrix"]

        self.assertEqual(cells, ("matrix0", "matrix1"))

    def test_every_cell_that_is_not_a_repeat_is_carried_by_some_group(self) -> None:
        carried = {cell for _, cells in parameter.GROUPS.values() for cell in cells}

        self.assertEqual(carried | {"matrix2", "matrix3"}, set(parameter.CELLS))


class Keyed(unittest.TestCase):
    def test_it_takes_the_slots_the_group_names(self) -> None:
        self.assertEqual(parameter.keyed((10, 11, 12, 13, 14, 15, 16), (2, 6)), (12, 16))

    def test_a_single_slot_gives_a_single_element_key(self) -> None:
        self.assertEqual(parameter.keyed((10, 11, 12, 13, 14, 15, 16), (5,)), (15,))

    def test_no_slots_gives_an_empty_key(self) -> None:
        self.assertEqual(parameter.keyed((10, 11), ()), ())


class Gathered(unittest.TestCase):
    def test_it_builds_one_row_per_distinct_key(self) -> None:
        seen = [((0, 0, 1, 32, 256, 0, 7), (5, 6)), ((9, 9, 1, 32, 256, 0, 7), (5, 6))]
        rows = parameter.gathered(seen, (2, 6))
        self.assertEqual(rows, {(1, 7): (5, 6)})

    def test_two_keys_that_differ_make_two_rows(self) -> None:
        seen = [((0, 0, 1, 32, 256, 0, 7), (5, 6)), ((0, 0, 2, 32, 256, 0, 7), (8, 9))]
        rows = parameter.gathered(seen, (2, 6))
        self.assertEqual(len(rows), 2)

    def test_a_repeated_key_carrying_a_different_answer_is_reported(self) -> None:
        seen = [((0, 0, 1, 32, 256, 0, 7), (5, 6)), ((0, 0, 1, 32, 256, 0, 7), (7, 8))]
        with self.assertRaises(parameter.Disagreement):
            parameter.gathered(seen, (2, 6))


class Mirrored(unittest.TestCase):
    def test_a_matrix_that_is_two_words_twice_passes(self) -> None:
        parameter.mirrored({"matrix0": 30000, "matrix1": 400, "matrix2": -400, "matrix3": 30000})

    def test_a_matrix_whose_last_word_is_not_the_first_is_refused(self) -> None:
        with self.assertRaises(parameter.NotMirrored):
            parameter.mirrored({"matrix0": 1, "matrix1": 2, "matrix2": -2, "matrix3": 3})

    def test_a_matrix_whose_third_word_is_not_the_second_negated_is_refused(self) -> None:
        with self.assertRaises(parameter.NotMirrored):
            parameter.mirrored({"matrix0": 1, "matrix1": 2, "matrix2": 2, "matrix3": 1})


class Sized(unittest.TestCase):
    def test_it_counts_two_bytes_a_word_for_the_key_and_the_state(self) -> None:
        self.assertEqual(parameter.sized({(1,): (2, 3)}), 6)

    def test_it_counts_every_row(self) -> None:
        self.assertEqual(parameter.sized({(1,): (2, 3), (4,): (5, 6)}), 12)

    def test_a_wider_key_costs_more(self) -> None:
        self.assertEqual(parameter.sized({(1, 2): (3,)}), 6)

    def test_an_empty_table_costs_nothing(self) -> None:
        self.assertEqual(parameter.sized({}), 0)


class Fixed(unittest.TestCase):
    def test_arguments_that_never_varied_are_confirmed_against_a_run(self) -> None:
        seen = [(0, 0, 0, 32, 256, 0, 0), (1, 1, 1, 32, 256, 1, 1)]
        self.assertEqual(parameter.fixed(seen), {3: 32, 4: 256})

    def test_an_argument_that_varies_is_not_reported_as_fixed(self) -> None:
        seen = [(0, 0, 0, 32, 256, 0, 0), (0, 0, 0, 33, 256, 0, 0)]
        self.assertNotIn(3, parameter.fixed(seen))

    def test_an_empty_run_fixes_nothing(self) -> None:
        self.assertEqual(parameter.fixed([]), {})


script.entry(__name__, unittest.main)
