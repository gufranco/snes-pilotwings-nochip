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
;   reciprocal.bin   131,072 bytes   the mantissa $10 answers, one per input
;   sine.bin         131,072 bytes   what $04 multiplies a magnitude by
;   cosine.bin       131,072 bytes   the same, for the other half
;
; Each is 65,536 entries of two bytes, one for every value a sixteen bit word
; can hold, so no input can miss and the fallback behind them is unreachable.
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

; What $10 answers as its mantissa, for every input it can be given. The
; exponent is not here: it is a count of leading zeros less the second
; argument, which is a handful of instructions and would be a wasteful table.
org $6D8000
dsp1_reciprocal_of:
incbin "../build/reciprocal-0.bin"
org $6E8000
incbin "../build/reciprocal-1.bin"
org $6F8000
incbin "../build/reciprocal-2.bin"
org $708000
incbin "../build/reciprocal-3.bin"

; What $04 multiplies a magnitude by, per angle, for the first half it answers.
; A whole turn is 65,536, so the index is the angle with nothing done to it.
org $718000
dsp1_sine_of:
incbin "../build/sine-0.bin"
org $728000
incbin "../build/sine-1.bin"
org $738000
incbin "../build/sine-2.bin"
org $748000
incbin "../build/sine-3.bin"

; The same, for the second half.
org $758000
dsp1_cosine_of:
incbin "../build/cosine-0.bin"
org $768000
incbin "../build/cosine-1.bin"
org $778000
incbin "../build/cosine-2.bin"
org $788000
incbin "../build/cosine-3.bin"

print "reciprocal of starts at ", hex(dsp1_reciprocal_of)
print "sine of starts at       ", hex(dsp1_sine_of)
print "cosine of starts at     ", hex(dsp1_cosine_of)
