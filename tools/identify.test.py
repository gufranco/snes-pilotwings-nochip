import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import identify  # noqa: E402

import dumps  # noqa: E402


class LookTest(unittest.TestCase):
    def test_a_region_with_no_file_here_is_reported_as_absent(self) -> None:
        one = dumps.artifacts()[0]

        found = identify.look(one, root=ROOT / "nowhere")

        self.assertEqual(found.state, identify.STATE_ABSENT)

    def test_an_absent_file_is_not_counted_as_a_failure(self) -> None:
        one = dumps.artifacts()[0]

        found = identify.look(one, root=ROOT / "nowhere")

        self.assertTrue(found.ok)

    def test_a_file_that_is_here_is_read_and_judged(self) -> None:
        one = dumps.artifacts()[0]
        with tempfile.TemporaryDirectory() as made:
            where = Path(made) / "roms"
            where.mkdir()
            (where / one.filename).write_bytes(b"\x00" * 16)

            found = identify.look(one, root=made)

            self.assertNotEqual(found.state, identify.STATE_ABSENT)

    def test_a_file_that_matches_is_reported_as_matching(
        self,
    ) -> None:
        one = dumps.artifacts()[0]
        found = identify.judge(one, b"", digest=one.accepted[0]["sha256"])

        self.assertEqual(found.state, identify.STATE_OK)

    def test_a_file_that_matches_is_well(self) -> None:
        one = dumps.artifacts()[0]

        found = identify.judge(one, b"", digest=one.accepted[0]["sha256"])

        self.assertTrue(found.ok)

    def test_a_file_of_the_wrong_length_is_reported_as_wrong(self) -> None:
        one = dumps.artifacts()[0]

        found = identify.judge(one, b"\x00" * 16)

        self.assertEqual(found.state, identify.STATE_WRONG)

    def test_a_wrong_file_is_not_well(self) -> None:
        one = dumps.artifacts()[0]

        found = identify.judge(one, b"\x00" * 16)

        self.assertFalse(found.ok)

    def test_a_wrong_file_says_which_way_it_is_wrong(self) -> None:
        one = dumps.artifacts()[0]

        found = identify.judge(one, b"\x00" * 16)

        self.assertIn("smaller", found.detail)

    def test_a_file_belonging_to_another_region_is_named_as_that_region(self) -> None:
        first, second = dumps.artifacts()[0], dumps.artifacts()[1]

        found = identify.judge(first, b"", digest=second.accepted[0]["sha256"])

        self.assertIn(second.region, found.detail)

    def test_a_file_belonging_to_another_region_is_not_accepted(self) -> None:
        first, second = dumps.artifacts()[0], dumps.artifacts()[1]

        found = identify.judge(first, b"", digest=second.accepted[0]["sha256"])

        self.assertFalse(found.ok)


class ReprTest(unittest.TestCase):
    def test_a_look_names_the_region_and_what_it_found(self) -> None:
        one = dumps.artifacts()[0]

        said = repr(identify.look(one, root=ROOT / "nowhere"))

        self.assertIn(one.region, said)


class ReportTest(unittest.TestCase):
    def test_the_report_names_every_declared_region(self) -> None:
        said = "\n".join(identify.report(root=ROOT / "nowhere"))

        for one in dumps.artifacts():
            self.assertIn(one.region, said)

    def test_the_report_offers_a_digest_command_for_this_machine(self) -> None:
        said = "\n".join(identify.report(root=ROOT / "nowhere"))

        self.assertIn("sha256", said.lower())

    def test_a_run_with_nothing_present_still_exits_zero(self) -> None:
        said: list[str] = []

        code = identify.main(root=ROOT / "nowhere", say=said.append)

        self.assertEqual(code, 0)

    def test_a_run_prints_something(self) -> None:
        said: list[str] = []

        identify.main(root=ROOT / "nowhere", say=said.append)

        self.assertTrue(said)


if __name__ == "__main__":
    unittest.main()
