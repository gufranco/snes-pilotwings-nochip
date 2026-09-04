"""What `patch.py` finds by its bytes, against what a disassembler finds.

`hooked` replaces every access to the part inside one run of the game's own code,
and it finds them by matching three bytes rather than by decoding the run. That
is only safe while the two agree, and a scan that drifted from the instruction
boundaries would replace an operand and leave a branch pointing into the middle
of a call, which is a fault no test of the scan against itself could see.

So the scan is checked against a disassembler that tracks the register widths,
on the dumps this project reads. Kept apart from the rest because it needs one of
those dumps, and skipped out loud on a machine without them.
"""

import unittest
from pathlib import Path
from typing import Any, override

import dumps
import hardware
import patch
import sites

ROOT = Path(__file__).resolve().parent

ROMS = ROOT / "roms"

WIDE_ACCUMULATOR = False
NARROW_INDEX = True
"""The widths most blocks run in, and the default for a region with no block in it."""

WIDTHS = {
    0x0004E: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x00071: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x01601: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x04AA4: (True, NARROW_INDEX),
    0x04B13: (True, NARROW_INDEX),
    0x04B4A: (WIDE_ACCUMULATOR, False),
    0x04DB3: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x0503F: (True, NARROW_INDEX),
    0x051F1: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x05447: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x05507: (WIDE_ACCUMULATOR, NARROW_INDEX),
    0x055D8: (WIDE_ACCUMULATOR, NARROW_INDEX),
}
"""What each block's accumulator and index widths are on entry, eight bits when true.

Taken from the `sep` or `rep` that precedes each push rather than assumed, and one
per block rather than one for the file. Assuming one cost a whole audit: read
sixteen bits wide, $00:D04A spells `lda $1aea` followed by a three byte compare, a
`tcs`, and an `sbc $30c2,y` naming the console's own register space. $00:D031 is
`sep #$30`, so that block is eight bits wide, where the same bytes spell `lda
$1aea`, `cmp #$0a` and a branch. The walk re-synchronises four instructions later
at the port access after them, which is why the port scan cannot tell the two
readings apart and why these are stated here.

`test_the_widths_are_what_the_port_scan_agrees_with` is what holds them honest: a
wrong pair moves an access or invents one, and the byte scan then disagrees.
"""

HELPERS = {0x04D83: (False, True)}
"""Subroutines called from inside a block, which inherit its bank and have no push.

One of them, $00:CD83, nine instructions called three times a frame from the flight
model. Nothing that starts from a push finds it, which is how the `sbc $8000` in it
went unreplaced from the first build.
"""

BANK = 0x8000
"""What one bank holds, so a file offset can be read as an address inside it."""

SETS_THE_FLAGS = (
    "lda",
    "ldx",
    "ldy",
    "adc",
    "sbc",
    "and",
    "ora",
    "eor",
    "cmp",
    "cpx",
    "cpy",
    "bit",
    "inc",
    "dec",
    "inx",
    "dex",
    "iny",
    "dey",
    "asl",
    "lsr",
    "rol",
    "ror",
    "tax",
    "tay",
    "txa",
    "tya",
    "pla",
    "plx",
    "ply",
    "plp",
    "trb",
    "tsb",
    "sep",
    "rep",
)
"""Every instruction in this region that writes negative or zero."""

READS_THE_FLAGS = ("bpl", "bmi", "beq", "bne")
"""And every one that branches on them."""


def _rom() -> bytes | None:
    """The American dump, which is the one the offsets in `patch.HOOKED` name.

    Identified by its digest rather than by its filename, because the region a
    scan is checked against is a property of one image and not of whatever a file
    happens to be called.
    """
    for name in sorted(ROMS.glob("*.sfc")):
        raw = name.read_bytes()
        found = dumps.identify(raw)
        if found is not None and "usa" in found.name.lower():
            return raw
    return None


STOPS = ("plb", "rts", "rtl", "rti", "jmp", "jml", "bra", "brl")
"""What ends a path. A `jmp` or a `bra` ends this one and opens another."""

REACH = 0x400
"""How far past its start any one block can run. Every one of them is far shorter."""


