from collections.abc import Iterable, Mapping, Sequence
from itertools import product
from pathlib import Path
from typing import Any

import exchanges
import hardware
import microcode

STEPS = 3000

REGIONS = ("usa", "jp", "eur")

CARRIER = {0x13: 0x11}

CARRIER_WORDS = {0x13: 4}

COMPLETE = (0x13, 0x18)


def ask(part: Any, command: int, words: Sequence[int], answers: int) -> tuple[int, ...]:
    part.write(command)
    for one in words:
        part.write(one & 0xFF)
        part.write(one >> 8)
    got: list[int] = []
    for _ in range(STEPS):
        part.step(16)
        if part.asking:
            got.append(part.read())
            if len(got) >= answers * 2:
                break
    return tuple(got[k] | got[k + 1] << 8 for k in range(0, len(got) - 1, 2))


def domains(runs: Iterable[Sequence[Any]]) -> dict[int, tuple[tuple[int, ...], ...]]:
    seen: dict[int, dict[int, set[int]]] = {}
    for run in runs:
        last: dict[int, tuple[int, ...]] = {}
        for one in run:
            if one.answer and one.command in COMPLETE:
                held = last.get(CARRIER[one.command], ()) if one.command in CARRIER else ()
                for at, word in enumerate((*one.words, *held)):
                    seen.setdefault(one.command, {}).setdefault(at, set()).add(word)
            last[one.command] = one.words
    return {
        command: tuple(tuple(sorted(words[at])) for at in sorted(words))
        for command, words in seen.items()
    }


def wanted(values: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(product(*values))


def filled(
    command: int,
    keys: Sequence[tuple[int, ...]],
    answers: int,
    have: Mapping[tuple[int, ...], tuple[int, ...]],
    mask: str = microcode.MASK,
    say: Any = None,
) -> dict[tuple[int, ...], tuple[int, ...]]:
    own = len(keys[0]) - CARRIER_WORDS.get(command, 0)
    out = dict(have)
    part = hardware.load("snesdsp").Chip(mask)
    carrier = CARRIER.get(command)
    for at, key in enumerate(keys):
        if key in out:
            continue
        if carrier is not None:
            ask(part, carrier, key[own:], 0)
        out[key] = ask(part, command, key[:own], answers)
        if say is not None and at % 200 == 0:
            say(f"  ${command:02x} {at:,} of {len(keys):,}")
    return out


def gather(where: Path = Path("build")) -> tuple[Sequence[Any], ...]:
    return tuple(exchanges.taken((where / f"trace-{one}.bin").read_bytes()) for one in REGIONS)


def report(found: Mapping[int, tuple[int, int]]) -> list[str]:
    lines = ["  cmd    recorded    complete   filled in"]
    for command in sorted(found):
        recorded, whole = found[command]
        lines.append(f"  ${command:02x}  {recorded:10,}  {whole:10,}  {whole - recorded:10,}")
    return lines
