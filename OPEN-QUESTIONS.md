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

## 6. The image cannot grow past 1 megabyte

**Measured 2026-09-02, and it settles entry 4 the other way.**

Entry 4 concluded the image could grow to 3.75 megabytes because that fits
inside what a low cartridge addresses. It fits, and the game does not run.

Padding the retail dump with zeroes and changing nothing else, run against the
local snes9x fork:

| image | banks | frames drawn in 3,000 |
|---|---|---:|
| 1,024 KB | `$00`-`$1F` | 2,657, the same as the retail dump |
| 1,056 KB | `$00`-`$20` | 605 |
| 1,216 KB | `$00`-`$25` | 605 |
| 2,048 KB | `$00`-`$3F` | 605 |
| 4,096 KB | `$00`-`$7F` | 605 |

Thirty two banks work and thirty three do not. Nothing else differs: same code,
same header, same input script, zeroes in every added byte.

Three things it is not. Not the header's size byte, since declaring 11, 12 or 13
changes nothing. Not the loss of the mirrors, since filling the whole image with
repeated copies of the game changes nothing. Not the coprocessor window at
`$30`-`$3F`, since 33 banks fails and reaches only `$20`.

**What this costs.** The table is 3.0 megabytes and there is room for about 100
kilobytes beside the game, the code and the three tables taken from the part. A
recorded-answer table of that size is not reachable at all, which turns entry 5c
from the fastest route into the only one: the answers have to be computed.

**What would close it.** Reading snes9x's own map for a low cartridge above one
megabyte, and checking the same boundary against a second emulator and against
hardware. A limit measured on one emulator is a property of that emulator until
a second one agrees.

## 7. What the conversion still gets wrong, with everything else ruled out

**Measured 2026-09-02 at one megabyte, where the size limit above does not
apply.** Three builds, one input script, 3,000 frames:

| build | frames drawn |
|---|---:|
| the retail dump padded to 1 MB | 2,657 |
| that, plus this project's code and the tables taken from the part, with the 122 sites left alone | 2,657 |
| the same with the 122 sites replaced | 605 |

So everything this project adds to the image is harmless, and the fault is in
the replacement of the sites or in the port that stands behind them.

**What the port sees.** Counters kept in its own state, read out of work RAM:
213 writes, 213 completed commands, 85 reads, and the last command completed is
`$80`. Those numbers are identical at frame 200 and at frame 2000, so the game
stops using the part entirely after its opening handshake. The recording shows
the retail cartridge issuing 130 `$80` writes at frame 0 and then nothing until
frame 1790, so the conversion never reaches the point where the part is asked a
real question.

**What is ruled out.** The lookup, the fallback, the answers, and the table,
because none of them is ever reached.

## 9. What answers the absolute accesses, and what is left

**Measured 2026-09-02.** Entry 8 found that most of the traffic reaches the part
through three byte absolute instructions with the data bank at `$3F`, which
cannot take a four byte call. The way past it is not to touch those
instructions at all.

Twelve places set that bank, each with `pea $003F` followed by `plb`. Rewriting
the bank those twelve name sends every absolute access after them somewhere this
project fills, without one of them being modified.

What that bank has to hold is a status byte with its top bit set, at every
address the poll can name and in both halves of a word. The poll spins until
that bit appears, so a byte without it is an endless loop, which is exactly how
the game died: at frame 935 it entered `$00CAD7` and never came out.

| build | frames drawn in 3,000 | in 18,000 |
|---|---:|---:|
| retail dump padded to 1 MB | 2,657 | 17,657 |
| this conversion | 2,569 | 17,569 |
| this conversion, before the redirect | 605 | 605 |

The gap is a constant 88 frames from the opening seconds and does not grow, and
frames delivered match frames run, so the game runs the whole demo at full pace
without stopping.

**What is still wrong.** The picture. Those reads now return this project's
zeroes rather than answers, so everything the part computed is nought.

**What would fix it, and why it is now mechanical.** `pea $003F` and `plb` are
three bytes and one, which is four, which is exactly the length of a long call.
So each of the twelve routines can be entered by a call at its first
instruction, and a routine entered that way can do the whole exchange through
the port and return past the body it replaced.

The twelve, with the command each sends where the code names one outright:

| where | command |
|---|---|
| `$00071` | `$00` |
| `$04aa4` | `$0a`, already replaced as a span |
| `$04b13` | `$10` |
| `$04b4a` | `$02` |
| `$0004e`, `$01601`, `$04db3`, `$0503f`, `$051f1`, `$05447`, `$05507`, `$055d8` | held in a register rather than an immediate |

**What is not in doubt any more.** The port, the lookup, the fallback, the
tables, the 1 megabyte layout and the site replacement are all measured innocent
or working. What is left is reimplementing twelve routines, and each one is
bounded work with a known entry point.

## 10. What `$0a` computes, and how much code the three heavy commands are

**Measured 2026-09-03.**

The three commands that decide the picture are far smaller than the traffic
suggests. Counting distinct instruction addresses rather than instructions
executed:

| command | executed | distinct | multiplier loads |
|---|---:|---:|---:|
| `$02` | 534 | 273 | 154 |
| `$06` | 361 | 186 | 86 |
| `$0a` | 12,225 | **48** | 1,528 |

`$0a` looked the largest and is the smallest. Its 12,225 instructions are a loop
of about twenty five run 191 times, plus three subroutines. That is less code
than `op_08`, which is already written and exact against the part.

**What it computes.** A Mode 7 matrix per scanline, 191 groups of four words.
Two of the four are the scale terms and the other two are nought while the
aircraft is level. The subroutines it calls are the part's reciprocal: `$00D3`
reads the data ROM table, `$0077` and `$003A` normalise around it.

Fitting the scale terms against the scanline number confirms the shape. If
`A(k) = C / (k - h)` then `1/A` is a straight line in `k`, and it is:

| case | horizon from A | horizon from D | median error |
|---|---:|---:|---|
| 1 | 49.67 | 50.14 | 1.5 and 1.1 |
| 2 | 48.79 | 49.14 | 1.4 and 0.8 |
| 3 | 48.86 | 49.15 | 1.4 and 0.8 |
| 4 | 48.89 | 49.17 | 1.6 and 0.9 |

The horizon sits in the same place in every case and the constants move with the
flight, which is what a perspective divide against a camera does. So `$0a` is a
reciprocal per scanline scaled by two constants that come from `$02`.

**Why the fit is not the implementation.** A median error of one and a worst of
seventy is a curve through the answers, not the arithmetic that produced them.
The part works in a fixed point format with a separate exponent, which is what
`$0077` and `$003A` exist for, and a reimplementation that guesses the rounding
is wrong on every input rather than only between samples. That is the same
reasoning that kept the thirteen unread commands on nearest-row rather than on
invented arithmetic.

**What is needed.** The 48 instructions read to the bit, then held against the
part on the same four hundred argument sets `op_00`, `op_08` and `op_04` were.
The reciprocal it needs is already in the cartridge, exhaustive over all 65,536
inputs, so the loop is a table read and two multiplies once the format is known.

**Order.** `$0a` first, at 48 instructions and the whole ground plane. Then
`$02` at 273, which produces the constants `$0a` and `$06` both need. Then `$06`
at 186, whose shape entry 5c already fixes.

## 12. `$0a` decoded, and the one thing it still needs

**Read and measured 2026-09-03.** Four facts, each checked against the part
rather than inferred.

**It steps by a constant.** The value handed to the reciprocal advances by
exactly 512 per scanline. Watched at the call site over the first twelve
scanlines: -25088, -24576, -24064, -23552, and so on without exception. So the
per scanline input is a start plus 512 times the scanline, and the start is what
the twelve instructions of setup compute.

**What comes back is a reciprocal of a half.** Input times output is 0.5 in the
part's fixed point, to five digits, on every row sampled. That is a reciprocal
with a half in the numerator, which is what keeps the result inside a signed
word.

**It is the reciprocal this cartridge already carries.** The table `derived.py`
drove out of the part, 65,536 entries covering every input, returns exactly what
the part returned on all six values checked, to the bit. So the expensive half of
`$0a` needs no arithmetic written at all: it is a table read this project has
had since before any of this.

**The shape.** Per scanline the loop computes two scales from that reciprocal,
writes each into two places in the near half of RAM, and the output stage sends
four words, each the high half of a near value against a far one:

| word | near, per scanline | far, the matrix |
|---|---|---|
| 0 | `RAM[$3F]` | `RAM[$BF]` |
| 1 | `RAM[$3E]` | `RAM[$BE]` |
| 2 | `RAM[$2F]` | `RAM[$AF]` |
| 3 | `RAM[$2E]` | `RAM[$AE]` |

**What it still needs, and this is the finding that matters.** The four far
values are not `$02`'s answer. Driving `$02` alone and reading the part's RAM
straight afterwards, all four are nought, while a real run produces output that
is plainly not. So the matrix `$0a` multiplies by is accumulated by more than
`$02`, and the commands that answer nothing at all, `$01` and `$11`, are the
candidates: they exist to set state and nothing else.

That was worth finding out before writing the routine. An implementation of
`$0a` that took `$02`'s four answer words for the matrix would have been wrong
in a way that looks plausible, which is the shape of fault this project has
already been caught by twice.

**What is left for `$0a`.** The start value from its twelve instructions of
setup, the two constants at `RAM[$CC]` and `RAM[$CB]`, the normalisation in
`$0077`, and wherever the far half is written. Then the routine, held against
the part on four hundred argument sets the way `op_00`, `op_08` and `op_04`
were.

## 13. `$0a` read off the part rather than off the microcode

**Measured 2026-09-03, and this supersedes the operand pairing in entry 12.**

Entry 12 named the matrix as `RAM[$BF]/$BE/$AF/$AE`, read out of the instruction
operands. That was wrong, and the way it was found to be wrong is worth keeping:
driving `$02` on its own and reading the part's RAM afterwards showed all four
slots still nought while a real run plainly produced output from them. So the
operand decode was set aside and the part was watched directly instead.

**Watching it needed one correction first.** Replaying a recording by writing the
command and then reading as many bytes as the recording holds desynchronises the
part, because a read takes whatever is latched whether or not anything is
pending. Reading nothing at all for a command that answers nothing, and exactly
the recorded count for one that answers, brings the first 129 exchanges into
exact agreement. The one remaining divergence is a `$0a`, whose answer is a
stream the game stops reading when it likes, so replaying it leaves the part
mid-answer and every later command reads the leftovers. Skipping the earlier
`$0a` calls reproduces a live one word for word.

**The whole per-scanline body, as the part executes it.** Thirty-four memory
events, every one of them accounted for:

| step | what happens |
|---|---|
| 1 | `RAM[$09]` increments by one. It starts at the command's single argument |
| 2 | `RAM[$c8]` is read. It is the horizon offset, 53 in this frame |
| 3 | a normalise loop over `RAM[$00]` and `RAM[$01]` with three ROM constants |
| 4 | the reciprocal is a ROM read, at an index that moves with the scanline |
| 5 | `RAM[$4c]` and `RAM[$cc]` are read, a mantissa and an exponent |
| 6 | a power of two is read from ROM, then `RAM[$3f]` and `RAM[$2f]` are written |
| 7 | `RAM[$4b]` and `RAM[$cb]` are read, the second mantissa and exponent |
| 8 | another power of two, then `RAM[$3e]` and `RAM[$2e]` are written |
| 9 | four products are formed and sent |

**The matrix is at `$7f`, `$7e`, `$6f`, `$6e`,** and the four answer words are

