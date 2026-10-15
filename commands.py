from typing import Any, override

DATA_PORT = 0x8000

DATA_BANK = 0x3F

LONG_STORE = 0x8F

ABSOLUTE_STORES = {0x8D: "sta", 0x8E: "stx", 0x8C: "sty", 0x9C: "stz"}

IMMEDIATE_LOADS = {0xA9: "a", 0xA2: "x", 0xA0: "y"}

WRITES = {"sta": "a", "stx": "x", "sty": "y", "stz": None}

ACCUMULATOR = 0x20

INDEX = 0x10

LOOKBACK = 512

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

DISAGREE = "origins disagree"

UNREACHED = "nothing that decodes onto it reaches it"

ARGUMENT = "a sixteen bit store, so an argument word"

MID_EXCHANGE = "another store reached the port first, so an argument word"

OUT_OF_REACH = "an eight bit store whose value is set further back than this looks"

CONSTANT = "an eight bit store of a constant"


class Site:
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
        return self.command is not None

    @override
    def __repr__(self) -> str:
        what = f"${self.command:02x}" if self.command is not None else self.why
        return f"<Site ${self.offset:05x} {self.text} {what}>"


def store_at(rom: bytes, at: int) -> tuple[str, int] | None:
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

LEAVES = frozenset({"rts", "rtl", "rti", "jmp", "jml", "jsr", "jsl", "bra", "brl", "plb"})


def at_port(one: Any) -> str | None:
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
    return tuple(at for at in range(len(rom)) if store_at(rom, at) is not None)


STATUS_PORT = 0xC000

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

LONG_READS = {
    0xAF: "lda",
    0x6F: "adc",
    0xEF: "sbc",
    0x2F: "and",
    0x0F: "ora",
    0x4F: "eor",
    0xCF: "cmp",
}

PORTS = {DATA_PORT: DATA, STATUS_PORT: STATUS}


class Access:
    __slots__ = ("mnemonic", "offset", "register", "size", "way")

    def __init__(self, offset: int, mnemonic: str, size: int, register: str, way: str) -> None:
        self.offset = offset
        self.mnemonic = mnemonic
        self.size = size
        self.register = register
        self.way = way

    @property
    def long(self) -> bool:
        return self.size == 4

    @override
    def __repr__(self) -> str:
        form = "long" if self.long else "absolute"
        return f"<Access ${self.offset:05x} {self.mnemonic} {self.register} {self.way} {form}>"


def access_at(rom: bytes, at: int) -> Access | None:
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
    found = (access_at(rom, at) for at in range(len(rom)))
    return tuple(one for one in found if one is not None)


class _Decode:
    __slots__ = ("held", "known", "narrow", "port")

    def __init__(self) -> None:
        self.narrow = {"a": True, "x": True}
        self.known = {"a": False, "x": False}
        self.held: dict[str, int | None] = {"a": None, "x": None, "y": None}
        self.port: str | None = None

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
        flag = self.widths_of(register)
        narrow = self.narrow[flag] if self.known[flag] else None
        value = 0 if register is None else self.held[register]
        return narrow, value, self.port


def _land(rom: bytes, disassemble: Any, origin: int, target: int) -> _Decode | None:
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
    return tuple(sorted({one.command for one in sites if one.command is not None}))
