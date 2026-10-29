import unittest
from pathlib import Path
from typing import Any, override

import attitude
import derived
import hardware
import script

DSP = hardware.load("snesdsp")

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
SINE, COSINE = BUILD / "sine.bin", BUILD / "cosine.bin"
SETUP = 0x02
ANSWERS = 4

STEP = 2048


class MatrixAgainstThePartTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        tables = SINE.with_name("sine-0.bin").exists() and COSINE.with_name("cosine-0.bin").exists()
        script.skip_unless(tables, "no sine or cosine table in build; run derived.py first")
        script.skip_unless("dsp1" in DSP.available(), "no part image on this machine")
        self.sine, self.cosine = derived.pieces(SINE), derived.pieces(COSINE)
        self.part: Any = DSP.Chip("dsp1")

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


script.entry(__name__, unittest.main)