def _walk(rom: bytes, start: int, m: bool, x: bool, bound: int) -> Any:
    """Every instruction reachable from one entry, following the branches.

    Block by block rather than in one pass, because a walk that runs past a
    routine's end decodes the next one at the wrong register widths and reports
    instructions that are not there. That is not a hypothetical: bounds taken from
    such a walk once put 44 bytes of ordinary arithmetic inside a region.

    Following the branches rather than falling through, because a block can have
    more than one arm and the arms are not laid out in order. $00:D03F has two: the
    one a linear walk sees ends at $00:D068, and the other begins at $00:D06C, runs
    to $00:D0AA, and holds three accesses to the game's own memory.
    """
    hardware.install()
    from mos65xx import opcodes65816

    seen: dict[int, Any] = {}
    todo = [(start, m, x)]
    while todo:
        at, cm, cx = todo.pop()
        if at in seen or not bound <= at < bound + REACH:
            continue
        for one in opcodes65816.disassemble(rom, at, at + REACH, count=REACH, m=cm, x=cx):
            if one.offset in seen:
                break
            seen[one.offset] = one
            if one.mnemonic in ("sep", "rep"):
                eight = one.mnemonic == "sep"
                if one.operand & 0x20:
                    cm = eight
                if one.operand & 0x10:
                    cx = eight
            if one.mode == "relative":
                step = one.operand - 0x100 if one.operand > 0x7F else one.operand
                todo.append((one.offset + one.size + step, cm, cx))
            elif one.mnemonic in ("jmp", "bra") and one.mode in ("absolute", "relative"):
                if one.mode == "absolute":
                    todo.append((one.operand - BANK, cm, cx))
                break
            if one.mnemonic in STOPS:
                break
    return [seen[at] for at in sorted(seen)]


def _block(rom: bytes, site: int) -> Any:
    m, x = WIDTHS[site]
    return _walk(rom, site + 4, m, x, site)


def _decoded(rom: bytes) -> Any:
    """Every instruction the redirect covers: the twelve blocks and the one helper."""
    found: list[Any] = []
    for site in sorted(WIDTHS):
        found += _block(rom, site)
    for start, (m, x) in sorted(HELPERS.items()):
        found += _walk(rom, start, m, x, start)
    return found


