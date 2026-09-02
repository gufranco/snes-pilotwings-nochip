# Open questions

Every place a claim in this repository is narrower than it looks, with the measurement that would
close it. Thirteen entries. The closed ones are kept, because what closed them is worth reading and
because two of them were closed once already with an answer that turned out to be wrong.

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

**How much it matters, measured.** Driving every argument set the three
recordings produced through both masks, sampled at 200 per command, the two agree
everywhere except one command:

| command | argument sets the game sends | masks agree |
|---|---:|---|
| `$28` | 6,182 | no, on 102 of 200 driven |
| the other 18 | 67,159 | yes, on every set driven |

So the mask decides one command out of nineteen, and that command is 2.3% of the
cartridge's traffic. Everything else a replacement answers is the same either
way. The tables are the same either way too, byte for byte, per entry 3b.

**Which mask snes9x reproduces, measured.** Replaying the European recording
through both masks and comparing against what snes9x answered, every command
scores identically on the two except `$28`, which agrees 18 times out of 172 on
DSP-1 and 172 times out of 172 on DSP-1B. So the emulator the recordings came
from reproduces the corrected mask on the one command that separates them.

That says what snes9x does. It does not say what a board does, and a replacement
built to match the recordings would inherit the emulator's choice rather than the
cartridge's.

**What would close it.** Reading the part number off a retail Pilotwings board,
for each region. Failing that, driving a working cartridge through `$28` and
recording which answer comes back: the sibling that models the part records a
divergent input for commands `$04`, `$0b`, `$1b`, `$24`, `$2b` and `$3b`, and the
measurement above adds `$28` on inputs the game itself sends, which is the easier
one to reach because the game reaches it unaided.

**Until then.** Nothing here claims which mask is being reproduced. The doctor
reports which masks are present on the machine so a reader knows which question a
run there could not have answered. A replacement may be written for all of it
except `$28` without the answer.

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

**How far from closing, measured.** Counting distinct argument sets as the
European run proceeds, the set is still climbing steeply when the run ends:

| frames | distinct sets | new in the last 500 |
|---:|---:|---:|
| 4,000 | 23,614 | 4,929 |
| 8,000 | 42,495 | 6,623 |
| 12,000 | 73,341 | 6,849 |

The final interval is one of the largest in the whole run. There is no flattening
anywhere, and this is the demo, which flies a fixed sequence with the controls
untouched.

**What would close it.** It does not close. No recording can enumerate a set that
is a continuous function of player input. What can be closed is the narrower
question of which commands have a set that does not grow. Driving real lessons
rather than the demo would raise the floor and would not change its nature.

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

## 2c. How large the observed argument sets are

**Closed.** 73,341 distinct argument sets across 19 commands, which is 586,728
bytes at one stored answer each, or 4.66% of a 96 Mbit image.

The figure published before this one was wrong twice over. The port split was
wrong, so every argument word was rebuilt from the low bytes of two different
arguments and 1,482,010 status polls were counted as answers; that was fixed in
[`census.py`](census.py). Underneath it the exchange boundary was wrong too: a
run of writes ended by a read is not an exchange, because command `$0a` answers
with a stream the cartridge reads 176 times over and accepts writes during it.

[`exchanges.py`](exchanges.py) cuts at the site that issued the command instead,
which is a boundary the byte stream cannot blur: a program counter that only ever
touches the low half of the data port issued commands, one that touches both
halves wrote argument words, and the recording carries the counter of every
access. A read inside an exchange is then an answer rather than a boundary.

The split that decides table against arithmetic falls out of it:

| | commands | rows | bytes | share of traffic |
|---|---:|---:|---:|---:|
| answered by an inline compare | 5 | 22 | 176 | 30.5% |
| answered by a table | 13 | 46,832 | 374,656 | 54.3% |
| computed, being a multiply | 1 | n/a | 0 | 15.8% |

`$13` is a quarter of all traffic and takes fourteen argument sets. `$0e` takes
one. The multiply is a sixth of the traffic and needs no table at all.

**What is still narrow.** This is what three runs of the attract demo produced,
which is entry 2 and does not close.

## 2d. One of the three recordings on the bench was not a recording

**Closed, and the claim that replaced it was wrong too.** An earlier version of
this entry said two of the three had been cut. Re-running all three at 12,000
frames settles it: the Japanese and European files are byte for byte identical to
fresh runs, and `trace-idle.bin` is a USA run rather than a truncated Japanese
one. Only `trace-usa.bin` was a stub, at 128 records, and it has been re-taken.

