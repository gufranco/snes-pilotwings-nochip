; Pilotwings without the DSP-1: everything the conversion adds, in one place.
;
; The order below is the order the pieces depend on each other, and each file
; says what it is at its own top:
;
;   dsp1-ops.asm        the commands whose arithmetic is known exactly
;   dsp1-answer.asm     the lookup, which is what a command reaches first
;   dsp1-fallback.asm   what answers when the lookup finds no row
;   dsp1-port.asm       the four stubs the game's own accesses are turned into
;   dsp1-tables.asm     the four tables the chip's formulas rebuild
;   dsp1-derived.asm    the three tables taken from the chip itself
;   lut-map.asm         the recorded answers, built by lutbuild.py
;
; The last three are generated or placed at fixed banks by their own files, so
; only the code needs an origin here.
;
; The whole cartridge has to fit inside banks $00 to $7D, because $7E and $7F
; are the console's memory and everything from $80 up is a second view of what
; is already below. So: the game holds $00 to $0F and every byte of it, because
; 4 megabits is exactly sixteen banks. Nothing this project adds can sit in
; there, which is why the code starts at $10 rather than in the space that
; looked spare. Above it: the answers in $11 to $6D, and the tables taken from
; the chip in $6E to $79.

lorom

org $108000
!PORTRAM = $7FDC00              ; measured free: the game never wrote $7FDB76
                                ; through $7FFBFF across a full run of the demo

incsrc "dsp1-ops.asm"
incsrc "dsp1-answer.asm"
incsrc "dsp1-fallback.asm"
incsrc "dsp1-port.asm"
code_end:

incsrc "dsp1-tables.asm"
incsrc "dsp1-derived.asm"
incsrc "../build/lut-map.asm"

print "code          ", dec(code_end-$108000), " bytes"
print "dsp1_answer at ", hex(dsp1_answer)
print "dsp1_lut at    ", hex(dsp1_lut)
print "op_00 at       ", hex(op_00)
print "op_08 at       ", hex(op_08)
print "op_04 at       ", hex(op_04)
print "SYM dsp_write ", hex(dsp_write)
print "SYM dsp_read ", hex(dsp_read)
print "SYM dsp_status ", hex(dsp_status)
print "SYM dsp_ignore ", hex(dsp_ignore)
print "SYM dsp_port_reset ", hex(dsp_port_reset)
print "SYM dsp_stream ", hex(dsp_stream)
