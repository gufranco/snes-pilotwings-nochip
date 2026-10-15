import math
import struct
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, override

PROGRAM_WORDS = 2048

PROGRAM_BYTES_PER_WORD = 3

TABLE_WORDS = 1024

TABLE_BYTES_PER_WORD = 2

IMAGE_BYTES = PROGRAM_WORDS * PROGRAM_BYTES_PER_WORD + TABLE_WORDS * TABLE_BYTES_PER_WORD

TOLERANCE = 0

WHOLE_INPUT_BYTES = 65536 * 2

RECIPROCAL = "reciprocal"
SINE = "sine"
COSINE = "cosine"
ARCCOSINE = "arccosine"


class WrongShape(Exception):
    pass


class Table:
    __slots__ = ("count", "formula", "name", "of")

    def __init__(self, name: str, count: int, formula: str, of: Callable[[int], int]) -> None:
        self.name = name
        self.count = count
        self.formula = formula
        self.of = of

    def values(self) -> tuple[int, ...]:
        return tuple(self.of(k) for k in range(self.count))

    @override
    def __repr__(self) -> str:
        return f"<Table {self.name} {self.count} words, {self.formula}>"


HIGHEST = 32767

LOWEST = -32768


def toward_zero(value: float) -> int:
    return min(HIGHEST, max(LOWEST, int(value)))


KNOWN = (
    Table(
        RECIPROCAL,
        128,
        "2^22 / (128 + k), rounded and clamped",
        lambda k: min(HIGHEST, round(2**22 / (128 + k))),
    ),
    Table(
        SINE,
        128,
        "sin(pi k / 128) x 32768, fraction cut off",
        lambda k: toward_zero(math.sin(math.pi * k / 128) * 32768),
    ),
    Table(
        COSINE,
        128,
        "cos(pi k / 128) x 32768, fraction cut off",
        lambda k: toward_zero(math.cos(math.pi * k / 128) * 32768),
    ),
    Table(
        ARCCOSINE,
        256,
        "acos(k / 256) x 32768 / pi",
        lambda k: round(math.acos(k / 256) * 32768 / math.pi),
    ),
)


def words(image: bytes) -> tuple[int, ...]:
    if len(image) != IMAGE_BYTES:
        raise WrongShape(
            f"an image of this part is {IMAGE_BYTES} bytes, and this one is {len(image)}"
        )
    raw = image[PROGRAM_WORDS * PROGRAM_BYTES_PER_WORD :]
    return struct.unpack(f">{TABLE_WORDS}h", raw)


def find(carried_words: Sequence[int], table: Table) -> int | None:
    wanted = table.values()
    for at in range(len(carried_words) - table.count + 1):
        if all(abs(carried_words[at + k] - wanted[k]) <= TOLERANCE for k in range(table.count)):
            return at
    return None


def carried(image: bytes) -> dict[str, int]:
    found = words(image)
    where = {one.name: find(found, one) for one in KNOWN}
    return {name: at for name, at in where.items() if at is not None}


def table_bytes() -> int:
    return sum(one.count for one in KNOWN) * TABLE_BYTES_PER_WORD


def report(image: bytes) -> list[str]:
    where = carried(image)
    lines = ["  table        words   at     formula"]
    for one in KNOWN:
        at = where.get(one.name)
        seat = f"{at:5d}" if at is not None else "  not carried"
        lines.append(f"  {one.name:12s} {one.count:5d}  {seat}  {one.formula}")
    lines.append("")
    lines.append(
        f"  {len(where)} of {len(KNOWN)} carried, {table_bytes():,} bytes to reproduce them all,"
        f" against {WHOLE_INPUT_BYTES:,} for one table over a whole input"
    )
    return lines


def read(path: Path | str) -> dict[str, int]:
    return carried(Path(path).read_bytes())


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if not argv:
        say("usage: tables.py <microcode image>")
        return 2
    for line in report(Path(argv[0]).read_bytes()):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
