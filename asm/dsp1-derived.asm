; Pilotwings without the DSP-1: the tables that come from the chip, not a formula.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; dsp1-tables.asm rebuilds four tables from their formulas, because those four
; are formulas: a reciprocal, a sine, a cosine and an arccosine, each matching
; its expression entry for entry with nothing forgiven.
;
; These three are not formulas. They are what the chip answers *after* it has
; interpolated between those four and refined the result, with clamps whose
; rounding nobody here has measured. A routine that recomputes them is a routine
; that is nearly right, and nearly right is how the ground ends up in the wrong
; place. So they are taken from the chip itself:
;
;   reciprocal-0.bin  32,768 bytes   the mantissa $00d3 answers, per normalised input
;   sine.bin         131,072 bytes   what $04 multiplies a magnitude by
;   cosine.bin       131,072 bytes   the same, for the other half
;
; The two trig tables are 65,536 entries of two bytes, one for every value a
; sixteen bit word can hold. The reciprocal is 16,384, because that is the whole
; range its caller can hand it: the chip's own normalise loop always leaves a
; magnitude between $4000 and $7fff. Either way no input can miss and the routine
; behind them is unreachable.
;
; ===========================================================================
; WHERE THEY COME FROM, AND WHY THAT IS NOT A COMPILED ARTEFACT
; ===========================================================================
;
; derived.py drives the chip across the whole input range and writes what it
; says. It runs on the machine of whoever is building, against the chip they
; already have, into the build directory, which is ignored. Nothing here is
; committed and nothing here can be, because it is the chip's own behaviour.
;
; That is the same arrangement the four formula tables have. There the formula
; stands in for the chip; here the chip stands in for a formula nobody can
; write. Both are computed at build time and neither is pasted in.
;
; To produce them:
;
;     SNES_DSP_FIRMWARE_DIR=firmware python3 derived.py dsp1 build
;
; The mask is named rather than defaulted. This cartridge wants the DSP-1, and
; building these from the DSP-1B would put the corrected arithmetic in, which is
; the arithmetic that crashes the demo's plane.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   incbin "path"   Place the whole of that file here, byte for byte. It is the
;                   only instruction in this file, and it produces no code: the
;                   bytes simply become part of the ROM at this point.
;
;   label:          A name for the address the next thing lands at. Code
;                   elsewhere writes dsp1_reciprocal_of and never has to know
;                   the number.
;
;   print           Prints a line while building, so the size shows in the log
;                   rather than being discovered later.
;
; An entry is found by doubling the input and adding it to the label, because
; each entry is two bytes. That is one shift and one add, which is why these
; are tables rather than searches.
; ===========================================================================

; ===========================================================================
; WHY EACH TABLE IS IN FOUR PIECES
; ===========================================================================
;
; A low-addressed bank reaches $8000 to $FFFF, which is 32,768 bytes, or 16,384
; entries. A whole table is 131,072 bytes, so it does not fit in one and the
; assembler refuses outright to lay a run of bytes across a bank border.
;
; So each table is four pieces in four consecutive banks, and a lookup picks the
; piece from the top two bits of the index. derived.py writes the pieces already
; cut, numbered from zero.
; ===========================================================================

; What $10 answers as its mantissa used to sit here, one entry for every input,
; four banks of it. Nothing ever read it: $10 is answered from the recorded
; table, which covers every key the game was seen to ask for and costs a
; thousandth of the space. Those four banks are the recorded table's now, which
; is what lets it carry the commands that draw the ground rather than only the
; three it had room for.
;
; What sits here instead is one bank rather than four, and a different question.
; $0a asks the chip's own routine at $00d3 for a reciprocal, and it only ever
; asks about a value that has just come out of the normalise loop at $003a, which
; leaves a magnitude between $4000 and $7fff. That is 16,384 entries, which is
; exactly one bank, and the bound comes from reading the loop rather than from
; watching what a recording asked for, so the table is complete by construction.
;
; The sign is not stored. $00d3 strips it at $0d6, refines the magnitude, and
; negates the answer at $0f0, so one half of the range answers both halves and
; asm/dsp1-ground.asm puts the sign back in two instructions.
org $F38000
dsp1_reciprocal_of:
incbin "../build/reciprocal-0.bin"

