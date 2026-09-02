"""Which command bytes the cartridge's own code can issue, read out of the image.

A recording says which commands the game did send on one run. This asks the other
question, which is the one that bounds a replacement: which commands are written
down in the cartridge at all. The two answer differently and neither contains the
other, so both are taken.

Finding the places is the part that had been done too narrowly. The driver model
searches for an absolute long access, which carries its own bank and so can be
matched exactly on four bytes. That is sound and it is a minority of this
cartridge's traffic: the hot paths set the data bank once with `pea $003f` and
`plb`, then reach the part with ordinary absolute stores, which spell two bytes
and carry no bank. Measured against a recording, the long form is about three in
five writes and one in thirty reads, so a census taken from it alone is not a
census of the driver.

Reading the value is the other part. A command byte is an eight bit store of a
constant, and the constant is not always in the instruction: the cartridge loads
it into Y once and then issues `sty $8000` on every pass of a loop, so a search
for an immediate directly in front of a store misses those sites entirely. The
value is therefore carried forward from wherever the register was last loaded.

Nothing here executes. A 65816 image cannot be decoded backwards, so each store
is approached by decoding forwards from every origin in a window in front of it
and keeping the origins whose decode lands exactly on it. Origins that disagree
leave a site undetermined rather than answered, and a site no origin reaches is
reported as that. Both are what a coincidence in data looks like, which is the
other thing this has to survive: a search by encoding cannot tell an instruction
from two bytes of graphics that spell one.
"""

from typing import Any, override

DATA_PORT = 0x8000
"""The address the cartridge reaches the part's data port at.

This one and no mirror. The part answers across the whole of `$8000` to `$bfff`,
so an image holds many addresses that would reach it, and the driver uses exactly
one. An address in the range that is not this one is data that happens to spell
an access, and dropping those is most of what separates the two.
"""

DATA_BANK = 0x3F
"""The bank the long form of the access names."""

LONG_STORE = 0x8F

ABSOLUTE_STORES = {0x8D: "sta", 0x8E: "stx", 0x8C: "sty", 0x9C: "stz"}

IMMEDIATE_LOADS = {0xA9: "a", 0xA2: "x", 0xA0: "y"}

WRITES = {"sta": "a", "stx": "x", "sty": "y", "stz": None}
"""Which register each store takes its value from, and that `stz` takes none."""

ACCUMULATOR = 0x20

INDEX = 0x10

LOOKBACK = 512
"""How far in front of a store an origin may begin.

Measured rather than chosen. A routine here sets its register widths once with a
`sep` at its entry and then issues `sty $8000` throughout, so the instruction that
decides whether a store is eight bits wide sits as much as 450 bytes in front of
it. At 160 the search was silent on nine of the thirty sites a recording
confirmed; at 512 it is silent on one. Past that it buys nothing and costs: 640
reads the same commands and raises the number of stores whose origins disagree
from eight to eleven, because a wider window admits more decodes that were never
instructions.

The work is quadratic in this, so it is a real cost rather than a free margin.
"""

SPOILS = {
    "a": frozenset(
        {
            "lda",
            "adc",
            "sbc",
            "and",
            "ora",
            "eor",
            "asl",
            "lsr",
            "rol",
            "ror",
            "inc",
            "dec",
            "pla",
            "tax",
            "txa",
            "tya",
            "tay",
            "tsc",
            "tdc",
            "xba",
            "tsb",
            "trb",
            "mvn",
            "mvp",
            "jsr",
            "jsl",
            "plb",
            "plp",
            "rtl",
            "rts",
        }
    ),
    "x": frozenset(
        {"ldx", "inx", "dex", "tax", "tsx", "tyx", "plx", "mvn", "mvp", "jsr", "jsl", "plp"}
    ),
    "y": frozenset({"ldy", "iny", "dey", "tay", "txy", "ply", "mvn", "mvp", "jsr", "jsl", "plp"}),
}
"""Which instructions leave a register holding something other than a constant.

Generous on purpose. A register this cannot follow is reported as out of reach,
and a register it wrongly believes it can follow would be reported as a command
the cartridge does not issue, which is the worse of the two.
"""