| word | product |
|---|---|
| 0 | `RAM[$3f]` against `RAM[$7f]` |
| 1 | `RAM[$3e]` against `RAM[$7e]` |
| 2 | `RAM[$2f]` against `RAM[$6f]` |
| 3 | `RAM[$2e]` against `RAM[$6e]` |

In the frame measured the matrix is an identity, `32767, 0, 0, 32767`, which is
why two of every four answer words are nought and the other two are the
per-scanline values unchanged. That is a property of this frame, not of `$0a`.

**The per-scanline law, fitted and then confirmed against the horizon offset the
part reads.** Both values are a constant over the distance to the horizon:

| n | `$3f` | `$3e` | `$3f` times n+53 | `$3e` times n+53 |
|---:|---:|---:|---:|---:|
| -103 | -32 | -149 | 1600 | 7450 |
| -100 | -34 | -159 | 1598 | 7473 |
| -97 | -36 | -170 | 1584 | 7480 |
| -94 | -39 | -183 | 1599 | 7503 |

The divisor is `n + RAM[$c8]`, and `RAM[$c8]` is 53. The scatter in the products
is integer rounding in the part, not a worse fit.

**What this changes.** Both tables `$0a` needs are ROM tables this project has
already extracted whole: the reciprocal and the powers of two. Nothing about the
expensive half has to be written as arithmetic. What has to be written is the
normalise, two multiplies, and the four output products.

**What is left.** The fixed-point scaling that turns the reciprocal and a
mantissa and exponent pair into `$3f`, and the same for `$3e`. The trace names
every input to it, so it can be pinned by driving the part across a spread of
`RAM[$4c]`, `RAM[$cc]` and `RAM[$c8]` rather than by reading instructions. Then
the routine, held against the part on four hundred argument sets the way
`op_00`, `op_08` and `op_04` were.

**And `$01` and `$11` are not where the matrix comes from.** Each writes four
words and touches none of `$7f`, `$7e`, `$6f`, `$6e`. `$02` writes thirty-five,
including every constant the loop reads. The matrix is `$02`'s, and the earlier
suspicion of the two answerless commands was wrong.

## 14. `$0a` computed rather than replayed, and what still blocks it

**Measured 2026-09-03.** `raster.py` computes `$0a` instead of replaying it, and
its tests hold it to values taken off the part. What follows is what is settled
and what is not, kept apart on purpose.

### Settled, each checked against the part

**The output stage.** Four words a scanline, each the high half of a product
against a matrix `$02` leaves at `RAM[$7f]`, `RAM[$7e]`, `RAM[$6f]`, `RAM[$6e]`.
In the frame measured that matrix is an identity, which is why two words in four
are nought there. That is a property of the frame, not of the command.

**The first scale.** `(mantissa * reciprocal) >> (27 - exponent)`, then one
added. Swept against the part across eight exponents and fourteen mantissas,
every one exact.

**The second scale.** The same product carried forward,
`(product * mantissa) >> (42 - exponent - exponent)`, then one added. Swept the
same way, every one exact. The carrying is why changing the first mantissa moves
the second value, which is what showed these are one calculation and not two.

**The fold.** A distance outside the table's octave shifts both scales, and it
shifts each by one, not the second by two. Assuming two fitted 19 distances and
assuming one fitted 50, which is how the error was found.

**The reciprocal is a table read.** The part holds `2**20 / x` for x from 32 to
64 in quarter steps, based at word 101, and 101 is the value it keeps in
`RAM[$00]`. On the eleven distances checked directly the table entry is exactly
`round(2**20 / x)`.

### Not settled

**Which entry a distance selects.** Measured against the part, the divisor is one
less than the distance over part of the range and equal to it over another, and
no rule fitted both. It is taken per distance instead, the way `complete.py`
takes `$13` and `$18`, which is also what the cartridge can afford: one indexed
read.

**Lines below the horizon.** Solving a reciprocal from the answer succeeds for
every distance above the horizon and for none below it, so something in the
second scale differs there. The count is reported rather than smoothed over:
50 of 191 scanlines with the fold chosen naively.

### What blocks wiring it into the cartridge

`$0a` reads six values and a matrix, and `$02` writes every one of them. Watching
the part confirms it: `$01` and `$11` write four words each and touch none of
them. So a correct `$0a` in the cartridge is worth nothing until `$02` is
decoded, and `$02` is the next thing to do rather than a later one.

## 15. `$02` solved, and where `$0a` still stops

**Measured 2026-09-03.**

### `$02` is trigonometry, and it tabulates in 32 KiB

Swept one argument at a time against the part, every one of its outputs has a
single owner:

| argument | what it sets |
|---|---|
| 0 and 1 | two answer words, passed through |
| 2 and 6 | the first mantissa and exponent |
| 5 | the matrix |
| 6 | the horizon, and the second mantissa and exponent |
| 3 and 4 | nothing. Neither ever varies |

**Argument 5 is an angle.** The matrix it writes is `32767 cos` and `32767 sin`
of a full turn in 65,536 steps, matching to within one unit at every angle
sampled, and the four entries carry two numbers because the cosine is written
twice and the sine twice, once negated.

**Argument 6 is a pitch.** The horizon it sets is the fourth argument against
the cosine of it: at a pitch of 8192, which is an eighth of a turn, the horizon
is 181 against a predicted 181.

**Arguments 3 and 4 never vary.** Across all three recordings argument 3 is
always 32 and argument 4 always 256, so neither is a key. `parameter.fixed`
re-derives that from whatever run it is given rather than trusting it.

**The split is not a hopeful reading.** `parameter.gathered` refuses a key that
carries two different answers, and driven across all 6,980 distinct argument
sets it refused none. That is the whole domain of the recordings, not a sample.

**What it costs.** 1,193 rows keyed on argument 6, 3,302 on argument 5, 3,033 on
the pair, which is 31.7 KiB against 123 KiB for one flat table. Built from the
European recording it answers every `$02` call in the American and Japanese ones,
all three at 100%. That is three recordings of one attract sequence agreeing with
each other, so it covers the demo and says nothing about a player.

**`$02` can be driven in one pass.** It leaves the same state whether reached by
replaying the recording up to it or by driving it directly, and driving it twice
with the same arguments gives the same state both times. So the whole extraction
takes eight seconds rather than a day.

### `$0a`'s sign rule was wrong, and the fix is uniform

Both scales end by taking one away, and that one is taken away on both sides of
the horizon. Reading it as an addition whose sign followed the line fitted every
distance above the horizon and none below it, which is exactly how it showed up:
the sky agreed and the ground did not. Correcting it widened the distances that
could be solved from 50 to 195.

### Where it stops

The normalise loop is not a function of the distance. Held at -46 and reached
from a horizon of 53, 60 and 80 it gives -35; from 40 it gives -34; from 120 the
second value changes again. Solving a table from the recording agrees: 30
distances of 192 are contradicted, meaning no single value reproduces every line
that asks for them.

So a reciprocal table keyed on distance cannot be right, and `raster.py` takes
the mapping as an argument rather than building a wrong one. The demo asks for
only 196 distinct distances, from -50 to 145, which covers 100% of its scanlines,
so whatever the real key turns out to be the table stays small.

## 16. The lookup was reading the wrong bank, twice

**Found 2026-09-03 by running the cartridge's own lookup in a processor model
against the recording, rather than by reading it.**

Two constants in `dsp1-answer.asm` named where the recorded-answer table lives,
and both named bank `$11` while `lut-map.asm` assembles it at `$1D`:

| constant | said | is |
|---|---|---|
| `!LUT` | `$118000` | `$1D8000` |
| `!LUTBANK` | `$0011` | `$001D` |

Bank `$11` holds the reciprocal driven out of the part, so the lookup read that
as its index and as its rows. It found a count of 255 and a first command of
`$7f`, matched nothing, and fell through to the fallback on every command, every
time. The wrong answers were literally the opening words of the reciprocal
table: `32767, 32767, 32767, 21846`.

Correcting the first stopped the demo hanging: it ran 4,000 frames where it had
stopped at 1,812. Correcting the second made the lookup work at all.

| command | before | after |
|---|---|---|
| `$10` | 0 right of 40 | **40 right of 40** |
| `$13` | 0 right of 84 | 21 right of 84 |
| `$00` | 56 right of 56 | 56 right of 56 |

**Why two, and why this was hard to see.** The two constants are adjacent, and
correcting one leaves the other silently wrong: the index is found, the fields
come back correct, and only the rows are read from somewhere else. The search
then closes empty and the fallback answers, which looks exactly like a key the
table has never seen.

**How it was found.** Not by reading the source, which had been read several
times. By running `dsp1_answer` in the processor model with a key known to be in
the table, stopping where the search returns, and reading its state: `KEYW 2`,
`ANSW 2`, `ROWS 2,498`, `ROWAT $25`, all correct, and `LOW 0 HIGH 0 MID 0`,
which is a range that closed with nothing in it. The search had decided row 0
was above a key that is row 0.

**What this does not fix.** `$06`, `$02`, `$0e`, `$0c`, `$0d`, `$14`, `$28` and
`$03` are not in the table and have no routine, so they still answer from the
fallback and still answer wrongly. `$06` alone is 31.7% of every call the game
makes. The demo therefore still goes dark after its first fade: the picture
needs those, and the two corrections here were what stood between the emulation
and being exercised at all.

## 17. A lookup costs more than the arithmetic it replaces

**Measured 2026-09-03 by running each command in a processor model and counting
cycles.** This reverses the assumption the cartridge is built on.

| how it is answered | command | cycles |
|---|---|---:|
| computed | `$00` | 956 |
| computed | `$04` | 1,325 |
| computed | `$08` | 1,469 |
| looked up | `$18`, 48 rows | 3,928 |
| looked up | `$10`, 2,498 rows | 5,903 |
| looked up | `$06`, 75,278 rows | 10,273 |

The smallest table in the cartridge holds forty eight rows and still costs four
times what computing a product from scratch does.

**Why.** The table is searched rather than indexed, and each step of the search
calls `lut_key_at`, which multiplies the row number by the key width using a
shift and add loop of up to sixteen passes, then turns a thirty two bit flat
offset into a bank and an address. A lookup is a dozen or more of those. Reading
a byte of ROM costs eight cycles; working out which byte to read costs six
thousand.

**What it means for the demo.** `$06` runs 228,963 times across the recording, at
10,273 cycles each, which is 2.35 billion. The whole demo is roughly 18,000
frames of 59,561 cycles, which is 1.07 billion. The table approach asks for more
than twice the entire budget before the game does anything else.

**The cheap fix, when performance comes up.** Bisect over byte offsets rather
than row numbers. The multiply then disappears from the inner loop entirely,
because halving an offset is a shift. That one change speeds every command at
once, and nothing else about the design has to move.

## 18. What `$0a` still needs

Every command except `$0a` now answers exactly: 400 of 400 against the recording.
`$0a` cannot be tabulated, measured rather than assumed: 6,980 distinct keys of
up to 764 answer words is 10.18 MiB, against 715 KiB free in a LoROM cartridge's
whole address space. So it is computed, and what stands in the way is one rule.

**Where the table lives.** The part's own data ROM holds it, and it is now read
rather than guessed: `table[101 + 4 * (x - 32)] = 2**20 / x`, for `x` from 32 to
64 in quarter steps, which is words 101 to 229. Checked at `x` of 32, 33 and 40.
That settles the values a scanline can pick from, and leaves only which one.

