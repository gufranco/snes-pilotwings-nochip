import unittest
from pathlib import Path
from typing import override

import census
import script

ROOT = Path(__file__).resolve().parent

TRACES = sorted((ROOT / "build").glob("trace-*.bin")) if (ROOT / "build").is_dir() else []

BIG = [one for one in TRACES if one.stat().st_size > 1_000_000]


@unittest.skipIf(not BIG, "no recorded run on this machine")
class AgainstARecordingTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.census = census.read(BIG[0])

    def test_a_recording_holds_exchanges(self) -> None:
        self.assertGreater(self.census.total, 1000)

    def test_the_game_uses_far_fewer_commands_than_the_part_accepts(self) -> None:
        self.assertLess(len(self.census.commands), 64)

    def test_every_share_is_a_fraction(self) -> None:
        shares = [self.census.share(one) for one in self.census.commands]

        self.assertTrue(all(0.0 <= one <= 1.0 for one in shares))

    def test_the_shares_add_up(self) -> None:
        total = sum(self.census.share(one) for one in self.census.commands)

        self.assertAlmostEqual(total, 1.0, places=6)

    def test_some_command_asks_for_the_same_arguments_every_time(self) -> None:
        fewest = min(self.census.distinct(one) for one in self.census.commands)

        self.assertEqual(fewest, 1)

    def test_the_whole_observed_set_fits_in_the_image_many_times_over(self) -> None:
        self.assertLess(self.census.table_bytes(), 96 * 1024 * 1024 // 8 // 8)

    def test_the_multiply_is_answered_by_computing_it(self) -> None:
        # Arrange
        script.skip_unless(
            census.MULTIPLY in self.census.commands, "this recording never multiplied"
        )
        seen = self.census.distinct(census.MULTIPLY)

        # Act
        tier = census.tier_of(census.MULTIPLY, seen)

        # Assert
        self.assertEqual(tier, census.COMPUTED)

    def test_the_report_names_every_command_it_counted(self) -> None:
        said = "\n".join(census.report(self.census))

        self.assertTrue(all(f"${one:02X}" in said for one in self.census.commands))


@unittest.skipIf(not BIG, "no recorded run on this machine")
class NotClosedTest(unittest.TestCase):
    def test_the_observed_set_is_a_floor_rather_than_the_answer(self) -> None:
        first = census.read(BIG[0])
        combined = dict(first.seen)
        for other in BIG[1:]:
            for command, counted in census.read(other).seen.items():
                combined.setdefault(command, type(counted)()).update(counted)

        self.assertGreaterEqual(
            sum(len(one) for one in combined.values()),
            sum(len(one) for one in first.seen.values()),
        )


script.entry(__name__, unittest.main)
