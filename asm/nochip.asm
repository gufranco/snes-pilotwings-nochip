; Pilotwings without the DSP-1: everything the conversion adds, in one place.
;
; The order below is the order the pieces depend on each other, and each file
; says what it is at its own top:
;
;   dsp1-ops.asm        the commands whose arithmetic is known exactly
;   dsp1-answer.asm     the lookup, which is what a command reaches first
;   dsp1-fallback.asm   what answers when the lookup finds no row
;   dsp1-tables.asm     the four tables the chip's formulas rebuild
;   dsp1-derived.asm    the three tables taken from the chip itself
;   lut-map.asm         the recorded answers, built by lutbuild.py
;
; The last three are generated or placed at fixed banks by their own files, so
; only the code needs an origin here.
;
; The whole cartridge has to fit inside banks $00 to $7D, because $7E and $7F
; are the console's memory and everything from $80 up is a second view of what
; is already below. So: the game holds $00 to $0F, the recorded answers hold
; $10 to $6C, and the tables taken from the chip hold $6D to $78. The code goes
; in bank $0F, in the space above the game's own 4 megabits.

lorom

org $0F8000
incsrc "dsp1-ops.asm"
incsrc "dsp1-answer.asm"
incsrc "dsp1-fallback.asm"
code_end:

incsrc "dsp1-tables.asm"
incsrc "dsp1-derived.asm"
incsrc "../build/lut-map.asm"

print "code          ", dec(code_end-$0F8000), " bytes"
print "dsp1_answer at ", hex(dsp1_answer)
print "dsp1_lut at    ", hex(dsp1_lut)
print "op_00 at       ", hex(op_00)
print "op_08 at       ", hex(op_08)
print "op_04 at       ", hex(op_04)
