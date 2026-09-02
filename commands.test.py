import unittest

import commands
import hardware

DISASSEMBLE = hardware.load("mos65xx").disassemble


def read(program: bytes) -> tuple[commands.Site, ...]:
    return commands.read(program, DISASSEMBLE)


def instruction(program: bytes) -> object:
    return DISASSEMBLE(program, 0, 0x8000, count=1)[0]


def reaching(program: bytes, at: int = 0) -> commands.Access:
    """The access at that offset, refusing to carry on if there is none."""
    found = commands.access_at(program, at)
    assert found is not None
    return found


def nothing(*_args: object, **_named: object) -> list[object]:
    """A disassembler that decodes nothing, which is what one out of bytes does."""
    return []


IMMEDIATE_LONG = bytes([0xE2, 0x20, 0xA9, 0x06, 0x8F, 0x00, 0x80, 0x3F])
"""sep #$20; lda #$06; sta $3f8000"""

IMMEDIATE_ABSOLUTE = bytes([0xE2, 0x20, 0xA9, 0x11, 0x8D, 0x00, 0x80])
"""sep #$20; lda #$11; sta $8000"""

HELD_IN_Y = bytes([0xE2, 0x30, 0xA0, 0x28, 0xAD, 0x00, 0x80, 0x8C, 0x00, 0x80])
"""sep #$30; ldy #$28; lda $8000; sty $8000"""

ZERO = bytes([0xE2, 0x20, 0x9C, 0x00, 0x80])
"""sep #$20; stz $8000"""

SIXTEEN_BIT = bytes([0xC2, 0x20, 0x8D, 0x00, 0x80])
"""rep #$20; sta $8000"""

VALUE_OUT_OF_REACH = bytes([0xE2, 0x20, 0x8D, 0x00, 0x80])
"""sep #$20; sta $8000, with nothing that loaded the accumulator"""

NOTHING_IN_FRONT = bytes([0x8D, 0x00, 0x80])
"""sta $8000 at the very start, so no origin reaches it"""

DISAGREEING = bytes([0xE2, 0x20, 0xA9, 0xC2, 0x20, 0xEA, 0xEA, 0x9C, 0x00, 0x80])
"""One decode reads sep, lda, jsr; another reads rep, nop, nop. They land
together on the same store and disagree about how wide it is."""

A_MIRROR = bytes([0xE2, 0x20, 0xA9, 0x06, 0x8D, 0xEB, 0x8F])
"""sep #$20; lda #$06; sta $8feb, which reaches the part and is not the port"""

ANSWERED = bytes([0xAD, 0x00, 0x80])
"""lda $8000, the read that ends an exchange and leaves the part waiting again"""

ARGUMENT_AFTER_COMMAND = bytes(
    [0xE2, 0x30, 0xA9, 0x00, 0x8D, 0x00, 0x80, 0xA2, 0x72, 0x8E, 0x00, 0x80]
)
"""sep #$30; lda #$00; sta $8000; ldx #$72; stx $8000.

The second store holds a constant and is eight bits wide and is an argument
word, because the first store already took the part out of waiting.
"""


HELD_IN_Y_INDEX_ONLY = bytes([0xE2, 0x10, 0xA0, 0x28, 0x8C, 0x00, 0x80])
"""sep #$10; ldy #$28; sty $8000, which narrows the index registers and not A"""

PADDED = bytes(600) + IMMEDIATE_LONG
"""The same command, further into an image than a decode is allowed to reach back"""


class PortTest(unittest.TestCase):
    def test_a_long_store_to_the_port_is_a_write(self) -> None:
        one = instruction(bytes([0x8F, 0x00, 0x80, 0x3F]))

        self.assertEqual(commands.at_port(one), commands.WRITING)

    def test_an_absolute_load_from_the_port_is_a_read(self) -> None:
        one = instruction(bytes([0xAD, 0x00, 0x80]))

        self.assertEqual(commands.at_port(one), commands.READING)

    def test_a_long_access_to_another_address_reaches_nothing(self) -> None:
        self.assertIsNone(commands.at_port(instruction(bytes([0xAF, 0x34, 0x12, 0x7E]))))

    def test_an_absolute_access_to_another_address_reaches_nothing(self) -> None:
        self.assertIsNone(commands.at_port(instruction(bytes([0xAD, 0x34, 0x12]))))

    def test_an_instruction_naming_no_address_reaches_nothing(self) -> None:
        self.assertIsNone(commands.at_port(instruction(bytes([0xEA]))))

    def test_an_immediate_reaches_nothing_however_it_reads(self) -> None:
        self.assertIsNone(commands.at_port(instruction(bytes([0xA9, 0x00]))))

    def test_pushing_the_address_of_the_port_is_not_reaching_it(self) -> None:
        self.assertIsNone(commands.at_port(instruction(bytes([0xF4, 0x00, 0x80]))))


