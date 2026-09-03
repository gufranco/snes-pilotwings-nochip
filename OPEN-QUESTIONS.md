# Open questions

Every place a claim in this repository is narrower than it looks, with the measurement that would
close it. Thirteen entries. The closed ones are kept, because what closed them is worth reading and
because two of them were closed once already with an answer that turned out to be wrong.

A question is closed by evidence, never by a decision to stop asking. Until then the narrow claim
stands and the broad one is not made anywhere.

## 1. Which mask a retail Pilotwings board carries

**Answered: the DSP-1, and not the DSP-1B.** Kept as an entry because what
settles it is the game's own behaviour rather than anything in the dump, and
because the reason matters to every routine this project writes.

**What was unknown.** The DSP-1 shipped in three masks. The DSP-1B corrected an arithmetic fault and
left the command set alone, so the two answer differently for some inputs while accepting the same
commands. Which mask a given board carries cannot be determined from a dump: nothing in the ROM
records it, and all three regions declare the same chipset byte.

**Why it matters here.** A replacement has to answer like the part it replaces. If a retail
Pilotwings board carries the uncorrected mask and this project reproduces the corrected one, the
conversion is arithmetically better than the cartridge and wrong for it. The family standard settles
which way that goes: a part's defects are modelled rather than corrected, because a model that
quietly fixes a hardware bug is wrong for the machine that shipped.

**Which mask, answered from outside.** The dump does not say, and the behaviour
of the game does. Pilotwings carries the DSP-1 or the DSP-1A, never the DSP-1B,
and the way anybody can check is the attract demo: on a DSP-1 the plane lands,
and on a DSP-1B it crashes.

