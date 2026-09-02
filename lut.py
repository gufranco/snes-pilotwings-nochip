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

import exchanges
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


ON_RANGE = "indexed on the range the game used, so no input inside it can miss"

ON_SET = "indexed on the set that was recorded, so an unseen argument misses"


class Choice:
    """How one command is answered, and what that costs."""

    __slots__ = ("bytes_", "command", "complete", "rows", "why")

    def __init__(self, command: int, why: str, rows: int, bytes_: int, complete: bool) -> None:
        self.command = command
        self.why = why
        self.rows = rows
        self.bytes_ = bytes_
        self.complete = complete

    @override
    def __repr__(self) -> str:
        return f"<Choice ${self.command:02x} {self.rows:,} rows, {self.bytes_:,} bytes>"


def plan(census: exchanges.Census, command: int, out: int = 1, budget: int = CEILING) -> Choice:
    """Whether that command gets a table over its range or over its set.

    The range is preferred wherever it fits, and it is preferred even when it is
    the larger of the two. A table over the range answers every argument between
    the ends the game was seen to use, so the fallback behind it is unreachable
    for anything inside them; a table over the set answers only the arguments a
    recording happened to catch, and the fallback behind that one is reached the
    first time a player produces a set the recording did not.

    Paying for the wider table is the whole point of having the budget.
    """
    spans = exchanges.spans(census, command)
    rows = 1 << sum(one.bits for one in spans) if spans else 1
    dense = rows * out * BYTES_PER_ROW
    held = census.distinct(command)
    sparse = held * out * BYTES_PER_ROW
    if dense <= budget:
        return Choice(command, ON_RANGE, rows, dense, True)
    return Choice(command, ON_SET, held, sparse, False)


def planned(
    census: exchanges.Census,
    widths: dict[int, int] | None = None,
    budget: int = CEILING - GAME_BYTES,
) -> tuple[Choice, ...]:
    """A choice for every command, sharing one budget between them all.

    The budget belongs to the cartridge rather than to each command, and treating
    it as each command's is how a plan comes back larger than the cartridge it
    was made for. Command `$0a` answers twelve words at a time, so a table over
    its range is 12,582,912 bytes on its own, which is affordable only if nothing
    else needs anything.

    Every command starts on a table over the set that was recorded, which is the
    cheap and incomplete option, and the budget is then spent widening as many as
    it reaches to a table over the range. Cheapest widening first, because that
    buys completeness for the most commands, and completeness is the whole reason
    to spend: a command answered over its range cannot reach the fallback for any
    argument between the ends the game was seen to use.
    """
    widths = widths or {}
    over_set = {
        one: Choice(
            one,
            ON_SET,
            census.distinct(one),
            census.distinct(one) * widths.get(one, 1) * BYTES_PER_ROW,
            False,
        )
        for one in census.commands
    }
    over_range = {
        one: plan(census, one, widths.get(one, 1), budget=budget) for one in census.commands
    }
    chosen = dict(over_set)
    left = budget - sum(one.bytes_ for one in over_set.values())
    for command in sorted(census.commands, key=lambda one: over_range[one].bytes_):
        wider = over_range[command].bytes_ - over_set[command].bytes_
        if over_range[command].complete and wider <= left:
            chosen[command] = over_range[command]
            left -= wider
    return tuple(chosen[one] for one in census.commands)


def planned_bytes(choices: tuple[Choice, ...]) -> int:
    return sum(one.bytes_ for one in choices)


KEY_WORD_BYTES = 2


class Table:
    """One command's rows, as a cartridge would hold them.

    Keys sorted, so a replacement finds a row by halving the range rather than
    walking it: seventeen compares reaches any row of the largest table here,
    against seventy five thousand for a walk.

    A row carries its key as well as its answer, which is what a table keyed on a
    set costs over one keyed on a range: the range table finds a row by
    arithmetic on the argument and stores no key at all. Several of these keys
    are wider than the answer they lead to.
    """

    __slots__ = ("answer_words", "answers", "command", "key_words", "keys")

    def __init__(
        self,
        command: int,
        keys: tuple[tuple[int, ...], ...],
        answers: tuple[tuple[int, ...], ...],
        key_words: int,
        answer_words: int,
    ) -> None:
        self.command = command
        self.keys = keys
        self.answers = answers
        self.key_words = key_words
        self.answer_words = answer_words

    @property
    def rows(self) -> int:
        return len(self.keys)

    @property
    def size(self) -> int:
        return self.rows * (self.key_words + self.answer_words) * KEY_WORD_BYTES

    @override
    def __repr__(self) -> str:
        return f"<Table ${self.command:02x} {self.rows:,} rows, {self.size:,} bytes>"


def gather(
    runs: tuple[tuple[Any, ...], ...], command: int, carrier: int | None
) -> dict[tuple[int, ...], tuple[int, ...]]:
    """Every row a set of runs holds for that command, under that key.

    The answers come from the recordings rather than from driving the part,
    because a recording already holds what the part answered. Driving it again
    would reproduce those answers at best and diverge from them at worst.
    """
    found: dict[tuple[int, ...], tuple[int, ...]] = {}
    for run in runs:
        last: dict[int, tuple[int, ...]] = {}
        for one in run:
            if one.command == command and one.answer:
                held = last.get(carrier, ()) if carrier is not None else ()
                found[(*one.words, *held)] = one.answer
            last[one.command] = one.words
    return found


def table(runs: tuple[tuple[Any, ...], ...], command: int, carrier: int | None) -> Table:
    """That command's rows, padded to one width and sorted for a binary search."""
    held = gather(runs, command, carrier)
    if not held:
        return Table(command, (), (), 0, 0)
    key_words = max(len(one) for one in held)
    answer_words = max(len(one) for one in held.values())
    rows = sorted(
        (
            tuple(key) + (0,) * (key_words - len(key)),
            tuple(answer) + (0,) * (answer_words - len(answer)),
        )
        for key, answer in held.items()
    )
    return Table(
        command,
        tuple(one for one, _ in rows),
        tuple(one for _, one in rows),
        key_words,
        answer_words,
    )


def encode(built: Table) -> bytes:
    """That table as the cartridge holds it: a count, then keys, then answers.

    Every field is wider than it looks like it needs to be, and each was widened
    after the narrow one overflowed on real data. The count is thirty two bits
    because `$06` keyed on its arguments and the last `$02` holds 75,278 rows,
    and sixteen bits wrap to 9,742. The two widths are sixteen bits each because
    `$0a` answers 704 words in one exchange, and eight bits wrap to 192.
    """
    out = bytearray()
    out += struct.pack(">IHH", built.rows, built.key_words, built.answer_words)
    for one in built.keys:
        out += struct.pack(f">{len(one)}H", *one)
    for one in built.answers:
        out += struct.pack(f">{len(one)}H", *one)
    return bytes(out)


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    count = int(argv[0]) if argv else FULL_DOMAIN
    for line in report(count):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