DISAGREE = "origins disagree"

UNREACHED = "nothing that decodes onto it reaches it"

ARGUMENT = "a sixteen bit store, so an argument word"

MID_EXCHANGE = "another store reached the port first, so an argument word"

OUT_OF_REACH = "an eight bit store whose value is set further back than this looks"

CONSTANT = "an eight bit store of a constant"


class Site:
    """One store to the data port, and what is known about what it issues."""

    __slots__ = ("command", "narrow", "offset", "size", "text", "why")

    def __init__(
        self,
        offset: int,
        text: str,
        size: int,
        narrow: bool | None,
        command: int | None,
        why: str,
    ) -> None:
        self.offset = offset
        self.text = text
        self.size = size
        self.narrow = narrow
        self.command = command
        self.why = why

    @property
    def issues(self) -> bool:
        """Whether this store puts a command byte the image names into the part."""
        return self.command is not None

    @override
    def __repr__(self) -> str:
        what = f"${self.command:02x}" if self.command is not None else self.why
        return f"<Site ${self.offset:05x} {self.text} {what}>"


def store_at(rom: bytes, at: int) -> tuple[str, int] | None:
    """The store to the data port that starts here, or nothing if none does."""
    if rom[at : at + 1] == bytes([LONG_STORE]):
        if rom[at + 1 : at + 4] == bytes([DATA_PORT & 0xFF, DATA_PORT >> 8, DATA_BANK]):
            return "sta", 4
        return None
    mnemonic = ABSOLUTE_STORES.get(rom[at]) if at < len(rom) else None
    if mnemonic is None:
        return None
    if rom[at + 1 : at + 3] != bytes([DATA_PORT & 0xFF, DATA_PORT >> 8]):
        return None
    return mnemonic, 3


WRITING = "write"

READING = "read"

NOT_MEMORY = ("pea", "per")
"""Instructions carrying an address they never touch memory at."""

LEAVES = frozenset({"rts", "rtl", "rti", "jmp", "jml", "jsr", "jsl", "bra", "brl", "plb"})
"""Instructions after which a straight decode is no longer following one exchange.

A store is an argument word rather than a command when another store reached the
port first, and that only holds inside one run of straight code. This cartridge
issues a command, writes its arguments, and then yields through
`jmp ($0000,x)`, so the answer is collected by a different routine and a linear
decode never meets the read that ends the exchange. Without this, the write that
opens the next routine reads as an argument of the last one, and six of the
commands a recording confirmed went unreported. `plb` is here for the same
reason from the other end: it is how a routine here takes the data bank, so it
marks the start of one rather than the middle.
"""


def at_port(one: Any) -> str | None:
    """Which way an instruction reaches the data port, or nothing if it misses it.

    Both forms again, and the same reason: an image that reaches the part with
    ordinary absolute accesses is invisible to a reader that only knows the long
    one.
    """
    if one.operand is None or one.mnemonic in NOT_MEMORY:
        return None
    if one.mode == "absoluteLong":
        if one.operand != (DATA_BANK << 16) | DATA_PORT:
            return None
    elif one.mode == "absolute":
        if one.operand != DATA_PORT:
            return None
    else:
        return None
    return WRITING if one.mnemonic in ABSOLUTE_STORES.values() else READING


def stores(rom: bytes) -> tuple[int, ...]:
    """Every offset whose bytes spell a store to the data port, in either form.

    A search by encoding, so it reports data that happens to spell one. `read` is
    what separates those, by asking whether anything decodes onto them.
    """
    return tuple(at for at in range(len(rom)) if store_at(rom, at) is not None)


STATUS_PORT = 0xC000
"""Where the part's ready bit answers, on the same board and the same banks."""

DATA = "data"

STATUS = "status"

