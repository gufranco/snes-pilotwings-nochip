import sys
from collections.abc import Sequence
from typing import Any

import hardware
import script

PROGRAM_WORDS = 2048

DISPATCH = 8

SHIFT = "shr1 a"

CARRY_SET = "jca"
CARRY_CLEAR = "jnca"
HOME = "jmp $0000"

MOST = 400

ALWAYS = 0x100
ON_CARRY = 0x082
ON_NO_CARRY = 0x080

_JUMP_FORM = 2
_FORM_SHIFT = 22
_BRANCH_SHIFT = 13
_TARGET_SHIFT = 2
_BANK_BITS = 11

MASK = "dsp1"

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


def jump_word(branch: int, target: int) -> int:
    low = target & ((1 << _BANK_BITS) - 1)
    bank = target >> _BANK_BITS & 0x3
    return _JUMP_FORM << _FORM_SHIFT | branch << _BRANCH_SHIFT | low << _TARGET_SHIFT | bank


_SHIFT_ALU = 11
_ALU_SHIFT = 16

SHIFT_WORD = _SHIFT_ALU << _ALU_SHIFT


def _opcodes() -> Any:
    return hardware.load("upd7725").opcodes


def text_of(word: int) -> str:
    return str(_opcodes().decode(word).text)


def listing(program: Sequence[int]) -> dict[int, str]:
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
    named = listing(program)
    return {command: _walk(named, command) for command in range(256)}


def handlers(program: Sequence[int]) -> dict[int, tuple[int, ...]]:
    found: dict[int, list[int]] = {}
    for command, at in dispatch(program).items():
        if at is not None:
            found.setdefault(at, []).append(command)
    return {at: tuple(commands) for at, commands in found.items()}


def body(program: Sequence[int], at: int, most: int = MOST) -> tuple[tuple[int, str], ...]:
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


FORMS = ("op", "rt", "jp", "ld")

PRODUCT_SOURCES = ("ram[dp]", "idb", "m", "n")

STEPS = ("", "dp+1", "dp-1", "dp=0")

FAR_HALF = 0x80


def fields(raw: int) -> dict[str, int]:
    return {
        "form": raw >> 22 & 3,
        "product": raw >> 20 & 3,
        "alu": raw >> 16 & 15,
        "accumulator": raw >> 15 & 1,
        "step": raw >> 13 & 3,
        "page": raw >> 9 & 15,
        "table_step": raw >> 8 & 1,
        "source": raw >> 4 & 15,
        "destination": raw & 15,
    }


def explain(raw: int) -> str:
    part = fields(raw)
    if FORMS[part["form"]] == "ld":
        return f"{_destinations()[part['destination']]} = ${raw >> 6 & 0xFFFF:04x}"
    if FORMS[part["form"]] == "jp":
        return "branch"
    said = []
    source = _sources()[part["source"]]
    destination = _destinations()[part["destination"]]
    if destination == "klm":
        said.append(f"l <- {source}; k <- ram[dp|${FAR_HALF:02x}]")
    elif destination != "none":
        said.append(f"{destination} <- {source}")
    operation = _alu()[part["alu"]]
    if operation != "nop":
        letter = "ab"[part["accumulator"]]
        said.append(f"{letter} = {letter} {operation} {PRODUCT_SOURCES[part['product']]}")
    if part["step"]:
        said.append(STEPS[part["step"]])
    if part["page"]:
        said.append(f"dp ^= ${part['page']:x}0")
    if part["table_step"]:
        said.append("rp-1")
    return "; ".join(said) or "nothing"


def _sources() -> Any:
    return _opcodes().SOURCES


def _destinations() -> Any:
    return _opcodes().DESTINATIONS


def _alu() -> Any:
    return _opcodes().ALU


script.entry(__name__, main, sys.argv[1:])