**Whether the reciprocal follows the distance is still open, and two attempts to
settle it were both confounded by the same mistake.** Recorded here in full,
because the mistake is easy to make again and neither number should be quoted.

The answer does not carry a scale. It carries the scale multiplied by a matrix
entry and shifted, `(near * M) >> 15`. Every viewpoint used here has `M` of
`$7fff`, and `(n * 0x7fff) >> 15` is `n - 1` for every positive `n` up to 32,768.
So a reading that takes the answer word as the scale is one low on every single
line, and one low is not a rounding difference here: the scales are as small as
12, so an error of one moves the reciprocal by most of a table entry.

Both measurements on 2026-09-03 made exactly that error. The first intersected
candidate entries across 4,179 viewpoints and reported 2,843 empty
intersections. The second corrected the scale, solved the reciprocal as an
interval instead of an entry, and reported 608,535. Neither number is evidence
about the part, because a systematic off-by-one in the input makes an empty
intersection the expected result whether or not the reciprocal follows the
distance.

What is real is the check that needs no intersection. With the scale read
correctly, the reciprocal is `2**20 / |d|` almost exactly for `|d|` of 5 or less,
and drifts above it as the distance grows, reaching about 3% by `|d|` of 144 and
7 to 11% by 118 on a single viewpoint. Predicting every scanline from
`2**20 // |d|` reproduces 12.7% of them across 200 viewpoints. So the part is
computing a reciprocal, and quantising it in a way that is not plain truncation
of that division.

The earlier claim in this section, that twenty four calls showed no conflicts,
is also withdrawn. It was measured the same way and is subject to the same fault.

**The walking reading is a hypothesis and nothing more.** It says the part
carries a normalised value down the scanlines and renormalises when it crosses
the octave, which would make the entry follow the path rather than the distance.
It fits the original observation that one distance reached from two horizons
takes two entries, and it has not been tested. It is written down as the thing to
test first, never as a finding.

**Why it cannot be sidestepped by storing more.** Keyed on its own argument plus
`$02`'s seven, `$0a` is unambiguous, and the cost was measured again on
2026-09-03: 9,210,432 bytes for the American recording, the same for the Japanese
and 10,775,576 for the European. A LoROM cartridge addresses banks `$00` to `$7D`,
which is 4 MiB in total and less than half of what one region needs. Raising the
image to 96 Mbit does not help, because the ceiling is the address space and not
the image. So `$0a` is computed or it is nothing.

**Where to start next, in order.**

1. Read the command out of the part's program. Every attempt so far has inferred
   the rule from answers, and three inferences have now failed. The instruction
   stream is the only source that cannot be confounded by a reading error, and
   `microcode.py` already loads it.
2. Redo the intersection with the scale read through the matrix, since no
   measurement to date has actually done that. Only then is a conflict count
   evidence about the part rather than about the reading.
3. Take the reciprocal from the part directly. `$10` answers one, and if `$0a`
   uses the same unit then its quantisation is already available without solving
   anything.

Only the diagonal viewpoints, `M` of `$7fff` on both entries, were used above.
That is 4,179 of the recording and it makes the scale recoverable, but it also
means every number here describes one corner of the input space.

## 19. The demo does run, and what is missing is the ground

**Found 2026-09-03 by comparing frames against the retail cartridge rather than
by reading the screen.**

The replacement was thought to be stuck on the "DEMO FLIGHT" card. It is not.
Held against retail at the same frame, the two agree on the glider, the
controller icon and the right-hand gauge, and disagree on the ground: retail
draws sea, island and runway, and the replacement draws flat colour.

Memory says the same thing more precisely. Through frame 1,700 the two images
differ in three to seven bytes of low memory, and every one of them is a counter
one step apart, which is a frame of phase and not a fault. At frame 1,750 exactly
one byte differs. By frame 1,800 the pair have converged again on `$7E:000C` and
`$7E:000D` and diverge in 624 bytes, which is flight state rather than a stalled
state machine. Both cartridges are flying.

So the missing piece is `$0a` and only `$0a`. It is the per-scanline transform
that draws the ground, it answers nought by design until the rule in section 18
is found, and nought is flat colour. Every other command answers exactly.

**What this corrects.** Two earlier readings were wrong and are recorded here so
the next session does not repeat them. The first blamed `$02` and `$0e`, on the
grounds that `$7E:0060` through `$7E:0067` are nought at frame 1,800; those are
downstream of a ground that was never drawn. The second replaced the runs at
`$00:CB4A` and around it, which sent the image black: measured afterwards, that
address is reached zero times in the retail cartridge as well, so the run was
never a chip site and filling it with padding destroyed working code.

## 20. `$0a`, what is now settled and what six attempts ruled out

**Measured 2026-09-03.** Section 18 says to stop inferring the rule from answers.
This section records the last round of inference so nobody pays for it again, and
the parts of `$0a` that are now nailed down.

### Settled, and not to be re-derived

**The routine is at `$35f`.** Its loop runs `$364` to `$390`, and it calls two
subroutines that matter. `$03a` is the normalise: it doubles the accumulator
until it overflows, incrementing the data pointer once per doubling, so the
count of doublings ends up in the pointer. `$0d3` is the lookup: it sets the ROM
pointer to 100 and then reads several consecutive words with `rpdec`, taking one
into `a`, one into `tr` and one into `l`, which is the shape of an interpolation
between neighbouring entries rather than a single read.

**The reciprocal table is words 101 to 229**, holding `2**20 / x` for `x` from 32
to 64 in quarter steps, so `table[101 + 4 * (x - 32)]`. Read out of the part's
data ROM and checked at three points.

**The two shifts in `raster.py` are correct.** Searched exhaustively over 24
values of the first shift against 30 of the second, on twelve viewpoints spanning
five different exponents. The best fit is `27 - e1` and `42 - e1 - e2` on every
one of them, which is exactly what the module already had.

**Given the right reciprocal, the model reproduces the answer exactly.** Solving
one value per scanline by search reproduces all four answer words on 95 to 148
scanlines of 176, depending on the viewpoint. So the only unknown left in `$0a`
is that one value.

### Ruled out

Each of these was measured, not argued.

| Candidate key or model | Result |
|---|---|
| The reciprocal follows the distance | 4,617 conflicts over 40 viewpoints |
| It follows the distance and `e1` | 3,126 conflicts, so `e1` is not the missing term |
| It follows the scanline index | Zero agreement between any two horizons |
| It follows the walk, `(start, horizon, line)` | 545,700 empty intersections |
| The distance is missing an integer offset | No offset from -6 to +6 aligns two viewpoints |
| It is `2**20 / |d|` exactly | Reproduces 12.7% of scanlines |
| The same, with interpolation between table entries | 14.8%, and interpolation changed nothing |
| It is held in one of the part's 256 memory words | No word tracks it, under any shift |

The last row is the useful one. The value never appears in memory, so it lives in
a register or is never formed at all, and every attempt above assumed it exists
as a number the part computes once per line. That assumption is the thing to drop.

### The next step, narrowly

Read `$03a` and `$0d3` as instructions rather than as shapes: what the normalise
leaves in the pointer, which words `$0d3` reads at `rp = 100` and what it does
with them. `microcode.explain` prints the fields of a single word and
`routines.run` executes a routine against the model, so both halves can be
checked one instruction at a time against a case whose answer is already known.
That is bounded work on a routine of about fifty instructions, and it is the only
route left that does not go through the answers.

### `$02`'s state, verified and ready

Separately, everything `$0a` will need from `$02` is measured and holds across all
6,980 argument sets in the three recordings, with no key carrying two answers:

| table | keys on | rows | bytes |
|---|---|---|---|
| horizon and the second scale | argument 6 | 1,193 | 9,544 |
| the matrix | argument 5 | 3,302 | 19,812 |
| the first scale | arguments 2 and 6 | 3,033 | 24,264 |

53,620 bytes in total. The matrix needs two words rather than four, confirmed on
every set: the first and last entries are always equal and the middle two are
always negatives of each other. Arguments 3 and 4 never vary, at 32 and 256.

`parameter.py` and `state02.py` already build these and are included in no build.
Wiring them in is blocked on nothing except that `$0a` has no use for them yet.

### On enlarging the image

Storing `$0a`'s answers outright costs 9,210,432 bytes for the American recording
and 10,775,576 for the European. That is a question of address space rather than
of image size: LoROM reaches 4 MiB and ExHiROM 6 MiB, so 96 Mbit of storage does
not help without bank-switching hardware. It would also cover only the recorded
attract sequence and not a player.

Storing the reciprocal instead is a quarter of the size at worst, one word per
scanline against four, and far smaller than that under any key that works. So the
size question is settled the moment the key is.

## 21. `$0a` read out of the part, one instruction at a time

**Measured 2026-09-03, by executing the part's own program in the model and
watching its registers rather than by fitting its answers.** This is the method
section 18 asked for, and it settles in one pass what six attempts at inference
could not.

### The method that works

The model exposes the processor. Setting `registers.pc` and calling `core.step()`
runs one instruction, so a command can be driven normally and interrupted at any
address to read what the part is holding. Two addresses inside `$0a` matter:
`$372` and `$37b`, immediately after each of its two calls to `$0077`.

### The output stage, exact

At those two addresses the accumulator holds the two scales for the current
scanline. Multiplying them by the matrix reproduces **176 of 176 scanlines, all
four words each, with no exceptions**:

    answer = ((scale * M) >> 15) for M in (M0, M1, M2, M3)
    the first scale against M0 and M2, the second against M1 and M3

So the four answer words are two numbers, and everything `$0a` does reduces to
producing those two per scanline.

### The normalise, `$03a`

    dp = 0
    l <- a; a = a and idb        keep a copy, set the flags
    if a is zero, return with dp = 0
    loop: l <- a; a = a + a; dp + 1
          repeat while the addition did not overflow
    a <- l; dp - 1               step back to the last value that fit

It doubles until **signed** overflow, so the result lands in `[0x4000, 0x7fff]`,
normalised to bit 14 rather than bit 15, and the doubling count is left in the
data pointer. Every earlier attempt normalised one bit too far.

### The reciprocal, `$0d3`

It is not a table read. It guards zero by answering `$7fff`, normalises the sign,
sets the ROM pointer to 100, reads consecutive words while multiplying, **computes
a new ROM pointer from an intermediate result** at `$0de`, and saturates to
`$7fff` at two separate points. That is a refinement rather than a lookup, which
is why a table read reproduced 14.8% and interpolating between entries changed
nothing.

Captured at its return, it answers a mantissa in `a` and an exponent in `b`:

| d | a | b | 2**20 / a |
|---|---|---|---|
| -34 | -30840 | 3 | 34.00 |
| -33 | -31776 | 3 | 33.00 |
| -32 | -16384 | 4 | 64.00 |
| -31 | -16912 | 4 | 62.00 |
| -16 | -16384 | 5 | 64.00 |

So `a = 2**20 / (|d| << (b - 3))`, with the divisor held in `(32, 64]` and `b`
counting the doublings from a base of 3. The sign of `a` follows the sign of the
distance, on every line. **The reciprocal is a function of the distance alone**,
which is visible directly here and was never visible through the answers.

One detail is unresolved and is the next thing to look at: across the first
eighteen lines the implied divisor runs 49, 48, 47 ... 35, then **repeats 35**
before continuing 34, 33. A step of exactly one per scanline would not repeat, so
the walk carries a fractional part. That single repeat is the whole of what is
still unexplained about the reciprocal.

### What is still missing