ABSOLUTE_READS = {
    0xAD: "lda",
    0xAE: "ldx",
    0xAC: "ldy",
    0x6D: "adc",
    0xED: "sbc",
    0x2D: "and",
    0x0D: "ora",
    0x4D: "eor",
    0xCD: "cmp",
    0x2C: "bit",
}
"""Every absolute instruction this driver takes a value from the part with.

A read is not only a load here. The cartridge collects an answer straight into
an accumulate with `adc $8000`, tests the ready bit with `bit $c000`, and steps
an index with `ldx $8000`, so a search for loads alone finds a fraction of the
read side. These are the ten the recording exercised plus the arithmetic and
logical forms that share the encoding, which cost nothing to accept and would
otherwise be a hole exactly like the one absolute addressing already was.
"""

LONG_READS = {
    0xAF: "lda",
    0x6F: "adc",
    0xEF: "sbc",
    0x2F: "and",
    0x0F: "ora",
    0x4F: "eor",
    0xCF: "cmp",
}
"""The same instructions in the form that spells its own bank.

There is no long `ldx`, `ldy` or `bit`, which is why the absolute table is longer
than this one rather than a mirror of it.
"""

PORTS = {DATA_PORT: DATA, STATUS_PORT: STATUS}


class Access:
    """One instruction that reaches the part, and which way it goes."""

    __slots__ = ("mnemonic", "offset", "register", "size", "way")

    def __init__(self, offset: int, mnemonic: str, size: int, register: str, way: str) -> None:
        self.offset = offset
        self.mnemonic = mnemonic
        self.size = size
        self.register = register
        self.way = way

    @property
    def long(self) -> bool:
        """Whether the instruction spelled the bank it reached."""
        return self.size == 4

    @override
    def __repr__(self) -> str:
        form = "long" if self.long else "absolute"
        return f"<Access ${self.offset:05x} {self.mnemonic} {self.register} {self.way} {form}>"


def access_at(rom: bytes, at: int) -> Access | None:
    """The access to either of the part's registers that starts here.

    Reads and writes, both addressing forms, both registers. `store_at` answers
    the narrower question the command reading needs; this one answers what a
    replacement needs, which is every instruction it has to stand in for.
    """
    if at >= len(rom):
        return None
    opcode = rom[at]
    long_form = opcode == LONG_STORE or opcode in LONG_READS
    size = 4 if long_form else 3
    if at + size > len(rom):
        return None
    if long_form and rom[at + 3] != DATA_BANK:
        return None
    register = PORTS.get(rom[at + 1] | rom[at + 2] << 8)
    if register is None:
        return None
    if opcode == LONG_STORE:
        return Access(at, "sta", 4, register, WRITING)
    if opcode in LONG_READS:
        return Access(at, LONG_READS[opcode], 4, register, READING)
    if opcode in ABSOLUTE_STORES:
        return Access(at, ABSOLUTE_STORES[opcode], 3, register, WRITING)
    if opcode in ABSOLUTE_READS:
        return Access(at, ABSOLUTE_READS[opcode], 3, register, READING)
    return None


def accesses(rom: bytes) -> tuple[Access, ...]:
    """Every offset whose bytes spell an access to either register.

    A search by encoding again, with the same caveat: an image holds bytes that
    spell one without ever being run as one. What separates those is the same
    thing that separates them for a store, which is whether a decode reaches it.
    """
    found = (access_at(rom, at) for at in range(len(rom)))
    return tuple(one for one in found if one is not None)


