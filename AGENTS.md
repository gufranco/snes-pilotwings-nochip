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

Those four are not everything the handlers read. Watching the data ROM while the part runs the game's
own command stream, the handlers touch 315 of the 1024 words across 30,000 exchanges and 98 of those
sit outside all four, in six stretches, none of them monotone. They are constants rather than a fifth
scalar function, and a replacement needs them as well. Which command reads which table is in entry 3c
of [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md); `$0a` is the only one that reaches all four.

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

This project reproduces the DSP-1, never the DSP-1B. That is not a preference. The DSP-1B corrected
an arithmetic fault, the attract demo is a recording of button presses rather than a script, and
nobody re-recorded it, so on the corrected part the plane flies the same inputs into the ground
instead of landing. An sd2snes picks the DSP-1 for this cartridge and the Virtual Console releases
emulate this mask for the same reason.

So a routine here that is more accurate than the part is wrong, and visibly so. Entry 1 in
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) carries the measurement: the two masks answer every command
the game issues identically except `$28`, whose own handler is the same in both and whose
normalisation subroutines are not.

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

## Ask the three questions in the order the standard gives

The standard names them and this repository has got two of them wrong, so they
are worth restating with what the measurement here showed.

Which calculations the game can ask for is answered by reading the whole image.
[`commands.py`](commands.py) reads 20 command bytes out of every region, and the
recordings only ever produced 18 or 19, so the image reaches further than any run.

What range each argument takes is answered by [`exchanges.py`](exchanges.py),
which reports the lowest, the highest and the count of distinct values at every
position. Both figures go together: twelve of the nineteen commands hold a
position spanning the whole sixteen bit word while using a few thousand values
inside it, so a width without a distinct count reads as dense when it is sparse.

Which exact values are asked for is answered only by running the game, and it
does not close. Of the argument words written to the port, 7% are immediates
fixed in the image and 93% come from direct page, indexed or absolute reads, so
the image holds almost none of them.

Two mistakes made here are named in the standard and both were made in that
order. The first sized against the part's input domain, which made a feasible
table look impossible. The second called a run time value unknowable and stopped,
when its ends were one query away.

## A uniform arity is the check on a protocol read from a trace

A recording gives accesses, never a protocol. Turning one into the other is a
reading, and a reading needs something outside itself to be checked against.
Here that check is arity: a driver written by people gives each command a fixed
number of argument words, so a command that appears to take two different counts
is a defect in the reading rather than a fact about the part.

The first cut collected every write in a span into one tuple. Under it five of
the nineteen commands reported two counts, and the two always differed by exactly
four words. That constant is what gave it away. `$0a` writes one word, reads its
answer through four instructions that fire 176 or 191 times, and then writes four
words more, and those trailing four were being attributed to whichever command
came next.

Both repairs that suggest themselves are wrong, and the wrong one is the tempting
one. Handing the trailing writes to the next command turns a `$14` that always
takes six words into one that sometimes takes ten, which is worse than the defect
it was meant to fix. Keeping them where they are and separating them by position
leaves every command with one count in all three regions.

The distinction that survives is not about ownership. A write issued after the
part has begun answering cannot have decided that answer, so it is not part of
the key a table is indexed on, whoever it belongs to. `words` carries the writes
that could have decided the answer and `later` the writes that could not.

## Assembly is source, is commented line by line, and is fast

Three rules bind every `.asm` file in this repository, and a file that breaks any
of them is incomplete rather than merely untidy.

**Everything ships as source.** The `.asm` files are the deliverable. Nothing
assembled is checked in: no patched image, no object file, no symbol file, no
table pasted in as a block of numbers. A build produces those into an ignored
directory and a clone reproduces them from source. Where a table can be computed,
it is computed by the assembler at build time from the same expression that
describes it, because a table worked out where it is used cannot drift away from
the code that uses it and a table pasted in as numbers can.

**Every file is commented line by line, for a reader who does not know
assembly.** This is not the comment policy that governs the rest of the
repository, and the difference is deliberate. In a high level language a name
carries the meaning, so a comment restating it is noise that goes stale. In
assembly there are no names: there are registers, raw addresses and opcodes, and
nothing in `lda $2140` says what `$2140` is or why it is being read. So each file
opens with what it does and what a reader needs to know to follow it, each block
says what it is for, and each line that is not self-evident carries a short note
of what it does and why. A number that came from a measurement says which one.

**Performance is an absolute priority.** This code runs in place of a coprocessor
on a 3.58 MHz processor, inside a frame budget the game already spends. Every
routine is written for speed first:

- Count cycles, not instructions, and state the count where it matters.
- Prefer the shortest addressing mode that reaches: direct page over absolute,
  absolute over long. Direct page is one byte and one cycle cheaper per access.
