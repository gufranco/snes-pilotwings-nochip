import struct
import unittest
from pathlib import Path

import patch
import sites

ROOT = Path(__file__).resolve().parent

STUBS = {
    "dsp_write": 0x0F8100,
    "dsp_read": 0x0F8200,
    "dsp_status": 0x0F8300,
    "dsp_ignore": 0x0F8400,
    "dsp_stream": 0x0F8500,
    "dsp_route_10": 0x0F8600,
    "route_0e": 0x0F8700,
    "route_02": 0x0F8800,
    "route_00_d03f": 0x0F8900,
    "route_00_d507": 0x0F8A00,
    "route_00_8071": 0x0F8B00,
    "route_00_d447": 0x0F8C00,
}


def _image(instructions: bytes = b"") -> bytes:
    out = bytearray(0x10000)
    out[: len(instructions)] = instructions
    return bytes(out)


def _cartridge(instructions: bytes = b"") -> bytes:
    """A whole image the site scanner will accept, with one site in it."""
    out = bytearray(sites.CARTRIDGE_BYTES)
    out[0x8000 : 0x8000 + len(instructions)] = instructions
    out[0x7FD5] = 0x20
    out[0x7FD7] = 0x09
    return bytes(out)


class ClassifyTest(unittest.TestCase):
    def test_a_store_to_the_data_port_writes(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F]))

        self.assertEqual(patch.classify(rom, 0), "dsp_write")

    def test_a_load_from_the_data_port_reads(self) -> None:
        rom = _image(bytes([patch.LDA_LONG, 0x00, 0x80, 0x3F]))

        self.assertEqual(patch.classify(rom, 0), "dsp_read")

    def test_a_load_from_the_status_register_is_a_status_read(self) -> None:
        rom = _image(bytes([patch.LDA_LONG, 0x00, 0xC0, 0x3F]))

        self.assertEqual(patch.classify(rom, 0), "dsp_status")

    def test_a_store_to_the_status_register_is_ignored(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0xC0, 0x3F]))

        self.assertEqual(patch.classify(rom, 0), "dsp_ignore")

    def test_a_mirror_of_the_data_port_still_reads_as_one(self) -> None:
        rom = _image(bytes([patch.LDA_LONG, 0xEB, 0x8F, 0x3F]))

        self.assertEqual(patch.classify(rom, 0), "dsp_read")

    def test_another_bank_is_not_a_site(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, 0x7E]))

        self.assertIsNone(patch.classify(rom, 0))

    def test_the_first_bank_of_the_window_is_a_site(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, patch.FIRST_BANK]))

        self.assertEqual(patch.classify(rom, 0), "dsp_write")

    def test_a_middle_bank_of_the_window_is_a_site(self) -> None:
        rom = _image(bytes([patch.LDA_LONG, 0x31, 0xD1, 0x39]))

        self.assertEqual(patch.classify(rom, 0), "dsp_status")

    def test_the_bank_below_the_window_is_not(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, patch.FIRST_BANK - 1]))

        self.assertIsNone(patch.classify(rom, 0))

    def test_another_opcode_is_not_a_site(self) -> None:
        rom = _image(bytes([0xEA, 0x00, 0x80, 0x3F]))

        self.assertIsNone(patch.classify(rom, 0))


class AppliedTest(unittest.TestCase):
    def test_the_site_becomes_a_long_call(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F]))

        out = patch.applied(rom, {0: "dsp_write"}, STUBS)

        self.assertEqual(out[0], patch.JSL)

    def test_the_call_names_the_stub(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F]))

        out = patch.applied(rom, {0: "dsp_write"}, STUBS)

        self.assertEqual((out[1], out[2], out[3]), (0x00, 0x81, 0x0F))

    def test_it_takes_exactly_the_bytes_the_instruction_took(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F, 0xEA]))

        out = patch.applied(rom, {0: "dsp_write"}, STUBS)

        self.assertEqual(out[4], 0xEA)

    def test_the_image_keeps_its_length(self) -> None:
        rom = _image(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F]))

        self.assertEqual(len(patch.applied(rom, {0: "dsp_write"}, STUBS)), len(rom))