Feeding `a << (b - 3)` into the existing scale formula reproduces 23% of
scanlines, up from 12.7%, so the reciprocal is right and the arithmetic between
it and the scale is not yet. `$0077` is that arithmetic: it normalises again,
adjusts an exponent against ROM pointers `$0f` and `$31`, and loads the
multiplier. Reading it the same way this section read `$03a` and `$0d3` is the
remaining work, and the scales are already capturable exactly, so any candidate
can be checked against them line by line instead of against the answers.

## 22. `$0a`, the whole chain

**Measured 2026-09-03 by stepping the part and reading its registers at each
stage.** Every step below was checked against the part rather than fitted.

### The chain

For each scanline, with `m1` and `e1` the first scale's mantissa and exponent
from `$02`, and `m2` and `e2` the second's:

1. **Distance.** The loop keeps a line counter in `RAM[$09]`, seeded from the
   command's argument and incremented once per line, and forms the distance from
   it and the horizon in `RAM[$c8]`. Captured at `$36b`, the distance magnitude
   runs 49, 48, 47, 46 where the naive `argument + 1 + line + horizon` gives 50,
   49, 48, 47, so the magnitude is one less than that expression throughout.

2. **Normalise, `$03a`.** Double until signed overflow, then step back. Leaves
   the magnitude in `[0x4000, 0x7fff]` and the count of doublings behind. At
   `$36b` the accumulator holds exactly `-(49 << 9)`, `-(48 << 9)`, and so on.

3. **Reciprocal, `$0d3`.** Answers a mantissa in `a` and an exponent in `b`, with
   `a = 2**20 / x` for `x` the magnitude held in `(32, 64]` and `b` counting the
   doublings from a base of 3. It refines rather than reads: it computes its ROM
   pointer from an intermediate at `$0de` and saturates twice.

4. **Multiply.** `a = (m1 * recip) >> 15` and `b = b + e1`. Verified against the
   part: `m1` of `$6000` against a reciprocal of `-21400` gives `-16050`, and
   `b` of 3 plus `e1` of 3 gives 6, both exactly as captured at `$370`.

5. **Scale, `$0077`.** `scale = a >> (15 - b)`, an arithmetic shift.
   **175 of 176 scanlines, 99%.** The single miss is the saturation path, where
   `$0077` clamps to `$7fff` rather than shifting.

6. **Output.** Four words from the two scales and the matrix:
   `(scale * M) >> 15`, the first scale against `M0` and `M2`, the second against
   `M1` and `M3`. **176 of 176 scanlines, all four words, 100%.**

### Why every earlier attempt failed

They all tried to recover one number per scanline from the answers. The chain has
two normalisations, two saturations and a mantissa-exponent pair, so no single
number exists to recover, and the exponent moves with `e1`, which is exactly the
pattern that made the conflicts track `e1` rather than the horizon.

### What is left

The saturation case in `$0077`, worth one scanline in 176, and confirming the
distance expression against a second viewpoint. Both are checkable line by line
against captured scales rather than against answers, so neither is open-ended.

With that, `$0a` is arithmetic the cartridge can run: one normalise, one
reciprocal, two multiplies and two shifts per scanline, with no table beyond the
reciprocal itself. The storage question raised earlier is moot, since nothing
large needs storing.

## 23. `$0a` closed, and the ground it draws

**Measured 2026-09-03. Every number below came from driving the part or from
running the built cartridge, never from reading either.**

### Both loose ends from entry 22 are shut

The saturation path and the distance expression were the two things entry 22 left
open. Both are now measured rather than argued about.

**`$0077` has three exits, not one.** It normalises, works out
`over = exponent - count - 15`, and then:

| `over` | what it does | where |
|---|---|---|
| below nought | shifts right by `-over`, by multiplying by a power of two | `$07e` |
| exactly nought | hands the normalised value back untouched | `$080`, `$086` |
| above nought | clamps to `$7fff`, or `$8001` when negative | `$083`, `$085` |

`$8001` rather than `$8000`: the part loads that constant, so the most negative
scale it can answer is minus 32,767. Across 43,440 answer words the exact exit
fired 121 times and the clamp 132, so neither is a corner nobody reaches.

The shift is a multiply by a word out of the part's own data ROM. Read off the
part: `$022` through `$030` hold 1, 2, 4 up to 16,384, and `$000` through `$021`
are all nought. So a shift of sixteen or more is a multiply by nought rather than
a sign fill, and every shift below that is an arithmetic shift right.

**The distance is not `argument + 1 + line + horizon`.** It is
`((step * line) >> 15) + horizon`, with `step` a seventh word `$02` deposits at
`RAM[$49]` and `line` starting at the argument itself. Entry 22 read the
magnitude as one less than the naive expression, and that off-by-one was the
fractional walk: the step is 32,032 rather than 32,768, so the distance repeats a
value roughly every fourteen scanlines. That repeat is the one thing entry 21
could not explain, and nothing was wrong with the reciprocal at all.

### The reciprocal is a table after all, over the right domain

Entry 15 concluded that a reciprocal table keyed on distance could not be right,
because the same distance reached from different horizons gave different values.
That conclusion is withdrawn. The key is not the distance: it is the distance
**after `$003a` has normalised it**, and the exponent that normalise leaves is
carried separately. Keyed that way it is an exact function, checked on every
scanline of 60 argument sets.

The domain comes from the code rather than from a recording. `$003a` doubles
while the top two bits agree, so what it leaves always has a magnitude between
`$4000` and `$7fff`. That is 16,384 values, one bank, and no input can miss it.
The sign is not stored either: `$00d3` strips it, refines the magnitude, and
negates on the way out.

### The whole chain, as the cartridge now runs it

Per scanline: one multiply for the distance, one normalise, one table read, one
multiply and one shift for each of two scales, and four multiplies for the four
answer words. `raster.py` is that arithmetic in Python and
`asm/dsp1-ground.asm` is the same thing in 65816.

**43,440 of 43,440 answer words exact**, on 60 `$02` and `$0a` pairs spread
across all three recordings, against the part and against the recordings both.

## 24. Three commands never reached the port at all

**Found 2026-09-03, by dumping the cartridge's own work RAM rather than by
reading the code.** This is why the ground was missing, and it had nothing to do
with `$0a`'s arithmetic.

### What the dump showed

With `$0a` computing exactly, the ground was still blank. `!CARRY_02`, where the
port keeps `$02`'s arguments, held `$5555` on every frame: the game's own fill,
never written. So `$02` had never once completed through the port.

### Why

The game reaches the part two ways. Most sites are a four byte long store, which
`patch.py` replaces one for one with a call. Twelve places instead push the data
bank and use three byte absolute instructions, which have no room for a call and
nothing in the operand a scanner can recognise. Those go to the window at bank
`$7D`, which is ROM: every store is discarded and every read comes back nought.

Three commands are asked for that way, and 44,474 of the recording's calls go
through it:

| command | where | what was lost |
|---|---|---|
| `$02` | `$00:CB4E` | the ten words `$0a` reads, and four the game turns into its own state |
| `$0a` | `$00:CAA8` | the line the stream starts at |
| `$10` | `$00:CB17` | already replaced, by `dsp_route_10` |

`$02` is the one that mattered. The game computed its own state from four
zeroes, and one of those zeroes is what `$0a`'s argument is derived from, so the
ground had no chance of being right however exact its arithmetic was.

### The fix, and the two boundaries that had to be right

Both runs are now replaced whole, the way `$10` already was. Two details cost a
black screen each before they were read properly:

**Neither run may start at the `pea` that sets the data bank.** On the path the
demo takes, the `pea` before `$02` at `$00:CB4A` is jumped over by a `bra` at
`$00:CB3F`, so the byte the closing `plb` at `$00:CBB2` collects was pushed by
the `pea` before the `$10` run. A run that swallowed a `pea` leaves the stack one
byte out.

**Both boundaries were off by one on the first attempt.** The recording names the
site by the counter *after* the store, so `$00:CAAF` is the `rep` following the
command byte rather than the store itself. Ending a run one byte early leaves the
high byte of an address behind as an opcode: `$80` is a branch, and `$09` is an
or. Reading the bytes rather than the site numbers settles it.

### What the cartridge now writes

Its own 65816 code, checked against the part on the arguments the running game
supplied: **704 of 704 words exact**, on two frames sampled minutes apart. The
ground draws, and the runway and the island sit where the retail cartridge puts
them.

## 25. What it costs, measured rather than modelled

**Measured 2026-09-03 by building variants with one stage removed and watching a
frame counter the game itself steps.**

### How it is measured

`RAM[$1a1c]` steps once per frame of the game's own loop. In the retail
cartridge it moves 300 times in 300 console frames, exactly. That ratio is the
speed, and it needs no model of what any instruction costs.

The converted cartridge moves it 20 times in 300, so the flight runs at **a
fifteenth of speed**. Nothing stalls and no frame is dropped: the console
delivers every one, and the game's own loop is what waits.

### Where the time goes

Each row is a build with one stage taken out, so the difference from the full
build is what that stage costs. The last column is frames of processor time per
frame of the game.

| build | speed | frames | what it says |
|---|---|---|---|
| everything | 0.067 | 15.0 | |
| `ground_block` returns at once | 0.250 | 4.0 | 4 frames are not `$0a` at all |
| `ground_line` writes constants | 0.200 | 5.0 | the scanline chain is 10 frames |
| the four output multiplies removed | 0.090 | 11.1 | they are 3.9 of those 10 |
| the three state searches removed | 0.077 | 13.0 | they are about 2 |
| the two `$0077` calls removed | 0.067 | 15.0 | too small to read |

Two of those readings changed what to work on.

**A quarter of the cost is not `$0a`.** Four frames per game frame go on the
lookup and the port before the ground is computed at all: `$02` and `$10` each
take a search of the recorded table, and the port serves eighty writes and
twenty two reads a frame. That was there before this work and is untouched by it.

**The two saturating scale routines cost nothing measurable.** They were the
obvious suspects, being loops of up to fifteen shifts each, and taking both out
moved the counter by less than one tick. The multiplies are the cost, not the
loops.

### What was tried and did not work

The distance multiply is gone, replaced by a running thirty two bit sum stepped
by one line's worth. That is exact rather than close, because the part's
multiplier answers bits fifteen through thirty of the product and those are the
bits the sum already holds. **0.057 to 0.067, seventeen per cent**, with every
one of 704 words still exact.

A multiply written for this file rather than reused from `$00` was **slower**:
0.067 to 0.063. The console's multiplier takes two byte registers side by side,
so one sixteen bit store starts it and eight changes of accumulator width
disappear, and the eight cycles it needs can be spent setting up the next pair
instead of on `nop`s. All of that is real, and splitting the operands into bytes
and putting the thirty two bit product back together cost more than it saved. It
was reverted: `op_00_body` is shorter, already checked against the part on four
hundred argument sets, and shared with three other commands.

### What is left, in the order it is worth doing

1. **The four output multiplies, 3.9 frames.** The matrix is fixed for a whole
   frame and carries two numbers rather than four, and the scale it multiplies is
   usually small enough that two of the four partial products are nought. A path
   chosen once per frame rather than per scanline is where to look.
2. **The two chain multiplies, most of the remaining 6 frames.**
3. **The four frames outside `$0a`.** The largest single piece of that is a
   recorded-table search for `$02`, whose answer the game turns into four words
   it could be handed directly.

None of it changes an answer, so all of it can be checked against
`raster.retail.test.py` and against the running cartridge, which is the point of
having pinned the arithmetic before optimising it.

## 27. What is left before the demo is the demo, and it is not `$0a`

