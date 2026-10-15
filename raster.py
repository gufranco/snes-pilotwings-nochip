from collections.abc import Mapping, Sequence

WORD = 0x10000
SIGN = 0x8000

MATRIX = (0x7F, 0x7E, 0x6F, 0x6E)

STEP = 0x49
HORIZON = 0xC8
FIRST_MANTISSA = 0x4C
FIRST_EXPONENT = 0xCC
SECOND_MANTISSA = 0x4B
SECOND_EXPONENT = 0xCB

NORMAL_LOW = 0x4000

PRODUCT_SHIFT = 15

EXPONENT_BASE = 6

ON_NOUGHT = (0x7FFF, 0x2F)

CLAMP_HIGH = 0x7FFF
CLAMP_LOW = -0x7FFF

SHIFT_LIMIT = 16


def signed(word: int) -> int:
    word &= 0xFFFF
    return word - WORD if word & SIGN else word


def product(one: int, two: int) -> int:
    return signed((signed(one) * signed(two) * 2 >> 16) & 0xFFFF)


def normalise(value: int) -> tuple[int, int]:
    value = signed(value)
    if value == 0:
        return 0, 0
    count = 0
    while (value >> 15 & 1) == (value >> 14 & 1):
        value = signed((value << 1) & 0xFFFF)
        count += 1
    return value, count


def reciprocal(held: int, count: int, table: Sequence[int]) -> tuple[int, int]:
    if held == 0:
        return ON_NOUGHT
    magnitude = min(abs(held), CLAMP_HIGH)
    mantissa = table[magnitude - NORMAL_LOW]
    return (mantissa if held > 0 else -mantissa), count - EXPONENT_BASE


def scaled(mantissa: int, exponent: int) -> int:
    held, count = normalise(mantissa)
    over = exponent - count - PRODUCT_SHIFT
    if over == 0:
        return held
    if over > 0:
        return CLAMP_HIGH if held >= 0 else CLAMP_LOW
    places = -over
    if places >= SHIFT_LIMIT:
        return 0
    return held >> places


def scanline(state: Mapping[int, int], line: int, table: Sequence[int]) -> tuple[int, int]:
    held, count = normalise(product(state[STEP], line) + state[HORIZON])
    mantissa, exponent = reciprocal(held, count, table)
    first = product(state[FIRST_MANTISSA], mantissa)
    first_exponent = exponent + state[FIRST_EXPONENT]
    second = product(state[SECOND_MANTISSA], first)
    return (
        scaled(first, first_exponent),
        scaled(second, first_exponent + state[SECOND_EXPONENT]),
    )


def answer(
    state: Mapping[int, int], start: int, lines: int, table: Sequence[int]
) -> tuple[int, ...]:
    out: list[int] = []
    for step in range(lines):
        near, far = scanline(state, start + step, table)
        for value, at in ((near, MATRIX[0]), (far, MATRIX[1]), (near, MATRIX[2]), (far, MATRIX[3])):
            out.append(product(state[at], value) & 0xFFFF)
    return tuple(out)


def shortfall(got: Sequence[int], want: Sequence[int]) -> tuple[int, int]:
    right = wrong = 0
    for at in range(0, min(len(got), len(want)), 4):
        if tuple(got[at : at + 4]) == tuple(want[at : at + 4]):
            right += 1
        else:
            wrong += 1
    return right, wrong
