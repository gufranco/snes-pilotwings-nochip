"""The commands whose whole input domain fits, driven out of the part rather than recorded.

A table built from a recording covers the recording. Measured here, that is 100%
of the questions it was built from, 91.4% of a different recording of the same
attract demo, and 7.2% of the second half of a recording whose first half it
learned. The first two figures flatter it: the three recordings are the same
sequence, so agreement between them measures repetition. The third is what a
player would see.

For most commands nothing can be done about that, because the domain is too
large to hold. For a few it can, and this module is those few.

Two conditions have to hold together.

The domain has to be small. Some arguments here are quantised rather than
continuous: one of `$13`'s words has a span of 32,769 and takes seven values.
Sizing by span says the command is impossible and sizing by the values it can
actually take says 1,512 rows. Both sizings are taken, and the second decides.

And the part has to answer the same thing when driven on the key alone. That is
not automatic: the key indexes an answer, it does not necessarily hold the state
that produced it, and OPEN-QUESTIONS entry 2j measures which commands reproduce.
`$13` and `$18` reproduce every time, so a row absent from the recording can be
filled in by asking the part. `$10` reproduces 83 times in 100, so it cannot,
and it is not here: it is the reciprocal, and the whole reciprocal is already a
table taken from the part, so the answer for `$10` is a routine reading that.

What this buys is the difference between a fast path and a complete one. For a
command in here no key can miss, so the fallback behind it stops being a thing
that might run and becomes a thing that cannot.
"""

from collections.abc import Iterable, Mapping, Sequence
from itertools import product
from pathlib import Path
from typing import Any

import exchanges
import hardware
import microcode

STEPS = 3000

REGIONS = ("usa", "jp", "eur")

CARRIER = {0x13: 0x11}
"""Which earlier command's arguments join the key, for the ones in here."""

CARRIER_WORDS = {0x13: 4}
"""How many words the carrier contributes, so a key can be split back apart."""

COMPLETE = (0x13, 0x18)
"""The commands this module completes, and why only these two.

`$13` is 1,512 combinations against 244 recorded, and 27.7% of every call the
game makes, which makes it the largest single gain available. `$18` is 48
against 4 and is worth doing because it is free.

`$10` is deliberately absent although its domain is only 4,996 combinations.
Driving it in isolation reproduces the replay 83 times in 100, so 17% of any row
filled in that way would be wrong, and a wrong row is worse than a missing one:
a missing row falls back and a wrong row does not. Its route is the reciprocal
table, which covers all 65,536 inputs exactly.

`$04`, `$00` and `$08` are absent for the opposite reason. Their arithmetic is
known exactly, so a routine covers their whole domain at no cost in space, and a
table would be a larger way of being no more right.
"""


def ask(part: Any, command: int, words: Sequence[int], answers: int) -> tuple[int, ...]:
    """One question put to the part."""
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


def domains(runs: Iterable[Sequence[Any]]) -> dict[int, tuple[tuple[int, ...], ...]]:
    """Every value each argument word of a completable command was seen to take.

    The domain is read off the recordings and it is a floor, not a ceiling: a
    value no run showed is not in it. What makes that tolerable here and not
    elsewhere is that these words are quantised, so the set is small, closed and
    the same across all three regions rather than a sample of a continuum.
    """
    seen: dict[int, dict[int, set[int]]] = {}
    for run in runs:
        last: dict[int, tuple[int, ...]] = {}
        for one in run:
            if one.answer and one.command in COMPLETE:
                held = last.get(CARRIER[one.command], ()) if one.command in CARRIER else ()
                for at, word in enumerate((*one.words, *held)):
                    seen.setdefault(one.command, {}).setdefault(at, set()).add(word)
            last[one.command] = one.words
    return {
        command: tuple(tuple(sorted(words[at])) for at in sorted(words))
        for command, words in seen.items()
    }


def wanted(values: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    """Every key the domain allows, which for these commands is every combination."""
    return tuple(product(*values))


def filled(
    command: int,
    keys: Sequence[tuple[int, ...]],
    answers: int,
    have: Mapping[tuple[int, ...], tuple[int, ...]],
    mask: str = microcode.MASK,
    say: Any = None,
) -> dict[tuple[int, ...], tuple[int, ...]]:
    """The recorded rows, plus every other key in the domain asked of the part.

    A recorded answer is never replaced. The recording is the part answering in
    the state the game put it in and this is the part answering from a reset, so
    where both exist the recording is the better evidence.
    """
    own = len(keys[0]) - CARRIER_WORDS.get(command, 0)
    out = dict(have)
    part = hardware.load("snesdsp").Chip(mask)
    carrier = CARRIER.get(command)
    for at, key in enumerate(keys):
        if key in out:
            continue
        if carrier is not None:
            ask(part, carrier, key[own:], 0)
        out[key] = ask(part, command, key[:own], answers)
        if say is not None and at % 200 == 0:
            say(f"  ${command:02x} {at:,} of {len(keys):,}")
    return out


def gather(where: Path = Path("build")) -> tuple[Sequence[Any], ...]:
    """The recordings, read from disk."""
    return tuple(exchanges.taken((where / f"trace-{one}.bin").read_bytes()) for one in REGIONS)


def report(found: Mapping[int, tuple[int, int]]) -> list[str]:
    lines = ["  cmd    recorded    complete   filled in"]
    for command in sorted(found):
        recorded, whole = found[command]
        lines.append(f"  ${command:02x}  {recorded:10,}  {whole:10,}  {whole - recorded:10,}")
    return lines
