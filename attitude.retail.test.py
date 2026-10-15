import unittest
from pathlib import Path
from typing import Any, override

import attitude
import derived
import hardware

MISSING = hardware.load("snesdsp").NoFirmware

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
SETUP = 0x02
ANSWERS = 4

STEP = 2048


def _tables() -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    sine, cosine = BUILD / "sine.bin", BUILD / "cosine.bin"
    if not (sine.with_name("sine-0.bin").exists() and cosine.with_name("cosine-0.bin").exists()):
        return None
    return derived.pieces(sine), derived.pieces(cosine)


def _part() -> Any:
    try:
        return hardware.load("snesdsp").Chip("dsp1")
    except MISSING:
        return None


class MatrixAgainstThePartTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tables = _tables()
        if tables is None:
            self.skipTest("no sine or cosine table in build; run derived.py first")
        self.sine, self.cosine = tables
        part = _part()
        if part is None:
            self.skipTest("no part image on this machine")
        self.part = part

    def test_every_cell_agrees_on_a_grid_that_reaches_the_corners(self) -> None:
        tried = 0
        for six in range(0, 0x10000, STEP):
            for five in range(0, 0x10000, STEP):
                derived.ask(self.part, SETUP, (0, 0, 0, 0, 0, five, six), ANSWERS)
                want = {
                    cell: self.part.core.stores.scratch[cell] for cell in attitude.CELLS.values()
                }

                got = attitude.matrix(self.sine, self.cosine, five, six)

                self.assertEqual(got, want, f"arg5 {five:#06x} arg6 {six:#06x}")
                tried += 1
        self.assertEqual(tried, (0x10000 // STEP) ** 2)

    def test_half_a_turn_is_the_angle_the_table_alone_gets_wrong(self) -> None:
        five, six = attitude.HALF_TURN, attitude.HALF_TURN
        derived.ask(self.part, SETUP, (0, 0, 0, 0, 0, five, six), ANSWERS)
        want = self.part.core.stores.scratch[attitude.CELLS["row1col1"]]

        plain = attitude.product(
            attitude.signed(self.cosine[five]), attitude.signed(self.cosine[six])
        )

        self.assertNotEqual(plain, want)
        self.assertEqual(attitude.matrix(self.sine, self.cosine, five, six)[0x6B], want)


if __name__ == "__main__":
    unittest.main()
