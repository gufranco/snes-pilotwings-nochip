import unittest
from pathlib import Path

import patch

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


class HookedTest(unittest.TestCase):
    def _region(self, body: bytes) -> bytes:
        out = bytearray(0x10000)
        at = patch.HOOKED[0][0]
        out[at : at + len(body)] = body
        return bytes(out)

    def test_a_store_to_the_port_becomes_a_call(self) -> None:
        out, _ = patch.hooked(self._region(bytes([0x8D, 0x00, 0x80])), STUBS)

        at = patch.HOOKED[0][0]
        self.assertEqual(out[at], patch.JSR)
        self.assertEqual(out[at + 1] | out[at + 2] << 8, STUBS["thunk_sta"] & 0xFFFF)

    def test_every_shape_the_region_holds_has_a_thunk(self) -> None:
        for opcode, name in {**patch.HOOKS, **patch.STATUS_HOOKS}.items():
            self.assertIn(name, STUBS, f"{opcode:#04x}")

    def test_a_read_of_the_status_by_bit_takes_its_own_thunk(self) -> None:
        out, _ = patch.hooked(self._region(bytes([0x2C, 0x00, 0xC0])), STUBS)

        at = patch.HOOKED[0][0]
        self.assertEqual(out[at + 1] | out[at + 2] << 8, STUBS["thunk_bit_status"] & 0xFFFF)

    def test_bit_on_the_data_port_is_left_alone(self) -> None:
        out, _ = patch.hooked(self._region(bytes([0x2C, 0x00, 0x80])), STUBS)

        self.assertEqual(out[patch.HOOKED[0][0]], 0x2C)

    def test_every_region_is_searched(self) -> None:
        rom = bytearray(0x60000)
        for start, _ in patch.HOOKED:
            rom[start : start + 3] = bytes([0x8D, 0x00, 0x80])

        _, replaced = patch.hooked(bytes(rom), STUBS)

        self.assertEqual(replaced, len(patch.HOOKED))

    def _windowed(self, body: bytes) -> bytes:
        out = bytearray(0x60000)
        at = patch.WINDOWED[0][0]
        out[at : at + len(body)] = body
        return bytes(out)

    def test_an_access_to_the_games_own_memory_becomes_a_call(self) -> None:
        opcode, operand = next(iter(patch.MIRRORED))
        body = bytes([opcode, operand & 0xFF, operand >> 8])

        out, _ = patch.hooked(self._windowed(body), STUBS)

        at = patch.WINDOWED[0][0]
        self.assertEqual(out[at], patch.JSR)
        self.assertEqual(
            out[at + 1] | out[at + 2] << 8, STUBS[patch.MIRRORED[opcode, operand]] & 0xFFFF
        )

    def test_the_same_access_outside_a_block_is_left_alone(self) -> None:
        # Arrange
        opcode, operand = next(iter(patch.MIRRORED))
        rom = bytearray(0x60000)
        at = max(end for _, end in patch.WINDOWED)
        rom[at : at + 3] = bytes([opcode, operand & 0xFF, operand >> 8])

        # Act
        out, replaced = patch.hooked(bytes(rom), STUBS)

        # Assert
        self.assertEqual(out[at], opcode)
        self.assertEqual(replaced, 0)

    def test_every_shape_the_blocks_hold_has_a_thunk(self) -> None:
        for key, name in patch.MIRRORED.items():
            self.assertIn(name, STUBS, f"{key[0]:#04x} {key[1]:#06x}")

    def test_a_read_of_the_status_takes_its_own_thunk(self) -> None:
        out, _ = patch.hooked(self._region(bytes([0xAC, 0x00, 0xC0])), STUBS)

        at = patch.HOOKED[0][0]
        self.assertEqual(out[at + 1] | out[at + 2] << 8, STUBS["thunk_ldy_status"] & 0xFFFF)

    def test_a_read_of_the_port_and_of_the_status_are_told_apart(self) -> None:
        port, _ = patch.hooked(self._region(bytes([0xAC, 0x00, 0x80])), STUBS)
        status, _ = patch.hooked(self._region(bytes([0xAC, 0x00, 0xC0])), STUBS)

        at = patch.HOOKED[0][0]
        self.assertNotEqual(port[at + 1 : at + 3], status[at + 1 : at + 3])

    def test_an_access_outside_every_region_is_left_alone(self) -> None:
        rom = bytearray(0x60000)
        gap = patch.HOOKED[0][1]
        rom[gap : gap + 3] = bytes([0x8D, 0x00, 0x80])

        out, _ = patch.hooked(bytes(rom), STUBS)

        self.assertEqual(out[gap], 0x8D)

    def test_something_that_is_not_an_access_is_left_alone(self) -> None:
        out, _ = patch.hooked(self._region(bytes([0x8D, 0x01, 0x80])), STUBS)

        self.assertEqual(out[patch.HOOKED[0][0]], 0x8D)

    def test_it_counts_what_it_replaced(self) -> None:
        body = bytes([0x8D, 0x00, 0x80]) * 3

        _, replaced = patch.hooked(self._region(body), STUBS)

        self.assertEqual(replaced, 3)

    def test_it_counts_nothing_when_there_is_nothing_to_replace(self) -> None:
        _, replaced = patch.hooked(self._region(bytes([0xEA, 0xEA, 0xEA])), STUBS)

        self.assertEqual(replaced, 0)


if __name__ == "__main__":
    unittest.main()
