"""The three tables that carry `$02`'s state into the cartridge, built from the part.

`$0a` draws the ground and reads ten words to do it: a per-line step, a horizon,
two mantissas, two exponents and a four word matrix. `$02` writes every one of
them, and the recorded-answer table carries only the four words `$02` hands back,
which is why the cartridge could compute nothing until now.

So the state is taken from the part directly. Every distinct `$02` argument set
the recordings hold is driven, the ten cells are read out of the part's own
memory, and `parameter.py` splits them into three tables keyed on fewer arguments
than the whole set. `state02.py` packs each one, key first and sorted, so the
cartridge bisects rather than walks.

Why one bank each. A low addressed bank reaches $8000 to $FFFF, which is 32,768
bytes, and the assembler refuses to lay a run of bytes across a bank border. All
three tables fit inside one, measured: 9,544, 30,330 and 19,812 bytes. `TooBig`
refuses a table that does not, rather than letting the assembler place it
somewhere it cannot be read from.

Nothing here is committed. It reads a cartridge dump and a part the person
running it already owns, and writes into the ignored build directory.

    UPD7725_FIRMWARE_DIR=firmware python3 state02build.py dsp1 build

The mask is named rather than defaulted, for the reason `microcode.MASK` gives:
the DSP-1B corrected an arithmetic fault, and the demo is a recording of button
presses rather than a script, so on the corrected part the plane flies the same
inputs into the ground.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import derived
import exchanges
import hardware
import parameter
import state02

SETUP = 0x02
"""The command that writes the state, and the only one driven here."""

ANSWER_WORDS = 4
"""How many words `$02` hands back. Not the state; the state is read out of RAM."""

REGIONS = ("usa", "jp", "eur")
"""Which recordings the argument sets are taken from.

All three rather than one. They are recordings of the same attract sequence in
three regions, and the sets differ between them, so the union covers every demo
this project can be built for.
"""

BANK_BYTES = 0x8000
"""What one low addressed bank holds, and so what one table may not exceed."""

FIRST_BANK = 0xF0
"""The first bank free for these.

The game holds $00 to $0F, this project's code $10, the sine and cosine taken
from the part $11 to $18, the recorded answers $19 to $6F, and the window the
redirected accesses land in is $7D. So $70 upwards is what is left, and the two
banks above $7D are the console's memory rather than the cartridge at all.
"""

ORDER = ("line", "scale", "matrix")
"""The order the tables are placed in, so the assembly and the report agree."""


class TooBig(Exception):
    """A table that will not fit the one bank the cartridge gives it.

    Raised rather than cut into pieces. A table split across banks has no single
    stride the search can multiply an index by, so the cartridge could not bisect
    it, and a lookup that cannot bisect is a lookup that walks 3,302 rows for
    every frame.
    """


def argument_sets(runs: Iterable[Sequence[Any]]) -> tuple[tuple[int, ...], ...]:
    """Every distinct `$02` argument set the recordings hold.

    Sorted, so two machines building from the same recordings write the same
    bytes, and so the report reads the same way twice.
    """
    found = {
        one.words
        for run in runs
        for one in run
        if one.command == SETUP and len(one.words) == parameter.WORDS
    }
    return tuple(sorted(found))


WHOLE_SCALE = 0x8000
"""The scale to ask `$02` for so the horizon comes back as the value behind it.

