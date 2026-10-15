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

HELPERS = {0x04D83: (False, True)}

BANK = 0x8000

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

READS_THE_FLAGS = ("bpl", "bmi", "beq", "bne")


def _rom() -> bytes | None:
    for name in sorted(ROMS.glob("*.sfc")):
        raw = name.read_bytes()
        found = dumps.identify(raw)
        if found is not None and "usa" in found.name.lower():
            return raw
    return None


STOPS = ("plb", "rts", "rtl", "rti", "jmp", "jml", "bra", "brl")

REACH = 0x400


def _walk(rom: bytes, start: int, m: bool, x: bool, bound: int) -> Any:
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

    def _walked_in_block(self, site: int) -> set[int]:
        return {
            one.offset
            for one in _block(self.rom, site)
            if one.mode == "absolute" and one.operand in (0x8000, patch.STATUS_FROM)
        }

    def _scanned_in_block(self, site: int) -> set[int]:
        end = max(one.offset for one in _block(self.rom, site))
        found = set()
        for at in range(site + 4, end + 1):
            if self.rom[at + 1] != 0x00:
                continue
            page = self.rom[at + 2]
            port = page == patch.PORT_PAGE and self.rom[at] in patch.HOOKS
            status = page == patch.STATUS_PAGE and self.rom[at] in patch.STATUS_HOOKS
            if port or status:
                found.add(at)
        return found

    def test_the_widths_are_what_the_port_scan_agrees_with(self) -> None:
        # Arrange
        sites = sorted(WIDTHS)

        # Act
        disagreeing = [
            f"{site + BANK:#06x}"
            for site in sites
            if self._walked_in_block(site) != self._scanned_in_block(site)
        ]

        # Assert
        self.assertEqual(disagreeing, [])

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
        # Arrange
        decoded = set(self.mirrored)

        # Act
        scanned_only = self._mirrors(self.rom) - decoded

        # Assert
        self.assertEqual(scanned_only, set())

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

    def _flags_read_after(self, at: int) -> bool:
        for step in self.listing[at + 1 :]:
            if step.mnemonic in READS_THE_FLAGS:
                return True
            if step.mnemonic in SETS_THE_FLAGS:
                return False
        return False

    def test_nothing_reads_the_flags_the_index_loads_do_not_set(self) -> None:
        # Arrange
        loads = [
            (at, one)
            for at, one in enumerate(self.listing)
            if one.mnemonic in ("ldx", "ldy") and one.mode == "absolute" and one.operand == 0x8000
        ]

        # Act
        read = [f"{one.address:#06x}" for at, one in loads if self._flags_read_after(at)]

        # Assert
        self.assertEqual(read, [])

    def test_every_shape_the_region_holds_has_a_thunk_named_for_it(self) -> None:
        for one in self.real.values():
            table = patch.HOOKS if one.operand == 0x8000 else patch.STATUS_HOOKS
            self.assertIn(self.rom[one.offset], table, f"{one.address:#06x}")

    def test_nothing_tests_the_data_port_the_way_only_the_status_is_tested(self) -> None:
        # Arrange
        tests = [one for one in self.real.values() if one.mnemonic == "bit"]

        # Act
        elsewhere = [f"{one.address:#06x}" for one in tests if one.operand != patch.STATUS_FROM]

        # Assert
        self.assertEqual(elsewhere, [])


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
