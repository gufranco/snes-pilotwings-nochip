"""What `$0a` computes, read out of the part's own program stage by stage.

`$0a` is the command the cartridge asks for most: 78% of every access in the
recording is the loop that reads its answer. It answers 764 words in one region
and 704 in another, and no table can hold it, so the cartridge has to compute it.

This is that arithmetic, written as the cartridge computes it. It is the
reference `asm/dsp1-ground.asm` mirrors: same stages, same rounding, same two
saturating exits, so a disagreement between the two is a fault in one of them
rather than a difference of approach.

The chain, per scanline, with the part's own addresses:

    $366  distance    (step * line) >> 15, plus the horizon
    $36a  normalise   $003a: double while the top two bits agree, keeping the
                      last value that fitted, and count the doublings
    $36b  reciprocal  $00d3: a mantissa, and an exponent that is the count less
                      six. A table over the normalised range, because that
                      routine refines rather than reads
    $36d  first pair  mantissa = (first mantissa from $02 * reciprocal) >> 15
                      exponent = reciprocal exponent + first exponent from $02
    $371  first scale $0077: normalise again, then shift right by fifteen less
                      the exponent, or saturate
    $377  second pair mantissa = (second mantissa from $02 * the first
                      chain's mantissa, before its shift) >> 15
                      exponent = the first exponent plus the second from $02
    $37a  second scale the same $0077
    $382  the answer  four words, the two scales against four matrix words

Why six earlier attempts at this failed, and none of them was close. Every one
tried to recover a single number per scanline from the answers. There is none to
recover: the chain carries two normalisations, two saturating exits and a
mantissa with its own exponent, and the second scale is a cascade off the first
rather than a second branch off the reciprocal. That cascade is why the conflicts
tracked the first exponent rather than the horizon, which read as noise.

And an answer word is not a scale. It is a scale multiplied by a matrix word and
shifted, which against `$7fff` is one less than the scale. Reading answers as
scales quietly voided three separate measurements before it was caught.

Checked against the part on 60 argument sets drawn from all three recordings:
43,440 answer words, every one of them exact, against the part and against the
recordings both.
"""

from collections.abc import Mapping, Sequence

WORD = 0x10000
SIGN = 0x8000

MATRIX = (0x7F, 0x7E, 0x6F, 0x6E)
"""Where `$02` leaves the matrix that `$0a` multiplies by."""

STEP = 0x49
HORIZON = 0xC8
FIRST_MANTISSA = 0x4C
FIRST_EXPONENT = 0xCC
SECOND_MANTISSA = 0x4B
SECOND_EXPONENT = 0xCB
"""The six constants `$02` deposits and `$0a` reads on every scanline."""

NORMAL_LOW = 0x4000
"""The lowest magnitude the normalise loop can leave, and so the table's base."""

PRODUCT_SHIFT = 15
"""How the multiplier takes the high half of a product."""

EXPONENT_BASE = 6
"""What the reciprocal's exponent is the doubling count less.

Read off the part: `$0077`'s caller seeds `b` with seven and `$003a` takes the
doubling count off it, then `$00d3` answers one less its own input exponent.
"""

ON_NOUGHT = (0x7FFF, 0x2F)
"""What `$00d3` answers for a distance of nought, at `$0f2` and `$0f3`.

An exponent large enough that the shift below saturates, which is the part's own
answer to a scanline exactly level with the horizon.
"""

CLAMP_HIGH = 0x7FFF
CLAMP_LOW = -0x7FFF
"""What `$0077` clamps to at `$083` and `$085`.

Not `$8000`. The part loads `$8001`, so the most negative scale it can give back
is one short of the most negative word.
"""

SHIFT_LIMIT = 16
"""Past this the part reads a word of its own ROM that is nought.

`$0077` shifts by multiplying by a power of two out of the data ROM. Words `$022`
through `$030` hold 1 up to 16,384, and `$000` through `$021` are all nought, so
a shift of sixteen or more is a multiply by nought rather than a sign fill.
"""


def signed(word: int) -> int:
    word &= 0xFFFF
    return word - WORD if word & SIGN else word


def product(one: int, two: int) -> int:
    """What the part's multiplier leaves: the product doubled, high word kept.

    Rounded down, including for a negative product, which is the same arithmetic
    `op_00_body` in `asm/dsp1-ops.asm` performs.
    """
    return signed((signed(one) * signed(two) * 2 >> 16) & 0xFFFF)


def normalise(value: int) -> tuple[int, int]:
    """`$003a`: double while the top two bits agree, keeping the last that fitted.

    Answers the value and the count of doublings. Nought is answered untouched,
    because doubling it never changes its sign and the loop would not end.
    """
    value = signed(value)
    if value == 0:
        return 0, 0
    count = 0
    while (value >> 15 & 1) == (value >> 14 & 1):
        value = signed((value << 1) & 0xFFFF)
        count += 1
    return value, count


def reciprocal(held: int, count: int, table: Sequence[int]) -> tuple[int, int]:
    """`$00d3`, as one read of a table over the range the normalise loop leaves.

    The sign is not in the table. The part strips it at `$0d6`, refines the
    magnitude, and negates the answer at `$0f0`, so one half of the range answers
    both halves. The one magnitude that cannot be negated in a word is clamped
    the way the part's own absolute value clamps it.
    """
    if held == 0:
        return ON_NOUGHT
    magnitude = min(abs(held), CLAMP_HIGH)
    mantissa = table[magnitude - NORMAL_LOW]
    return (mantissa if held > 0 else -mantissa), count - EXPONENT_BASE


def scaled(mantissa: int, exponent: int) -> int:
    """`$0077`: normalise, work out the shift, and take one of its three exits."""
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
    """The two scales for one scanline."""
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
    """The whole stream `$0a` sends, four words a scanline.

    The first group belongs to the line the argument names, not the one after it.
    """
    out: list[int] = []
    for step in range(lines):
        near, far = scanline(state, start + step, table)
        for value, at in ((near, MATRIX[0]), (far, MATRIX[1]), (near, MATRIX[2]), (far, MATRIX[3])):
            out.append(product(state[at], value) & 0xFFFF)
    return tuple(out)


def shortfall(got: Sequence[int], want: Sequence[int]) -> tuple[int, int]:
    """How many scanlines agree and how many do not.

    A pair rather than a percentage, so a caller cannot quote the good half
    without carrying the other one along with it.
    """
    right = wrong = 0
    for at in range(0, min(len(got), len(want)), 4):
        if tuple(got[at : at + 4]) == tuple(want[at : at + 4]):
            right += 1
        else:
            wrong += 1
    return right, wrong
