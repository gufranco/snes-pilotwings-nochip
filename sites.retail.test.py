import unittest
from pathlib import Path

import dumps
import sites

ROOT = Path(__file__).resolve().parent

HELD = {
    one.region: ROOT / "roms" / one.filename
    for one in dumps.artifacts()
    if (ROOT / "roms" / one.filename).is_file()
}


@unittest.skipIf(not HELD, "no cartridge dump on this machine")
class ReachesTheePartTest(unittest.TestCase):
    def test_every_dump_held_is_the_one_it_is_named_for(self) -> None:
        wrong = [
            region
            for region, path in HELD.items()
            if getattr(dumps.identify(path.read_bytes()), "region", None) != region
        ]

        self.assertEqual(wrong, [])

    def test_every_region_reaches_the_part_from_more_than_a_hundred_sites(self) -> None:
        counts = {region: sites.census(path.read_bytes()).sites for region, path in HELD.items()}

        self.assertTrue(all(count > 100 for count in counts.values()), counts)

    def test_the_regions_agree_on_how_many_distinct_exchanges_there_are(self) -> None:
        distinct = {sites.census(path.read_bytes()).distinct for path in HELD.values()}

        self.assertEqual(len(distinct), 1, distinct)

    def test_no_region_reaches_the_part_in_a_way_another_never_does(self) -> None:
        shapes = [set(sites.census(path.read_bytes()).shapes) for path in HELD.values()]
        shared = set.intersection(*shapes)

        self.assertEqual([sorted(one - shared) for one in shapes if one - shared], [])


if __name__ == "__main__":
    unittest.main()
