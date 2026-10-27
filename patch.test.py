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
    "dsp_route_02": 0x0F8700,
    "dsp_route_0a": 0x0F8800,
    "dsp_horizon": 0x0F8B00,
    "thunk_sta": 0x00AD28,
    "thunk_lda": 0x00AD2D,
    "thunk_sty": 0x00AD32,
    "thunk_stx": 0x00AD37,
    "thunk_stz": 0x00AD3C,
    "thunk_ldy": 0x00AD41,
    "thunk_ldx": 0x00AD46,
    "thunk_ldy_status": 0x00AD4B,
    "thunk_adc": 0x00AD50,
    "thunk_bit_status": 0x00AD55,
    "thunk_ldx_status": 0x00AD5A,
    "dsp_read_adc": 0x0F8900,
    "dsp_read_eor": 0x0F8A00,
    "thunk_sbc": 0x00AD5F,
    "thunk_adc_0130": 0x00AD64,
    "thunk_sta_0130": 0x00AD69,
    "thunk_lda_1800y": 0x00AD6E,
    "thunk_lda_1808y": 0x00AD73,
    "thunk_lda_1810x": 0x00AD78,
    "thunk_lda_1812x": 0x00AD7D,
    "thunk_lda_1814x": 0x00AD82,
    "thunk_lda_1aea": 0x00AD87,
    "thunk_lda_1848": 0x00AD8C,
    "thunk_lda_185a": 0x00AD91,
    "thunk_lda_1858": 0x00AD96,
    "thunk_lda_1828": 0x00AD9B,
    "thunk_lda_182a": 0x00ADA0,
    "thunk_lda_182c": 0x00ADA5,
    "thunk_lda_182e": 0x00ADAA,
    "thunk_cmp_182c": 0x00ADAF,
    "thunk_cmp_182e": 0x00ADB4,
    "thunk_lda_1ac3": 0x00ADB9,
    "thunk_lda_1870": 0x00ADBE,
    "thunk_lda_1876": 0x00ADC3,
    "thunk_lda_1820x": 0x00ADC8,
    "thunk_lda_1828x": 0x00ADCD,
    "thunk_lda_1840x": 0x00ADD2,
    "thunk_lda_1860x": 0x00ADD7,
    "thunk_ldx_1af9": 0x00ADDC,
    "raster_rearm": 0x00ADE1,
    "raster_arm_wait": 0x00ADE6,
    "raster_nmi": 0x00ADEB,
}


def _image(instructions: bytes = b"") -> bytes:
    out = bytearray(0x10000)
    out[: len(instructions)] = instructions
    return bytes(out)


def _cartridge(instructions: bytes = b"") -> bytes:
    out = bytearray(sites.CARTRIDGE_BYTES)
    out[0x8000 : 0x8000 + len(instructions)] = instructions
    out[0x7FD5] = 0x20
    out[0x7FD7] = 0x09
    out[patch.NMI_VECTOR] = patch.NMI_HANDLER & 0xFF
    out[patch.NMI_VECTOR + 1] = patch.NMI_HANDLER >> 8
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


class HeldTest(unittest.TestCase):
    def test_the_entry_every_caller_passes_through_points_at_the_gap(self) -> None:
        rom = _image()

        out = patch.held(rom, STUBS)

        at = patch.ARM_JUMP
        self.assertEqual(out[at + 1] | out[at + 2] << 8, 0x8000 + (patch.ARM_GAP & 0x7FFF))

    def test_the_gap_holds_a_long_jump_to_the_wait(self) -> None:
        rom = _image()

        out = patch.held(rom, STUBS)

        at = patch.ARM_GAP
        self.assertEqual(out[at], patch.JML)
        self.assertEqual(
            out[at + 1] | out[at + 2] << 8 | out[at + 3] << 16, STUBS["raster_arm_wait"]
        )

    def test_it_refuses_a_gap_that_holds_something(self) -> None:
        rom = bytearray(_image())
        rom[patch.ARM_GAP + 2] = 0x60

        with self.assertRaises(patch.ArmGapTaken):
            patch.held(bytes(rom), STUBS)


class NmiHookTest(unittest.TestCase):
    def test_the_vector_points_at_this_project(self) -> None:
        rom = bytearray(_image())
        rom[patch.NMI_VECTOR] = patch.NMI_HANDLER & 0xFF
        rom[patch.NMI_VECTOR + 1] = patch.NMI_HANDLER >> 8

        out = patch.hooked_nmi(bytes(rom), STUBS)

        at = patch.NMI_VECTOR
        self.assertEqual(out[at] | out[at + 1] << 8, STUBS["raster_nmi"] & 0xFFFF)

    def test_it_refuses_a_vector_that_names_something_else(self) -> None:
        rom = bytearray(_image())
        rom[patch.NMI_VECTOR] = 0x34
        rom[patch.NMI_VECTOR + 1] = 0x12

        with self.assertRaises(patch.VectorMoved):
            patch.hooked_nmi(bytes(rom), STUBS)


