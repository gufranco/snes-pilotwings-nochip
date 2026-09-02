# Open questions

Every place a claim in this repository is narrower than it looks, with the measurement that would
close it. Four entries.

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

## 2. What Pilotwings actually asks for

**What is unknown.** The exchange shapes are read out of the cartridge's code, so they say which
accesses each routine makes. They do not say which command bytes those routines send, how often, or
with what arguments, because that is decided at run time by where the player is and what the aircraft
is doing.

**Why it matters here.** The sweep covers all 256 command bytes evenly. That is the right way
to measure the part, and it is the wrong way to weigh the work: a command Pilotwings never sends
costs nothing to get wrong, and the one it sends every frame decides whether the conversion keeps
pace. Without the census, any statement about which commands matter is a guess.

**What would close it.** Driving each cartridge under an emulator with every byte in and out of the
port recorded, then counting. The sibling project did exactly this for its own part and the recording
is what its correctness claim rests on.

**Until then.** No claim is made about which commands matter, and no work is prioritised by one.

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
