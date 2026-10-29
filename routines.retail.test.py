import subprocess
import unittest
from pathlib import Path
from typing import override

import hardware
import microcode
import routines
import script
import toolchain

DSP = hardware.load("snesdsp")

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
IMAGE = BUILD / "ops.sfc"
SOURCE = ROOT / "asm" / "ops-check.asm"

IMAGE_BYTES = 4 * 1024 * 1024

TRIED = 400

CASES = (
    ("$00", 0x00, 2, 1, "op_00"),
    ("$08", 0x08, 3, 2, "op_08"),
    ("$04", 0x04, 2, 2, "op_04"),
)


def assemble() -> subprocess.CompletedProcess[str]:
    BUILD.mkdir(exist_ok=True)
    IMAGE.write_bytes(bytes(IMAGE_BYTES))
    return subprocess.run(
        toolchain.command(
            toolchain.ASSEMBLER,
            (),
            ["--no-title-check", str(SOURCE.relative_to(ROOT)), str(IMAGE.relative_to(ROOT))],
        ),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def placed(listing: str) -> dict[str, int]:
    rows = (line.split() for line in listing.splitlines())
    return {parts[0]: int(parts[2], 16) for parts in rows if len(parts) == 3 and parts[1] == "at"}


class PlacedTest(unittest.TestCase):
    def test_only_the_lines_naming_a_placement_are_read(self) -> None:
        # Arrange
        listing = "op_00 at 8123\nassembled 3 routines\nop_08 at 81F0\n"

        # Act
        found = placed(listing)

        # Assert
        self.assertEqual(found, {"op_00": 0x8123, "op_08": 0x81F0})


class AgainstThePartTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        script.skip_unless(microcode.MASK in DSP.available(), "no microcode on this machine")
        done = assemble()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.where: dict[str, int] = placed(done.stdout)
        self.image = IMAGE.read_bytes()

    def test_every_routine_was_placed(self) -> None:
        for _, _, _, _, label in CASES:
            self.assertIn(label, self.where, label)

    def test_every_routine_answers_what_the_part_answers(self) -> None:
        for name, command, takes, gives, label in CASES:
            entry = self.where[label]
            for words in routines.inputs(takes, TRIED, seed=command):
                mine = routines.run(self.image, entry, words, gives)
                theirs = routines.asked(command, words, gives)

                self.assertEqual(mine, theirs, f"{name} on {words}")

    def test_no_routine_runs_away(self) -> None:
        # Arrange
        asked = [
            (self.where[label], words, gives)
            for _, _, takes, gives, label in CASES
            for words in routines.inputs(takes, 8, seed=1)
        ]

        # Act
        answered = [routines.run(self.image, entry, words, gives) for entry, words, gives in asked]

        # Assert
        self.assertEqual(len(answered), len(asked))


script.entry(__name__, unittest.main)
