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
JSR = 0x20

COMBINING = {0x6F: "dsp_read_adc", 0x4F: "dsp_read_eor"}
"""Long instructions that read the part and compute with what they read.

`adc $3f8000` and `eor $3f8000` are four bytes and reach the part the same way a
long load does, and neither is a load. The driver model this project is checked
against searches for the long store and the long load only, so it reports neither,
and every one of these went unreplaced from the first build until they were found:
seven sites, reading whatever the answer table happens to hold at $3f8000 and
computing with it.

One of them decides whether an exchange happens at all. `adc $3f8000` at
$00:A1AD is followed by `bmi`, and the branch skips the whole of `$06`, which is
the command this cartridge asks more often than any other. So `$06` was never
asked, and the flight model has been running without it.

The encoding is exact rather than heuristic, the same way the model's own search
is: no other instruction puts that bank and that address in those three bytes.
"""

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

PORT_FROM = 0x8000
"""Where the part's window starts inside a bank.

Below this is the console's own system area rather than the cartridge, so a long
instruction naming it is not reaching the part however much its bank looks like
it. `classify` needs no such bound because the driver model has already applied
the window before it is asked; `combining` does its own search and so applies it
here.
"""

STATUS_FROM = 0xC000
"""Where the data port stops and the status register starts inside a bank."""

PORT_PAGE = 0x80
STATUS_PAGE = 0xC0
"""The high byte of each, as a three byte instruction spells it."""

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


def combining(rom: bytes, limit: int | None = None) -> dict[int, str]:
    """Every long read-modify access to the part, and the stub each one needs.

    Separate from the driver model's own search because the model reports loads
    and stores, which is the right answer to the question it asks. These are a
    third shape, and they are found here rather than by widening that model,
    because the model is held against a library of real cartridges and this is
    one cartridge's habit.
    """
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

    `combining` adds the third shape the scanner does not report, a long
    instruction that reads the part and computes with what it reads. Those are
    four bytes as well, so they are replaced the same way.
    """
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
    """The image with every site turned into a call to its stub."""
    out = bytearray(rom)
    for at, stub in where.items():
        target = stubs[stub]
        out[at] = JSL
        out[at + 1] = target & 0xFF
        out[at + 2] = target >> 8 & 0xFF
        out[at + 3] = target >> 16 & 0xFF
    return bytes(out)


HEADER_SIZE = 0x7FD7
"""Where the header records how large the image is, as a power of two kibibytes.

The conversion grows the cartridge well past what the retail one was, and a
header still claiming the old size tells an emulator to map only part of what is
there. The tables that answer the commands live in the part it would leave out.
"""


def declared(rom: bytes, fast: bool) -> bytes:
    """The image with its header saying what it now is."""
    out = bytearray(rom)
    out[HEADER_CHIPSET] = CHIPSET_PLAIN
    out[HEADER_SIZE] = max((len(rom) // 1024).bit_length() - 1, 1)
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


NOP = 0xEA

PEA = 0xF4
"""The instruction that pushes a bank number for the one after it to pull.

"pea $003F" then "plb" is how this game points its data bank at the part, and
it is the only three byte thing in the whole arrangement that names the part in
a way anything can recognise. Rewriting the bank it names moves every absolute
access that follows, without touching any of them.
"""

WINDOW_BANK = 0x7D
"""The bank those accesses are sent to instead.

It has to be one this project fills, because the accesses land on whatever is
there: a status poll waits for a byte with its top bit set and spins forever on
one without. asm/dsp1-port.asm puts that byte at every address the poll can
name.
"""

SPANS = (
    (0x04AA8, 0x04AB9, "dsp_route_0a"),
    (0x04AB9, 0x04AD1, "dsp_horizon"),
    (0x04AD1, 0x04B0F, "dsp_stream"),
    (0x04B17, 0x04B39, "dsp_route_10"),
    (0x04B4E, 0x04BB2, "dsp_route_02"),
)
"""Runs of the game's own code replaced whole, rather than one instruction each.

The instruction-for-instruction replacement above works because a long store or
load and a long call are both four bytes. Some of what this cartridge does to
reach the part is not a long instruction at all: it sets the data bank to $3F
and uses three byte absolute addressing, which has no room for a call and
nothing in the operand for a scanner to recognise.

What it does have is length. $04AD1 to $04B0E is the loop that reads $0a's 704
word answer, 62 bytes of it, and a call needs four. So the loop is replaced as a
whole and the rest filled with instructions that do nothing.

Five instructions inside that one span account for 12,224,960 of the 15,673,471
accesses the recording holds, which is 78% of everything the cartridge ever
asked the part.

Four of the five carry an exchange. $02 is the one that mattered most and was
found last: it writes the ten words $0a reads to draw the ground, and every one
of its own four answer words came back nought until its run was replaced. $0a's
command byte and argument go the same way, which is why the line the ground
starts at had to be recovered rather than read out of the port.

The fifth, `dsp_horizon`, is not an exchange. It is eight instructions of the
game reaching its own memory, which the redirect breaks because they are three
byte absolute instructions and the bank they land in is the one being
redirected. asm/dsp1-port.asm says what they carry and what it cost to leave
them alone.

None of the four starts at the `pea` that sets the data bank. On the path the
demo takes, the one before $02 is jumped over, so the byte its closing `plb`
collects was pushed by the `pea` before the $10 run. A run that swallowed a `pea`
would leave the stack one byte out and black the screen.
"""


HOOKED = (
    (0x00054, 0x000C4),
    (0x0160A, 0x0164F),
    (0x04AAC, 0x04BA5),
    (0x04D83, 0x04DAD),
    (0x04DCD, 0x050A8),
    (0x051F7, 0x05280),
    (0x0547C, 0x05679),
)
"""The runs of the game's own code whose accesses are replaced one at a time.

