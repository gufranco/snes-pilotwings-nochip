"""The three tables that carry `$02`'s state into the cartridge.

`$0a` reads a horizon, two mantissas, two exponents and a matrix, and `$02`
writes every one of them. The cartridge therefore needs that state, not just the
four words `$02` answers, and the recorded-answer table carries only the answer.

Stored flat against `$02`'s seven argument words this would be 6,980 rows of
nine words, which is 123 KiB. `parameter.py` measures that the state separates,
each piece answering to fewer arguments than the whole, and driving the part
across all 6,980 sets confirms no piece needs more than the arguments named. Split
that way it is 31.7 KiB, which fits in the banks this cartridge leaves empty.

Each table is written as fixed-width rows, key first, sorted by key, so the
cartridge can bisect rather than walk. That matters because `$02` runs once a
frame and `$0a` reads its result 191 times, so the search is paid once and the
arithmetic 191 times.

Nothing here is committed. It reads a cartridge dump and a part the person
running it already owns, and writes into the ignored build directory.
"""

import struct
from collections.abc import Mapping

WORD = 0x10000
"""One more than the largest word a row can hold, since every field is 16 bits."""


class TooWide(Exception):
    """A key or a word that will not fit the sixteen bits a row gives it.

    Raised rather than masked, because a masked value is a row that looks
    ordinary and answers wrongly, which is the failure this project has been
    caught by before.
    """


class Ragged(Exception):
    """Rows that are not all the same width.

    The cartridge bisects by multiplying an index by a stride, so a table whose
    rows differ in width has no stride and cannot be searched at all.
    """


def stride(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> int:
    """How many words a row takes, key included."""
    for key, words in table.items():
        return len(key) + len(words)
    return 0


def rows(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> int:
    """How many rows the table holds."""
    return len(table)


def checked(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> None:
    """Refuse a table the cartridge could not search or could not hold."""
    width = None
    for key, words in table.items():
        shape = (len(key), len(words))
        if width is None:
            width = shape
        elif shape != width:
            raise Ragged(f"row {key} is {shape}, an earlier row is {width}")
        for value in (*key, *words):
            if not -WORD // 2 <= value < WORD:
                raise TooWide(f"row {key} carries {value}, which is not a word")


def packed(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> bytes:
    """The table as the cartridge reads it: key then words, sorted, little endian."""
    checked(table)
    out = bytearray()
    for key in sorted(table):
        for value in (*key, *table[key]):
            out += struct.pack("<H", value & 0xFFFF)
    return bytes(out)
