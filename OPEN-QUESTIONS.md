# Open questions

Every place a claim in this repository is narrower than it looks, with the measurement that would
close it. Seven entries, one of them closed and kept because what closed it is worth reading.

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

## 2. The recordings are runs of the attract demo, not of the game

**What is unknown.** Every recording taken so far runs with no controller input
at all. That is the demo the game plays to itself, which is a fixed sequence.
Nobody has flown a lesson.

**Why it matters here.** Whatever sizes the tables is a floor rather than an
answer. A player working the controls produces argument sets the demo never
will, because most of the commands take arguments that track the aircraft's
attitude and take a new value on almost every frame. The European run reaches
further into the game than the Japanese one and issues command `$04` 511 times,
which the shorter run never issues at all: a difference in how far the demo got,
not in what the cartridge can do.

**What would close it.** It does not close. No recording can enumerate a set
that is a continuous function of player input. What can be closed is the
narrower question of which commands have a set that does not grow. Driving real
lessons rather than the demo would sharpen that split and would not change its
nature.

**Until then.** No table is sized against the observed set as though it were
complete, and the design computes rather than looks up wherever the set grows.
A lookup with no entry for an unseen argument has no answer at all, which is why
the observed set is never the whole design.

## 2b. Whether any exchange chooses its command at run time

**Closed.** None does. Every place the cartridge issues a command byte issues a
constant, and the reason it looked otherwise was that the search was reading the
wrong thing in two ways at once.

It read only the absolute long form of the access, which is a minority of this
driver: the hot paths take the data bank with `pea $003f` and `plb` and then use
ordinary absolute stores, which carry no bank and cannot be matched on four
bytes. And it looked for an immediate directly in front of a store, which misses
the idiom this cartridge actually uses, `ldy #$28` once at the top of a routine
and then `sty $8000` on every pass of the loop.

[`commands.py`](commands.py) reads both forms and carries the register forward.
It reads 20 command bytes out of every one of the three images, and `$80` out of
the European one as well. Checked against a recording of the Japanese image it
agrees with 27 of the 30 sites that were executed and contradicts none; against
the European one, 33 of 36 and again none. Every command either recording issued
is one the code reading also finds, except `$80` in Japan, whose site is real and
whose register widths are set further back than the decode window reaches.

**What is still narrow.** The reading is a lower bound on a per-site basis: three
sites in each image go unread rather than misread, and every store the search
cannot resolve is reported as unresolved rather than guessed at. A store whose
bytes are data that happens to spell one cannot be told from an instruction by
encoding alone, which is why the reading is checked against a recording rather
than trusted on its own.

## 2c. How large the observed argument sets actually are

**What is unknown.** How many distinct argument sets each command is asked for.
An earlier answer to this was published and has been withdrawn, because both
halves of the way it was counted were wrong.

The first half was the port split. The part answers below `DSP0.boundary`, which
snes9x sets to `0xc000` here, so `0x8000` and `0x8001` are the two halves of the
data port and `0xc000` and `0xc001` are the status register.
[`census.py`](census.py) split on the lowest bit instead, so every argument word
was rebuilt from the low bytes of two different arguments and 1,482,010 status
polls were counted as answers. That is fixed.

The second half is not. An exchange was taken to be a run of writes ended by a
read, and command `$0a` breaks that rule: it answers with a stream the cartridge
reads 176 times over and accepts writes during the stream rather than treating
them as a new command. Ten per cent of the runs the old rule called exchanges
hold writes from code more than 32 bytes apart, which is two routines' traffic
joined into one.

**Why it matters here.** It is what decides, per command, between a table and
arithmetic. The split itself survives without the numbers, because the
per-command traffic counts stand on the program counter rather than on the byte
stream, but the size of each table does not.

**What would close it.** Bounding an exchange by the site that issued it rather
than by the shape of the byte stream. The recording carries the program counter
of every access and [`commands.py`](commands.py) says which instruction issues a
command, so an exchange can be cut at the next command site rather than at the
next read, which is a rule command `$0a` does not break.

**Until then.** No table is sized, and no figure for the observed set appears
anywhere here.

## 2d. Two of the three recordings on the bench are not what they say

**What is unknown.** Nothing about the cartridge. This entry records the state of
the evidence, because a reader who re-runs the analysis here will not reproduce
what an earlier version of the readme reported.

The published figures were taken over three runs of 12,000 frames. Of the
recordings that produced them, the USA one is now 128 records long, which is the
first 1,536 bytes of a run and nothing after it. The Japanese one stops at frame
10,418 rather than 11,999. The Japanese and idle recordings are both exactly
188,081,652 bytes, which two independent runs do not produce by accident, so both
were cut. Only the European run reaches the frame count that was claimed.

**Why it matters here.** A figure in the readme is one somebody ran, and that is
only worth anything if the run it came from is still there to re-run. Two of
these are not, and the difference shows: the European run issues command `$04`
and the Japanese one never does, purely because it got further.

**What would close it.** Recording all three again, at a stated frame count, and
checking the length of each file against the count before reading it. The
recorder already prints how many accesses it made, and nothing compared that
against the file it wrote.

**Until then.** Every figure here names the recording it came from and the number
of frames that recording actually holds, rather than describing a set of three
runs as one measurement.

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
