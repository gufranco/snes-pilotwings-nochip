# Pilotwings without the DSP-1

Tooling that builds Pilotwings images for all three regional releases with the DSP-1 coprocessor replaced by tables and 65816 code in the cartridge, held to the retail cartridges for what the game asks and to the part's own microcode for every answer.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-pilotwings-nochip/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**16** commands answered against the part on every question **3** regional recordings hold, **0** wrong answers, **43,440** of **43,440** `$0a` ground words exact, **1,055** tests, **100%** statement and branch coverage of every module, no dependencies outside the standard library and **5** pinned submodules

```python
import tables
import tabulate

for one in tables.KNOWN:
    print(f"{one.name:10} {one.count:3} words  first {one.values()[:3]}")
print(tables.table_bytes(), "bytes for all four")

for words in (1, 2, 3):
    print(words, f"{tabulate.bytes_for(words):,}", tabulate.storable(words))
```

```
reciprocal 128 words  first (32767, 32514, 32264)
sine       128 words  first (0, 804, 1607)
cosine     128 words  first (32767, 32758, 32728)
arccosine  256 words  first (16384, 16343, 16303)
1280 bytes for all four
1 131,072 True
2 8,589,934,592 False
3 562,949,953,421,312 False
```

The first loop rebuilds the four tables the DSP-1 carries in its data ROM from their formulas, which is what [`tables.py`](tables.py) searches the microcode for. The second sizes a table holding every answer to a command that reads one, two or three argument words: one word fits in a 96 Mbit cartridge and two do not. That line is why the replacement stores answers the game asks for and computes the rest.

## Install

### Step by step

Five steps from nothing to a working checkout. The doctor in step 4 confirms the first three.

1. **Install Python, git, and Docker if you will assemble.**

   | | Windows | macOS | Linux |
   |:--|:--|:--|:--|
   | Python 3.12 or newer | `winget install Python.Python.3.12` | `brew install python@3.12` | your distribution's `python3` package |
   | git | `winget install Git.Git` | `xcode-select --install` | your distribution's `git` package |
   | Docker, only for the assembler and the recording emulator | `winget install Docker.DockerDesktop`, then start Docker Desktop | Docker Desktop, or `brew install colima docker` then `colima start` | Docker Engine, then `sudo systemctl start docker` |

   On Windows, type `py -3.12` wherever this page says `python3`.

2. **Clone the repository. Do not download it.**

   ```bash
   git clone --recurse-submodules https://github.com/gufranco/snes-pilotwings-nochip.git
   cd snes-pilotwings-nochip
   ```

   > [!CAUTION]
   > Cloning is the only way to get a copy that works. The green **Code** button on GitHub also offers **Download ZIP**, and a ZIP never works here: the 5 models this project runs on are separate repositories pinned as git submodules, a ZIP carries none of them, and nothing can add them afterwards. The doctor names such a copy a downloaded archive; delete it and clone. A clone made without `--recurse-submodules` is repaired in place with `git submodule update --init --recursive`.

