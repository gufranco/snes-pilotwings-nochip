import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, override

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
    __slots__ = ("command", "words")

    def __init__(self, command: int, words: tuple[int, ...]) -> None:
        self.command = command
        self.words = words

    @override
    def __repr__(self) -> str:
        return f"<Exchange ${self.command:02X} {len(self.words)} words>"


class Census:
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
    seen: dict[int, Counter[tuple[int, ...]]] = defaultdict(Counter)
    for one in exchanges(trace):
        seen[one.command][one.words] += 1
    return Census(dict(seen))


def read(path: Path | str) -> Census:
    return taken(Path(path).read_bytes())


def table_bytes(rows: int) -> int:
    return rows * ANSWER_BYTES


def tier_of(command: int, distinct: int) -> str:
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
