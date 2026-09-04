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

HEADER = 1
ENTRY_BYTES = 12

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
    rows_at = HEADER + ENTRY_BYTES * len(commands)
    body = bytearray()
    for command in commands:
        rows, key_words, answer_words = tables[command]
        ordered = sorted(rows, key=lambda one: tuple(one[0]))
        out.append(command)
        out.append(key_words)
        out += struct.pack("<H", answer_words)
        out += struct.pack("<I", len(ordered))
        out += struct.pack("<I", rows_at + len(body))
        for key, _ in ordered:
            body += struct.pack(f"<{key_words}H", *_padded(key, key_words))
        for _, answer in ordered:
            body += struct.pack(f"<{answer_words}H", *_padded(answer, answer_words))
    return bytes(out + body)


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
    for line in report(built, raw):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
