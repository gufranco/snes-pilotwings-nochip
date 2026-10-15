import struct
from collections.abc import Mapping

WORD = 0x10000


class TooWide(Exception): ...


class Ragged(Exception): ...


def stride(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> int:
    for key, words in table.items():
        return len(key) + len(words)
    return 0


def rows(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> int:
    return len(table)


def checked(table: Mapping[tuple[int, ...], tuple[int, ...]]) -> None:
    width: tuple[int, int] | None = None
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
    checked(table)
    out = bytearray()
    for key in sorted(table):
        for value in (*key, *table[key]):
            out += struct.pack("<H", value & 0xFFFF)
    return bytes(out)