The two signals that looked like truncation both have ordinary explanations. The
Japanese and idle files are exactly the same length because a USA and a Japanese
run make exactly the same number of accesses, 15,673,471. And the Japanese run
stops at frame 10,418 because the NTSC images make no further access to the part
after that, not because the file ends: it ran all 12,000 frames. Europe reaches
11,999 because the PAL demo is still flying there, which is also why it is the
only run that issues command `$04`.

**What this cost.** An inference published as a finding. Two circumstantial
signals were read as proof of truncation when the measurement that settles it,
running the recorder again and comparing, was one command away.

**Until then.** The recorder prints the number of accesses it made and nothing
compared that against the file it wrote. Any future recording is checked that
way before a figure is taken from it.

## 2e. The recordings are the game against snes9x, not against a DSP-1

**Measured, by replaying a recording through the part's own microcode.** The
European recording was driven command for command into `snes-dsp-python`, writing
what the cartridge wrote and reading as many words as the cartridge read. Over
the first 7,184 answered exchanges:

| mask | agreed | differed |
|---|---:|---:|
| DSP-1 | 6,711 | 473 |
| DSP-1B | 6,865 | 319 |

**The disagreements are not drift.** Not one exchange read a different number of
words than the recording held, so the two never fell out of step, and agreement
resumes after every disagreement rather than stopping at the first. They
concentrate in six commands and leave seven untouched.

| command | agreed | differed |
|---|---:|---:|
| `$03`, `$0c`, `$13`, `$28` on DSP-1B | all | none |
| `$00` | 1,287 | 1 |
| `$0d` | 311 | 1 |
| `$06` | 2,068 | 12 |
| `$02`, `$10` | 172 each | 33 each |
| `$0a`, `$0e` | 172 each | 34 each |
| `$14` | 1 | 171 |

**Two candidate causes were ruled out.** The recording opens with 128 bare `$80`
writes carrying no arguments, and the microcode routes `$80` to the signed
multiply, which wants two words. Skipping that preamble entirely changed not one
figure, so it is not the cause. Nor is a stale part: the disagreements appear on
a part that has been driven through the same history the game gave it.

**How far the replay itself can be trusted, measured in blocks of 20,000.**

| exchanges | agreed | differed | rate |
|---|---:|---:|---:|
| 0 to 100,000 | 105,741 | 3,024 | 96.7% to 97.4% |
| 120,000 | 13,719 | 4,918 | 73.6% |
| 140,000 to 160,000 | 37,071 | 976 | 97.4% |
| 180,000 | 16,521 | 2,511 | 86.8% |
| 200,000 onward | 69 | 76,874 | 0.1% |

The replay holds near 97% for 200,000 exchanges, dips twice and recovers, then
loses the part and never recovers. `$00` is the control, being a signed multiply
that no state can change: it agrees 8,527 times of 8,542 through the first 60,000
exchanges and 23,212 of 44,289 over the whole run, which is the same break seen
from a command that cannot legitimately disagree at all.

So the steady 3% is the divergence and everything past 200,000 is the replay
rather than the part. Draining the part's output between exchanges was tried as
the repair and is worse: `$0d` falls from 311 agreed and 1 differed to 0 and 312,
because the drain consumes words the next exchange legitimately reads. What loses
the part at 200,000 is not yet known.

**Until then.** Seven commands' recorded answers are confirmed against the
microcode. Six are not, and `$14` is almost wholly unconfirmed. A table built
from recorded answers stores snes9x's answer wherever the two differ, so the
answers are taken from the part rather than from the recording, and the keys
alone come from the game.

## 2ee. Three recordings, one recording's worth of coverage

**Measured.** The three traces are different files with different digests, and
two of them ask the part exactly the same questions.

| recording | exchanges | distinct command and argument keys |
|---|---:|---:|
| USA | 257,189 | 62,319 |
| Japan | 257,189 | 62,319 |
| Europe | 280,622 | 68,951 |

The USA and Japanese key sets are equal, element for element. The European set
contains both and adds 6,632 keys, and lacks nothing either of them has.

**Why it matters.** Every figure here that says three recordings is really
reporting one, with the European run the only one that widens anything. A fourth
recording of the same attract demo in a fourth region would be expected to add
nothing either, so more regions is not the way to grow the set. Entry 2g's
driven run is, because it changes what the game does rather than where it was
sold.

