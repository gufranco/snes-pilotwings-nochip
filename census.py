"""What the cartridge actually asks the part, counted from a recorded run.

The size of a command's input domain is arithmetic, and it answers a question
nobody needs: what a table would cost if the game could send anything. The game
cannot. What decides whether an answer can be stored is how many distinct
argument sets the cartridge actually sends, and only running it says that.

So this reads a port recording and counts. Every write to the data port that
follows a read starts an exchange, the first byte of it is the command, and the
rest are argument words, low byte first. Accesses to the status register are not
part of the exchange and are skipped.

What the counting is worth is bounded, and the bound is the important part. A
recording says what the game did on that run. It cannot say what the game can
do, and the two are not close here: the set of argument sets was still growing
by thousands per thousand frames when the longest recording ended. A command
whose arguments come from the aircraft's attitude takes a new value on almost
every frame, so its set does not close and no recording will ever show it
closing.

That splits the commands rather than settling them all one way. A handful ask
for the same one or two argument sets for an entire run, and for those a table
is small and complete. The rest are computed, and the recording is what says
which is which.
"""

import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, override

RECORD_BYTES = 12

DATA_PORT = 0x8000
"""The even address of the two the part answers at.

The lowest bit picks the port, so an odd address is the status register and says
nothing about what was asked.
"""

ANSWER_BYTES = 8
"""What one stored answer occupies.

The widest answer any command gives is four words. Storing every row at that
width costs nothing worth saving and keeps a lookup one shift rather than a
multiply.
"""

MULTIPLY = 0x00
"""The command that is a signed fixed point product of its two arguments.

It is never worth storing. The console has a hardware multiplier, so computing
it is cheaper than any lookup, and it is the command with the most distinct
arguments in every recording taken.
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
    __slots__ = ("command", "words")

    def __init__(self, command: int, words: tuple[int, ...]) -> None:
        self.command = command
        self.words = words

    @override
    def __repr__(self) -> str:
        return f"<Exchange ${self.command:02X} {len(self.words)} words>"


class Census:
    """Every command a recording used, with how often and how variously."""

    __slots__ = ("seen",)

    def __init__(self, seen: dict[int, Counter[tuple[int, ...]]]) -> None:
        self.seen = seen

    @property
    def commands(self) -> tuple[int, ...]:
        return tuple(sorted(self.seen))

    @property
    def total(self) -> int:
        return sum(sum(one.values()) for one in self.seen.values())

    def exchanges(self, command: int) -> int:
        return sum(self.seen[command].values()) if command in self.seen else 0

    def distinct(self, command: int) -> int:
        return len(self.seen[command]) if command in self.seen else 0

    def share(self, command: int) -> float:
        total = self.total
        return self.exchanges(command) / total if total else 0.0

    def table_bytes(self) -> int:
        return table_bytes(sum(len(one) for one in self.seen.values()))

    @override
    def __repr__(self) -> str:
        return f"<Census {len(self.seen)} commands, {self.total} exchanges>"


def exchanges(trace: bytes) -> list[Exchange]:
    """Every exchange in a recording, in the order the cartridge made them.

    An exchange is a run of writes, and it is complete at the first read that
    follows it, because that read is the cartridge collecting the answer. Ending
    it at the next write instead would drop the last exchange of every recording,
    which has no next write.
    """
    found: list[Exchange] = []
    run: list[int] = []
    for at in range(len(trace) // RECORD_BYTES):
        _, _, address, is_read, byte = struct.unpack_from("<IIHBB", trace, at * RECORD_BYTES)
        if address & 1:
            continue
        if is_read:
            if run:
                found.append(_exchange_of(run))
                run = []
            continue
        run.append(byte)
    return found


def _exchange_of(run: list[int]) -> Exchange:
    command, body = run[0], run[1:]
    words = tuple(body[at] | (body[at + 1] << 8) for at in range(0, len(body) - 1, 2))
    return Exchange(command, words)


def taken(trace: bytes) -> Census:
    """The census of one recording."""
    seen: dict[int, Counter[tuple[int, ...]]] = defaultdict(Counter)
    for one in exchanges(trace):
        seen[one.command][one.words] += 1
    return Census(dict(seen))


def read(path: Path | str) -> Census:
    return taken(Path(path).read_bytes())


def table_bytes(rows: int) -> int:
    return rows * ANSWER_BYTES


def tier_of(command: int, distinct: int) -> str:
    """How a replacement should answer that command, given how much it varies.

    The multiply is named rather than measured, because the console computes it
    faster than any lookup however few arguments it is given.
    """
    if command == MULTIPLY:
        return COMPUTED
    if distinct <= INLINE_LIMIT:
        return INLINE
    return TABLE


def report(census: Census) -> list[str]:
    lines = [
        f"{census.total:,} exchanges over {len(census.commands)} commands",
        "",
        "  cmd   exchanges   share   distinct   how to answer it",
    ]
    for command in sorted(census.commands, key=lambda one: -census.exchanges(one)):
        distinct = census.distinct(command)
        lines.append(
            f"  ${command:02X}  {census.exchanges(command):10,}  {census.share(command):6.1%}"
            f"  {distinct:9,}   {tier_of(command, distinct)}"
        )
    return lines


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if not argv:
        say("usage: census.py <trace>")
        return 2
    for line in report(read(argv[0])):
        say(line)
    return 0
