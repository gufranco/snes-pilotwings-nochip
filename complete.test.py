import unittest
from pathlib import Path
from typing import Any, override

import complete
import hardware

ROOT = Path(__file__).resolve().parent


class _Exchange:
    def __init__(self, command: int, words: tuple[int, ...], answer: tuple[int, ...]) -> None:
        self.command = command
        self.words = words
        self.answer = answer


class _Part:
    def __init__(self, answer: tuple[int, ...] = (9, 8, 7)) -> None:
        self.answer = answer
        self.written: list[int] = []
        self.given: list[int] = []

    @property
    def asking(self) -> bool:
        return bool(self.given)

    def write(self, byte: int) -> None:
        self.written.append(byte)

    def step(self, _cycles: int) -> None:
        if not self.given:
            self.given = [half for word in self.answer for half in (word & 0xFF, word >> 8)]

    def read(self) -> int:
        return self.given.pop(0)


class _Slow(_Part):
    def __init__(self, answer: tuple[int, ...], quiet: int) -> None:
        super().__init__(answer)
        self.quiet = quiet

    @override
    def step(self, cycles: int) -> None:
        if self.quiet:
            self.quiet -= 1
            return
        super().step(cycles)


class _Silent(_Part):
    @override
    def step(self, cycles: int) -> None:
        return


class _Loaded:
    def __init__(self, part: _Part) -> None:
        self.part = part

    def Chip(self, _mask: str) -> _Part:
        return self.part


class DomainTest(unittest.TestCase):
    def test_it_collects_every_value_a_word_took(self) -> None:
        run = (_Exchange(0x18, (1, 5, 2, 32), (9,)), _Exchange(0x18, (3, 5, 2, 32), (8,)))

        found = complete.domains((run,))

        self.assertEqual(found[0x18][0], (1, 3))

    def test_a_word_that_never_changes_has_one_value(self) -> None:
        run = (_Exchange(0x18, (1, 5, 2, 32), (9,)), _Exchange(0x18, (3, 5, 2, 32), (8,)))

        found = complete.domains((run,))

        self.assertEqual(found[0x18][3], (32,))

    def test_a_command_that_is_not_completable_is_left_out(self) -> None:
        run = (_Exchange(0x06, (1, 2, 3), (9,)),)

        self.assertEqual(complete.domains((run,)), {})

    def test_a_carrier_joins_the_key(self) -> None:
        run = (
            _Exchange(0x11, (7, 8, 9, 10), ()),
            _Exchange(0x13, (0, 1, 2), (9, 8, 7)),
        )

        found = complete.domains((run,))

        self.assertEqual(len(found[0x13]), 7)

    def test_the_three_regions_are_pooled(self) -> None:
        one = (_Exchange(0x18, (1, 5, 2, 32), (9,)),)
        two = (_Exchange(0x18, (4, 5, 2, 32), (8,)),)

        found = complete.domains((one, two))

        self.assertEqual(found[0x18][0], (1, 4))


class WantedTest(unittest.TestCase):
    def test_it_is_every_combination(self) -> None:
        self.assertEqual(len(complete.wanted(((1, 2), (3, 4, 5)))), 6)

    def test_one_value_per_word_is_one_key(self) -> None:
        self.assertEqual(complete.wanted(((1,), (2,))), ((1, 2),))


class FilledTest(unittest.TestCase):
    def test_a_recorded_row_is_kept_rather_than_asked_again(self) -> None:
        real = hardware.load
        hardware.load = lambda package: _Loaded(_Part((1,)))
        try:
            found = complete.filled(0x18, (((1, 5, 2, 32)),), 1, {(1, 5, 2, 32): (77,)})
        finally:
            hardware.load = real

        self.assertEqual(found[(1, 5, 2, 32)], (77,))

    def test_a_missing_row_comes_from_the_part(self) -> None:
        real = hardware.load
        hardware.load = lambda package: _Loaded(_Part((1,)))
        try:
            found = complete.filled(0x18, (((2, 5, 2, 32)),), 1, {})
        finally:
            hardware.load = real

        self.assertEqual(found[(2, 5, 2, 32)], (1,))

    def test_every_key_in_the_domain_ends_up_present(self) -> None:
        keys = ((1, 5, 2, 32), (2, 5, 2, 32), (3, 5, 2, 32))
        real = hardware.load
        hardware.load = lambda package: _Loaded(_Part((4,)))
        try:
            found = complete.filled(0x18, keys, 1, {})
        finally:
            hardware.load = real

        self.assertEqual(sorted(found), sorted(keys))

    def test_a_carrier_is_written_before_the_command(self) -> None:
        part = _Part((5, 6, 7))
        real = hardware.load
        hardware.load = lambda package: _Loaded(part)
        try:
            complete.filled(0x13, ((0, 1, 2, 7, 8, 9, 10),), 3, {})
        finally:
            hardware.load = real

        self.assertEqual(part.written[0], 0x11)

    def test_it_reports_progress_when_asked(self) -> None:
        said: list[str] = []
        real = hardware.load
        hardware.load = lambda package: _Loaded(_Part((1,)))
        try:
            complete.filled(0x18, (((1, 5, 2, 32)),), 1, {}, say=said.append)
        finally:
            hardware.load = real

        self.assertTrue(said)


class AskTest(unittest.TestCase):
    def test_it_waits_for_a_part_that_is_not_ready_at_once(self) -> None:
        found = complete.ask(_Slow((7,), quiet=3), 0x18, (1, 2), 1)

        self.assertEqual(found, (7,))

    def test_a_part_that_never_answers_gives_nothing(self) -> None:
        found = complete.ask(_Silent((7,)), 0x18, (1, 2), 1)

        self.assertEqual(found, ())


class ReportTest(unittest.TestCase):
    def test_it_names_every_command(self) -> None:
        lines = complete.report({0x13: (244, 1512)})

        self.assertTrue(any("$13" in one for one in lines))

    def test_it_says_how_many_were_filled_in(self) -> None:
        lines = complete.report({0x13: (244, 1512)})

        self.assertTrue(any("1,268" in one for one in lines))


class GatherTest(unittest.TestCase):
    def test_it_reads_every_region_from_disk(self) -> None:
        into = ROOT / "build" / "complete-test"
        into.mkdir(parents=True, exist_ok=True)
        for region in complete.REGIONS:
            (into / f"trace-{region}.bin").write_bytes(b"")

        found: tuple[Any, ...] = complete.gather(into)

        self.assertEqual(len(found), 3)


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "complete.py").exists())


if __name__ == "__main__":
    unittest.main()
