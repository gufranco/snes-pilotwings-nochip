import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import cycles  # noqa: E402


def _image(program: bytes = b"", at: int = 0x0000) -> bytes:
    out = bytearray(0x8000)
    out[at : at + len(program)] = program
    return bytes(out)


def _wram() -> bytearray:
    return bytearray(0x20000)


class MemoryTest(unittest.TestCase):
    def test_the_cartridge_answers_above_its_half_way_mark(self) -> None:
        memory = cycles.Memory(_image(b"\xab"), _wram())

        self.assertEqual(memory.read8(0x008000), 0xAB)

    def test_the_second_view_of_a_bank_answers_the_same_bytes(self) -> None:
        memory = cycles.Memory(_image(b"\xab"), _wram())

        self.assertEqual(memory.read8(0x808000), memory.read8(0x008000))

    def test_past_the_end_of_the_image_answers_nought(self) -> None:
        memory = cycles.Memory(_image(), _wram())

        self.assertEqual(memory.read8(0x7D8000), 0)

    def test_below_the_half_way_mark_and_outside_memory_answers_nought(self) -> None:
        memory = cycles.Memory(_image(), _wram())

        self.assertEqual(memory.read8(0x407000), 0)

    def test_the_console_s_own_banks_answer_the_snapshot(self) -> None:
        wram = _wram()
        wram[0x00010] = 0x5A
        wram[0x10010] = 0xA5
        memory = cycles.Memory(_image(), wram)

        self.assertEqual((memory.read8(0x7E0010), memory.read8(0x7F0010)), (0x5A, 0xA5))

    def test_the_first_eight_kilobytes_show_again_at_the_bottom_of_a_bank(self) -> None:
        wram = _wram()
        wram[0x0420] = 0x77
        memory = cycles.Memory(_image(), wram)

        self.assertEqual((memory.read8(0x000420), memory.read8(0x3F0420)), (0x77, 0x77))

    def test_that_mirror_reaches_the_second_view_of_those_banks_too(self) -> None:
        wram = _wram()
        wram[0x0420] = 0x77
        memory = cycles.Memory(_image(), wram)

        self.assertEqual(memory.read8(0xB00420), 0x77)

    def test_a_write_to_memory_lands_in_the_snapshot(self) -> None:
        memory = cycles.Memory(_image(), _wram())

        memory.write8(0x7E1234, 0x99)

        self.assertEqual(memory.wram[0x1234], 0x99)

    def test_a_write_to_the_cartridge_changes_nothing(self) -> None:
        memory = cycles.Memory(_image(b"\xab"), _wram())

        memory.write8(0x008000, 0x00)

        self.assertEqual(memory.read8(0x008000), 0xAB)


class MultiplierTest(unittest.TestCase):
    def test_writing_both_operands_gives_their_product(self) -> None:
        memory = cycles.Memory(_image(), _wram())

        memory.write8(cycles.MULTIPLICAND, 7)
        memory.write8(cycles.MULTIPLIER, 6)

        self.assertEqual(memory.read8(cycles.PRODUCT), 42)

    def test_the_product_reads_back_as_two_bytes(self) -> None:
        memory = cycles.Memory(_image(), _wram())

        memory.write8(cycles.MULTIPLICAND, 200)
        memory.write8(cycles.MULTIPLIER, 200)

        got = memory.read8(cycles.PRODUCT) | memory.read8(cycles.PRODUCT + 1) << 8
        self.assertEqual(got, 40000)

    def test_a_second_multiplier_reuses_the_first_operand(self) -> None:
        memory = cycles.Memory(_image(), _wram())

        memory.write8(cycles.MULTIPLICAND, 3)
        memory.write8(cycles.MULTIPLIER, 4)
        memory.write8(cycles.MULTIPLIER, 5)

        self.assertEqual(memory.read8(cycles.PRODUCT), 15)


class SymbolTest(unittest.TestCase):
    def test_it_reads_a_plain_line(self) -> None:
        self.assertEqual(cycles.symbol("ground_block", "ground_block at   908123\n"), 0x908123)

    def test_it_reads_a_line_meant_for_the_patcher(self) -> None:
        self.assertEqual(cycles.symbol("dsp_write", "SYM dsp_write 90ABCD\n"), 0x90ABCD)

    def test_a_name_the_log_does_not_carry_is_refused(self) -> None:
        with self.assertRaises(cycles.Missing):
            cycles.symbol("nowhere", "ground_block at 908123\n")

    def test_a_short_line_is_stepped_over(self) -> None:
        self.assertEqual(cycles.symbol("one", "\nnoise\none at 4242\n"), 0x4242)


