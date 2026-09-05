<div align="center">

# Pilotwings without the DSP-1

**Tooling to build Pilotwings ROMs with the coprocessor designed out, so they run from any flash
cartridge that can hold them. All three regions.**

[![licence](https://img.shields.io/github/license/gufranco/snes-pilotwings-nochip)](LICENSE)

</div>

---

## What this is

Pilotwings carries a DSP-1: an NEC uPD77C25 running a program Nintendo masked into it. The part
computes. It rotates and projects coordinates for the mode 7 ground, divides, takes reciprocals, and
answers the trigonometry the flight model asks for. Without it the game does not fly.

This project replaces the part with code and tables in the cartridge, and points the cartridge's own
instructions at them. Nothing about the board changes and there is no coprocessor left to emulate.
Whether the image has to grow at all is measured rather than assumed, and on the evidence so far it
does not.

You supply the retail dumps. Nothing here contains game data, and nothing ever will.

## Status

The replacement answers, and the demo draws its ground. Every one of the sixteen
commands that return anything comes back with exactly what the part returned, on
every question the three recordings hold. What is left is speed, named below and
in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md); nothing that is not built is implied
to be.

| part | state |
|------|-------|
| dump identification, all three regions | works, against measured digests |
| where each cartridge reaches the part | works, both forms of the access, checked against a recording |
| which commands the cartridge can issue | 20 in every image, checked against a recording |
| what the part answers | works, by running the part's own microcode |
| whether an answer can be stored instead of computed | measured, per command |
| how many argument sets each command takes | measured, 73,341 across three runs |
| which tables the part computes from | measured, four of them, 1,282 bytes, rebuilt exactly |
| the three tables no formula reproduces | taken from the part, 294,912 bytes, exact |
| `$02`'s derived state, which is everything `$0a` reads | three tables from the part, 59,686 bytes, no key carrying two answers across all 6,980 argument sets |
| `$00`, `$08` and `$04` as 65816 arithmetic | exact against the part, 400 random argument sets each |
| the table of answers | built, 15 commands, 3,014,801 bytes |
| `$13` and `$18` | complete over their whole domain, driven out of the part, so no key can miss |
| the lookup, in 65816 | exact on every recorded question, all three regions |
| the fallback, in 65816 | answers every command, including keys no recording holds, without looping |
| `$0a` | written in 65816, exact: 43,440 of 43,440 answer words against the part, on 60 argument sets across all three recordings |
| the three commands the game asks for through its redirected window | routed, so `$02`'s state and `$0a`'s starting line reach the cartridge |
| the accesses that reach the part through that window | routed. 200 three byte accesses, each replaced with a call that fits in three bytes, plus the five runs replaced whole |
| the long accesses that read the part and compute with what they read | routed. Seven of them, six `adc` and one `eor`, unreplaced since the first build because the scanner knew only the long load and the long store |
| the accesses in those runs that are not the part at all | all 31 routed. The window is ROM, so the game's own three byte reads and writes of its work RAM through the bank mirror answered nought and went nowhere; one of them is the counter the demo's next phase waits on. OPEN-QUESTIONS section 30 |
| why the demo left the retail course at game frame 175 | closed. The counter at `$0130` never counted, so the phase it gates never began |
| the demo | flies, draws its ground, and tracks the retail cartridge's own flight through game frame 405, which is as far as the comparison has been run. Work RAM differs by 30 to 60 bytes a frame, 22 of them at every frame and twelve of those a patched call the game copies into work RAM |
| the instrument panel | drawn on every picture. It was there all along on one picture in sixteen: the flight screen is three bands separated by two scanline interrupts, the sequence is armed once per frame of the game's clock, and one frame of that clock is now sixteen pictures. The third interrupt does nothing in the retail cartridge and is the only thing that happens once per picture, so it arms the sequence again. Screen brightness across the demo went from a spread of 31.1 to one of 0.05, at the retail cartridge's own level. OPEN-QUESTIONS section 32 |
| whether the image has to grow | yes, to 3.75 MB, which is inside what a low cartridge addresses |
| speed | 9.94 console frames per frame of the game's own clock over a fixed 750 frames of the flight, against 19.6 before and 11.07 this morning. That is 6.0 frames a second where the cartridge gives 60. One call to `$0a` costs 21.7% fewer processor cycles than it did this morning, measured on the model rather than on the console, because the console cannot compare two builds at that resolution. OPEN-QUESTIONS sections 36 to 39 |

### How much of the game it covers

Answering the questions it was built from is not coverage, so the table is
measured by holdout: built from part of the recordings and asked the rest.

| what was asked | hit rate |
|---|---:|
| the questions it was built from | 100% |
| a different recording of the same attract demo | 93.4% |
| the second half of a recording whose first half it learned | 11.2% |

The middle figure is the one to distrust. All three recordings are the same
attract sequence, so agreement between them measures repetition. The last figure
is what a player doing something the demo never did would see, and it is the
honest one.

Per command, on that last figure: `$13` 39.4%, `$10` 10.9%, `$00` 5.4%, `$06`
0%. `$06` is 31.7% of every call the game makes and cannot be tabulated at any
size, so its arithmetic is the single highest-value thing left to read.

Two commands are not measured this way because they no longer can miss. `$13`
and `$18` have arguments that are quantised rather than continuous: one of
`$13`'s words spans 32,769 and takes seven values. Sizing by span says 5.48e17
rows and sizing by the values the word can hold says 1,512. Every combination
was driven out of the part and stored, and all 248 rows the recordings do hold
came back identical when driven the same way, which is what says the fill is
sound rather than assumed.

`$10` was not completed although its domain is only 4,996 combinations. Driven
on its key alone it reproduces the recording 83 times in 100, so 17% of any
filled row would be wrong, and a wrong row is worse than a missing one: the
missing one falls back and the wrong one does not.

### What the lookup answers

Driven on the processor model against the three recordings, forty questions per
command per region:

| command | right | wrong |
|---|---:|---:|
| `$00` `$02` `$03` `$06` `$08` `$0c` `$0d` `$0e` `$10` `$13` `$14` `$1b` `$28` | 120 each | 0 |
| `$04` | 40 | 0 |
| `$18` | 10 | 0 |
| `$0a` | 0 | 120 |

`$04` and `$18` have fewer because the recordings hold fewer distinct questions
for them, not because fewer were tried. `$0a` answers 764 words of nought, which
is deliberate: it is bounded, it reads nothing it has not set, and it is
obviously wrong rather than plausibly wrong.

### How fast it is, against the part it replaces

Counted on the processor model, driving the assembled image. The call rate comes
from the recordings, which carry a frame number per access.

| | per call | a median frame, 43 calls | of a frame |
|---|---:|---:|---:|
| the part, wall time the game was blocked | tens to ~250 | about 2,700 | 6% |
| this replacement | 7,764 | 333,850 | 750% |

So it is correct and it is far too slow. A frame is 44,671 processor cycles when
a read costs 8 master clocks, and the game has to do everything else in the same
frame.

The reason is that the table is the slow path. `$00` costs 6,562 cycles through
the table and 398 through the arithmetic that was read out of the part and
checked exact against it, which is sixteen times cheaper and covers the whole
domain instead of only what was recorded. The same holds for `$08`, 5,696
against 920, and `$04`, 3,960 against 833.

That points the remaining work at exactly the two commands the coverage figures
already pointed at. `$06` is 30.8% of calls and `$13` is 26.9%; reading their
arithmetic is the largest gain in speed and in coverage, and it is one task.

### Where everything sits in the cartridge

A low cartridge carries banks `$00` to `$7D` and nothing above, so the whole
image is 121 banks, 3,964,928 bytes, with 5 banks still spare:

| what | banks |
|---|---|
| the game as it ships | `$00`-`$0F` |
| the replacement's own code | `$10` |
| the sine and cosine taken from the part | `$11`-`$18` |
| the answers | `$19`-`$6F` |
| the state `$02` leaves behind, which is what `$0a` reads | `$70`-`$72` |
| the reciprocal taken from the part | `$73` |
| the window the game's redirected accesses land in | `$7D` |

```bash
python3 tools/identify.py
```

It reports what it found, and when a file does not match it says which way it is wrong, prints the
digest it computed, and gives a command for working the digest out yourself on macOS, Linux or
Windows.

## What was measured

### One replacement covers all three regions

The three images reach the part the same way. Reading the code for stores to the data port, in both
of the two forms the cartridge uses, gives 208 in the USA image, 218 in the Japanese one and 208 in
the European one, and the twenty command bytes read out of them are the same twenty in all three.

The long form of the access, the one that spells its own bank, lands on exactly two addresses in
every region: 84 instructions at `$3f:8000` and 9 at `$3f:c000`, the same counts in all three. It is
the same driver three times over, which is the finding the shape of this project follows from: a
replacement written for one region is a replacement for the other two, and the PAL release is not a
separate problem.

### Most of the driver is invisible to a search for the long form

The obvious way to find where a cartridge reaches a coprocessor is to search for an absolute long
access, because it carries its own bank and can be matched exactly on four bytes. That search is
sound and it is not enough here. The hot paths take the data bank once with `pea $003f` and `plb`
and then use ordinary absolute stores, which spell two bytes and name no bank.

Measured against a recording of the Japanese image, which carries the program counter of every
access:

| | instructions | long form | absolute | share of bytes moved by the long form |
|---|---:|---:|---:|---:|
| writing to the part | 118 | 40 | 78 | 62.2% |
| reading from it | 47 | 13 | 34 | 7.9% |

So a reader that knows only the long form sees a minority of the writes and almost none of the
reads. [`commands.py`](commands.py) reads both, and the hottest loop in the game is one it would
otherwise miss entirely: `sta $8000` after `plb`, followed by 176 passes of poll-and-read.

The same search by encoding also reports bytes that are not instructions. In the USA image 29 of the
122 long-form matches sit at 29 different addresses scattered across banks `$30` to `$3e`, one match
each, which is what data that happens to spell an access looks like rather than what a driver looks
like. Japan has 28 of those and Europe 30, and they are the whole of the difference between the
three totals.

### Where a table works, and where it cannot

The plan this started from was to compute every answer ahead of time and ship the results, which is
what a cartridge with room to spare is for. Whether that works for a given command is decided by how
many argument words it reads, because that is the exponent on the size of the table it would take.
One word is 65,536 rows and a cartridge holds that. Two words is 4,294,967,296 rows.

So it was measured through the part's own protocol. A command written one word short of what it
wants still echoes; written one word past, it falls silent. The count is that silence, stepped back
one, and it is checked against arithmetic nobody told it about: command `$00` takes two words and
answers their product as signed fixed point with fifteen fractional bits, which is what
`0x1234 x 0x5678 -> 0x0C4C` is. A protocol reading that gets an unprompted calculation right is a
protocol reading that works.

Forty five of the 256 command bytes answer at all. The rest are not commands.

| words in | words out | commands | a table of every answer |
|---:|---:|---:|---|
| 1 | 1 | 2 | 131,072 bytes, which fits |
| 2 | 1 | 2 | 8,589,934,592 bytes, 683 times the whole image |
| 3 | 1 | 14 | 562 TB |
| 4 | 1 | 7 | larger still |
| 5 | 1 | 17 | larger still |
| 6 | 12 | 1 | larger still |
| 10 | 1 | 2 | larger still |

Two commands can have every answer stored. The other forty three cannot, and not by a margin a
bigger cartridge closes: the smallest of them is already 683 times a 96 Mbit image. The line sits
between one argument word and two, there is no arithmetic in between, and nothing moves it.

### What the game actually asks for, which is a different question

The table above is about the input domain: what a table would cost if the game
could send anything. It cannot, and the gap is enormous, so the domain is the wrong
thing to size against.

[`emu/`](emu/) records every byte the cartridge exchanges with the part, with the
program counter of the instruction that moved it. That last field is what makes
the recording checkable against the code, and it is what the numbers below rest
on: a command byte is the one thing this cartridge writes eight bits at a time,
so a program counter that only ever touches the low half of the port issued one.

From a run of the Japanese image over 12,000 frames with no input at all, so the
attract demo flies rather than sitting on a menu, 257,189 commands were issued
from 30 sites. The NTSC images stop reaching the part after frame 10,418 and the
PAL one is still flying at 11,999, which is why Europe issues command `$04` and
the other two never do. The traffic is not spread evenly:

| command | share | issued | sites | what it is |
|---|---:|---:|---:|---|
| `$06` | 28.9% | 74,261 | 2 | |
| `$13` | 25.4% | 65,332 | 1 | |
| `$00` | 15.0% | 38,668 | 10 | a signed multiply, so computed rather than stored |
| `$11` | 4.7% | 12,136 | 2 | |
| `$0a` | 2.7% | 6,946 | 1 | answers with a stream read 176 times over |
| the other 13 | 23.3% | 59,846 | 14 | |

Two commands are more than half of everything the cartridge asks for, and the
multiply is a further sixth of it and needs no table at all, because the console
has a hardware multiplier.

### Where a table works, measured by cutting at the site that issued it

An exchange is not a run of writes ended by a read. Command `$0a` answers with a
stream the cartridge reads 176 times over and the part accepts writes during that
stream, so a read in the middle of one exchange looks exactly like the end of it.
Counted that way, a tenth of the runs hold writes from code more than 32 bytes
apart, which is two routines' traffic joined into one.

[`exchanges.py`](exchanges.py) cuts at the command site instead, which the byte
stream cannot blur: a program counter that only ever touches the low half of the
data port issued commands, one that touches both halves wrote argument words, and
the recording carries the counter of every access.

Across all three runs, 73,341 distinct argument sets over 19 commands. At one
stored answer each that is 586,728 bytes, 4.66% of a 96 Mbit image. The split
that decides how to answer each command:

| | commands | rows | bytes | share of traffic |
|---|---:|---:|---:|---:|
| an inline compare chain | 5 | 22 | **176** | **30.5%** |
| a table | 13 | 46,832 | 374,656 | 54.3% |
| computed, being a multiply | 1 | none | 0 | 15.8% |

Twenty two rows and 176 bytes answer three tenths of everything the cartridge
asks for. `$13` alone is a quarter of the traffic and takes fourteen argument
sets; `$0e` takes one.

### What the part actually computes from

The list this project expected to tabulate was a sine, a cosine, a reciprocal, a
square root and an arctangent, and that was what a coprocessor of this kind
normally carries rather than anything measured. The part settles it itself: the
uPD77C25 keeps 1024 words of data ROM beside its program, and what a microcode
interpolates from is written down in there.

[`tables.py`](tables.py) rebuilds each candidate from its formula and searches for
it. Four are there, each to within one unit, which is rounding:

| table | words | formula | bytes |
|---|---:|---|---:|
| reciprocal | 129 | `2^22 / (128 + k)` | 258 |
| sine | 128 | `sin(pi k / 128) x 32767` | 256 |
| cosine | 128 | `cos(pi k / 128) x 32767` | 256 |
| arccosine | 256 | `acos(k / 256) x 32768 / pi` | 512 |
| | | **total** | **1,282** |

There is no square root and no arctangent, and nothing expected an arccosine.
Both masks carry the same four byte for byte, the DSP-1B holding three of them
two words lower, so the correction the DSP-1B made was to the program.

That answers the sizing question by dissolving it. A replacement carrying what
the part carries needs about a kilobyte, not 131,072 bytes per function, and
interpolating the way the microcode does is also the only way to be exactly right
rather than close.

### What range each argument takes

An argument computed at run time still has ends, and the ends decide what shape
of table is possible. [`exchanges.py`](exchanges.py) reports the lowest, the
highest and the count of distinct values at every argument position:

| what the positions look like | commands | what a table indexes on |
|---|---:|---|
| one or a handful of values | 5 | the values, in line |
| a few thousand, filling their range | 2 | the range, 2^18 and 2^20 rows |
| at least one spanning the whole word | 12 | nothing dense |

The third row is why a width on its own misleads. Command `$0d` takes about four
thousand distinct values at each of three positions and each position runs the
full 0 to 65,535, so the values are scattered rather than dense and a table on the
range would be 2^48 rows almost all of which answer inputs nobody sends. Both
figures are reported together for that reason.

### What a table built from those ranges costs

[`lut.py`](lut.py) plans one table per command and shares a single cartridge
budget between them. Each starts on a table over the set that was recorded, which
is cheap and can miss, and the budget is then spent widening as many as it reaches
to a table over the range, cheapest widening first. A command answered over its
range cannot reach the fallback for any argument between the ends the game used.

| command | rows | bytes | indexed on |
|---|---:|---:|---|
| `$04` | 1,048,576 | 2,097,152 | the range, complete |
| `$10` | 262,144 | 524,288 | the range, complete |
| `$0e` | 4 | 8 | the range, complete |
| `$80` | 1 | 2 | the range, complete |
| the other 15 | 74,020 | 140,878 | the set, so they can miss |

| | bytes |
|---|---:|
| the whole table | 2,762,528 |
| the game inside it | 524,288 |
| the image it makes | 3,286,816 |
| a 96 Mbit cartridge | 12,582,912 |
| **headroom** | **9,296,096** |

Four of the nineteen are complete over the range the game used. The other fifteen
hold a position spanning the whole sixteen bit word, so a table over their range
is 2^32 rows or more and nothing holds it; those are answered from the recorded
set and are where the fallback can be reached.

Widening those fifteen is not a budget problem and more cartridge does not fix
it. It needs either the scalar decomposition, where each function takes one
argument and 65,536 rows covers it outright, or a recording that covers more of
the game.

### The part keeps state, so arguments alone are not the key

Seven of the sixteen commands that answer give different answers for identical
arguments, because the part keeps state and a command reading a matrix another
command loaded is not a function of its own arguments. Command `$0e` takes one
argument set in every recording and answers it 6,260 different ways, which had
made it look like the cheapest table here at eight bytes.

Six of the seven become deterministic once the key carries one earlier command's
arguments as well: `$03` on the last `$14`, `$06`, `$0d` and `$0e` on the last
`$02`, `$13` and `$1b` on the last `$11`. Keyed that way nothing is ambiguous,
the whole table is 301,308 bytes and the image 825,596.

`$0a` is not tabulatable from these runs on any key tried, and that is measured
three ways rather than asserted once. No earlier command settles it, alone or in
any pair or triple. Storing each distinct whole answer costs 16,762,160 bytes,
which is more than a 96 Mbit cartridge holds. Storing the four word steps and
indexing them costs 538,583 distinct steps before any index array.

It writes one word, reads its answer through four instructions that each fire 176
or 191 times, then writes four words more. The answer is a per scanline stream
rather than a row.

None of that matters any more, because `$0a` no longer has to be stored. Reading
the part's own program stage by stage, and checking each stage against its
registers rather than against its answers, gives the arithmetic outright: one
normalise, one reciprocal, two multiplies and two shifts per scanline. The output
stage reproduces every recorded scanline exactly and the scale stage 175 of 176.
The chain is in OPEN-QUESTIONS section 22, and the sizes above are kept only to
record what the storage route would have cost.

### What the table actually encodes to

[`lut.py`](lut.py) emits each command's rows as a cartridge would hold them: a
row count, the key and answer widths, then the keys sorted so a replacement finds
a row by halving the range rather than walking it. Seventeen compares reach any
row of the largest table here.

| command | keyed on | rows | key words | answer words | bytes |
|---|---|---:|---:|---:|---:|
| `$06` | arguments and last `$02` | 75,278 | 10 | 3 | 1,957,236 |
| `$0d` | arguments and last `$02` | 6,557 | 10 | 3 | 170,490 |
| `$00` | arguments | 26,487 | 2 | 1 | 158,930 |
| `$02` | arguments | 6,980 | 7 | 4 | 153,568 |
| `$0e` | arguments and last `$02` | 6,980 | 9 | 2 | 153,568 |
| `$03` | arguments and last `$14` | 5,268 | 9 | 3 | 126,440 |
| the other 9 | | 22,904 | | | 268,708 |

| | bytes |
|---|---:|
| the table, settled commands only | 2,988,940 |
| the game inside it | 524,288 |
| the image it makes | 3,513,228 |
| a 96 Mbit cartridge | 12,582,912 |
| **headroom** | **9,069,684** |
| what plain low addressing reaches | 4,194,304 |

Only `$0a` is left to the fallback. The image stays inside plain low addressing,
so none of the windowed layout is needed.

### Where each row's answer came from

The keys come from the recordings, because only the game says what it asks. The
answers come from the part wherever the part could be driven to the same state,
because the recordings were made against snes9x and the two do not always agree.

| | rows |
|---|---:|
| answer driven from the part's own program | 108,311 |
| answer still the one the recording held | 42,345 |

Seventy percent by row. The rest are keys the game asks only after exchange
200,000, which is where a replay stops staying in step with the part, so they
keep the recorded answer and are marked as unconfirmed rather than dropped.
`$04` is the one command at zero percent: all 324 of its rows sit past that point.

A row carries its key as well as its answer, which is what a table keyed on a set
costs over one keyed on a range: a range table finds its row by arithmetic and
stores no key at all. Several of these keys are wider than the answer they lead
to, `$06` at ten words of key for three of answer, and that is the price of a
part that keeps state.

### What a recording can and cannot say

A recording says what the game did. It cannot say what the game can do. Most of
these commands take arguments that come from the aircraft's attitude and take a
new value on almost every frame, so no recording will ever show their input set
closing, and a lookup with no entry for an unseen argument has no answer at all.
The design is therefore a table where the set closes and computation where it
does not, and never a table alone. Which commands fall on which side is measured
above, and the answer does not close: it is what three runs of the demo produced,
and a player working the controls produces sets the demo never will.

Reading the cartridge's code rather than running it answers the other half.
[`commands.py`](commands.py) reads 20 command bytes out of every one of the three
images, and Europe reads one more, `$80`. Against the Japanese recording it
agrees on 27 of the 30 sites that were actually executed, contradicts none, and
is silent on three, each for a stated reason. Against the European one it agrees
on 33 of 36 and again contradicts none, and every command that recording issued
is one the code reading also finds.

| | commands |
|---|---:|
| read out of the code, all three images | 20 |
| Europe also reads | `$80` |
| the Japanese recording issued | 18 |
| the European recording issued | 19 |
| read but never seen to run | `$21`, `$23` |

`$80` is not a computation. It sends the part back to waiting for a command, and
the cartridge writes it 128 times in a row at `$0702a` to flush the part.

### Whether the image has to grow at all

Probably nothing, and that is the answer to a question this project was built
around. The tables are 1,282 bytes and the retail image already has room for
them, which [`layout.py`](layout.py) measures rather than assumes:

| region | free in runs of 256 bytes or more | largest single run |
|---|---:|---:|
| USA | 63,122 | 4,249 |
| Japan | 74,207 | 8,395 |
| Europe | 63,122 | 4,249 |

Every one of them holds all four tables in one piece with tens of kilobytes to
spare. A run of one repeated byte is evidence that nothing uses it rather than
proof, so a candidate run is checked against the driver census before anything
goes in it, but the shape of the answer is not in doubt: this does not look like
a cartridge that has to grow.

That matters because growing is not free. An image past the address space needs
the windowed layout the sibling project uses, which is a substantial piece of work
and changes which emulators load the result. On the current evidence none of that
is needed here.

What remains unmeasured is the replacement code itself, which is not written.

Products need no table at all: command `$00` is a signed multiply, it is a sixth
of everything the cartridge asks for, and the console's hardware multiplier
computes it faster than any lookup.

## The dumps

Named as No-Intro names them. Every digest is of the whole file with no copier header. SHA-256 is
the one that decides; the others are there to cross-check against databases that still key on them.

| file | read as | size |
|---|---|---|
| Pilotwings, USA | `roms/pilotwings-usa.sfc` | 524,288 |
| Pilotwings, Japan | `roms/pilotwings-jp.sfc` | 524,288 |
| Pilotwings, Europe | `roms/pilotwings-eur.sfc` | 524,288 |

| region | SHA-256 | CRC32 |
|---|---|---|
| USA | `03d0127f5de3237e22ad00de0c20763274da7b71142dde693240ac96d10983a3` | `266C44ED` |
| Japan | `d1845de22c3c7f2606bda20e09c8f7a78f92f5cbbb6bfe01f96a1d1e84b30394` | `77871727` |
| Europe | `f70a72f3d3a65497cdc4d849877a29cf4f7bd10439bb7f5cb8675cdfc0e706d4` | `DEF45776` |

All three declare version `0x00` in their headers, and no later revision of any of them appears in
the set these were measured from.

Identification is by digest and by nothing else, and this project has a concrete reason rather than
a general preference. A Nintendo Campus Challenge cartridge built on this game is the same 524,288
bytes, declares the same chipset `0x03`, and carries the same internal title `PILOTWINGS`. A check
on the length, the chipset or the title accepts it as a retail dump. Its map byte and its digests
are the only things that say otherwise.

## Prerequisites

| Tool | Version | Why |
|:-----|:--------|:----|
| [Python 3](https://www.python.org/) | 3.12 | every analysis module |
| Your own cartridge dumps | 524,288 bytes each | placed in `roms/` under the names above |
| Your own copy of the microcode | 8,192 bytes | placed in `firmware/`, for the checks that drive the part |

Nothing is installed from a package index. Nothing is downloaded.

## The hardware this is checked against

```bash
git clone --recurse-submodules https://github.com/gufranco/snes-pilotwings-nochip.git
```

The models this project measures itself against are not written here. Each is its own repository,
pinned as a submodule at the root of this one under the name of the repository it is, and each is
held to something outside itself rather than to its author's confidence. They sit at the root rather
than under a folder because anybody opening this should see what it is built on without going
looking.

| model | what proves it |
|---|---|
| [65816](https://github.com/gufranco/mos65xx-python) | a per-opcode suite, 5,120,000 cases |
| [DSP-1](https://github.com/gufranco/snes-dsp-python) | the part's own microcode, run rather than described |
| [cartridge map](https://github.com/gufranco/snes-mapper-python) | every header combination in a real cartridge library |
| [ROM image](https://github.com/gufranco/snes-rom-image-python) | the whole of that same library, rewritten and checked |
| [driver](https://github.com/gufranco/snes-driver-python) | where in the cartridge's code it reaches the part |

There is no graphics model here, unlike the sibling project that converts bitmaps. This part computes
numbers and returns numbers; it never touches a tile, so a model of the console's tile format would
be a dependency with nothing to answer.

The 65816 model is also the instrument the replacement will be measured with. It drives a bus cycle
by cycle, so what a routine costs is the cycles it actually took rather than a sum from a table.

They also start dirty. Memory and registers hold arbitrary but reproducible values rather than
zeroes, because real hardware does, and anything here that wants a cleared machine has to ask for
one. That turns a read of something never written from an accident into a question.

## When something is wrong

```bash
python3 doctor.py
```

It looks at this machine and prints what is actually there: the Python, every model this project is
pinned to and its version, whether the coprocessor can run at all, which of its two masks are
present, and which cartridge dumps are here. It then asks every model for its own report and files
what comes back under that model's name, so the whole chain is in one place rather than one layer of
it.

A check that fails says what it saw, and a check that itself throws is reported as what it threw
rather than taking the report down with it. Paste all of it into an issue.

## Repository guide

Analysis modules in Python, each with its tests beside it.

| file | role |
|------|------|
| [`hardware.py`](hardware.py) | puts the pinned hardware models on the import path, and says where the microcode is |
| [`dumps.py`](dumps.py) | which dumps this project reads, and what makes each one itself |
| [`sites.py`](sites.py) | where each cartridge reaches the part through the long form of the access |
| [`commands.py`](commands.py) | every instruction that reaches the part, and which command bytes the code can issue |
| [`exchanges.py`](exchanges.py) | what a recorded run asked for, cut at the site that issued it |
| [`census.py`](census.py) | the same question cut at the byte stream, which command `$0a` breaks |
| [`tables.py`](tables.py) | which tables the part carries, read out of its own data ROM |
| [`layout.py`](layout.py) | whether the replacement fits in the image the cartridge already is |
| [`tabulate.py`](tabulate.py) | whether a command's answers can be stored instead of computed |
| [`microcode.py`](microcode.py) | the part's own dispatch tree, walked for all 256 command bytes |
| [`derived.py`](derived.py) | drives the part to produce the three tables no formula reproduces |
| [`raster.py`](raster.py) | what `$0a` computes, read out of the part stage by stage. The reference the assembly mirrors |
| [`parameter.py`](parameter.py) | how the state `$02` leaves behind splits into tables smaller than the whole |
| [`state02.py`](state02.py) | packs one of those tables the way the cartridge searches it |
| [`state02build.py`](state02build.py) | drives the part across every `$02` argument set and writes all three |
| [`routines.py`](routines.py) | runs the assembled 65816 against the part, and fails when they disagree |
| [`lutbuild.py`](lutbuild.py) | builds the table of recorded answers, and says what it left out |
| [`doctor.py`](doctor.py) | what is actually on this machine, the whole chain, printed for a bug report |
| [`version.py`](version.py) | the release number, rewritten by [`scripts/set-version.sh`](scripts/set-version.sh) |
| [`artifacts.manifest.json`](artifacts.manifest.json) | every dump this project reads, and what makes each one itself |
| [`tools/identify.py`](tools/identify.py) | checks a dump, and says what is wrong when it is |
| [`tools/cycles.py`](tools/cycles.py) | what one call to a routine costs, on the processor model, which is the only instrument fine enough to compare two builds |
| [`asm/nochip.asm`](asm/nochip.asm) | the whole replacement, and where each piece sits in the cartridge |
| [`asm/dsp1-answer.asm`](asm/dsp1-answer.asm) | the lookup: the index, the binary search, the answer copy, and the two commands that need no search |
| [`asm/dsp1-fallback.asm`](asm/dsp1-fallback.asm) | what answers when the lookup finds no row |
| [`asm/dsp1-port.asm`](asm/dsp1-port.asm) | the stubs the game's own accesses become, and the runs replaced whole |
| [`asm/dsp1-ground.asm`](asm/dsp1-ground.asm) | `$0a`, the command that draws the ground, and the three tables it reads |
| [`asm/dsp1-window.asm`](asm/dsp1-window.asm) | the bank the game's redirected accesses land in |
| [`asm/dsp1-raster.asm`](asm/dsp1-raster.asm) | the interrupt that starts the flight screen's three band sequence again, once per picture |
| [`asm/dsp1-ops.asm`](asm/dsp1-ops.asm) | the three commands whose arithmetic is known exactly |
| [`asm/dsp1-tables.asm`](asm/dsp1-tables.asm) | the four tables the part's own formulas rebuild, entry for entry |
| [`asm/dsp1-derived.asm`](asm/dsp1-derived.asm) | where the three tables taken from the part are placed |
| [`mos65xx-python/`](mos65xx-python/) | the 65816, held to a per-opcode suite |
| [`snes-dsp-python/`](snes-dsp-python/) | the DSP-1, running the part's own microcode |
| [`snes-mapper-python/`](snes-mapper-python/) | the cartridge map, held to a library of real cartridges |
| [`snes-rom-image-python/`](snes-rom-image-python/) | image handling, held to that same library |
| [`snes-driver-python/`](snes-driver-python/) | where the cartridge's own code reaches the part |

## Working on this

| What | Command |
|:-----|:--------|
| Every test | `for t in *.test.py tools/*.test.py; do python3 "$t" \|\| break; done` |
| Coverage, which fails below 100% | `python3 -m coverage erase && for t in *.test.py tools/*.test.py; do python3 -m coverage run -a "$t"; done && python3 -m coverage report` |
| What is on this machine | `python3 doctor.py` |
| Lint | `ruff check .` |
| Types | `mypy .` |
| Format | `ruff format --check .` |
| Which dumps are here | `python3 tools/identify.py` |

332 tests across 14 files. 298 need nothing but a checkout; 34 need a dump or the microcode and
report themselves as skipped without one, so a fresh clone runs the suite green.

The checks that need an artifact live in `*.retail.test.py` files kept out of the coverage
measurement. A machine with the dump runs one set of paths and a machine without it runs the other,
so no single build can exercise both, and a gate that demands the impossible gets switched off
rather than met.

### Conventions

| Convention | Where |
|:-----------|:------|
| Commit messages | [Conventional Commits](https://www.conventionalcommits.org/), which drives the version number |
| Python style | [`pyproject.toml`](pyproject.toml), ruff at line length 100, targeting 3.12 |
| Tests | one `<module>.test.py` beside each module, standard library `unittest` |
| Coverage | 100% of statements and branches, enforced by [`pyproject.toml`](pyproject.toml). A branch with no test fails the build rather than lowering the number |
| Comments | required in the assembly and only there: entry and exit state, register widths, and where each recovered address came from |
| Releases | semantic versioning cut by the pipeline. Each image carries its version in the filename |

### Decisions worth knowing

- **No ROM data enters this repository.** Not dumps, not intermediates, not test fixtures. It is why
  parts of the suite skip rather than fail without a dump.
- **The part's own microcode answers for the part.** Nothing here computes a DSP-1 result. What a
  command answers is whatever the program the chip carries answers, and a check that needs that
  program reports it had nothing to run rather than passing without it.
- **The cartridge is the only oracle for what is asked.** A command and an argument set are a
  request because a retail cartridge sends them. Producing a plausible answer for a pair nobody
  asked for proves nothing.
- **Whether to store or to compute is a measurement, never a preference.** The table above comes
  from [`tabulate.py`](tabulate.py), which drives the part and counts. Both sides of the line are
  printed, because a single total would hide which commands moved.
- **A reading of the code is checked against a run of it, and the other way round.** Neither is
  trusted alone. A search by encoding cannot tell an instruction from data that spells one, and a
  recording cannot see a routine the run never entered. Where the two disagree the disagreement is
  the finding.
- **What is not known is written down, and so is what turned out to be wrong.**
  [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) carries every place a claim here is narrower than it
  looks, with the measurement that would settle it, and a withdrawn claim stays there with the fault
  that produced it rather than being quietly deleted.

## Contributing

Measurements first. [CONTRIBUTING.md](CONTRIBUTING.md) has the gates a change is expected to pass,
[SECURITY.md](SECURITY.md) says what belongs in a private report, and the
[Code of Conduct](CODE_OF_CONDUCT.md) applies wherever this project is discussed.

Never attach a cartridge or a microcode image, and never link to somewhere either can be downloaded.
A digest identifies a file without carrying it.

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the same script that
stamps the release, so the version it names is the version that shipped.

## Acknowledgements

**Nintendo EAD and Argonaut**, for the game.

**The snes9x and ares teams**, for the emulators these images will be checked against.

**neviksti and the Star Ocean chip-free conversion**, which is where the addressing rule for images
too large for the address space comes from.

**The Zeldix community**, where most of the SNES romhacking knowledge this leans on is written down.

## Legal

No ROM data is distributed here. Everything in this repository operates on files you must already
own, and the analysis is derived from retail cartridges you supply.

The tooling, the assembly and this document are released under the [MIT licence](LICENSE). That
covers my own work and nothing else. It grants no rights in the game.

## Image size is not a constraint to optimise against

The cartridge may grow to **96 Mbit** whenever that buys fidelity, stability or
speed. This is a standing decision by the project owner, recorded here so no
later session re-derives the opposite from an old measurement.

What that means in practice:

- Never drop a command from the answer table for space. Grow the image instead.
- Never approximate arithmetic to avoid carrying a table. Carry the table.
- Never treat "it does not fit" as a reason to stop. It fits; make it bigger.

The numbers, so the trade is visible rather than assumed. A LoROM cartridge
addresses banks `$00` to `$7d`, which is 126 banks of 32 KiB, or just under 4
MiB, and every bank above that needs the windowed layout the sibling project
uses. Answering all twelve of the commands the game asks for takes 87 banks:
`$06` alone is 1,957,228 bytes, because it has 75,278 distinct keys and answers
three words to each. That is 60 banks for one command, and it is the command the
game asks for most.

An earlier note in this file put a ceiling at 1 MiB on the strength of one
measurement. That measurement does not hold: images of 2 MiB and 4 MiB both boot
and run the demo identically, once the header's size byte is set to match. The
header byte is what an emulator maps from, so an image that grows without it
maps only the part the old byte described, and the tables that answer the
commands live in the part it leaves out.