**Measured 2026-09-03 by matching our run against the retail cartridge frame for
frame on the game's own frame counter, rather than on console frames.**

### The demo is exact for 174 game frames and then stops being

`RAM[$1a1c]` steps once per frame of the game's own loop, in both cartridges, so
it lines the two runs up whatever speed either is running at. Compared that way:

| game frame | work RAM differing, first 8 KiB | what it is |
|---|---|---|
| 160 to 174 | around 380 bytes | the port's own state, the same every frame |
| 175 onward | 790 and climbing | the flight has diverged |

At frame 174 the retail cartridge levels out: `$58` goes from nought to one and
the pitch at `$2a` starts coming down, 14170 to 14167 to 14164. Ours keeps
turning, walking `$54` past 197 and never making the transition at all.

Section 30 closes this: the transition is gated on a counter at `$0130` that the
window redirect had stopped counting, and both cartridges make it once the counter
does.

Everything up to that point is exact. Every `$02` key our cartridge asks in those
174 frames is one the recordings hold, so the lookup hits and all eight words the
game derives from `$02` match the part. `$0a`'s 704 words match on every frame
sampled, before the divergence and after it.

### Sixteen sites still answer nought

The cause is not arithmetic. Classifying every command site in the recording by
the instruction that reaches the part:

| how the cartridge reaches the part | sites | calls |
|---|---|---|
| a four byte long store, replaced one for one | 12 | 160,939 |
| the redirected window, replaced whole | 3 | 20,834 |
| **the redirected window, nothing answering** | **16** | **17,730** |

Those sixteen are `$00:CDB3` to `$00:D4B0`, which is the flight physics, and they
ask `$00` seven times, `$0d` twice, and `$01`, `$03`, `$0e`, `$14` and `$28` once
each. Every one of them reads nought back, because the window is ROM filled with
nought. The physics runs on those noughts, which is why it holds a turn it should
have come out of.

### Why the three that are replaced could be and these cannot, yet

`$02`, `$0a` and `$10` are each one run of code that talks to the part and then
stops, so a run can be lifted out whole and answered in one call. This region is
not shaped that way: 104 separate accesses to the part are interleaved with the
game's own arithmetic, which clamps, negates and accumulates between them.
Replacing the region whole means reimplementing the flight model, which is not on
the table.

And no single access can be replaced where it stands. They are three byte
absolute instructions, because the data bank is already pointing at the part, and
a call is four bytes.

### The route that fits

Pairs of instructions do fit. `lda $36` and `sta $8000` are five bytes together,
which is a four byte call and one byte spare, and that spare byte is enough to
carry the direct page offset the load used:

    lda $36 / sta $8000     ->     jsl dsp_send_dp : db $36

The routine reads that byte through the return address the call pushed, uses it
as the offset, hands the word to the port, and returns one byte further on. The
same shape covers taking an answer back, and a handful of variants cover the
loads that are immediate, indexed or off the stack.

104 accesses across sixteen exchanges, and the shapes they take were counted
rather than guessed: 23 are a direct page load into a store, 13 a `sty`, 12 a
plain read, and the rest a long tail of about twenty forms. It is mechanical work
that `patch.py` can generate, and it is the next thing to do.

### What this does not say

That routing those sixteen is enough. It is necessary: the physics cannot be
right while part of it reads nought. Whether anything else is also wrong is a
question for after they answer, and the frame-for-frame comparison above is the
measurement that will say.

## 28. The sixteen sites are routed, and they were not what stops the demo

**Done and measured 2026-09-03.** Entry 27 said routing them was necessary and
did not say it was sufficient. It was necessary, and it is not sufficient.

### How they were routed

110 accesses across $00:CDB3 to $00:D4B0, each a three byte absolute instruction
where a four byte call does not fit. `jsr` does fit, because it stays inside the
bank it is called from, so every one of them became a call to a thunk in the
game's own bank which calls across to bank $10:

| shape | how many | what answers it |
|---|---|---|
| `sta $8000` | 52 | `dsp_write`, unchanged |
| `sty $8000` | 22 | a hook, because the width is the index register's |
| `lda $8000` | 19 | `dsp_read`, unchanged |
| `adc $8000` | 6 | a hook that performs the add rather than reproducing its flags |
| `ldy $c000` | 3 | a hook, because the poll after it branches on the sign |
| `stx $8000` | 3 | a hook |
| `ldx $8000` | 3 | a hook |
| `stz $8000` | 1 | a hook |
| `ldy $8000` | 1 | a hook |

**The thunks needed 45 bytes of the game's own bank**, and where they sit was
measured rather than chosen. $00:AD28 begins 322 bytes of `$ff`, and a run of one
repeated byte is not proof that nothing reads it, so 1,631 bytes across the
fourteen such runs in that bank were overwritten with a marker and the demo run
for 1,800 frames. The console's whole 128 KiB came out byte for byte identical to
the unmodified build at every frame sampled.

**One deliberate difference.** Neither index register has a long addressing mode,
so `ldx $8000` and `ldy $8000` move their value through the stack and end with
the caller's flags rather than flags set from what was loaded. All four of those
in the region are followed by a store or an `adc`, and the next instruction to
read negative or zero always comes after one that writes them, so nothing can
observe it. That is a property of the code rather than of any recording, and
`patch.retail.test.py` walks forward from each one and fails if a branch on those
flags comes first.

### They work

`$06` and `$08`, two of the flight model's own variables, now hold what the
retail cartridge holds at every game frame sampled. Before the routing they held
a different value on every other frame, because half of what the model read came
back nought.

### They are not the trigger

The demo still leaves the retail cartridge's course at the same game frame it did
before, 175, with the same values. Routing 110 accesses that were reading nought
changed the divergence point by nothing at all.

So the flight model was running on noughts and is not any more, and something
else decides what happens at frame 174. What that is is the open question. The
plane is in a level turn up to there, `$54` climbing one a frame, and retail
stops it at 197 while ours carries on. Neither of the two places that write `$58`
explains it: one needs a stage counter that reads $0800 in both, and the other
only ever lowers the value.

### A measurement that was not one

Entry 27 read a diff of the console's memory as showing 174 frames of exact
agreement and a step change after. The step change is real. The agreement was
not: a snapshot is taken at a console frame boundary, one game frame is one
console frame in the retail cartridge and about fifteen in this one, so every
snapshot here lands at an arbitrary point inside the game's own loop and several
hundred working variables differ from the first frame onward for that reason
alone. The claim that survives is the narrower one it rested on: the arguments
`$02` is asked with match the recording's, frame for frame, until 175.

## 29. Seven accesses the scanner was never looking for

**Found 2026-09-04 by logging every exchange the cartridge completes and diffing
that against the recording's own, rather than by reading code.**

### The measurement that found it

A throwaway build wrote the command byte of every completed exchange into a ring
in work RAM. Dumping it beside the recording's command stream showed the two are
not the same shape:

    the recording   11 13 06 13 06 13 06 13 06 11 13 06 ...
    ours            11 13    13    13    13    11 13    ...

`$06` was not happening at all. It is the command this cartridge asks most often,
74,261 times in one recording, and it had never once been asked.

### Why

`$00:A1AD` holds `adc $3f8000`, a long instruction that reads the part and adds
what it reads to the accumulator. The `bmi` after it decides whether the whole
`$06` exchange happens.

`patch.py` never replaced it. It classifies a site by opcode and knew two: the
long store and the long load. So `adc` read the byte the answer table happens to
hold at `$3f8000`, and the branch after it went whichever way that byte said.

Seven sites are like that: six `adc` and one `eor`. The driver model this project
is checked against does not report them either, and for a good reason: it answers
"where does this cartridge reach the part", and it answers it for the two shapes
every cartridge uses. A read-modify-write against a coprocessor port is this
cartridge's own habit. So `patch.py` searches for those two shapes itself, with
the same exact encoding test, and says why in `COMBINING`.

### And five more windowed regions

Entry 28 hooked one run of three byte accesses, `$00:CDB3` to `$00:D4B0`, on the
strength of one push of the part's bank. There are twelve such pushes. Clustering
the accesses each one leads to gives six runs holding 199 accesses, not one run
holding 110:

| run | accesses |
|---|---|
| `$00:8054` to `$00:80C4` | 18 |
| `$00:960A` to `$00:964F` | 12 |
| `$00:CAAC` to `$00:CBA5` | 31 |
| `$00:CDCD` to `$00:D0A8` | 77 |
| `$00:D1F7` to `$00:D280` | 25 |
| `$00:D47C` to `$00:D679` | 36 |

Two shapes appear only in the new runs: `bit` on the status, and `ldx` on it.
`bit` needs care, because `bit` against an immediate is the one form that sets
zero alone, so its hook works out the three flags a real read would set and writes
them into the flags the caller gets back.

### A bound taken from a bad walk

The first attempt at those bounds broke the flight from its thirty eighth frame.
The clusterer disassembled forward from each push for a fixed distance, ran past
the end of the routine, decoded the next one at the wrong register widths, and
reported accesses that are not there. Forty four bytes of ordinary arithmetic
ended up inside a region and were replaced with calls.

Stopping the walk where the routine returns fixes it, and `patch.retail.test.py`
now decodes each region from its own start for the same reason.

### What it did not fix

None of the three moved game frame 175, and section 30 says why: the trigger was
not an answer at all. They were real faults and they were fixed:

| fault | how long it had been there | effect |
|---|---|---|
| seven long read-modify accesses unreplaced | since the first build | `$06` never asked |
| `$11`'s arguments never kept | since the first build | `$13` and `$1b` keyed on the game's own fill |
| five windowed runs unhooked | since entry 28 | 89 more accesses reading nought |

Speed was ruled out as the cause at the same time. Overclocking the console's
processor to snes9x's "max" setting takes the flight from a fifteenth of speed to a
seventh, and the divergence stayed at game frame 175 exactly, which is what a
threshold on a frame counter does and not what a race does.

## 30. Frame 175, and the accesses that were never the part

**The demo now tracks the retail cartridge past game frame 400.** It used to leave
its course at 175 and never come back. What stopped it was not an answer: every
answer the table serves was already exact, and the whole search for a wrong answer
came back empty.

### The measurement that ended the search

Counting table misses per command, with the counters zeroed at first use rather
than read against whatever the console powered up with:

| command | asked per frame | missed | what a miss means |
|---|---|---|---|
| `$00` | 7.9 | every time | its arithmetic, exact, so a miss costs nothing |
| `$03` | 1.0 | every time | the nearest row instead of the answer |
| `$0d` | 2.0 | half of them | the same |
| `$02` `$06` `$0c` `$0e` `$10` `$13` `$14` `$28` | 0.5 to 5.6 | never | |

`$03` misses because its key carries the last `$14`'s six arguments and those were
nought. `$14` itself hits every time, and its arguments really are nought at that
point in the demo, which the recording agrees with. So the misses are honest and
they are not the trigger either.

### What was actually wrong

The conversion redirects the twelve `pea $003F` pushes to a bank it fills, so that
any access it failed to replace lands somewhere harmless rather than on a part that
is no longer there. That works for the part. It also moves everything else in those
blocks, and not everything in them is the part.

The first eight kilobytes of every bank from `$00` to `$3F` mirror work RAM. Bank
`$3F` address `$09E0` is work RAM `$09E0`, and the game uses that: thirty five
three byte absolute instructions inside those blocks reach its own memory. The
window is ROM at every address, so every one of those reads answered nought and
every one of those writes went nowhere, from the first build.

Two of them decide the demo:

    $00:CF44  adc $0130        a counter, four less every frame
    $00:CF47  sta $0130
    $00:CF52  sta $0130        reset once it passes the threshold

