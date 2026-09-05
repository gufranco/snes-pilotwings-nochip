"""What one call to a routine costs, on the processor model rather than a console.

The console cannot answer this, and five changes were rejected on its say-so
before that was understood. A change to the code changes how many console frames
a frame of the game's clock takes, which changes where the demo sits when the
measuring window opens, which changes the scenery and so the work. The same
change then reads as 1.64 console frames faster over one window and 0.23 slower
over another, and neither figure is its cost.

The model has none of that: the same memory, the same entry, the same registers,
and a cycle count belonging to the routine and to nothing else. It is what found
that eight byte table entries are worth a tenth of `$0a`, where the console had
reported them as a loss.

Two things it does not do. It counts the processor's own cycles and does not
know that the console's memory is slower than its cartridge, so a change trading
a memory access for an instruction reads better here than it runs. And it
measures one call from one state, so the state has to be chosen: a snapshot of
the console's memory taken while the demo was flying, with the fields that say
the multiply tables are already built cleared, so the call builds them the way a
first call would.

    python3 tools/cycles.py <image> <assembler log> [<routine>] [<snapshot>]
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hardware

MIRROR = 0x7F
"""Which bank a bank number names the same bytes as.

Every bank from $80 up is a second view of the one 128 below it, and this
project reads its own tables through that view because the cartridge answers
faster there.
"""

WORK_RAM = (0x7E, 0x7F)

RETURN = 0x7D0001
"""Where the routine is made to return to, so the run knows it has ended.

Inside the window bank, which carries no code, so no routine can reach it by
running on. The address pushed is one below, because a long return adds one to
what it pulls.
"""

MOST = 6_000_000

CACHED = 0x0DC8
"""The four constants the multiply tables were last built from."""

PADDED = 0x0DD0
"""The word that says the one byte each table entry opens with has been written."""

TABLES = 0xE000
"""Where the multiply tables begin, in the console's own memory."""

POWER_ON = 0x55

MULTIPLICAND = 0x004202
MULTIPLIER = 0x004203
PRODUCT = 0x004216
"""The console's own multiplier, eight bits by eight into sixteen.

Modelled because the arithmetic this project measures reaches for it, and a
routine that used it would otherwise read nought and answer nothing. The eight
cycle wait the hardware imposes is the caller's business, not this one's.
"""


class Memory:
    """The cartridge as low addressing sees it, over a snapshot of the console's.

    Three regions and nothing else. Banks $7E and $7F are the console's memory.
    The first 8 KiB of it shows again at the bottom of every bank up to $3F and
    from $80 to $BF, which is where the direct page and the two stream buffers
    live. Everything at $8000 and above is the cartridge.
    """

    __slots__ = ("first", "image", "product", "wram")

    def __init__(self, image: bytes, wram: bytearray) -> None:
        self.image = image
        self.wram = wram
        self.first = 0
        self.product = 0

    def _memory_at(self, address: int) -> int | None:
        bank, inside = address >> 16, address & 0xFFFF
        if bank in WORK_RAM:
            return (bank - WORK_RAM[0]) * 0x10000 + inside
        if (bank <= 0x3F or 0x80 <= bank <= 0xBF) and inside < 0x2000:
            return inside
        return None

    def read8(self, address: int) -> int:
        at = address & 0xFFFFFF
        if at == PRODUCT:
            return self.product & 0xFF
        if at == PRODUCT + 1:
            return self.product >> 8 & 0xFF
        where = self._memory_at(at)
        if where is not None:
            return self.wram[where]
        bank, inside = at >> 16, at & 0xFFFF
        if inside >= 0x8000:
            offset = (bank & MIRROR) * 0x8000 + (inside - 0x8000)
            if offset < len(self.image):
                return self.image[offset]
        return 0

    def write8(self, address: int, value: int) -> None:
        at = address & 0xFFFFFF
        if at == MULTIPLICAND:
            self.first = value & 0xFF
        elif at == MULTIPLIER:
            self.product = self.first * (value & 0xFF)
        where = self._memory_at(at)
        if where is not None:
            self.wram[where] = value & 0xFF


class Missing(Exception):
    """A routine the assembler's log does not name, which is a typo not a result."""


def symbol(name: str, log: str) -> int:
    """Where the assembler put that routine, out of what it printed."""
    for line in log.splitlines():
        head = line.split()
        if len(head) >= 3 and head[0] == name and head[1] == "at":
            return int(head[-1], 16)
        if len(head) >= 3 and head[0] == "SYM" and head[1] == name:
            return int(head[-1], 16)
    raise Missing(name)


def unbuilt(wram: bytes) -> bytearray:
    """That snapshot, with the multiply tables and the fields that cache them cleared.

    A snapshot taken mid-flight says the tables are already built for the
    constants it holds, so a call made from it skips the build and measures half
    the routine. Worse, a build whose tables are laid out differently reads the
    snapshot's as though they were its own and answers wrongly, which looks like
    a correctness result and is really a measurement fault.
    """
    out = bytearray(wram)
    for at in range(CACHED, PADDED):
        out[at] ^= 0xFF
    out[PADDED] = 0x00
    out[PADDED + 1] = 0x00
    for at in range(TABLES, 0x10000):
        out[at] = POWER_ON
    return out


def cost(
    image: bytes, log: str, wram: bytearray, entry: str, most: int = MOST
) -> tuple[int, int, bytearray]:
    """The cycles and instructions one call takes, and the memory it left behind.

    A routine that never returns stops at `most` rather than running forever, and
    reports the count it reached, which is how a run that went astray is told
    apart from one that was merely long.
    """
    memory = Memory(image, wram)
    cpu: Any = hardware.load("mos65xx").Cpu("65816", memory=memory)
    cpu.reset()
    cpu.emulation = False
    cpu.m8 = False
    cpu.x8 = False
    cpu.d = 0x0000
    cpu.db = 0x00
    at = symbol(entry, log)
    landing = RETURN - 1
    cpu.write8(0x01FF, landing >> 16)
    cpu.write8(0x01FE, landing >> 8 & 0xFF)
    cpu.write8(0x01FD, landing & 0xFF)
    cpu.s = 0x01FC
    cpu.pc = at & 0xFFFF
    cpu.pb = at >> 16
    started = cpu.cycles
    steps = 0
    while steps < most:
        cpu.step()
        steps += 1
        if (cpu.pb << 16 | cpu.pc) == RETURN:
            break
    return cpu.cycles - started, steps, memory.wram


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if len(argv) < 2:
        say("usage: cycles.py <image> <assembler log> [<routine>] [<memory snapshot>]")
        return 2
    root = Path(__file__).resolve().parent.parent
    entry = argv[2] if len(argv) > 2 else "ground_block"
    where = Path(argv[3]) if len(argv) > 3 else root / "build" / "nb2" / "wram-000300.bin"
    if not where.exists():
        say(f"no memory snapshot at {where}")
        return 1
    cycles, steps, _ = cost(
        Path(argv[0]).read_bytes(),
        Path(argv[1]).read_text(),
        unbuilt(where.read_bytes()),
        entry,
    )
    say(f"{Path(argv[0]).stem:14} {cycles:9,} cycles  {steps:8,} instructions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
