import unittest
from pathlib import Path
from typing import override

import tables

ROOT = Path(__file__).resolve().parent

MASKS = {
    one.stem: one.read_bytes()
    for one in sorted((ROOT / "firmware").glob("dsp1*.bin"))
    if one.stat().st_size == tables.IMAGE_BYTES
}


@unittest.skipIf(not MASKS, "no microcode image on this machine")
class AgainstTheMicrocodeTest(unittest.TestCase):
    carried: dict[str, dict[str, int]]

    @classmethod
    @override
    def setUpClass(cls) -> None:
        cls.carried = {name: tables.carried(image) for name, image in MASKS.items()}

    def test_every_mask_carries_every_table_this_expects(self) -> None:
        for name, found in self.carried.items():
            self.assertEqual(set(found), {one.name for one in tables.KNOWN}, name)

    def test_the_reciprocal_sits_in_the_same_place_in_every_mask(self) -> None:
        where = {found[tables.RECIPROCAL] for found in self.carried.values()}

        self.assertEqual(len(where), 1, self.carried)

    def test_the_tables_cost_about_a_kilobyte_rather_than_hundreds(self) -> None:
        self.assertLess(tables.table_bytes(), 2048)

    def test_no_table_needs_a_whole_sixteen_bit_input(self) -> None:
        self.assertTrue(all(one.count <= 256 for one in tables.KNOWN))

    def test_the_report_names_every_table_for_every_mask(self) -> None:
        for name, image in MASKS.items():
            said = "\n".join(tables.report(image))

            self.assertNotIn("not carried", said, name)


@unittest.skipIf(len(MASKS) < 2, "only one mask on this machine, so nothing to compare")
class BetweenTheMasksTest(unittest.TestCase):
    def test_the_masks_do_not_hold_their_tables_in_the_same_places(self) -> None:
        seats = [tuple(sorted(tables.carried(image).items())) for image in MASKS.values()]

        self.assertNotEqual(len(set(seats)), 1)

    def test_they_carry_the_same_tables_all_the_same(self) -> None:
        names = [frozenset(tables.carried(image)) for image in MASKS.values()]

        self.assertEqual(len(set(names)), 1)

    def test_the_data_they_hold_is_the_same_run_at_a_different_seat(self) -> None:
        held = [tables.words(image) for image in MASKS.values()]
        first, second = held[0], held[1]
        table = next(one for one in tables.KNOWN if one.name == tables.SINE)
        at_first = tables.find(first, table)
        at_second = tables.find(second, table)
        assert at_first is not None and at_second is not None

        self.assertEqual(
            first[at_first : at_first + table.count],
            second[at_second : at_second + table.count],
        )


if __name__ == "__main__":
    unittest.main()
