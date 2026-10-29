import struct
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import script
import sites

STA_LONG = 0x8F
LDA_LONG = 0xAF
JSL = 0x22
JSR = 0x20

COMBINING = {0x6F: "dsp_read_adc", 0x4F: "dsp_read_eor"}

FIRST_BANK = 0x30
LAST_BANK = 0x3F

PORT_FROM = 0x8000

STATUS_FROM = 0xC000

PORT_PAGE = 0x80
STATUS_PAGE = 0xC0

SITE_BYTES = 4

CHIPSET_PLAIN = 0x00

HEADER_SPEED = 0x7FD5
HEADER_CHIPSET = 0x7FD6
HEADER_COMPLEMENT = 0x7FDC
HEADER_CHECKSUM = 0x7FDE

FAST = 0x10


def classify(rom: bytes, at: int) -> str | None:
    opcode = rom[at]
    if opcode not in (STA_LONG, LDA_LONG):
        return None
    if not FIRST_BANK <= rom[at + 3] <= LAST_BANK:
        return None
    status = (rom[at + 1] | rom[at + 2] << 8) >= STATUS_FROM
    if opcode == STA_LONG:
        return "dsp_ignore" if status else "dsp_write"
    return "dsp_status" if status else "dsp_read"


def combining(rom: bytes, limit: int | None = None) -> dict[int, str]:
    edge = len(rom) if limit is None else limit
    found: dict[int, str] = {}
    for at in range(min(edge, len(rom)) - SITE_BYTES + 1):
        stub = COMBINING.get(rom[at])
        if stub is None or rom[at + 1] != 0x00:
            continue
        if not FIRST_BANK <= rom[at + 3] <= LAST_BANK:
            continue
        if not PORT_FROM <= (rom[at + 1] | rom[at + 2] << 8) < STATUS_FROM:
            continue
        found[at] = stub
    return found


def plan(rom: bytes, limit: int | None = None, reached: Any = None) -> dict[int, str]:
    edge = len(rom) if limit is None else limit
    found: dict[int, str] = {}
    for at in (reached or sites.reached)(rom):
        if at + SITE_BYTES > edge:
            continue
        stub = classify(rom, at)
        if stub is not None:
            found[at] = stub
    found.update(combining(rom, edge))
    return found


def applied(rom: bytes, where: Mapping[int, str], stubs: Mapping[str, int]) -> bytes:
    out = bytearray(rom)
    for at, stub in where.items():
        target = stubs[stub]
        out[at] = JSL
        out[at + 1] = target & 0xFF
        out[at + 2] = target >> 8 & 0xFF
        out[at + 3] = target >> 16 & 0xFF
    return bytes(out)


HEADER_SIZE = 0x7FD7


