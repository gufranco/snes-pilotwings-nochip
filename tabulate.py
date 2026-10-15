from typing import Any, override

import hardware

DATA = 0x3F8000

MODEL = "dsp1"

IDLE_WORD = 0x8080

MOST_WORDS = 12

WORD_BITS = 16

PROBE = 0x1234

CARTRIDGE_BUDGET = 96 * 1024 * 1024 // 8

GAME_BYTES = 524288


def free(budget: int = CARTRIDGE_BUDGET) -> int:
    return budget - GAME_BYTES


def kernel_bytes(out: int = 1) -> int:
    return bytes_for(1, out)


def kernel_tables(budget: int = CARTRIDGE_BUDGET, out: int = 1) -> int:
    return free(budget) // kernel_bytes(out)


class Shape:
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
    return 1 << (WORD_BITS * words)


def bytes_for(words: int, out: int = 1) -> int:
    return entries_for(words) * out * 2


def storable(words: int, out: int = 1, budget: int = CARTRIDGE_BUDGET) -> bool:
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
    part = chip(model)
    part.write_bus(DATA, command)
    for _ in range(words):
        part.write_bus(DATA, word & 0xFF)
        part.write_bus(DATA, (word >> 8) & 0xFF)
    return _read_words(part, MOST_WORDS)


def _idle(given: list[int]) -> bool:
    return all(one == IDLE_WORD for one in given)


def shape_of(command: int, word: int = PROBE, model: str = MODEL) -> Shape:
    for written in range(1, MOST_WORDS + 1):
        if _idle(_offered(command, written, word, model)):
            if written == 1:
                return Shape(command, None, 0)
            given = _offered(command, written - 1, word, model)
            return Shape(command, written - 1, sum(1 for one in given if one != IDLE_WORD))
    return Shape(command, None, 0)


def ask(command: int, words: tuple[int, ...], reads: int = 1, model: str = MODEL) -> bytes:
    part = chip(model)
    part.write_bus(DATA, command)
    for word in words:
        part.write_bus(DATA, word & 0xFF)
        part.write_bus(DATA, (word >> 8) & 0xFF)
    return bytes(part.read_bus(DATA) for _ in range(reads * 2))


def deterministic(command: int = 0x00, model: str = MODEL) -> bool:
    return ask(command, (PROBE, PROBE), model=model) == ask(command, (PROBE, PROBE), model=model)


def sweep(model: str = MODEL) -> tuple[Shape, ...]:
    return tuple(shape_of(command, model=model) for command in range(256))
