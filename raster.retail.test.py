import unittest
from pathlib import Path
from typing import Any, override

import derived
import exchanges
import hardware
import parameter
import raster

ROOT = Path(__file__).resolve().parent

BUILD = ROOT / "build"

REGIONS = ("usa", "jp", "eur")

SETUP = 0x02
STREAM = 0x0A

MASK = "dsp1"

PAIRS_PER_REGION = 6

LOOP = 0x364

COUNTER = 0x09

STAGES = {
    "raw": 0x369,
    "held": 0x36B,
    "reciprocal": 0x36C,
    "first": 0x370,
    "scale one": 0x372,
    "scale two": 0x37B,
}


def _missing() -> str | None:
    if hardware.load("snesdsp").why_not():
        return "no microcode image, so the part cannot be run"
    if not all((BUILD / f"trace-{one}.bin").exists() for one in REGIONS):
        return "no recordings in build/, so there are no arguments to check against"
    return None


def _part() -> Any:
    return hardware.load("snesdsp").Chip(MASK)


def _pairs(region: str) -> list[tuple[tuple[int, ...], int, int]]:
    run = exchanges.taken((BUILD / f"trace-{region}.bin").read_bytes())
    found: list[tuple[tuple[int, ...], int, int]] = []
    last: tuple[int, ...] | None = None
    for one in run:
        if one.command == SETUP and len(one.words) == parameter.WORDS:
            last = one.words
        elif one.command == STREAM and last is not None and one.answer:
            found.append((last, one.words[0], len(one.answer)))
    step = max(1, len(found) // PAIRS_PER_REGION)
    return [found[at] for at in range(0, len(found), step)][:PAIRS_PER_REGION]


def _state(part: Any) -> dict[int, int]:
    return {at: derived.signed(part.core.stores.scratch[at]) for at in _CELLS}


_CELLS = (
    raster.STEP,
    raster.HORIZON,
    raster.FIRST_MANTISSA,
    raster.FIRST_EXPONENT,
    raster.SECOND_MANTISSA,
    raster.SECOND_EXPONENT,
    *raster.MATRIX,
)


def _stream(part: Any, first: int, count: int) -> tuple[int, ...]:
    part.write(STREAM)
    part.write(first & 0xFF)
    part.write(first >> 8)
    core = part.core
    host = part.console
    got: list[int] = []
    for _ in range(3_000_000):
        core.step()
        if core.registers.sr.rqm:
            got.append(host.read(0))
            if len(got) >= count * 2:
                break
    return tuple(got[k] | got[k + 1] << 8 for k in range(0, len(got) - 1, 2))


class Reciprocal(unittest.TestCase):
    @override
    def setUp(self) -> None:
        why = _missing()
        if why:
            self.skipTest(why)
        self.part = _part()

    def test_it_answers_every_value_the_normalise_loop_can_leave(self) -> None:
        table = derived.reciprocal(self.part, derived.NORMAL_LOW, derived.NORMAL_LOW + 64)

        self.assertEqual(len(table), 64)

    def test_a_negative_input_is_the_positive_one_negated(self) -> None:
        table = derived.reciprocal(self.part, 0x5000, 0x5001)

        self.assertEqual(derived.refined(self.part, 0xB000), -table[0])

    def test_the_exponent_is_one_less_the_one_handed_in(self) -> None:
        core = self.part.core
        for handed in (0, 1, 7, -2):
            core.registers.sp = 1
            core.registers.stack[0] = derived.SENTINEL
            core.registers.a = 0x6000
            core.registers.b = handed & 0xFFFF
            core.registers.pc = derived.RECIPROCAL_ENTRY
            while core.registers.pc != derived.SENTINEL:
                core.step()

            self.assertEqual(derived.signed(core.registers.word("b")), 1 - handed)


class Chain(unittest.TestCase):
    @override
    def setUp(self) -> None:
        why = _missing()
        if why:
            self.skipTest(why)
        self.table = derived.reciprocal(_part(), derived.NORMAL_LOW, derived.NORMAL_HIGH)

    def test_every_stage_agrees_on_every_scanline(self) -> None:
        checked = 0
        for region in REGIONS:
            for words, first, count in _pairs(region):
                part = _part()
                derived.ask(part, SETUP, words, 4)
                state = _state(part)
                for row in self._rows(part, first, count):
                    self._compare(state, row["line"], row)
                    checked += 1

        self.assertGreater(checked, 1000)

    def _rows(self, part: Any, first: int, count: int) -> list[dict[str, int]]:
        part.write(STREAM)
        part.write(first & 0xFF)
        part.write(first >> 8)
        core = part.core
        host = part.console
        rows: list[dict[str, int]] = []
        row: dict[str, int] | None = None
        got: list[int] = []
        wanted = {at: name for name, at in STAGES.items()}
        for _ in range(3_000_000):
            here = core.registers.pc
            if here == LOOP:
                if row is not None:
                    rows.append(row)
                row = {"line": derived.signed(core.stores.scratch[COUNTER])}
            name = wanted.get(here)
            if name is not None and row is not None:
                row[name] = derived.signed(core.registers.word("a"))
                if name == "reciprocal":
                    row["exponent"] = derived.signed(core.registers.word("b"))
                if name == "first":
                    row["first exponent"] = derived.signed(core.registers.word("b"))
            core.step()
            if core.registers.sr.rqm:
                got.append(host.read(0))
                if len(got) >= count * 2:
                    break
        return [one for one in rows if len(one) == len(STAGES) + 3]

    def _compare(self, state: dict[int, int], line: int, row: dict[str, int]) -> None:
        raw = raster.product(state[raster.STEP], line) + state[raster.HORIZON]
        self.assertEqual(raw, row["raw"], f"the distance for line {line}")

        held, count = raster.normalise(raw)
        self.assertEqual(held, row["held"], f"the normalise for line {line}")

        mantissa, exponent = raster.reciprocal(held, count, self.table)
        self.assertEqual(mantissa, row["reciprocal"], f"the reciprocal for line {line}")
        self.assertEqual(exponent, row["exponent"], f"the reciprocal exponent for line {line}")

        first = raster.product(state[raster.FIRST_MANTISSA], mantissa)
        self.assertEqual(first, row["first"], f"the first mantissa for line {line}")
        first_exponent = exponent + state[raster.FIRST_EXPONENT]
        self.assertEqual(first_exponent, row["first exponent"], f"the first exponent for {line}")

        one, two = raster.scanline(state, line, self.table)
        self.assertEqual(one, row["scale one"], f"the first scale for line {line}")
        self.assertEqual(two, row["scale two"], f"the second scale for line {line}")


class Answer(unittest.TestCase):
    @override
    def setUp(self) -> None:
        why = _missing()
        if why:
            self.skipTest(why)
        self.table = derived.reciprocal(_part(), derived.NORMAL_LOW, derived.NORMAL_HIGH)

    def test_every_word_agrees_with_the_part(self) -> None:
        words = 0
        for region in REGIONS:
            for arguments, first, count in _pairs(region):
                part = _part()
                derived.ask(part, SETUP, arguments, 4)
                state = _state(part)
                theirs = _stream(part, first, count)
                ours = raster.answer(state, derived.signed(first), count // 4, self.table)

                self.assertEqual(raster.shortfall(ours, theirs)[1], 0, f"{region} {arguments}")
                words += len(theirs)

        self.assertGreater(words, 10_000)

    def test_it_also_agrees_with_what_the_recording_holds(self) -> None:
        for region in REGIONS:
            run = exchanges.taken((BUILD / f"trace-{region}.bin").read_bytes())
            recorded = {}
            last: tuple[int, ...] | None = None
            for one in run:
                if one.command == SETUP and len(one.words) == parameter.WORDS:
                    last = one.words
                elif one.command == STREAM and last is not None and one.answer:
                    recorded[(last, one.words[0])] = one.answer
            for arguments, first, count in _pairs(region):
                part = _part()
                derived.ask(part, SETUP, arguments, 4)
                ours = raster.answer(_state(part), derived.signed(first), count // 4, self.table)

                self.assertEqual(ours, recorded[(arguments, first)], f"{region} {arguments}")


if __name__ == "__main__":
    unittest.main()
