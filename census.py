"""What the cartridge actually asks the part, counted from a recorded run.

The size of a command's input domain is arithmetic, and it answers a question
nobody needs: what a table would cost if the game could send anything. The game
cannot. What decides whether an answer can be stored is how many distinct
argument sets the cartridge actually sends, and only running it says that.

So this reads a port recording and counts. Every write to the data port that
follows a read starts an exchange, the first byte of it is the command, and the
rest are argument words, low byte first. Accesses to the status register are not
part of the exchange and are skipped.

Which addresses are which is read from the emulator that made the recording
rather than assumed. snes9x maps a low cartridge of this size as
`M_DSP1_LOROM_S` and sets `DSP0.boundary` to `0xc000`, and both its accessors
branch on `address < DSP0.boundary`, so `0x8000` and `0x8001` are the two halves
of one data port and `0xc000` and `0xc001` are the status register. This split on
the lowest bit instead, which is the convention some other parts use. That
dropped the high byte of every argument word, so every word was built from the
low bytes of two different arguments, and it read every status poll as an answer,
so exchanges ended wherever the cartridge happened to look at the ready bit. Both
counts it produced were wrong and neither looked it.

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

The split is the point and the numbers underneath it are not settled. Where an
exchange begins and ends is read out of the byte stream here, and command `$0a`
does not respect that reading: see `exchanges`. Nothing in this repository sizes
a table from what this counts until an exchange is cut at the site that issued it
instead, which is entry 2c in OPEN-QUESTIONS.md.
"""

import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, override

RECORD_BYTES = 12

DATA_PORT = 0x8000
"""The low half of the data port, and where a caller writes a command byte.

A sixteen bit access to it also touches `0x8001`, which carries the high byte of
the same word. Both are the data port.
"""

STATUS_BOUNDARY = 0xC000
"""Where the data port stops and the status register starts.

`DSP0.boundary` in snes9x, for a low cartridge no larger than a megabyte, which
is what all three of these are. Every address below it is the data port and every
address at or above it is the status register.
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

    That rule holds for a command that is written whole and then answered whole,
    and command `$0a` is not one: it answers with a long stream the cartridge
    reads in a loop, and the part takes writes during that stream rather than
    treating them as a new command. A run bounded by a read therefore splits one
    of those exchanges into pieces and can join the tail of one to the head of
    the next, so a count taken this way is a reading of the byte stream and not a
    count of what the cartridge asked.
    """
    found: list[Exchange] = []
    run: list[int] = []
    for at in range(len(trace) // RECORD_BYTES):
        _, _, address, is_read, byte = struct.unpack_from("<IIHBB", trace, at * RECORD_BYTES)
        if address >= STATUS_BOUNDARY:
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
