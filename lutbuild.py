"""One table holding every answer the game was seen to need, for every command.

This is the lookup the replacement reaches first. It carries what the game
actually asks for rather than what the part accepts, because the part's input
domain is the exponent of its argument count and nothing holds that, while the
game's own set fits with room to spare.

The layout is one blob. It opens with a count and an index, one entry per
command, and each entry says where that command's rows begin and how wide its
keys and answers are. The rows follow, keys first and sorted, so a replacement
finds one by halving the range rather than walking it.

    byte 0        how many commands are in here
    then, per command, twelve bytes:
        + 0       the command byte
        + 1       key words
        + 2       answer words, two bytes, because $0a answers 764 of them
        + 4       how many rows
        + 8       where the rows start, from the beginning of the blob

Answers come from the part wherever the part could be driven to the same state,
and from the recording everywhere else. Keys always come from the recording,
because only the game says what it asks.

Nothing here is committed. It is built on the machine of whoever has the
cartridge and the part, into the ignored build directory, and the assembler
folds it in.

A miss is possible, and that is the whole reason every command also has a
routine behind it. The table holds a set, not a range: an argument no recording
showed has no row, and the fallback is what answers then. One command, `$0a`,
misses always: see UNSTORABLE below for the measurement that put it there.
"""

import struct
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import complete
import exchanges

BANK_BYTES = 0x8000
"""What one low-addressed bank holds, and so how the blob is cut up."""

HEADER = 2
"""The count of commands, and one byte of nothing after it.

The pad is what keeps every row on an even offset, and that is what keeps a
word from ever being split across two banks.

A bank holds 32,768 bytes, which is even, so a bank boundary falls between two
words exactly when the row stream starts on an even offset. Every stride here is
a whole number of words, so once the first row is even every word after it is.
Start the stream on an odd offset instead and some word, eventually, has its
first byte at $FFFF and its second in a bank the cartridge does not put there:
on a low cartridge the byte after $9AFFFF is $9B8000, not $9B0000.

It happened. With a one byte header the rows began at 449 and command $02's row
4,649 began at 65,535, so its first word was read half from the table and half
from the console's own memory, the search missed a key it holds, and the
fallback answered with the row below. One key in 2,801 across a run.
"""

COMMAND_MAP = 256
"""A byte per command byte, saying which entry answers it, or $FF for none.

It sits between the count and the entries, so it is always at the same place and
the entries are always 257 bytes in. Without it the cartridge walked the entries
comparing command bytes, which averaged six comparisons and a hundred and
seventy five cycles on every lookup the game makes.
"""

NO_ENTRY = 0xFF
"""What the map holds for a command the table does not answer."""

ENTRY_BYTES = 16
"""How wide one command's entry in the index is.

Sixteen rather than the twelve the five fields need. The sixteenth byte is where
this command's answers begin, which is where its rows begin plus its row count
times its key width times two. The cartridge worked that out for itself on every
lookup, and working it out is a thirty two bit multiply.

Sixteen rather than thirteen because the walk over the index steps by this
number, and stepping by a power of two is a shift where stepping by anything
else is an addition.
"""

REGIONS = ("usa", "jp", "eur")

ROOM = 95 * BANK_BYTES - 4096
"""How much of the cartridge is left for this table.

Two banks, $1D and $1E. The game holds sixteen, this project's code one, and
the three tables taken from the part twelve, and the image cannot pass thirty
two banks at all, which OPEN-QUESTIONS entry 6 measures. So the recorded answers
get what is left rather than what they would like: 98,304 bytes against the
3,014,801 the full set needs.

Which commands make it in is decided by what each buys. A command whose
arithmetic is already exact in 65816 gains nothing from a row, and a command too
large to fit cannot have one, so the table holds the ones in between.
"""

UNSTORABLE = (0x0A,)
"""Commands whose answers no table can hold, whatever they are keyed on.

Only `$0a`, and the reason is size rather than ambiguity. Keyed on its own
argument word its answer is not a function of the key at all: two keys, and one
of them carries every answer the recording holds. Keyed on its own word plus
`$02`'s arguments it becomes a function, exactly, with no ambiguous key in any
of the three recordings. It is still not storable. `$0a` answers 764 words, the
three recordings hold 5,232, 5,232 and 5,738 distinct answers, and every one of
the 764 positions differs between at least two of them, so nothing can be
factored out as constant. Storing the European recording alone would take 8.7
megabytes, against 3.9 for the whole cartridge.

That it is an exact function of `$02`'s arguments is the useful half of the
finding: it says `$0a` is arithmetic waiting to be read out of the chip's
program, not state that has to be remembered.
"""

