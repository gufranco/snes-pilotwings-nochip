"""Whether the replacement fits in the image the cartridge already is.

This project was built expecting to grow the image, up to the 96 Mbit a flash
cartridge in common use holds, because a table per scalar function over a whole
sixteen bit input is 131,072 bytes and five of those do not fit in 512 KB. That
expectation was wrong at its root: the part interpolates from four small tables
totalling 1,282 bytes, per `tables.py`, so the question is no longer how much to
grow by but whether anything has to grow at all.

Growing is not free. An image past the address space needs the windowed layout
the sibling project uses, which is a real piece of work and changes which
emulators load the result. So this measures the other side: how much of the
retail image is filler the cartridge does not use, in runs long enough to put
something in.

A run of one repeated byte is not proof that nothing reads it. It is evidence,
and it is the same evidence every patch of this kind has ever run on, so what
this reports is where to look rather than where it is safe to write. A candidate
run is checked against the driver census before anything is put in it.
"""

from pathlib import Path
from typing import Any

FILLERS = (0xFF, 0x00)
"""The two bytes an unused stretch of a mask ROM is left as.

`$ff` is an erased part and `$00` is a zeroed one, and this cartridge holds long
runs of both. Anything else repeating is data with a meaning.
"""

LEAST = 256
"""How long a run has to be before it is worth reporting.

Short enough to hold a routine, long enough that a run of repeated bytes inside
real data does not read as free space. Below this the count fills with fragments
nothing can be put in.
"""


def runs(
    rom: bytes, least: int = LEAST, fillers: tuple[int, ...] = FILLERS
) -> tuple[tuple[int, int], ...]:
    """Every stretch of one repeated filler byte at least that long."""
    found: list[tuple[int, int]] = []
    for filler in fillers:
        start: int | None = None
        for at in range(len(rom) + 1):
            if at < len(rom) and rom[at] == filler:
                start = at if start is None else start
                continue
            if start is not None and at - start >= least:
                found.append((start, at))
            start = None
    return tuple(sorted(found))


def free(rom: bytes, least: int = LEAST) -> int:
    """How many bytes those runs come to."""
    return sum(end - start for start, end in runs(rom, least))


def largest(rom: bytes, least: int = LEAST) -> int:
    """The longest single run, which is what a blob kept whole has to fit in."""
    found = runs(rom, least)
    return max((end - start for start, end in found), default=0)


def fits(rom: bytes, wanted: int, least: int = LEAST) -> bool:
    """Whether that many bytes fit in one run, so a blob can stay contiguous."""
    return largest(rom, least) >= wanted


def spread(rom: bytes, wanted: int, least: int = LEAST) -> bool:
    """Whether that many bytes fit at all, across as many runs as it takes."""
    return free(rom, least) >= wanted


def must_grow(rom: bytes, wanted: int, least: int = LEAST) -> bool:
    """Whether the image has to get bigger to hold that much."""
    return not spread(rom, wanted, least)


def report(rom: bytes, wanted: int, least: int = LEAST) -> list[str]:
    found = runs(rom, least)
    lines = [
        f"  {len(rom):,} bytes of image, {free(rom, least):,} free"
        f" in {len(found)} runs of {least} bytes or more",
        f"  largest run {largest(rom, least):,} bytes",
        f"  wanted {wanted:,} bytes",
        "",
    ]
    if must_grow(rom, wanted, least):
        lines.append("  the image has to grow to hold it")
        return lines
    whole = "in one piece" if fits(rom, wanted, least) else "across more than one run"
    lines.append(f"  the image does not have to grow, and holds it {whole}")
    lines.append("")
    lines.append("  the longest runs:")
    for start, end in sorted(found, key=lambda one: one[0] - one[1])[:8]:
        lines.append(f"    ${start:06x}..${end - 1:06x}  {end - start:,} bytes")
    return lines


def main(argv: tuple[str, ...] | list[str] = (), say: Any = print) -> int:
    if len(argv) < 2:
        say("usage: layout.py <image> <bytes wanted>")
        return 2
    for line in report(Path(argv[0]).read_bytes(), int(argv[1])):
        say(line)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