The next phase of the demo begins when that counter passes its threshold. At four
a frame it takes 175 frames to get there. With the counter stuck at nought the
phase never began, and everything the phase drives, `$13` from `$0e` to nought,
`$4a` counting, the camera moving, stayed as it was.

### And one access that was the part

`$00:CD87 sbc $8000` is a port read, in a nine instruction subroutine the flight
model calls three times a frame. The subroutine has no bank push of its own; it is
called from inside the flight model's block and inherits its bank, so nothing that
starts from a push finds it and it sits outside every region the clustering
produced. The read never happened, so every read after it in the same answer was
one word early.

A shape by this name was added and then removed once before, on the grounds that it
came from a walk that had decoded past the end of a routine. The walk was bad and
the instruction is real.

### What was tried and rejected

Moving the window to a bank below `$40` fixes all thirty five in one line, because
such a bank carries the mirror. Measured: the run came out 30,000 bytes from the
cartridge at every frame rather than the 200 it was at, because it changes every
windowed access at once, including the ones that were reading nought from code
paths whose behaviour then changed. So each one is corrected on its own, with a
measurement per change, and the window stays where it is.

### Where it stands

| frames 66 to 405, work RAM against the cartridge at the same game frame | |
|---|---|
| before | 200 bytes differ, stepping to 650 at frame 175 and never recovering |
| after | 45 to 65 bytes differ, no step, through frame 405 |

### The rest of them, and what finding them took

All 31 are routed now. Getting the list right needed two corrections to how the
blocks are read, and both had already produced a wrong answer once.

**A block is decoded at the widths it runs in, and those are not the same for
every block.** The first audit used one pair for all twelve and reported an
`sbc $30c2,y` in the block at `$00:D03F`, which would have been the only one of
these naming the console's own register space rather than memory. `$00:D031` is
`sep #$30`, so that block runs eight bits wide, and the same bytes there spell
`lda $1aea`, `cmp #$0a` and a branch. Four instructions later the walk lands back
on the port access after them, which is why a scan for the port cannot tell the
two readings apart. `patch.retail.test.py` now carries a width pair per block and
a test that fails if one of them moves an access or invents one.

**A block is walked by following its branches, not by falling through.** The same
block has two arms. The one a linear walk sees ends at `$00:D068`; the other
begins at `$00:D06C`, runs to `$00:D0AA`, and holds `lda $1ac3`, `lda $1876` and
`lda $1870`. A fall-through walk misses all three.

The bounds also matter in the other direction. Two instructions at `$00:D55F` and
`$00:D581` spell shapes this set knows and sit in the gap between two blocks,
where the game's own data bank is in force and they already reach what they mean
to. Bounding the search by the blocks rather than by the port-access runs is what
leaves them alone.

| frames 69 to 405, work RAM against the cartridge at the same game frame | |
|---|---|
| with eight routed | 30 to 110 a frame, with one-frame spikes to 641 and 195 near 375 |
| with all 31 routed | 30 to 60 a frame, worst 133 outside the last sampled frame |

Twenty two bytes differ at every frame. Twelve are three patched calls inside code
the game copies into work RAM and executes there, which cannot match by
construction. The other ten are `$0182` through `$0186` and `$01E2` through
`$01E6`, which this build writes and the cartridge leaves at the console's
power-on fill. That is the next thread.


## 31. Where the time goes, and the tenth of it that came back

**17.72 console frames per frame of the game's own clock**, down from 19.55.
Measured on `RAM[$1a1c]`, which both cartridges step once per frame of their own
loop, over 7,000 console frames in the middle of the flight.

### The split

Each row is the whole flight re-measured with one piece stubbed out, so the
difference from the row above is what that piece costs.

| build | console frames per game frame | what the gap is |
|---|---|---|
| as it stands | 17.72 | |
| `mul16` returning at once | 12.32 | 5.40, the multiply itself |
| `op_00_body` returning at once | 9.42 | 2.90 more, the sign handling around it |

So the multiply is 47% of the running time, and it is asked 1,061 times a frame:
six per scanline of the ground, 176 scanlines.

That count was 471 the first time it was measured, which is the same number with
a sixteen bit counter that had wrapped once. A per-call cost worked out from the
wrapped count is a factor of two wrong, and it made the routine look far more
expensive per call than it is.

### What was tried on it

**The screen's own multiplier.** $211B and $211C multiply sixteen signed bits by
eight signed with no wait, where $4202 multiplies eight unsigned by eight and
needs eight cycles before the answer can be read. Two of the first replace four
of the second and the sign handling disappears with them.

It came out at 17.99 against 19.55, a twelfth, and the ground it produced
differed from the cartridge's on a third of its words. Both halves of that are
reasons not to keep it: the saving is small because the cost is the thirty two
bit bookkeeping around the multiply rather than the multiply, and a wrong answer
is not worth a twelfth of anything. Reverted.

### What was kept

**The second view of the cartridge.** Everything above bank $80 is the same ROM
read three cycles faster instead of four, once $420D says so. This project's
code and tables now live there and the game's own banks do not, so the game's
timing is untouched.

Two things had to be true before it was worth anything, and the second was not:

| | |
|---|---|
| the header bit at $7FD5 | set by `patch.py`, and by itself worth nothing |
| $420D | never written, because a game built for the slower timing never writes it. `dsp_port_reset` writes it now |

Moving the code alone gave 18.13. Moving the tables with it gave 17.72.

**One bank arithmetic assumption broke on the way.** `lut_place` stepped over
banks $7E and $7F, which are memory rather than cartridge, by comparing every row
address against them. Every bank in the second view is above that comparison, so
it answered the same way every time and added two banks to every row address in
the table. The demo ran, faster, and read the wrong rows: 31,000 bytes of work
RAM away from the cartridge instead of 20. The comparison is made when the file
is assembled now, since which side of the hole the table sits on is known then.

**And one in the model.** `routines.py` mapped a bank straight onto a file offset
with no mask, so a read of bank $91 ran off the end of the image and answered
nought. `$04` reads its trig tables that way and started answering nought with
it. The mirror is in the model now.

### Four of the six multiplies became a table

**14.26 console frames per game frame**, from 17.72.

Every one of the six has the same shape: something that does not change for the
whole stream, times something that does. Four of them share two constants,
because ground_state writes the cosine into two of the four matrix words and the
sine, negated, into the other two. So two tables of the constant times each of
the 256 byte values answer four of the six, and a product is then two lookups
and an addition rather than four hardware multiplies, four eight cycle waits and
a sign put back around the outside.

A table is built by adding the constant to a running sum 256 times, and it is
built once per stream against 176 scanlines of use. Half the streams do not
rebuild at all: across the recording the key the matrix is looked up by repeats
from one frame to the next 54% of the time.

An entry is five bytes, not four: a nought and then the constant times the entry
number. The nought is what lets one entry answer both halves of a multiply,
since reading the four bytes after it gives k times b and reading the four
bytes starting at it gives that times 256, which is the shift the high byte
needs and which costs eleven instructions to do by hand.

**Two things went wrong, and both were silent.**

The memory the tables went into was not free. !PORTRAM's run was chosen by
keeping the bytes that never changed across a run of the demo, and a byte the
game reads but never writes passes that test as easily as one it never touches.
$7FDE00 is such a byte. Five kilobytes of tables written over it stopped the
demo before its second frame. What is actually spare was then measured the other
way: bytes holding the console's power-on fill in every one of 600 frames of the
retail cartridge, which a byte the game reads cannot. That leaves $7FED01 to
$7FFBFF, 3,839 bytes, which is two tables and not four.

And the assembler evaluates left to right. `!MULTAB+!MULSPAN*0+1` is
`((!MULTAB+!MULSPAN)*0)+1`, which is 1. Every table read went to address 1 and
every table stayed as the console left it, with nothing in the source looking
wrong and the demo running just slowly enough to look plausible. Each table is
named outright now.

### All six, and a better way to measure

**11.54 console frames per game frame**, from 14.53.

The other two got tables once the search for spare memory was widened from the
window !PORTRAM sits in to the whole 128 kilobytes. Measured the same way, bytes
holding the console's power-on fill in every one of 600 retail frames, the
longest run is $7E:E000 to $7E:FFFF at 8,192 bytes, and there are 32,888 bytes
of them altogether. Four tables need 5,120.

**The measurement had to be fixed first.** Console frames per game frame varies
with what is on screen, from 10.6 to 13.5 across one run, so timing two builds
over the same console frames times them on different scenery. Every figure here
is now the console frames taken to run game frames 250 to 500, which fixes the
workload.

Under that measure the split of 11.63 is:

| | console frames | |
|---|---|---|
| ground_line | 6.56 | of which the six multiplies are 5.46 |
| the table search | 3.51 | |
| the answer copy | ~0 | |
| everything else | ~1.6 | the port, the other commands, and the game itself |

A table lookup is 231 cycles against the general multiply's 350, which is less
of a gap than it looks like it should be: 37 instructions, four of them long
reads.

### Three things tried that were slower

**Eight byte entries**, so that an index would be three doublings rather than
two doublings, a store, an addition and a load. 12.94 against 11.54. The four
instructions a multiply are real, and the noughts and the build loop walking
half again as far cost more.

**The answer base in the header**, so that lut_answer would not multiply the row
count by the key width on every call. 11.63 against 11.54, and the routine it
was meant to speed up measures at nothing either way.

**The row offset by shifts** rather than the bit serial loop, chosen from a jump
table on the width. 11.76 against 11.54. The widths asked for are small enough
that the loop it replaces was already short.

All three were exact. They are recorded because the reasoning behind each was
sound and the measurement disagreed, which is the only reason any of them was
reverted.

### What is left

The multiply, at 47%. What it spends its time on is not the arithmetic but
assembling a thirty two bit product out of sixteen bit pieces, and a table has
not changed that: it replaced four hardware multiplies and their waits with four
long reads.

Then the table search at 3.51, which is around 435 bisect steps a frame across
twenty odd commands. `$06` alone is 75,278 rows and seventeen steps, ten times a
frame. An index on the first byte of the key would cut eight steps off every
search of it, at 256 entries a command in ROM.

## 32. The panel was never missing, and the flicker was one interrupt

**The instrument panel and the sky are drawn on every picture now.** They were
drawn correctly all along, on one picture in sixteen, and the fifteen between
them were the flicker.

### What the screen actually is

The flight screen is not one picture. It is three bands, and the console is told
to change what it draws between them from an interrupt fired at a named scanline:

| scanline | what its handler does |
|---|---|
| 47 | sets the sky layer's scroll from `$1ff0` through `$1ff3` |
| 94 | sets the drawing mode from `$f14d` and the layers from `$1fef`, which is what turns the panel band into the ground band |
| 255 | `$f1da`, a bare `rts` |

Each handler arms the next from `$18fa` and `$18fd` and steps a counter at
`$0080`. The sequence is armed from the top by `$00:f168`, reached through
`jsr $fe7e` at `$00:ec92`, once per frame of the game's clock.

### Why that is enough on the cartridge and not here

On the retail cartridge one frame of the game's clock is one picture, so nobody
has to tell the two apart. Here the part answers in software and one frame of
that clock is about eleven to sixteen pictures. The sequence is armed once, runs
once, and the pictures after it are drawn with what the last interrupt left
behind: the ground band's mode and layers over the whole screen. No panel, no
sky, and the ground's own mode stretched across the top.

### What the measurements ruled out first

