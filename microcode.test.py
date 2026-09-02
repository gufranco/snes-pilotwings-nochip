import unittest
from pathlib import Path

import hardware
import microcode

ROOT = Path(__file__).resolve().parent


class _Stores:
    def __init__(self) -> None:
        self.program = [0] * microcode.PROGRAM_WORDS


class _Core:
    def __init__(self) -> None:
        self.stores = _Stores()


class _Chip:
    def __init__(self) -> None:
        self.core = _Core()


class _Loaded:
    """A stand in for the model, so reading a program needs no microcode."""

    def __init__(self, asked: list[str] | None = None) -> None:
        self.asked = asked

    def Chip(self, mask: str) -> _Chip:
        if self.asked is not None:
            self.asked.append(mask)
        return _Chip()


def program(words: dict[int, int], length: int = microcode.PROGRAM_WORDS) -> tuple[int, ...]:
    built = [microcode.jump_word(microcode.ALWAYS, 0)] * length
    for at, word in words.items():
        built[at] = word
    return tuple(built)


def tree(carry: int, no_carry: int) -> dict[int, int]:
    """The smallest dispatch there can be: one bit tested, two arms."""
    return {
        microcode.DISPATCH: microcode.SHIFT_WORD,
        microcode.DISPATCH + 1: microcode.jump_word(microcode.ON_CARRY, carry),
        microcode.DISPATCH + 2: microcode.jump_word(microcode.ON_NO_CARRY, no_carry),
    }


class WordTest(unittest.TestCase):
    def test_a_jump_word_reads_back_as_a_jump_to_its_target(self) -> None:
        word = microcode.jump_word(microcode.ALWAYS, 0x123)

        self.assertIn("$0123", microcode.text_of(word))

    def test_a_carry_jump_names_the_carry_condition(self) -> None:
        word = microcode.jump_word(microcode.ON_CARRY, 0x123)

        self.assertTrue(microcode.text_of(word).startswith(microcode.CARRY_SET))

    def test_the_shift_word_reads_back_as_a_shift(self) -> None:
        self.assertTrue(microcode.text_of(microcode.SHIFT_WORD).startswith(microcode.SHIFT))


class ListingTest(unittest.TestCase):
    def test_every_word_gets_a_line(self) -> None:
        found = microcode.listing(program({}, 4))

        self.assertEqual(len(found), 4)

    def test_a_line_is_keyed_on_its_address(self) -> None:
        found = microcode.listing(program({}, 4))

        self.assertEqual(sorted(found), [0, 1, 2, 3])


class DispatchTest(unittest.TestCase):
    def test_an_odd_command_takes_the_carry_arm(self) -> None:
        found = microcode.dispatch(program(tree(0x100, 0x200)))

        self.assertEqual(found[1], 0x100)

    def test_an_even_command_takes_the_other_arm(self) -> None:
        found = microcode.dispatch(program(tree(0x100, 0x200)))

        self.assertEqual(found[0], 0x200)

    def test_every_command_byte_is_answered(self) -> None:
        self.assertEqual(len(microcode.dispatch(program(tree(0x100, 0x200)))), 256)

    def test_a_tree_that_never_leaves_reports_nothing(self) -> None:
        looping = {
            microcode.DISPATCH: microcode.SHIFT_WORD,
            microcode.DISPATCH + 1: microcode.jump_word(microcode.ON_CARRY, microcode.DISPATCH),
            microcode.DISPATCH + 2: microcode.jump_word(microcode.ON_NO_CARRY, microcode.DISPATCH),
        }

        self.assertIsNone(microcode.dispatch(program(looping))[0])


class BodyTest(unittest.TestCase):
    def test_a_body_stops_at_the_jump_home(self) -> None:
        built = program(
            {0x100: microcode.SHIFT_WORD, 0x101: microcode.jump_word(microcode.ALWAYS, 0)}
        )

        self.assertEqual(len(microcode.body(built, 0x100)), 2)

    def test_a_body_keeps_the_address_of_each_line(self) -> None:
        built = program(
            {0x100: microcode.SHIFT_WORD, 0x101: microcode.jump_word(microcode.ALWAYS, 0)}
        )

        self.assertEqual([at for at, _ in microcode.body(built, 0x100)], [0x100, 0x101])

    def test_a_body_that_never_ends_is_cut_at_the_limit(self) -> None:
        built = program(dict.fromkeys(range(256, 1024), microcode.SHIFT_WORD))

        self.assertEqual(len(microcode.body(built, 0x100, most=8)), 8)