class StoreTest(unittest.TestCase):
    def test_the_long_form_of_the_store_is_recognised(self) -> None:
        self.assertEqual(commands.store_at(IMMEDIATE_LONG, 4), ("sta", 4))

    def test_the_absolute_form_of_the_store_is_recognised(self) -> None:
        self.assertEqual(commands.store_at(IMMEDIATE_ABSOLUTE, 4), ("sta", 3))

    def test_a_store_through_the_index_registers_is_recognised(self) -> None:
        self.assertEqual(commands.store_at(HELD_IN_Y, 7), ("sty", 3))

    def test_a_store_of_zero_is_recognised(self) -> None:
        self.assertEqual(commands.store_at(ZERO, 2), ("stz", 3))

    def test_an_instruction_that_is_not_a_store_is_not_one(self) -> None:
        self.assertIsNone(commands.store_at(IMMEDIATE_LONG, 0))

    def test_a_long_store_naming_another_bank_is_not_one(self) -> None:
        self.assertIsNone(commands.store_at(bytes([0x8F, 0x00, 0x80, 0x20]), 0))

    def test_a_long_store_naming_another_address_is_not_one(self) -> None:
        self.assertIsNone(commands.store_at(bytes([0x8F, 0xEB, 0x8F, 0x3F]), 0))

    def test_an_absolute_store_to_a_mirror_of_the_port_is_not_the_port(self) -> None:
        self.assertIsNone(commands.store_at(A_MIRROR, 4))

    def test_a_long_store_running_off_the_end_is_not_one(self) -> None:
        self.assertIsNone(commands.store_at(bytes([0x8F, 0x00, 0x80]), 0))

    def test_an_absolute_store_running_off_the_end_is_not_one(self) -> None:
        self.assertIsNone(commands.store_at(bytes([0x8D, 0x00]), 0))


class AccessTest(unittest.TestCase):
    def test_a_long_store_to_the_data_port_is_found(self) -> None:
        one = reaching(bytes([0x8F, 0x00, 0x80, 0x3F]))

        self.assertEqual((one.mnemonic, one.register, one.way), ("sta", commands.DATA, "write"))

    def test_a_long_load_from_the_status_register_is_found(self) -> None:
        one = reaching(bytes([0xAF, 0x00, 0xC0, 0x3F]))

        self.assertEqual((one.mnemonic, one.register, one.way), ("lda", commands.STATUS, "read"))

    def test_an_absolute_accumulate_from_the_port_is_a_read(self) -> None:
        one = reaching(bytes([0x6D, 0x00, 0x80]))

        self.assertEqual((one.mnemonic, one.way), ("adc", "read"))

    def test_an_absolute_bit_test_of_the_status_register_is_a_read(self) -> None:
        one = reaching(bytes([0x2C, 0x00, 0xC0]))

        self.assertEqual((one.mnemonic, one.register), ("bit", commands.STATUS))

    def test_an_absolute_store_through_an_index_register_is_a_write(self) -> None:
        one = reaching(bytes([0x8C, 0x00, 0x80]))

        self.assertEqual((one.mnemonic, one.way), ("sty", "write"))

    def test_the_long_form_says_it_spelled_its_bank(self) -> None:
        self.assertTrue(reaching(bytes([0x8F, 0x00, 0x80, 0x3F])).long)

    def test_the_absolute_form_says_it_did_not(self) -> None:
        self.assertFalse(reaching(bytes([0x8D, 0x00, 0x80])).long)

    def test_a_long_access_naming_another_bank_reaches_nothing(self) -> None:
        self.assertIsNone(commands.access_at(bytes([0xAF, 0x00, 0x80, 0x20]), 0))

    def test_an_access_to_an_address_that_is_neither_register_reaches_nothing(self) -> None:
        self.assertIsNone(commands.access_at(bytes([0xAD, 0x00, 0x90]), 0))

    def test_an_instruction_that_reaches_no_port_is_not_an_access(self) -> None:
        self.assertIsNone(commands.access_at(bytes([0xEA, 0x00, 0x80]), 0))

    def test_an_access_running_off_the_end_is_not_one(self) -> None:
        self.assertIsNone(commands.access_at(bytes([0xAF, 0x00, 0x80]), 0))

    def test_an_offset_past_the_end_is_not_one(self) -> None:
        self.assertIsNone(commands.access_at(bytes([0x8D, 0x00, 0x80]), 9))

    def test_the_repr_names_the_offset_and_the_form(self) -> None:
        said = repr(reaching(bytes([0x8F, 0x00, 0x80, 0x3F])))

        self.assertIn("long", said)

    def test_the_repr_of_an_absolute_access_says_so(self) -> None:
        said = repr(reaching(bytes([0x8D, 0x00, 0x80])))

        self.assertIn("absolute", said)