Four things were measured and none of them was it, which is worth recording
because each looked plausible and each cost a build:

| suspected | measured |
|---|---|
| video memory | byte for byte identical between a bright picture and the dark one after it |
| the HDMA channels | all eleven registers of all eight channels identical between the two |
| this project's tables stamping on the game | `$7e:e000` through `$7e:ffff` holds the power-on fill in retail across twenty samples of the demo; the differences there are our own tables mid-rebuild |
| forcing every HDMA channel on | raised the brightness and wrecked the ground, because the channels it turns on have no tables |

The diff that pointed the right way was by row rather than by byte: rows 0 to 46
and 48 to 93 differ and rows 94 to 223 do not, and 47 and 94 are exactly the two
scanlines the interrupts fire on.

### The fix, and why it goes where it goes

The third interrupt is the only thing in the game that happens once per picture
rather than once per frame of the game's clock, and in the retail cartridge it
does nothing at all. So `patch.py` points its table entry at
`asm/dsp1-raster.asm`, which arms the sequence from the top. Scanline 255 is
below the picture, so the work lands between one picture and the next.

`$00:f168` itself is deliberately not called. It ends by enabling interrupts and
is shared with screens that are not the flight, and a build that called it
stopped working the moment the demo reached the runway. The rearm reads the same
four tables `$00:f168` reads rather than repeating its numbers, and does nothing
at all unless `$1fef` holds `$13`, which is the flight.

### What it cost and what it changed

| measure | before | after |
|---|---|---|
| screen brightness across sixteen pictures of the demo | 83.6 to 114.7, spread 31.1 | 114.3 to 114.4, spread 0.05 |
| console frames per frame of the game's clock | 11.41 | 11.15 |
| the flight model, `$1800` to `$1aff`, against a build without the rearm | | identical on all 271 game frames compared |

The flight model being identical is what says this is a display change and
nothing else. The display buffers differ by 15 to 100 bytes a frame, which is the
sprite shadow caught at a slightly different moment inside a game frame that is
eleven pictures long.

## 33. Two commands that need no search, and two measured dead ends

**10.77 console frames per frame of the game's clock**, from 11.19, measured over
game frames 250 to 500 so the scenery is the same in both.

### What was changed

`$13` is a quarter of everything the table is ever asked, 65,332 of 257,189 calls
across a recording, and it has 1,512 rows, so halving them takes eleven compares.
Each of those compares works out a row's address with a thirty two bit multiply
before it reads a single word.

None of it was needed. Its seven key words take 1, 7, 8, 9, 1, 3 and 1 distinct
values, and those multiply to exactly 1,512: the key set is the whole product
rather than an arbitrary subset. A sorted list of every combination is counting
in mixed radix, so the row is the sum over the key's words of how far along that
word's own list the value sits, times the rows one step of it covers. Walking a
word's values and adding its stride at each step gives that sum with no multiply
at all.

`lutbuild.py` now finds any command shaped that way and writes the value lists
and strides to `build/lut-axes.asm`. Two qualify: `$13`, and `$18`, which the
game asks three times in a whole recording.

A value the block does not hold falls through to the search, which will not find
it either and will fall back. Nothing here can answer wrongly by being asked for
something outside the domain.

### Two that were measured and reverted

**A four byte table entry with a signed second table.** The five byte entry is a
nought followed by the constant times the entry number, so one table answers both
halves of a multiply: reading from the nought gives the product times 256 and
reading past it gives the product. The price is paid on every use, because an
entry's address is its number times five, and that is a shift, a shift, a store,
an addition and a load, done twice per multiply. Two tables of four byte entries
make the address two shifts, and holding the second one already signed removes
the sign correction and its branch as well.

Measured, it is faster where it was meant to be and loses overall:

| | console frames per game frame |
|---|---|
| as it stands, five byte entries | 11.19 |
| four byte entries, both tables built | 11.74 |
| four byte entries, the signed table left unbuilt | 10.09 |

So the multiply itself came down by 1.10 and building the second table cost 1.65.
The third row is not a correct build, it is the same instruction stream with the
second table's contents left as whatever was there, and it is what says the
multiply and the build can be told apart at all.

Checking each of the four constants on its own rather than in the two pairs the
searches produce them in changed nothing, 11.75 to 11.74, which sent the search
for the cost somewhere else. A counter in `ground_build` then said why: it runs
2.9 times per game frame, not the 2.0 the 54% and 52% repeat rates suggest. A
table is built 256 entries at a time and read about 264 times, so the ratio is
close enough to one that doubling what a build writes cannot be paid for by
anything the reads save.

**An index on the first key word.** Section 31 closed by naming this as the next
thing to do, on the reasoning that an index over 256 buckets cuts eight steps off
a seventeen step search. Measured against the keys themselves, it does not: `$06`
takes 836 distinct values in its first word and 57,342 of its 75,278 rows share
one high byte, so a byte index takes it from 17 steps to 16. Weighted by how
often each command is asked, a byte index leaves 93% of the steps and an index on
the whole first word leaves 82%.

The reasoning was sound and assumed a distribution nobody had looked at. Looking
at it is what made `$13` visible, which is the change that was worth making.

### What a one entry cache would have bought

Nothing, and it is worth writing down because it is the obvious first idea.
Across a recording the three busiest commands repeat the previous call's key
0.1%, 0.0% and 0.7% of the time. The commands that do repeat, `$11` at 99.7% and
`$0e` at 100%, are a twentieth of the calls between them.

## 34. Whether anything but the processor can do this arithmetic

**No, and the reason is that the ground already owns the only other multiplier.**

The console has one arithmetic unit besides the 65816's own: `$211B` and `$211C`
are the mode 7 matrix A and B registers, and they double as a multiplier taking
sixteen signed bits times eight signed, with the twenty four bit product readable
at `$2134` through `$2136` and no wait at all. The processor's own multiplier at
`$4202` is eight by eight unsigned and makes the caller wait eight cycles, so the
mode 7 one is better on both counts.

It cannot be used. Read out of the running cartridge, the channels HDMAEN's `$f6`
turns on are:

| channel | writes | table |
|---|---|---|
| 1 | `$2131`, `$2132` | `$7F:6D00` |
| 2 | `$2126`, `$2127` | `$7F:6400` |
| 4 | `$211B`, `$211C` | `$00:CBB4` |
| 5 | `$211D`, `$211E` | `$00:CBBD` |
| 6 | `$211F`, `$2120` | `$00:CBC6` |
| 7 | `$210D`, `$210E` | `$00:CBCF` |

Channel 4 writes both of the multiplier's input registers on every scanline of
the picture, because that is how the ground is drawn: the matrix changes per
scanline and HDMA is what changes it. So between writing a multiplier operand and
reading the product, the hardware may overwrite the operand, and the odds of that
over a whole frame are not small.

Section 31 records an earlier attempt at this that came back with a third of the
ground's words wrong and was reverted as an unexplained failure. This is the
explanation.

There is no window to use it in either. The computation for one frame of the
game's clock spans about eleven pictures, and vertical blank is a seventh of a
picture, so confining the multiplies to the gap between pictures would cost far
more than it saves.

### The rest of the console

| | why not |
|---|---|
| the audio processor | a real second processor, but reaching it means four ports and a handshake, and one round trip costs more than the multiply it would replace. It also runs the game's music |
| DMA | moves bytes about twelve times faster than the processor and computes nothing. The tables are a running sum, not a copy |
| tables precomputed in the image | the constants take 3,052, 3,151, 1,199 and 841 distinct values across the four, and a table each is 1,280 bytes, so the set is 10.5 megabytes against the 12 the whole cartridge could ever be |
| mode 7 itself | it consumes a matrix and produces a picture. Nothing reads back out of it |

### Where the time actually is

Measured by stubbing one piece at a time, over game frames 250 to 500:

| | console frames per game frame | what the gap is |
|---|---|---|
| as it stands | 10.77 | |
| the six lookups stubbed out | 8.37 | 2.40, the lookups themselves |
| the second of two tables left unbuilt, section 33 | | 1.65, what building a table set costs |

So of the multiply's roughly 4.05 console frames, building the tables is 1.65 and
reading them is 2.40. A table is 256 entries and is read about 264 times, which
is why section 33's four byte entries lost: they made the reading cheaper by 1.10
and the building dearer by 1.65.

### Two more that measured worse

**Checking each of the four constants separately** rather than in the two pairs
the searches hand them over in: 10.77 either way. The two words of a pair come
out of one search keyed on one argument, so they move together and the finer
check never fires.

**Reordering the build loop** so the sum's low half advances the moment it has
been stored, which saves reloading both halves and is eight cycles an entry out
of sixty four: 10.96 against 10.80. The tables it builds are byte for byte the
ones the current loop builds, so it is correct and it is slower, and no reading of
the instruction timings accounts for it. Recorded rather than kept.

## 35. The search stopped being worth optimising, and the number that says so

**About 130 halvings per frame of the game's clock**, counted on a counter inside
`lut_compare` over game frames 300 to 310. Section 31 recorded 435, and section
33's change to `$13` is most of the difference.

That reframes what is left. At 130 halvings the whole search is under a console
frame of the 10.77, so removing it entirely would buy less than a tenth, and the
multiply at roughly 4.05 is four times the size of it.

### The index that was built and thrown away

`$06` is the largest command in the table, 75,278 rows and seventeen halvings,
and its first key word takes 836 values inside a span of 916. The rows are sorted
on that word, so each value's rows are one unbroken run, and 3,668 bytes of index
naming where each run starts replaces every compare before it: seventeen halvings
become 12.7 on average across the rows. `$02` is the same shape and costs another
3,680 bytes, and together they were measured against the recording as taking the
weighted halvings across every command to 62%.

Built, it made no difference at all: 10.80 console frames per game frame with and
without, on the fine grid. The answers stayed right, matching the retail
cartridge's flight model to two bytes on all 271 game frames compared, so the
narrowing was correct. It just was not worth anything.

The counter says why more precisely, and says something else that has not been
explained: with the index the count went **up**, 130 to 170. A narrower range
cannot take more halvings, and the answers were identical, so the discrepancy is
in the counting rather than in the search, and it was not chased because the
quantity being measured had already turned out to be too small to matter.

The lesson is the same one section 33 records about the byte index: a cost model
built from how often the recording asks each command is not a measurement of
where the time goes. Both times the model said a change was worth about a fifth
of the search and both times the console disagreed. What settles it is a counter
in the routine and a clock on the frame.

## 36. An exact clock, and what it says 15 frames a second would take

**11.07 console frames per frame of the game's clock**, over game frames 250 to
1000, against the retail cartridge's 1.00 measured the same way. That is 5.4
frames a second where the cartridge gives 60.

### The instrument came first, because the old one was lying

Every speed figure before this was taken by dumping work RAM on a grid of console
frames and interpolating the counter between samples. The grid was 20 or 100
console frames wide and the differences being argued over were smaller than that.
`emu/native.cpp` now watches the counter on every console frame and reports the
exact frame each end of the window was first reached on.

Calibrated by adding 24 instructions that do nothing to a routine that runs three
times a frame: 10.748 against 10.780, which is the noise floor. Differences above
about 0.05 are real.

### Where the time is

Each row is the whole flight re-measured with one piece stubbed out.

| | console frames per game frame |
|---|---|
| the retail cartridge | 1.00 |
| as it stands | 11.07 |
| with ground_line never called | 6.10 |
| with the multiply tables never built | 9.42 |