COMPUTED = (0x00, 0x80, 0x04, 0x08)
"""Commands answered by arithmetic, so a row would only agree with it.

Their routines were read out of the part's own program and checked exact
against it on four hundred random argument sets each, and looking one up costs
sixteen times what computing it does. Leaving them out is what makes room for
the commands that have no arithmetic yet.
"""

CARRIER = {0x03: 0x14, 0x06: 0x02, 0x0D: 0x02, 0x0E: 0x02, 0x13: 0x11, 0x1B: 0x11}
"""Which earlier command's arguments join the key, for the ones that need it.

Measured: these six answer differently for identical arguments, and adding one
earlier command's arguments to the key leaves nothing ambiguous.
"""


def encode(
    tables: Mapping[int, tuple[Sequence[tuple[Sequence[int], Sequence[int]]], int, int]],
) -> bytes:
    """The blob, from a table of rows per command."""
    commands = sorted(tables)
    out = bytearray()
    out.append(len(commands))
    out.append(0)
    out += bytes(commands.index(one) if one in commands else NO_ENTRY for one in range(COMMAND_MAP))
    rows_at = HEADER + COMMAND_MAP + ENTRY_BYTES * len(commands)
    body = bytearray()
    for command in commands:
        rows, key_words, answer_words = tables[command]
        ordered = sorted(rows, key=lambda one: tuple(one[0]))
        out.append(command)
        out.append(key_words)
        out += struct.pack("<H", answer_words)
        out += struct.pack("<I", len(ordered))
        out += struct.pack("<I", rows_at + len(body))
        out += struct.pack("<I", rows_at + len(body) + len(ordered) * key_words * 2)
        for key, _ in ordered:
            body += struct.pack(f"<{key_words}H", *_padded(key, key_words))
        for _, answer in ordered:
            body += struct.pack(f"<{answer_words}H", *_padded(answer, answer_words))
    if (rows_at + len(body)) % 2 or rows_at % 2:
        raise Uneven(f"the rows begin at {rows_at}, which is odd, so a word can be split")
    return bytes(out + body)


class Uneven(Exception):
    """A layout that puts a row on an odd offset, which HEADER explains."""


def _padded(words: Sequence[int], width: int) -> tuple[int, ...]:
    return tuple(one & 0xFFFF for one in words) + (0,) * (width - len(words))


def sliced(raw: bytes) -> tuple[bytes, ...]:
    """The blob cut into pieces no larger than a bank, because nothing spans one."""
    return tuple(raw[at : at + BANK_BYTES] for at in range(0, max(len(raw), 1), BANK_BYTES))


FIRST_BANK = 0x99
"""The bank the table starts in, chosen so that all of it stays addressable.

This is a low cartridge, so only banks $00 to $7D carry anything: $7E and $7F
are the console's memory and everything from $80 up is a second view of what is
already below. The game itself holds $00 to $0F, all sixteen banks of it, and
this project's code holds $10, so the first bank free for a table is $11.
"""

WORK_RAM = (0x7E, 0x7F)
"""The two banks that are the console's memory rather than the cartridge.

Low addressing reaches the cartridge in banks $00 to $7D and again from $80, and
these two are work RAM in between. A table long enough to run into them has to
step over them, which is what makes the pieces not simply consecutive.
"""


def banks(pieces: int, first: int) -> tuple[int, ...]:
    """Which bank each piece lands in, stepping over the two that are memory."""
    chosen: list[int] = []
    at = first
    while len(chosen) < pieces:
        if at not in WORK_RAM:
            chosen.append(at)
        at += 1
    return tuple(chosen)


def source(pieces: int, first_bank: int) -> str:
    """The assembly that places those pieces, one bank each."""
    lines = [
        "; Built by lutbuild.py. Not source, not committed, and regenerated by",
        "; anybody who builds. See lutbuild.py for what is in here and why.",
        "",
    ]
    for piece, bank in enumerate(banks(pieces, first_bank)):
        lines.append(f"org ${bank:02X}8000")
        if piece == 0:
            lines.append("dsp1_lut:")
        lines.append(f'incbin "lut-{piece}.bin"')
    lines.append("")
    return "\n".join(lines)


AXES_BANK = 0xF4
"""Where the axis blocks are placed, in the second view of the cartridge.

Above the reciprocal at $73 and clear of everything else this project places.
The blocks are a few hundred bytes, so one bank is more than enough.
"""