3. **Put your dump in `external/roms/`** under its name in [the dump list](#the-dumps): `pilotwings-usa.sfc`, `pilotwings-jp.sfc`, `pilotwings-eur.sfc`. The microcode goes in `external/firmware/`. Then check it; each dump you supplied should read `ok`:

   ```bash
   python3 tools/identify.py
   ```

4. **Run the doctor.** It checks the checkout, every model, each dump, and ends by naming the next thing to run:

   ```bash
   python3 doctor.py
   ```

   ```
     N checks, nothing to report
     next: python3 tools/identify.py
   ```

   A line marked `!` carries what to do on the line below it. The setup mistakes it catches:

   | The doctor says | Do this |
   |:--|:--|
   | `checkout: no git metadata` | Delete the folder and clone, step 2 |
   | `... is not checked out` | `git submodule update --init --recursive` |
   | `cartridge ...: missing` | Step 3 |

5. **There is no single build command yet.** The project is highly experimental: it records the game, builds tables and patches an image through the commands under [The interface](#the-interface), and many problems are expected. Reports are welcome.

### Requirements and the doctor

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any, to fetch the five submodules |
| Your own cartridge dumps | 524,288 bytes each, in `external/roms/` under the names in [The dumps](#the-dumps) |
| Your own copy of the DSP-1 microcode | 8,192 bytes, as `external/firmware/dsp1.bin` and `external/firmware/dsp1b.bin` |
| Docker | Any, only to build the assembler in [`asm/`](asm/) and the recording emulator in [`emu/`](emu/) |

Nothing is installed from a package index and nothing is downloaded. The five models this project measures itself against are git submodules at the repository root. A source archive from the download-zip link carries none of them, and the doctor names such a folder as one.

The microcode can sit anywhere `UPD7725_FIRMWARE_DIR` names instead of `external/firmware/`. Without it, every check that drives the part reports that it had nothing to run.

The doctor prints the machine, this project's version, whether the folder is a git clone, every model and its version, whether the microcode runs, which of the two masks are present, the state of each dump, and the report of each model's own doctor filed under that model's name. It exits 0 when every check passes and 1 otherwise. Paste its whole output into any bug report. On a fresh recursive clone with no dumps and no microcode it ends with:

```
  5 of 93 checks did not pass
  next: fix the first line marked ! above, then run python3 doctor.py again
```

The five are the missing microcode, the two masks the DSP model has no image for, and the empty `cartridges` directory each of two submodules ships.

## The interface

This is a set of scripts run from the repository root, plus the modules they are built from. A script that takes arguments prints a usage line and exits 2 without them.

### Commands

| Command | Arguments | What it does | Exit |
|:--|:--|:--|:--|
| `python3 doctor.py` | none | Reports the machine and the whole chain of models | 0 clean, 1 when a check did not pass |
| `python3 tools/identify.py` | none | Checks each file in `external/roms/` against [`artifacts.manifest.json`](artifacts.manifest.json) and prints the commands that compute a SHA-256 on macOS, Linux and Windows | 0 when every dump matches or is absent, 1 when one is wrong |
| `python3 exchanges.py <trace>` | a recording | Cuts the recording at each command site and prints every command with its exchanges, share, distinct argument sets, sites and how it can be answered | 0, 2 |
| `python3 tables.py <microcode image>` | an 8,192 byte image | Finds the four tables in the image's data ROM and prints the word each starts at | 0, 2 |
| `python3 microcode.py <mask>` | `dsp1` or `dsp1b` | Walks the microcode's dispatch for all 256 command bytes and prints each handler with the commands the cartridge writes | 0, 2 |
| `python3 layout.py <image> <bytes wanted>` | an image and a size | Finds runs of `$FF` or `$00` of 256 bytes or more and says whether the image holds the size without growing | 0, 2 |
| `python3 lut.py [<rows>]` | rows per table, default 65,536 | Sizes the four tables tabulated over a whole input | 0 |
| `python3 derived.py <mask> [<directory>] [--reindex]` | a mask, the output directory, default `build` | Drives the part for its reciprocal over `$4000` to `$7FFF` and its sine and cosine at 65,536 angles, and counts leading doublings for every word. Writes `reciprocal`, `recip-up`, `recip-down`, `recip-exponent`, `leading`, `sine` and `cosine` as 32,768 byte pieces named `<stem>-<n>.bin`. `--reindex` rebuilds the three `recip-` tables from a reciprocal already on disk | 0, 2 |
| `python3 state02build.py <mask> [<directory>]` | a mask, the directory holding the recordings and receiving the output, default `build` | Drives `$02` on every argument set the recordings hold and writes its three state tables, `state02-map.asm`, `state02-data.asm` and the clamped cosine at 65,536 angles | 0, 2 |
| `python3 lutbuild.py <mask> [<directory>]` | a mask, the output directory, default `build` | Builds the table of recorded answers from `build/trace-usa.bin`, `build/trace-jp.bin` and `build/trace-eur.bin`, completes `$13` and `$18` by driving the DSP-1, and writes `lut-<n>.bin`, `lut-map.asm` and `lut-axes.asm` | 0, 2 |
| `python3 patch.py <rom> <symbols> <out> <game bytes> [--slow]` | the assembled image, a symbol file of `name hex` lines, the output path, the length of the game inside the image | Points every access the cartridge makes to the part at the replacement, clears the coprocessor from the header, sets the size byte, sets the fast ROM bit unless `--slow` is given, and rewrites the checksum | 0, 1 when the image reaches no part, 2 |
| `python3 tools/cycles.py <image> <assembler log> [<routine>] [<snapshot>]` | an image, the assembler's printed symbols, default routine `ground_block`, default snapshot `build/nb2/wram-000300.bin` | Runs one call to the routine on the 65816 model and prints its cycles and instructions | 0, 1 without a snapshot, 2 |
| `python3 tools/profile.py <image> <symbol file> [<routine>] [<snapshot>] [--built]` | as above, plus `--built` when the snapshot already holds the built tables | Runs one call and splits its cycles by the label each instruction sits under, top 16 | 0, 1 without a snapshot or labels, 2 |

```bash
python3 tables.py external/firmware/dsp1.bin
```

```
  table        words   at     formula
  reciprocal     128    101  2^22 / (128 + k), rounded and clamped
  sine           128    280  sin(pi k / 128) x 32768, fraction cut off
  cosine         128    408  cos(pi k / 128) x 32768, fraction cut off
  arccosine      256    542  acos(k / 256) x 32768 / pi

  4 of 4 carried, 1,280 bytes to reproduce them all, against 131,072 for one table over a whole input
```

The same command on `external/firmware/dsp1b.bin` finds the sine, cosine and arccosine two words lower, at 278, 406 and 540, and the reciprocal at 101.

### The recording emulator

[`emu/`](emu/) builds `pwemu`, snes9x at commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2` with a hook on every DSP-1 port access, behind a minimal libretro front end.

```bash
docker build -t pwemu emu
docker run --rm -v "$PWD:/work" -e PWTRACE=build/trace-usa.bin pwemu external/roms/pilotwings-usa.sfc 12000
```

| Input | Meaning |
|:--|:--|
| `<rom> <frames>` | The image and the number of frames to run |
| `PWTRACE` | Path of the binary port log |
| `PWSCRIPT` | Input script, one `frame button...` per line, buttons named `up`, `down`, `left`, `right`, `a`, `b`, `x`, `y`, `l`, `r`, `start` and `select` |
| `PWRAM` | Path that receives every run of work RAM no frame changed, as `start end length` |
| `PWPC` | Path that receives the program counter sampled once a frame |

It ends with `RESULT load=ok frames=<n> delivered=<n> accesses=<n> brightness=<x>` and exits 0, or exits 1 when the image cannot be read or loaded.

Each record in the port log is 12 bytes, little endian: the frame as 32 bits, the program counter with its bank as 32 bits, the port address as 16 bits, 1 for a read or 0 for a write, and the byte moved. [`exchanges.py`](exchanges.py) and [`census.py`](census.py) read that format.

[`emu/native.cpp`](emu/native.cpp) runs the same recording through a libretro core loaded at run time, `native <core> <rom> <frames>`, and [`emu/play.cpp`](emu/play.cpp) opens a window on one, `play <core> <rom>`.

### The assembler

[`asm/Dockerfile`](asm/Dockerfile) builds asar v1.81. [`asm/nochip.asm`](asm/nochip.asm) is the entry file. It places the replacement in bank `$10`, includes every other `.asm` file in [`asm/`](asm/), and reads the tables the scripts above write into `build/`. Its printed `SYM <name> <address>` lines are what [`tools/cycles.py`](tools/cycles.py) reads.

### Dumps, versions and the models underneath

| Module | Call | Returns |
|:--|:--|:--|
| [`dumps.py`](dumps.py) | `artifacts()` | The three `Artifact` records: `name`, `region`, `filename`, `declares`, `accepted`, `provenance` |
| | `identify(data, digest=None)` | The `Artifact` whose SHA-256 matches, or `None` |
| | `identify_digest(digest)` | The same, from a digest already computed |
| | `diagnose(data, digest=None)` | A `Finding` with `kind`, `detail` and `repair`. `kind` is `match`, `copier-header`, `wrong-size` or `unrecognised` |
| | `digest_commands(filename)` | The SHA-256 command for `macOS`, `Linux` and `Windows` |
| | `manifest()`, `through()`, `not_this()` | The manifest, its sources, and the files it names to refuse |
| [`version.py`](version.py) | `VERSION`, `stamped(name, release=None)` | The release, and the file name an image of that release carries |
| [`hardware.py`](hardware.py) | `install(environment=None)` | Puts every model on `sys.path`, adds `external/firmware/` to `UPD7725_FIRMWARE_DIR`, and returns that variable |
| | `load(package)` | A model package: `mos65xx`, `snesdsp`, `mapper`, `romimage`, `snesdriver` or `upd7725` |
| | `root_of(package)` | The model's directory. Any other name raises `UnknownPackage` |
| [`tools/identify.py`](tools/identify.py) | `look(artifact, root)`, `judge(artifact, data)` | A `Looked` with `region`, `filename`, `state` of `ok`, `absent` or `wrong`, `detail`, and `ok` |

```python
import dumps
import version

for one in dumps.artifacts():
    print(one.region, one.filename, one.declares["chipset"], one.declares["map"])

for data in (bytes(524_288 + 512), bytes(1_000), bytes(524_288)):
    found = dumps.diagnose(data)
    print(found.kind, "|", found.detail)

print(version.stamped("pilotwings-usa"))
```

```
USA pilotwings-usa.sfc 0x03 0x20
Japan pilotwings-jp.sfc 0x03 0x20
Europe pilotwings-eur.sfc 0x03 0x20
copier-header | the file is 512 bytes longer than a bare dump, which is what a copier adds
wrong-size | 1,000 bytes, which is smaller than the 524,288 a dump holds
unrecognised | the right length, and its sha256 is 07854d2fef297a06ba81685e660c332de36d5d18d546927d30daad6d7fda1541, which none of the 3 declared dumps carries
pilotwings-usa-v0.1.0.sfc
```

A length, a chipset or a title never identifies a dump here, and the digest always does.

### Reading the cartridge's code

| Module | Call | Returns |
|:--|:--|:--|
| [`commands.py`](commands.py) | `accesses(rom)` | Every `Access` to the data port at `$8000` or the status port at `$C000`, long form in bank `$3F` or absolute. Each has `offset`, `mnemonic`, `size`, `register`, `way` and `long` |
| | `stores(rom)`, `store_at(rom, at)` | Offsets of stores to the data port, and the store at one offset |
| | `read(rom, disassemble)` | A `Site` per store, decoded back up to 512 bytes, with `command`, `narrow`, `issues` and `why` |
| | `commands(sites)` | The sorted command bytes those sites issue |
| [`sites.py`](sites.py) | `reached(rom)`, `census(rom)` | Where the long form reaches the part, through [snes-driver-python](https://github.com/gufranco/snes-driver-python), and a `Census` of `sites` and `shapes` |

```python
import commands

code = bytes.fromhex("8f 00 80 3f  ad 00 c0  8d 00 80  ea  af 00 80 3f")
for one in commands.accesses(code):
    print(one, one.long)
print(commands.stores(code))
```

```
<Access $00000 sta data write long> True
<Access $00004 lda status read absolute> False
<Access $00007 sta data write absolute> False
<Access $0000b lda data read long> True
(0, 7)
```

### Reading a recording

| Module | Call | Returns |
|:--|:--|:--|
| [`exchanges.py`](exchanges.py) | `taken(trace)` | Every `Exchange`, cut at the site that issued it: `site`, `command`, `words`, `answer`, and `later` for words written after the answer began |
| | `issuing(trace)` | The program counters that write the low half of the data port only, each with its one command byte |
| | `census(trace)`, `read(path)` | A `Census` with `commands`, `total`, `issued(c)`, `distinct(c)`, `share(c)`, `sites(c)` and `table_bytes()` |
| | `spans(census, command)` | A `Span` per argument position: `lowest`, `highest`, `distinct`, `width`, `bits`, and `dense` when the distinct values fill at least half the width |
| | `readings(runs, command)` | A `Reading` naming the earlier command whose arguments make the key decide the answer: `carrier`, `rows`, `ambiguous`, `pure`, `tabulatable` |
| | `tier_of(command, distinct)` | `computed` for `$00`, `inline` up to 16 argument sets, `table` above |
| [`census.py`](census.py) | `taken(trace)`, `exchanges(trace)`, `report(census)` | The same question cut at the byte stream, each read ending an exchange. `$0a` breaks that cut. A library only: running the file prints nothing |

```python
import struct

import exchanges


def access(pc, address, is_read, byte):
    return struct.pack("<IIHBB", 0, pc, address, is_read, byte)


def multiply(first, second, answer):
    out = access(0x00A000, 0x8000, 0, 0x00)
    for word in (first, second):
        out += access(0x00A010, 0x8000, 0, word & 0xFF)
        out += access(0x00A010, 0x8001, 0, word >> 8)
    out += access(0x00A020, 0x8000, 1, answer & 0xFF)
    out += access(0x00A020, 0x8001, 1, answer >> 8)
    return out


trace = multiply(0x1234, 0x5678, 0x0C4C) + multiply(0x1234, 0x5678, 0x0C4C) + multiply(2, 3, 0)
for one in exchanges.taken(trace):
    print(one, [hex(word) for word in one.words], [hex(word) for word in one.answer])

census = exchanges.census(trace)
print("\n".join(exchanges.report(census)))
for span in exchanges.spans(census, 0x00):
    print(span, span.width, span.dense)
```

```
<Exchange $00 from $00a000 2 words> ['0x1234', '0x5678'] ['0xc4c']
<Exchange $00 from $00a000 2 words> ['0x1234', '0x5678'] ['0xc4c']
<Exchange $00 from $00a000 2 words> ['0x2', '0x3'] ['0x0']
3 exchanges over 1 commands

  cmd   exchanges   share   distinct   sites   how to answer it
  $00           3  100.0%          2       1   computed
<Span 0 2..4660, 2 used> 4659 False
<Span 1 3..22136, 2 used> 22134 False
```

The trace is three `$00` exchanges in the recording format. The site at `$00A000` only ever writes one byte to the low half of the port, so it is the command site, and the two words after it are the arguments. `$0C4C` is the signed product of `$1234` and `$5678` with fifteen fractional bits, which is what the part answers.

### Asking the part

These drive the microcode through [snes-dsp-python](https://github.com/gufranco/snes-dsp-python), so each needs the microcode on the machine.

| Module | Call | Returns |
|:--|:--|:--|
| [`tabulate.py`](tabulate.py) | `shape_of(command)`, `sweep(model="dsp1")` | A `Shape` with `writes`, `reads` and `answers`, measured by writing one word more each time until the part falls silent |
| | `ask(command, words, reads=1)`, `deterministic(command=0)` | The answer bytes, and whether two identical questions answer alike |
| | `entries_for(words)`, `bytes_for(words, out=1)`, `storable(words)` | The size of a table over a whole input, and whether it fits in half of a 96 Mbit cartridge. These need no microcode |
| [`tables.py`](tables.py) | `KNOWN`, `carried(image)`, `find(words, table)`, `words(image)`, `table_bytes()` | The four `Table` records, where each sits in an image, and their size. `words` raises `WrongShape` on an image that is not 8,192 bytes |
| [`microcode.py`](microcode.py) | `program_of(mask)`, `dispatch(program)`, `handlers(program)`, `body(program, at)`, `listing(program)` | The 2,048 program words, where each command byte lands, and the instructions from a handler to its return |
| | `ISSUED` | The 19 command bytes the cartridge writes |
| [`derived.py`](derived.py) | `reciprocal(part)`, `refined(part, value)`, `trig(part)`, `ask(part, command, words, answers)` | The part's reciprocal over `$4000` to `$7FFF`, and its sine and cosine at every angle. `refined` raises `Runaway` after 200 instructions without returning |
| | `leading(value)`, `counted()`, `doublings(folded)`, `inverted(mantissas, negative)` | Leading-bit counts and the reciprocal reindexed for the ground routine. `inverted` raises `ValueError` on a table that is not 16,384 entries |
| | `write(where, values)`, `write_bytes(where, raw)`, `pieces(where)` | Write and read back 32,768 byte pieces. `pieces` raises `FileNotFoundError` when none exist |
| [`complete.py`](complete.py) | `domains(runs)`, `wanted(values)`, `filled(command, keys, answers, have)` | Every value each argument of `$13` and `$18` takes, every combination of them, and the answers driven out of the part for the combinations no recording holds |
| [`routines.py`](routines.py) | `run(image, entry, words, answers)`, `asked(command, words, answers)`, `inputs(count, how_many, seed)` | One assembled routine run on the 65816 model, the part's answer to the same question, and seeded random arguments. `run` raises `TooLong` after 40,000 instructions |

### The arithmetic read out of the part

| Module | Call | Returns |
|:--|:--|:--|
| [`attitude.py`](attitude.py) | `matrix(sine, cosine, five, six)` | The nine cells of the matrix `$02` builds, keyed by their scratch address `$5A` to `$7C` |
| [`raster.py`](raster.py) | `answer(state, start, lines, table)`, `scanline(state, line, table)` | `$0a`'s four answer words per scanline, computed the way the part computes them |
| | `product`, `normalise`, `reciprocal`, `scaled`, `shortfall(got, want)` | The stages, and how many scanlines of two answers agree |
| [`parameter.py`](parameter.py) | `GROUPS`, `CELLS`, `gathered(seen, slots)`, `fixed(runs)`, `mirrored(state)`, `sized(rows)` | Which of `$02`'s seven arguments each state word follows. `gathered` raises `Disagreement` when a key gives two states, and `mirrored` raises `NotMirrored` when the matrix is not two words twice |
| [`state02.py`](state02.py) | `packed(table)`, `checked(table)`, `rows(table)`, `stride(table)` | A keyed table as sorted little endian words. `checked` raises `Ragged` on rows of different widths and `TooWide` on a value outside a word |
| [`state02build.py`](state02build.py) | `gather(mask, where)`, `driven(part, sets)`, `tables(seen)`, `clamped(part)`, `checked(built)` | The three state tables, and `TooBig` when one passes a 32,768 byte bank |

```python
import attitude
import raster

print(raster.product(0x4000, 0x4000), raster.product(0x7FFF, -0x8000))
print(raster.normalise(0x0100), raster.normalise(-1), raster.normalise(0))
print(raster.scaled(0x2000, 14), raster.scaled(0x2000, 20), raster.scaled(0x2000, 2))

sine = [0x0000, 0x5A82]
cosine = [0x7FFF, 0x5A82]
cells = attitude.matrix(sine, cosine, 0, 1)
print({f"${at:02x}": f"${word:04x}" for at, word in cells.items()})
```

```
8192 -32767
(16384, 6) (-32768, 15) (0, 0)
4096 32767 1
{'$5a': '$5a81', '$5b': '$a57e', '$5c': '$0000', '$6a': '$5a81', '$6b': '$5a81', '$6c': '$0000', '$7a': '$0000', '$7b': '$0000', '$7c': '$7ffe'}
```

`product` multiplies two signed words with fifteen fractional bits. `normalise` shifts left until bits 15 and 14 differ and returns the shift count beside the result. `scaled` applies an exponent and clamps at `$7FFF`. The matrix is built at angle 0 for the fifth argument and at the angle whose sine and cosine are both `$5A82` for the sixth.

```python
import state02

table = {(2, 1): (10, -1), (1, 5): (20, 30)}
print(state02.rows(table), state02.stride(table))
print(state02.packed(table).hex(" "))

try:
    state02.packed({(1,): (2,), (3, 4): (5,)})
except state02.Ragged as error:
    print(error)
```

```
2 4
01 00 05 00 14 00 1e 00 02 00 01 00 0a 00 ff ff
row (3, 4) is (2, 1), an earlier row is (1, 1)
```

Rows are sorted by key so the cartridge finds one by halving, and each row is its key words followed by its answer words.

### Tables, the image and the patch

| Module | Call | Returns |
|:--|:--|:--|
| [`lutbuild.py`](lutbuild.py) | `rows_of(runs)`, `completed(built, runs)`, `chosen(built, calls, room)`, `gather(where)` | The recorded answers per command, keyed on `CARRIER` where the part keeps state, with `$13` and `$18` completed and the rest chosen by calls per byte |
| | `encode(tables)`, `sliced(raw)`, `banks(pieces, first)`, `source(pieces, first_bank)` | The table as the cartridge reads it, cut into banks from `$99` that skip `$7E` and `$7F`. `encode` raises `Uneven` when a row would start on an odd byte |
| | `axes(built)`, `axes_source(found)` | The commands whose keys are every combination of their values, and the code that counts their row instead of searching |
| | `CARRIER`, `COMPUTED`, `UNSTORABLE` | The carriers, the commands answered by arithmetic, `$00`, `$04`, `$08` and `$80`, and `$0a` |
| [`lut.py`](lut.py) | `KERNELS`, `expand(table, count)`, `blob(count)`, `cost(count)`, `image_bytes(count)` | The four tables interpolated over a whole input, and their size |
| | `plan(census, command)`, `planned(census)`, `table(runs, command, carrier)`, `encode(table)` | A table per command indexed on the range or on the recorded set, and its encoding |
| [`layout.py`](layout.py) | `runs(rom, least=256)`, `free(rom)`, `largest(rom)`, `fits(rom, wanted)`, `spread(rom, wanted)`, `must_grow(rom, wanted)` | Runs of `$FF` or `$00` as `(start, end)`, their total, the longest, and whether a size fits |
| [`patch.py`](patch.py) | `plan(rom, limit)`, `applied`, `spanned`, `hooked`, `rearmed`, `held`, `hooked_nmi`, `redirected`, `declared`, `checksummed`, `symbols(path)` | Each step the command runs, in that order. `held` raises `ArmGapTaken` when the six bytes it needs at `$07E84` are not empty, and `hooked_nmi` raises `VectorMoved` when the interrupt vector does not name `$F0A0` |

```python
import layout

image = bytes([0x42]) * 1_000 + bytes([0xFF]) * 600 + bytes([0x42]) * 10 + bytes(300)
print(layout.runs(image))
print(layout.free(image), layout.largest(image))
print(layout.fits(image, 500), layout.fits(image, 700), layout.must_grow(image, 1_000))
```

```
((1000, 1600), (1610, 1910))
900 600
True False True
```

## Status

Every command that returns anything answers exactly what the part answered, on every question the three recordings hold. What is left is speed, tracked in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md).

| Part | State |
|:--|:--|
| Dump identification, all three regions | By SHA-256 against [`artifacts.manifest.json`](artifacts.manifest.json) |
| Where each cartridge reaches the part | Both forms of the access, checked against a recording |
| Which commands the cartridge can issue | 20 in every image, checked against a recording |
| What the part answers | Its own microcode, run |
| Argument sets the recordings hold | 73,341 across three runs |
| The tables the part computes from | Four, 1,280 bytes, rebuilt exactly |
| The three tables no formula reproduces | Taken from the part, 294,912 bytes |
| `$02`'s state, which is everything `$0a` reads | Three tables from the part, 59,686 bytes, no key carrying two answers across all 6,980 argument sets |
| `$00`, `$08` and `$04` | 65816 arithmetic, exact against the part on 400 random argument sets each |
| The table of recorded answers | 12 commands |
| `$13` and `$18` | Complete over their whole domain, driven out of the part |
| The lookup | Exact on every recorded question, all three regions |
| The fallback | Answers every command, including keys no recording holds, without looping |
| `$0a` | 65816, exact: 43,440 of 43,440 answer words on 60 argument sets across all three recordings |
| The accesses through the redirected window | 200 three byte accesses each replaced with a three byte call, plus five runs replaced whole |
| Long accesses that compute with what they read | Seven routed, six `adc` and one `eor` |
| The game's own work RAM reads and writes through the window's bank | All 31 routed. [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md) section 30 |
| The demo | Flies, draws its ground, and tracks the retail cartridge's flight through game frame 405, the end of the comparison run. Work RAM differs by 30 to 60 bytes a frame, 22 of them at every frame and twelve of those a patched call the game copies into work RAM |
| The instrument panel | Drawn on every picture. Screen brightness across the demo has a spread of 0.05, at the retail cartridge's level. Section 32 |
| The band cut through the instrument panel | On 2.2% of frames. Section 48 |
| The ten words `$02` leaves behind | Computed or read from a table covering the whole key, all ten exact against the part on 596 frames spanning the demo |
| Image size | Grows, inside what a low cartridge addresses |

### Speed

| Measurement | Value |
|:--|:--|
| One call to `$0a`, averaged across 149 frames of the demo | 77,044 processor cycles |
| One call to `$0a` that is not the first | 130,147 cycles, steady to within 3% across 24 states of a flight |
| Scanlines whose distance matches the line above, so their answers are copied | 63.6% |
| Six table multiplies a scanline, as a share of `$0a` | 54.7% |
| Building the four multiply tables, outside any frame | 62,665 cycles |
| One lookup of 600 keys from a recording | 1,566,405 cycles |
| A frame when a read costs 8 master clocks | 44,671 processor cycles |
| The part, wall time the game was blocked per call | tens of cycles to about 250, about 2,700 a median frame of 43 calls |
| The arithmetic for `$00`, `$08` and `$04` | 398, 920 and 833 cycles |

Measured on the processor model, never on the console. A change moves where the demo sits when a measurement window opens, so the console's frame-rate meter is not monotone in work: adding 25,566 cycles of dead work to the ground made it report a better rate. Sections 36 to 39, 49, 51 and 52 carry the runs.

Across a whole game frame, sampled by program counter against the assembler's line map:

| Where | Share |
|:--|--:|
| The ground | 46.8% |
| The recorded-answer search | 20.6% |
| The game's own code | 15.4% |
| The port | 11.2% |

Two commands that need no search are emitted by [`lutbuild.py`](lutbuild.py) as code that counts their row. One of them is asked 9.4 times a game frame. Section 50.

### How much of the game the table covers

Built from part of the recordings and asked the rest:

| What was asked | Hit rate |
|:--|--:|
| The questions it was built from | 100% |
| A different recording of the same attract demo | 93.4% |
| The second half of a recording whose first half it learned | 11.2% |

All three recordings are the same attract sequence, so the middle figure measures repetition. The last is what a player doing something the demo never did meets. On that figure `$10` hits 10.9% and `$06` 0%. `$06` is 31.7% of every call the game makes.

`$13` and `$18` are not measured this way because they cannot miss. Their arguments are quantised: one of `$13`'s words spans 32,769 and takes seven values, so sizing by span says 5.48e17 rows and sizing by values says 1,512. Every combination was driven out of the part, and all 248 rows the recordings hold came back identical when driven the same way.

`$10` has a domain of 4,996 combinations and is not completed. Driven on its key alone it reproduces the recording 83 times in 100, so 17% of a filled row would be wrong. A missing row falls back to code and a wrong row does not.

### What the lookup answers

Driven on the processor model against the three recordings, forty questions per command per region:

| Command | Right | Wrong |
|:--|--:|--:|
| `$00` `$02` `$03` `$06` `$08` `$0c` `$0d` `$0e` `$10` `$13` `$14` `$1b` `$28` | 120 each | 0 |
| `$04` | 40 | 0 |
| `$18` | 10 | 0 |

The recordings hold fewer distinct questions for `$04` and `$18`.

## What was measured

### One replacement covers all three regions

Reading the code for stores to the data port, in both forms the cartridge uses, gives 208 in the USA image, 218 in the Japanese one and 208 in the European one. The twenty command bytes read out of them are the same twenty in all three.

The long form lands on two addresses in every region: 84 instructions at `$3f:8000` and 9 at `$3f:c000`, the same counts in all three. It is one driver three times over, so a replacement for one region is a replacement for the other two.

### Most of the driver is invisible to a search for the long form

The hot paths take the data bank once with `pea $003f` and `plb`, then use absolute stores that spell two bytes and name no bank. Measured against a recording of the Japanese image, which carries the program counter of every access:

| | Instructions | Long form | Absolute | Share of bytes moved by the long form |
|:--|--:|--:|--:|--:|
| Writing to the part | 118 | 40 | 78 | 62.2% |
| Reading from it | 47 | 13 | 34 | 7.9% |

[`commands.py`](commands.py) reads both. The hottest loop in the game is `sta $8000` after `plb`, followed by 176 passes of poll-and-read.

A search by encoding also reports bytes that are not instructions. In the USA image 29 of the 122 long-form matches sit at 29 different addresses across banks `$30` to `$3e`, one match each. Japan has 28 and Europe 30, and they are the whole of the difference between the three totals.

### How many words each command reads

Measured through the part's protocol: a command written one word short of what it wants still echoes, and written one word past it falls silent. The count is that silence stepped back one. It is checked against arithmetic: command `$00` answers the signed product of its two words with fifteen fractional bits, `0x1234 x 0x5678 -> 0x0C4C`.

Forty five of the 256 command bytes answer at all.

| Words in | Words out | Commands | A table of every answer |
|--:|--:|--:|:--|
| 1 | 1 | 2 | 131,072 bytes, which fits |
| 2 | 1 | 2 | 8,589,934,592 bytes, 683 times a 96 Mbit image |
| 3 | 1 | 14 | 562 TB |
| 4 | 1 | 7 | Larger still |
| 5 | 1 | 17 | Larger still |
| 6 | 12 | 1 | Larger still |
| 10 | 1 | 2 | Larger still |

Two commands can have every answer stored. The smallest of the other forty three is 683 times a 96 Mbit image. The table above sizes the part's input domain. What the game asks for is far smaller, and the sections below size that.

### What the game asks for

From a run of the Japanese image over 12,000 frames with no input, so the attract demo flies, 257,189 commands were issued from 30 sites. The NTSC images stop reaching the part after frame 10,418 and the PAL one is still flying at 11,999, which is why Europe issues `$04` and the other two never do.

| Command | Share | Issued | Sites | What it is |
|:--|--:|--:|--:|:--|
| `$06` | 28.9% | 74,261 | 2 | |
| `$13` | 25.4% | 65,332 | 1 | |
| `$00` | 15.0% | 38,668 | 10 | A signed multiply, computed |
| `$11` | 4.7% | 12,136 | 2 | |
| `$0a` | 2.7% | 6,946 | 1 | Answers with a stream read 176 times over |
| The other 13 | 23.3% | 59,846 | 14 | |

### Cutting a recording at the site that issued it

`$0a` answers with a stream the cartridge reads 176 times over, and the part accepts writes during that stream. A read inside one exchange then looks like the end of it, and cut that way a tenth of the runs hold writes from code more than 32 bytes apart.

[`exchanges.py`](exchanges.py) cuts at the command site instead. A program counter that only touches the low half of the data port issued a command, and one that touches both halves wrote argument words.

Across all three runs: 73,341 distinct argument sets over 19 commands, 586,728 bytes at one stored answer each.

| | Commands | Rows | Bytes | Share of traffic |
|:--|--:|--:|--:|--:|
| An inline compare chain | 5 | 22 | 176 | 30.5% |
| A table | 13 | 46,832 | 374,656 | 54.3% |
| Computed, being a multiply | 1 | none | 0 | 15.8% |

### What the part computes from

The uPD77C25 keeps 1024 words of data ROM beside its program. [`tables.py`](tables.py) rebuilds each candidate from its formula and searches for it. Four are there, word for word:

| Table | Words | Formula | Bytes |
|:--|--:|:--|--:|
| Reciprocal | 128 | `2^22 / (128 + k)`, rounded and clamped | 256 |
| Sine | 128 | `sin(pi k / 128) x 32768`, fraction cut off | 256 |
| Cosine | 128 | `cos(pi k / 128) x 32768`, fraction cut off | 256 |
| Arccosine | 256 | `acos(k / 256) x 32768 / pi` | 512 |
| | | **Total** | **1,280** |

There is no square root and no arctangent. Both masks carry the same four, the DSP-1B holding three of them two words lower.

### What range each argument takes

[`exchanges.py`](exchanges.py) reports the lowest, the highest and the count of distinct values at every argument position:

| What the positions look like | Commands | What a table indexes on |
|:--|--:|:--|
| One or a handful of values | 5 | The values, inline |
| A few thousand, filling their range | 2 | The range, 2^18 and 2^20 rows |
| At least one spanning the whole word | 12 | Nothing dense |

Command `$0d` takes about four thousand distinct values at each of three positions, and each runs the full 0 to 65,535. A table on the range would be 2^48 rows, almost all for inputs nobody sends, so both figures are always reported together.

### The part keeps state

Seven of the sixteen answering commands give different answers for identical arguments, because a command reading a matrix another command loaded is not a function of its own arguments. `$0e` takes one argument set in every recording and answers it 6,260 different ways.

Six of the seven become deterministic once the key also carries one earlier command's arguments, which is `CARRIER` in [`lutbuild.py`](lutbuild.py):

| Command | Keyed on its arguments and the last |
|:--|:--|
| `$03` | `$14` |
| `$06`, `$0d`, `$0e` | `$02` |
| `$13`, `$1b` | `$11` |

`$0a` is the seventh. No earlier command settles it, alone or in any pair or triple. Storing each distinct whole answer costs 16,762,160 bytes, and storing the four word steps costs 538,583 distinct steps before any index. It is computed instead: one normalise, one reciprocal, two multiplies and two shifts per scanline, read out of the part's program stage by stage and checked against its registers. Section 22.

### What the table encodes to

[`lutbuild.py`](lutbuild.py) sorts each command's rows by key, so the cartridge finds a row by halving. From the three recordings, before `$13` and `$18` are completed:

| Command | Keyed on | Rows | Key words | Answer words | Bytes |
|:--|:--|--:|--:|--:|--:|
| `$06` | Arguments and last `$02` | 75,278 | 10 | 3 | 1,957,228 |
| `$0d` | Arguments and last `$02` | 6,557 | 10 | 3 | 170,482 |
| `$02` | Arguments | 6,980 | 7 | 4 | 153,560 |
| `$0e` | Arguments and last `$02` | 6,980 | 9 | 2 | 153,560 |
| `$03` | Arguments and last `$14` | 5,268 | 9 | 3 | 126,432 |
| `$14` | Arguments | 4,406 | 6 | 3 | 79,308 |
| `$28` | Arguments | 6,182 | 3 | 1 | 49,456 |
| `$1b` | Arguments and last `$11` | 2,986 | 7 | 1 | 47,776 |
| `$0c` | Arguments | 3,480 | 3 | 2 | 34,800 |
| `$10` | Arguments | 2,498 | 2 | 2 | 19,984 |
| `$13` | Arguments and last `$11` | 244 | 7 | 3 | 4,880 |
| `$18` | Arguments | 4 | 4 | 1 | 40 |
| | | | | **Total** | **2,797,956** |

That is 86 banks of 32,768 bytes. A row carries its key as well as its answer, and `$06` spends ten words of key on three of answer because the part keeps state.

### What a recording can and cannot say

A recording says what the game did, never what it can do. Most arguments come from the aircraft's attitude and take a new value on almost every frame, so no recording shows their input set closing. Every command therefore has a fallback in code behind the table.

Reading the code answers the other half. [`commands.py`](commands.py) reads 20 command bytes out of every image, and Europe reads one more, `$80`. Against the Japanese recording it agrees on 27 of the 30 sites that ran, contradicts none, and is silent on three. Against the European one it agrees on 33 of 36 and contradicts none.

| | Commands |
|:--|--:|
| Read out of the code, all three images | 20 |
| Europe also reads | `$80` |
| The Japanese recording issued | 18 |
| The European recording issued | 19 |
| Read but never seen to run | `$21`, `$23` |

`$80` sends the part back to waiting for a command. The cartridge writes it 128 times in a row at `$0702a` to flush the part.

### Room in the retail image

[`layout.py`](layout.py) measures runs of one repeated byte, 256 bytes or longer:

| Region | Free in those runs | Largest single run |
|:--|--:|--:|
| USA | 63,122 | 4,249 |
| Japan | 74,207 | 8,395 |
| Europe | 63,122 | 4,249 |

Each holds the four 1,280 byte tables in one piece. The table of recorded answers does not fit, so the image grows. A run of one repeated byte is evidence that nothing uses it, so a candidate run is checked against the driver census before anything goes in it.

## The dumps

Named as No-Intro names them. Every digest is of the whole file with no copier header. SHA-256 decides, and CRC32 is there to cross-check against databases that still key on it.

| File | Read as | Size |
|:--|:--|--:|
| Pilotwings, USA | `external/roms/pilotwings-usa.sfc` | 524,288 |
| Pilotwings, Japan | `external/roms/pilotwings-jp.sfc` | 524,288 |
| Pilotwings, Europe | `external/roms/pilotwings-eur.sfc` | 524,288 |

| Region | SHA-256 | CRC32 |
|:--|:--|:--|
| USA | `03d0127f5de3237e22ad00de0c20763274da7b71142dde693240ac96d10983a3` | `266C44ED` |
| Japan | `d1845de22c3c7f2606bda20e09c8f7a78f92f5cbbb6bfe01f96a1d1e84b30394` | `77871727` |
| Europe | `f70a72f3d3a65497cdc4d849877a29cf4f7bd10439bb7f5cb8675cdfc0e706d4` | `DEF45776` |

All three declare version `0x00`. A Nintendo Campus Challenge cartridge built on this game is the same 524,288 bytes, declares the same chipset `0x03`, and carries the same internal title `PILOTWINGS`. Its map byte and its digests are the only things that tell it apart, which is why identification is by digest alone.

## The models underneath

| Model | Submodule | Held to |
|:--|:--|:--|
| 65816 | [mos65xx-python](https://github.com/gufranco/mos65xx-python) | A per-opcode suite, 5,120,000 cases |
| DSP-1 | [snes-dsp-python](https://github.com/gufranco/snes-dsp-python) | The part's own microcode, run |
| Cartridge map | [snes-mapper-python](https://github.com/gufranco/snes-mapper-python) | Every header combination in a library of real cartridges |
| ROM image | [snes-rom-image-python](https://github.com/gufranco/snes-rom-image-python) | The same library, rewritten and checked |
| Driver | [snes-driver-python](https://github.com/gufranco/snes-driver-python) | Where a cartridge's code reaches its coprocessor |

There is no graphics model. This part computes numbers and never touches a tile.

The 65816 model is the instrument every cycle count above comes from: it drives the bus cycle by cycle, so a routine costs the cycles it took. It starts with memory and registers holding reproducible scrambled values rather than zeroes, so a read of something never written shows up as a wrong answer.

## Where everything sits in the cartridge

A low cartridge carries banks `$00` to `$7D`. Everything this project adds is read through the mirror at `$80` and up, which answers a read in six master clocks against eight once `$420D` is set.

| What | Banks | Read through |
|:--|:--|:--|
| The game as it ships | `$00`-`$0F` | |
| The replacement's code | `$10` | `$90` |
| The sine and cosine taken from the part | `$11`-`$18` | `$91`-`$98` |
| The recorded answers | `$19`-`$6F` | `$99`-`$EF` |
| `$02`'s state, which `$0a` reads | `$70`-`$72` | `$F0`-`$F2` |
| The reciprocal taken from the part | `$73` | `$F3` |
| The window the game's redirected accesses land in | `$7D` | `$7D` |

Answering all twelve recorded commands takes 87 banks, 60 of them for `$06`. The image may grow to 96 Mbit whenever that buys fidelity, stability or speed. Every bank above `$7D` needs a windowed layout, so the image stays below it while it can. Images of 2 MiB and 4 MiB boot and run the demo identically once the header's size byte matches, and [`patch.py`](patch.py) sets that byte from the image's length.

## Is it right

Two oracles, and nothing here computes a DSP-1 result of its own. The retail cartridges decide what is asked: a command and an argument set are a question because a retail cartridge sends them. The part's microcode decides the answer, run through [snes-dsp-python](https://github.com/gufranco/snes-dsp-python).

| Claim | Held to | Where |
|:--|:--|:--|
| A dump is the dump | SHA-256 in [`artifacts.manifest.json`](artifacts.manifest.json) | [`tools/identify.py`](tools/identify.py) |
| Where the cartridge reaches the part | A reading of the code checked against a recording of a run, both ways | [`commands.retail.test.py`](commands.retail.test.py), [`sites.retail.test.py`](sites.retail.test.py) |
| What a routine answers | The same question asked of the part | [`routines.retail.test.py`](routines.retail.test.py), [`raster.retail.test.py`](raster.retail.test.py), [`attitude.retail.test.py`](attitude.retail.test.py) |
| The four tables | The microcode's data ROM, word for word | [`tables.retail.test.py`](tables.retail.test.py) |
| The patch | The retail images | [`patch.retail.test.py`](patch.retail.test.py) |

The checks that need a dump or the microcode live in the ten `*.retail.test.py` files, 87 tests that report themselves skipped when either is absent. They are kept out of the coverage measurement, because a machine with the artifacts runs one set of paths and a machine without them runs the other.

This project reproduces the DSP-1 and never the DSP-1B. The attract demo is a recording of button presses, and on the DSP-1B's corrected arithmetic the plane flies the same inputs into the ground. Which mask a retail board carries cannot be read from a dump. That question and every other claim narrower than it looks are in [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md), each with the measurement that would settle it.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-pilotwings-nochip/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy .
for t in *.test.py tools/*.test.py; do python3 "$t" || break; done
python3 -m coverage erase
for t in *.test.py tools/*.test.py; do python3 -m coverage run -a "$t"; done
python3 -m coverage report
```

1,055 tests across 41 files, one `<module>.test.py` beside each module. Coverage is a hard gate at 100% of statements and branches, set in [`pyproject.toml`](pyproject.toml). Commits follow Conventional Commits, and semantic-release cuts the version from them.

Comments appear in the assembly and only there: entry and exit state, register widths, and where each address came from. Python source carries none.

Never attach a cartridge or a microcode image to an issue, and never link to somewhere either can be downloaded. A digest identifies a file without carrying it.

## References

- No-Intro, for the names and digests of the three retail dumps.
- snes9x at commit `2971061cf07fdc6fc7d18883edf4e648eb16a6d2`, https://github.com/snes9xgit/snes9x, built by [`emu/Dockerfile`](emu/Dockerfile) to record every port access. The recordings are evidence about that emulator's DSP-1, which is why the lookup is checked against the part's own microcode rather than against them.
- asar v1.81, https://github.com/RPGHacker/asar, built by [`asm/Dockerfile`](asm/Dockerfile).
- neviksti's chip-free Star Ocean conversion, for the addressing rule for images larger than a low cartridge's address space.
- Nintendo EAD and Argonaut, for the game.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by [`scripts/set-version.sh`](scripts/set-version.sh), the script that stamps [`version.py`](version.py).

## License

MIT. See [LICENSE](LICENSE). It covers the tooling, the assembly and this document, and grants no rights in the game. No ROM data is distributed here: everything operates on dumps you supply.
