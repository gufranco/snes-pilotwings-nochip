import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hardware

MIRROR = 0x7F

WORK_RAM = (0x7E, 0x7F)

RETURN = 0x7D0001

MOST = 6_000_000

CACHED = 0x0DC8

PADDED = 0x0DD0

TABLES = 0xE000

POWER_ON = 0x55

MULTIPLICAND = 0x004202
MULTIPLIER = 0x004203
PRODUCT = 0x004216


class Memory:
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


class Missing(Exception): ...


def symbol(name: str, log: str) -> int:
    for line in log.splitlines():
        head = line.split()
        if len(head) >= 3 and head[0] == name and head[1] == "at":
            return int(head[-1], 16)
        if len(head) >= 3 and head[0] == "SYM" and head[1] == name:
            return int(head[-1], 16)
    raise Missing(name)


def unbuilt(wram: bytes) -> bytearray:
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