class RearmTest(unittest.TestCase):
    def test_the_third_handler_points_at_the_rearm(self) -> None:
        rom = _image()

        out = patch.rearmed(rom, STUBS)

        at = patch.RASTER_THIRD
        self.assertEqual(out[at] | out[at + 1] << 8, STUBS["raster_rearm"] & 0xFFFF)

    def test_the_first_two_handlers_are_left_alone(self) -> None:
        rom = bytearray(_image())
        rom[patch.RASTER_THIRD - 4 : patch.RASTER_THIRD] = b"\x95\xf1\xad\xf1"

        out = patch.rearmed(bytes(rom), STUBS)

        self.assertEqual(out[patch.RASTER_THIRD - 4 : patch.RASTER_THIRD], b"\x95\xf1\xad\xf1")

    def test_it_changes_two_bytes_and_no_others(self) -> None:
        rom = _image()

        out = patch.rearmed(rom, STUBS)

        self.assertEqual(sum(1 for one, two in zip(rom, out, strict=True) if one != two), 2)


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
        starts = {start for start, _, _ in patch.SPANS}
        end = next(stop for _, stop, _ in patch.SPANS if stop not in starts)
        rom[end] = 0xAB

        out = patch.spanned(bytes(rom), STUBS)

        self.assertEqual(out[end], 0xAB)


class CombiningTest(unittest.TestCase):
    def _image(self, opcode: int, page: int = 0x80, bank: int = 0x3F) -> bytes:
        out = bytearray(0x10000)
        out[0x100:0x104] = bytes([opcode, 0x00, page, bank])
        return bytes(out)

    def test_a_long_add_from_the_port_is_a_site(self) -> None:
        self.assertEqual(patch.combining(self._image(0x6F)), {0x100: "dsp_read_adc"})

    def test_a_long_exclusive_or_from_the_port_is_a_site(self) -> None:
        self.assertEqual(patch.combining(self._image(0x4F)), {0x100: "dsp_read_eor"})

    def test_a_long_store_is_left_to_the_driver_model(self) -> None:
        self.assertEqual(patch.combining(self._image(0x8F)), {})

    def test_a_bank_outside_the_window_is_not_a_site(self) -> None:
        self.assertEqual(patch.combining(self._image(0x6F, bank=0x2F)), {})

    def test_an_address_below_the_port_is_not_a_site(self) -> None:
        self.assertEqual(patch.combining(self._image(0x6F, page=0x70)), {})

    def test_it_stops_where_the_game_does(self) -> None:
        self.assertEqual(patch.combining(self._image(0x6F), limit=0x80), {})

    def test_the_plan_carries_them_with_the_rest(self) -> None:
        rom = bytearray(sites.CARTRIDGE_BYTES)
        rom[0x8000:0x8004] = bytes([patch.STA_LONG, 0x00, 0x80, 0x3F])
        rom[0x8004:0x8008] = bytes([0x6F, 0x00, 0x80, 0x3F])
        rom[0x7FD5] = 0x20

        where = patch.plan(bytes(rom))

        self.assertEqual(where.get(0x8004), "dsp_read_adc")


class BuildTest(unittest.TestCase):
    def test_it_writes_a_patched_image(self) -> None:
        into = ROOT / "build" / "patch-test"
        into.mkdir(parents=True, exist_ok=True)
        (into / "one.sfc").write_bytes(_cartridge(bytes([patch.STA_LONG, 0x00, 0x80, 0x3F])))
        (into / "symbols.txt").write_text(
            "dsp_write 0F8100\ndsp_read 0F8200\ndsp_status 0F8300\n"
            "dsp_ignore 0F8400\ndsp_stream 0F8500\ndsp_route_10 0F8600\n"
            "dsp_route_02 0F8700\ndsp_route_0a 0F8800\n"
            "thunk_sta 00AD28\nthunk_lda 00AD2D\nthunk_sty 00AD32\n"
            "thunk_stx 00AD37\nthunk_stz 00AD3C\nthunk_ldy 00AD41\n"
            "thunk_ldx 00AD46\nthunk_ldy_status 00AD4B\nthunk_adc 00AD50\n"
            "thunk_bit_status 00AD55\nthunk_ldx_status 00AD5A\n"
            "dsp_read_adc 0F8900\ndsp_read_eor 0F8A00\n"
            "dsp_horizon 0F8B00\nthunk_sbc 00AD5F\n"
            "thunk_adc_0130 00AD64\nthunk_sta_0130 00AD69\n"
            "thunk_lda_1800y 00AD6E\nthunk_lda_1808y 00AD73\n"
            "thunk_lda_1810x 00AD78\nthunk_lda_1812x 00AD7D\n"
            "thunk_lda_1814x 00AD82\n"
            "thunk_lda_1aea 00AD87\nthunk_lda_1848 00AD8C\n"
            "thunk_lda_185a 00AD91\nthunk_lda_1858 00AD96\n"
            "thunk_lda_1828 00AD9B\nthunk_lda_182a 00ADA0\n"
            "thunk_lda_182c 00ADA5\nthunk_lda_182e 00ADAA\n"
            "thunk_cmp_182c 00ADAF\nthunk_cmp_182e 00ADB4\n"
            "thunk_lda_1ac3 00ADB9\nthunk_lda_1870 00ADBE\n"
            "thunk_lda_1876 00ADC3\nthunk_lda_1820x 00ADC8\n"
            "thunk_lda_1828x 00ADCD\nthunk_lda_1840x 00ADD2\n"
            "thunk_lda_1860x 00ADD7\nthunk_ldx_1af9 00ADDC\n"
            "raster_rearm 00ADE1\nraster_arm_wait 00ADE6\n"
            "raster_nmi 00ADEB\n"
        )

        code = patch.main(
            (
                str(into / "one.sfc"),
                str(into / "symbols.txt"),
                str(into / "out.sfc"),
                str(sites.CARTRIDGE_BYTES),
                "--slow",
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
