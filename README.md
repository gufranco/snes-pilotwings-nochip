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
| where each cartridge reaches the part | works, against the driver model |
| what the part answers | works, by running the part's own microcode |
| whether an answer can be stored instead of computed | measured, per command |
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

Every instruction in each dump that touches the part was found by asking the driver model, which is
held to a library of real cartridges rather than to a reading of them.

| region | sites | distinct exchanges |
|--------|------:|-------------------:|
| USA | 122 | 17 |
| Japan | 121 | 17 |
| Europe | 123 | 17 |

The seventeen exchange shapes are the same seventeen in all three. Sixteen of them occur the same
number of times in each region, and the counts differ only for the bare status poll, which is what
the three site totals differ by. That is the finding the shape of this project follows from: a
replacement written for one region is a replacement for the other two, and the PAL release is not a
separate problem.

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

### What growing the image to 96 Mbit actually buys

Not whole-command tables, which the measurement above rules out for all but two. What it buys is
tables for the scalar functions those commands are built from, and that is where the work goes.

The part is a mathematical processor. Its commands compose a small set of functions of a single
sixteen bit argument: a sine, a cosine, a reciprocal, a square root, an arctangent taken over a
ratio. Each of those covers its entire domain in 131,072 bytes. A replacement that computes a
rotation still has to take a sine, and taking it from a table is an indexed read rather than a
series.

| | bytes |
|---|---:|
| the image at 96 Mbit | 12,582,912 |
| the retail cartridge inside it | 524,288 |
| left for tables | 12,058,624 |
| one table over a whole sixteen bit input | 131,072 |
| **tables that fit** | **92** |

Ninety two is far more than the handful of scalar functions a DSP-1 replacement needs, so the
ceiling is not the constraint. Products need no table at all: the console has a hardware multiplier,
and command `$00` is exactly a signed multiply.

That is the shape this project takes. Tabulate the two commands that can be tabulated whole,
tabulate every scalar kernel at its full domain, use the console's multiplier for products, and
write 65816 for the composition that remains. The measurement is what decided the split rather than
a preference for one approach.

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
| [`sites.py`](sites.py) | where each cartridge reaches the part, and every distinct exchange |
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

227 tests across 10 modules. 212 need nothing but a checkout; 15 need a dump or the microcode and
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
- **What is not known is written down.** [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) carries every place
  a claim here is narrower than it looks, with the measurement that would settle it.

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