class AccessesTest(unittest.TestCase):
    def test_an_image_that_reaches_nothing_has_no_accesses(self) -> None:
        self.assertEqual(commands.accesses(bytes(64)), ())

    def test_reads_and_writes_are_both_found(self) -> None:
        program = bytes([0x8D, 0x00, 0x80]) + bytes([0xAD, 0x00, 0x80])

        ways = {one.way for one in commands.accesses(program)}

        self.assertEqual(ways, {"read", "write"})

    def test_both_registers_are_found(self) -> None:
        program = bytes([0xAD, 0x00, 0x80]) + bytes([0x2C, 0x00, 0xC0])

        registers = {one.register for one in commands.accesses(program)}

        self.assertEqual(registers, {commands.DATA, commands.STATUS})

    def test_the_access_is_reported_at_the_offset_it_sits_at(self) -> None:
        program = bytes(4) + bytes([0x8F, 0x00, 0x80, 0x3F])

        self.assertEqual(commands.accesses(program)[0].offset, 4)


class StoresTest(unittest.TestCase):
    def test_an_image_that_never_stores_to_the_port_has_no_stores(self) -> None:
        self.assertEqual(commands.stores(bytes(64)), ())

    def test_the_store_is_reported_at_the_offset_it_sits_at(self) -> None:
        self.assertEqual(commands.stores(IMMEDIATE_LONG), (4,))

    def test_both_forms_are_found_by_the_same_search(self) -> None:
        found = commands.stores(IMMEDIATE_LONG + IMMEDIATE_ABSOLUTE)

        self.assertEqual(len(found), 2)


