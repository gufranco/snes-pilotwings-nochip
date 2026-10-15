import subprocess
import unittest
from pathlib import Path
from typing import override

import hardware
import routines

MISSING = hardware.load("snesdsp").NoFirmware

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
IMAGE = BUILD / "ops.sfc"
SOURCE = ROOT / "asm" / "ops-check.asm"

IMAGE_BYTES = 4 * 1024 * 1024

ASSEMBLER = "pilotwings-asar-191"

TRIED = 400

CASES = (
    ("$00", 0x00, 2, 1, "op_00"),
    ("$08", 0x08, 3, 2, "op_08"),
    ("$04", 0x04, 2, 2, "op_04"),
)


def assembled() -> dict[str, int] | None:
    BUILD.mkdir(exist_ok=True)
    IMAGE.write_bytes(bytes(IMAGE_BYTES))
    try:
        done = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{ROOT}:/work",
                "-w",
                "/work",
                ASSEMBLER,
                "--no-title-check",
                str(SOURCE.relative_to(ROOT)),
                str(IMAGE.relative_to(ROOT)),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    where: dict[str, int] = {}
    for line in done.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == "at":
            where[parts[0]] = int(parts[2], 16)
    return where or None


class AgainstThePartTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        found = assembled()
        if found is None:
            self.skipTest("the assembler image is not on this machine")
        try:
            routines.asked(0x00, (1, 1), 1)
        except MISSING:
            self.skipTest("no microcode on this machine")
        self.where: dict[str, int] = found
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
        for name, _, takes, gives, label in CASES:
            entry = self.where[label]
            for words in routines.inputs(takes, 8, seed=1):
                try:
                    routines.run(self.image, entry, words, gives)
                except routines.TooLong as raised:
                    self.fail(f"{name}: {raised}")


if __name__ == "__main__":
    unittest.main()
