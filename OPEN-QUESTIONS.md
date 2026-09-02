# Open questions

Every place a claim in this repository is narrower than it looks, with the measurement that would
close it. Five entries.

A question is closed by evidence, never by a decision to stop asking. Until then the narrow claim
stands and the broad one is not made anywhere.

## 1. Which mask a retail Pilotwings board carries

**What is unknown.** The DSP-1 shipped in three masks. The DSP-1B corrected an arithmetic fault and
left the command set alone, so the two answer differently for some inputs while accepting the same
commands. Which mask a given board carries cannot be determined from a dump: nothing in the ROM
records it, and all three regions declare the same chipset byte.

**Why it matters here.** A replacement has to answer like the part it replaces. If a retail
Pilotwings board carries the uncorrected mask and this project reproduces the corrected one, the
conversion is arithmetically better than the cartridge and wrong for it. The family standard settles
which way that goes: a part's defects are modelled rather than corrected, because a model that
quietly fixes a hardware bug is wrong for the machine that shipped.

**What would close it.** Reading the part number off a retail Pilotwings board, for each region.
Failing that, driving a working cartridge through an input where the two masks are known to differ
and recording which answer comes back. The sibling that models the part carries a record of inputs
where they part company, so the second measurement has a known place to look rather than needing a
search.

**Until then.** Nothing here claims which mask is being reproduced. The doctor reports which masks
are present on the machine so a reader knows which question a run there could not have answered.

## 2. The recordings are three runs of the attract demo, not the game

**What is unknown.** Everything the census reports comes from three 12,000 frame
runs, one per region, with no controller input at all. That is the demo the game
plays to itself, which is a fixed sequence. Nobody has flown a lesson.

**Why it matters here.** The census is what sizes the tables, and it is a floor
rather than an answer. The set of distinct argument sets was still growing by
about 3,600 per 500 frames when the longest run ended, and the second half of
that run produced half of everything it found. A player working the controls
produces argument sets the demo never will, because thirteen of the nineteen
commands take arguments that track the aircraft's attitude and take a new value
almost every frame.

**What would close it.** It does not close. No recording can enumerate a set
that is a continuous function of player input. What can be closed is the
narrower question of which commands have a set that does not grow, and that is
what the split in the readme reports. Driving real lessons rather than the demo
would sharpen that split and would not change its nature.

**Until then.** No table is sized against the observed set as though it were
complete, and the design computes rather than looks up wherever the set grows.
A lookup with no entry for an unseen argument has no answer at all, which is why
the observed set is never the whole design.

## 2b. Twenty exchanges choose their command at run time

**What is unknown.** Reading the cartridge's code recovers the command byte for
11 of the 49 exchanges in the USA image, because those carry it in the
instruction. The other 20 load it from a register or a variable, and what values
those can hold has not been traced.

**Why it matters here.** It is the only route to an upper bound on which
commands the game can issue. The recordings give a lower bound of 19 commands;
the code gives 8, one of which no recording produced. Neither is the answer, and
the union of 20 is still a floor.

**What would close it.** Following the value backwards from each of those 20
sites to where it is set. If they read from a table in the cartridge, that table
enumerates every command the game can send and the question closes completely.

**Until then.** The command list is stated as what has been observed and what has
been read, with both counts given, and never as what the game can do.

## 3. Which scalar functions the commands are actually built from

**What is unknown.** The measurement says how many words each command takes and gives, and that is
the outside of the part. It does not say which functions the microcode composes to get there. The
list this project expects to tabulate, a sine, a cosine, a reciprocal, a square root and an
arctangent, is what a mathematical coprocessor of this kind normally carries, and normally is not a
measurement.

**Why it matters here.** The tables are the whole speed argument. Tabulating a function the part
never uses wastes 131,072 bytes and buys nothing; missing one it does use leaves a series in the
inner loop.

**What would close it.** Disassembling the microcode and reading what it computes, or fitting each
command's answers against candidate functions across its input domain and seeing which composition
reproduces them exactly.

**Until then.** No table is built. The count of 92 that fit is arithmetic about the image and says
nothing about which tables are wanted.

## 4. Whether the image needs to grow at all

**What is unknown.** The retail cartridge is 512 KB. This project may grow it to hold tables and
replacement code, up to the 96 Mbit ceiling a flash cartridge in common use will hold. How much is
actually needed is not known, because the replacement is not written.

**Why it matters here.** An image that fits the original address space needs no addressing work at
all. One that does not needs the windowed layout the sibling project uses, which is a substantial
piece of work and changes which emulators load the result.

**What would close it.** Writing the replacement and measuring it.

**Until then.** No layout is committed to and no size is claimed. The 96 Mbit figure in
[`tabulate.py`](tabulate.py) is a ceiling used to decide what cannot be stored, never a target.
