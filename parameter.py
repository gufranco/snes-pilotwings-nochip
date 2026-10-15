from collections.abc import Iterable, Mapping, Sequence

WORDS = 7

FIXED = {3: 32, 4: 256}

CELLS: Mapping[str, int] = {
    "step": 0x49,
    "horizon": 0xC8,
    "mantissa1": 0x4C,
    "exponent1": 0xCC,
    "mantissa2": 0x4B,
    "exponent2": 0xCB,
    "matrix0": 0x7F,
    "matrix1": 0x7E,
    "matrix2": 0x6F,
    "matrix3": 0x6E,
}

GROUPS: Mapping[str, tuple[tuple[int, ...], tuple[str, ...]]] = {
    "line": ((6,), ("step", "horizon", "exponent2")),
    "scale": ((2, 6), ("mantissa1", "exponent1", "mantissa2")),
    "matrix": ((5,), ("matrix0", "matrix1")),
}

BYTES_PER_WORD = 2


class Disagreement(Exception): ...


class NotMirrored(Exception): ...


def keyed(words: Sequence[int], slots: Sequence[int]) -> tuple[int, ...]:
    return tuple(words[slot] for slot in slots)


def fixed(runs: Iterable[Sequence[int]]) -> dict[int, int]:
    seen: dict[int, set[int]] = {}
    for words in runs:
        for slot, word in enumerate(words):
            seen.setdefault(slot, set()).add(word)
    return {slot: next(iter(vals)) for slot, vals in seen.items() if len(vals) == 1}


def mirrored(state: Mapping[str, int]) -> None:
    if state["matrix3"] != state["matrix0"] or state["matrix2"] != -state["matrix1"]:
        raise NotMirrored(
            f"matrix {tuple(state[f'matrix{k}'] for k in range(4))} is not two words twice,"
            " so storing two of them would lose the other two"
        )


def gathered(
    seen: Iterable[tuple[Sequence[int], Sequence[int]]], slots: Sequence[int]
) -> dict[tuple[int, ...], tuple[int, ...]]:
    rows: dict[tuple[int, ...], tuple[int, ...]] = {}
    for words, state in seen:
        key = keyed(words, slots)
        found = tuple(state)
        if key in rows and rows[key] != found:
            raise Disagreement(
                f"key {key} gives {rows[key]} and {found}, so slots {tuple(slots)} are not enough"
            )
        rows[key] = found
    return rows


def sized(rows: Mapping[tuple[int, ...], tuple[int, ...]]) -> int:
    return sum((len(key) + len(state)) * BYTES_PER_WORD for key, state in rows.items())
