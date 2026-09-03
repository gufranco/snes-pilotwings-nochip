"""Turn a cartridge that needs the DSP-1 into one that does not.

The game never calls anything. It reads and writes an address in bank $3F, and
the part answered there. So the conversion is not a matter of pointing a call
somewhere else: every one of those accesses has to become a call.

What makes that possible is a coincidence of encoding. Every one of the 122
accesses is a single four byte long instruction, `sta $3Fxxxx` or `lda $3Fxxxx`,
and `jsl` is also four bytes. So each one is replaced where it stands, with
nothing moved, no space borrowed and no branch retargeted. A patch that had to
relocate code would have to understand the routine around it; this one does not
have to understand anything.

Which stub a site gets is decided by its operand. The board decodes the part
across banks $30 to $3F, and inside any of them everything below $C000 is the
data port and everything above is the status register. The game uses the whole
range: 100 of the accesses name bank $3F and 22 name one of the other fifteen.

    sta, data      ->  jsl dsp_write
    lda, data      ->  jsl dsp_read
    lda, status    ->  jsl dsp_status
    sta, status    ->  jsl dsp_ignore

Nothing here is committed and nothing here can be. It reads a cartridge dump the
person running it already owns, writes into the ignored build directory, and the
digests in artifacts.manifest.json say whether the dump was the right one.
"""

import struct
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import sites

STA_LONG = 0x8F
LDA_LONG = 0xAF
JSL = 0x22

FIRST_BANK = 0x30
LAST_BANK = 0x3F
"""The banks the part answered in on this board.

Sixteen of them, not one. The board decodes the part across the whole range, so
the same two registers appear in every bank from $30 to $3F, and the game uses
that: 100 accesses name bank $3F and 22 name one of the others. Checking only
$3F leaves those 22 reaching a part that is no longer there.

These match snes-driver-python's window for this part on a low cartridge, which
is held against a library of real cartridges rather than against a reading of
one. They are restated here so that a change to either is a visible
disagreement rather than a silent one.
"""

STATUS_FROM = 0xC000
"""Where the data port stops and the status register starts inside a bank."""

SITE_BYTES = 4
"""The length of the instruction at a site, and of the call that replaces it.

The whole approach rests on these being equal. A long store or load names a
24-bit address, which is one opcode and three bytes, and so does a long call.
"""

CHIPSET_PLAIN = 0x00
"""What the header carries when a cartridge is ROM and nothing else.

The dumps say $03, which is ROM plus a coprocessor. Leaving that would tell an
emulator to attach a DSP-1 the image no longer talks to.
"""

HEADER_SPEED = 0x7FD5
HEADER_CHIPSET = 0x7FD6
HEADER_COMPLEMENT = 0x7FDC
HEADER_CHECKSUM = 0x7FDE

FAST = 0x10
"""The bit in the speed byte that asks for three cycle ROM reads instead of four.

It applies only to banks $80 and above, so setting it is worth nothing unless
the code that benefits is reached through that mirror, and it changes the timing
of everything the game does rather than only of what this conversion added.
"""


def classify(rom: bytes, at: int) -> str | None:
    """Which stub the site at that offset needs, or nothing if it is not one."""
    opcode = rom[at]
    if opcode not in (STA_LONG, LDA_LONG):
        return None
    if not FIRST_BANK <= rom[at + 3] <= LAST_BANK:
        return None
    status = (rom[at + 1] | rom[at + 2] << 8) >= STATUS_FROM
    if opcode == STA_LONG:
        return "dsp_ignore" if status else "dsp_write"
    return "dsp_status" if status else "dsp_read"


def plan(rom: bytes, limit: int | None = None, reached: Any = None) -> dict[int, str]:
    """Every site in the game's own code, and the stub each one needs.

    `limit` is where the game ends. Everything past it is what this project
    added, and the scanner has no way to tell code from data: a table of
    recorded answers is millions of bytes, and some of them spell a long store
    into the part's window by coincidence. Scanning the whole image found 408
    sites where the game has 122, and the difference was table entries about to
    be overwritten with a call.

    A reported offset this cannot replace is skipped rather than guessed at. The
    scanner reports long loads and stores, which is exactly what fits in four
    bytes; anything else reaching the window would need the routine around it
    moved, which is a different job from this one.
    """
    edge = len(rom) if limit is None else limit
    found: dict[int, str] = {}
    for at in (reached or sites.reached)(rom):
        if at + SITE_BYTES > edge:
            continue
        stub = classify(rom, at)
        if stub is not None:
            found[at] = stub
    return found


def applied(rom: bytes, where: Mapping[int, str], stubs: Mapping[str, int]) -> bytes:
    """The image with every site turned into a call to its stub."""
    out = bytearray(rom)
    for at, stub in where.items():
        target = stubs[stub]
        out[at] = JSL
        out[at + 1] = target & 0xFF
        out[at + 2] = target >> 8 & 0xFF
        out[at + 3] = target >> 16 & 0xFF
    return bytes(out)


def declared(rom: bytes, fast: bool) -> bytes:
    """The image with its header saying what it now is."""
    out = bytearray(rom)
    out[HEADER_CHIPSET] = CHIPSET_PLAIN
    if fast:
        out[HEADER_SPEED] |= FAST
    return bytes(out)


def checksummed(rom: bytes) -> bytes:
    """The image with its header checksum brought back into agreement.

    A cartridge carries a sum of all its bytes and that sum inverted. Nothing on
    real hardware checks either, but an emulator reports a mismatch, and a
    reader who sees one cannot tell a deliberate change from a corrupt file.

    The two fields are cleared to a fixed pattern before the sum is taken, which
    is what makes running this twice give the same answer.
    """
    out = bytearray(rom)
    out[HEADER_CHECKSUM : HEADER_CHECKSUM + 2] = b"\x00\x00"
    out[HEADER_COMPLEMENT : HEADER_COMPLEMENT + 2] = b"\xff\xff"
    total = sum(out) & 0xFFFF
    struct.pack_into("<H", out, HEADER_CHECKSUM, total)
    struct.pack_into("<H", out, HEADER_COMPLEMENT, total ^ 0xFFFF)
    return bytes(out)


def report(where: Mapping[int, str]) -> list[str]:
    counts: dict[str, int] = {}
    for stub in where.values():
        counts[stub] = counts.get(stub, 0) + 1
    lines = [f"{len(where)} sites replaced"]
    for stub in sorted(counts):
        lines.append(f"  {stub:12} {counts[stub]:4}")
    return lines


def symbols(where: Path) -> dict[str, int]:
    """Where each stub landed, as the assembler reported it."""
    return {
        name: int(value, 16)
        for name, value in (line.split() for line in where.read_text().splitlines() if line.strip())
    }


def main(argv: Sequence[str] = (), say: Any = print) -> int:
    if len(argv) < 4:
        say("usage: patch.py <rom> <symbols> <out> <game bytes> [--fast]")
        return 2
    rom = Path(argv[0]).read_bytes()
    where = plan(rom, limit=int(argv[3]))
    if not where:
        say("no sites found: this image does not reach the part")
        return 1
    out = applied(rom, where, symbols(Path(argv[1])))
    out = declared(out, fast="--fast" in argv)
    out = checksummed(out)
    Path(argv[2]).write_bytes(out)
    for line in report(where):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