class Accesses(unittest.TestCase):
    @override
    def setUp(self) -> None:
        rom = _rom()
        if rom is None:
            self.skipTest("no cartridge dump in roms/, so there is nothing to disassemble")
        self.rom = rom
        self.listing = _decoded(rom)
        self.real = {
            one.offset: one
            for one in self.listing
            if one.mode == "absolute" and one.operand in (patch.STATUS_FROM, 0x8000)
        }
        self.mirrored = {
            one.offset: one
            for one in self.listing
            if (rom[one.offset], one.operand) in patch.MIRRORED
        }
        self.scanned = self._scanned(rom)

    def _scanned(self, rom: bytes) -> set[int]:
        found = set()
        for start, end in patch.HOOKED:
            for at in range(start, min(end, len(rom)) - 2):
                if rom[at + 1] != 0x00:
                    continue
                port = rom[at + 2] == patch.PORT_PAGE and rom[at] in patch.HOOKS
                status = rom[at + 2] == patch.STATUS_PAGE and rom[at] in patch.STATUS_HOOKS
                if port or status:
                    found.add(at)
        return found

    def _mirrors(self, rom: bytes) -> set[int]:
        found = set()
        for start, end in patch.WINDOWED:
            for at in range(start, min(end, len(rom)) - 2):
                if (rom[at], rom[at + 1] | rom[at + 2] << 8) in patch.MIRRORED:
                    found.add(at)
        return found

    def test_the_widths_are_what_the_port_scan_agrees_with(self) -> None:
        """What pins each block's widths, since the table above cannot pin itself.

        A wrong pair drifts the walk, which moves an access or invents one, and the
        byte scan for the port disagrees. The port's operands are the check because
        no ordinary instruction in these blocks carries $8000 or $C000.
        """
        for site in sorted(WIDTHS):
            listing = _block(self.rom, site)
            end = max(one.offset for one in listing)
            walked = {
                one.offset
                for one in listing
                if one.mode == "absolute" and one.operand in (0x8000, patch.STATUS_FROM)
            }
            scanned = set()
            for at in range(site + 4, end + 1):
                if self.rom[at + 1] != 0x00:
                    continue
                page = self.rom[at + 2]
                port = page == patch.PORT_PAGE and self.rom[at] in patch.HOOKS
                status = page == patch.STATUS_PAGE and self.rom[at] in patch.STATUS_HOOKS
                if port or status:
                    scanned.add(at)
            self.assertEqual(walked, scanned, f"{site + BANK:#06x}")

    def test_every_block_ends_on_the_pull_that_closes_it(self) -> None:
        for site in sorted(WIDTHS):
            last = _block(self.rom, site)[-1]
            self.assertIn(last.mnemonic, ("plb", "rts"), f"{site + BANK:#06x}")

    def test_every_block_the_image_holds_is_in_the_table(self) -> None:
        want = bytes([patch.PEA, patch.LAST_BANK, 0x00])
        found, at = set(), 0
        while True:
            at = self.rom.find(want, at)
            if at < 0 or at >= sites.CARTRIDGE_BYTES:
                break
            found.add(at)
            at += 3
        self.assertEqual(found, set(WIDTHS))

    def test_the_blocks_are_the_bounds_the_mirrored_scan_uses(self) -> None:
        walked = set()
        for site in WIDTHS:
            listing = _block(self.rom, site)
            last = max(listing, key=lambda one: one.offset)
            walked.add((site, last.offset + last.size))
        self.assertEqual(walked, set(patch.WINDOWED))

    def test_every_mirrored_access_the_scan_finds_is_a_real_instruction(self) -> None:
        """The one place a byte scan could turn data into a call.

        A port access is recognised by an operand of $8000 or $C000, which the
        game's own data almost never spells. A mirrored access is recognised by an
        ordinary work RAM address, which it might, so every offset the scan matches
        has to be an instruction boundary the disassembler agrees with.
        """
        self.assertEqual(self._mirrors(self.rom) - set(self.mirrored), set())

    def test_the_scan_finds_every_mirrored_access_the_disassembler_does(self) -> None:
        self.assertEqual(set(self.mirrored) - self._mirrors(self.rom), set())

    def test_every_mirrored_access_is_as_long_as_the_call_that_replaces_it(self) -> None:
        for one in self.mirrored.values():
            self.assertEqual(one.size, patch.ACCESS_BYTES, f"{one.address:#06x}")

    def test_the_blocks_hold_the_mirrored_accesses_they_are_said_to(self) -> None:
        self.assertEqual(len(self.mirrored), 31)

    def test_the_scan_finds_every_access_the_disassembler_does(self) -> None:
        self.assertEqual(set(self.real) - self.scanned, set())

    def test_the_scan_finds_nothing_the_disassembler_does_not(self) -> None:
        self.assertEqual(self.scanned - set(self.real), set())

    def test_the_region_holds_the_accesses_it_is_said_to(self) -> None:
        self.assertGreater(len(self.real), 100)

    def test_every_access_is_as_long_as_the_call_that_replaces_it(self) -> None:
        for one in self.real.values():
            self.assertEqual(one.size, patch.ACCESS_BYTES, f"{one.address:#06x}")

    def test_nothing_branches_into_the_middle_of_an_access(self) -> None:
        inside: set[int] = set()
        for at in self.real:
            inside |= set(range(at + 1, at + patch.ACCESS_BYTES))

        landing = set()
        for one in self.listing:
            if one.mode == "relative":
                step = one.operand - 0x100 if one.operand > 0x7F else one.operand
                landing.add(one.offset + one.size + step)
            elif one.mnemonic in ("jmp", "jsr") and one.mode == "absolute":
                landing.add(one.operand - BANK)

        self.assertEqual(landing & inside, set())

    def test_nothing_reads_the_flags_the_index_loads_do_not_set(self) -> None:
        """The one place the hooks answer differently from the instruction they replace.

        `ldx $8000` and `ldy $8000` have no long addressing mode, so their hooks
        move the value through the stack and restore the caller's flags after,
        which leaves negative and zero as the caller had them rather than set from
        what was loaded. That is safe only while nothing reads them, so this walks
        forward from each one to the next instruction that writes those flags and
        fails if a branch on them comes first.
        """
        writes = set(SETS_THE_FLAGS)
        reads = set(READS_THE_FLAGS)

        for at, one in enumerate(self.listing):
            if one.mnemonic not in ("ldx", "ldy"):
                continue
            if one.mode != "absolute" or one.operand != 0x8000:
                continue
            for step in self.listing[at + 1 :]:
                self.assertNotIn(step.mnemonic, reads, f"{one.address:#06x} has its flags read")
                if step.mnemonic in writes:
                    break

    def test_every_shape_the_region_holds_has_a_thunk_named_for_it(self) -> None:
        for one in self.real.values():
            table = patch.HOOKS if one.operand == 0x8000 else patch.STATUS_HOOKS
            self.assertIn(self.rom[one.offset], table, f"{one.address:#06x}")

    def test_nothing_tests_the_data_port_the_way_only_the_status_is_tested(self) -> None:
        """`bit` reads the status and never the port, which is what lets its hook
        answer a constant instead of taking a word off the answer."""
        for one in self.real.values():
            if one.mnemonic == "bit":
                self.assertEqual(one.operand, patch.STATUS_FROM, f"{one.address:#06x}")


