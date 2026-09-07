"""The three by three matrix `$02` builds, as formulas over the part's own trig.

`$0a` reads ten words of what `$02` leaves behind and this project computes every
one of them. `$06` reads seventeen, and nine of those are a matrix `$0a` never
touches. This is that matrix.

Which cells `$06` depends on was found by changing one at a time and asking the
same question again, rather than by reading the listing: a cell a routine writes
before it reads looks like an input in a disassembly and is not one. Which
formula each cell follows was then found by searching the products of the part's
own sine and cosine of `$02`'s fifth and sixth arguments, and every one of the
nine matched.

    $5a = cos6 * 1        $5b = sin6 * -1       $5c = 0
    $6a = cos5 * sin6     $6b = cos5 * cos6     $6c = sin5 * 1
    $7a = sin5 * -sin6    $7b = sin5 * -cos6    $7c = cos5 * 1

Three things about that arithmetic are not obvious and all three were measured.

The product is floored rather than truncated toward nought. The part's own `$00`
floors, checked against it on 3,000 random pairs with no disagreement, and so
does this.

"One" is $7fff. Multiplying by it is not the identity: it takes one off a
positive value and leaves a negative one alone, which is why four of the nine
cells are the trig value less one wherever it is positive.

Negating $8000 does not fold back to $8000. The part multiplies by a positive
one there rather than by a negative one, so the negation is kept as the number
it is and only the answer is narrowed. Without that, `$7b` is wrong on every
argument set whose sixth word is exactly half a turn.

And one table entry has to be corrected. `build/cosine.bin` is what command `$04`
answers, which is the value already multiplied by $7fff, and that multiply cannot
tell $8000 from $8001. The matrix uses the value before it. Swept against the
part on 4,096 angles, the sine table is that value everywhere and the cosine
table differs at exactly one: half a turn, where the part holds $8000.
"""

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
"""Where each of the nine sits in the part's own memory."""

ONE = 0x7FFF
"""What the part multiplies by where the arithmetic wants an identity."""

HALF_TURN = 0x8000
"""The one angle whose cosine the extracted table cannot hold."""

HALF_TURN_COSINE = 0x8000
"""What the part holds there instead of the $8001 the table says."""

ANGLES = (5, 6)
"""Which of `$02`'s seven arguments the matrix is built from."""


def signed(word: int) -> int:
    """That word read as a signed sixteen bit value."""
    return word - 0x10000 if word & 0x8000 else word


def product(one: int, two: int) -> int:
    """The signed fractional product, floored, as the part leaves it.

    Both operands are already signed, and minus $8000 arrives here as 32,768
    rather than folded back, for the reason the module docstring gives.
    """
    return ((one * two) >> 15) & 0xFFFF


def cosine_of(table: Sequence[int], angle: int) -> int:
    """That table's entry, with the one the scaling cannot hold put back."""
    return HALF_TURN_COSINE if angle == HALF_TURN else table[angle]


def matrix(sine: Sequence[int], cosine: Sequence[int], five: int, six: int) -> dict[int, int]:
    """The nine cells, for those two arguments."""
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