class BodyEdgeTest(unittest.TestCase):
    def test_a_body_starting_past_the_program_is_empty(self) -> None:
        built = program({})

        self.assertEqual(microcode.body(built, microcode.PROGRAM_WORDS), ())

    def test_a_body_stops_where_the_program_does(self) -> None:
        built = program({})
        at = microcode.PROGRAM_WORDS - 3

        self.assertEqual(len(microcode.body(built, at)), 1)


class HandlerGroupingTest(unittest.TestCase):
    def test_a_byte_that_never_leaves_joins_no_group(self) -> None:
        looping = {
            microcode.DISPATCH: microcode.SHIFT_WORD,
            microcode.DISPATCH + 1: microcode.jump_word(microcode.ON_CARRY, microcode.DISPATCH),
            microcode.DISPATCH + 2: microcode.jump_word(microcode.ON_NO_CARRY, microcode.DISPATCH),
        }

        self.assertEqual(microcode.handlers(program(looping)), {})


class HandlersTest(unittest.TestCase):
    def test_commands_reaching_one_place_are_grouped(self) -> None:
        found = microcode.handlers(program(tree(0x100, 0x100)))

        self.assertEqual(len(found[0x100]), 256)

    def test_two_arms_make_two_groups(self) -> None:
        found = microcode.handlers(program(tree(0x100, 0x200)))

        self.assertEqual(sorted(found), [0x100, 0x200])


class ReportTest(unittest.TestCase):
    def test_the_report_counts_the_handlers(self) -> None:
        lines = microcode.report(program(tree(0x100, 0x200)))

        self.assertIn("2", lines[0])

    def test_the_report_names_a_command_the_game_issues(self) -> None:
        lines = microcode.report(program(tree(0x100, 0x200)))

        self.assertTrue(any("$00" in line for line in lines))


class ProgramOfTest(unittest.TestCase):
    def test_it_reads_the_program_out_of_the_model(self) -> None:
        real = hardware.load
        hardware.load = lambda package: _Loaded()
        try:
            found = microcode.program_of(microcode.MASK)
        finally:
            hardware.load = real

        self.assertEqual(len(found), microcode.PROGRAM_WORDS)

    def test_it_asks_the_model_for_the_mask_it_was_given(self) -> None:
        asked: list[str] = []
        real = hardware.load
        hardware.load = lambda package: _Loaded(asked)
        try:
            microcode.program_of("dsp1")
        finally:
            hardware.load = real

        self.assertEqual(asked, ["dsp1"])


class MaskTest(unittest.TestCase):
    def test_the_project_reproduces_the_uncorrected_part(self) -> None:
        self.assertEqual(microcode.MASK, "dsp1")


class MainTest(unittest.TestCase):
    def test_a_named_mask_is_reported_on(self) -> None:
        said: list[str] = []
        built = program(tree(0x100, 0x200))

        code = microcode.main(("dsp1",), say=said.append, read=lambda _: built)

        self.assertEqual(code, 0)

    def test_a_named_mask_reports_its_handlers(self) -> None:
        said: list[str] = []
        built = program(tree(0x100, 0x200))

        microcode.main(("dsp1",), say=said.append, read=lambda _: built)

        self.assertTrue(any("$0100" in one for one in said))

    def test_with_no_image_it_says_so(self) -> None:
        said: list[str] = []

        self.assertEqual(microcode.main((), say=said.append), 2)

    def test_with_no_image_it_prints_a_usage_line(self) -> None:
        said: list[str] = []

        microcode.main((), say=said.append)

        self.assertTrue(said)


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "microcode.py").exists())


if __name__ == "__main__":
    unittest.main()