The reason is that the DSP-1B is more accurate. Its arithmetic fix changed the
answers the flight model gets, the demo is a recording of button presses rather
than a script, and nobody re-recorded it. So a more correct part flies the same
inputs into the ground. Reported at
[Nintendo Life](https://www.nintendolife.com/news/2019/05/random_the_captivating_mystery_of_pilotwingsr_crashing_plane)
and
[ResetEra](https://www.resetera.com/threads/pilotwings-snes-do-you-own-the-safe-landing-or-plane-crash-version.175182/),
and acted on by hardware and by Nintendo: an sd2snes picks the DSP-1 for this
cartridge, and the Virtual Console releases emulate this mask rather than
reusing the DSP-1 emulation from other games.

**So this project reproduces a part that is wrong on purpose.** The family
standard already says a part's defects are modelled rather than corrected,
because a model that quietly fixes a hardware bug is wrong for the machine that
shipped. This is that rule with a visible consequence: correcting the arithmetic
crashes the plane.

**Where the difference sits, read out of the program.** Both masks answer every
command the game issues identically except `$28`, and `$28`'s own handler is the
same instruction for instruction in both. It reads three words, sums their
squares, and calls three subroutines, which makes it a vector length. Two of
those three differ:

| subroutine | what differs |
|---|---|
| `$0042` | nothing |
| `$0077` | the DSP-1 opens with `call $003A` and the DSP-1B does not |
| `$0123` | reordered, and the DSP-1B reaches a different constant |

So the correction is in the normalisation that follows the sum of squares,
which is what a length needs and what an accuracy fix would touch.

**What this costs the recordings.** They were made against snes9x, and snes9x
answers `$28` the way a DSP-1B does, measured at 172 of 172 exchanges against
18 of 172 for the DSP-1. The recordings are therefore of the crashing demo, not
the one a cartridge plays. Every argument the game computed after the first
`$28` it disagreed on is an argument the real machine would not have produced,
which is the same mechanism entry 2e already reports from the other side and is
now the more likely reason a replay stops staying in step.

**What is settled and what is not.** That this cartridge wants a DSP-1 is
settled well enough to build on. Which of the DSP-1 and the DSP-1A a given board
carries is still not readable from a dump, and does not matter here: the two
differ in manufacture rather than in program.

**What the cartridge database says, and what it does not.** The DSP model's
manifest names `dsp1` for all three Pilotwings regions, and says in the same
entry that which of the three masks a board carries is not determinable from a
dump. So the family is settled and the mask is not, which is this entry.

**How far apart the two masks actually are, measured.** The manifest also says
the DSP-1B "corrected an arithmetic fault and left the command set alone". The
command set is indeed untouched, and the rest understates it:

| | words differing |
|---|---:|
| program, compared position for position | 993 of 2,048 |
| program, after shifting one to line them up | 427 of 2,048 |
| data ROM, position for position | 537 of 1,024 |

The shift is real: the DSP-1B holds its tables two words earlier and its
handlers one word earlier, and lining the programs up on that shift takes the
matching words from 1,055 to 1,620. What is left after it is 427 words that
genuinely differ, which is a fifth of the program rather than a corrected fault.

**The four tables are the same in both.** Each of the four is found in both
masks by its formula with nothing forgiven, at word 101, 280, 408 and 542 in the
DSP-1 and 101, 278, 406 and 540 in the DSP-1B. Identical values, different
seats. Anything built from the formulas is therefore right for either mask, and
[`asm/dsp1-tables.asm`](asm/dsp1-tables.asm) is.

**The dispatch is the same shape in both.** Walking the tree for all 256 command
bytes gives 20 handlers in each, with the same commands reaching the same
handler, every address one word apart. `$00` and `$80` share a handler in both,
which is the difference from snes9x recorded in entry 2e.

**So the mask decides one command.** Everything the game issues answers
identically on both except `$28`, which is what the earlier replay showed from
the other direction: 6,711 of 7,184 answered exchanges agree under the DSP-1 and
6,865 under the DSP-1B, the whole of the difference being `$28`.

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

**Until then.** This project reproduces the DSP-1. The doctor
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

**Why it cannot be repaired, and why 70% is the ceiling.** Restarting the replay
at exchange 240,000 on a fresh part scores 6.3%. Priming it first with the 200
exchanges before that point scores 6.7%, and priming with 5,000 scores 6.7% as
well, the same number to the answer. State saturates almost at once and is still
wrong, so no amount of priming reaches it.

That names the mechanism. The game computes its next arguments from the answer it
was given, and it was given snes9x's. Wherever the two parts differ, every
argument after that point is one the real part would never have been asked. The
recorded stream stops being a stream the part could have produced, so a replay
cannot follow it however it is started. Rows whose keys appear only past that
point can never take an answer from the part, and they are 30% of the table.

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

**What is left.** `$0a` still has no row, but the reason has changed and the
earlier reason was wrong. It was recorded here as ambiguous under every carrier,
and that measurement was taken before the exchange cutter separated the writes
that follow an answer from the writes that precede it. `$0a` is the command that
separation exists for: it writes one word, streams its answer, then writes four
more. With the four trailing words no longer in its key, the measurement comes
out the other way.

| carrier | keys | ambiguous |
|---|---:|---:|
| none, its own argument only | 2 | 1 |
| the last `$02` | 6,980 | 0 |

Nought ambiguous, in all three recordings, which is the same result the six
state-dependent commands give. `$0a` is a function of its argument and `$02`'s.

What rules it out is size alone.

| what was measured | what it costs |
|---|---:|
| distinct answers, USA and JP recordings | 5,232 each |
| distinct answers, European recording | 5,738 |
| positions of the 764 that ever differ | 764, so nothing factors out as constant |
| the European recording stored whole | 8.7 megabytes, against 3.9 for the entire cartridge |

**Where it goes instead.** Not into the table, and for now not into a routine
either. [`asm/dsp1-fallback.asm`](asm/dsp1-fallback.asm) answers `$0a` with 764
words of nought: bounded, deterministic, reading no memory it has not set, and
obviously wrong rather than plausibly wrong. It is the one command of sixteen
whose answers are not right.

**What would close it.** Reading the arithmetic out of the part's own program.
That the answer is an exact function of `$02`'s arguments is what says the
arithmetic is there to be read, rather than state that has to be remembered.

**Until then.** Fifteen of sixteen commands answer from the table exactly, on
every question the three recordings hold. `$0a` answers nought.

## 2i2. A recorded-set table covers the recording, and that was measured late

**Measured.** Coverage was taken by holdout: build the table from part of the
recordings and ask it the rest.

| what was asked | hit rate |
|---|---:|
| the questions it was built from | 100% of 253,933 calls |
| a different recording of the same attract demo | 93.4% |
| the second half of a recording whose first half it learned | 11.2% |

The middle figure measures repetition rather than coverage. All three recordings
are the same attract sequence flying the same path, so the European run mostly
repeats questions the other two already asked. Quoted on its own it is
misleading, and the last figure is the one that describes a player.

Per command on the last figure: `$13` 39.4%, `$10` 10.9%, `$00` 5.4%, and `$06`
0% of 39,766 calls.

**How wrong a miss is.** Measured on the 21,850 real misses from the middle
scenario, worst error across the answer words:

| command | worst | within 16 |
|---|---:|---:|
| `$1b` | 1 | all |
| `$13` | 26 | 61% |
| `$03` | 73 | 56% |
| `$06` | 1,820 | none |
| `$0e` | 23,154 | none |
| `$08` | 26,912 | none |

`$1b` and `$13` degrade into a near neighbour. `$0e`, `$0c` and `$14` do not:
adjacent keys carry answers tens of thousands apart, so the nearest row there is
noise rather than an approximation.

**What was done about it.** The domain of each command was sized two ways, by the
span of each argument word and by the set of distinct values it takes, because a
quantised word makes those differ by orders of magnitude. `$13` spans 5.48e17 and
holds 1,512 combinations; `$18` holds 48. Both reproduce the recording exactly
when driven on the key alone, so both were completed out of the part and neither
can miss now. `$10` has only 4,996 combinations and was deliberately not
completed: it reproduces 83 times in 100, so 17% of any filled row would be
wrong, and a wrong row does not fall back.

**What is left.** `$06` is 31.7% of every call, has 75,278 rows, sizes at 5.78e23
combinations, and answers nothing on unseen flight. No table reaches it. Its
arithmetic is the single highest-value thing left to read, and `$14` and `$0d`
follow it for the same reason.

**What this changed in how the work is done.** The domain is now derived before a
table is built rather than after, and the rule is in
[AGENTS.md](AGENTS.md). Building the recorded-set table first and measuring its
coverage afterwards is what produced a table that looked finished and answers
11.2% of a run it has not seen.

## 2j. A key that indexes an answer is not the state that produces it

**Measured.** The six state-dependent commands are keyed on their arguments plus
one earlier command's, and that key leaves nothing ambiguous across all three
recordings. So the key indexes the recorded answers correctly.

It does not follow that the key holds the state the part needs, and it does not.
Driving each key in isolation, resetting the part, writing the carrier command
with its recorded arguments, then writing the target command, reproduces the
answer the same part gave during a replay only for the commands that carry no
state at all:

| command | isolated drive reproduced the replay |
|---|---:|
| `$00`, `$08`, `$0c`, `$13`, `$18`, `$1b`, `$28` | 100% |
| `$06` | 92% |
| `$10` | 83% |
| `$02`, `$0e` | 78% |
| `$0d` | 51% |
| `$03` | 5% |
| `$14` | 0% |

`$13` and `$1b` are the interesting rows. Both are keyed on a carrier, and both
reproduce perfectly, so a carrier in the key does not by itself mean the part
needs more than the key. `$14` is the opposite extreme: it carries no carrier in
its key and reproduces nothing, so a key with no carrier does not mean the
command is stateless.

**What this changes and what it does not.** It does not make the table wrong. A
table stores what the part answered, and the key is what finds the row. It does
mean the key cannot be used to regenerate a row: a row missing from the table
cannot be filled in by driving the part on its key alone, because the part will
not be in the state that produced it.

**Why that matters here.** It closes the cheapest route to raising the share of
rows whose answer came from the part rather than from the recording. That share
is bounded by how far a replay stays in step, which is entry 2e.

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

## 3c. Which table each command reads, and what else it reads

**Measured, by watching the data ROM while the part runs the game's own command
stream.** Every read of the part's 1024 word constant store was recorded across
60,000 exchanges of the European recording, with `$00` agreeing 8,527 times of
8,542 as the control that the replay stayed in step.

| command | tables it reads |
|---|---|
| `$0a` | reciprocal, sine, cosine, arccosine |
| `$02` | reciprocal, sine, cosine |
| `$11` | reciprocal, sine, cosine |
| `$01`, `$0c` | sine, cosine |
| `$06`, `$0e`, `$10`, `$13`, `$14`, `$28` | reciprocal |
| `$00`, `$03`, `$0d` | none of the four |
| `$80` | nothing at all |

`$0a` is the only command that reaches all four, and the only one that touches
arccosine. It is also the widest reader by far, at 852 distinct seats against 239
for the next.

**The four tables are not everything the handlers read.** Across 30,000
exchanges the handlers read 315 of the 1024 words, and 98 of those sit outside
every table [`tables.py`](tables.py) names, in six stretches: 30 to 59, 98 to
100, 230 to 279, 536 to 539, 801 to 809, and 811 to 812.

None of the six is monotone, so none is a scalar function of its index the way
the four named tables are. They are constants and coefficients. A replacement
therefore needs the four tables and these as well, and a claim that the four are
what the commands are built from is short by 98 words.

**What this does not say.** A stretch here is what the game read, never a table's
extent, so the bounds above are floors. Naming what the constants are is open.

## 3d. The division, and why it becomes a table of one argument

**What `$00D3` is.** The subroutine `$10`, `$04` and `$28` all reach. It sets the
ROM pointer to word 100, one before the reciprocal table, reads two adjacent
entries, interpolates between them, refines, and saturates to `$7FFF` at two
separate points. `$003A` before it is the normalisation: it shifts the argument
left until it overflows, counting as it goes.

**Why reimplementing it directly was abandoned.** The saturation is visible from
outside. Asked for the reciprocal of an exact power of two, the part answers a
mantissa of `$7FFF` with one less in the exponent, where ideal arithmetic gives
`$4000`. So an implementation that computes the right answer is wrong here, and
matching it means reproducing an interpolation and a refinement step whose exact
rounding depends on ALU behaviour this project has not measured. Guessing at
that is how the two faults in `$00` and `$08` happened, and those were far
simpler.

**What `$10` is, measured rather than read.** It is deterministic and carries no
state: the same arguments answer the same way on a part that has just been
reset and on one that has been driven through other commands first.

Given a first word `a` and a second word `b`, it answers the reciprocal of
`a * 2^b` in two words, a mantissa and an exponent. Two properties were measured
across the input range and both hold everywhere tried:

| property | measured |
|---|---|
| the mantissa depends only on `a` | yes, unchanged across seven values of `b` |
| the exponent is `f(a) - b` | yes, exactly, across six values of `b` |

So the second argument does nothing but shift the exponent, and the whole
command is a function of one sixteen bit word plus a subtraction.

**What that costs.** A mantissa for every value `a` can take is 65,536 entries of
two bytes, which is 131,072 bytes and cannot miss: every input has a row. The
exponent needs no table at all. Sampled across the range it takes eleven values
between 1 and 47, which is a count of leading zeros and is a few instructions.

**Where the table comes from.** Not from a formula, because the values are the
part's own approximation rather than a function anybody can write down. Not
checked in either, because that is a copy of the part's behaviour and the
standard here is that nothing assembled or extracted is committed. It is
generated at build time by driving the part the person building already has,
the same part `tables.py` already checks the four scalar tables against.

**What is still open.** Whether `$04` and `$28` decompose the same way. Both
reach the same subroutine, so the same shape is likely and is not yet measured.

## 3e. What `$28` and `$04` turned out to be

**`$28` is the vector length, and it is inaccurate on purpose.** It reads three
words, sums their squares, and answers the square root of that sum. Measured
against the true length:

| input | `$28` | true length | short by |
|---|---:|---:|---:|
| 3, 4, 0 | 4 | 5.00 | 20% |
| 100, 0, 0 | 98 | 100.00 | 2.0% |
| 300, 400, 0 | 495 | 500.00 | 1.0% |
| 1000, 1000, 1000 | 1712 | 1732.05 | 1.2% |
| 32767, 0, 0 | 32508 | 32767.00 | 0.79% |

It is short everywhere and the shortfall settles near eight parts in a thousand
as the argument grows. That is the square root's own approximation error, and
`$28` is the one command whose answers differ between the two masks, so this is
very likely the arithmetic the DSP-1B corrected and the reason the demo's plane
lands on one mask and crashes on the other. A replacement that computes an
accurate length here is wrong, and wrong in the way that is visible on screen.

**`$04` is not yet named.** It takes two words and answers two, and neither the
reverse of `$10` nor a plain shift fits what it returns. Fed a normalised
mantissa and an exponent it answers the exponent less one in the first word and
nothing in the second; fed what `$10` hands back it answers something else
again. It reaches `$0132`, which no other command here reaches, so it is the one
command whose subroutine is still unread.

**What to do next, in order.** `$10` is ready to build: a table of 65,536
mantissas generated at build time from the part, plus a leading zero count for
the exponent. `$28` needs its square root approximation measured to the bit
rather than to a percentage, and the same table treatment probably applies, since
it too is a function of one quantity, the sum of squares. `$04` needs `$0132`
read first.

## 3f. `$0132` and `$04`, and the shape all three share

**What `$0132` is.** It sets the ROM pointer to word 541 and walks backwards
from there, reading four entries and interpolating between them, clamping to
`$8001` and `$7FFF` at the ends. Word 541 sits one before the arccosine and just
past the cosine, in the stretch entry 3c reported as belonging to no named
table. So the seats that looked unaccounted for are this routine's, and it is
the trigonometric lookup rather than a fifth table.

**What `$04` is.** Polar to rectangular. Given an angle and a magnitude it
answers the magnitude times the sine and the magnitude times the cosine, in that
order. The angle is a whole turn per 65,536, so `$4000` is a quarter turn:

| angle | `$04` with magnitude 1000 | sine, cosine of that angle |
|---|---|---|
| `$0000` | 0, 999 | 0, 1000 |
| `$1000` | 382, 923 | 382, 923 |
| `$2000` | 707, 707 | 707, 707 |
| `$4000` | 999, 0 | 1000, 0 |
| `$8000` | 0, -1000 | 0, -1000 |
| `$C000` | -1000, 0 | -1000, 0 |

The ones that are short by one are the chip truncating rather than rounding,
which is the same fractional multiply `$00` answers with.

**All three commands have one shape.** `$10`, `$04` and `$28` each turn out to
be a table over a single sixteen bit word plus fixed arithmetic:

| command | the table | the arithmetic around it |
|---|---|---|
| `$10` | a mantissa per input, 65,536 entries | the exponent is a count of leading zeros, less the second argument |
| `$04` | a sine and a cosine per angle, 65,536 each | one fractional multiply by the magnitude, per half |
| `$28` | not yet reduced, but it is a square root of one quantity | the sum of three squares, which `$08` already answers |

For `$04` the table holds more precision than the command hands back. Asked with
a magnitude of `$7FFF` it returns a value one short of what it multiplies by
internally, so the table is recovered by asking with several magnitudes and
keeping the one value that explains them all. Across 65 angles sampled over the
whole range, exactly one value did, every time, and never further than one from
what the command returned.

**Why a table rather than the routine.** These are approximations the chip makes,
not functions anybody can write down, and matching them means matching an
interpolation and a clamp whose rounding is not something this project has
measured. A table holds the chip's own answers, so it is exact by construction
and no input can miss it. It is generated at build time from the part the
builder already has, never checked in, the same way the four scalar tables are
checked rather than carried.

**What that costs.** 131,072 bytes for `$10` and 262,144 for `$04`, against
9,069,684 spare in a 96 Mbit image.

## 3g. `$03`, `$13` and `$06`, which are half the traffic between them

**`$01` and `$11` load a matrix; `$03` and `$13` apply it.** The two loaders
share one handler and the two appliers share another, so which of the pair is
being run has to reach the handler in the command byte itself, and the recorded
pairing bears that out: `$03` follows `$01` and `$13` follows `$11`.

Loaded with the first non-zero `$01` the recording contains, `$03` answers the
columns of a diagonal matrix when fed the unit vectors, and scanning one
component alone is a straight line all the way:

| input | `$03` |
|---|---|
| `$0800`, 0, 0 | 1023, 0, 0 |
| `$1000`, 0, 0 | 2047, 0, 0 |
| `$2000`, 0, 0 | 4095, 0, 0 |
| `$4000`, 0, 0 | 8190, 0, 0 |
| `$6000`, 0, 0 | 12285, 0, 0 |

**`$03` is exactly a matrix product.** Recovering the three columns by feeding
the unit vector `$4000` on each axis, the answer for any other vector is the
product of that matrix with it, shifted right fourteen. On thirty random vectors
whose components stay under `$1000` it is exact thirty times.

Above that it is not, and that is the next thing to measure rather than a fault
in the model: the same thirty vectors drawn from the whole sixteen bit range
match three times, so something saturates and the rule for it is not yet known.

**`$06` is not that.** It has a constant term, which suggested an affine
transform, and an affine model fails on every input tried, small ones included.
Scanning the third component moves all three answers in a way no product does.
At 119 instructions against 26, and given a projection is what its arguments
look like, it almost certainly divides, which is why it reaches the same
reciprocal subroutine `$10` does.

**What this is worth.** `$03` and `$13` are 27.6% of everything the cartridge
asks and they are nine multiplies and six additions once the matrix is in hand.
Getting the matrix is the work of `$01` and `$11`, which are 6.9%. So a quarter
of the traffic turns on one command that has not been read yet.

## 3h. What `$01` and `$11` put in the matrix

**Four words, and each one is now named.** Probed by loading the matrix and then
reading its columns back through `$03` on the unit vectors:

| word | what it is |
|---|---|
| 0 | a scale. The diagonal comes out as a quarter of it: `$1000` gives 1023, `$7FFF` gives 8190 |
| 1 | a rotation about the third axis. Moves the first two rows, leaves the third |
| 2 | a rotation about the second axis. Moves the first and third |
| 3 | a rotation about the first axis. Moves the second and third |

**The angle unit is a whole turn per 65,536**, the same as `$04`. At `$1000`,
which is a sixteenth of a turn, the entries are 7567 and 3134 against a diagonal
of 8190, so 0.9239 and 0.3827. Those are the cosine and sine of 22.5 degrees to
four figures. At `$4000` the matrix is a clean quarter turn.

**The three compose in that order.** With the third-axis rotation at `$1000` and
the second at `$2000`, the chip's matrix is

    [[5350, -2216, 5792], [3134, 7567, 0], [-5351, 2216, 5791]]

and multiplying the two single-angle matrices in that order, shifted right
thirteen, gives

    [[5349, -2216, 5790], [3133, 7565, 0], [-5350, 2215, 5789]]

The other order does not resemble it at all. So the order is settled and the
shift is thirteen.

**Where the ones and twos come from.** The chip builds each entry from its trig
values and rounds once. Composing two matrices that have each already been
rounded, as above, rounds twice. So the model is right and reproducing it to the
bit needs the chip's own sine and cosine at full sixteen bit angle resolution,
which is the table `$04` needs, and the rounding of each entry, which is not yet
measured.

**What this leaves.** `$01` and `$11` are structurally solved and not yet exact.
They gate `$03` and `$13`, which are 27.6% of the traffic and are otherwise nine
multiplies and six additions.

## 3i. `$06`, and the divisor it hides

**It is not a projection and not a transform.** Scaling the whole vector leaves a
projection unchanged and doubles a transform, and `$06` does neither: the three
components at `$0200` answer 366, -549, 244 and at `$1000` they answer -255,
213, -17. Multiplying the answer by the third component is not constant either,
so it is not a plain divide by that component.

**What the third component does.** Holding the first two and scanning the third:

| third | `$06` |
|---|---|
| `$0100` | -320, -35, -21 |
| `$0400` | -304, 24, -20 |
| `$1000` | -255, 213, -17 |
| `$4000` | -155, 596, -10 |

The first and third answers both fall smoothly toward zero, and both roughly
halve while the third component grows sixty-four fold. A divide by the component
itself would have fallen sixty-four fold. A divide by a constant plus the
component fits: solving for that constant from the two ends gives about 14,400,
and the seventh word `$02` was loaded with in this recording is 14,170.

So `$06` divides by something `$02` set, offset by the third component, which is
a perspective divide against a near plane rather than against the origin. That is
why it reaches the same reciprocal subroutine `$10` does, and why 119
instructions rather than 26.

**What is needed to finish it.** The reciprocal, exactly, which entry 3d already
shows has to be a table rather than a reimplementation. `$06` is 28.8% of the
traffic and it is behind that one table, as `$10` is.

## 4. Whether the image needs to grow at all

**Answered, 2026-09-02: yes, to 3.75 megabytes, and no further.**

The replacement is written and measured. The image is 121 banks, $00 to $78,
which is 3,964,928 bytes:

| what | banks | bytes |
|---|---|---:|
| the game as it ships, with the replacement's code in the space above it | `$00`-`$0F` | 524,288 |
| the answers | `$10`-`$6C` | 3,014,801 |
| the three tables taken from the part itself | `$6D`-`$78` | 393,216 |

**What that settles.** No windowed layout and no second address space. A low
cartridge carries banks `$00` to `$7D` and nothing above: `$7E` and `$7F` are the
console's own memory, and everything from `$80` up is a second view of what is
already below. 121 banks of 126 is inside that, so the whole cartridge is
reachable with ordinary long addressing and every emulator that loads a 4 megabyte
low cartridge loads this one.

This was found the hard way. The table was first placed from bank `$30`, which
put its last fourteen banks above `$7F`, where they read back as the game's own
first fourteen banks. Nothing reported an error; the lookup simply returned the
wrong row.

**What is left of the 96 megabit figure.** Nothing. It was a ceiling used to
decide what could not be stored, and the answer came in at a twenty fifth of it.
It stays in [`tabulate.py`](tabulate.py) as that ceiling and is not a target.

**The one thing the size does rule out.** `$0a`, per entry 2f. Its answers would
take 8.7 megabytes on their own, which is more than twice the whole cartridge.

## 5. Whether the replacement is fast enough to run the game

**Measured 2026-09-02, and no: it is about seven times an entire frame.**

Every figure below is 65816 cycles counted on the processor model, driving the
assembled image.

| | per call | a median frame, 43 calls | of a frame |
|---|---:|---:|---:|
| the part, wall time the game was blocked | tens to ~250 | about 2,700 | 6% |
| this replacement, every call a hit | 7,764 | 333,850 | 750% |

A frame is 357,368 master clocks, which is 44,671 processor cycles when a read
costs 8 of them and 59,561 when it costs 6. The game has to do everything else
in the same frame, so the replacement's share needs to be a fraction of it
rather than a multiple.

Call rate is measured rather than assumed. The recordings carry a frame number
per access, and across all three the busy frames take a mean of 37 calls, a
median of 43, a 99th percentile of 46 and a worst case of 128.

**Where it goes.** The search is a binary one over as many as 75,278 rows, so
seventeen comparisons, and each comparison recomputes the row's address from
scratch: a software multiply of the row number by the key width, then the
conversion from a flat offset to a bank and address, then the words themselves.
That is roughly 650 cycles a comparison.

**The finding that matters.** The table is the slow path, not the fast one.

| command | through the table | through its own arithmetic |
|---|---:|---:|
| `$00` | 6,562 | 398 |
| `$08` | 5,696 | 920 |
| `$04` | 3,960 | 833 |

Sixteen times slower for `$00`, and the arithmetic is exact on the whole domain
where the table covers only what was recorded. For a command whose arithmetic is
known, computing beats looking up on both counts at once, and the 191,314 bytes
those three occupy in the table buy nothing.

**What that changes.** The order of work is now the same by both measures. `$06`
is 30.8% of calls, costs 9,805 cycles through the table and answers nothing on
unseen flight. `$13` is 26.9%, costs 7,151 and answers 39.4%. Reading those two
handlers out of the part's program is the largest available gain in speed and in
coverage together, and it is the same task.

**Caveat on the part's own latency.** Several commands report a single cycle to
the first answer byte, which is not credible as a hardware latency and is more
likely the model buffering. The rows that do report plausibly, `$02` at 527 DSP
cycles, `$06` at 356, `$14` at 134, `$0e` at 114, are the ones the estimate above
rests on. A tighter figure needs the part timed against a hardware capture rather
than against its own model.

**What would close this.** Reading `$06` and `$13`, then re-measuring. If the
weighted mean lands under about 400 cycles a call the replacement fits in roughly
a third of what the game already spent waiting, and the question closes. If a
table has to stay for some command, the search needs a bucket index on the first
key word and the row address needs the console's multiplier rather than a
software loop.

## 5b. The table was not the reason it is slow

**Measured 2026-09-02.** Removing the table does not fix the speed, because the
table was never the largest cost. Both routes land in the same place.

| route | a median frame of 43 calls |
|---|---:|
| the searched table, measured | 333,850 cycles, 7.5 frames |
| arithmetic, estimated from the part's own work | roughly 300,000, 7 frames |

**What the part actually does.** Counted by stepping its own program:

| command | share of calls | instructions it runs | of those, loading the multiplier |
|---|---:|---:|---:|
| `$02` | 2.9% | 534 | 154 |
| `$06` | 30.8% | 361 | 86 |
| `$0a` | 2.9% | 12,225 | streamed |

`$06` is 43 signed 16 by 16 multiplies a call. The part has a 16 by 16
multiplier that retires one per cycle and runs at 7.6 MHz. The 65816 has an 8 by
8 multiplier with an eight cycle latency and runs at 3.58 MHz, so one of those
multiplies costs it roughly a hundred cycles against the part's one. That single
difference is about forty to one in wall time, and no amount of care in the
assembly changes it.

**How much the part was doing.** Weighted across the recording it spends about
230 processor-equivalent cycles a call, which is 9,876 in a median frame, or 22%
of one. `$0a` alone is 13% of a frame. That work moves onto the processor whole.

**The game did not wait for it.** Status polling never runs longer than three
reads in a row and averages 1.9, so the part was always ready and its 22% ran
alongside the game's own code rather than instead of it. A software replacement
is serial, so it adds to a processor that was already busy.

**What follows.** Full speed on the 65816 is not reachable by writing better
assembly. The reachable goal is the smallest measured slowdown, and the levers
in order of size are: reducing the work algebraically, such as hoisting a matrix
that `$13` and `$11` set up out of the `$06` calls that use it; indexing where a
domain allows it, as `$10` does; then FastROM, which is worth 15 to 25% and no
more.

**The cartridge is SlowROM.** Header `$FFD5` is `$20` in all three regions, with
chipset `$03`, ROM plus DSP. FastROM would set it to `$30`, and on a low
cartridge the faster timing applies only to banks `$80` and above, so both the
game's code and this table would have to be reached through the mirror. It also
changes the timing of every raster effect in the game, so it is verified by
rendering rather than by reasoning.

## 5c. What `$06` is, and what that makes the fastest route

**Measured 2026-09-02 by driving the part.**

`$06` is a perspective projection: three affine numerators over one affine
denominator shared by all three.

The evidence, in the order it was found. Sweeping the first argument alone moves
the first output linearly, by a slope of 0.535 across the whole recorded range,
and leaves the other two outputs untouched. Sweeping the third argument alone
produces a reciprocal: `309904 / (2767 - w2)` predicts every sampled point to
within one. Fitting three affine numerators over one affine denominator on 40
probes and testing on 20 held out gives a worst error of 2.80 on outputs that
reach into the thousands, which is the part's own fixed point rounding rather
than a wrong model.

A plain matrix was tested first and rejected: predicting `f(v)` from `f(0)` and
the three unit responses is out by up to 2,163.

**What it costs.** Nine multiplies for the matrix, one reciprocal, three
multiplies for the divide. Twelve multiplies and one table read, against the 43
multiplies the part's own program runs. The reciprocal is already in the
cartridge as an exhaustive 65,536 entry table, so it is one indexed read.

**The general finding.** The route is not "arithmetic everywhere". It is "never
search", and the cheapest form differs per command:

| form | cost | which commands |
|---|---:|---|
| a direct index | tens of cycles | `$13`, `$18`, `$10` |
| arithmetic over an indexed table | hundreds | `$06`, and by structure `$0d`, `$0e`, `$03` |
| arithmetic alone | hundreds | `$00`, `$08`, `$04` |
| a searched table | thousands | what everything uses today |

`$13` is the clearest case and needs no decoding at all. Its own arguments have
56 combinations and its whole table is 1,512 rows, so the row number is
computable rather than searchable.

**What is still unmeasured.** `$0a`, which is 2.9% of calls and the largest
single computation the part does.
