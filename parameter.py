"""The state `$02` leaves behind, which is everything `$0a` reads.

`$0a` is the command the cartridge asks for most, and it computes nothing from
its own argument alone: it reads a horizon, two mantissas, two exponents and a
matrix, and `$02` writes all seven. Watching the part settles who writes what.
`$01` and `$11`, the two commands that answer nothing at all, write four words
each and touch none of them. So `$02` is the whole of `$0a`'s input.

Storing that state against `$02`'s seven argument words would be one flat table
of 6,980 rows, which is 123 KiB and does not fit beside everything else this
cartridge already carries. It does not have to be flat, because the state
separates cleanly and each piece answers to fewer arguments than the whole:

| what it sets                  | answers to      |
|-------------------------------|-----------------|
| horizon, and the second scale | argument 6      |
| the matrix                    | argument 5      |
| the first scale               | arguments 2 and 6 |

That separation is measured rather than assumed. Holding the other arguments at
three widely different settings and moving only the ones a group names leaves
that group's output identical every time, which is what makes the split safe to
build on rather than a hopeful reading of the arithmetic.

Split that way the same coverage costs 32 KiB, because the matrix needs two
words rather than four: the part writes the cosine twice and the sine twice, once
negated, so the four entries carry two numbers.

Two arguments never vary at all. Across all three recordings argument 3 is
always 32 and argument 4 is always 256, so neither is a key. `fixed` re-derives
that from whatever run it is handed rather than trusting the sentence above,
because an argument that was constant in three recordings is constant in three
recordings and not by nature.

What the tables cover. Built from the European recording they answer every `$02`
call in the American and Japanese ones as well, all three at 100%. That is
agreement between three recordings of the same attract sequence rather than
proof about a player, and the honest reading is that this covers the demo.
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

GROUPS: Mapping[str, tuple[int, ...]] = {
    "horizon": (6,),
    "matrix": (5,),
    "scale": (2, 6),
}
"""Which arguments each piece of the state answers to.

Each entry was checked by holding every other argument at three widely different
settings and confirming the group's output did not move.
"""

BYTES_PER_WORD = 2


class Disagreement(Exception):
    """One key seen twice carrying two different answers.

    That would mean the group answers to an argument this split does not key on,
    so the split is wrong and the table built from it would be wrong with it.
    Raised rather than resolved, because either answer might be the right one and
    picking silently would hide the fault.
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
    return sum(len(state) * BYTES_PER_WORD for state in rows.values())
