# Working in this repository

The family standard is in [FAMILY.md](FAMILY.md) and binds this repository as it binds every other
member. This file carries what is only true here. Where the two appear to disagree, the standard
wins and the disagreement is a defect in this file.

## What this project is, in one paragraph

Pilotwings carries a DSP-1, an NEC uPD77C25 running a program Nintendo masked into it, and the part
computes: it rotates and projects coordinates for the mode 7 ground, divides, takes reciprocals, and
answers the trigonometry the flight model asks for. This project replaces the part with tables and
65816 routines in the cartridge and points the cartridge's own instructions at them. All three
regional releases are targets, and one replacement covers all three because all three carry the same
driver: the same twenty command bytes, and the same 84 long-form writes and 9 long-form reads at the
two addresses it uses.

## Storing an answer is a measurement, not a preference

Whether a command's answers can be stored is decided by how many argument words it reads, because
that is the exponent on the table it would take. It is measured through the part's protocol, not
guessed: written one word short of what it wants the part still echoes, written one past it falls
silent, and the count is that silence stepped back one. The reading is checked against arithmetic
nobody supplied, since command `$00` answers the signed fixed-point product of its two words.

Forty five of 256 command bytes answer at all. Two of them take a single word and can be tabulated
whole at 131,072 bytes each. The rest take two or more, and the smallest of those is 683 times a
96 Mbit image.

What growing the image buys is therefore not whole-command tables. It is a table per scalar function
the commands are built from, and which functions those are is no longer a guess: the part carries
1024 words of data ROM and [`tables.py`](tables.py) reads four numeric tables out of it, a reciprocal
`2^22 / (128 + k)`, a sine, a cosine and an arccosine, each matching its formula to within one unit.
There is no square root and no arctangent. All four together are 1,282 bytes.

Tabulating those four over their whole sixteen bit input is 524,288 bytes, which is exhaustive rather
than merely large: every value an argument can hold has a row, so a lookup cannot miss. Products need
no table at all, because the console has a hardware multiplier.

Anybody proposing to widen or narrow that split re-runs [`tabulate.py`](tabulate.py) and shows the
number, because the number is what decided it. Two earlier readings of the same question were wrong
in ways that both looked right, and they are described in that module so the third one is not made
again.

## What answers for the part

Nothing here computes a DSP-1 result. The expected answer to any command comes from running the
part's own microcode through [snes-dsp-python](https://github.com/gufranco/snes-dsp-python), and
that microcode belongs to whoever made the part, so it is never carried here and is supplied by
whoever runs this. A check that needs it reports that it had nothing to run rather than passing.

Two masks of the part exist whose answers differ, and which one a retail board carries cannot be
read out of a dump. Nothing here claims which one is being reproduced. That is the first entry in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md), and a change that assumes an answer to it is wrong even when
it works.

## The five models, and why there are five

Each is its own repository, pinned as a submodule at the root, and held to something outside itself.

| model | answers for |
|---|---|
| [mos65xx](https://github.com/gufranco/mos65xx-python) | the processor the replacement runs on, and the instrument it is measured with |
| [snesdsp](https://github.com/gufranco/snes-dsp-python) | what the part answers, by running its program |
| [mapper](https://github.com/gufranco/snes-mapper-python) | the cartridge map |
| [romimage](https://github.com/gufranco/snes-rom-image-python) | the forms an image is stored in |
| [snesdriver](https://github.com/gufranco/snes-driver-python) | where the cartridge's own code reaches the part |

There is no graphics model, unlike the sibling project that converts bitmaps. This part computes
numbers and returns numbers and never touches a tile, so a model of the tile format would be a
dependency with nothing to answer. Adding one needs a reason that names what it would answer.

## The table is the design and the fallback is what keeps it honest

The family standard carries this rule; what follows is what it means here.

The table holds what the game asks for, never what the part accepts. Sizing
against the part's input domain concludes that nothing can be stored, because the
domain is the exponent of the argument count. Sizing against the game concludes
that almost all of it can. Any figure here says which of the two it measured.

What the game asks for is a property of the whole game. A recording is a floor,
and a recording of the attract demo with the controls untouched is the lowest
floor there is. A figure taken from one states the frames it covers and what the
run was doing.

Two questions come apart and are answered separately. Which calculations the game
can ask for is answered by reading the whole image, and that closes. Which values
it asks for them with is answered by running the game, and that does not: the
values are computed from state the image does not hold.

Every command has a fallback in 65816, and it is never optional. A lookup with no
row has no answer, so a replacement that meets one either hangs or reads whatever
was in memory. The intent is that the fallback never runs; the requirement is that
it always could. A slower answer beats a stopped machine.

A fallback nobody measured is a fallback nobody has. Its cost is stated in cycles
and a build reports how often it fired, rather than asserting it did not.

## What must never enter this repository

No cartridge dump, no microcode image, no fragment of either, no intermediate built from either, and
no test fixture carrying any of it. Digests yes, bytes never. Nothing here says where a dump can be
obtained and nothing here downloads one.

`roms/`, `firmware/`, `build/` and `dist/` are ignored, and the ignore file covers them on its own
rather than relying on one configured on a machine, because that one does not travel with a clone.

## Gates

Every one of these passes before a change is done. A gate that was not run is a gate that failed.

| gate | command |
|---|---|
| tests | `for t in *.test.py tools/*.test.py; do python3 "$t" \|\| break; done` |
| coverage, 100% of statements and branches | `python3 -m coverage erase && for t in *.test.py tools/*.test.py; do python3 -m coverage run -a "$t"; done && python3 -m coverage report` |
| types | `mypy .` |
| lint | `ruff check .` |
| format | `ruff format --check .` |
| this machine | `python3 doctor.py` |

The checks needing a dump or the microcode live in `*.retail.test.py` and are kept out of the
coverage measurement. A machine holding the artifacts runs one set of paths and a machine without
them runs the other, so no single build exercises both.

## A search by encoding is not a reading of the driver

Two failures came out of treating one as the other, and both looked right.

The long form of the access spells its own bank, so four bytes match it exactly.
That makes it the natural thing to search for, and it is a minority of this
driver: the hot paths take the data bank with `pea $003f` and `plb` and then use
ordinary absolute stores. Measured against a recording, the long form carries
62% of the writes and 8% of the reads. Anything that reports where the cartridge
reaches the part reads both forms, and [`commands.py`](commands.py) is what does.

The same search also reports bytes that were never instructions. Twenty nine of
the 122 long-form matches in the USA image sit at 29 different addresses, one
each, scattered across banks `$30` to `$3e`. A driver does not have that shape.
Those coincidences are the whole of the difference between the three regions'
site totals, so a claim that the regions differ has to survive dropping them
first, and this one did not.

## Conventions that are only true here

- **Identification is by SHA-256 and by nothing else.** A Nintendo Campus Challenge cartridge built
  on this game is the same length, declares the same chipset, and carries the same internal title, so
  a check on any of those accepts it as a retail dump. This is why the rule is absolute here rather
  than a general preference.
- **All three regions or none.** A change that works for one region and is untested on the other two
  is not done. They share every exchange shape, so there is no cost to covering all three and no
  excuse for not doing it.
- **The PAL release is not a footnote.** Europe counts a different number of cycles per frame, so
  every timing figure states which console it was measured on rather than folding the two into one
  number.
- **A figure in the readme is one somebody ran.** When a claim is checked and found stale, the claim
  was the defect, never the check.

## Where the open questions are

[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) carries four, each with the measurement that would close it.
Read it before claiming anything about which mask is reproduced, which commands matter, or how large
the finished image needs to be. Nothing in this repository claims any of those three today.
