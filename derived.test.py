import struct
import unittest
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import override

import derived
import hardware

ROOT = Path(__file__).resolve().parent


class _Part:
    """A stand in for the chip that answers a rule, so no microcode is needed."""

    def __init__(self, rule: Callable[[int, tuple[int, ...]], Sequence[int]]) -> None:
        self.rule = rule
        self.taken: list[int] = []
        self.pending: list[int] = []

    def write(self, value: int) -> None:
        self.taken.append(value)

    def step(self, count: int) -> None:
        if self.pending or len(self.taken) < 2:
            return
        command, *rest = self.taken
        words = tuple(rest[k] | rest[k + 1] << 8 for k in range(0, len(rest) - 1, 2))
        answer = self.rule(command, words)
        self.taken = []
        self.pending = [byte for word in answer for byte in (word & 0xFF, word >> 8)]

    @property
    def asking(self) -> bool:
        return bool(self.pending)

    def read(self) -> int:
        return self.pending.pop(0)


def part_answering(rule: Callable[[int, tuple[int, ...]], Sequence[int]]) -> _Part:
    return _Part(rule)


class AskTest(unittest.TestCase):
    def test_it_hands_back_the_words_the_part_gave(self) -> None:
        part = part_answering(lambda command, words: (0x1234, 0x5678))

        self.assertEqual(derived.ask(part, 0x10, (1, 0), 2), (0x1234, 0x5678))

    def test_it_passes_the_command_and_the_arguments_on(self) -> None:
        seen: list[tuple[int, tuple[int, ...]]] = []

        def rule(command: int, words: tuple[int, ...]) -> tuple[int, ...]:
            seen.append((command, words))
            return (0,)

        derived.ask(part_answering(rule), 0x04, (0x1111, 0x2222), 1)

        self.assertEqual(seen[0], (0x04, (0x1111, 0x2222)))


class QuietPartTest(unittest.TestCase):
    def test_a_part_that_says_nothing_answers_nothing(self) -> None:
        class Silent:
            def write(self, value: int) -> None:
                pass

            def step(self, count: int) -> None:
                pass

            @property
            def asking(self) -> bool:
                return False

        self.assertEqual(derived.ask(Silent(), 0x10, (1, 0), 2), ())

    def test_a_part_that_answers_late_is_still_heard(self) -> None:
        class Slow:
            def __init__(self) -> None:
                self.left = 3
                self.pending: list[int] = []

            def write(self, value: int) -> None:
                pass

            def step(self, count: int) -> None:
                self.left -= 1
                if self.left == 0:
                    self.pending = [0x34, 0x12]

            @property
            def asking(self) -> bool:
                return bool(self.pending)

            def read(self) -> int:
                return self.pending.pop(0)

        self.assertEqual(derived.ask(Slow(), 0x10, (1, 0), 1), (0x1234,))


class _Registers:
    """The registers the reciprocal is driven through, at the widths it uses."""

    def __init__(self) -> None:
        self.a = 0
        self.b = 0
        self.pc = 0
        self.sp = 0
        self.stack = [0, 0, 0, 0]

    def word(self, name: str) -> int:
        return int(getattr(self, name)) & 0xFFFF


class _Routine:
    """A part that runs one made up routine, so no microcode is needed.

    It answers after `takes` instructions by putting `rule(a)` in the
    accumulator and returning to whatever was pushed, which is what the real
    routine does and all this driver depends on.
    """

    def __init__(self, rule: Callable[[int], int], takes: int = 3) -> None:
        self.rule = rule
        self.takes = takes
        self.core = self
        self.registers = _Registers()
        self.left = 0
        self.asked: list[int] = []

    def step(self) -> None:
        self.left += 1
        if self.left < self.takes:
            return
        self.left = 0
        self.asked.append(self.registers.a)
        self.registers.a = self.rule(self.registers.a) & 0xFFFF
        self.registers.sp -= 1
        self.registers.pc = self.registers.stack[self.registers.sp]


