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

ROOT = Path(__file__).resolve().parent

ROMS = ROOT / "roms"

WIDE_ACCUMULATOR = False
NARROW_INDEX = True
"""The widths the region runs in, taken from the `sep` before it rather than guessed."""

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


def _decoded(rom: bytes) -> Any:
    """Every instruction in every hooked region, decoded from that region's start.

    Region by region rather than in one pass, because a walk that runs past a
    routine's end decodes the next one at the wrong register widths and reports
    instructions that are not there. That is not a hypothetical: bounds taken
    from such a walk once put 44 bytes of ordinary arithmetic inside a region.
    """
    hardware.install()
    from mos65xx import opcodes65816

    found = []
    for start, end in patch.HOOKED:
        listing = opcodes65816.disassemble(
            rom,
            start,
            start + BANK,
            count=6000,
            m=WIDE_ACCUMULATOR,
            x=NARROW_INDEX,
        )
        found += [one for one in listing if start <= one.offset < end]
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
        for start, end in patch.HOOKED:
            for at in range(start, min(end, len(rom)) - 2):
                if (rom[at], rom[at + 1] | rom[at + 2] << 8) in patch.MIRRORED:
                    found.add(at)
        return found

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

    def test_the_region_holds_the_mirrored_accesses_it_is_said_to(self) -> None:
        self.assertEqual(len(self.mirrored), 8)

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


def _decoded_accesses(rom: bytes) -> dict[int, Any]:
    return {
        one.offset: one
        for one in _decoded(rom)
        if (one.mode == "absolute" and one.operand in (patch.STATUS_FROM, 0x8000))
        or (rom[one.offset], one.operand) in patch.MIRRORED
    }


if __name__ == "__main__":
    unittest.main()
