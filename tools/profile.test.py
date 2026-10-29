import sys
import unittest
from pathlib import Path
from typing import override

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import script  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))

import profile as profiler  # noqa: E402

SYMBOLS = """; wla symbolic information file

[labels]
90:8000 :ground_block
90:8100 :ground_line
90:8200 :macro_7_again
90:8300 :0004:00000123
"""


class TypedTest(unittest.TestCase):
    def test_it_finds_a_label_a_source_file_declares(self) -> None:
        self.assertIn("ground_line", profiler.typed(ROOT))

    def test_it_leaves_out_a_name_no_source_file_declares(self) -> None:
        self.assertNotIn("macro_7_again", profiler.typed(ROOT))


class MarksTest(unittest.TestCase):
    def test_it_keeps_only_the_labels_asked_for(self) -> None:
        placed = profiler.marks(SYMBOLS, {"ground_block", "ground_line"})

        self.assertEqual(placed, [(0x908000, "ground_block"), (0x908100, "ground_line")])

    def test_it_drops_the_assembler_s_own_anonymous_names(self) -> None:
        placed = profiler.marks(SYMBOLS, {"ground_block"})

        self.assertEqual([name for _, name in placed], ["ground_block"])

    def test_it_returns_them_in_address_order(self) -> None:
        placed = profiler.marks(
            "90:8100 :ground_line\n90:8000 :ground_block\n", {"ground_block", "ground_line"}
        )

        self.assertEqual([at for at, _ in placed], [0x908000, 0x908100])

    def test_a_file_with_no_labels_gives_nothing(self) -> None:
        self.assertEqual(profiler.marks("; nothing here\n", {"ground_block"}), [])


class OwnerTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.placed = [(0x908000, "one"), (0x908100, "two"), (0x908200, "three")]

    def test_an_address_on_a_label_belongs_to_it(self) -> None:
        self.assertEqual(profiler.owner(self.placed, 0x908100), "two")

    def test_an_address_after_a_label_belongs_to_it(self) -> None:
        self.assertEqual(profiler.owner(self.placed, 0x9080FF), "one")

    def test_an_address_past_the_last_label_belongs_to_it(self) -> None:
        self.assertEqual(profiler.owner(self.placed, 0x90FFFF), "three")

    def test_an_address_below_every_label_belongs_to_none(self) -> None:
        self.assertEqual(profiler.owner(self.placed, 0x900000), "?")

    def test_no_labels_at_all_gives_none(self) -> None:
        self.assertEqual(profiler.owner([], 0x908000), "?")


def _image(program: bytes) -> bytes:
    out = bytearray(0x8000)
    out[0 : len(program)] = program
    return bytes(out)


class SpendTest(unittest.TestCase):
    def test_it_charges_a_call_to_the_routine_that_ran(self) -> None:
        image = _image(bytes((0xEA, 0xEA, 0x6B)))
        placed = [(0x008000, "one")]

        took, ran, total = profiler.spend(
            image, "one at 008000\n", bytearray(0x20000), "one", placed
        )

        self.assertEqual((took["one"], ran["one"]), (total, 3))

    def test_it_splits_the_cost_between_two_routines(self) -> None:
        image = _image(bytes((0xEA, 0xEA, 0x6B)))
        placed = [(0x008000, "one"), (0x008002, "two")]

        took, _, total = profiler.spend(image, "one at 008000\n", bytearray(0x20000), "one", placed)

        self.assertEqual(sorted(took), ["one", "two"])
        self.assertEqual(took["one"] + took["two"], total)

    def test_the_total_is_the_sum_of_the_parts(self) -> None:
        image = _image(bytes((0xA9, 0x01, 0x00, 0xEA, 0x6B)))
        placed = [(0x008000, "one"), (0x008003, "two")]

        took, _, total = profiler.spend(image, "one at 008000\n", bytearray(0x20000), "one", placed)

        self.assertEqual(sum(took.values()), total)


