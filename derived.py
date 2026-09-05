"""The tables the replacement cannot compute, taken from the part instead.

Four of the part's tables are formulas, and `asm/dsp1-tables.asm` rebuilds those
from the formulas at build time. These are not. They are what the part answers
after interpolating between those four and refining, with clamps whose rounding
this project has not measured, so a routine that recomputes them is a routine
that is nearly right. A table of what the part actually says is exact by
construction and no input can miss it.

Three are needed, and each is a function of one sixteen bit word, which is what
makes them tables rather than impossibilities:

    reciprocal   16,384 entries   the mantissa `$00d3` answers, per normalised input
    sine         65,536 entries   what `$04` multiplies a magnitude by
    cosine       65,536 entries   the same, for the other half

None is checked in. They are built here, on the machine of whoever has the
part, into the ignored build directory, and the assembler folds them in. That is
the same arrangement the four formula tables have, with the part standing in for
the formula.

Why the reciprocal is 16,384 entries rather than 65,536. It is only ever asked
for a value that has just come out of the part's own normalise loop at `$003a`,
which doubles until signed overflow and therefore always leaves a magnitude in
`[$4000, $7fff]`. That bound comes from reading the loop, not from watching which
values a recording happened to ask for, so the table is complete by construction
and no input can miss it. The sign is not stored either: `$00d3` takes the
magnitude, refines it, and negates the answer on the way out, so one half of the
range answers both.

Why it is driven as a routine rather than as a command. `$10` answers a mantissa
too, but through a wrapper that scales and shifts it, so its answers are not the
mantissa `$0a` reads. Setting the program counter to `$00d3` and stepping asks
the part the question `$0a` asks. The routine makes no calls of its own, so one
level of return stack is enough to catch it coming back.

One thing to know about driving the part for this. A fresh part per question
answers 68 a second and one part asked repeatedly answers 5,145, which is the
difference between four hours and thirteen seconds. Reuse is only safe because
these were measured to carry no state: the same arguments answer the same way on
a part just reset and on one driven through thousands of other questions first,
and `ask` is checked against the fresh-part path.
"""

import struct
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import hardware

WHOLE = 0x10000
"""How many values a sixteen bit word takes, and so how long the trig tables are."""

NORMAL_LOW = 0x4000
NORMAL_HIGH = 0x8000
"""The range the part's own normalise loop leaves a magnitude in.

Read off `$003a`: it doubles while the top two bits agree and steps back on the
doubling that would have overflowed, so what comes out has bit 14 set and bit 15
clear. Every value the reciprocal is ever asked for has been through it.
"""

RECIPROCAL_ENTRY = 0x0D3
"""Where the reciprocal routine begins inside the part's program."""

SENTINEL = 0x7FF
"""An address to put on the return stack, so a return is visible from outside.

The routine does not reach it and nothing is executed there. It is a value to
recognise: the part comes back to whatever was pushed, so pushing something the
program never contains turns a return into an observable event.
"""

RECIPROCAL_STEPS = 200
"""How long to let one reciprocal run before calling it stuck.

The longest path through `$00d3` is about thirty instructions. Two hundred is far
past that and short enough that a routine which never returns is reported rather
than waited on.
"""

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


class Runaway(Exception):
    """A routine driven directly that did not come back.

    Raised rather than left to the caller as a wrong number, because a table
    built from a runaway holds whatever the accumulator happened to have.
    """


def refined(part: Any, value: int) -> int:
    """One reciprocal mantissa, by running the part's own routine on that value.

    The exponent is left out on purpose. It comes back as one less the exponent
    handed in, measured across the whole range, so the cartridge computes it from
    the normalise count in two instructions and needs no table for it.
    """
    core = part.core
    core.registers.sp = 1
    core.registers.stack[0] = SENTINEL
    core.registers.a = value & 0xFFFF
    core.registers.b = 0
    core.registers.pc = RECIPROCAL_ENTRY
    for _ in range(RECIPROCAL_STEPS):
        core.step()
        if core.registers.pc == SENTINEL:
            return signed(core.registers.word("a"))
    raise Runaway(
        f"the reciprocal at ${RECIPROCAL_ENTRY:03x} did not return for ${value:04x}"
        f" within {RECIPROCAL_STEPS} instructions"
    )


def reciprocal(
    part: Any,
    low: int = NORMAL_LOW,
    high: int = NORMAL_HIGH,
    watch: Callable[[int], None] | None = None,
) -> tuple[int, ...]:
    """The mantissa `$00d3` answers across the range the normalise loop produces.

    Positive magnitudes only. A negative input takes the same path with its sign
    stripped and the answer negated, which is two instructions in the cartridge
    rather than another 32 KiB.
    """
    found = []
    for value in range(low, high):
        found.append(refined(part, value))
        if watch is not None and (value - low) % 4096 == 0:
            watch(value - low)
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


