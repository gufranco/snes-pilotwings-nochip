import unittest

import parameter


class Slots(unittest.TestCase):
    def test_the_two_arguments_that_never_vary_are_named(self) -> None:
        self.assertEqual(parameter.FIXED, {3: 32, 4: 256})

    def test_every_group_keys_on_arguments_that_exist(self) -> None:
        for slots in parameter.GROUPS.values():
            for slot in slots:
                self.assertIn(slot, range(parameter.WORDS))

    def test_no_group_keys_on_an_argument_that_never_varies(self) -> None:
        for slots in parameter.GROUPS.values():
            self.assertFalse(set(slots) & set(parameter.FIXED))


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


class Sized(unittest.TestCase):
    def test_it_counts_two_bytes_a_word(self) -> None:
        self.assertEqual(parameter.sized({(1,): (2, 3)}), 4)

    def test_it_counts_every_row(self) -> None:
        self.assertEqual(parameter.sized({(1,): (2, 3), (4,): (5, 6)}), 8)

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


if __name__ == "__main__":
    unittest.main()
