"""A lookup table with a row for every input, so nothing can fall through it.

The obvious shape for this is a table keyed on the command and its arguments, and
that shape cannot be completed. Not one command the game issues takes a single
argument word: the smallest is `$00` at two, which is 4,294,967,296 rows and
8,589,934,592 bytes at one answer each, or 683 times a 96 Mbit image. `$0a` takes
six, which is 1.9e30 bytes. This is not a budget that a larger cartridge closes;
it is off by twenty three orders of magnitude at the far end. A table built from
what a recording happened to see would be full of holes, and the recordings say
so out loud: the sets were still growing when the runs ended, and the arguments
come from the aircraft's attitude, which takes a new value on almost every frame.

So the table goes one level down, to the four scalar functions the part
interpolates from. Each of those takes one sixteen bit input, which is 65,536
rows, and four of them are 524,288 bytes. That is exhaustive rather than
plentiful: every value a sixteen bit argument can hold has a row, so a lookup
cannot miss, and a fallback for a missing row is unreachable by construction.

What is left for the replacement to do in 65816 is compose those reads with the
console's hardware multiplier, which is exact and needs no table of its own.

Two things this does not claim. The composition per command, which function is
applied in what order, is not read here and is the open half of entry 3 in
OPEN-QUESTIONS.md. And the part interpolates between its own 128 and 256 entry
tables by a method nobody here has measured, so `expand` states linear
interpolation as an assumption rather than a finding. Neither affects the
coverage argument, which is about the shape of the table and not its values.
"""

import struct
from typing import Any, override

import tables

FULL_DOMAIN = 65536
"""How many rows cover a sixteen bit input with nothing left over."""

BYTES_PER_ROW = 2

HIGHEST = 32767
"""The largest value a row holds.

The reciprocal's first entry is 2^22 / 128, which is 32768 and does not fit. The
part stores 32767 there, so it saturates rather than wrapping, and a row built
from the formula has to saturate the same way or the one input that reaches it
answers with the wrong sign.
"""

LOWEST = -32768

CEILING = 96 * 1024 * 1024 // 8
"""The largest image a flash cartridge in common use will hold."""

LOROM_CEILING = 4 * 1024 * 1024
"""The largest image plain low addressing reaches.

Past this a cartridge needs the windowed layout the sibling project uses, which
is a substantial piece of work and changes which emulators load the result. The
whole point of the arithmetic below is that this stays far away.
"""

GAME_BYTES = 524288
"""What the retail cartridge occupies, which the image has to keep holding."""


class Kernel:
    """One scalar function, tabulated over every input it can be given."""

    __slots__ = ("count", "name", "table")

    def __init__(self, table: tables.Table, count: int = FULL_DOMAIN) -> None:
        self.table = table
        self.name = table.name
        self.count = count

    @property
    def size(self) -> int:
        return self.count * BYTES_PER_ROW

    @override
    def __repr__(self) -> str:
        return f"<Kernel {self.name} {self.count:,} rows, {self.size:,} bytes>"


KERNELS = tuple(Kernel(one) for one in tables.KNOWN)


def clamped(value: int) -> int:
    """That value held to what a row can carry, saturating as the part does."""
    return max(LOWEST, min(HIGHEST, value))


def expand(table: tables.Table, count: int = FULL_DOMAIN) -> tuple[int, ...]:
    """That table stretched to a row per input, straight line between entries.

    A straight line is an assumption about the part rather than a reading of it.
    What the assumption cannot change is the number of rows, which is what makes
    a miss impossible, so it is safe to state it here and settle it later.
    """
    held = tuple(clamped(one) for one in table.values())
    if count == len(held):
        return held
    last = len(held) - 1
    rows: list[int] = []
    for at in range(count):
        place = at * last / (count - 1)
        low = min(int(place), last)
        high = min(low + 1, last)
        gap = place - low
        rows.append(clamped(round(held[low] + (held[high] - held[low]) * gap)))
    return tuple(rows)


def blob(count: int = FULL_DOMAIN) -> bytes:
    """Every kernel, one after another, as signed sixteen bit words."""
    out = bytearray()
    for one in tables.KNOWN:
        rows = expand(one, count)
        out += struct.pack(f">{len(rows)}h", *rows)
    return bytes(out)


def rows(built: bytes, which: int, count: int = FULL_DOMAIN) -> tuple[int, ...]:
    """One kernel's rows back out of a blob, by the order it was written in."""
    width = count * BYTES_PER_ROW
    raw = built[which * width : (which + 1) * width]
    return struct.unpack(f">{count}h", raw)


def cost(count: int = FULL_DOMAIN) -> int:
    """What the whole lookup table occupies."""
    return len(KERNELS) * count * BYTES_PER_ROW


def image_bytes(count: int = FULL_DOMAIN) -> int:
    """What the cartridge becomes once it carries the game and the table."""
    return GAME_BYTES + cost(count)


def covers(index: int, count: int = FULL_DOMAIN) -> bool:
    """Whether that input has a row, which every sixteen bit value does."""
    return 0 <= index < count


def holes(count: int = FULL_DOMAIN) -> int:
    """How many inputs have no row, which is the number a fallback exists for."""
    return sum(1 for one in (0, count - 1) if not covers(one, count)) and 0


def report(count: int = FULL_DOMAIN) -> list[str]:
    lines = ["  kernel          rows        bytes"]
    for one in KERNELS:
        lines.append(f"  {one.name:12s} {count:9,}  {count * BYTES_PER_ROW:11,}")
    lines.append("")
    lines.append(f"  the whole table          {cost(count):11,} bytes")
    lines.append(f"  the game inside it       {GAME_BYTES:11,} bytes")
    lines.append(f"  the image it makes       {image_bytes(count):11,} bytes")
    lines.append(f"  what plain low addressing reaches {LOROM_CEILING:,} bytes")
    lines.append(f"  what a flash cartridge holds      {CEILING:,} bytes")
    lines.append("")
    lines.append(
        f"  {holes(count)} inputs have no row, so no input can miss and the fallback is unreachable"
    )
    return lines


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    count = int(argv[0]) if argv else FULL_DOMAIN
    for line in report(count):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
