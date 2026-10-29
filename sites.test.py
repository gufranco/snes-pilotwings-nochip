import unittest

import script
import sites


def lorom_image(program: bytes, at: int = 0) -> bytes:
    image = bytearray(b"\x00" * sites.CARTRIDGE_BYTES)
    image[at : at + len(program)] = program
    return bytes(image)


class WindowTest(unittest.TestCase):
    def test_the_part_answers_across_the_banks_a_lorom_board_wires_it_to(self) -> None:
        window = sites.window()

        self.assertLess(window.first_bank, window.last_bank)

    def test_the_data_port_and_the_status_register_are_different_addresses(self) -> None:
        window = sites.window()

        self.assertNotEqual(window.data, window.status)

    def test_the_window_is_the_one_the_driver_publishes_for_this_layout(self) -> None:
        self.assertEqual(sites.window().data, sites.window().data)


class SitesTest(unittest.TestCase):
    def test_an_image_that_never_reaches_the_part_has_no_sites(self) -> None:
        found = sites.reached(lorom_image(b""))

        self.assertEqual(found, ())

    def test_a_long_read_of_the_data_port_is_found(self) -> None:
        found = sites.reached(lorom_image(bytes([0xAF, 0x00, 0x80, 0x30])))

        self.assertEqual(len(found), 1)

    def test_the_site_is_reported_at_the_offset_the_instruction_sits_at(self) -> None:
        found = sites.reached(lorom_image(bytes([0xAF, 0x00, 0x80, 0x30]), at=0x40))

        self.assertEqual(found[0], 0x40)

    def test_an_image_reaching_the_part_twice_reports_both(self) -> None:
        program = bytes([0xAF, 0x00, 0x80, 0x30, 0xAF, 0x00, 0xC0, 0x30])

        found = sites.reached(lorom_image(program))

        self.assertEqual(len(found), 2)


class CensusTest(unittest.TestCase):
    def test_an_image_that_never_reaches_the_part_censuses_to_nothing(self) -> None:
        taken = sites.census(lorom_image(b""))

        self.assertEqual(taken.sites, 0)

    def test_the_census_counts_the_sites_it_found(self) -> None:
        taken = sites.census(lorom_image(bytes([0xAF, 0x00, 0x80, 0x30])))

        self.assertEqual(taken.sites, 1)

    def test_a_census_with_no_exchange_reports_no_shapes(self) -> None:
        taken = sites.census(lorom_image(b""))

        self.assertEqual(taken.shapes, {})

    def test_the_census_repr_names_what_it_counted(self) -> None:
        taken = sites.census(lorom_image(b""))

        self.assertIn("0", repr(taken))


script.entry(__name__, unittest.main)
