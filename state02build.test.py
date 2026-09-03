import struct
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar, override

import hardware
import parameter
import state02
import state02build

ROOT = Path(__file__).resolve().parent


class _Core:
    """The part's memory, as much of it as the state lives in."""

    def __init__(self, cells: dict[int, int]) -> None:
        self.stores = self
        self.scratch = dict(cells)


class _Part:
    """A stand in for the part, answering `$02` by a rule and holding state.

    It has to behave like the real one in the two ways this builder depends on:
    it takes a command and its arguments a byte at a time, and it leaves the ten
    cells behind in its own memory rather than in the answer.
    """

    def __init__(self, rule: Any) -> None:
        self.rule = rule
        self.taken: list[int] = []
        self.pending: list[int] = []
        self.core = _Core(dict.fromkeys(parameter.CELLS.values(), 0))

    def write(self, value: int) -> None:
        self.taken.append(value)

    def step(self, count: int) -> None:
        if self.pending or len(self.taken) < 2:
            return
        command, *rest = self.taken
        words = tuple(rest[k] | rest[k + 1] << 8 for k in range(0, len(rest) - 1, 2))
        self.taken = []
        for name, value in self.rule(command, words).items():
            self.core.scratch[parameter.CELLS[name]] = value & 0xFFFF
        self.pending = [0, 0, 0, 0, 0, 0, 0, 0]

    @property
    def asking(self) -> bool:
        return bool(self.pending)

    def read(self) -> int:
        return self.pending.pop(0)


def _state(**named: int) -> dict[str, int]:
    found = dict.fromkeys(parameter.CELLS, 0)
    found.update(named)
    found["matrix3"] = found["matrix0"]
    found["matrix2"] = -found["matrix1"]
    return found


def _flat(command: int, words: tuple[int, ...]) -> dict[str, int]:
    """A part whose every cell follows the arguments the split says it should."""
    return _state(
        step=words[6] & 0x7FFF,
        horizon=words[6] % 97,
        exponent2=words[6] % 5,
        mantissa1=(words[2] + words[6]) & 0x7FFF,
        exponent1=(words[2] % 7),
        mantissa2=(words[2] * 3 + words[6]) & 0x7FFF,
        matrix0=words[5] % 30011,
        matrix1=words[5] % 811,
    )


class _Exchange:
    __slots__ = ("answer", "command", "words")

    def __init__(self, command: int, words: tuple[int, ...]) -> None:
        self.command = command
        self.words = words
        self.answer = (0,)


def _sets(count: int) -> tuple[tuple[int, ...], ...]:
    return tuple((1, 2, 3 + k, 32, 256, 5 + k, 7 + k) for k in range(count))


class ArgumentSets(unittest.TestCase):
    def test_it_takes_only_the_setup_command(self) -> None:
        run = [_Exchange(0x02, (1, 2, 3, 32, 256, 5, 6)), _Exchange(0x0A, (9,))]

        self.assertEqual(state02build.argument_sets([run]), ((1, 2, 3, 32, 256, 5, 6),))

    def test_a_repeated_set_appears_once(self) -> None:
        one = _Exchange(0x02, (1, 2, 3, 32, 256, 5, 6))

        self.assertEqual(len(state02build.argument_sets([[one, one]])), 1)

    def test_sets_from_every_recording_are_united(self) -> None:
        first = [_Exchange(0x02, (1, 2, 3, 32, 256, 5, 6))]
        second = [_Exchange(0x02, (1, 2, 4, 32, 256, 5, 6))]

        self.assertEqual(len(state02build.argument_sets([first, second])), 2)

    def test_they_come_out_sorted_so_two_builds_agree(self) -> None:
        run = [
            _Exchange(0x02, (1, 2, 9, 32, 256, 5, 6)),
            _Exchange(0x02, (1, 2, 3, 32, 256, 5, 6)),
        ]

        found = state02build.argument_sets([run])

        self.assertEqual(found, tuple(sorted(found)))

    def test_a_set_of_the_wrong_width_is_left_out(self) -> None:
        run = [_Exchange(0x02, (1, 2, 3))]

        self.assertEqual(state02build.argument_sets([run]), ())