class RefinedTest(unittest.TestCase):
    def test_it_hands_back_what_the_routine_left_in_the_accumulator(self) -> None:
        self.assertEqual(
            derived.refined(_Routine(lambda one: one ^ 0x5555), 0x4000), 0x4000 ^ 0x5555
        )

    def test_a_negative_answer_reads_as_negative(self) -> None:
        self.assertEqual(derived.refined(_Routine(lambda one: 0xFFFF), 0x4000), -1)

    def test_it_asks_the_routine_the_value_it_was_given(self) -> None:
        part = _Routine(lambda one: 0)

        derived.refined(part, 0x5678)

        self.assertEqual(part.asked, [0x5678])

    def test_it_enters_at_the_routine_the_stream_calls(self) -> None:
        seen: list[int] = []
        part = _Routine(lambda one: 0)
        part.asked = seen

        derived.refined(part, 0x4000)

        self.assertEqual(part.registers.pc, derived.SENTINEL)

    def test_a_routine_that_never_returns_is_reported(self) -> None:
        with self.assertRaises(derived.Runaway):
            derived.refined(_Routine(lambda one: 0, takes=derived.RECIPROCAL_STEPS + 10), 0x4000)


class ReciprocalTest(unittest.TestCase):
    def test_it_holds_one_entry_for_every_value_the_normalise_loop_can_leave(self) -> None:
        found = derived.reciprocal(_Routine(lambda one: one), low=0x4000, high=0x4040)

        self.assertEqual(len(found), 64)

    def test_each_entry_is_the_mantissa_the_part_gave(self) -> None:
        found = derived.reciprocal(_Routine(lambda one: one ^ 0x5555), low=0x4000, high=0x4004)

        self.assertEqual(found[2], 0x4002 ^ 0x5555)

    def test_the_range_it_covers_is_the_one_the_loop_produces(self) -> None:
        self.assertEqual(derived.NORMAL_HIGH - derived.NORMAL_LOW, 0x4000)


class TrigTest(unittest.TestCase):
    def test_it_holds_a_sine_and_a_cosine_for_every_angle(self) -> None:
        part = part_answering(lambda command, words: (words[0] & 0x7FFF, 0x0100))

        sine, cosine = derived.trig(part, count=32)

        self.assertEqual((len(sine), len(cosine)), (32, 32))

    def test_it_recovers_the_value_that_explains_every_magnitude(self) -> None:
        def rule(command: int, words: tuple[int, ...]) -> tuple[int, ...]:
            hidden = 1000
            return (((words[1] * hidden) >> 15) & 0xFFFF, 0)

        sine, _ = derived.trig(part_answering(rule), count=2)

        self.assertEqual(sine[0], 1000)

    def test_an_angle_it_cannot_explain_keeps_what_was_returned(self) -> None:
        def rule(command: int, words: tuple[int, ...]) -> tuple[int, ...]:
            return ((words[1] * 7) & 0xFFFF, 0)

        sine, _ = derived.trig(part_answering(rule), count=1)

        self.assertIsInstance(sine[0], int)


class WatchTest(unittest.TestCase):
    def test_the_reciprocal_reports_where_it_has_reached(self) -> None:
        seen: list[int] = []

        derived.reciprocal(_Routine(lambda one: 1), low=0x4000, high=0x4002, watch=seen.append)

        self.assertEqual(seen, [0])

    def test_the_trig_reports_where_it_has_reached(self) -> None:
        seen: list[int] = []
        part = part_answering(lambda command, words: (1, 2))

        derived.trig(part, count=2, watch=seen.append)

        self.assertEqual(seen, [0])


class SignedTest(unittest.TestCase):
    def test_a_word_below_the_halfway_point_stays_itself(self) -> None:
        self.assertEqual(derived.signed(0x1234), 0x1234)

    def test_a_word_above_it_reads_as_negative(self) -> None:
        self.assertEqual(derived.signed(0xFFFE), -2)


class MainRunTest(unittest.TestCase):
    def test_it_drives_the_part_and_writes_every_table(self) -> None:
        said: list[str] = []
        into = ROOT / "build" / "derived-main"
        real = hardware.load
        hardware.load = lambda package: _Loaded()
        held = derived.WHOLE
        low, high = derived.NORMAL_LOW, derived.NORMAL_HIGH
        derived.WHOLE = 2
        derived.NORMAL_HIGH = derived.NORMAL_LOW + 2
        try:
            code = derived.main(("dsp1", str(into)), say=said.append)
        finally:
            hardware.load = real
            derived.WHOLE = held
            derived.NORMAL_LOW, derived.NORMAL_HIGH = low, high

        self.assertEqual(code, 0)
        self.assertTrue((into / "reciprocal-0.bin").exists())
        self.assertTrue((into / "sine-0.bin").exists())
        self.assertTrue((into / "cosine-0.bin").exists())


