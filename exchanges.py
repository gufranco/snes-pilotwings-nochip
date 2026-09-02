"""What the cartridge asked the part for, cut at the site that issued it.

`census.py` cuts an exchange where the byte stream looks like it ends: a run of
writes, closed by the first read. That reading works for a command written whole
and answered whole, and command `$0a` is not one. It answers with a stream the
cartridge reads 176 times over and the part swallows writes during that stream
rather than treating them as a new command, so a read in the middle of one
exchange looks exactly like the end of it. A tenth of the runs counted that way
held writes from code more than 32 bytes apart, which is two routines' traffic
joined into one.

The recording carries the program counter of every access, and that settles it
without any reading of the stream at all. A command byte is the one thing this
cartridge writes eight bits at a time, so a counter that only ever touches the
low half of the port issued commands and one that touches both halves wrote
argument words. An exchange therefore runs from one command site to the next, and
a read inside it is an answer rather than a boundary.

What that buys over the byte-stream rule is a count that does not depend on the
protocol being uniform. What it costs is a recording: this cannot be run against
an image, only against a run of one.
"""

import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, override

RECORD_BYTES = 12

DATA_PORT = 0x8000

STATUS_BOUNDARY = 0xC000
"""Where the data port stops and the status register starts.

`DSP0.boundary` in snes9x for a low cartridge of this size. Every address below
it is the data port and every address at or above it is the status register.
"""

ANSWER_BYTES = 8
"""What one stored answer occupies.

The widest answer any command gives is four words. Storing every row at that
width costs nothing worth saving and keeps a lookup one shift rather than a
multiply.
"""

MULTIPLY = 0x00
"""The command that is a signed fixed point product of its two arguments.

Never worth storing. The console has a hardware multiplier, so computing it is
cheaper than any lookup however few arguments it turns out to take.
"""

INLINE_LIMIT = 16
"""Above how many distinct argument sets a compare chain stops being the answer.

Below it a replacement can test the arguments against each known set in line and
branch to a stored answer. Above it the chain costs more than the arithmetic it
was meant to avoid.
"""

INLINE = "inline"
TABLE = "table"
COMPUTED = "computed"


class Exchange:
    """One command the cartridge issued, with what it sent and what came back."""

    __slots__ = ("answer", "command", "site", "words")

    def __init__(
        self, site: int, command: int, words: tuple[int, ...], answer: tuple[int, ...]
    ) -> None:
        self.site = site
        self.command = command
        self.words = words
        self.answer = answer

    @override
    def __repr__(self) -> str:
        return f"<Exchange ${self.command:02x} from ${self.site:06x} {len(self.words)} words>"


def _records(trace: bytes) -> Any:
    return struct.iter_unpack("<IIHBB", trace[: len(trace) // RECORD_BYTES * RECORD_BYTES])


def issuing(trace: bytes) -> dict[int, int]:
    """Every program counter that issued a command, and the byte it issued.

    A counter qualifies when every access it made was an eight bit write of one
    constant to the low half of the data port. A sixteen bit write touches the
    high half under the same counter, which is what rules an argument word out,
    and a counter that wrote two different bytes is not a site this can name.
    """
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
    """Every exchange the recording holds, in the order the cartridge made them."""
    sites = issuing(trace)
    found: list[Exchange] = []
    site: int | None = None
    command = 0
    written: list[int] = []
    answered: list[int] = []

    def close() -> None:
        if site is None:
            return
        found.append(Exchange(site, command, _worded(written), _worded(answered)))

    for _, pbpc, address, is_read, byte in _records(trace):
        if address >= STATUS_BOUNDARY:
            continue
        if pbpc in sites:
            close()
            site, command = pbpc, sites[pbpc]
            written, answered = [], []
            continue
        if site is None:
            continue
        (answered if is_read else written).append(byte)
    close()
    return tuple(found)


def _worded(bytes_: list[int]) -> tuple[int, ...]:
    return tuple(bytes_[at] | bytes_[at + 1] << 8 for at in range(0, len(bytes_) - 1, 2))


class Census:
    """Every command a recording issued, with how often and how variously."""

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
    """What one argument position of one command was ever given."""

    __slots__ = ("distinct", "highest", "lowest", "position")

    def __init__(self, position: int, lowest: int, highest: int, distinct: int) -> None:
        self.position = position
        self.lowest = lowest
        self.highest = highest
        self.distinct = distinct

    @property
    def width(self) -> int:
        """How many values lie between the two ends, both included."""
        return self.highest - self.lowest + 1

    @property
    def bits(self) -> int:
        """How many bits an index into that width needs."""
        return max(1, (self.width - 1).bit_length())

    @property
    def dense(self) -> bool:
        """Whether the values fill their range or are scattered through it.

        The distinction decides which table is possible. A position that fills
        its range can be indexed directly, and one that scatters through a wide
        range cannot: the rows between the values it used would be rows for
        inputs nobody has seen, which is the whole of the difference between a
        table sized against a range and one sized against a set.
        """
        return self.distinct * 2 >= self.width

    @override
    def __repr__(self) -> str:
        return f"<Span {self.position} {self.lowest}..{self.highest}, {self.distinct} used>"


def spans(taken_census: Census, command: int) -> tuple[Span, ...]:
    """The reach of each argument position of that command, as recorded.

    A floor like everything else a recording gives: the ends are the ends of what
    was seen, and a run that went further would widen them.
    """
    words = [one for one in taken_census.seen.get(command, ()) if one]
    if not words:
        return ()
    found = []
    for position in range(max(len(one) for one in words)):
        values = {one[position] for one in words if len(one) > position}
        found.append(Span(position, min(values), max(values), len(values)))
    return tuple(found)


def index_bits(taken_census: Census, command: int) -> int:
    """How many bits a table indexed on those spans would need."""
    return sum(one.bits for one in spans(taken_census, command))


class Reading:
    """What a command's answers depend on, measured from a run."""

    __slots__ = ("ambiguous", "carrier", "command", "rows")

    def __init__(self, command: int, carrier: int | None, rows: int, ambiguous: int) -> None:
        self.command = command
        self.carrier = carrier
        self.rows = rows
        self.ambiguous = ambiguous

    @property
    def pure(self) -> bool:
        """Whether the arguments alone decide the answer."""
        return self.carrier is None and self.ambiguous == 0

    @property
    def tabulatable(self) -> bool:
        """Whether some key seen here decides the answer for every row."""
        return self.ambiguous == 0

    @override
    def __repr__(self) -> str:
        held = (
            "arguments" if self.carrier is None else f"arguments and the last ${self.carrier:02x}"
        )
        return f"<Reading ${self.command:02x} on {held}, {self.rows} rows>"


def readings(runs: tuple[tuple[Exchange, ...], ...], command: int) -> Reading:
    """What decides that command's answer, taking the simplest key that works.

    A table answers a command only when the key it is indexed on decides the
    answer. The arguments alone do not always: this part keeps state, so a
    command that reads a matrix another command loaded gives different answers
    for the same arguments and a table keyed on them would return whichever row
    was written last.

    So the arguments are tried first and the answer is a pure function or it is
    not. When it is not, each command seen earlier in the run is tried as the
    thing carrying the state, and the one that leaves nothing ambiguous is the
    key. A command where nothing does is not tabulatable from this run and says
    so rather than being tabulated wrongly.
    """
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
    """How a replacement should answer that command, given how much it varies."""
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


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