class Driven(unittest.TestCase):
    def test_it_reads_every_cell_out_of_the_part(self) -> None:
        part = _Part(_flat)

        seen = state02build.driven(part, _sets(1))

        self.assertEqual(set(next(iter(seen.values()))), set(parameter.CELLS))

    def test_one_row_per_argument_set(self) -> None:
        part = _Part(_flat)

        self.assertEqual(len(state02build.driven(part, _sets(4))), 4)

    def test_a_matrix_that_is_not_two_words_twice_is_refused(self) -> None:
        def broken(command: int, words: tuple[int, ...]) -> dict[str, int]:
            found = _flat(command, words)
            found["matrix3"] = found["matrix0"] + 1
            return found

        with self.assertRaises(parameter.NotMirrored):
            state02build.driven(_Part(broken), _sets(1))

    def test_it_reports_where_it_has_reached(self) -> None:
        reached: list[int] = []

        state02build.driven(_Part(_flat), _sets(1), watch=reached.append)

        self.assertEqual(reached, [0])


class Tables(unittest.TestCase):
    def test_it_builds_one_table_per_group(self) -> None:
        built = state02build.tables(state02build.driven(_Part(_flat), _sets(4)))

        self.assertEqual(set(built), set(parameter.GROUPS))

    def test_each_table_keys_on_the_arguments_its_group_names(self) -> None:
        built = state02build.tables(state02build.driven(_Part(_flat), _sets(4)))

        for name, (slots, _) in parameter.GROUPS.items():
            self.assertEqual(len(next(iter(built[name]))), len(slots))

    def test_each_row_carries_the_cells_its_group_names(self) -> None:
        built = state02build.tables(state02build.driven(_Part(_flat), _sets(4)))

        for name, (_, cells) in parameter.GROUPS.items():
            self.assertEqual(len(next(iter(built[name].values()))), len(cells))

    def test_a_cell_that_answers_to_an_argument_the_split_omits_is_reported(self) -> None:
        def leaking(command: int, words: tuple[int, ...]) -> dict[str, int]:
            found = _flat(command, words)
            found["horizon"] = words[0]
            return found

        seen = state02build.driven(
            _Part(leaking), ((1, 0, 0, 32, 256, 0, 7), (2, 0, 0, 32, 256, 0, 7))
        )

        with self.assertRaises(parameter.Disagreement):
            state02build.tables(seen)


class Checked(unittest.TestCase):
    def test_tables_that_fit_pass(self) -> None:
        state02build.checked(state02build.tables(state02build.driven(_Part(_flat), _sets(4))))

    def test_a_table_larger_than_one_bank_is_refused(self) -> None:
        wide: dict[tuple[int, ...], tuple[int, ...]] = {(k,): (0,) * 8 for k in range(4000)}

        with self.assertRaises(state02build.TooBig):
            state02build.checked({"line": wide})

    def test_a_ragged_table_is_refused(self) -> None:
        with self.assertRaises(state02.Ragged):
            state02build.checked({"line": {(1,): (2,), (2,): (3, 4)}})


