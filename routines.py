"""Run the replacement's own 65816 against the part it replaces.

The routines in `asm/` are assembled, loaded into the processor model, and given
the same command and arguments the part is given. The two answers have to match
on every input tried, and a routine that does not match is not written down as
done.

Three things this needs that a bare processor does not have.

The console's multiplier is one: `$4202`, `$4203` and `$4216` are hardware, and
on a plain 65816 they are ordinary bytes, so every multiply would answer nothing
and every comparison would fail for a reason that has nothing to do with the
routine. `Console` supplies that and only that.

The direct page is the second. It lives in bank zero whatever the data bank
holds, so arguments go there rather than anywhere else. Putting them where the
data bank points is a way to watch a correct routine read nothing.

The third belongs to the assembler and is recorded in `asm/dsp1-ops.asm`,
because that is the file it bites: the width of an immediate comes from how many
digits were typed rather than from the mode the register is in, so a short one
shifts every instruction after it and the routine runs into whatever the shifted
bytes happen to spell.
"""

import random
from collections.abc import Iterator, Sequence
from typing import Any

import hardware
import microcode

CODE = 0x0F8000
"""Where `asm/ops-check.asm` places the routines."""

FILE_AT = 0x078000
"""The same address as a position in the file, under low ROM addressing."""

SPAN = 0x0400
"""How much of the image holds routines. Leaving it is how a return is seen."""

STACK = 0x01FF

ARG = 0x00
OUT = 0x10

MOST_STEPS = 40000

MULTIPLICAND = 0x004202
MULTIPLIER = 0x004203
PRODUCT = 0x004216


class Console:
    """Flat memory, plus the one piece of console hardware the routines use."""

    __slots__ = ("cells", "first", "product")

    def __init__(self) -> None:
        self.cells: dict[int, int] = {}
        self.first = 0
        self.product = 0

    def read8(self, address: int) -> int:
        at = address & 0xFFFFFF
        if at == PRODUCT:
            return self.product & 0xFF
        if at == PRODUCT + 1:
            return self.product >> 8 & 0xFF
        return self.cells.get(at, 0)

    def write8(self, address: int, value: int) -> None:
        at = address & 0xFFFFFF
        value &= 0xFF
        if at == MULTIPLICAND:
            self.first = value
        elif at == MULTIPLIER:
            self.product = self.first * value
        self.cells[at] = value


class TooLong(Exception):
    """A routine that never returned, which is a defect and not a slow answer."""


def run(image: bytes, entry: int, words: Sequence[int], answers: int) -> tuple[int, ...]:
    """That routine, on those arguments, as the processor runs it."""
    cpu = hardware.load("mos65xx").Cpu("65816", memory=Console())
    for step, one in enumerate(image[FILE_AT : FILE_AT + SPAN]):
        cpu.write8(CODE + step, one)
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
    """What the part answers, which is the only thing a routine is right against."""
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
    """Argument sets to try, the same ones on every run.

    Seeded rather than arbitrary, so a failure names a case somebody else can
    reach. The whole sixteen bit range is drawn from rather than a plausible
    one: a routine right only on the values a game happens to send is a routine
    nobody has tested.
    """
    source = random.Random(seed)
    for _ in range(how_many):
        yield tuple(source.randrange(0x10000) for _ in range(count))