class Replaced(unittest.TestCase):
    @override
    def setUp(self) -> None:
        rom = _rom()
        if rom is None:
            self.skipTest("no cartridge dump in roms/, so there is nothing to replace")
        self.rom = rom
        named = {*patch.HOOKS.values(), *patch.STATUS_HOOKS.values(), *patch.MIRRORED.values()}
        self.stubs = dict.fromkeys(named, 0x00AD28)

    def test_it_replaces_every_access_and_nothing_else(self) -> None:
        out, _ = patch.hooked(self.rom, self.stubs)

        changed = {at for at in range(len(self.rom)) if self.rom[at] != out[at]}
        inside = {at for start, end in patch.HOOKED for at in range(start, end)}
        self.assertEqual(changed - inside, set())

    def test_it_leaves_everything_before_the_first_region_alone(self) -> None:
        out, _ = patch.hooked(self.rom, self.stubs)

        first = patch.HOOKED[0][0]
        self.assertEqual(out[:first], self.rom[:first])

    def test_it_leaves_everything_after_the_last_region_alone(self) -> None:
        out, _ = patch.hooked(self.rom, self.stubs)

        last = patch.HOOKED[-1][1]
        self.assertEqual(out[last:], self.rom[last:])

    def test_the_count_it_reports_is_what_the_disassembler_finds(self) -> None:
        _, replaced = patch.hooked(self.rom, self.stubs)

        self.assertEqual(replaced, len(_decoded_accesses(self.rom)))


class RasterChain(unittest.TestCase):
    """That the handler table is where and what asm/dsp1-raster.asm assumes.

    The rearm reads the same four tables the game's own arming routine reads and
    replaces only the third handler. Every one of those addresses is a constant
    written into this project rather than derived, so each is checked against the
    dump instead of trusted.
    """

    @override
    def setUp(self) -> None:
        rom = _rom()
        if rom is None:
            self.skipTest("no cartridge dump in roms/, so there is no table to read")
        self.rom = rom

    def test_the_table_holds_the_three_handlers_the_chain_runs(self) -> None:
        at = patch.RASTER_THIRD - 4

        got = tuple(self.rom[at + k] | self.rom[at + k + 1] << 8 for k in (0, 2, 4))

        self.assertEqual(got, (0xF195, 0xF1AD, 0xF1DA))

    def test_the_third_handler_is_a_bare_return(self) -> None:
        self.assertEqual(self.rom[0xF1DA - 0x8000], 0x60)

    def test_the_arming_routine_reads_the_tables_the_rearm_reads(self) -> None:
        arming = self.rom[0xF168 - 0x8000 : 0xF194 - 0x8000]

        for opcode, table in ((0xBD, 0xF14D), (0xBD, 0xF150), (0xBC, 0xF153)):
            self.assertIn(bytes((opcode, table & 0xFF, table >> 8)), arming, hex(table))

    def test_the_tail_reads_the_two_scanline_tables_the_rearm_reads(self) -> None:
        tail = self.rom[0xF1B9 - 0x8000 : 0xF1DE - 0x8000]

        for table in (0x18FA, 0x18FD):
            self.assertIn(bytes((0xBC, table & 0xFF, table >> 8)), tail, hex(table))

    def test_the_step_counter_is_where_the_rearm_writes_it(self) -> None:
        dispatch = self.rom[0xF1DE - 0x8000 : 0xF1F6 - 0x8000]

        self.assertIn(bytes((0xAE, 0x80, 0x00)), dispatch)
        self.assertIn(bytes((0x6C, 0x76, 0x00)), self.rom[0xF1DB - 0x8000 : 0xF1DE - 0x8000])


def _decoded_accesses(rom: bytes) -> dict[int, Any]:
    return {
        one.offset: one
        for one in _decoded(rom)
        if (one.mode == "absolute" and one.operand in (patch.STATUS_FROM, 0x8000))
        or (rom[one.offset], one.operand) in patch.MIRRORED
    }


if __name__ == "__main__":
    unittest.main()
