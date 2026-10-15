import struct
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import hardware

WHOLE = 0x10000

NORMAL_LOW = 0x4000
NORMAL_HIGH = 0x8000

RECIPROCAL_ENTRY = 0x0D3

SENTINEL = 0x7FF

RECIPROCAL_STEPS = 200

SINE_AND_COSINE = 0x04

STEPS = 3000

PROBES = (0x7FFF, 0x4000, 0x1234, 0x0100, 0x0007, 0x0001)

NUDGES = (0, 1, -1, 2, -2)


def signed(word: int) -> int:
    return word - 0x10000 if word >= 0x8000 else word


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


class Runaway(Exception): ...


def refined(part: Any, value: int) -> int:
    core = part.core
    core.registers.sp = 1
    core.registers.stack[0] = SENTINEL
    core.registers.a = value & 0xFFFF
    core.registers.b = 0
    core.registers.pc = RECIPROCAL_ENTRY
    for _ in range(RECIPROCAL_STEPS):
        core.step()
        if core.registers.pc == SENTINEL:
            return signed(core.registers.word("a"))
    raise Runaway(
        f"the reciprocal at ${RECIPROCAL_ENTRY:03x} did not return for ${value:04x}"
        f" within {RECIPROCAL_STEPS} instructions"
    )


def reciprocal(
    part: Any,
    low: int = NORMAL_LOW,
    high: int = NORMAL_HIGH,
    watch: Callable[[int], None] | None = None,
) -> tuple[int, ...]:
    found = []
    for value in range(low, high):
        found.append(refined(part, value))
        if watch is not None and (value - low) % 4096 == 0:
            watch(value - low)
    return tuple(found)


def trig(
    part: Any, count: int = WHOLE, watch: Callable[[int], None] | None = None
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    sine: list[int] = []
    cosine: list[int] = []
    for angle in range(count):
        wanted = {one: ask(part, SINE_AND_COSINE, (angle, one), 2) for one in PROBES}
        start = wanted[PROBES[0]]
        for half, into in ((0, sine), (1, cosine)):
            base = signed(start[half])
            for nudge in NUDGES:
                unit = base + nudge
                if all(
                    ((signed(one) * unit) >> 15) & 0xFFFF == wanted[one][half] for one in PROBES
                ):
                    into.append(unit)
                    break
            else:
                into.append(base)
        if watch is not None and angle % 4096 == 0:
            watch(angle)
    return tuple(sine), tuple(cosine)


BANK_BYTES = 0x8000


WHOLE_WORD = 0x10000


def leading(value: int) -> int:
    if value == 0:
        return 0
    count = 0
    now = value
    while True:
        doubled = (now << 1) & 0xFFFF
        if (now ^ doubled) & 0x8000:
            return count
        now = doubled
        count += 1


def counted() -> bytes:
    return bytes(leading(one) for one in range(WHOLE_WORD))


def write_bytes(where: Path | str, raw: bytes) -> int:
    stem = Path(where)
    for piece, at in enumerate(range(0, len(raw), BANK_BYTES)):
        stem.with_name(f"{stem.stem}-{piece}{stem.suffix}").write_bytes(raw[at : at + BANK_BYTES])
    return len(raw)


def write(where: Path | str, values: Sequence[int]) -> int:
    raw = b"".join(struct.pack("<H", one & 0xFFFF) for one in values)
    stem = Path(where)
    for piece, at in enumerate(range(0, len(raw), BANK_BYTES)):
        stem.with_name(f"{stem.stem}-{piece}{stem.suffix}").write_bytes(raw[at : at + BANK_BYTES])
    return len(raw)


def pieces(where: Path | str) -> tuple[int, ...]:
    stem = Path(where)
    raw = b""
    piece = 0
    while True:
        one = stem.with_name(f"{stem.stem}-{piece}{stem.suffix}")
        if not one.exists():
            break
        raw += one.read_bytes()
        piece += 1
    if not raw:
        raise FileNotFoundError(f"no pieces of {stem} on disk")
    return tuple(struct.unpack(f"<{len(raw) // 2}H", raw))


FOLDED = 0x8000

HORIZON_MANTISSA = 0x7FFF
HORIZON_EXPONENT = 0x002F

BIAS = 6


def doublings(folded: int) -> int:
    if folded == 0:
        return 15
    count = 0
    while folded < NORMAL_LOW:
        folded <<= 1
        count += 1
    return count


def inverted(mantissas: Sequence[int], negative: bool) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if len(mantissas) != NORMAL_HIGH - NORMAL_LOW:
        raise ValueError(
            f"a reciprocal table is {NORMAL_HIGH - NORMAL_LOW:,} entries, not {len(mantissas):,}"
        )
    mantissa: list[int] = []
    exponent: list[int] = []
    for folded in range(FOLDED):
        count = doublings(folded)
        if folded == 0 and not negative:
            mantissa.append(HORIZON_MANTISSA)
            exponent.append(HORIZON_EXPONENT)
            continue
        exponent.append(count - BIAS & 0xFFFF)
        magnitude = (folded + 1 if negative else folded) << count & 0xFFFF
        if magnitude >= NORMAL_HIGH or magnitude == 0:
            magnitude = NORMAL_HIGH - 1
        answer = mantissas[magnitude - NORMAL_LOW] & 0xFFFF
        mantissa.append(-answer & 0xFFFF if negative else answer)
    return tuple(mantissa), tuple(exponent)


def reindex(into: Path, values: Sequence[int], say: Any) -> None:
    for negative, stem in ((False, "recip-up"), (True, "recip-down")):
        mantissa, exponent = inverted(values, negative=negative)
        say(f"  wrote {write(into / f'{stem}.bin', mantissa):,} bytes")
        if not negative:
            continue
        say(f"  wrote {write(into / 'recip-exponent.bin', exponent):,} bytes")


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    rest = [one for one in argv if one != "--reindex"]
    again = len(rest) != len(list(argv))
    if not rest:
        say("usage: derived.py <mask> [<directory>] [--reindex], one of dsp1 or dsp1b")
        return 2
    into = Path(rest[1]) if len(rest) > 1 else Path("build")
    into.mkdir(exist_ok=True)

    if again:
        say(f"turning the reciprocal already in {into} inside out")
        reindex(into, pieces(into / "reciprocal.bin"), say)
        return 0

    part = hardware.load("snesdsp").Chip(rest[0])

    say(f"driving the {rest[0]} for {NORMAL_HIGH - NORMAL_LOW:,} reciprocals")
    values = reciprocal(part, NORMAL_LOW, NORMAL_HIGH, watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {write(into / 'reciprocal.bin', values):,} bytes")
    reindex(into, values, say)

    say(f"counting the doublings for all {WHOLE_WORD:,} words")
    say(f"  wrote {write_bytes(into / 'leading.bin', counted()):,} bytes")

    say(f"driving it for {WHOLE:,} angles, six magnitudes each")
    sine, cosine = trig(part, watch=lambda at: say(f"  {at:,}"))
    say(f"  wrote {write(into / 'sine.bin', sine):,} bytes")
    say(f"  wrote {write(into / 'cosine.bin', cosine):,} bytes")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
