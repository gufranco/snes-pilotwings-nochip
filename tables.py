"""Which tables the part carries, read out of its own data ROM.

The list this project expected to tabulate was a sine, a cosine, a reciprocal, a
square root and an arctangent, and that list was what a mathematical coprocessor
of this kind normally carries rather than anything measured. It was wrong in
three places, and the part says so itself: the uPD77C25 keeps 1024 words of data
ROM alongside its program, and what a program interpolates from is written down
in there in plain sixteen bit words.

Four numeric tables are in it, each reproduced here from its formula and searched
for rather than recognised by eye:

    reciprocal    129 words   2^22 / (128 + k)
    sine          128 words   sin(pi k / 128) x 32767
    cosine        128 words   cos(pi k / 128) x 32767
    arccosine     256 words   acos(k / 256) x 32768 / pi

There is no square root and no arctangent, and nothing expected an arccosine.
The four together are 1,282 bytes, against the 131,072 a single table over a
whole sixteen bit input would take, so the question of how many such tables fit
in a grown image turns out to have been the wrong question: a replacement that
carries what the part carries needs about a kilobyte and interpolates the same
way the microcode does, which is also the only way to be right rather than close.

Both masks carry the same four, byte for byte. The DSP-1B holds them two words
lower than the DSP-1, and that shift is the whole of the difference in their data
ROMs, so whatever the DSP-1B corrected it corrected in the program. See
OPEN-QUESTIONS.md entry 1, which this narrows without closing.
"""

import math
import struct
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, override

PROGRAM_WORDS = 2048

PROGRAM_BYTES_PER_WORD = 3
"""The program is twenty four bits wide, so three bytes hold one instruction."""

TABLE_WORDS = 1024

TABLE_BYTES_PER_WORD = 2

IMAGE_BYTES = PROGRAM_WORDS * PROGRAM_BYTES_PER_WORD + TABLE_WORDS * TABLE_BYTES_PER_WORD

TOLERANCE = 1
"""How far a word may sit from the formula and still be that formula.

One unit. The part's tables were rounded from real arithmetic, and rounding is
the only difference this should forgive. Two would start accepting a table that
is nearly the same function, which is exactly the mistake this module exists to
stop being made by eye.
"""

WHOLE_INPUT_BYTES = 65536 * 2
"""What one table over a whole sixteen bit input would cost, for comparison."""

RECIPROCAL = "reciprocal"
SINE = "sine"
COSINE = "cosine"
ARCCOSINE = "arccosine"


class WrongShape(Exception):
    pass


class Table:
    """One table the part is expected to carry, and how to rebuild it."""

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


KNOWN = (
    Table(RECIPROCAL, 129, "2^22 / (128 + k)", lambda k: round(2**22 / (128 + k))),
    Table(
        SINE, 128, "sin(pi k / 128) x 32767", lambda k: round(math.sin(math.pi * k / 128) * 32767)
    ),
    Table(
        COSINE, 128, "cos(pi k / 128) x 32767", lambda k: round(math.cos(math.pi * k / 128) * 32767)
    ),
    Table(
        ARCCOSINE,
        256,
        "acos(k / 256) x 32768 / pi",
        lambda k: round(math.acos(k / 256) * 32768 / math.pi),
    ),
)


def words(image: bytes) -> tuple[int, ...]:
    """The data ROM of an image, as signed sixteen bit words.

    Signed because two of these tables go negative over their range, and a
    cosine read unsigned stops looking like a cosine halfway through.
    """
    if len(image) != IMAGE_BYTES:
        raise WrongShape(
            f"an image of this part is {IMAGE_BYTES} bytes, and this one is {len(image)}"
        )
    raw = image[PROGRAM_WORDS * PROGRAM_BYTES_PER_WORD :]
    return struct.unpack(f">{TABLE_WORDS}h", raw)


def find(carried_words: Sequence[int], table: Table) -> int | None:
    """Where that table sits in those words, or nothing if it does not."""
    wanted = table.values()
    for at in range(len(carried_words) - table.count + 1):
        if all(abs(carried_words[at + k] - wanted[k]) <= TOLERANCE for k in range(table.count)):
            return at
    return None


def carried(image: bytes) -> dict[str, int]:
    """Every table this image carries, and the word it starts at."""
    found = words(image)
    where = {one.name: find(found, one) for one in KNOWN}
    return {name: at for name, at in where.items() if at is not None}


def table_bytes() -> int:
    """What a replacement pays to carry the same four tables."""
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
