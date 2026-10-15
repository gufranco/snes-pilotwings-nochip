from pathlib import Path
from typing import Any

FILLERS = (0xFF, 0x00)

LEAST = 256


def runs(
    rom: bytes, least: int = LEAST, fillers: tuple[int, ...] = FILLERS
) -> tuple[tuple[int, int], ...]:
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
    return sum(end - start for start, end in runs(rom, least))


def largest(rom: bytes, least: int = LEAST) -> int:
    found = runs(rom, least)
    return max((end - start for start, end in found), default=0)


def fits(rom: bytes, wanted: int, least: int = LEAST) -> bool:
    return largest(rom, least) >= wanted


def spread(rom: bytes, wanted: int, least: int = LEAST) -> bool:
    return free(rom, least) >= wanted


def must_grow(rom: bytes, wanted: int, least: int = LEAST) -> bool:
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