def declared(rom: bytes, fast: bool) -> bytes:
    out = bytearray(rom)
    out[HEADER_CHIPSET] = CHIPSET_PLAIN
    out[HEADER_SIZE] = max((len(rom) // 1024).bit_length() - 1, 1)
    if fast:
        out[HEADER_SPEED] |= FAST
    return bytes(out)


def checksummed(rom: bytes) -> bytes:
    out = bytearray(rom)
    out[HEADER_CHECKSUM : HEADER_CHECKSUM + 2] = b"\x00\x00"
    out[HEADER_COMPLEMENT : HEADER_COMPLEMENT + 2] = b"\xff\xff"
    total = sum(out) & 0xFFFF
    struct.pack_into("<H", out, HEADER_CHECKSUM, total)
    struct.pack_into("<H", out, HEADER_COMPLEMENT, total ^ 0xFFFF)
    return bytes(out)


NOP = 0xEA

PEA = 0xF4

WINDOW_BANK = 0x7D

RASTER_THIRD = 0x0714B

ARM_JUMP = 0x07E7E

ARM_GAP = 0x07E84

JML = 0x5C

NMI_VECTOR = 0x07FEA

NMI_HANDLER = 0xF0A0


SPANS = (
    (0x04AA8, 0x04AB9, "dsp_route_0a"),
    (0x04AB9, 0x04AD1, "dsp_horizon"),
    (0x04AD1, 0x04B0F, "dsp_stream"),
    (0x04B17, 0x04B39, "dsp_route_10"),
    (0x04B4E, 0x04BB2, "dsp_route_02"),
)


HOOKED = (
    (0x00054, 0x000C4),
    (0x0160A, 0x0164F),
    (0x04AAC, 0x04BA5),
    (0x04D83, 0x04DAD),
    (0x04DCD, 0x050A8),
    (0x051F7, 0x05280),
    (0x05447, 0x05679),
)

HOOKS = {
    0x8D: "thunk_sta",
    0x8C: "thunk_sty",
    0x8E: "thunk_stx",
    0x9C: "thunk_stz",
    0xAD: "thunk_lda",
    0xAC: "thunk_ldy",
    0xAE: "thunk_ldx",
    0x6D: "thunk_adc",
    0xED: "thunk_sbc",
}

STATUS_HOOKS = {
    0xAC: "thunk_ldy_status",
    0xAE: "thunk_ldx_status",
    0x2C: "thunk_bit_status",
}

ACCESS_BYTES = 3

WINDOWED = (
    (0x0004E, 0x00070),
    (0x00071, 0x000C5),
    (0x01601, 0x01656),
    (0x04AA4, 0x04B10),
    (0x04B13, 0x04BB3),
    (0x04B4A, 0x04BB3),
    (0x04DB3, 0x04FCE),
    (0x0503F, 0x050AB),
    (0x051F1, 0x05285),
    (0x05447, 0x054AA),
    (0x05507, 0x0554C),
    (0x055D8, 0x05682),
)

MIRRORED = {
    (0x6D, 0x0130): "thunk_adc_0130",
    (0x8D, 0x0130): "thunk_sta_0130",
    (0xB9, 0x1800): "thunk_lda_1800y",
    (0xB9, 0x1808): "thunk_lda_1808y",
    (0xBD, 0x1810): "thunk_lda_1810x",
    (0xBD, 0x1812): "thunk_lda_1812x",
    (0xBD, 0x1814): "thunk_lda_1814x",
    (0xAD, 0x1AEA): "thunk_lda_1aea",
    (0xAD, 0x1848): "thunk_lda_1848",
    (0xAD, 0x185A): "thunk_lda_185a",
    (0xAD, 0x1858): "thunk_lda_1858",
    (0xAD, 0x1828): "thunk_lda_1828",
    (0xAD, 0x182A): "thunk_lda_182a",
    (0xAD, 0x182C): "thunk_lda_182c",
    (0xAD, 0x182E): "thunk_lda_182e",
    (0xCD, 0x182C): "thunk_cmp_182c",
    (0xCD, 0x182E): "thunk_cmp_182e",
    (0xBD, 0x1820): "thunk_lda_1820x",
    (0xBD, 0x1828): "thunk_lda_1828x",
    (0xBD, 0x1840): "thunk_lda_1840x",
    (0xBD, 0x1860): "thunk_lda_1860x",
    (0xAD, 0x1AC3): "thunk_lda_1ac3",
    (0xAD, 0x1870): "thunk_lda_1870",
    (0xAD, 0x1876): "thunk_lda_1876",
    (0xAE, 0x1AF9): "thunk_ldx_1af9",
}


def hooked(rom: bytes, stubs: Mapping[str, int]) -> tuple[bytes, int]:
    out = bytearray(rom)
    found: dict[int, str] = {}
    for start, end in HOOKED:
        for at in range(start, min(end, len(rom)) - 2):
            if out[at + 1] != 0x00:
                continue
            page = out[at + 2]
            if page == PORT_PAGE:
                name = HOOKS.get(out[at])
            elif page == STATUS_PAGE:
                name = STATUS_HOOKS.get(out[at])
            else:
                continue
            if name is not None:
                found[at] = name

    for start, end in WINDOWED:
        for at in range(start, min(end, len(rom)) - 2):
            name = MIRRORED.get((out[at], out[at + 1] | out[at + 2] << 8))
            if name is not None:
                found[at] = name

    for at, name in found.items():
        target = stubs[name]
        out[at] = JSR
        out[at + 1] = target & 0xFF
        out[at + 2] = target >> 8 & 0xFF
    return bytes(out), len(found)


def spanned(rom: bytes, stubs: Mapping[str, int]) -> bytes:
    out = bytearray(rom)
    for start, end, stub in SPANS:
        target = stubs[stub]
        out[start] = JSL
        out[start + 1] = target & 0xFF
        out[start + 2] = target >> 8 & 0xFF
        out[start + 3] = target >> 16 & 0xFF
        for at in range(start + SITE_BYTES, end):
            out[at] = NOP
    return bytes(out)


def rearmed(rom: bytes, stubs: Mapping[str, int]) -> bytes:
    out = bytearray(rom)
    target = stubs["raster_rearm"]
    out[RASTER_THIRD] = target & 0xFF
    out[RASTER_THIRD + 1] = target >> 8 & 0xFF
    return bytes(out)


class ArmGapTaken(Exception): ...


def held(rom: bytes, stubs: Mapping[str, int]) -> bytes:
    out = bytearray(rom)
    if any(out[ARM_GAP + at] for at in range(6)):
        raise ArmGapTaken(
            f"the six bytes at ${ARM_GAP:05x} hold"
            f" {out[ARM_GAP : ARM_GAP + 6].hex(' ')} rather than nothing"
        )

    target = stubs["raster_arm_wait"]
    out[ARM_GAP] = JML
    out[ARM_GAP + 1] = target & 0xFF
    out[ARM_GAP + 2] = target >> 8 & 0xFF
    out[ARM_GAP + 3] = target >> 16 & 0xFF

    where = 0x8000 + (ARM_GAP & 0x7FFF)
    out[ARM_JUMP + 1] = where & 0xFF
    out[ARM_JUMP + 2] = where >> 8 & 0xFF
    return bytes(out)


class VectorMoved(Exception): ...


def hooked_nmi(rom: bytes, stubs: Mapping[str, int]) -> bytes:
    out = bytearray(rom)
    held = out[NMI_VECTOR] | out[NMI_VECTOR + 1] << 8
    if held != NMI_HANDLER:
        raise VectorMoved(
            f"the interrupt vector at ${NMI_VECTOR:05x} names ${held:04x}"
            f" rather than ${NMI_HANDLER:04x}"
        )
    target = stubs["raster_nmi"]
    out[NMI_VECTOR] = target & 0xFF
    out[NMI_VECTOR + 1] = target >> 8 & 0xFF
    return bytes(out)


def redirected(rom: bytes) -> tuple[bytes, int]:
    out = bytearray(rom)
    want = bytes([PEA, LAST_BANK, 0x00])
    moved = 0
    at = 0
    while True:
        at = out.find(want, at)
        if at < 0:
            break
        out[at + 1] = WINDOW_BANK
        moved += 1
        at += 3
    return bytes(out), moved


def report(where: Mapping[int, str]) -> list[str]:
    counts: dict[str, int] = {}
    for stub in where.values():
        counts[stub] = counts.get(stub, 0) + 1
    lines = [f"{len(where)} sites replaced, {len(SPANS)} runs replaced whole"]
    for stub in sorted(counts):
        lines.append(f"  {stub:12} {counts[stub]:4}")
    return lines


def symbols(where: Path) -> dict[str, int]:
    return {
        name: int(value, 16)
        for name, value in (line.split() for line in where.read_text().splitlines() if line.strip())
    }


def main(argv: Sequence[str] = (), say: Any = print) -> int:
    if len(argv) < 4:
        say("usage: patch.py <rom> <symbols> <out> <game bytes> [--slow]")
        return 2
    rom = Path(argv[0]).read_bytes()
    where = plan(rom, limit=int(argv[3]))
    if not where:
        say("no sites found: this image does not reach the part")
        return 1
    stubs = symbols(Path(argv[1]))
    out = applied(rom, where, stubs)
    out = spanned(out, stubs)
    out, replaced = hooked(out, stubs)
    out = rearmed(out, stubs)
    out = held(out, stubs)
    out = hooked_nmi(out, stubs)
    out, moved = redirected(out)
    say(f"{moved} data bank pushes redirected")
    say(f"{replaced} three byte accesses replaced one at a time")
    out = declared(out, fast="--slow" not in argv)
    out = checksummed(out)
    Path(argv[2]).write_bytes(out)
    for line in report(where):
        say(line)
    return 0


script.entry(__name__, main, sys.argv[1:])