def axes(built: Mapping[int, Any]) -> dict[int, tuple[tuple[int, ...], ...]]:
    """The commands whose keys are every combination of a few values per word.

    Such a command needs no search at all. Its rows are sorted, and a sorted
    list of every combination is mixed-radix counting: the first key word
    changes slowest, the last fastest, so a key's row number is the sum over
    words of how far along that word's own list the value sits, times the number
    of rows one step of it covers.

    Only a command whose key set is exactly the product of its per-word value
    sets qualifies. A command missing even one combination would still have
    sorted rows, but the arithmetic above would name a row that is not the one
    it wanted, and the answer would be wrong rather than absent.
    """
    found: dict[int, tuple[tuple[int, ...], ...]] = {}
    for command, (rows, key_words, _) in built.items():
        if not rows:
            continue
        values = tuple(tuple(sorted({key[at] for key, _ in rows})) for at in range(key_words))
        whole = 1
        for one in values:
            whole *= len(one)
        if whole == len(rows):
            found[command] = values
    return found


def strides(values: Sequence[Sequence[int]]) -> tuple[int, ...]:
    """How many rows one step of each key word covers, most significant first."""
    out: list[int] = []
    covered = 1
    for one in reversed(values):
        out.append(covered)
        covered *= len(one)
    return tuple(reversed(out))


def axes_routine(command: int, values: Sequence[Sequence[int]]) -> list[str]:
    """One command's row, as code rather than as a list to walk.

    The row a key names is a mixed-radix number: each key word takes one of a
    short list of values, and its position in that list is worth a fixed number
    of rows. Both the list and what a position is worth are known when this is
    written, so the comparisons are written out.

    The cartridge used to walk the lists, and walking cost it a thirty two bit
    addition for every value it rejected and another pass over the rest of the
    list once it matched. Written out, a rejected value is a compare and a
    branch, and a match adds one constant.

    The values are tested from the last to the first, and each test branches only
    over its own match. That is one instruction slower per rejected value than
    testing them in order and branching to a block below, and it is written this
    way because it keeps every branch short whatever the list length: the other
    shape puts a nine value list 125 bytes from its own branches, and a short
    branch reaches 127. What leaves a match is a jump rather than a branch, for
    the same reason and at the same cost.
    """
    lines = [
        f"lut_axes_{command:02x}:",
        "    ldx.w #$0000                ; the row, built up a word at a time",
        "",
    ]
    for at, (one, covered) in enumerate(zip(values, strides(values), strict=True)):
        lines.append(f"    lda.w !PAGE+!ARG+{at * 2}")
        for step in range(len(one) - 1, 0, -1):
            lines.append(f"    cmp.w #${one[step]:04X}")
            lines.append(f"    bne .w{at}n{step}")
            lines.append("    txa")
            lines.append("    clc")
            lines.append(f"    adc.w #${step * covered:04X}")
            lines.append("    tax")
            lines.append(
                f"    jmp .w{at}done            ; a jump rather than a branch: same\n                                ; three cycles, and no limit on the reach"
            )
            lines.append(f".w{at}n{step}:")
        lines.append(f"    cmp.w #${one[0]:04X}        ; the first value is worth nothing")
        lines.append(f"    beq .w{at}done")
        lines.append("    jmp lut_axes_none           ; a value no row carries")
        lines.append(f".w{at}done:")
        lines.append("")
    lines += [
        "    stx !MID",
        "    stz !MID+2                  ; no command answered this way has more",
        "                                ; rows than a word holds",
        "    plp",
        "    sec",
        "    rtl",
        "",
    ]
    return lines


def axes_source(found: Mapping[int, Sequence[Sequence[int]]], bank: int = AXES_BANK) -> str:
    """The routines asm/dsp1-answer.asm jumps to instead of searching."""
    lines = [
        "; Built by lutbuild.py. Not source, not committed, and regenerated by",
        "; anybody who builds. See lutbuild.py for what is in here and why.",
        "",
        f"org ${bank:02X}8000",
        "",
        "; --------------------------------------------------------------------------",
        "; Which routine answers this command, if any.",
        "; --------------------------------------------------------------------------",
        "lut_axes_dispatch:",
    ]
    for command in sorted(found):
        lines.append(f"    cmp.w #${command:04X}")
        lines.append("    bne +                       ; the long way round, because a")
        lines.append(
            f"    jmp lut_axes_{command:02x}             ; routine can be further off than a"
        )
        lines.append("+                               ; short branch reaches")
    lines.append("")
    lines.append("lut_axes_none:")
    lines.append("    plp")
    lines.append("    jml lut_find                ; not one of them, so the search answers")
    lines.append("")
    for command in sorted(found):
        lines += axes_routine(command, found[command])
    return "\n".join(lines)