class UnbuiltTest(unittest.TestCase):
    def test_the_cached_constants_are_made_to_match_nothing(self) -> None:
        wram = bytes(0x10000)

        out = cycles.unbuilt(wram)

        self.assertEqual(out[0x0DC8:0x0DD0], b"\xff" * 8)

    def test_the_word_that_says_the_pads_are_written_is_cleared(self) -> None:
        wram = bytearray(0x10000)
        wram[0x0DD0] = 0x7E
        wram[0x0DD1] = 0xA5

        out = cycles.unbuilt(bytes(wram))

        self.assertEqual((out[0x0DD0], out[0x0DD1]), (0x00, 0x00))

    def test_the_tables_are_filled_with_the_power_on_byte(self) -> None:
        out = cycles.unbuilt(bytes(0x10000))

        self.assertEqual(set(out[0xE000:0x10000]), {0x55})

    def test_everything_else_is_left_as_it_was(self) -> None:
        wram = bytearray(0x10000)
        wram[0x0420] = 0x33

        out = cycles.unbuilt(bytes(wram))

        self.assertEqual(out[0x0420], 0x33)


class CostTest(unittest.TestCase):
    def test_a_routine_that_returns_at_once_costs_one_instruction(self) -> None:
        image = _image(bytes((0x6B,)))

        spent, steps, _ = cycles.cost(image, "one at 008000\n", bytearray(0x20000), "one")

        self.assertEqual(steps, 1)
        self.assertGreater(spent, 0)

    def test_it_reports_the_memory_the_call_left_behind(self) -> None:
        image = _image(bytes((0xA9, 0x77, 0x00, 0x8D, 0x20, 0x04, 0x6B)))

        _, _, wram = cycles.cost(image, "one at 008000\n", bytearray(0x20000), "one")

        self.assertEqual(wram[0x0420], 0x77)

    def test_a_routine_that_never_returns_stops_at_the_bound(self) -> None:
        forever = _image(bytes((0x80, 0xFE)))

        _, steps, _ = cycles.cost(forever, "one at 008000\n", bytearray(0x20000), "one", most=5)

        self.assertEqual(steps, 5)

    def test_a_longer_routine_costs_more_than_a_shorter_one(self) -> None:
        short = _image(bytes((0x6B,)))
        long = _image(bytes((0xEA, 0xEA, 0xEA, 0x6B)))

        one, _, _ = cycles.cost(short, "one at 008000\n", bytearray(0x20000), "one")
        two, _, _ = cycles.cost(long, "one at 008000\n", bytearray(0x20000), "one")

        self.assertGreater(two, one)


class MainTest(unittest.TestCase):
    def test_with_no_arguments_it_says_how_to_call_it(self) -> None:
        said: list[str] = []

        code = cycles.main((), say=said.append)

        self.assertEqual(code, 2)
        self.assertTrue(said[0].startswith("usage:"))

    def test_a_missing_snapshot_is_reported_rather_than_raised(self) -> None:
        into = ROOT / "build" / "cycles-test"
        into.mkdir(parents=True, exist_ok=True)
        (into / "one.sfc").write_bytes(_image(bytes((0x6B,))))
        (into / "one.log").write_text("one at 008000\n")
        said: list[str] = []

        code = cycles.main(
            (str(into / "one.sfc"), str(into / "one.log"), "one", str(into / "nothing.bin")),
            say=said.append,
        )

        self.assertEqual(code, 1)
        self.assertIn("no memory snapshot", said[0])

    def test_it_reports_the_cost_of_the_named_routine(self) -> None:
        into = ROOT / "build" / "cycles-test"
        into.mkdir(parents=True, exist_ok=True)
        (into / "one.sfc").write_bytes(_image(bytes((0x6B,))))
        (into / "one.log").write_text("one at 008000\n")
        (into / "snap.bin").write_bytes(bytes(0x20000))
        said: list[str] = []

        code = cycles.main(
            (str(into / "one.sfc"), str(into / "one.log"), "one", str(into / "snap.bin")),
            say=said.append,
        )

        self.assertEqual(code, 0)
        self.assertIn("cycles", said[0])


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "tools" / "cycles.py").exists())


if __name__ == "__main__":
    unittest.main()
