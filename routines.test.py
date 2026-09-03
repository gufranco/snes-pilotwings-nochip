import unittest
from pathlib import Path

import hardware
import routines

ROOT = Path(__file__).resolve().parent


class _Part:
    """A stand in for the chip, so the reader can be exercised with no microcode.

    It takes a command and its arguments, then hands back the words it was told
    to, one byte at a time, the way the real port does.
    """

    def __init__(self, gives: tuple[int, ...]) -> None:
        self.bytes = [byte for word in gives for byte in (word & 0xFF, word >> 8)]
        self.written: list[int] = []

    def write(self, value: int) -> None:
        self.written.append(value)

    def step(self, count: int) -> None:
        pass

    @property
    def asking(self) -> bool:
        return bool(self.bytes)

    def read(self) -> int:
        return self.bytes.pop(0)


class _Loaded:
    def __init__(self, gives: tuple[int, ...], asked: list[str] | None = None) -> None:
        self.gives = gives
        self.asked = asked

    def Chip(self, mask: str) -> _Part:
        if self.asked is not None:
            self.asked.append(mask)
        return _Part(self.gives)


RTL = 0x6B
"""One `rtl`, which returns from a routine called across banks."""

LDA_IMMEDIATE = 0xA9
STA_DIRECT = 0x85
STA_LONG = 0x8F


def image_of(code: bytes) -> bytes:
    """An image with that code where ops-check.asm places its routines."""
    return bytes(routines.FILE_AT) + code + bytes(routines.SPAN)


class ConsoleTest(unittest.TestCase):
    def test_an_ordinary_address_reads_back_what_was_written(self) -> None:
        memory = routines.Console()

        memory.write8(0x7E1234, 0x42)

        self.assertEqual(memory.read8(0x7E1234), 0x42)

    def test_an_address_never_written_reads_as_nothing(self) -> None:
        self.assertEqual(routines.Console().read8(0x7E1234), 0)

    def test_writing_both_operands_forms_the_product(self) -> None:
        memory = routines.Console()

        memory.write8(routines.MULTIPLICAND, 12)
        memory.write8(routines.MULTIPLIER, 12)

        self.assertEqual(memory.read8(routines.PRODUCT), 144)

    def test_the_product_reaches_sixteen_bits(self) -> None:
        memory = routines.Console()

        memory.write8(routines.MULTIPLICAND, 0xFF)
        memory.write8(routines.MULTIPLIER, 0xFF)

        low = memory.read8(routines.PRODUCT)
        high = memory.read8(routines.PRODUCT + 1)
        self.assertEqual(low | high << 8, 0xFE01)

    def test_the_second_operand_is_what_starts_the_multiply(self) -> None:
        memory = routines.Console()

        memory.write8(routines.MULTIPLICAND, 5)

        self.assertEqual(memory.read8(routines.PRODUCT), 0)


class CartridgeReadTest(unittest.TestCase):
    def test_an_address_in_a_cartridge_bank_reads_from_the_image(self) -> None:
        memory = routines.Console(bytes(range(256)) * 4)

        self.assertEqual(memory.read8(0x008000), 0)

    def test_a_later_bank_reads_further_into_the_image(self) -> None:
        memory = routines.Console(bytes([7]) * 0x20000)

        self.assertEqual(memory.read8(0x018000), 7)

    def test_past_the_end_of_the_image_reads_as_nothing(self) -> None:
        memory = routines.Console(bytes([7]) * 16)

        self.assertEqual(memory.read8(0x208000), 0)

    def test_something_written_wins_over_the_image(self) -> None:
        memory = routines.Console(bytes([7]) * 0x10000)

        memory.write8(0x008000, 3)

        self.assertEqual(memory.read8(0x008000), 3)

    def test_below_the_window_reads_as_nothing(self) -> None:
        memory = routines.Console(bytes([7]) * 0x10000)

        self.assertEqual(memory.read8(0x000123), 0)


def _long(value: int) -> tuple[int, int, int]:
    return value & 0xFF, value >> 8 & 0xFF, value >> 16


class RunTest(unittest.TestCase):
    def test_a_routine_that_returns_at_once_answers_nothing(self) -> None:
        found = routines.run(image_of(bytes([RTL])), routines.CODE, (), 0)

        self.assertEqual(found, ())

    def test_a_routine_that_stores_a_word_answers_it(self) -> None:
        code = bytes([LDA_IMMEDIATE, 0x34, STA_LONG, *_long(routines.OUT), RTL])

        found = routines.run(image_of(code), routines.CODE, (), 1)

        self.assertEqual(found[0] & 0xFF, 0x34)

    def test_a_routine_that_never_returns_is_a_defect(self) -> None:
        loop = bytes([0x80, 0xFE])

        with self.assertRaises(routines.TooLong):
            routines.run(image_of(loop), routines.CODE, (), 0)

    def test_the_arguments_land_where_a_routine_reads_them(self) -> None:
        code = bytes([0xA5, routines.ARG, STA_LONG, *_long(routines.OUT), RTL])

        found = routines.run(image_of(code), routines.CODE, (0x0055,), 1)

        self.assertEqual(found[0] & 0xFF, 0x55)


class AskedTest(unittest.TestCase):
    def test_it_returns_the_words_the_part_gave(self) -> None:
        real = hardware.load
        hardware.load = lambda package: _Loaded((0x1234, 0x5678))
        try:
            found = routines.asked(0x02, (1, 2), 2)
        finally:
            hardware.load = real

        self.assertEqual(found, (0x1234, 0x5678))

    def test_it_asks_the_mask_it_was_given(self) -> None:
        asked: list[str] = []
        real = hardware.load
        hardware.load = lambda package: _Loaded((1,), asked)
        try:
            routines.asked(0x00, (1, 1), 1, mask="dsp1")
        finally:
            hardware.load = real

        self.assertEqual(asked, ["dsp1"])

    def test_a_part_that_says_nothing_answers_nothing(self) -> None:
        real = hardware.load
        hardware.load = lambda package: _Loaded(())
        try:
            found = routines.asked(0x01, (1, 2, 3, 4), 0)
        finally:
            hardware.load = real

        self.assertEqual(found, ())


class InputsTest(unittest.TestCase):
    def test_it_yields_as_many_sets_as_asked(self) -> None:
        self.assertEqual(len(list(routines.inputs(2, 7, seed=1))), 7)

    def test_each_set_has_as_many_words_as_asked(self) -> None:
        found = next(iter(routines.inputs(3, 1, seed=1)))

        self.assertEqual(len(found), 3)

    def test_every_word_fits_sixteen_bits(self) -> None:
        for one in routines.inputs(3, 40, seed=1):
            for word in one:
                self.assertLess(word, 0x10000)

    def test_the_same_seed_gives_the_same_sets(self) -> None:
        first = list(routines.inputs(2, 5, seed=9))
        again = list(routines.inputs(2, 5, seed=9))

        self.assertEqual(first, again)

    def test_a_different_seed_gives_different_sets(self) -> None:
        first = list(routines.inputs(2, 5, seed=9))
        other = list(routines.inputs(2, 5, seed=10))

        self.assertNotEqual(first, other)


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "routines.py").exists())

    def test_the_routines_it_runs_are_here(self) -> None:
        self.assertTrue((ROOT / "asm" / "dsp1-ops.asm").exists())


if __name__ == "__main__":
    unittest.main()
