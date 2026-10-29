import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import script

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cycles

import hardware

SOURCE = ("asm/*.asm", "build/lut-*.asm")

LABEL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):")
PLACED = re.compile(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+:?(\S+)")
SHOW = 16


def typed(root: Path) -> set[str]:
    out: set[str] = set()
    for pattern in SOURCE:
        for path in root.glob(pattern):
            for line in path.read_text().splitlines():
                found = LABEL.match(line)
                if found:
                    out.add(found.group(1))
    return out


def marks(symbols: str, keep: set[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for line in symbols.splitlines():
        found = PLACED.match(line.strip())
        if found and found.group(3) in keep:
            out.append((int(found.group(1) + found.group(2), 16), found.group(3)))
    out.sort()
    return out


def owner(placed: list[tuple[int, str]], at: int) -> str:
    low, high = 0, len(placed)
    while low < high:
        middle = (low + high) // 2
        if placed[middle][0] <= at:
            low = middle + 1
        else:
            high = middle
    return placed[low - 1][1] if low else "?"


def spend(
    image: bytes,
    log: str,
    wram: bytearray,
    entry: str,
    placed: list[tuple[int, str]],
) -> tuple[dict[str, int], dict[str, int], int]:
    memory = cycles.Memory(image, wram)
    cpu: Any = hardware.load("mos65xx").Cpu("65816", memory=memory)
    cpu.reset()
    cpu.emulation = False
    cpu.m8 = False
    cpu.x8 = False
    cpu.d = 0x0000
    cpu.db = 0x00
    at = cycles.symbol(entry, log)
    landing = cycles.RETURN - 1
    cpu.write8(0x01FF, landing >> 16)
    cpu.write8(0x01FE, landing >> 8 & 0xFF)
    cpu.write8(0x01FD, landing & 0xFF)
    cpu.s = 0x01FC
    cpu.pc = at & 0xFFFF
    cpu.pb = at >> 16

    took: dict[str, int] = {}
    ran: dict[str, int] = {}
    total = 0
    for _ in range(cycles.MOST):
        here = cpu.pb << 16 | cpu.pc
        before = cpu.cycles
        cpu.step()
        cost = cpu.cycles - before
        who = owner(placed, here)
        took[who] = took.get(who, 0) + cost
        ran[who] = ran.get(who, 0) + 1
        total += cost
        if (cpu.pb << 16 | cpu.pc) == cycles.RETURN:
            break
    return took, ran, total


def report(took: dict[str, int], ran: dict[str, int], total: int, say: Any) -> None:
    say(f"  {'routine':22} {'cycles':>10} {'share':>7} {'instructions':>13}")
    for who, cost in sorted(took.items(), key=lambda pair: -pair[1])[:SHOW]:
        say(f"  {who:22} {cost:10,} {cost / total:6.1%} {ran[who]:13,}")
    say(f"  {'':22} {total:10,} {1.0:6.1%} {sum(ran.values()):13,}")


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    rest = [one for one in argv if one != "--built"]
    built = len(rest) != len(list(argv))
    if len(rest) < 2:
        say("usage: profile.py <image> <symbol file> [<routine>] [<snapshot>] [--built]")
        return 2
    root = Path(__file__).resolve().parent.parent
    entry = rest[2] if len(rest) > 2 else "ground_block"
    where = Path(rest[3]) if len(rest) > 3 else root / "build" / "nb2" / "wram-000300.bin"
    if not where.exists():
        say(f"no memory snapshot at {where}")
        return 1
    placed = marks(Path(rest[1]).read_text(), typed(root))
    if not placed:
        say(f"no source-level labels in {rest[1]}")
        return 1
    log = "\n".join(f"SYM {name} {at:06X}" for at, name in placed)
    raw = where.read_bytes()
    wram = bytearray(raw) if built else cycles.unbuilt(raw)
    took, ran, total = spend(Path(rest[0]).read_bytes(), log, wram, entry, placed)
    say(f"  {entry} on {Path(rest[0]).stem}, tables {'built' if built else 'blank'}\n")
    report(took, ran, total, say)
    return 0


script.entry(__name__, main, sys.argv[1:])
