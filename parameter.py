"""The state `$02` leaves behind, which is everything `$0a` reads.

`$0a` is the command the cartridge asks for most, and it computes nothing from
its own argument alone: it reads a per-line step, a horizon, two mantissas, two
exponents and a four word matrix, and `$02` writes all ten. Watching the part
settles who writes what. `$01` and `$11`, the two commands that answer nothing
at all, write four words each and touch none of them. So `$02` is the whole of
`$0a`'s input.

Storing that state against `$02`'s seven argument words would be one flat table
of 6,980 rows, which is 136 KiB and does not fit beside everything else this
cartridge already carries. It does not have to be flat, because the state
separates cleanly and each piece answers to fewer arguments than the whole:

| what it sets                        | answers to        |
|-------------------------------------|-------------------|
| the step, the horizon, the second exponent | argument 6 |
| the two mantissas and the first exponent   | arguments 2 and 6 |
| the matrix                          | argument 5        |

That separation is measured rather than assumed. Sweeping one argument at a time
against the part, from three widely different starting sets, leaves each group's
output untouched by every argument the group does not name, and driving all 6,980
distinct sets the recordings hold produces no key that carries two answers.

Split that way the same coverage costs 58.3 KiB, because the matrix needs two
words rather than four: the part writes the cosine twice and the sine twice, once
negated, so the four entries carry two numbers. That identity is checked on every
set rather than assumed, because a table built on it is wrong with it.

Two arguments never vary at all. Across all three recordings argument 3 is
always 32 and argument 4 is always 256, so neither is a key. `fixed` re-derives
that from whatever run it is handed rather than trusting the sentence above,
because an argument that was constant in three recordings is constant in three
recordings and not by nature. It matters here: sweeping argument 3 off 32 does
move the horizon and both mantissas, so the split holds only while those two sit
where every recording has them.

What the tables cover. Built from all three recordings they answer every `$02`
call in each of them. That is agreement between three recordings of the same
attract sequence rather than proof about a player, and the honest reading is that
this covers the demo. A key no recording showed takes the nearest row instead,
which is a near miss rather than a failure, because these arguments are an
aircraft's attitude sampled every frame.
"""

from collections.abc import Iterable, Mapping, Sequence

WORDS = 7
"""How many argument words `$02` takes."""

FIXED = {3: 32, 4: 256}
"""The arguments that never varied, and what they held.

Measured across all three recordings. `fixed` recomputes this from a run rather
than reading it from here, so a run that disagrees is visible instead of quietly
overridden.
"""

CELLS: Mapping[str, int] = {
    "step": 0x49,
    "horizon": 0xC8,
    "mantissa1": 0x4C,
    "exponent1": 0xCC,
    "mantissa2": 0x4B,
    "exponent2": 0xCB,
    "matrix0": 0x7F,
    "matrix1": 0x7E,
    "matrix2": 0x6F,
    "matrix3": 0x6E,
}
"""Where in the part's own memory each piece of the state lives.

Read off the part rather than guessed: these are the addresses `$0a`'s loop
loads from, at `$364` through `$38b`, and driving `$02` and reading them back is
what says which argument moves which.
"""

GROUPS: Mapping[str, tuple[tuple[int, ...], tuple[str, ...]]] = {
    "line": ((6,), ("step", "horizon", "exponent2")),
    "scale": ((2, 6), ("mantissa1", "exponent1", "mantissa2")),
    "matrix": ((5,), ("matrix0", "matrix1")),
}
"""Which arguments each piece of the state answers to, and which cells it carries.

The matrix carries two cells rather than four because the other two are those two
over again: `matrix3` repeats `matrix0` and `matrix2` is `matrix1` negated, on
every one of the 6,980 sets. `mirrored` checks that rather than trusting it.
"""

BYTES_PER_WORD = 2


class Disagreement(Exception):
    """One key seen twice carrying two different answers.

    That would mean the group answers to an argument this split does not key on,
    so the split is wrong and the table built from it would be wrong with it.
    Raised rather than resolved, because either answer might be the right one and
    picking silently would hide the fault.
    """


class NotMirrored(Exception):
    """A matrix whose four words are not two words twice.

    The table stores two and the cartridge rebuilds four, so a set that breaks
    the identity would be stored correctly and read back wrong. Raised rather
    than stored, because the wrong half of a matrix puts the ground somewhere
    plausible.
    """


def keyed(words: Sequence[int], slots: Sequence[int]) -> tuple[int, ...]:
    """The part of an argument set that a group keys on."""
    return tuple(words[slot] for slot in slots)


def fixed(runs: Iterable[Sequence[int]]) -> dict[int, int]:
    """The arguments that never varied across a run, and what they held."""
    seen: dict[int, set[int]] = {}
    for words in runs:
        for slot, word in enumerate(words):
            seen.setdefault(slot, set()).add(word)
    return {slot: next(iter(vals)) for slot, vals in seen.items() if len(vals) == 1}


def mirrored(state: Mapping[str, int]) -> None:
    """Refuse a matrix that is not the cosine twice and the sine twice."""
    if state["matrix3"] != state["matrix0"] or state["matrix2"] != -state["matrix1"]:
        raise NotMirrored(
            f"matrix {tuple(state[f'matrix{k}'] for k in range(4))} is not two words twice,"
            " so storing two of them would lose the other two"
        )


def gathered(
    seen: Iterable[tuple[Sequence[int], Sequence[int]]], slots: Sequence[int]
) -> dict[tuple[int, ...], tuple[int, ...]]:
    """One row per distinct key, and a refusal when a key carries two answers."""
    rows: dict[tuple[int, ...], tuple[int, ...]] = {}
    for words, state in seen:
        key = keyed(words, slots)
        found = tuple(state)
        if key in rows and rows[key] != found:
            raise Disagreement(
                f"key {key} gives {rows[key]} and {found}, so slots {tuple(slots)} are not enough"
            )
        rows[key] = found
    return rows


def sized(rows: Mapping[tuple[int, ...], tuple[int, ...]]) -> int:
    """What a table costs in the cartridge, in bytes."""
    return sum((len(key) + len(state)) * BYTES_PER_WORD for key, state in rows.items())