class _Decode:
    """What one forward decode knows by the time it lands on a store."""

    __slots__ = ("held", "known", "narrow", "port")

    def __init__(self) -> None:
        self.narrow = {"a": True, "x": True}
        self.known = {"a": False, "x": False}
        self.held: dict[str, int | None] = {"a": None, "x": None, "y": None}
        self.port: str | None = None
        """Which way the last access to the data port went, before this store.

        The part takes a command byte only while it is waiting for one, and it
        stops waiting the moment one arrives. So a store whose nearest
        predecessor at the port is another store is an argument word, whatever
        it happens to hold. Without this the search reads the second byte of
        every two byte argument pair as a command: the European image writes
        `sta $8000` with the command and then `stx $8000` with an argument, and
        X held a constant, so `$72` was reported as a command that image issues.
        """

    def widths_of(self, register: str | None) -> str:
        return "a" if register in (None, "a") else "x"

    def step(self, one: Any) -> None:
        reached = at_port(one)
        if reached is not None:
            self.port = reached
        elif one.mnemonic in LEAVES:
            self.port = None
        if one.mnemonic in ("sep", "rep") and one.operand is not None:
            narrow = one.mnemonic == "sep"
            if one.operand & ACCUMULATOR:
                self.narrow["a"] = narrow
                self.known["a"] = True
            if one.operand & INDEX:
                self.narrow["x"] = narrow
                self.known["x"] = True
            return
        register = IMMEDIATE_LOADS.get(one.opcode)
        if register is not None and one.mode.startswith("immediate"):
            self.held[register] = one.operand
            return
        for name, spoiled in SPOILS.items():
            if one.mnemonic in spoiled:
                self.held[name] = None

    def reading(self, register: str | None) -> tuple[bool | None, int | None, str | None]:
        """The width, the value and the last port access this decode can vouch for."""
        flag = self.widths_of(register)
        narrow = self.narrow[flag] if self.known[flag] else None
        value = 0 if register is None else self.held[register]
        return narrow, value, self.port


def _land(rom: bytes, disassemble: Any, origin: int, target: int) -> _Decode | None:
    """Decode forward from an origin, and return it only if it lands on the target."""
    found = _Decode()
    at = origin
    while at < target:
        read = disassemble(
            rom, at, 0x8000 + at % 0x8000, count=1, m=found.narrow["a"], x=found.narrow["x"]
        )
        if not read:
            return None
        one = read[0]
        found.step(one)
        at += one.size
    return found if at == target else None


def _readings(
    rom: bytes, disassemble: Any, at: int, register: str | None
) -> list[tuple[bool | None, int | None, str | None]]:
    said = []
    for back in range(1, LOOKBACK + 1):
        if at - back < 0:
            break
        landed = _land(rom, disassemble, at - back, at)
        if landed is not None:
            said.append(landed.reading(register))
    return said


def read(rom: bytes, disassemble: Any) -> tuple[Site, ...]:
    """Every store to the data port, with the command byte it issues where known.

    `disassemble` is handed in rather than reached for, so this module states what
    it needs and a caller decides which model answers for the processor.
    """
    found = []
    for at in stores(rom):
        store = store_at(rom, at)
        assert store is not None
        mnemonic, size = store
        named = f"${DATA_BANK:02x}{DATA_PORT:04x}" if size == 4 else f"${DATA_PORT:04x}"
        register = WRITES[mnemonic]
        said = _readings(rom, disassemble, at, register)
        widths = {narrow for narrow, _, _ in said if narrow is not None}
        values = {value for _, value, _ in said if value is not None}
        after = {port for _, _, port in said if port is not None}
        text = f"{mnemonic} {named}"
        if len(widths) > 1 or len(values) > 1 or len(after) > 1:
            found.append(Site(at, text, size, None, None, DISAGREE))
        elif WRITING in after:
            found.append(Site(at, text, size, None, None, MID_EXCHANGE))
        elif not widths:
            found.append(Site(at, text, size, None, None, UNREACHED))
        elif not next(iter(widths)):
            found.append(Site(at, text, size, False, None, ARGUMENT))
        elif not values:
            found.append(Site(at, text, size, True, None, OUT_OF_REACH))
        else:
            found.append(Site(at, text, size, True, next(iter(values)), CONSTANT))
    return tuple(found)


def commands(sites: tuple[Site, ...]) -> tuple[int, ...]:
    """Every distinct command byte those sites issue."""
    return tuple(sorted({one.command for one in sites if one.command is not None}))
