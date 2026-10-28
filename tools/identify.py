import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

import dumps  # noqa: E402

STATE_OK = "ok"
STATE_ABSENT = "absent"
STATE_WRONG = "wrong"


class Looked:
    __slots__ = ("detail", "filename", "region", "state")

    def __init__(self, region: str, filename: str, state: str, detail: str) -> None:
        self.region = region
        self.filename = filename
        self.state = state
        self.detail = detail

    @property
    def ok(self) -> bool:
        return self.state in (STATE_OK, STATE_ABSENT)

    @override
    def __repr__(self) -> str:
        return f"<Looked {self.region} {self.state}>"


def judge(one: Any, data: bytes, digest: str | None = None) -> Looked:
    said = dumps.diagnose(data, digest=digest)
    if said.kind == "match" and one.region in said.detail:
        return Looked(one.region, one.filename, STATE_OK, said.detail)
    if said.kind == "match":
        return Looked(
            one.region,
            one.filename,
            STATE_WRONG,
            f"this is {said.detail}, which is a different region under this name",
        )
    return Looked(one.region, one.filename, STATE_WRONG, said.detail)


def look(one: Any, root: Path | str = ROOT) -> Looked:
    where = Path(root) / "external" / "roms" / one.filename
    if not where.is_file():
        return Looked(one.region, one.filename, STATE_ABSENT, "not on this machine")
    return judge(one, where.read_bytes())


def report(root: Path | str = ROOT) -> list[str]:
    lines = [f"cartridge dumps, checked against {dumps.MANIFEST.name}", ""]
    for one in dumps.artifacts():
        found = look(one, root)
        mark = "ok  " if found.state == STATE_OK else ("    " if found.ok else "   !")
        lines.append(f"  {mark}  {found.region} / {found.filename}: {found.detail}")
    lines.append("")
    lines.append(f"  {dumps.DECIDES} is what decides. Work one out yourself with:")
    for system, command in dumps.digest_commands(
        f"external/roms/{dumps.artifacts()[0].filename}"
    ).items():
        lines.append(f"    {system:8s} {command}")
    return lines


def main(
    argv: tuple[str, ...] | list[str] = (),
    root: Path | str = ROOT,
    say: Callable[[str], None] = print,
) -> int:
    found = [look(one, root) for one in dumps.artifacts()]
    for line in report(root):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