class _Both:
    """A part that answers a command and also runs the routine driven directly.

    `main` needs both: the trig tables come from asking `$04`, and the reciprocal
    comes from stepping `$00d3`. One object stands in for both so the whole entry
    point can be exercised without any microcode.
    """

    def __init__(self) -> None:
        self.asking_part = _Part(lambda command, words: (1, 2))
        self.routine = _Routine(lambda one: 1)
        self.core = self.routine.core
        self.registers = self.routine.registers

    def write(self, value: int) -> None:
        self.asking_part.write(value)

    def step(self, count: int) -> None:
        self.asking_part.step(count)

    @property
    def asking(self) -> bool:
        return self.asking_part.asking

    def read(self) -> int:
        return self.asking_part.read()


class _Loaded:
    def Chip(self, mask: str) -> "_Both":
        return _Both()


class WriteTest(unittest.TestCase):
    def test_it_reports_the_whole_length(self) -> None:
        where = ROOT / "build" / "derived-test.bin"
        where.parent.mkdir(exist_ok=True)

        self.assertEqual(derived.write(where, (1, 2, 3)), 6)

    def test_a_short_table_lands_in_one_piece(self) -> None:
        where = ROOT / "build" / "derived-test.bin"
        where.parent.mkdir(exist_ok=True)

        derived.write(where, (1, 2, 3))

        self.assertEqual(len((ROOT / "build" / "derived-test-0.bin").read_bytes()), 6)

    def test_a_table_past_a_bank_is_cut_at_the_border(self) -> None:
        where = ROOT / "build" / "derived-test.bin"
        where.parent.mkdir(exist_ok=True)

        derived.write(where, tuple(range(derived.BANK_BYTES // 2 + 4)))

        first = (ROOT / "build" / "derived-test-0.bin").read_bytes()
        self.assertEqual(len(first), derived.BANK_BYTES)

    def test_what_did_not_fit_goes_in_the_next_piece(self) -> None:
        where = ROOT / "build" / "derived-test.bin"
        where.parent.mkdir(exist_ok=True)

        derived.write(where, tuple(range(derived.BANK_BYTES // 2 + 4)))

        self.assertEqual(len((ROOT / "build" / "derived-test-1.bin").read_bytes()), 8)

    def test_it_writes_low_byte_first(self) -> None:
        where = ROOT / "build" / "derived-test.bin"
        where.parent.mkdir(exist_ok=True)

        derived.write(where, (0x1234,))

        raw = (ROOT / "build" / "derived-test-0.bin").read_bytes()
        self.assertEqual(struct.unpack("<H", raw)[0], 0x1234)

    def test_a_negative_value_is_written_as_the_part_holds_it(self) -> None:
        where = ROOT / "build" / "derived-test.bin"
        where.parent.mkdir(exist_ok=True)

        derived.write(where, (-2,))

        raw = (ROOT / "build" / "derived-test-0.bin").read_bytes()
        self.assertEqual(struct.unpack("<H", raw)[0], 0xFFFE)


class MainTest(unittest.TestCase):
    def test_with_no_mask_it_says_so(self) -> None:
        said: list[str] = []

        self.assertEqual(derived.main((), say=said.append), 2)

    def test_with_no_mask_it_prints_a_usage_line(self) -> None:
        said: list[str] = []

        derived.main((), say=said.append)

        self.assertTrue(said)


def _as_the_cartridge_did(value: int, mantissas: Sequence[int]) -> tuple[int, int]:
    """The mantissa and exponent the doubling loop and the table read used to give.

    A transcription of the two routines the tables replace, instruction for
    instruction, so the tables are checked against the behaviour rather than
    against the reasoning that produced them.
    """
    count = 0
    accumulator = value
    if accumulator != 0:
        while True:
            doubled = accumulator << 1 & 0xFFFF
            if accumulator >> 15 == doubled >> 15:
                count += 1
                accumulator = doubled
            else:
                break
    exponent = count - 6 & 0xFFFF

    if accumulator == 0:
        return 0x7FFF, 0x002F

    negative = accumulator >= 0x8000
    if negative:
        magnitude = 0x7FFF if accumulator == 0x8000 else -accumulator & 0xFFFF
    else:
        magnitude = accumulator
    mantissa = mantissas[magnitude - 0x4000] & 0xFFFF
    if negative:
        mantissa = -mantissa & 0xFFFF
    return mantissa, exponent


def _folded(value: int) -> int:
    return value if value < 0x8000 else value ^ 0xFFFF


class DoublingsTest(unittest.TestCase):
    def test_a_value_already_normalised_is_not_doubled(self) -> None:
        self.assertEqual(derived.doublings(0x4000), 0)

    def test_one_short_of_normalised_is_doubled_once(self) -> None:
        self.assertEqual(derived.doublings(0x3FFF), 1)

    def test_the_smallest_value_is_doubled_fourteen_times(self) -> None:
        self.assertEqual(derived.doublings(0x0001), 14)

    def test_the_largest_folded_value_is_not_doubled(self) -> None:
        self.assertEqual(derived.doublings(0x7FFF), 0)

    def test_nought_folded_is_doubled_fifteen_times(self) -> None:
        self.assertEqual(derived.doublings(0x0000), 15)

    def test_it_agrees_with_the_loop_on_every_positive_value(self) -> None:
        wrong = [v for v in range(1, 0x8000) if derived.doublings(v) != _count_of(v)]

        self.assertEqual(wrong, [])

    def test_it_agrees_with_the_loop_on_every_negative_value(self) -> None:
        wrong = [v for v in range(0x8000, 0x10000) if derived.doublings(_folded(v)) != _count_of(v)]

        self.assertEqual(wrong, [])


def _count_of(value: int) -> int:
    count = 0
    accumulator = value
    while True:
        doubled = accumulator << 1 & 0xFFFF
        if accumulator >> 15 == doubled >> 15:
            count += 1
            accumulator = doubled
        else:
            return count


class InvertedTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.mantissas = tuple(0x4000 + (k * 7 & 0x3FFF) for k in range(0x4000))

    def test_each_table_holds_one_entry_per_folded_value(self) -> None:
        mantissa, exponent = derived.inverted(self.mantissas, negative=False)

        self.assertEqual((len(mantissa), len(exponent)), (0x8000, 0x8000))

    def test_the_positive_table_answers_what_the_cartridge_did(self) -> None:
        mantissa, exponent = derived.inverted(self.mantissas, negative=False)

        wrong = [
            v
            for v in range(1, 0x8000)
            if (mantissa[v], exponent[v]) != _as_the_cartridge_did(v, self.mantissas)
        ]
        self.assertEqual(wrong, [])

    def test_the_negative_table_answers_what_the_cartridge_did(self) -> None:
        mantissa, exponent = derived.inverted(self.mantissas, negative=True)

        wrong = [
            v
            for v in range(0x8000, 0x10000)
            if (mantissa[_folded(v)], exponent[_folded(v)])
            != _as_the_cartridge_did(v, self.mantissas)
        ]
        self.assertEqual(wrong, [])

    def test_the_two_tables_agree_on_every_exponent(self) -> None:
        _, one = derived.inverted(self.mantissas, negative=False)
        _, two = derived.inverted(self.mantissas, negative=True)

        self.assertEqual(one[1:], two[1:])

    def test_the_value_on_the_horizon_answers_the_part_s_own_constants(self) -> None:
        mantissa, exponent = derived.inverted(self.mantissas, negative=False)

        self.assertEqual((mantissa[0], exponent[0]), (0x7FFF, 0x002F))

    def test_a_mantissa_short_of_a_whole_table_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            derived.inverted((0x4000,) * 16, negative=False)


class ReindexTest(unittest.TestCase):
    def test_it_reads_the_pieces_it_wrote_earlier(self) -> None:
        into = ROOT / "build" / "derived-test"
        into.mkdir(parents=True, exist_ok=True)
        values = tuple(0x4000 + k % 0x3FFF for k in range(0x4000))
        derived.write(into / "reciprocal.bin", values)

        self.assertEqual(derived.pieces(into / "reciprocal.bin"), values)

    def test_a_missing_piece_is_reported_rather_than_read_as_short(self) -> None:
        into = ROOT / "build" / "derived-test"
        into.mkdir(parents=True, exist_ok=True)

        with self.assertRaises(FileNotFoundError):
            derived.pieces(into / "nothing.bin")


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "derived.py").exists())


if __name__ == "__main__":
    unittest.main()