def rows_of(runs: Sequence[Sequence[Any]]) -> dict[int, Any]:
    """Every row a set of runs holds, keyed the way the search will look.

    A command that answers nothing is left out: there is nothing to look up, and
    so is `$0a`, whose answers are a function of a wider key but far too large
    to hold. The six that need a carrier get one earlier command's arguments
    joined onto their key, which is what makes their answers a function of it.
    """
    found: dict[int, dict[tuple[int, ...], tuple[int, ...]]] = {}
    for run in runs:
        last: dict[int, tuple[int, ...]] = {}
        for one in run:
            if one.answer and one.command not in UNSTORABLE:
                held = last.get(CARRIER[one.command], ()) if one.command in CARRIER else ()
                found.setdefault(one.command, {})[(*one.words, *held)] = one.answer
            last[one.command] = one.words
    built: dict[int, Any] = {}
    for command, rows in found.items():
        if command in COMPUTED:
            continue
        key_words = max(len(one) for one in rows)
        answer_words = max(len(one) for one in rows.values())
        built[command] = (tuple(rows.items()), key_words, answer_words)
    return built


def weighed(runs: Sequence[Sequence[Any]]) -> dict[int, int]:
    """How many times each command was asked, across every recording."""
    calls: dict[int, int] = {}
    for run in runs:
        for one in run:
            if one.answer:
                calls[one.command] = calls.get(one.command, 0) + 1
    return calls


def sized(rows: Sequence[Any], key_words: int, answer_words: int) -> int:
    return len(rows) * (key_words + answer_words) * 2


def chosen(built: Mapping[int, Any], calls: Mapping[int, int], room: int) -> dict[int, Any]:
    """The commands worth the space, most calls per byte first.

    Everything does not fit, so this takes what the game asks for most often per
    byte it costs. A command left out still answers, from the routine behind the
    lookup, which is why leaving one out costs accuracy rather than correctness.
    """
    ranked = sorted(
        built,
        key=lambda command: -calls.get(command, 0) / sized(*built[command]),
    )
    kept: dict[int, Any] = {}
    spent = 0
    for command in ranked:
        cost = sized(*built[command])
        if spent + cost > room:
            continue
        kept[command] = built[command]
        spent += cost
    return kept


def gather(where: Path = Path("build"), say: Any = None) -> dict[int, Any]:
    """The rows every recording holds, with the completable commands completed."""
    runs = tuple(exchanges.taken((where / f"trace-{one}.bin").read_bytes()) for one in REGIONS)
    return chosen(completed(rows_of(runs), runs, say=say), weighed(runs), ROOM)


def completed(
    built: dict[int, Any], runs: Sequence[Sequence[Any]], say: Any = None
) -> dict[int, Any]:
    """Fill out the commands whose whole domain fits, and leave the rest alone.

    A recorded row is kept as recorded; only a key the recordings never showed is
    asked of the part. Which commands qualify, and why the ones that do not are
    excluded, is in complete.py.
    """
    for command, values in complete.domains(runs).items():
        rows, key_words, answer_words = built[command]
        keys = complete.wanted(values)
        whole = complete.filled(command, keys, answer_words, dict(rows), say=say)
        built[command] = (tuple(whole.items()), key_words, answer_words)
    return built


def report(built: Mapping[int, Any], raw: bytes) -> list[str]:
    lines = [f"{len(built)} commands, {len(raw):,} bytes, {len(sliced(raw))} banks", ""]
    lines.append("  cmd      rows  key  answer      bytes")
    for command in sorted(built):
        rows, key_words, answer_words = built[command]
        size = len(rows) * (key_words + answer_words) * 2
        lines.append(
            f"  ${command:02x}  {len(rows):>8,}  {key_words:>3}  {answer_words:>6}  {size:>11,}"
        )
    return lines


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if not argv:
        say("usage: lutbuild.py <mask> [<directory>], one of dsp1 or dsp1b")
        return 2
    into = Path(argv[1]) if len(argv) > 1 else Path("build")
    into.mkdir(exist_ok=True)
    built = gather(say=say)
    raw = encode(built)
    pieces = sliced(raw)
    for at, piece in enumerate(pieces):
        (into / f"lut-{at}.bin").write_bytes(piece)
    (into / "lut-map.asm").write_text(source(len(pieces), first_bank=FIRST_BANK))
    found = axes(built)
    (into / "lut-axes.asm").write_text(axes_source(found))
    say(
        f"{len(found)} commands need no search: "
        + ", ".join(f"${one:02x}" for one in sorted(found))
    )
    for line in report(built, raw):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