Twelve places set the data bank to the part and then use three byte absolute
instructions, which have no room for a four byte call and nothing in the operand
a scanner of long instructions can recognise. Those twelve overlap into these six
runs, which hold 200 accesses between them.

Three of the twelve are one run of code that talks to the part and then stops, and
those are lifted out whole by SPANS instead. The rest are not shaped that way: the
flight model's accesses are interleaved with its own clamping and accumulating,
so replacing the region means rewriting how the plane flies.

The bounds come from disassembling forward from each of the twelve pushes,
stopping where that routine returns, and clustering the accesses found. Stopping
at the return is what makes them right: a walk that runs past it decodes the next
routine at the wrong register widths and reports accesses that are not there,
which put 44 bytes of ordinary arithmetic inside a region and broke the flight
from its thirty eighth frame.

$04D83 is not one of those clusters and could not be. It is a nine instruction
subroutine with no bank push of its own, called three times a frame from inside
the flight model's block and inheriting its bank, so nothing that starts from a
push reaches it. One `sbc $8000` sits in it, and it went unreplaced from the first
build until 2026-09-04: the read never happened, so every read after it in the
same answer was one word early.
`patch.retail.test.py` re-derives them and fails if the byte scan below and a
disassembler that tracks the register widths disagree on so much as one access.
"""

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
"""Which thunk each access to the data port takes, by the opcode standing there.

Counted across the 200 accesses rather than assumed. A `jsr` is three bytes and
so is every one of these instructions, which is the whole reason this works where
a four byte call does not. asm/dsp1-hooks.asm says what each thunk preserves.
"""

STATUS_HOOKS = {
    0xAC: "thunk_ldy_status",
    0xAE: "thunk_ldx_status",
    0x2C: "thunk_bit_status",
}
"""And which one each access to the status register takes.

Separate from the table above because the status answers a constant and the data
port does not, so a read of it needs no fetch at all: the thunk sets the flags the
instruction would have set and leaves the registers alone. `bit` appears only
here, and `patch.retail.test.py` fails if one ever names the data port, because
this would then be answering the wrong question for it.
"""

ACCESS_BYTES = 3
"""The length of one of these instructions, and of the call that replaces it."""

MIRRORED = {
    (0x6D, 0x0130): "thunk_adc_0130",
    (0x8D, 0x0130): "thunk_sta_0130",
    (0xB9, 0x1800): "thunk_lda_1800y",
    (0xB9, 0x1808): "thunk_lda_1808y",
    (0xBD, 0x1810): "thunk_lda_1810x",
    (0xBD, 0x1812): "thunk_lda_1812x",
    (0xBD, 0x1814): "thunk_lda_1814x",
}
"""The accesses inside those runs that are not the part, and the thunk each takes.

Keyed on the opcode and the whole operand rather than on a page, because these
are ordinary memory and there is nothing about the address that marks it. Each
entry is one instruction the flight model uses to reach its own work RAM through
the bank mirror, which the redirect breaks; asm/dsp1-hooks.asm says what each one
carries and what leaving it alone cost.

Every entry is a shape the disassembler in `patch.retail.test.py` confirms is a
real instruction at every offset this matches, which is what keeps a coincidence
in a table of data from being turned into a call.
"""


def hooked(rom: bytes, stubs: Mapping[str, int]) -> tuple[bytes, int]:
    """The image with every access inside HOOKED turned into a call to its thunk.

    Found by the bytes rather than by decoding the region, which is safe here and
    checked: `patch.retail.test.py` disassembles the same run, tracking the
    register widths, and fails unless the two agree on every access and on its
    length. A scan that drifted from the instruction boundaries would replace an
    operand and leave a branch pointing into the middle of a call.
    """
    out = bytearray(rom)
    replaced = 0
    for start, end in HOOKED:
        for at in range(start, min(end, len(rom)) - 2):
            page = out[at + 2]
            if out[at + 1] != 0x00:
                name = MIRRORED.get((out[at], out[at + 1] | page << 8))
            elif page == PORT_PAGE:
                name = HOOKS.get(out[at])
            elif page == STATUS_PAGE:
                name = STATUS_HOOKS.get(out[at])
            else:
                name = MIRRORED.get((out[at], out[at + 1] | page << 8))
            if name is None:
                continue
            target = stubs[name]
            out[at] = JSR
            out[at + 1] = target & 0xFF
            out[at + 2] = target >> 8 & 0xFF
            replaced += 1
    return bytes(out), replaced


def spanned(rom: bytes, stubs: Mapping[str, int]) -> bytes:
    """The image with each named run replaced by a call to its routine."""
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


def redirected(rom: bytes) -> tuple[bytes, int]:
    """The image with every push of the part's bank naming this project's instead."""
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
    stubs = symbols(Path(argv[1]))
    out = applied(rom, where, stubs)
    out = spanned(out, stubs)
    out, replaced = hooked(out, stubs)
    out, moved = redirected(out)
    say(f"{moved} data bank pushes redirected")
    say(f"{replaced} accesses in the flight model replaced one at a time")
    out = declared(out, fast="--fast" in argv)
    out = checksummed(out)
    Path(argv[2]).write_bytes(out)
    for line in report(where):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