The horizon is that value times argument 4 shifted down fifteen places, measured
exact against the part across the whole word. Asking with $8000 makes the shift
undo the multiply and leaves minus the value, so one question reads it out.
"""

CLAMPED_ANGLES = 0x10000
"""How many angles the clamped cosine covers, which is every one a word can hold."""


def clamped(
    part: Any, count: int = CLAMPED_ANGLES, watch: Callable[[int], None] | None = None
) -> tuple[int, ...]:
    """The value `$02` derives its horizon and its second scale from, per angle.

    It is the cosine of the angle for most of the turn and something else near
    and past a quarter turn, where the part holds it at a floor. What that floor
    is has not been read out of the part's program, and it does not have to be:
    the value is a function of the angle alone, so asking the part for all 65,536
    of them is a complete answer that cannot miss.

    Three of the ten words `$0a` reads come out of this one table. The horizon is
    it times argument 4, shifted down fifteen places. The second mantissa and the
    second exponent are the normalise and the reciprocal of it, which the
    cartridge already runs for every scanline.

    Read through the horizon rather than out of the part's memory directly,
    because the cell the part keeps it in is the horizon's own and holds the
    scaled value, not this.
    """
    found: list[int] = []
    for angle in range(count):
        derived.ask(part, SETUP, (0, 0, 0, 0, WHOLE_SCALE, 0, angle), ANSWER_WORDS)
        horizon = part.core.stores.scratch[parameter.CELLS["horizon"]]
        found.append(-derived.signed(horizon) & 0xFFFF)
        if watch is not None and angle % 4096 == 0:
            watch(angle)
    return tuple(found)


def state_of(part: Any) -> dict[str, int]:
    """The ten cells `$0a` reads, as the part holds them right now."""
    return {
        name: derived.signed(part.core.stores.scratch[at]) for name, at in parameter.CELLS.items()
    }


def driven(
    part: Any,
    sets: Sequence[tuple[int, ...]],
    watch: Any = None,
) -> dict[tuple[int, ...], dict[str, int]]:
    """The state every argument set leaves behind, in one pass over one part.

    One part rather than a fresh one per question. `$02` leaves the same state
    whether it is reached by replaying the recording up to it or driven directly,
    and driving it twice with the same arguments leaves the same state both
    times, so reuse is safe and turns a day into eight seconds.
    """
    seen: dict[tuple[int, ...], dict[str, int]] = {}
    for at, words in enumerate(sets):
        derived.ask(part, SETUP, words, ANSWER_WORDS)
        found = state_of(part)
        parameter.mirrored(found)
        seen[words] = found
        if watch is not None and at % 2000 == 0:
            watch(at)
    return seen


def tables(
    seen: Mapping[tuple[int, ...], Mapping[str, int]],
) -> dict[str, dict[tuple[int, ...], tuple[int, ...]]]:
    """The three tables, each keyed on the arguments its group answers to."""
    built: dict[str, dict[tuple[int, ...], tuple[int, ...]]] = {}
    for name, (slots, cells) in parameter.GROUPS.items():
        rows = ((words, tuple(state[cell] for cell in cells)) for words, state in seen.items())
        built[name] = parameter.gathered(rows, slots)
    return built


def checked(built: Mapping[str, Mapping[tuple[int, ...], tuple[int, ...]]]) -> None:
    """Refuse any table the cartridge could not hold or could not search."""
    for name, table in built.items():
        state02.checked(table)
        size = parameter.sized(table)
        if size > BANK_BYTES:
            raise TooBig(
                f"the {name} table is {size:,} bytes and one bank holds {BANK_BYTES:,},"
                " so the cartridge could not bisect it"
            )


BUILT_BY = (
    "; Built by state02build.py. Not source, not committed, and regenerated by",
    "; anybody who builds. See state02build.py for what is in here and why.",
    "",
)


def source(built: Mapping[str, Mapping[tuple[int, ...], tuple[int, ...]]]) -> str:
    """The shape of each table, as constants the lookup reads.

    Every table publishes its row count, its stride and its key width, so no
    length lives in two places and none can go stale against the bytes beside it.

    Separate from `placement` because the assembler resolves a define where it
    reads it and a label on either pass. The code needs these constants before it
    is assembled and the bytes have to land after it, so the two cannot be one
    file.
    """
    lines = list(BUILT_BY)
    for name in ORDER:
        table = built[name]
        upper = name.upper()
        lines.append(f"!STATE02_{upper}_ROWS   = {state02.rows(table)}")
        lines.append(
            f"!STATE02_{upper}_STRIDE = {state02.stride(table) * parameter.BYTES_PER_WORD}"
        )
        lines.append(f"!STATE02_{upper}_KEYS   = {len(next(iter(table), ()))}")
        lines.append("")
    return "\n".join(lines)


def placement(first_bank: int) -> str:
    """The assembly that puts each table at the top of its own bank.

    The lookup takes both the bank and the offset from the label here rather than
    from a constant of its own. Naming an address twice is how two constants in
    dsp1-answer.asm came to say $11 while the bytes were at $1d, which made every
    command miss.
    """
    lines = list(BUILT_BY)
    for step, name in enumerate(ORDER):
        lines.append(f"org ${first_bank + step:02X}8000")
        lines.append(f"state02_{name}:")
        lines.append(f'incbin "state02-{name}.bin"')
    lines.append("")
    return "\n".join(lines)


def report(built: Mapping[str, Mapping[tuple[int, ...], tuple[int, ...]]]) -> list[str]:
    lines = ["  table     rows  keys  words      bytes  bank"]
    for step, name in enumerate(ORDER):
        table = built[name]
        keys = len(next(iter(table), ()))
        lines.append(
            f"  {name:8} {state02.rows(table):>5}  {keys:>4}"
            f"  {state02.stride(table) - keys:>5}  {parameter.sized(table):>9,}"
            f"   ${FIRST_BANK + step:02X}"
        )
    lines.append(f"  total {sum(parameter.sized(one) for one in built.values()):,} bytes")
    return lines


def gather(mask: str, where: Path = Path("build"), say: Any = None) -> dict[str, Any]:
    """Every table, driven out of the part named by that mask."""
    runs = tuple(exchanges.taken((where / f"trace-{one}.bin").read_bytes()) for one in REGIONS)
    sets = argument_sets(runs)
    if say is not None:
        say(f"{len(sets):,} distinct $02 argument sets across {len(REGIONS)} recordings")
        say(f"arguments that never varied: {parameter.fixed(sets)}")
    part = hardware.load("snesdsp").Chip(mask)
    watch = None if say is None else (lambda at: say(f"  {at:,}"))
    built = tables(driven(part, sets, watch=watch))
    checked(built)
    return built


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if not argv:
        say("usage: state02build.py <mask> [<directory>], one of dsp1 or dsp1b")
        return 2
    into = Path(argv[1]) if len(argv) > 1 else Path("build")
    into.mkdir(exist_ok=True)
    built = gather(argv[0], into, say=say)
    for name, table in built.items():
        (into / f"state02-{name}.bin").write_bytes(state02.packed(table))
    (into / "state02-map.asm").write_text(source(built))
    (into / "state02-data.asm").write_text(placement(FIRST_BANK))

    say(f"driving the part for {CLAMPED_ANGLES:,} clamped cosines")
    values = clamped(hardware.load("snesdsp").Chip(argv[0]), watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {derived.write(into / 'state02-clamped.bin', values):,} bytes")
    for line in report(built):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
