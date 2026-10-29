import unittest

import exchanges
import script


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


script.entry(__name__, unittest.main)
