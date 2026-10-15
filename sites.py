from typing import Any, override

import hardware

CARTRIDGE_BYTES = 524288

PART = "dsp"

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
    return driver().window_for(PART, LAYOUT)


def reached(rom: bytes) -> tuple[int, ...]:
    return tuple(driver().sites(rom, window()))


def census(rom: bytes) -> Census:
    found = reached(rom)
    if not found:
        return Census(0, {})
    return Census(len(found), dict(driver().shapes(rom, window())))
