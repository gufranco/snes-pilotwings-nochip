import hashlib
import unittest

import dumps


def synthetic(size: int = dumps.CARTRIDGE_BYTES, fill: int = 0x5A) -> bytes:
    return bytes([fill]) * size


class ManifestTest(unittest.TestCase):
    def test_sha256_is_what_decides(self) -> None:
        self.assertEqual(dumps.DECIDES, "sha256")

    def test_all_three_regions_are_declared(self) -> None:
        regions = {one.region for one in dumps.artifacts()}

        self.assertEqual(regions, {"USA", "Japan", "Europe"})

    def test_every_declared_region_carries_a_measured_digest(self) -> None:
        without = [one.region for one in dumps.artifacts() if not one.accepted]

        self.assertEqual(without, [])

    def test_every_accepted_entry_carries_the_whole_ladder(self) -> None:
        for one in dumps.artifacts():
            for entry in one.accepted:
                self.assertEqual(
                    set(entry) & {"size", "crc32", "md5", "sha1", "sha256"},
                    {"size", "crc32", "md5", "sha1", "sha256"},
                )

    def test_every_declared_size_is_the_canonical_one(self) -> None:
        sizes = {entry["size"] for one in dumps.artifacts() for entry in one.accepted}

        self.assertEqual(sizes, {dumps.CARTRIDGE_BYTES})

    def test_no_two_regions_share_a_deciding_digest(self) -> None:
        deciding = [entry["sha256"] for one in dumps.artifacts() for entry in one.accepted]

        self.assertEqual(len(deciding), len(set(deciding)))

    def test_the_microcode_is_declared_through_the_sibling_that_loads_it(self) -> None:
        reached = dumps.through()

        self.assertEqual([one["sibling"] for one in reached], ["snes-dsp-python"])


class IdentifyTest(unittest.TestCase):
    def test_a_declared_dump_is_recognised_by_its_deciding_digest(self) -> None:
        one = dumps.artifacts()[0]

        found = dumps.identify_digest(one.accepted[0]["sha256"])

        self.assertEqual(getattr(found, "region", None), one.region)

    def test_a_digest_nothing_declares_is_not_recognised(self) -> None:
        self.assertIsNone(dumps.identify_digest("00" * 32))

    def test_a_file_of_the_right_bytes_is_identified(self) -> None:
        one = dumps.artifacts()[0]
        data = synthetic()

        found = dumps.identify(data, digest=one.accepted[0]["sha256"])

        self.assertEqual(getattr(found, "region", None), one.region)


class DiagnoseTest(unittest.TestCase):
    def test_a_copier_header_is_named_rather_than_reported_as_wrong_bytes(self) -> None:
        padded = bytes(dumps.COPIER_BYTES) + synthetic()

        said = dumps.diagnose(padded)

        self.assertEqual(said.kind, "copier-header")

    def test_the_copier_diagnosis_says_how_to_repair_it(self) -> None:
        padded = bytes(dumps.COPIER_BYTES) + synthetic()

        said = dumps.diagnose(padded)

        self.assertIn("strip", said.repair)

    def test_a_file_of_the_wrong_length_says_which_way_it_is_wrong(self) -> None:
        said = dumps.diagnose(synthetic(dumps.CARTRIDGE_BYTES // 2))

        self.assertEqual(said.kind, "wrong-size")

    def test_a_short_file_says_it_is_short(self) -> None:
        said = dumps.diagnose(synthetic(dumps.CARTRIDGE_BYTES // 2))

        self.assertIn("smaller", said.detail)

    def test_a_long_file_says_it_is_long(self) -> None:
        said = dumps.diagnose(synthetic(dumps.CARTRIDGE_BYTES * 2))

        self.assertIn("larger", said.detail)

    def test_a_file_of_the_right_length_that_matches_nothing_says_so(self) -> None:
        said = dumps.diagnose(synthetic())

        self.assertEqual(said.kind, "unrecognised")

    def test_an_unrecognised_file_prints_the_digest_it_computed(self) -> None:
        data = synthetic()

        said = dumps.diagnose(data)

        self.assertIn(hashlib.sha256(data).hexdigest(), said.detail)

    def test_a_declared_dump_is_diagnosed_as_matching(self) -> None:
        one = dumps.artifacts()[0]

        said = dumps.diagnose(synthetic(), digest=one.accepted[0]["sha256"])

        self.assertEqual(said.kind, "match")

    def test_the_match_names_the_region_it_found(self) -> None:
        one = dumps.artifacts()[0]

        said = dumps.diagnose(synthetic(), digest=one.accepted[0]["sha256"])

        self.assertIn(one.region, said.detail)

    def test_a_cartridge_the_manifest_warns_against_is_named(self) -> None:
        self.assertTrue(any("Campus Challenge" in one["name"] for one in dumps.not_this()))


class ReprTest(unittest.TestCase):
    def test_an_artifact_names_its_region(self) -> None:
        self.assertIn("USA", repr(dumps.artifacts()[0]))

    def test_a_finding_names_its_kind(self) -> None:
        self.assertIn("wrong-size", repr(dumps.diagnose(b"short")))


class CommandTest(unittest.TestCase):
    def test_a_digest_command_is_offered_for_every_operating_system(self) -> None:
        offered = dumps.digest_commands("somefile.sfc")

        self.assertEqual(set(offered), {"macOS", "Linux", "Windows"})

    def test_every_digest_command_names_the_file_it_is_given(self) -> None:
        offered = dumps.digest_commands("somefile.sfc")

        self.assertTrue(all("somefile.sfc" in one for one in offered.values()))


if __name__ == "__main__":
    unittest.main()
