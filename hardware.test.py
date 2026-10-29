import os
import sys
import unittest
from pathlib import Path

import hardware
import script

ROOT = Path(__file__).resolve().parent


class PackagesTest(unittest.TestCase):
    def test_every_named_package_has_a_directory_at_the_root(self) -> None:
        missing = [name for name in hardware.PACKAGES if not hardware.root_of(name).is_dir()]

        self.assertEqual(missing, [])

    def test_every_directory_is_a_submodule_this_repository_declares(self) -> None:
        declared = (ROOT / ".gitmodules").read_text()

        for directory in hardware.PACKAGES.values():
            self.assertIn(f"path = {directory}", declared)

    def test_a_nested_package_resolves_inside_its_parent(self) -> None:
        for package, (parent, directory) in hardware.INSIDE.items():
            self.assertEqual(
                hardware.root_of(package), hardware.root_of(parent) / directory, package
            )

    def test_a_nested_package_is_not_a_submodule_this_repository_declares(self) -> None:
        declared = (ROOT / ".gitmodules").read_text()

        for package, (_, directory) in hardware.INSIDE.items():
            self.assertNotIn(f"path = {directory}", declared, package)

    def test_a_package_this_project_does_not_carry_is_refused_by_name(self) -> None:
        with self.assertRaises(hardware.UnknownPackage) as raised:
            hardware.root_of("snesgfx")

        self.assertIn("snesgfx", str(raised.exception))

    def test_the_refusal_lists_what_is_carried(self) -> None:
        with self.assertRaises(hardware.UnknownPackage) as raised:
            hardware.root_of("nothing")

        for name in hardware.PACKAGES:
            self.assertIn(name, str(raised.exception))


class FirmwareTest(unittest.TestCase):
    def test_this_project_directory_goes_in_front_of_what_was_already_named(self) -> None:
        environment = {hardware.FIRMWARE_VARIABLE: "/somewhere/else"}

        named = hardware.name_firmware(environment)

        self.assertEqual(named.split(os.pathsep)[0], str(hardware.FIRMWARE))

    def test_a_directory_somebody_already_named_is_kept(self) -> None:
        environment = {hardware.FIRMWARE_VARIABLE: "/somewhere/else"}

        named = hardware.name_firmware(environment)

        self.assertIn("/somewhere/else", named.split(os.pathsep))

    def test_naming_it_twice_does_not_repeat_it(self) -> None:
        environment: dict[str, str] = {}

        hardware.name_firmware(environment)
        named = hardware.name_firmware(environment)

        self.assertEqual(named.count(str(hardware.FIRMWARE)), 1)

    def test_an_empty_environment_is_given_just_this_directory(self) -> None:
        environment: dict[str, str] = {}

        named = hardware.name_firmware(environment)

        self.assertEqual(named, str(hardware.FIRMWARE))


class LoadTest(unittest.TestCase):
    def test_a_model_is_returned_by_the_name_it_is_published_under(self) -> None:
        loaded = hardware.load("mapper")

        self.assertTrue(hasattr(loaded, "MODELS"))

    def test_installing_puts_every_model_on_the_import_path(self) -> None:
        hardware.install()

        for name in hardware.PACKAGES:
            self.assertIn(str(hardware.root_of(name)), sys.path)

    def test_loading_a_package_this_project_does_not_carry_is_refused(self) -> None:
        with self.assertRaises(hardware.UnknownPackage):
            hardware.load("nothing")


script.entry(__name__, unittest.main)
