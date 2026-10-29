import unittest

import script
import state02


class Packed(unittest.TestCase):
    def test_a_row_is_its_key_then_its_words_little_endian(self) -> None:
        self.assertEqual(state02.packed({(1,): (2,)}), b"\x01\x00\x02\x00")

    def test_rows_come_out_in_key_order_so_a_search_can_bisect(self) -> None:
        self.assertEqual(
            state02.packed({(2,): (0,), (1,): (0,)}),
            b"\x01\x00\x00\x00\x02\x00\x00\x00",
        )

    def test_a_negative_word_is_written_as_its_unsigned_pattern(self) -> None:
        self.assertEqual(state02.packed({(0,): (-1,)}), b"\x00\x00\xff\xff")

    def test_a_two_part_key_writes_both_parts(self) -> None:
        self.assertEqual(state02.packed({(1, 2): (3,)}), b"\x01\x00\x02\x00\x03\x00")

    def test_an_empty_table_packs_to_nothing(self) -> None:
        self.assertEqual(state02.packed({}), b"")


class Stride(unittest.TestCase):
    def test_it_counts_the_key_and_the_words(self) -> None:
        self.assertEqual(state02.stride({(1, 2): (3, 4, 5)}), 5)

    def test_an_empty_table_has_no_stride(self) -> None:
        self.assertEqual(state02.stride({}), 0)


class Rows(unittest.TestCase):
    def test_it_counts_what_was_packed(self) -> None:
        self.assertEqual(state02.rows({(1,): (0,), (2,): (0,)}), 2)


class Checked(unittest.TestCase):
    def test_a_table_whose_rows_all_match_passes(self) -> None:
        state02.checked({(1,): (2, 3)})

    def test_a_row_whose_word_will_not_fit_is_refused(self) -> None:
        with self.assertRaises(state02.TooWide):
            state02.checked({(1,): (70000,)})

    def test_a_key_that_will_not_fit_is_refused(self) -> None:
        with self.assertRaises(state02.TooWide):
            state02.checked({(70000,): (1,)})

    def test_rows_of_differing_width_are_refused(self) -> None:
        with self.assertRaises(state02.Ragged):
            state02.checked({(1,): (2,), (2,): (3, 4)})

    def test_keys_of_differing_width_are_refused(self) -> None:
        with self.assertRaises(state02.Ragged):
            state02.checked({(1,): (2,), (2, 3): (4,)})

    def test_an_empty_table_passes(self) -> None:
        state02.checked({})


script.entry(__name__, unittest.main)
