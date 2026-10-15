import random
from collections.abc import Iterator, Sequence
from typing import Any

import hardware
import microcode

CODE = 0x0F8000

FILE_AT = 0x078000

SPAN = 0x0400

STACK = 0x01FF

ARG = 0x00

OUT = 0x0E00

MOST_STEPS = 40000

MULTIPLICAND = 0x004202
MULTIPLIER = 0x004203

MIRROR = 0x7F

PRODUCT = 0x004216


class Console:
    __slots__ = ("cells", "first", "image", "product")

    def __init__(self, image: bytes = b"") -> None:
        self.cells: dict[int, int] = {}
        self.first = 0
        self.product = 0
        self.image = image

    def read8(self, address: int) -> int:
        at = address & 0xFFFFFF
        if at == PRODUCT:
            return self.product & 0xFF
        if at == PRODUCT + 1:
            return self.product >> 8 & 0xFF
        if at in self.cells:
            return self.cells[at]
        bank, inside = at >> 16, at & 0xFFFF
        if self.image and inside >= 0x8000:
            offset = (bank & MIRROR) * 0x8000 + (inside - 0x8000)
            if offset < len(self.image):
                return self.image[offset]
        return 0

    def write8(self, address: int, value: int) -> None:
        at = address & 0xFFFFFF
        value &= 0xFF
        if at == MULTIPLICAND:
            self.first = value
        elif at == MULTIPLIER:
            self.product = self.first * value
        self.cells[at] = value


class TooLong(Exception): ...


def run(image: bytes, entry: int, words: Sequence[int], answers: int) -> tuple[int, ...]:
    cpu = hardware.load("mos65xx").Cpu("65816", memory=Console(image))
    for at, word in enumerate(words):
        cpu.write8(ARG + at * 2, word & 0xFF)
        cpu.write8(ARG + at * 2 + 1, word >> 8)
    cpu.reset()
    cpu.emulation = False
    cpu.d = 0x0000
    cpu.db = 0x7E
    cpu.write8(STACK, CODE >> 16)
    cpu.write8(STACK - 1, 0xFF)
    cpu.write8(STACK - 2, 0xFF)
    cpu.s = STACK - 3
    cpu.pc = entry & 0xFFFF
    cpu.pb = entry >> 16
    for _ in range(MOST_STEPS):
        here = (cpu.pb << 16) | cpu.pc
        if here < CODE or here > CODE + SPAN:
            break
        cpu.step()
    else:
        raise TooLong(f"${entry:06x} ran {MOST_STEPS} instructions without returning")
    return tuple(cpu.read8(OUT + k * 2) | cpu.read8(OUT + k * 2 + 1) << 8 for k in range(answers))


def asked(command: int, words: Sequence[int], answers: int, mask: str = microcode.MASK) -> Any:
    part = hardware.load("snesdsp").Chip(mask)
    part.write(command)
    for word in words:
        part.write(word & 0xFF)
        part.write(word >> 8)
    got: list[int] = []
    for _ in range(4000):
        part.step(16)
        if part.asking:
            got.append(part.read())
            if len(got) >= answers * 2:
                break
    return tuple(got[k] | got[k + 1] << 8 for k in range(0, len(got) - 1, 2))


def inputs(count: int, how_many: int, seed: int) -> Iterator[tuple[int, ...]]:
    source = random.Random(seed)
    for _ in range(how_many):
        yield tuple(source.randrange(0x10000) for _ in range(count))