**Until then.** Coverage figures name the European recording rather than the
count of recordings, because the count of recordings is not what produced them.

## 2f. What range each argument takes, and what that allows

**Measured, and it splits the commands three ways.** An argument computed at run
time still has ends, and [`exchanges.py`](exchanges.py) reports the lowest, the
highest and the number of distinct values at every argument position.

| what the positions look like | commands | what a table can be indexed on |
|---|---:|---|
| every position holds one or a handful of values | `$0a`, `$0e`, `$11`, `$13`, `$18` | the values themselves, in line |
| positions span a few thousand and fill them | `$04`, `$10` | the range, at 2^20 and 2^18 rows |
| at least one position spans the whole sixteen bit word | `$01`, `$02`, `$03`, `$06`, `$08`, `$0c`, `$0d`, `$14`, `$1b`, `$28` | nothing dense |

The last group is the one that matters and the reason a width alone misleads.
Command `$0d` holds about four thousand distinct values at each of three
positions, and each of those positions runs from 0 to 65,535. The values are
scattered through the range rather than filling it, so a table indexed on the
range would be 2^48 rows of which all but twelve thousand answer inputs nobody
sends. Only a table indexed on the set works there, and a set is what a recording
gives, which is entry 2.

**Where this leaves the sizing.** Five commands need no table. Two can be indexed
on their range, `$10` in 524,288 bytes and `$04` in 2 MB. The other twelve are
sparse and are either a set lookup or the scalar decomposition of entry 3.

**What is still narrow.** These ends are the ends of what was recorded. A run
that went further would widen them, so they are a floor like everything else a
recording gives.

## 2g. Driving the game rather than watching it

**Attempted, and it did not reach a lesson.** The recorder takes an input script,
so a run was made with menu presses followed by 384 varied stick and button
changes over 12,000 frames of the European image.

It moved 23,490,058 bytes through the port against the demo's 18,054,439, so it
was doing more, and it produced 134,317 exchanges against 280,622 and 86 distinct
argument sets against 73,341. It also never issued six commands the demo issues.
More traffic and a narrower set is what a menu looks like, not a lesson.

**Why it matters here.** Entry 2 says the observed set has to come from the whole
game. A script written without seeing the screen cannot be steered into a lesson,
so this is the wrong instrument rather than a finished measurement.

**What would close it.** An input script built against what the screen shows,
which the recorder can already produce and nothing here reads yet, or a saved
state that starts inside a lesson.

**Until then.** The observed set is the attract demo's, and the 68 sets this run
added are the only evidence here of what input does to it.

## 2h. Which commands a table can be complete for

**Measured, on the corrected cut.** Fifteen of the sixteen commands that answer
have a key that decides every answer they gave, and the table built from those
keys encodes to 2,988,940 bytes.

| | bytes |
|---|---:|
| the fifteen settled commands | 2,988,940 |
| the four scalar tables over their whole input | 524,288 |
| the game image | 4,194,304 |
| a 96 Mbit cartridge | 12,582,912 |
| left over | 4,875,380 |

The largest single table is `$06` keyed on its arguments and the last `$02`, at
75,278 rows and 1,957,236 bytes. The smallest is `$18` at four rows and 48 bytes.

**What the headroom cannot buy.** A table over the whole range of a command
taking more than one word is 2^32 rows at best, so the fifteen are indexed on the
set the recordings hold rather than on the range. That is where the fallback is
reachable, and entry 3 is what removes the reachability: every scalar function
takes one argument, so 65,536 rows covers each outright and a miss cannot happen.

**Until then.** Fifteen commands answer from a table. One does not, and it is
`$0a`.

## 2i. The part keeps state, and a table keyed on arguments alone answers wrongly

**Measured, and it changes what a table has to be keyed on.** Seven of the
sixteen commands that answer give different answers for identical arguments. The part
keeps state, so a command reading a matrix another command loaded is not a
function of its own arguments, and a table keyed on them would return whichever
row happened to be written last.

**What settles it.** Six of the seven become fully deterministic once the key
carries the arguments of one earlier command as well:

| command | keyed on | rows | ambiguous |
|---|---|---:|---:|
| `$03` | its arguments and the last `$14` | 5,268 | 0 |
| `$06` | its arguments and the last `$02` | 75,278 | 0 |
| `$0d` | its arguments and the last `$02` | 6,557 | 0 |
| `$0e` | its arguments and the last `$02` | 6,980 | 0 |
| `$13` | its arguments and the last `$11` | 244 | 0 |
| `$1b` | its arguments and the last `$11` | 2,986 | 0 |