class HeaderTest(unittest.TestCase):
    def test_the_chipset_stops_claiming_a_coprocessor(self) -> None:
        rom = bytearray(_image())
        rom[patch.HEADER_CHIPSET] = 0x03

        out = patch.declared(bytes(rom), fast=False)

        self.assertEqual(out[patch.HEADER_CHIPSET], patch.CHIPSET_PLAIN)

    def test_the_speed_bit_is_left_alone_by_default(self) -> None:
        rom = bytearray(_image())
        rom[patch.HEADER_SPEED] = 0x20

        out = patch.declared(bytes(rom), fast=False)

        self.assertEqual(out[patch.HEADER_SPEED], 0x20)

    def test_the_speed_bit_is_set_when_asked(self) -> None:
        rom = bytearray(_image())
        rom[patch.HEADER_SPEED] = 0x20

        out = patch.declared(bytes(rom), fast=True)

        self.assertEqual(out[patch.HEADER_SPEED], 0x30)


class ChecksumTest(unittest.TestCase):
    def test_the_two_halves_are_complements(self) -> None:
        out = patch.checksummed(_image(b"\x01\x02\x03"))

        total = struct.unpack_from("<H", out, patch.HEADER_CHECKSUM)[0]
        complement = struct.unpack_from("<H", out, patch.HEADER_COMPLEMENT)[0]
        self.assertEqual(total ^ complement, 0xFFFF)

    def test_it_sums_every_byte(self) -> None:
        base = bytearray(_image(b"\x01\x02\x03"))
        base[patch.HEADER_CHECKSUM : patch.HEADER_CHECKSUM + 2] = b"\x00\x00"
        base[patch.HEADER_COMPLEMENT : patch.HEADER_COMPLEMENT + 2] = b"\xff\xff"

        out = patch.checksummed(_image(b"\x01\x02\x03"))

        total = struct.unpack_from("<H", out, patch.HEADER_CHECKSUM)[0]
        self.assertEqual(total, sum(base) & 0xFFFF)

    def test_running_it_twice_gives_the_same_answer(self) -> None:
        once = patch.checksummed(_image(b"\x01\x02\x03"))

        self.assertEqual(patch.checksummed(once), once)


class PlanTest(unittest.TestCase):
    def test_it_finds_a_site_the_scanner_reports(self) -> None:
        rom = _cartridge(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F]))

        found = patch.plan(rom)

        self.assertEqual(set(found.values()), {"dsp_write"})

    def test_an_image_that_never_reaches_the_part_has_none(self) -> None:
        self.assertEqual(patch.plan(_cartridge()), {})

    def test_a_site_past_where_the_game_ends_is_left_alone(self) -> None:
        rom = _cartridge(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F]))

        self.assertEqual(patch.plan(rom, limit=0x8000), {})

    def test_a_reported_site_this_cannot_replace_is_skipped(self) -> None:
        rom = _cartridge(bytes([0xCF, 0x00, 0x80, 0x3F, patch.STA_LONG, 0x00, 0x80, 0x3F]))

        found = patch.plan(rom, reached=lambda _rom: (0x8000, 0x8004))

        self.assertEqual(list(found.values()), ["dsp_write"])


class SymbolsTest(unittest.TestCase):
    def test_it_reads_a_name_and_an_address(self) -> None:
        into = ROOT / "build" / "patch-test"
        into.mkdir(parents=True, exist_ok=True)
        where = into / "symbols-one.txt"
        where.write_text("dsp_write 0F8100\n\n")

        self.assertEqual(patch.symbols(where), {"dsp_write": 0x0F8100})


class ReportTest(unittest.TestCase):
    def test_it_counts_the_sites(self) -> None:
        lines = patch.report({0: "dsp_write", 4: "dsp_read"})

        self.assertIn("2 sites replaced", lines[0])

    def test_it_names_every_stub(self) -> None:
        lines = patch.report({0: "dsp_write", 4: "dsp_read"})

        self.assertTrue(any("dsp_read" in one for one in lines))


