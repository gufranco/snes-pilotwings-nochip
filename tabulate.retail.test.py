import unittest

import tabulate


def microcode_here() -> bool:
    try:
        tabulate.chip()
    except Exception:
        return False
    return True


HELD = microcode_here()

MULTIPLY = 0x00


def q15(first: int, second: int) -> int:
    def signed(value: int) -> int:
        return value - 0x10000 if value & 0x8000 else value

    return (signed(first) * signed(second) >> 15) & 0xFFFF


@unittest.skipIf(not HELD, "no DSP-1 microcode on this machine")
class AgainstThePartTest(unittest.TestCase):
    def test_two_parts_built_fresh_answer_one_question_identically(self) -> None:
        self.assertTrue(tabulate.deterministic())

    def test_the_multiply_command_takes_two_words_and_gives_one(self) -> None:
        shape = tabulate.shape_of(MULTIPLY)

        self.assertEqual((shape.writes, shape.reads), (2, 1))

    def test_the_multiply_command_answers_the_product_this_test_worked_out(self) -> None:
        answer = tabulate.ask(MULTIPLY, (0x1234, 0x5678))

        self.assertEqual(int.from_bytes(answer, "little"), q15(0x1234, 0x5678))

    def test_it_answers_the_product_for_another_pair_too(self) -> None:
        answer = tabulate.ask(MULTIPLY, (0x2000, 0x4000))

        self.assertEqual(int.from_bytes(answer, "little"), q15(0x2000, 0x4000))

    def test_a_negative_operand_is_handled_as_signed(self) -> None:
        answer = tabulate.ask(MULTIPLY, (0xC000, 0x4000))

        self.assertEqual(int.from_bytes(answer, "little"), q15(0xC000, 0x4000))

    def test_some_command_bytes_answer_nothing_at_all(self) -> None:
        self.assertFalse(tabulate.shape_of(0x02).answers)

    def test_a_command_taking_one_word_exists(self) -> None:
        self.assertEqual(tabulate.shape_of(0x27).writes, 1)

    def test_a_single_input_command_can_have_every_answer_stored(self) -> None:
        shape = tabulate.shape_of(0x27)

        self.assertTrue(tabulate.storable(shape.writes or 0, shape.reads))

    def test_the_multiply_command_cannot(self) -> None:
        shape = tabulate.shape_of(MULTIPLY)

        self.assertFalse(tabulate.storable(shape.writes or 0, shape.reads))


@unittest.skipIf(not HELD, "no DSP-1 microcode on this machine")
class BothMasksTest(unittest.TestCase):
    def test_the_corrected_mask_answers_the_same_multiply(self) -> None:
        first = tabulate.ask(MULTIPLY, (0x1234, 0x5678), model="dsp1")
        second = tabulate.ask(MULTIPLY, (0x1234, 0x5678), model="dsp1b")

        self.assertEqual(first, second)

    def test_the_corrected_mask_takes_the_same_words_for_that_command(self) -> None:
        first = tabulate.shape_of(MULTIPLY, model="dsp1")
        second = tabulate.shape_of(MULTIPLY, model="dsp1b")

        self.assertEqual(first.writes, second.writes)


if __name__ == "__main__":
    unittest.main()
