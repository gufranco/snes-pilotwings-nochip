"""What each command takes and returns, and whether its answers can be stored.

The plan this project started from was to compute every answer ahead of time and
ship the results, which is what a cartridge with room to spare is for. Whether
that works is decided by how many argument words a command reads, because that is
the exponent on the size of the table it would take. One word is 65,536 rows and a
cartridge holds that. Two words is 4,294,967,296 rows and nothing holds that at
any output width.

So the count is measured against the part rather than reasoned about, and it is
measured by what the part gives back rather than by a length somebody chose. A
command written one word short of what it wants still has something in its
output, because the part echoes what it was given. Written one word past what it
wants, it has nothing. The count is that silence, stepped back one.

Two earlier readings of the same question were wrong in different ways, and both
are worth naming because both looked right. The first wrote six words to every
command and asked which positions moved the answer, which handed a command
wanting two words four it never asked for. The second read the status register,
which settles a word later than the answer appears and so reported every count
one too high.

The reading is checked against arithmetic that can be predicted independently.
Command 0x00 takes two words and returns one, and for 0x1234 and 0x5678 it
answers 0x0C4C, which is their product as signed fixed point with fifteen
fractional bits. A protocol reading that produces the right answer to a
calculation nobody told it about is a protocol reading that is correct.
"""

from typing import Any, override

import hardware

DATA = 0x3F8000
"""An even address in the window the part answers across, which is its data port.

The lowest bit picks the port and nothing above it matters, so which of the
sixteen banks is used does not matter to the part and does not matter here.
"""

MODEL = "dsp1"

IDLE_WORD = 0x8080
"""What the data port reads when the part has nothing more to say.

A result shorter than the read is padded with this, so a run of it is what marks
the end of an answer and, one word further on, the end of the command.
"""

MOST_WORDS = 12
"""How many words a command is offered before it is called unanswerable.

The longest command that does answer takes eleven, so this leaves one word of
margin. A command still silent after twelve is not a command.
"""

WORD_BITS = 16

PROBE = 0x1234

CARTRIDGE_BUDGET = 96 * 1024 * 1024 // 8
"""The largest image this project is willing to build, in bytes.

Ninety six megabits is the ceiling a flash cartridge in common use will hold and
the size the sibling project settled on for the same reason.
"""

GAME_BYTES = 524288
"""What the retail cartridge occupies, which the image has to keep holding."""


def free(budget: int = CARTRIDGE_BUDGET) -> int:
    """What is left for tables once the game is in the image."""
    return budget - GAME_BYTES


def kernel_bytes(out: int = 1) -> int:
    """One table covering every value of a single sixteen bit input."""
    return bytes_for(1, out)


def kernel_tables(budget: int = CARTRIDGE_BUDGET, out: int = 1) -> int:
    """How many such tables the image has room for.

    This is the number that decides what growing the image buys. A command whose
    answers cannot be stored is still computed from scalar functions of one
    argument, and each of those is a table of this size. The count below is how
    many of them the ceiling allows, which is what makes the arithmetic in a
    replacement an indexed read rather than a series.
    """
    return free(budget) // kernel_bytes(out)


class Shape:
    """What one command byte takes and gives."""

    __slots__ = ("command", "reads", "writes")

    def __init__(self, command: int, writes: int | None, reads: int) -> None:
        self.command = command
        self.writes = writes
        self.reads = reads

    @property
    def answers(self) -> bool:
        return self.writes is not None

    @override
    def __repr__(self) -> str:
        if not self.answers:
            return f"<Shape ${self.command:02X} answers nothing>"
        return f"<Shape ${self.command:02X} {self.writes} in, {self.reads} out>"


def entries_for(words: int) -> int:
    """How many rows a table covering every input of that width would need."""
    return 1 << (WORD_BITS * words)


def bytes_for(words: int, out: int = 1) -> int:
    return entries_for(words) * out * 2


def storable(words: int, out: int = 1, budget: int = CARTRIDGE_BUDGET) -> bool:
    """Whether every answer of that input width fits, with room left for the game.

    Room for the game is the point of the qualifier: a table filling the whole
    budget leaves nothing to hold the cartridge it was built for, so half the
    budget is the most a single table may claim.
    """
    return bytes_for(words, out) <= budget // 2


def chip(model: str = MODEL) -> Any:
    return hardware.load("snesdsp").Chip(model)


def _read_words(part: Any, count: int) -> list[int]:
    out = []
    for _ in range(count):
        low = part.read_bus(DATA)
        high = part.read_bus(DATA)
        out.append(low | (high << 8))
    return out


def _offered(command: int, words: int, word: int, model: str) -> list[int]:
    """What the part gives back after being written that many argument words."""
    part = chip(model)
    part.write_bus(DATA, command)
    for _ in range(words):
        part.write_bus(DATA, word & 0xFF)
        part.write_bus(DATA, (word >> 8) & 0xFF)
    return _read_words(part, MOST_WORDS)


def _idle(given: list[int]) -> bool:
    return all(one == IDLE_WORD for one in given)


def shape_of(command: int, word: int = PROBE, model: str = MODEL) -> Shape:
    """How many words this command takes, and how many it gives back.

    A command written one word short of what it wants still has something in its
    output, because the part echoes what it was given. Written one word past what
    it wants, it has nothing: the run has been consumed and the port answers idle
    from the first read. So the count is found by looking for that silence and
    stepping back one, rather than by asking the status register, which settles a
    word later than the answer appears.

    The reading is checked against arithmetic nobody told it about. Command 0x00
    written two words of 0x1234 answers 0x0296, which is that value squared as
    signed fixed point with fifteen fractional bits.
    """
    for written in range(1, MOST_WORDS + 1):
        if _idle(_offered(command, written, word, model)):
            if written == 1:
                return Shape(command, None, 0)
            given = _offered(command, written - 1, word, model)
            return Shape(command, written - 1, sum(1 for one in given if one != IDLE_WORD))
    return Shape(command, None, 0)


def ask(command: int, words: tuple[int, ...], reads: int = 1, model: str = MODEL) -> bytes:
    """One exchange with a part built fresh for it.

    Fresh, because several of these commands leave state behind that a later one
    reads. Reusing a part would measure the order the questions were asked in
    rather than the command being asked about.
    """
    part = chip(model)
    part.write_bus(DATA, command)
    for word in words:
        part.write_bus(DATA, word & 0xFF)
        part.write_bus(DATA, (word >> 8) & 0xFF)
    return bytes(part.read_bus(DATA) for _ in range(reads * 2))


def deterministic(command: int = 0x00, model: str = MODEL) -> bool:
    """Whether two parts built fresh answer one question identically."""
    return ask(command, (PROBE, PROBE), model=model) == ask(command, (PROBE, PROBE), model=model)


def sweep(model: str = MODEL) -> tuple[Shape, ...]:
    """Every command byte, measured the same way."""
    return tuple(shape_of(command, model=model) for command in range(256))
