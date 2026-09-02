"""Which cartridge dumps this project reads, and what makes each one itself.

The manifest beside this module is the record; nothing here hardcodes a digest.
Identification is by SHA-256 and by nothing else, and this project has a
concrete reason rather than a general preference: a Nintendo Campus Challenge
cartridge built on this game is the same length, declares the same chipset and
carries the same internal title, so a check on any of those three accepts it as
a retail dump.

A mismatch is triaged rather than reported as a bare refusal. A person holding
the wrong file wants to know which way it is wrong, and the three answers worth
separating are a copier header in front of the right bytes, a file of the wrong
length, and the right length with content nothing declares.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent

MANIFEST = ROOT / "artifacts.manifest.json"

CARTRIDGE_BYTES = 524288

COPIER_BYTES = 512
"""What a copier writes in front of the bytes a cartridge actually holds.

The dump underneath is identical, so this is a repair rather than a rejection:
the file is the right one wearing something a tool added.
"""

DECIDES = "sha256"


class Artifact:
    __slots__ = ("accepted", "declares", "filename", "name", "provenance", "region")

    def __init__(self, entry: dict[str, Any]) -> None:
        self.name = entry["name"]
        self.region = entry["region"]
        self.filename = entry["filename"]
        self.declares = entry["declares"]
        self.accepted = entry["accepted"]
        self.provenance = entry["provenance"]

    @override
    def __repr__(self) -> str:
        return f"<Artifact {self.region}>"


class Finding:
    __slots__ = ("detail", "kind", "repair")

    def __init__(self, kind: str, detail: str, repair: str = "") -> None:
        self.kind = kind
        self.detail = detail
        self.repair = repair

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.kind}>"


def manifest() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(MANIFEST.read_text())
    return loaded


def artifacts() -> tuple[Artifact, ...]:
    return tuple(Artifact(one) for one in manifest()["artifacts"])


def through() -> tuple[dict[str, Any], ...]:
    """Artifacts this project needs that a sibling repository loads and pins."""
    return tuple(manifest()["through"])


def not_this() -> tuple[dict[str, Any], ...]:
    return tuple(manifest()["not_this"])


def identify_digest(digest: str) -> Artifact | None:
    for one in artifacts():
        for entry in one.accepted:
            if entry[DECIDES] == digest:
                return one
    return None


def identify(data: bytes, digest: str | None = None) -> Artifact | None:
    return identify_digest(hashlib.sha256(data).hexdigest() if digest is None else digest)


def digest_commands(filename: str) -> dict[str, str]:
    """How to compute the deciding digest, per operating system.

    A refusal that leaves somebody unable to check the file themselves has
    reported a problem and withheld the way to act on it.
    """
    return {
        "macOS": f"shasum -a 256 {filename}",
        "Linux": f"sha256sum {filename}",
        "Windows": f"certutil -hashfile {filename} SHA256",
    }


def diagnose(data: bytes, digest: str | None = None) -> Finding:
    found = identify(data, digest=digest)
    if found is not None:
        return Finding("match", f"{found.name}, region {found.region}")

    if len(data) == CARTRIDGE_BYTES + COPIER_BYTES:
        return Finding(
            "copier-header",
            f"the file is {COPIER_BYTES} bytes longer than a bare dump, which is what a copier adds",
            f"strip the first {COPIER_BYTES} bytes and check it again",
        )

    if len(data) != CARTRIDGE_BYTES:
        which = "smaller" if len(data) < CARTRIDGE_BYTES else "larger"
        return Finding(
            "wrong-size",
            f"{len(data):,} bytes, which is {which} than the {CARTRIDGE_BYTES:,} a dump holds",
            "check that the file is a whole cartridge and not an archive or a fragment",
        )

    computed = hashlib.sha256(data).hexdigest()
    return Finding(
        "unrecognised",
        f"the right length, and its {DECIDES} is {computed}, which none of the "
        f"{len(artifacts())} declared dumps carries",
        "search that digest to find out what the file is",
    )
