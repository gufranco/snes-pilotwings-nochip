"""What each command byte reaches inside the part, read out of its program.

The part answers a command by walking a tree, not by indexing a table. It shifts
the command byte right one bit at a time and branches on the bit that fell out,
so 256 bytes reach a much smaller number of handlers and several bytes share
one. Which byte reaches which handler is therefore not something a dump shows by
inspection; it has to be walked.

This walks it, for all 256, and reports where each lands. Then it reads the
handler out. Both masks give 20 handlers with the same bytes reaching each, one
word apart, so the shape below is a property of the family rather than of a mask.

What this does not do is execute anything. `snes-dsp-python` runs the program and
answers what the part answers; this reads the program and says what it is made
of. The two are checked against each other rather than one standing in for the
other: the handler this names for a command has to be where a run of that
command actually goes.
"""

from collections.abc import Sequence
from typing import Any

import hardware

PROGRAM_WORDS = 2048
"""How many instructions the part holds. Each is twenty four bits."""

DISPATCH = 8
"""Where the tree starts.

Not zero. The first eight words wait for a request, take the command byte in
and mask it, and only then begin shifting. Walking from zero stops at the first
word that is not part of the tree and reports one handler for all 256 bytes,
which is what happened before this constant existed.
"""

SHIFT = "shr1 a"
"""How the tree tests a bit: shift the accumulator right, into the carry."""

CARRY_SET = "jca"
CARRY_CLEAR = "jnca"
HOME = "jmp $0000"
"""What ends a handler: a jump back to the wait at the top."""

MOST = 400
"""How many instructions of a handler to read before giving up.

Long enough for every handler in this part and short enough that a walk into
data comes back rather than reading to the end of the store.
"""

ALWAYS = 0x100
ON_CARRY = 0x082
ON_NO_CARRY = 0x080
"""Branch fields, by the value the part dispatches on.

Taken from the instruction set rather than chosen: these are the keys the
disassembler's own condition table uses for `jmp`, `jca` and `jnca`, and the
tests check that a word built from them reads back as the instruction meant.
"""

_JUMP_FORM = 2
_FORM_SHIFT = 22
_BRANCH_SHIFT = 13
_TARGET_SHIFT = 2
_BANK_BITS = 11

MASK = "dsp1"
"""Which mask of the part this project reproduces, and never the other.

Not a default that a caller may quietly change. Pilotwings wants the DSP-1: the
DSP-1B corrected an arithmetic fault, the attract demo is a recording of button
presses rather than a script, and nobody re-recorded it, so on the corrected part
the plane flies the same inputs into the ground instead of landing. Reproducing
the DSP-1B here would be more accurate than the cartridge and wrong for it.

Every entry point that needs a mask names one, so nothing picks it by accident.
Entry 1 of OPEN-QUESTIONS.md carries the measurement behind this.
"""

ISSUED = (
    0x00,
    0x01,
    0x02,
    0x03,
    0x04,
    0x06,
    0x08,
    0x0A,
    0x0C,
    0x0D,
    0x0E,
    0x10,
    0x11,
    0x13,
    0x14,
    0x18,
    0x1B,
    0x28,
    0x80,
)
"""The command bytes the cartridge's own code writes, from `commands.py`."""


def jump_word(branch: int, target: int) -> int:
    """The word that jumps to that address under that condition.

    Built here rather than looked up so a test can assemble a tree without the
    part's program, which never enters this repository.
    """
    low = target & ((1 << _BANK_BITS) - 1)
    bank = target >> _BANK_BITS & 0x3
    return _JUMP_FORM << _FORM_SHIFT | branch << _BRANCH_SHIFT | low << _TARGET_SHIFT | bank


_SHIFT_ALU = 11
_ALU_SHIFT = 16

SHIFT_WORD = _SHIFT_ALU << _ALU_SHIFT
"""One `shr1 a`, as the part encodes it.

The operate form is zero, so the whole word is the shift's own code in the
arithmetic field and nothing else. Checked by disassembling it rather than
asserted: the test reads it back and it says `shr1 a`.
"""


def _opcodes() -> Any:
    return hardware.load("upd7725").opcodes


def text_of(word: int) -> str:
    """That one word, named."""
    return str(_opcodes().decode(word).text)


def listing(program: Sequence[int]) -> dict[int, str]:
    """Every word of the program, named, keyed on where it sits."""
    return {one.address: one.text for one in _opcodes().disassemble(program)}


def _target(text: str) -> int:
    return int(text.split("$")[1], 16)


def _walk(named: dict[int, str], command: int) -> int | None:
    at = DISPATCH
    bits = command
    carry = 0
    seen: set[int] = set()
    while at not in seen:
        seen.add(at)
        text = named.get(at, "")
        if text.startswith(SHIFT):
            carry = bits & 1
            bits >>= 1
            at += 1
        elif text.startswith(CARRY_SET + " "):
            at = _target(text) if carry else at + 1
        elif text.startswith(CARRY_CLEAR + " "):
            at = at + 1 if carry else _target(text)
        else:
            return at
    return None


def dispatch(program: Sequence[int]) -> dict[int, int | None]:
    """Where each of the 256 command bytes lands, or nothing if it never leaves."""
    named = listing(program)
    return {command: _walk(named, command) for command in range(256)}


def handlers(program: Sequence[int]) -> dict[int, tuple[int, ...]]:
    """Each handler, and every command byte that reaches it."""
    found: dict[int, list[int]] = {}
    for command, at in dispatch(program).items():
        if at is not None:
            found.setdefault(at, []).append(command)
    return {at: tuple(commands) for at, commands in found.items()}


def body(program: Sequence[int], at: int, most: int = MOST) -> tuple[tuple[int, str], ...]:
    """One handler, from its first instruction to the jump that ends it."""
    named = listing(program)
    found: list[tuple[int, str]] = []
    for step in range(most):
        where = at + step
        text = named.get(where)
        if text is None:
            break
        found.append((where, text))
        if text == HOME:
            break
    return tuple(found)


def report(program: Sequence[int]) -> list[str]:
    found = handlers(program)
    lines = [
        f"{len(found)} handlers over 256 command bytes",
        "",
        "  handler  bytes  the ones the cartridge writes",
    ]
    for at in sorted(found):
        commands = found[at]
        mine = [one for one in commands if one in ISSUED]
        named = " ".join(f"${one:02x}" for one in mine) if mine else ""
        lines.append(f"  ${at:04x}  {len(commands):>5}  {named}")
    return lines


def program_of(mask: str) -> tuple[int, ...]:
    """The program that mask carries, as words.

    The image itself belongs to whoever made the part and is never here, so this
    reaches it through the model, which finds it on the machine or refuses.
    """
    part = hardware.load("snesdsp").Chip(mask)
    return tuple(part.core.stores.program[at] for at in range(PROGRAM_WORDS))


def main(
    argv: tuple[str, ...] | list[str] = (),
    say: Any = print,
    read: Any = program_of,
) -> int:
    if not argv:
        say("usage: microcode.py <mask>, one of dsp1 or dsp1b")
        return 2
    for line in report(read(argv[0])):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