**What is left.** `$0a` is not tabulatable by value from these runs, and that is
now measured three separate ways rather than asserted once.

| what was tried | what it cost |
|---|---|
| every single earlier command as the carrier | every row still ambiguous |
| every pair and triple drawn from `$01`, `$11`, `$80`, `$02`, `$06`, `$0e` | every row still ambiguous |
| storing each distinct whole answer | 10,970 answers of up to 764 words, 16,762,160 bytes, over a 96 Mbit cartridge on its own |
| storing the four word steps and indexing them | 538,583 distinct steps, 4,308,664 bytes for the steps before any index array |

The shape says why. `$0a` writes one word, reads its answer through four
instructions that each fire 176 or 191 times, and then writes four words more.
The answer is a per scanline stream rather than a row, and its content comes from
state accumulated over many earlier commands rather than from anything in the key.

**Where it goes instead.** `$0a` reads the reciprocal table in the part's own
data ROM, which entry 3 has already tabulated over its whole input. So `$0a` is
answered from that table by code, and it is the only command that is. That is a
lookup with a complete table underneath it, not a fallback: a miss cannot happen
because every value the reciprocal takes has a row.

**Until then.** Fifteen of sixteen commands answer from a table keyed on
recorded values. `$0a` answers from the scalar tables, which are exhaustive.

## 3. Which scalar functions the commands are built from

**Closed, and the expected list was wrong in three places.** The part carries
1024 words of data ROM alongside its program, and what a microcode interpolates
from is written down in there in plain sixteen bit words.
[`tables.py`](tables.py) rebuilds each candidate from its formula and searches for
it rather than recognising it by eye. Four are there, each to within one unit,
which is rounding:

| table | words | formula | at, DSP-1 | at, DSP-1B |
|---|---:|---|---:|---:|
| reciprocal | 129 | `2^22 / (128 + k)` | 101 | 101 |
| sine | 128 | `sin(pi k / 128) x 32767` | 280 | 278 |
| cosine | 128 | `cos(pi k / 128) x 32767` | 408 | 406 |
| arccosine | 256 | `acos(k / 256) x 32768 / pi` | 542 | 540 |

There is no square root and no arctangent, and nothing expected an arccosine.

**What it changes.** The whole sizing argument. The four together are 1,282
bytes, against the 131,072 a single table over a whole sixteen bit input takes,
so the count of how many such tables a grown image holds was an answer to a
question the part does not ask. A replacement carries what the part carries,
about a kilobyte, and interpolates the way the microcode does, which is also the
only way to be exactly right rather than close.

**What is still narrow.** Which of the four each command composes, and in what
order, is not read here. That needs the program rather than the data ROM. What is
settled is the set a replacement must carry, which is what the sizing depended on.

## 3b. What the two masks do with those tables

**What is unknown.** The DSP-1 and DSP-1B carry the same four tables, byte for
byte, and the DSP-1B holds three of them two words lower. That shift is the whole
of the difference between their data ROMs, so whatever the DSP-1B corrected it
corrected in the program.

**Why it matters here.** It narrows entry 1 without closing it. A replacement
reproducing the tables reproduces both masks' tables, so the mask question is
about the arithmetic around them rather than about the numbers themselves.

**What would close it.** Reading the two programs against each other. The images
are 2048 words of twenty four bit instructions and the two differ, so a
disassembly would say where.

## 4. Whether the image needs to grow at all

**What is unknown.** The retail cartridge is 512 KB and the replacement is not
written, so what it costs is not measured. What has changed since this entry was
written is that the tables are no longer the reason to grow it. The part carries
1,282 bytes of them, per entry 3, and the argument sets a table would answer from
are 586,728 bytes at the widest reading, per entry 2c. Neither needs a 96 Mbit
image, and the smaller of the two fits in what a 512 KB cartridge already has
spare.

**Why it matters here.** An image that fits the original address space needs no
addressing work at all. One that does not needs the windowed layout the sibling
project uses, which is substantial and changes which emulators load the result.
The evidence now points at the first, which would remove that work entirely.

**What would close it.** Writing the replacement and measuring it.

**Until then.** No layout is committed to and no size is claimed. The 96 Mbit
figure in [`tabulate.py`](tabulate.py) is a ceiling used to decide what cannot be
stored, and on the current evidence it is a ceiling nothing here approaches.