; The same behaviour, asked a different question, which is what removed the
; dearest loop in the ground.
;
; The table above is keyed on the magnitude the normalise loop *left*, so reading
; it meant running that loop first: doubling a word until its sign would change,
; twelve cycles a doubling, about ten doublings a scanline. It was 11% of one
; call and more than any single multiply.
;
; The magnitude a value normalises to is a function of the value, so the mantissa
; is too. These three are keyed on the value itself, and the loop is gone.
;
; Keyed on the *folded* value: a negative word is complemented first, because a
; word and its complement have the same run of leading sign bits and so the same
; doubling count. That halves the length. The two signs still need separate
; mantissas, because a negative value folds to one less than its own magnitude
; and so lands one step further up the table, and its answer comes back negated.
;
; The exponent is the doubling count less six and depends on the folded form
; alone, so one table serves both signs. Entry nought of the upward table holds
; the part's own answer for a distance of exactly nought, which is a scanline on
; the horizon, so that case needs no branch either.
;
; derived.py writes all three from the table above with no part driven, since
; turning a table inside out is arithmetic.
org $F58000
dsp1_recip_up:
incbin "../build/recip-up-0.bin"
org $F68000
dsp1_recip_up_high:
incbin "../build/recip-up-1.bin"

org $F78000
dsp1_recip_down:
incbin "../build/recip-down-0.bin"
org $F88000
dsp1_recip_down_high:
incbin "../build/recip-down-1.bin"

org $F98000
dsp1_recip_exponent:
incbin "../build/recip-exponent-0.bin"
org $FA8000
dsp1_recip_exponent_high:
incbin "../build/recip-exponent-1.bin"

; What $04 multiplies a magnitude by, per angle, for the first half it answers.
; A whole turn is 65,536, so the index is the angle with nothing done to it.
org $918000
dsp1_sine_of:
incbin "../build/sine-0.bin"
org $928000
incbin "../build/sine-1.bin"
org $938000
incbin "../build/sine-2.bin"
org $948000
incbin "../build/sine-3.bin"

; The same, for the second half.
org $958000
dsp1_cosine_of:
incbin "../build/cosine-0.bin"
org $968000
incbin "../build/cosine-1.bin"
org $978000
incbin "../build/cosine-2.bin"
org $988000
incbin "../build/cosine-3.bin"

; The value $02 derives its horizon and its second scale from, one entry per
; angle, driven out of the part by state02build.py.
;
; It is the cosine of the angle for most of the turn and something else near and
; past a quarter turn, where the part holds it at a floor. What that floor is has
; not been read out of the part's program, and it does not need to be: the value
; is a function of the angle alone, so every angle a word can hold is asked for
; and the answer cannot miss.
;
; Three of the ten words $0a reads come out of this: the horizon is this times
; argument 4 shifted down fifteen places, and the second mantissa and exponent
; are the normalise and the reciprocal of it. They were looked up in a table
; recorded from playthroughs before, which missed on 3%, 21% and 3% of the
; demo's own frames.
;
; Four banks, and the two pairs are not next to each other because the window the
; redirected accesses land in sits between them. The reader adds one to the bank
; for the upper half, which is what steps over it.
org $FB8000
dsp1_clamped_cosine:
incbin "../build/state02-clamped-0.bin"
org $FC8000
incbin "../build/state02-clamped-1.bin"
org $FE8000
incbin "../build/state02-clamped-2.bin"
org $FF8000
incbin "../build/state02-clamped-3.bin"

print "reciprocal of starts at ", hex(dsp1_reciprocal_of)
print "clamped cosine starts at", hex(dsp1_clamped_cosine)
print "recip up starts at      ", hex(dsp1_recip_up)
print "recip down starts at    ", hex(dsp1_recip_down)
print "recip exponent starts at", hex(dsp1_recip_exponent)
print "sine of starts at       ", hex(dsp1_sine_of)
print "cosine of starts at     ", hex(dsp1_cosine_of)