class ReportTest(unittest.TestCase):
    def test_it_names_the_dearest_routine_first(self) -> None:
        said: list[str] = []

        profiler.report({"cheap": 10, "dear": 90}, {"cheap": 1, "dear": 9}, 100, said.append)

        self.assertIn("dear", said[1])
        self.assertIn("cheap", said[2])

    def test_it_prints_a_share_of_the_total(self) -> None:
        said: list[str] = []

        profiler.report({"one": 50}, {"one": 5}, 100, said.append)

        self.assertIn("50.0%", said[1])

    def test_it_ends_with_the_total(self) -> None:
        said: list[str] = []

        profiler.report({"one": 50, "two": 50}, {"one": 5, "two": 5}, 100, said.append)

        self.assertIn("100", said[-1])
        self.assertIn("100.0%", said[-1])


class MainTest(unittest.TestCase):
    def _scratch(self) -> Path:
        into = ROOT / "build" / "profile-test"
        into.mkdir(parents=True, exist_ok=True)
        return into

    def test_with_no_arguments_it_says_how_to_call_it(self) -> None:
        said: list[str] = []

        code = profiler.main((), say=said.append)

        self.assertEqual(code, 2)
        self.assertTrue(said[0].startswith("usage:"))

    def test_a_missing_snapshot_is_reported_rather_than_raised(self) -> None:
        into = self._scratch()
        (into / "one.sfc").write_bytes(_image(bytes((0x6B,))))
        (into / "one.sym").write_text("90:8000 :ground_block\n")
        said: list[str] = []

        code = profiler.main(
            (
                str(into / "one.sfc"),
                str(into / "one.sym"),
                "ground_block",
                str(into / "nothing.bin"),
            ),
            say=said.append,
        )

        self.assertEqual(code, 1)
        self.assertIn("no memory snapshot", said[0])

    def test_a_symbol_file_with_no_source_labels_is_refused(self) -> None:
        into = self._scratch()
        (into / "one.sfc").write_bytes(_image(bytes((0x6B,))))
        (into / "bare.sym").write_text("90:8000 :macro_7_again\n")
        (into / "snap.bin").write_bytes(bytes(0x20000))
        said: list[str] = []

        code = profiler.main(
            (str(into / "one.sfc"), str(into / "bare.sym"), "ground_block", str(into / "snap.bin")),
            say=said.append,
        )

        self.assertEqual(code, 1)
        self.assertIn("no source-level labels", said[0])

    def test_it_reports_the_routine_it_was_asked_about(self) -> None:
        into = self._scratch()
        out = bytearray(0x8000)
        out[0] = 0x6B
        (into / "one.sfc").write_bytes(bytes(out))
        (into / "one.sym").write_text("90:8000 :ground_block\n")
        (into / "snap.bin").write_bytes(bytes(0x20000))
        said: list[str] = []

        code = profiler.main(
            (str(into / "one.sfc"), str(into / "one.sym"), "ground_block", str(into / "snap.bin")),
            say=said.append,
        )

        self.assertEqual(code, 0)
        self.assertIn("ground_block", said[0])
        self.assertIn("blank", said[0])

    def test_the_built_switch_is_reported_and_not_taken_as_a_path(self) -> None:
        into = self._scratch()
        out = bytearray(0x8000)
        out[0] = 0x6B
        (into / "one.sfc").write_bytes(bytes(out))
        (into / "one.sym").write_text("90:8000 :ground_block\n")
        (into / "snap.bin").write_bytes(bytes(0x20000))
        said: list[str] = []

        code = profiler.main(
            (
                str(into / "one.sfc"),
                str(into / "one.sym"),
                "ground_block",
                str(into / "snap.bin"),
                "--built",
            ),
            say=said.append,
        )

        self.assertEqual(code, 0)
        self.assertIn("built", said[0])


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "tools" / "profile.py").exists())


script.entry(__name__, unittest.main)