So `ground_line` is 4.97 of the 11.07, and building the tables is 1.65. Both
numbers carry a caveat worth stating: `ground_normalise` and `ground_scale` both
loop a number of times that depends on the value they are given, so a stub that
leaves those values garbage changes how long they run as well as removing work.

Everything else is small enough to have been counted rather than estimated, per
game frame: 132 calls into the port stubs, 29 into the mirrored hooks, 16 into
the lookup, and about 130 halvings inside it.

### What 15 frames a second would need

Four console frames per game frame. Removing every scanline of `$0a`'s
arithmetic and every table build together accounts for 6.62 of the 11.07, which
leaves 4.45, or 13.5 frames a second. So the target is above what a perfect `$0a`
reaches, and getting there would mean also removing the roughly 3.4 console
frames that sit between that and the retail cartridge's 1.00, none of which is
the port, the hooks or the search.

### One measurement that is still not understood

Counting `ground_normalise`'s doublings in a register rather than in a direct
page word takes eight cycles off each of about 2,120 doublings a frame. The
flight model it produces is byte for byte the one the current code produces, and
the doubling count is the same to within five. It measures 11.30 against 11.07.

That is the fourth change this session that was strictly cheaper in instructions
and measured slower, and the first one measured on an instrument known to be
exact to 0.05. It is recorded rather than explained.

## 37. The cost map, and why the small changes cannot be measured

**11.07 console frames per frame of the game's clock**, against the retail
cartridge's 1.00. Every figure below is from the exact clock section 36 added,
over game frames 250 to 1000.

### What each piece costs

Each row is the whole flight with one piece removed. The floor row leaves the
game and everything this project adds except `$0a` itself, and hands the game's
own code back the index register it carries on from, so the game does not notice.

| | console frames per game frame | what it says |
|---|---|---|
| the retail cartridge | 1.00 | |
| `$0a` reduced to nothing | 2.66 | everything else this project adds is 1.66 |
| as it stands | 11.07 | so `$0a` is 8.41, three quarters of the whole |
| with ground_line never called | 6.10 | ground_line is 4.97 |
| with ground_state never called | 4.99 | ground_state is 2.32, and it runs once a frame |

`ground_state` finds `$02`'s state and rebuilds the multiply tables, and the
rebuild is the bulk of it: measured on a counter, 2.9 of the four tables are
rebuilt per frame, each 256 entries.

Counted rather than estimated, per game frame: 132 calls into the port stubs, 29
into the mirrored hooks, 16 into the lookup, 130 halvings inside it, and one call
to `ground_block`.

### 15 frames a second is not ruled out by the floor

Section 36 put the floor at 4.45 and concluded the target was unreachable. That
was wrong: the stubs it rested on left `ground_normalise` and `ground_scale`
running on garbage, and both loop a number of times that depends on the value
they are given. The clean floor is 2.66, so 15 frames a second needs `$0a` down
from 8.41 to 1.34, which is a sixth of what it costs now. Hard, but the ceiling
is 22 frames a second rather than 13.

### Why nothing small can be measured here

The clock is exact and its cost model is linear: a spin loop of 176 turns costs
0.47 console frames and one of 704 costs 1.92, which is 4.09 times for four times
the work.

What is not stable is the comparison between two builds. The counter the window
is cut on runs from before the demo starts, and a change anywhere alters how many
console frames the run takes to reach a given count, so two builds sit at
different moments of the flight for the same counter value. Committed reaches
count 250 at console frame 4520 and a build differing only inside
`ground_normalise` reaches it at 4373. The gap between those two then reads as
1.64 over a fifty frame window, 0.37 over three hundred and fifty, and 0.23 over
seven hundred and fifty. None of those is a per-frame cost.

So only differences of about a console frame survive. Everything identified as
available is smaller: the index arithmetic inside the multiply is worth about
0.2, the build's indirect stores about 0.06, counting a loop in a register about
0.19. Five such changes were built and measured this session and all five came
back worse, which is what an unmeasurable difference looks like.

### What was measured and rejected

| | |
|---|---|
| dropping the two least-read tables and multiplying directly | 13.49 against 11.07, so a general multiply costs about five times a table lookup |
| a larger cache of built tables | 53.6% of frames reuse the previous frame's constant and 53.5% reuse one of the last thirty two, so there is nothing beyond the check already made |
| storing the table through an indexed address rather than a direct page pointer | 11.26 against 11.07 |
| counting the normalise doublings in a register | 11.30 against 11.07, with a byte-identical flight model and the same doubling count to within five |

## 38. An instrument fine enough to optimise against, and 15.7% off `$0a`

**252,778 processor cycles for one call to `ground_block`, from 299,896.** The
console reads that as 10.59 console frames per frame of the game's clock over
game frames 250 to 1000, from 11.07.

### Why the console could not be used

Section 37 recorded five changes that were strictly cheaper in instructions and
measured slower, and left it unexplained. The explanation is that no comparison
between two builds on the console means anything at this resolution. A change
alters how many console frames a frame of the game's clock takes, which alters
where the demo sits when the measuring window opens, which alters the scenery
and so the work. Measured across four windows, one such change reads 1.37 and
0.96 console frames **faster** in two of them and 0.23 and 0.16 slower in the
other two. The sign is a property of the window.

Widening the window to three thousand game frames does not fix it either: two
changes that each measure faster alone measure slower together.

### What replaced it

[`tools/cycles.py`](tools/cycles.py) runs one call of a named routine on the
processor model this project already checks its arithmetic with, over a snapshot
of the console's memory, and reports the cycles and instructions it took. Same
memory, same entry, same registers, no demo, no window.

Two things the snapshot has to have done to it, and both were found by getting
them wrong first. The fields saying which constants the multiply tables were
last built for must be made to match nothing, or the call skips the build and
measures half the routine. And the tables themselves must be cleared, or a build
whose entries are laid out differently reads the snapshot's as though they were
its own: that produced a three byte difference in the ground that looked like a
fault in the arithmetic and was a fault in the measurement.

### What it found

Every one of these was rejected on the console's evidence first.

| | cycles for one call | |
|---|---|---|
| before | 299,896 | |
| eight byte table entries | 273,610 | an entry's address is its number shifted three places, where five bytes made it a shift, a shift, a store, an addition and a load, twice per multiply |
| the doubling count in a register | included above | the direct page is the console's own memory, so an increment there is a read, a change and a write of the slow half |
| the table build storing to a named address | included above | rather than through a pointer in the direct page, which fetched three bytes from that same slow memory before each store |
| the product shifted in the accumulator | 267,274 | a shift in the direct page is a read, a change and a write |
| the high half never reaching memory | 260,170 | it stays in the accumulator through the sign correction, which now tests the sign with `bit` |
| one index for both matrix tables | 252,778 | four of the six multiplies are two scales against two constants, and the same entry number reaches into either table |

The ground every one of them computes is byte for byte the ground the original
computes, over ten frames with the tables blanked first.

### One fault it found that the demo cannot

The sign correction subtracts the constant, which is entry one's value. At five
bytes an entry that is at offset six; at eight bytes entry one begins at offset
eight, so the value is at offset nine and offset six is padding nothing writes.
The demo never produces a negative varying word, so nothing in the flight shows
it. It is a fault by construction rather than one that was observed, and the
only reason it was found is that the model can be run against blank memory where
the console's leftovers cannot cover for it.

### What it does not measure

Processor cycles, not console cycles. It does not know that the console's memory
answers more slowly than its cartridge, so a change trading a memory access for
an instruction reads better here than it runs. Every change above moves in the
same direction on both instruments, which is the check that matters; a change
where they disagree needs the console's verdict on a long window and a reason.

## 39. Under ten console frames a game frame

**9.94 console frames per frame of the game's clock**, from 11.07, which is 6.0
frames a second against the retail cartridge's 60. One call to `ground_block`
costs 303,276 processor cycles against 387,215 this morning, measured on the
model section 38 added.

### Where it went, and what was done about it

The split, on the model, with every multiply table rebuilt:

| | share at the start of this round |
|---|---|
| building the four multiply tables | 25% |
| the six multiplies a scanline | 25% |
| the two scales, which normalise and then shift | 16% |
| normalising | 9.5% |
| everything else, including the reciprocal and the loop | 24.5% |

Four changes, each measured on its own and kept only if the ground it computed
was byte for byte the ground the original computed:

**Sixteen table entries a turn.** Advancing the index and testing the loop were
a third of what an entry cost when they were paid once an entry. Where each of
the sixteen sits is known when the file is assembled, so they are paid once per
sixteen. The return falls away past that: thirty two and sixty four are worth
another 0.2% between them and cost twice and four times the code.

**The variable shift written out.** An arithmetic shift right by a count worked
out at the time was a loop of compare, rotate, count down and branch, ten cycles
a place. Written out once per place and entered part way down, a place costs
five and the count is spent once on the way in. Both scales a scanline come
through it, 352 times a frame.

**The normalise not storing as it goes.** It doubled a value while the sign
held, keeping the last one that fitted in memory so that it could be put back.
It does not need to: the bit a doubling pushes out stays in the carry, and a
rotate right puts it back in bit fifteen, so the doubling that overflowed is
undone rather than remembered. That takes a store out of every one of the 2,120
doublings a frame.

**The first of a paired multiply finished where it stands.** The two products
sharing an index were both parked in memory and shifted afterwards. The first is
finished before the second begins instead, because the index the second needs is
already in the index register and nothing between them disturbs it.

### What is left, and what it is not

| | cycles of the 303,276 |
|---|---|
| building the tables | about 78,000 |
| the multiplies | about 78,000 |
| everything else in a scanline | about 130,000 |

The build writes 4,096 bytes per rebuild and 2.9 of the four tables rebuild per
frame. That is irreducible without writing fewer bytes, and the entries are
already the narrowest that answer both halves of a multiply from one table. A
larger cache of built tables buys nothing, measured: 53.6% of frames reuse the
previous frame's constant and 53.5% reuse one of the last thirty two.

Two limits on the instrument are worth repeating. It counts processor cycles and
not console cycles, so it does not know the console's memory answers more slowly
than its cartridge. And it measures one call from one state. Every change above
moves the same way on both instruments, which is the check that matters.

## 40. Two lines closed by measurement rather than by argument

The multiply tables cost 76,337 cycles to build and 83,051 to read, per call to
`ground_block` with every table rebuilt. That is 151 cycles for each of the
1,056 multiplies a frame, counting the build.

**Would the console's own multiplier be cheaper?** No. `op_00_body`, this
project's exact signed sixteen by sixteen, measures **303 cycles** on the model
with the multiplier at `$4202` emulated. Twice the table's all-in cost, so the
tables stay, and the eight kilobytes of the console's memory they occupy are
paid for.

**Can the build's running sum live in registers?** No. Holding the low half in
the accumulator and the high half in the index register removes two direct page
reads and two writes an entry and costs a push and a pull, and a pull is five
cycles where the read it replaced was four: 304,602 against 303,276.

### What the shape of the remaining cost is

| | cycles of the 303,276 |
|---|---|
| the six multiplies a scanline | 83,051 |
| building the four tables | 76,337 |
| `ground_line`'s own glue | 61,709 |
| the two scales, less the normalise and shift inside them | 17,232 |
| the loop, the state searches and the prologue | 20,303 |
| normalising, three times a scanline | 19,548 |
| the variable shift | 16,600 |
| the reciprocal | 8,496 |

Every remaining idea against those is worth about one percent, and one of them
was measured as a gain and turned out to be an index advanced by 128 where eight
entries are 64 bytes, filling half the table. At that size the risk of a wrong
measurement is comparable to the gain, which is where this stops.
