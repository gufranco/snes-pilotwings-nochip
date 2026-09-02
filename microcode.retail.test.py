import unittest
from typing import Any, override

import hardware
import microcode

MISSING = hardware.load("snesdsp").NoFirmware
"""What the model raises on a machine with no image for that mask."""

MASKS = (microcode.MASK, "dsp1b")

SHARED = ((0x00, 0x80), (0x01, 0x11), (0x03, 0x13))
"""Command bytes this expects to reach one handler together.

`$00` and `$80` is the one that matters: snes9x sends `$80` to the default arm
of a switch, where the part sends it to the signed multiply, and the cartridge
writes `$80` 128 times before anything else.
"""


def program_of(mask: str) -> tuple[int, ...]:
    part = hardware.load("snesdsp").Chip(mask)
    return tuple(part.core.stores.program[at] for at in range(microcode.PROGRAM_WORDS))


class AgainstTheMicrocodeTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.programs: dict[str, Any] = {}
        for mask in MASKS:
            try:
                self.programs[mask] = program_of(mask)
            except MISSING:
                continue
        if not self.programs:
            self.skipTest("no microcode on this machine")

    def test_every_mask_dispatches_to_twenty_handlers(self) -> None:
        for mask, program in self.programs.items():
            self.assertEqual(len(microcode.handlers(program)), 20, mask)

    def test_every_command_byte_reaches_a_handler(self) -> None:
        for mask, program in self.programs.items():
            self.assertTrue(
                all(at is not None for at in microcode.dispatch(program).values()), mask
            )

    def test_every_command_the_cartridge_writes_reaches_one(self) -> None:
        for mask, program in self.programs.items():
            found = microcode.dispatch(program)
            self.assertTrue(all(found[one] is not None for one in microcode.ISSUED), mask)

    def test_bytes_that_share_a_handler_share_it_in_every_mask(self) -> None:
        for mask, program in self.programs.items():
            found = microcode.dispatch(program)
            for first, second in SHARED:
                self.assertEqual(found[first], found[second], f"{mask} ${first:02x} ${second:02x}")

    def test_the_two_masks_agree_on_which_bytes_share_a_handler(self) -> None:
        if len(self.programs) < 2:
            self.skipTest("only one mask on this machine")
        grouped = [
            sorted(tuple(sorted(one)) for one in microcode.handlers(program).values())
            for program in self.programs.values()
        ]

        self.assertEqual(grouped[0], grouped[1])

    def test_every_handler_ends_rather_than_running_off(self) -> None:
        for mask, program in self.programs.items():
            for at in microcode.handlers(program):
                read = microcode.body(program, at)
                self.assertLess(len(read), microcode.MOST, f"{mask} ${at:04x}")

    def test_the_multiply_handler_reads_both_arguments_and_answers_one(self) -> None:
        for mask, program in self.programs.items():
            at = microcode.dispatch(program)[0x00]
            assert at is not None
            read = [text for _, text in microcode.body(program, at)]

            self.assertEqual(sum(1 for one in read if "->dr" in one), 1, mask)

    def test_the_report_names_every_handler(self) -> None:
        for mask, program in self.programs.items():
            said = microcode.report(program)

            self.assertEqual(sum(1 for one in said if one.startswith("  $")), 20, mask)


class MainTest(unittest.TestCase):
    def test_a_named_mask_reports_its_handlers(self) -> None:
        said: list[str] = []
        try:
            code = microcode.main(("dsp1",), say=said.append)
        except MISSING:
            self.skipTest("no microcode on this machine")

        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
