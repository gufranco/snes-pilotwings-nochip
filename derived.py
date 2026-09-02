"""The tables the replacement cannot compute, taken from the part instead.

Four of the part's tables are formulas, and `asm/dsp1-tables.asm` rebuilds those
from the formulas at build time. These are not. They are what the part answers
after interpolating between those four and refining, with clamps whose rounding
this project has not measured, so a routine that recomputes them is a routine
that is nearly right. A table of what the part actually says is exact by
construction and no input can miss it.

Two are needed and both are functions of a single sixteen bit word, which is
what makes them tables rather than impossibilities:

    reciprocal   65,536 entries   the mantissa `$10` answers, per input
    sine         65,536 entries   what `$04` multiplies a magnitude by
    cosine       65,536 entries   the same, for the other half

Neither is checked in. They are built here, on the machine of whoever has the
part, into the ignored build directory, and the assembler folds them in. That is
the same arrangement the four formula tables have, with the part standing in for
the formula.

One thing to know about driving the part for this. A fresh part per question
answers 68 a second and one part asked repeatedly answers 5,145, which is the
difference between four hours and thirteen seconds. Reuse is only safe because
both commands were measured to carry no state: the same arguments answer the
same way on a part just reset and on one driven through thousands of other
questions first, and `ask` is checked against the fresh-part path.
"""

import struct
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import hardware

WHOLE = 0x10000
"""How many values a sixteen bit word takes, and so how long each table is."""

RECIPROCAL = 0x10
SINE_AND_COSINE = 0x04

STEPS = 3000
"""How long to let the part run before giving up on an answer."""

PROBES = (0x7FFF, 0x4000, 0x1234, 0x0100, 0x0007, 0x0001)
"""Magnitudes `trig` asks with, to recover what `$04` multiplies by.

`$04` carries more precision than it hands back: asked with `$7FFF` it answers
one short of the value it used. So it is asked with several magnitudes and the
one value that explains all of them is kept. The largest comes first because it
is the closest starting point for the search.
"""

NUDGES = (0, 1, -1, 2, -2)
"""How far from the returned value to look. Measured: never further than one."""


def signed(word: int) -> int:
    return word - 0x10000 if word >= 0x8000 else word


def ask(part: Any, command: int, words: Sequence[int], answers: int) -> tuple[int, ...]:
    """One question, on a part that may already have answered thousands."""
    part.write(command)
    for one in words:
        part.write(one & 0xFF)
        part.write(one >> 8)
    got: list[int] = []
    for _ in range(STEPS):
        part.step(16)
        if part.asking:
            got.append(part.read())
            if len(got) >= answers * 2:
                break
    return tuple(got[k] | got[k + 1] << 8 for k in range(0, len(got) - 1, 2))


def reciprocal(
    part: Any, count: int = WHOLE, watch: Callable[[int], None] | None = None
) -> tuple[int, ...]:
    """The mantissa `$10` answers for every input it can be given.

    The exponent is left out on purpose. It is a count of leading zeros less the
    second argument, which is a handful of instructions and needs no table.
    """
    found = []
    for value in range(count):
        found.append(ask(part, RECIPROCAL, (value, 0), 2)[0])
        if watch is not None and value % 4096 == 0:
            watch(value)
    return tuple(found)


def trig(
    part: Any, count: int = WHOLE, watch: Callable[[int], None] | None = None
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """What `$04` multiplies a magnitude by, for every angle, both halves.

    Recovered rather than read, because the command truncates what it returns.
    For each angle the value that reproduces every probe is kept; where no
    candidate does, what the part returned is kept and the caller is no worse
    off than reading it directly.
    """
    sine: list[int] = []
    cosine: list[int] = []
    for angle in range(count):
        wanted = {one: ask(part, SINE_AND_COSINE, (angle, one), 2) for one in PROBES}
        start = wanted[PROBES[0]]
        for half, into in ((0, sine), (1, cosine)):
            base = signed(start[half])
            for nudge in NUDGES:
                unit = base + nudge
                if all(
                    ((signed(one) * unit) >> 15) & 0xFFFF == wanted[one][half] for one in PROBES
                ):
                    into.append(unit)
                    break
            else:
                into.append(base)
        if watch is not None and angle % 4096 == 0:
            watch(angle)
    return tuple(sine), tuple(cosine)


BANK_BYTES = 0x8000
"""What one low-addressed bank holds, and so how a table has to be cut up.

A bank reaches $8000 to $FFFF, which is 32,768 bytes, or 16,384 entries. A whole
table is 131,072, so it lands as four pieces in four consecutive banks and the
lookup picks the piece from the top two bits of the index. The assembler refuses
to place a run of bytes across a bank border, which is how this was found.
"""


def write(where: Path | str, values: Sequence[int]) -> int:
    """That table as the cartridge holds it, low byte first, and how long it is.

    Written as one file per bank, numbered, because nothing can span a bank.
    """
    raw = b"".join(struct.pack("<H", one & 0xFFFF) for one in values)
    stem = Path(where)
    for piece, at in enumerate(range(0, len(raw), BANK_BYTES)):
        stem.with_name(f"{stem.stem}-{piece}{stem.suffix}").write_bytes(raw[at : at + BANK_BYTES])
    return len(raw)


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if not argv:
        say("usage: derived.py <mask> [<directory>], one of dsp1 or dsp1b")
        return 2
    into = Path(argv[1]) if len(argv) > 1 else Path("build")
    into.mkdir(exist_ok=True)
    part = hardware.load("snesdsp").Chip(argv[0])

    say(f"driving the {argv[0]} for {WHOLE:,} reciprocals")
    values = reciprocal(part, watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {write(into / 'reciprocal.bin', values):,} bytes")

    say(f"driving it for {WHOLE:,} angles, six magnitudes each")
    sine, cosine = trig(part, watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {write(into / 'sine.bin', sine):,} bytes")
    say(f"  wrote {write(into / 'cosine.bin', cosine):,} bytes")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