class Placement(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.text = state02build.placement(0x70)

    def test_each_table_is_placed_in_its_own_bank(self) -> None:
        for step, name in enumerate(state02build.ORDER):
            self.assertIn(f"org ${0x70 + step:02X}8000\nstate02_{name}:", self.text)

    def test_each_table_is_included_from_the_build_directory(self) -> None:
        for name in state02build.ORDER:
            self.assertIn(f'incbin "state02-{name}.bin"', self.text)

    def test_it_says_it_is_generated(self) -> None:
        self.assertIn("Built by state02build.py", self.text)

    def test_it_carries_no_constants_the_code_needs_before_it(self) -> None:
        self.assertNotIn("!STATE02", self.text)


class Source(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.built = state02build.tables(state02build.driven(_Part(_flat), _sets(4)))
        self.text = state02build.source(self.built)

    def test_it_places_nothing_so_it_can_be_read_before_the_code(self) -> None:
        self.assertNotIn("org ", self.text)

    def test_the_row_count_is_published_for_the_lookup_to_read(self) -> None:
        self.assertIn(f"!STATE02_LINE_ROWS   = {state02.rows(self.built['line'])}", self.text)

    def test_the_stride_is_published_in_bytes(self) -> None:
        want = state02.stride(self.built["scale"]) * parameter.BYTES_PER_WORD
        self.assertIn(f"!STATE02_SCALE_STRIDE = {want}", self.text)

    def test_the_key_width_is_published(self) -> None:
        self.assertIn("!STATE02_SCALE_KEYS   = 2", self.text)

    def test_it_says_it_is_generated(self) -> None:
        self.assertIn("Built by state02build.py", self.text)


class Report(unittest.TestCase):
    def test_it_names_every_table(self) -> None:
        built = state02build.tables(state02build.driven(_Part(_flat), _sets(4)))

        lines = "\n".join(state02build.report(built))

        for name in state02build.ORDER:
            self.assertIn(name, lines)

    def test_it_gives_a_total(self) -> None:
        built = state02build.tables(state02build.driven(_Part(_flat), _sets(4)))

        self.assertIn("total", "\n".join(state02build.report(built)))


class StateOf(unittest.TestCase):
    def test_a_word_above_the_halfway_point_reads_as_negative(self) -> None:
        part = _Part(_flat)
        part.core.scratch[parameter.CELLS["matrix1"]] = 0xFFFF

        self.assertEqual(state02build.state_of(part)["matrix1"], -1)


class _Loaded:
    """What `hardware.load` answers with while these tests run."""

    asked: ClassVar[list[str]] = []

    def Chip(self, mask: str) -> _Part:
        _Loaded.asked.append(mask)
        return _Part(_flat)


class _NoPart:
    """Stand in for the model, so nothing here needs microcode on disk."""

    def __enter__(self) -> Path:
        _Loaded.asked = []
        self.held = hardware.load
        hardware.load = lambda package: _Loaded()
        self.where = tempfile.TemporaryDirectory()
        into = Path(self.where.name)
        for region in state02build.REGIONS:
            (into / f"trace-{region}.bin").write_bytes(_trace())
        return into

    def __exit__(self, *anything: object) -> None:
        hardware.load = self.held
        self.where.cleanup()


class Gather(unittest.TestCase):
    def test_it_drives_the_part_the_mask_names(self) -> None:
        with _NoPart() as into:
            state02build.gather("dsp1", into)

        self.assertEqual(_Loaded.asked, ["dsp1"])

    def test_it_builds_every_table(self) -> None:
        with _NoPart() as into:
            built = state02build.gather("dsp1", into)

        self.assertEqual(set(built), set(parameter.GROUPS))

    def test_it_says_how_many_argument_sets_it_found(self) -> None:
        seen: list[str] = []

        with _NoPart() as into:
            state02build.gather("dsp1", into, say=seen.append)

        self.assertTrue(any("argument sets" in one for one in seen))


def _trace() -> bytes:
    """A recording holding one `$02` exchange, in the twelve byte record shape."""
    records = [(0, 0x001234, 0x8000, 0, 0x02)]
    for word in (1, 2, 3, 32, 256, 5, 7):
        records.append((0, 0x005678, 0x8000, 0, word & 0xFF))
        records.append((0, 0x005678, 0x8000, 0, word >> 8))
    for _ in range(8):
        records.append((0, 0x009ABC, 0x8000, 1, 0))
    return b"".join(struct.pack("<IIHBB", *one) for one in records)


class Main(unittest.TestCase):
    def test_with_no_mask_it_says_so(self) -> None:
        said: list[str] = []

        self.assertEqual(state02build.main((), say=said.append), 2)
        self.assertTrue(any("usage" in one for one in said))

    def test_it_writes_every_table_and_both_halves_of_the_map(self) -> None:
        with _NoPart() as into:
            self.assertEqual(state02build.main(("dsp1", str(into)), say=lambda one: None), 0)

            for name in state02build.ORDER:
                self.assertTrue((into / f"state02-{name}.bin").exists())
            self.assertTrue((into / "state02-map.asm").exists())
            self.assertTrue((into / "state02-data.asm").exists())


class File(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "state02build.py").exists())


if __name__ == "__main__":
    unittest.main()
