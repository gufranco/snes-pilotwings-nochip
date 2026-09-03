"""What `$0a` computes, read off the part rather than off its instructions.

`$0a` is the command the cartridge asks for most: 78% of every access in the
recording is the loop that reads its answer. Until now this project could only
replay that answer from a table, which covers the recording and nothing else.

The shape, established by watching the part's memory rather than by decoding
operands. Once a frame `$02` deposits five constants and a matrix. Then each
call to `$0a` walks down the screen from a starting line given as its single
argument, and for every line does this:

    d = line + horizon                  how far this line is from the horizon
    r = reciprocal of d                 a table read, never a divide
    A = first scale, from r             one mantissa and one exponent
    B = second scale, carried out of A  the other mantissa and exponent

and then sends four words, each the high half of a product against the matrix:
A against the first entry, B against the second, A against the third, B against
the fourth.

Why the reciprocal is passed in rather than worked out here. The part holds
`2**20 / x` for x from 32 to 64 in quarter steps, based at word 101, which is
the value it keeps in `RAM[$00]`. Which entry a line selects is decided by a
normalise loop, and that loop is the one part of this command still not read.

It is not a function of the distance. Holding the distance at -46 and changing
only the horizon gives -35 at a horizon of 53, 60 and 80, then -34 at 40 and a
different second value again at 120. So the same distance reached from a
different starting line takes a different entry, and a table keyed on distance
cannot be right. Solving one from the recording bears that out: across the calls
that use it, 30 distances of 192 are contradicted outright, meaning no single
value reproduces every line that asks for them.

That is why this takes the mapping as an argument instead of building one. A
caller with a correct mapping gets exact answers, and a caller with a mapping
keyed on the wrong thing gets `shortfall` telling it so, rather than a routine
that quietly rounds a wrong answer into a plausible one.

What the earlier operand decode got wrong, and how it was caught. That reading
put the matrix at `RAM[$bf]` and its neighbours. Driving `$02` on its own and
then reading the part's memory showed those four words still nought while a real
run plainly produced output from them, so the decode was set aside and the part
watched directly instead. The matrix is at `RAM[$7f]`, `RAM[$7e]`, `RAM[$6f]`
and `RAM[$6e]`, and `$02` writes it. The two commands that answer nothing, `$01`
and `$11`, write four words each and touch none of it.
"""

from collections.abc import Mapping, Sequence

MATRIX = (0x7F, 0x7E, 0x6F, 0x6E)
"""Where `$02` leaves the matrix that `$0a` multiplies by."""

HORIZON = 0xC8
FIRST_MANTISSA = 0x4C
FIRST_EXPONENT = 0xCC
SECOND_MANTISSA = 0x4B
SECOND_EXPONENT = 0xCB
"""The five constants `$02` deposits and `$0a` reads on every scanline."""

FIRST_SHIFT = 27
"""What the first scale is shifted down by before its exponent is taken off.

Measured against the part across eight exponents and fourteen mantissas, every
one of them exact.
"""

SECOND_SHIFT = 42
"""The same for the second scale, which carries the first one's product forward.

That carrying is the reason changing the first mantissa moves the second value
as well, which is what showed these are one calculation rather than two.
"""

PRODUCT_SHIFT = 15
"""How the output stage takes the high half of a product."""


def scales(
    reciprocal: Mapping[int, tuple[int, int]], state: Mapping[int, int], distance: int
) -> tuple[int, int] | None:
    """The two per-scanline values, or nothing where the line has no answer.

    A line level with the horizon has none, because the distance it would divide
    by is nought. The part is never asked for one, and neither is this. A
    distance the part was never asked about is also nothing rather than a guess.

    The one taken away at the end is taken away whichever side of the horizon the
    line falls, and that is the whole of the sign handling. Reading it as an
    addition whose sign followed the line fitted every distance above the horizon
    and none below it, which is how the mistake showed up: the sky agreed and the
    ground did not.
    """
    entry = reciprocal.get(distance)
    if distance == 0 or entry is None:
        return None
    value, folded = entry
    first = FIRST_SHIFT - state[FIRST_EXPONENT] + folded
    second = SECOND_SHIFT - state[FIRST_EXPONENT] - state[SECOND_EXPONENT] + folded
    if first < 0 or second < 0:
        return None
    product = state[FIRST_MANTISSA] * value
    whole = product >> first
    carried = (product * state[SECOND_MANTISSA]) >> second
    if distance > 0:
        return whole - 1, carried - 1
    return -whole - 1, -carried - 1


def answer(
    reciprocal: Mapping[int, tuple[int, int]],
    state: Mapping[int, int],
    start: int,
    lines: int,
) -> tuple[int, ...]:
    """The whole stream `$0a` sends, four words a scanline."""
    out: list[int] = []
    for step in range(lines):
        pair = scales(reciprocal, state, start + 1 + step + state[HORIZON])
        if pair is None:
            out.extend((0, 0, 0, 0))
            continue
        near, far = pair
        for value, at in ((near, MATRIX[0]), (far, MATRIX[1]), (near, MATRIX[2]), (far, MATRIX[3])):
            out.append((value * state[at]) >> PRODUCT_SHIFT)
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
