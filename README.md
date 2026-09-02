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
instructions at them. The image grows to hold what is stored; nothing about the board changes, and
there is no coprocessor left to emulate.

You supply the retail dumps. Nothing here contains game data, and nothing ever will.

## Status

Early. What is measured is written down below; what is not built is named in
[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) rather than implied.

| part | state |
|------|-------|
| dump identification, all three regions | works, against measured digests |
| where each cartridge reaches the part | works, both forms of the access, checked against a recording |
| which commands the cartridge can issue | 20 in every image, checked against a recording |
| what the part answers | works, by running the part's own microcode |
| whether an answer can be stored instead of computed | measured, per command |
| how many argument sets each command takes | withdrawn, see [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) entry 2c |
| the replacement in 65816 | not started |
| the finished cartridge | not started |

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

From a run of the Japanese image over 10,419 frames with no input at all, so the
attract demo flies rather than sitting on a menu, 257,189 commands were issued
from 30 sites. The traffic is not spread evenly:

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

### The sizing that used to be here has been withdrawn

An earlier version of this section sized tables against the number of distinct
argument sets each command was seen to take. Those figures were wrong, and the
cause was in [`census.py`](census.py) rather than in the recording.

The part answers at two registers, and which address is which is decided by
`DSP0.boundary`, which snes9x sets to `0xc000` for a low cartridge of this size.
So `0x8000` and `0x8001` are the two halves of one data port and `0xc000` and
`0xc001` are the status register. The census split on the lowest bit instead,
which is the convention some other coprocessors use. Two things followed. Every
argument word was rebuilt from the low bytes of two different arguments, because
the high byte of each was dropped as though it were status. And 1,482,010 status
polls were read as answers, so exchanges ended wherever the cartridge happened to
look at the ready bit.

The split is fixed. The sizing is not being restated, because a second fault sits
underneath it: an exchange was taken to be a run of writes ended by a read, and
command `$0a` breaks that. It answers with a long stream the cartridge reads in a
loop and takes writes during that stream rather than treating them as a new
command, so the rule splits one of those exchanges into pieces and joins the tail
of one to the head of the next. Ten per cent of the runs the old rule called
exchanges hold writes from code more than 32 bytes apart. Sizing tables from a
count taken that way would be sizing them from a reading of the byte stream.

What survives is the split the sizing was for, which the per-command counts above
still support: a handful of commands are most of the traffic, the multiply is
computed rather than stored, and the rest need measuring again.

### What a recording can and cannot say

A recording says what the game did. It cannot say what the game can do. Most of
these commands take arguments that come from the aircraft's attitude and take a
new value on almost every frame, so no recording will ever show their input set
closing, and a lookup with no entry for an unseen argument has no answer at all.
The design is therefore a table where the set closes and computation where it
does not, and never a table alone. Which commands fall on which side is the
measurement that has been withdrawn.

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

### What growing the image to 96 Mbit buys

Room. How much of it a replacement needs is not known, because the replacement is
not written and the sizing that would have bounded it has been withdrawn. What
can be said is the ceiling: a table for one scalar function a replacement might
compute from, a sine, a cosine, a reciprocal, a square root, an arctangent, is
131,072 bytes over its whole sixteen bit domain.

| | bytes |
|---|---:|
| the image at 96 Mbit | 12,582,912 |
| the retail cartridge inside it | 524,288 |
| left over | 12,058,624 |
| one table over a whole sixteen bit input | 131,072 |
| **tables that fit** | **92** |

Ninety two of those fit, which is far more than a replacement needs, so the
ceiling is not the constraint and this table settles nothing about which tables
are wanted.

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
| [`commands.py`](commands.py) | which command bytes the cartridge's own code can issue, both forms |
| [`census.py`](census.py) | what a recorded run asked the part for |
| [`tabulate.py`](tabulate.py) | whether a command's answers can be stored instead of computed |
| [`doctor.py`](doctor.py) | what is actually on this machine, the whole chain, printed for a bug report |
| [`version.py`](version.py) | the release number, rewritten by [`scripts/set-version.sh`](scripts/set-version.sh) |
| [`artifacts.manifest.json`](artifacts.manifest.json) | every dump this project reads, and what makes each one itself |
| [`tools/identify.py`](tools/identify.py) | checks a dump, and says what is wrong when it is |
| [`asm/`](asm/) | assembly that will go into the ROM |
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