def pieces(where: Path | str) -> tuple[int, ...]:
    """A table `write` put on disk, read back whole out of its numbered pieces.

    So the re-index below can run without driving the part again. The reciprocal
    is the part's own behaviour and takes a while to collect; turning it inside
    out is arithmetic, and arithmetic should not need the hardware.
    """
    stem = Path(where)
    raw = b""
    piece = 0
    while True:
        one = stem.with_name(f"{stem.stem}-{piece}{stem.suffix}")
        if not one.exists():
            break
        raw += one.read_bytes()
        piece += 1
    if not raw:
        raise FileNotFoundError(f"no pieces of {stem} on disk")
    return tuple(struct.unpack(f"<{len(raw) // 2}H", raw))


FOLDED = 0x8000
"""How many values the folded form of a word takes, and so how long a re-index is.

A value and its bitwise complement fold to the same number, so a table keyed on
the folded form is half the length of one keyed on the word. The two halves need
different mantissas, which is why there are two tables rather than one.
"""

HORIZON_MANTISSA = 0x7FFF
HORIZON_EXPONENT = 0x002F
"""What `$00d3` answers for a distance of exactly nought, out of `$0f2` and `$0f3`.

A scanline exactly on the horizon. The exponent is large enough that the shift
after it saturates, which is the part's way of answering that there is no ground
on that line.
"""

BIAS = 6
"""What `$00d3` takes off the doubling count to make its exponent."""


def doublings(folded: int) -> int:
    """How many times `$003a` doubles a value whose folded form is that.

    The loop doubles while the top two bits agree, so what it leaves has bit 14
    set and bit 15 clear. The count is therefore the number of leading bits that
    match the sign, less one, and folding a negative value with a bitwise
    complement leaves that count unchanged. Nought folded is every bit a sign
    bit, which is fifteen doublings.
    """
    if folded == 0:
        return 15
    count = 0
    while folded < NORMAL_LOW:
        folded <<= 1
        count += 1
    return count


def inverted(mantissas: Sequence[int], negative: bool) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The part's reciprocal keyed on the value asked about rather than on the shift.

    `mantissas` is what `reciprocal` collected: one entry per normalised magnitude,
    which means the cartridge had to normalise first and then look up. The
    normalising was a loop, and the loop was the dearest thing in the ground.

    Keying on the value instead removes it. The magnitude a value normalises to
    is a function of the value, so the mantissa is too, and so is the exponent.

    The two signs need separate tables. A negative value folds to one less than
    its own magnitude, so it normalises to a magnitude one step up the table, and
    the answer comes back negated. The exponent is the same for both, because the
    doubling count is a property of the folded form alone.
    """
    if len(mantissas) != NORMAL_HIGH - NORMAL_LOW:
        raise ValueError(
            f"a reciprocal table is {NORMAL_HIGH - NORMAL_LOW:,} entries, not {len(mantissas):,}"
        )
    mantissa: list[int] = []
    exponent: list[int] = []
    for folded in range(FOLDED):
        count = doublings(folded)
        if folded == 0 and not negative:
            mantissa.append(HORIZON_MANTISSA)
            exponent.append(HORIZON_EXPONENT)
            continue
        exponent.append(count - BIAS & 0xFFFF)
        magnitude = (folded + 1 if negative else folded) << count & 0xFFFF
        if magnitude >= NORMAL_HIGH or magnitude == 0:
            magnitude = NORMAL_HIGH - 1
        answer = mantissas[magnitude - NORMAL_LOW] & 0xFFFF
        mantissa.append(-answer & 0xFFFF if negative else answer)
    return tuple(mantissa), tuple(exponent)


def reindex(into: Path, values: Sequence[int], say: Any) -> None:
    """The three tables the ground reads, turned inside out from the reciprocal.

    No part is driven here. The reciprocal above is the part's own behaviour;
    these are that same behaviour asked a different question, so they are
    arithmetic over what it already said.
    """
    for negative, stem in ((False, "recip-up"), (True, "recip-down")):
        mantissa, exponent = inverted(values, negative=negative)
        say(f"  wrote {write(into / f'{stem}.bin', mantissa):,} bytes")
        if not negative:
            continue
        say(f"  wrote {write(into / 'recip-exponent.bin', exponent):,} bytes")


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    rest = [one for one in argv if one != "--reindex"]
    again = len(rest) != len(list(argv))
    if not rest:
        say("usage: derived.py <mask> [<directory>] [--reindex], one of dsp1 or dsp1b")
        return 2
    into = Path(rest[1]) if len(rest) > 1 else Path("build")
    into.mkdir(exist_ok=True)

    if again:
        say(f"turning the reciprocal already in {into} inside out")
        reindex(into, pieces(into / "reciprocal.bin"), say)
        return 0

    part = hardware.load("snesdsp").Chip(rest[0])

    say(f"driving the {rest[0]} for {NORMAL_HIGH - NORMAL_LOW:,} reciprocals")
    values = reciprocal(part, NORMAL_LOW, NORMAL_HIGH, watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {write(into / 'reciprocal.bin', values):,} bytes")
    reindex(into, values, say)

    say(f"driving it for {WHOLE:,} angles, six magnitudes each")
    sine, cosine = trig(part, watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {write(into / 'sine.bin', sine):,} bytes")
    say(f"  wrote {write(into / 'cosine.bin', cosine):,} bytes")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