- Keep the direct page pointed at the working set so the cheap mode is reachable.
- Stay in sixteen bit mode for anything that moves words; `rep`/`sep` pairs
  around a byte operation usually cost more than they save.
- Unroll the inner loop of anything that runs per scanline or per pixel. The
  branch and the counter are pure overhead there.
- Prefer a table lookup to arithmetic when the table fits, and arithmetic to a
  lookup when the arithmetic is a shift.
- Do not call a subroutine from an inner loop when it can be inlined; `jsr` plus
  `rts` is twelve cycles that compute nothing.
- Reach ROM through the fast mirror at banks `$80`-`$BF` when the cartridge is
  configured for it, which answers a fetch in six master clocks against eight.

A routine that is correct and slow is not finished. Where a faster form was
rejected, the reason is written down beside the slower one, because the next
reader will otherwise assume nobody thought of it.

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
| yaml | `uvx yamllint==1.38.0 --strict .` |
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

A store into the window is not a store the port sees. Those hot paths reach the
part through a bank this project fills with ROM, so every write is discarded and
every read comes back nought. Three commands are asked for that way, and one of
them, `$02`, deposits the whole of what `$0a` reads to draw the ground. A
replacement that answers `$02` perfectly and never has it asked is
indistinguishable, from the inside, from one that answers it wrongly. The only
thing that told the two apart was dumping the cartridge's own work RAM and
finding the argument buffer still holding the game's fill. Anything that claims
a command is answered checks that the port was asked, not only that the answer
is right.

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
- **A run replaced whole is bounded by its bytes, not by a site number.** A recording names a site by
  the program counter *after* the store, so a run built from site numbers is off by one at both ends,
  and one byte left over is an opcode: `$80` is a branch and `$09` is an or. Dump the bytes, find the
  instruction boundaries, and never begin a run at a `pea` that sets the data bank, because the `plb`
  that collects its byte can be a hundred bytes further on and skipping the push unbalances the
  stack.

## Bound the domain before building a table, never after

A table keyed on values taken from a recording covers the recording and nothing
else. That is not a small caveat, it is the whole behaviour of the thing: a
recorded-set table answers the run it was built from perfectly and answers a run
it has not seen almost never. Measure it and the gap is not subtle. Splitting one
recording in half and asking the second half what the first half learned, this
project's table answered 7.2% of calls. Asking it a different recording of the
same demo it answered 91.4%, and that number is worse than useless without the
first one beside it: the recordings are the same attract sequence, so the 91.4%
measures repetition and not coverage.

So the domain comes first, and it comes from the code.

**Do this in order, per calculation, before a single row is written.**

1. **Read the part's own program for what bounds each input.** A table lookup
   with a fixed size bounds its index. A mask bounds a word. A shift bounds a
   magnitude. A clamp bounds both ends. These are true bounds, independent of
   any recording, and they are the only kind that is.

2. **Read the calling code for what it can compose.** An argument built from a
   fixed table, a constant, or a quantised angle has a domain the caller decides
   and the image holds. This closes for the same reason the command census
   closes: it is a property of the image, not of a run.

3. **Size an exhaustive table over that domain.** Both the span of each word and
   the set of distinct values it can take, because they give very different
   answers when an input is quantised. This project has an argument whose span is
   32,769 and whose value set is seven, and the two sizings differ by four orders
   of magnitude.

4. **Choose per calculation, and record which case it is.**

   | case | what to build |
   |---|---|
   | the exhaustive table fits | build it. No miss is possible, and the fallback behind it becomes unreachable rather than merely unlikely |
   | it does not fit, but the arithmetic is readable | read the arithmetic. A routine covers the whole domain and costs no space |
   | neither | a recorded-set table, and say plainly that it covers the recording and what the holdout rate is |

5. **Publish the holdout for every calculation in the third case.** Build the
   table from part of the recordings and ask it the rest. A coverage figure with
   no holdout beside it is a claim about the data it was built from.

**A recorded-set table is the last resort, never the first move.** Reaching for
one before steps 1 to 3 have been done produces a table that looks finished,
measures well against its own inputs, and fails on a player. The failure is
silent, because a fallback answers and nothing reports that it did.

**Weight the effort by traffic, not by command count.** Three commands here are
77% of all calls. Making a rare command exhaustive while a heavy one is guessing
from its nearest neighbour is work in the wrong place.

**A miss is not the same as a wrong answer, and both get measured.** When a
fallback takes the nearest row, how near it is varies by orders of magnitude
between calculations: measured on real misses here, one command's nearest row is
never more than 26 out and another's is 23,154 out. The first is a near miss and
the second is noise. Which is which decides whether a recorded-set table is
tolerable for that calculation at all.

## Where the open questions are

[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) carries four, each with the measurement that would close it.
Read it before claiming anything about which mask is reproduced, which commands matter, or how large
the finished image needs to be. Nothing in this repository claims any of those three today.

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
