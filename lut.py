import struct
import sys
from typing import Any, override

import exchanges
import script
import tables

FULL_DOMAIN = 65536

BYTES_PER_ROW = 2

HIGHEST = 32767

LOWEST = -32768

CEILING = 96 * 1024 * 1024 // 8

LOROM_CEILING = 4 * 1024 * 1024

GAME_BYTES = 524288


class Kernel:
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
    return max(LOWEST, min(HIGHEST, value))


def expand(table: tables.Table, count: int = FULL_DOMAIN) -> tuple[int, ...]:
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
    out = bytearray()
    for one in tables.KNOWN:
        rows = expand(one, count)
        out += struct.pack(f">{len(rows)}h", *rows)
    return bytes(out)


def rows(built: bytes, which: int, count: int = FULL_DOMAIN) -> tuple[int, ...]:
    width = count * BYTES_PER_ROW
    raw = built[which * width : (which + 1) * width]
    return struct.unpack(f">{count}h", raw)


def cost(count: int = FULL_DOMAIN) -> int:
    return len(KERNELS) * count * BYTES_PER_ROW


def image_bytes(count: int = FULL_DOMAIN) -> int:
    return GAME_BYTES + cost(count)


def covers(index: int, count: int = FULL_DOMAIN) -> bool:
    return 0 <= index < count


def holes(count: int = FULL_DOMAIN) -> int:
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
    runs: tuple[tuple[Any, ...], ...],
    command: int,
    carrier: int | None,
    answers: dict[int, dict[tuple[int, ...], tuple[int, ...]]] | None = None,
) -> dict[tuple[int, ...], tuple[int, ...]]:
    driven = (answers or {}).get(command, {})
    found: dict[tuple[int, ...], tuple[int, ...]] = {}
    for run in runs:
        last: dict[int, tuple[int, ...]] = {}
        for one in run:
            if one.command == command and one.answer:
                held = last.get(carrier, ()) if carrier is not None else ()
                key = (*one.words, *held)
                found[key] = driven.get(key, one.answer)
            last[one.command] = one.words
    return found


def table(
    runs: tuple[tuple[Any, ...], ...],
    command: int,
    carrier: int | None,
    answers: dict[int, dict[tuple[int, ...], tuple[int, ...]]] | None = None,
) -> Table:
    held = gather(runs, command, carrier, answers)
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
    out = bytearray()
    out += struct.pack("<IHH", built.rows, built.key_words, built.answer_words)
    for one in built.keys:
        out += struct.pack(f"<{len(one)}H", *one)
    for one in built.answers:
        out += struct.pack(f"<{len(one)}H", *one)
    return bytes(out)


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    count = int(argv[0]) if argv else FULL_DOMAIN
    for line in report(count):
        say(line)
    return 0


script.entry(__name__, main, sys.argv[1:])
