; Pilotwings without the DSP-1: everything the conversion adds, in one place.
;
; The order below is the order the pieces depend on each other, and each file
; says what it is at its own top:
;
;   state02-map.asm     how big $02's three state tables are, built by
;                       state02build.py. Constants only, and first, because the
;                       assembler resolves a define where it reads it
;   dsp1-ops.asm        the commands whose arithmetic is known exactly
;   dsp1-answer.asm     the lookup, which is what a command reaches first
;   dsp1-fallback.asm   what answers when the lookup finds no row
;   dsp1-port.asm       the four stubs the game's own accesses are turned into
;   dsp1-ground.asm     $0a, the command that draws the ground. After the port,
;                       because it reads the port's own state
;   dsp1-hooks.asm      the flight model's accesses, which are three bytes each
;                       and so too small for a call to reach this bank
;   dsp1-thunks.asm     what those three byte calls land on, in the game's own
;                       bank, in a run measured to be unread
;   dsp1-window.asm     the bank the game's redirected accesses land in
;   dsp1-tables.asm     the four tables the chip's formulas rebuild
;   dsp1-derived.asm    the three tables taken from the chip itself
;   state02-data.asm    $02's three state tables, built by state02build.py
;   lut-map.asm         the recorded answers, built by lutbuild.py
;
; The last five are generated or placed at fixed banks by their own files, so
; only the code needs an origin here.
;
; The whole cartridge has to fit inside banks $00 to $7D, because $7E and $7F
; are the console's memory and everything from $80 up is a second view of what
; is already below. So: the game holds $00 to $0F and every byte of it, because
; 4 megabits is exactly sixteen banks. Nothing this project adds can sit in
; there, which is why the code starts at $10 rather than in the space that
; looked spare. Above it: the sine and cosine taken from the chip in $11 to $18,
; the recorded answers in $19 to $6F, $02's three state tables in $70 to $72, the
; reciprocal taken from the chip in $73, and the window the redirected accesses
; land in at $7D.

lorom

incsrc "../build/state02-map.asm"

org $108000
!PORTRAM = $7FDC00              ; measured free: the game never wrote $7FDB76
                                ; through $7FFBFF across a full run of the demo


incsrc "dsp1-ops.asm"
incsrc "dsp1-answer.asm"
incsrc "dsp1-fallback.asm"
incsrc "dsp1-port.asm"
incsrc "dsp1-ground.asm"
incsrc "dsp1-hooks.asm"
code_end:

incsrc "dsp1-tables.asm"
incsrc "dsp1-thunks.asm"
incsrc "dsp1-window.asm"
incsrc "dsp1-derived.asm"
incsrc "../build/state02-data.asm"
incsrc "../build/lut-map.asm"

print "code          ", dec(code_end-$108000), " bytes"
print "dsp1_answer at ", hex(dsp1_answer)
print "dsp1_lut at    ", hex(dsp1_lut)
print "state02_line at   ", hex(state02_line)
print "state02_scale at  ", hex(state02_scale)
print "state02_matrix at ", hex(state02_matrix)
print "ground_block at   ", hex(ground_block)
print "op_00 at       ", hex(op_00)
print "op_08 at       ", hex(op_08)
print "op_04 at       ", hex(op_04)
print "SYM dsp_write ", hex(dsp_write)
print "SYM dsp_read ", hex(dsp_read)
print "SYM dsp_status ", hex(dsp_status)
print "SYM dsp_ignore ", hex(dsp_ignore)
print "SYM dsp_port_reset ", hex(dsp_port_reset)
print "SYM dsp_stream ", hex(dsp_stream)
print "SYM dsp_route_10 ", hex(dsp_route_10)
print "SYM dsp_route_02 ", hex(dsp_route_02)
print "SYM dsp_route_0a ", hex(dsp_route_0a)
print "SYM thunk_sta ", hex(thunk_sta)
print "SYM thunk_lda ", hex(thunk_lda)
print "SYM thunk_sty ", hex(thunk_sty)
print "SYM thunk_stx ", hex(thunk_stx)
print "SYM thunk_stz ", hex(thunk_stz)
print "SYM thunk_ldy ", hex(thunk_ldy)
print "SYM thunk_ldx ", hex(thunk_ldx)
print "SYM thunk_ldy_status ", hex(thunk_ldy_status)
print "SYM thunk_ldx_status ", hex(thunk_ldx_status)
print "SYM thunk_adc ", hex(thunk_adc)
print "SYM dsp_read_adc ", hex(dsp_read_adc)
print "SYM dsp_read_eor ", hex(dsp_read_eor)
print "SYM thunk_bit_status ", hex(thunk_bit_status)