class MainTest(unittest.TestCase):
    def test_with_no_arguments_it_says_so(self) -> None:
        said: list[str] = []

        self.assertEqual(patch.main((), say=said.append), 2)

    def test_with_no_arguments_it_prints_a_usage_line(self) -> None:
        said: list[str] = []

        patch.main((), say=said.append)

        self.assertTrue(said)

    def test_an_image_with_no_sites_is_refused(self) -> None:
        into = ROOT / "build" / "patch-test"
        into.mkdir(parents=True, exist_ok=True)
        (into / "plain.sfc").write_bytes(_image())
        (into / "symbols.txt").write_text("dsp_write 0F8100\n")
        said: list[str] = []

        code = patch.main(
            (
                str(into / "plain.sfc"),
                str(into / "symbols.txt"),
                str(into / "out.sfc"),
                str(sites.CARTRIDGE_BYTES),
            ),
            say=said.append,
        )

        self.assertEqual(code, 1)


class RedirectTest(unittest.TestCase):
    def test_a_push_of_the_part_s_bank_names_this_project_s(self) -> None:
        rom = _image(bytes([patch.PEA, patch.LAST_BANK, 0x00, 0xAB]))

        out, moved = patch.redirected(rom)

        self.assertEqual((out[1], moved), (patch.WINDOW_BANK, 1))

    def test_a_push_of_another_bank_is_left_alone(self) -> None:
        rom = _image(bytes([patch.PEA, 0x7E, 0x00, 0xAB]))

        out, moved = patch.redirected(rom)

        self.assertEqual((out[1], moved), (0x7E, 0))

    def test_every_push_is_moved(self) -> None:
        one = bytes([patch.PEA, patch.LAST_BANK, 0x00])

        _, moved = patch.redirected(_image(one + one + one))

        self.assertEqual(moved, 3)


class SpannedTest(unittest.TestCase):
    def test_the_run_starts_with_a_call(self) -> None:
        out = patch.spanned(_image(), STUBS)

        start = patch.SPANS[0][0]
        self.assertEqual(out[start], patch.JSL)

    def test_the_rest_of_the_run_does_nothing(self) -> None:
        out = patch.spanned(_image(), STUBS)

        start, end, _ = patch.SPANS[0]
        self.assertEqual(set(out[start + patch.SITE_BYTES : end]), {patch.NOP})

    def test_every_run_is_replaced(self) -> None:
        out = patch.spanned(_image(), STUBS)

        self.assertTrue(all(out[start] == patch.JSL for start, _, _ in patch.SPANS))

    def test_the_byte_after_the_run_is_untouched(self) -> None:
        rom = bytearray(_image())
        end = patch.SPANS[0][1]
        rom[end] = 0xAB

        out = patch.spanned(bytes(rom), STUBS)

        self.assertEqual(out[end], 0xAB)


class BuildTest(unittest.TestCase):
    def test_it_writes_a_patched_image(self) -> None:
        into = ROOT / "build" / "patch-test"
        into.mkdir(parents=True, exist_ok=True)
        (into / "one.sfc").write_bytes(_cartridge(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F])))
        (into / "symbols.txt").write_text(
            "dsp_write 0F8100\ndsp_read 0F8200\ndsp_status 0F8300\n"
            "dsp_ignore 0F8400\ndsp_stream 0F8500\ndsp_route_10 0F8600\n"
            "route_0e 0F8700\nroute_02 0F8800\nroute_00_d03f 0F8900\n"
            "route_00_d507 0F8A00\nroute_00_8071 0F8B00\nroute_00_d447 0F8C00\n"
        )

        code = patch.main(
            (
                str(into / "one.sfc"),
                str(into / "symbols.txt"),
                str(into / "out.sfc"),
                str(sites.CARTRIDGE_BYTES),
                "--fast",
            ),
            say=lambda _: None,
        )

        self.assertEqual(code, 0)
        self.assertEqual((into / "out.sfc").read_bytes()[0x8000], patch.JSL)


class FileTest(unittest.TestCase):
    def test_the_module_is_here(self) -> None:
        self.assertTrue((ROOT / "patch.py").exists())


if __name__ == "__main__":
    unittest.main()
