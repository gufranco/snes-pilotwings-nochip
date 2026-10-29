import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, override

import script

RECORD_BYTES = 12

DATA_PORT = 0x8000

STATUS_BOUNDARY = 0xC000

ANSWER_BYTES = 8

MULTIPLY = 0x00

INLINE_LIMIT = 16

INLINE = "inline"
TABLE = "table"
COMPUTED = "computed"


class Exchange:
    __slots__ = ("answer", "command", "later", "site", "words")

    def __init__(
        self,
        site: int,
        command: int,
        words: tuple[int, ...],
        answer: tuple[int, ...],
        later: tuple[int, ...] = (),
    ) -> None:
        self.site = site
        self.command = command
        self.words = words
        self.answer = answer
        self.later = later

    @override
    def __repr__(self) -> str:
        return f"<Exchange ${self.command:02x} from ${self.site:06x} {len(self.words)} words>"


def _records(trace: bytes) -> Any:
    return struct.iter_unpack("<IIHBB", trace[: len(trace) // RECORD_BYTES * RECORD_BYTES])


def issuing(trace: bytes) -> dict[int, int]:
    wrote: dict[int, set[int]] = defaultdict(set)
    wide: set[int] = set()
    for _, pbpc, address, is_read, byte in _records(trace):
        if address >= STATUS_BOUNDARY:
            continue
        if is_read or address != DATA_PORT:
            wide.add(pbpc)
            continue
        wrote[pbpc].add(byte)
    return {
        pbpc: next(iter(bytes_))
        for pbpc, bytes_ in wrote.items()
        if pbpc not in wide and len(bytes_) == 1
    }


def taken(trace: bytes) -> tuple[Exchange, ...]:
    sites = issuing(trace)
    found: list[Exchange] = []
    site: int | None = None
    command = 0
    written: list[int] = []
    answered: list[int] = []
    later: list[int] = []

    def close() -> None:
        if site is None:
            return
        found.append(Exchange(site, command, _worded(written), _worded(answered), _worded(later)))

    for _, pbpc, address, is_read, byte in _records(trace):
        if address >= STATUS_BOUNDARY:
            continue
        if pbpc in sites:
            close()
            site, command = pbpc, sites[pbpc]
            written, answered, later = [], [], []
            continue
        if site is None:
            continue
        if is_read:
            answered.append(byte)
        elif answered:
            later.append(byte)
        else:
            written.append(byte)
    close()
    return tuple(found)


def _worded(bytes_: list[int]) -> tuple[int, ...]:
    return tuple(bytes_[at] | bytes_[at + 1] << 8 for at in range(0, len(bytes_) - 1, 2))


class Census:
    __slots__ = ("seen", "where")

    def __init__(
        self, seen: dict[int, Counter[tuple[int, ...]]], where: dict[int, set[int]]
    ) -> None:
        self.seen = seen
        self.where = where

    @property
    def commands(self) -> tuple[int, ...]:
        return tuple(sorted(self.seen))

    @property
    def total(self) -> int:
        return sum(sum(one.values()) for one in self.seen.values())

    def issued(self, command: int) -> int:
        return sum(self.seen[command].values()) if command in self.seen else 0

    def distinct(self, command: int) -> int:
        return len(self.seen[command]) if command in self.seen else 0

    def share(self, command: int) -> float:
        total = self.total
        return self.issued(command) / total if total else 0.0

    def sites(self, command: int) -> tuple[int, ...]:
        return tuple(sorted(self.where[command])) if command in self.where else ()

    def table_bytes(self) -> int:
        return sum(len(one) for one in self.seen.values()) * ANSWER_BYTES

    @override
    def __repr__(self) -> str:
        return f"<Census {len(self.seen)} commands, {self.total} exchanges>"


def census(trace: bytes) -> Census:
    seen: dict[int, Counter[tuple[int, ...]]] = defaultdict(Counter)
    where: dict[int, set[int]] = defaultdict(set)
    for one in taken(trace):
        seen[one.command][one.words] += 1
        where[one.command].add(one.site)
    return Census(dict(seen), dict(where))


class Span:
    __slots__ = ("distinct", "highest", "lowest", "position")

    def __init__(self, position: int, lowest: int, highest: int, distinct: int) -> None:
        self.position = position
        self.lowest = lowest
        self.highest = highest
        self.distinct = distinct

    @property
    def width(self) -> int:
        return self.highest - self.lowest + 1

    @property
    def bits(self) -> int:
        return max(1, (self.width - 1).bit_length())

    @property
    def dense(self) -> bool:
        return self.distinct * 2 >= self.width

    @override
    def __repr__(self) -> str:
        return f"<Span {self.position} {self.lowest}..{self.highest}, {self.distinct} used>"


def spans(taken_census: Census, command: int) -> tuple[Span, ...]:
    words = [one for one in taken_census.seen.get(command, ()) if one]
    if not words:
        return ()
    found = []
    for position in range(max(len(one) for one in words)):
        values = {one[position] for one in words if len(one) > position}
        found.append(Span(position, min(values), max(values), len(values)))
    return tuple(found)


def index_bits(taken_census: Census, command: int) -> int:
    return sum(one.bits for one in spans(taken_census, command))


class Reading:
    __slots__ = ("ambiguous", "carrier", "command", "rows")

    def __init__(self, command: int, carrier: int | None, rows: int, ambiguous: int) -> None:
        self.command = command
        self.carrier = carrier
        self.rows = rows
        self.ambiguous = ambiguous

    @property
    def pure(self) -> bool:
        return self.carrier is None and self.ambiguous == 0

    @property
    def tabulatable(self) -> bool:
        return self.ambiguous == 0

    @override
    def __repr__(self) -> str:
        held = (
            "arguments" if self.carrier is None else f"arguments and the last ${self.carrier:02x}"
        )
        return f"<Reading ${self.command:02x} on {held}, {self.rows} rows>"


def readings(runs: tuple[tuple[Exchange, ...], ...], command: int) -> Reading:
    plain: dict[tuple[int, ...], set[tuple[int, ...]]] = defaultdict(set)
    keyed: dict[int, dict[Any, set[tuple[int, ...]]]] = defaultdict(lambda: defaultdict(set))
    for run in runs:
        last: dict[int, tuple[int, ...]] = {}
        for one in run:
            if one.command == command and one.answer:
                plain[one.words].add(one.answer)
                for prior, words in last.items():
                    keyed[prior][(one.words, words)].add(one.answer)
            last[one.command] = one.words
    loose = sum(1 for one in plain.values() if len(one) > 1)
    if loose == 0:
        return Reading(command, None, len(plain), 0)
    best = Reading(command, None, len(plain), loose)
    for prior, table in keyed.items():
        bad = sum(1 for one in table.values() if len(one) > 1)
        if bad < best.ambiguous:
            best = Reading(command, prior, len(table), bad)
    return best


def read(path: Path | str) -> Census:
    return census(Path(path).read_bytes())


def tier_of(command: int, distinct: int) -> str:
    if command == MULTIPLY:
        return COMPUTED
    return INLINE if distinct <= INLINE_LIMIT else TABLE


def report(taken_census: Census) -> list[str]:
    lines = [
        f"{taken_census.total:,} exchanges over {len(taken_census.commands)} commands",
        "",
        "  cmd   exchanges   share   distinct   sites   how to answer it",
    ]
    for command in sorted(taken_census.commands, key=lambda one: -taken_census.issued(one)):
        distinct = taken_census.distinct(command)
        lines.append(
            f"  ${command:02X}  {taken_census.issued(command):10,}"
            f"  {taken_census.share(command):6.1%}  {distinct:9,}"
            f"  {len(taken_census.sites(command)):6}   {tier_of(command, distinct)}"
        )
    return lines


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if not argv:
        say("usage: exchanges.py <trace>")
        return 2
    for line in report(read(argv[0])):
        say(line)
    return 0


script.entry(__name__, main, sys.argv[1:])
