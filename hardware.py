"""Put the hardware models this project is checked against on the import path.

Each model is its own repository, pinned here as a submodule at the root, so the
thing this project is measured against is itself measured: the processor against
a per-opcode suite, the coprocessor against its own microcode, the cartridge map
and the image handling against a library of real cartridges, and the driver
against the cartridges it reads.

Two consequences change what code here must do.

The models start unclean. Their memory and registers hold arbitrary but
reproducible values rather than zeroes, because hardware does. Anything here that
wants a cleared machine asks for one, and asking is the point: a read of
something never written stops looking deliberate.

And nothing is loaded by file path. `load()` returns a model by the name it is
published under, which reads the same at the top of a module as a file-path
helper and does not need an import moved below a statement to work.

There is no graphics model here, unlike the sibling project that converts
bitmaps. The part this project replaces computes numbers and returns numbers; it
never touches a tile, so a model of the console's tile format would be a
dependency with nothing to answer.
"""

import importlib
import os
import sys
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

FIRMWARE = ROOT / "firmware"

FIRMWARE_VARIABLE = "UPD7725_FIRMWARE_DIR"

PACKAGES = {
    "mos65xx": "mos65xx-python",
    "snesdsp": "snes-dsp-python",
    "mapper": "snes-mapper-python",
    "romimage": "snes-rom-image-python",
    "snesdriver": "snes-driver-python",
}
"""The package each submodule provides, and the directory it lives in.

The directories sit at the root of this repository under the names of the
repositories they are, rather than under a folder that hides them. Anybody who
opens this project sees what it is built on without going looking, which is the
point: each of those is a project in its own right, held to its own oracle.
"""


class UnknownPackage(Exception):
    pass


def root_of(package: str) -> Path:
    """Where a vendored model lives, by the name it is imported under."""
    directory = PACKAGES.get(package)
    if directory is None:
        raise UnknownPackage(
            f"{package} is not vendored here; this project carries {', '.join(sorted(PACKAGES))}"
        )
    return ROOT / directory


def install(environment: MutableMapping[str, str] | None = None) -> str:
    """Make every vendored model importable, and say where the microcode is.

    The coprocessor model runs the part's own microcode, which belongs to whoever
    made the part and is never carried in any of these repositories. It looks in
    the directories that variable names, then beside itself. Neither reaches a
    project two levels up, so this points it at the one this project keeps, and
    adds to whatever was already named rather than replacing it: somebody who set
    the variable meant it.
    """
    for package in PACKAGES:
        entry = str(root_of(package))
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return name_firmware(environment)


def name_firmware(environment: MutableMapping[str, str] | None = None) -> str:
    """Put this project's firmware directory in front of whatever was named."""
    where = environment if environment is not None else os.environ
    already = [one for one in where.get(FIRMWARE_VARIABLE, "").split(os.pathsep) if one]
    if str(FIRMWARE) in already:
        return where[FIRMWARE_VARIABLE]
    where[FIRMWARE_VARIABLE] = os.pathsep.join([str(FIRMWARE), *already])
    return where[FIRMWARE_VARIABLE]


def load(package: str) -> Any:
    """A model, by the name it is published under."""
    root_of(package)
    install()
    return importlib.import_module(package)
