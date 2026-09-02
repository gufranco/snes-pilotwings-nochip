import struct
import unittest
from pathlib import Path
from typing import Any, override

import census
import commands
import dumps
import hardware

ROOT = Path(__file__).resolve().parent

IMAGES = [
    (one.filename, (ROOT / "roms" / one.filename).read_bytes())
    for one in dumps.artifacts()
    if (ROOT / "roms" / one.filename).is_file()
]

TRACES = [
    one for one in sorted((ROOT / "build").glob("trace-*.bin")) if one.stat().st_size > 1_000_000
]

CORE = (
    0x00,
    0x01,
    0x02,
    0x03,
    0x04,
    0x06,
    0x08,
    0x0A,
    0x0C,
    0x0D,
    0x0E,
    0x10,
    0x11,
    0x13,
    0x14,
    0x18,
    0x1B,
    0x21,
    0x23,
    0x28,
)
"""The commands every one of the three images is read as issuing.

Europe reads one more, `$80`, which is the byte that leaves the part waiting for
a command rather than computing anything. The other two carry the same loop and
its widths are set further back than a decode reaches, so they go unread there
rather than absent.
"""


@unittest.skipIf(not IMAGES, "no cartridge dump on this machine")
class AgainstTheImagesTest(unittest.TestCase):
    model: Any
    read: dict[str, tuple[commands.Site, ...]]

    @classmethod
    @override
    def setUpClass(cls) -> None:
        """Read the images once for the whole class rather than once per check.

        Reading one is seconds of work, so doing it per check turns a suite that
        runs in half a minute into one nobody waits for.
        """
        cls.model = hardware.load("mos65xx")
        cls.read = {name: commands.read(rom, cls.model.disassemble) for name, rom in IMAGES}

    def test_every_image_reaches_the_part_more_than_the_long_form_alone_shows(self) -> None:
        for name, rom in IMAGES:
            found = commands.stores(rom)
            long_form = [one for one in found if rom[one] == commands.LONG_STORE]

            self.assertGreater(len(found), len(long_form), name)

    def test_every_image_issues_the_same_commands(self) -> None:
        for name, found in self.read.items():
            self.assertTrue(set(CORE).issubset(commands.commands(found)), name)

    def test_a_site_that_issues_a_command_is_eight_bits_wide(self) -> None:
        for name, found in self.read.items():
            for one in found:
                if one.issues:
                    self.assertIs(one.narrow, True, f"{name} ${one.offset:05x}")

    def test_a_sixteen_bit_store_never_issues_a_command(self) -> None:
        for name, found in self.read.items():
            for one in found:
                if one.narrow is False:
                    self.assertIsNone(one.command, f"{name} ${one.offset:05x}")

    def test_the_reading_is_the_same_every_time(self) -> None:
        name, rom = IMAGES[0]
        again = commands.read(rom, self.model.disassemble)

        self.assertEqual(commands.commands(again), commands.commands(self.read[name]))


def executed(path: Path, rom: bytes) -> dict[int, int]:
    """Every command site the recording confirmed, and the byte it wrote there.

    A command byte is the one thing the cartridge writes eight bits at a time, so
    a program counter that only ever touches the low half of the port issued one.
    The counter the recorder keeps points at the byte after the instruction, which
    is what turns it back into an offset in the image.
    """
    low: dict[int, int] = {}
    wide: set[int] = set()
    for _, pbpc, address, is_read, byte in struct.iter_unpack("<IIHBB", path.read_bytes()):
        if is_read or address >= census.STATUS_BOUNDARY:
            continue
        if address == commands.DATA_PORT:
            low[pbpc] = byte
        else:
            wide.add(pbpc)
    found: dict[int, int] = {}
    for pbpc, byte in low.items():
        if pbpc in wide:
            continue
        for size in (3, 4):
            at = ((pbpc >> 16) & 0x7F) * 0x8000 + ((pbpc & 0xFFFF) - size - 0x8000)
            if 0 <= at < len(rom) - 4:
                store = commands.store_at(rom, at)
                if store is not None and store[1] == size:
                    found[at] = byte
                    break
    return found


@unittest.skipIf(not IMAGES or not TRACES, "no recording and dump pair on this machine")
class AgainstARecordingTest(unittest.TestCase):
    ran: dict[int, int]
    read: dict[int, commands.Site]

    @classmethod
    @override
    def setUpClass(cls) -> None:
        region = TRACES[0].stem.split("-")[-1]
        matching = [one for one in IMAGES if region in one[0]]
        if not matching:
            raise unittest.SkipTest(f"no dump for the region {TRACES[0].name} was recorded from")
        rom = matching[0][1]
        cls.ran = executed(TRACES[0], rom)
        if not cls.ran:
            raise unittest.SkipTest(f"{TRACES[0].name} issued no command this can locate")
        disassemble = hardware.load("mos65xx").disassemble
        cls.read = {one.offset: one for one in commands.read(rom, disassemble)}

    def test_the_recording_confirms_command_sites(self) -> None:
        self.assertGreater(len(self.ran), 10)

    def test_every_site_the_recording_ran_was_found_by_the_search(self) -> None:
        missing = sorted(set(self.ran) - set(self.read))

        self.assertEqual(missing, [])

    def test_the_search_never_reads_a_command_the_recording_contradicts(self) -> None:
        wrong = sorted(
            at
            for at, byte in self.ran.items()
            if self.read[at].command is not None and self.read[at].command != byte
        )

        self.assertEqual(wrong, [])

    def test_the_search_reads_most_of_what_the_recording_ran(self) -> None:
        agreed = sum(1 for at, byte in self.ran.items() if self.read[at].command == byte)

        self.assertGreater(agreed * 10, len(self.ran) * 8)

    def test_a_site_the_search_will_not_read_says_why(self) -> None:
        for at in self.ran:
            if self.read[at].command is None:
                self.assertNotEqual(self.read[at].why, "")


if __name__ == "__main__":
    unittest.main()
