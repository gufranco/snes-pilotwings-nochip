"""Where a cartridge reaches the coprocessor, read out of the cartridge's code.

Nothing here executes. Every answer is a question about instructions sitting in
the image, put to the driver model, which is held to a library of real
cartridges rather than to its author's reading of them.

A site is one instruction that touches the part's window. An exchange is the run
of them one routine performs, and the shape of an exchange, which accesses in
which order at which widths, is what a replacement has to reproduce. Two
cartridges that share a shape can share a replacement for it.
"""

from typing import Any, override

import hardware

CARTRIDGE_BYTES = 524288

PART = "dsp"
"""The name the driver model publishes this part's window under.

It is the window that is shared, not the program: the DSP-1 through DSP-4 are
one piece of silicon carrying four different masks, so they answer at the same
addresses on the same board while computing unrelated things.
"""

LAYOUT = "lorom"


class Census:
    __slots__ = ("shapes", "sites")

    def __init__(self, sites: int, shapes: dict[str, int]) -> None:
        self.sites = sites
        self.shapes = shapes

    @property
    def distinct(self) -> int:
        return len(self.shapes)

    @override
    def __repr__(self) -> str:
        return f"<Census {self.sites} sites, {self.distinct} shapes>"


def driver() -> Any:
    return hardware.load("snesdriver")


def window() -> Any:
    """Where the part answers on a board wired this way."""
    return driver().window_for(PART, LAYOUT)


def reached(rom: bytes) -> tuple[int, ...]:
    """Every instruction in the image that touches the part."""
    return tuple(driver().sites(rom, window()))


def census(rom: bytes) -> Census:
    """How many sites the image has, and every distinct exchange with its count."""
    found = reached(rom)
    if not found:
        return Census(0, {})
    return Census(len(found), dict(driver().shapes(rom, window())))
