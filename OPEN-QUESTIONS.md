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

**What is unknown.** How far snes9x's reimplementation of the part diverges from
the microcode, and therefore how far the census diverges from what a real board
would have produced.

The recorder hooks snes9x, whose DSP-1 is C code written from the outside rather
than the part's own program. Reading the two against each other turns up a
divergence immediately. The microcode dispatches a command byte through a tree of
bit tests, and `$80` lands on `$01ab`, which is the signed multiply, the same
routine `$00` reaches. snes9x sends `$80` to the default arm of its switch, which
takes no arguments and leaves the part waiting. Those are not the same behaviour,
and the cartridge writes `$80` 128 times in a row at `$0702a`.

**Why it matters here.** The census is not a passive observation. The game reads
the answers and computes its next arguments from them, so an answer that differs
sends the run down a different path and the argument sets that follow are the
ones snes9x produced rather than the ones a DSP-1 would. Every figure taken from
a recording inherits that.

**What would close it.** Driving the same command and argument stream through the
part's own microcode, which `snes-dsp-python` runs, and comparing answer for
answer. Where the two agree the recording stands; where they differ it does not.

**Until then.** A figure from a recording says what the game did against snes9x.
Nothing here has checked how much of that is the part.

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

**Measured.** [`lut.py`](lut.py) plans a table per command against one shared
cartridge budget, starting every command on the recorded set and spending the
budget to widen as many as it reaches to the range.

Four of nineteen come out complete over the range the game used: `$04` at
2,097,152 bytes, `$10` at 524,288, `$0e` at 8 and `$80` at 2. The whole table is
2,762,528 bytes, the image 3,286,816, and a 96 Mbit cartridge leaves 9,296,096
spare.

**What the headroom cannot buy.** The other fifteen each hold an argument
position spanning the whole sixteen bit word, so a table over their range is 2^32
rows at best and 2^96 at worst. That is not a budget away. Those fifteen are
answered from the recorded set, and they are exactly where the fallback is
reachable.

**What would close it.** Either the scalar decomposition of entry 3, where every
function takes one argument and 65,536 rows covers it outright, or a recording
that covers enough of the game that the sets stop growing, which entry 2 says
does not happen.

**Until then.** Four commands cannot reach the fallback. Fifteen can, and a build
reports how often they did rather than claiming they did not.

## 2i. The part keeps state, and a table keyed on arguments alone answers wrongly

**Measured, and it changes what a table has to be keyed on.** Seven of the
sixteen commands that answer give different answers for identical arguments. The
part keeps state, so a command reading a matrix another command loaded is not a
function of its own arguments, and a table keyed on them would return whichever
row happened to be written last.

| command | sets ambiguous on arguments alone | worst |
|---|---:|---:|
| `$06` | 137 of 3,551 | 2,798 answers for one set |
| `$0a` | 2 of 2 | 10,968 |
| `$0e` | 1 of 1 | 6,260 |
| `$03` | 412 of 2,775 | 12 |
| `$13` | 10 of 14 | 22 |
| `$0d` | 3 of 6,287 | 2 |
| `$1b` | 1 of 2,980 | 2 |

`$0e` is the one worth looking at twice. It takes exactly one argument set in
every recording, which made it the cheapest table in this repository's sizing at
eight bytes, and it answers that one set 6,260 different ways.

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

Keyed that way the whole table is 301,308 bytes and the image 825,596, against
12,582,912 in a 96 Mbit cartridge.

**What is left.** `$0a` is not tabulatable from these runs whatever it is keyed
on. It is the streaming command, answering 176 reads of four words from a matrix
loaded earlier, so its answer is the matrix rather than a row.

**Until then.** Eighteen of nineteen commands have a key that decides their
answer. `$0a` has none, and a build that tables it on arguments alone is wrong
rather than incomplete.

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
