from collections.abc import Mapping, Sequence

CELLS: Mapping[str, int] = {
    "row0col0": 0x5A,
    "row0col1": 0x5B,
    "row0col2": 0x5C,
    "row1col0": 0x6A,
    "row1col1": 0x6B,
    "row1col2": 0x6C,
    "row2col0": 0x7A,
    "row2col1": 0x7B,
    "row2col2": 0x7C,
}

ONE = 0x7FFF

HALF_TURN = 0x8000

HALF_TURN_COSINE = 0x8000

ANGLES = (5, 6)


def signed(word: int) -> int:
    return word - 0x10000 if word & 0x8000 else word


def product(one: int, two: int) -> int:
    return ((one * two) >> 15) & 0xFFFF


def cosine_of(table: Sequence[int], angle: int) -> int:
    return HALF_TURN_COSINE if angle == HALF_TURN else table[angle]


def matrix(sine: Sequence[int], cosine: Sequence[int], five: int, six: int) -> dict[int, int]:
    sin5 = signed(sine[five])
    cos5 = signed(cosine_of(cosine, five))
    sin6 = signed(sine[six])
    cos6 = signed(cosine_of(cosine, six))
    return {
        CELLS["row0col0"]: product(cos6, ONE),
        CELLS["row0col1"]: product(sin6, -ONE),
        CELLS["row0col2"]: 0x0000,
        CELLS["row1col0"]: product(cos5, sin6),
        CELLS["row1col1"]: product(cos5, cos6),
        CELLS["row1col2"]: product(sin5, ONE),
        CELLS["row2col0"]: product(sin5, -sin6),
        CELLS["row2col1"]: product(sin5, -cos6),
        CELLS["row2col2"]: product(cos5, ONE),
    }