class ReadTest(unittest.TestCase):
    def test_a_command_carried_in_the_instruction_is_recovered(self) -> None:
        self.assertEqual(read(IMMEDIATE_LONG)[0].command, 0x06)

    def test_the_absolute_form_is_read_the_same_as_the_long_one(self) -> None:
        self.assertEqual(read(IMMEDIATE_ABSOLUTE)[0].command, 0x11)

    def test_a_command_held_in_an_index_register_is_recovered(self) -> None:
        self.assertEqual(read(HELD_IN_Y)[0].command, 0x28)

    def test_a_store_of_zero_issues_command_zero(self) -> None:
        self.assertEqual(read(ZERO)[0].command, 0x00)

    def test_a_sixteen_bit_store_is_an_argument_rather_than_a_command(self) -> None:
        self.assertIsNone(read(SIXTEEN_BIT)[0].command)

    def test_that_argument_is_reported_as_sixteen_bit_rather_than_unknown(self) -> None:
        self.assertIs(read(SIXTEEN_BIT)[0].narrow, False)

    def test_an_eight_bit_store_whose_value_is_out_of_reach_issues_nothing_known(self) -> None:
        self.assertIsNone(read(VALUE_OUT_OF_REACH)[0].command)

    def test_that_store_is_still_known_to_be_eight_bits_wide(self) -> None:
        self.assertIs(read(VALUE_OUT_OF_REACH)[0].narrow, True)

    def test_a_store_no_decode_reaches_is_left_undetermined(self) -> None:
        self.assertIsNone(read(NOTHING_IN_FRONT)[0].command)

    def test_that_store_has_no_width_either(self) -> None:
        self.assertIsNone(read(NOTHING_IN_FRONT)[0].narrow)

    def test_a_store_after_another_store_is_an_argument_however_constant(self) -> None:
        self.assertIsNone(read(ARGUMENT_AFTER_COMMAND)[1].command)

    def test_that_store_says_the_port_was_already_taken(self) -> None:
        self.assertIn("first", read(ARGUMENT_AFTER_COMMAND)[1].why)

    def test_the_command_in_front_of_it_is_still_read(self) -> None:
        self.assertEqual(read(ARGUMENT_AFTER_COMMAND)[0].command, 0x00)

    def test_a_read_of_the_port_leaves_the_next_store_a_command_again(self) -> None:
        found = read(IMMEDIATE_LONG + ANSWERED + IMMEDIATE_ABSOLUTE)

        self.assertEqual(found[1].command, 0x11)

    def test_decodes_that_disagree_leave_the_store_undetermined(self) -> None:
        self.assertIsNone(read(DISAGREEING)[0].command)

    def test_the_disagreement_is_said_rather_than_resolved(self) -> None:
        self.assertIn("disagree", read(DISAGREEING)[0].why)

    def test_a_determined_site_says_it_issues_a_command(self) -> None:
        self.assertTrue(read(IMMEDIATE_LONG)[0].issues)

    def test_an_undetermined_site_says_it_does_not(self) -> None:
        self.assertFalse(read(SIXTEEN_BIT)[0].issues)

    def test_the_site_names_the_offset_the_store_sits_at(self) -> None:
        self.assertEqual(read(IMMEDIATE_LONG)[0].offset, 4)

    def test_the_site_names_the_form_of_the_store(self) -> None:
        self.assertIn("3f8000", read(IMMEDIATE_LONG)[0].text)

    def test_the_absolute_form_is_named_without_a_bank(self) -> None:
        self.assertNotIn("3f", read(IMMEDIATE_ABSOLUTE)[0].text)

    def test_an_image_with_no_store_reads_to_nothing(self) -> None:
        self.assertEqual(read(bytes(64)), ())

    def test_narrowing_only_the_index_registers_still_reads_the_command(self) -> None:
        self.assertEqual(read(HELD_IN_Y_INDEX_ONLY)[0].command, 0x28)

    def test_a_store_further_in_than_the_window_reaches_is_still_read(self) -> None:
        self.assertEqual(read(PADDED)[0].command, 0x06)

    def test_a_disassembler_that_decodes_nothing_determines_nothing(self) -> None:
        found = commands.read(IMMEDIATE_LONG, nothing)

        self.assertIsNone(found[0].command)

    def test_that_store_is_reported_as_unreached_rather_than_as_an_argument(self) -> None:
        found = commands.read(IMMEDIATE_LONG, nothing)

        self.assertEqual(found[0].why, commands.UNREACHED)


class CommandsTest(unittest.TestCase):
    def test_every_command_the_image_issues_is_reported(self) -> None:
        found = read(IMMEDIATE_LONG + ANSWERED + IMMEDIATE_ABSOLUTE)

        self.assertEqual(commands.commands(found), (0x06, 0x11))

    def test_the_same_command_issued_twice_is_reported_once(self) -> None:
        found = read(IMMEDIATE_LONG + ANSWERED + IMMEDIATE_LONG)

        self.assertEqual(commands.commands(found), (0x06,))

    def test_a_site_that_issues_nothing_contributes_nothing(self) -> None:
        self.assertEqual(commands.commands(read(SIXTEEN_BIT)), ())


class ReprTest(unittest.TestCase):
    def test_a_determined_site_names_the_command_it_issues(self) -> None:
        self.assertIn("$06", repr(read(IMMEDIATE_LONG)[0]))

    def test_an_undetermined_site_names_why_it_is_undetermined(self) -> None:
        self.assertIn("argument", repr(read(SIXTEEN_BIT)[0]))


if __name__ == "__main__":
    unittest.main()
