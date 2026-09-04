; Pilotwings without the DSP-1: the nine landings in the game's own bank.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; asm/dsp1-hooks.asm explains why the flight model's accesses have to be
; replaced one at a time and why `jsr` is the only call that fits in three
; bytes. `jsr` reaches only the bank the code is running in, which is the game's
; own, so it cannot reach bank $10 where everything else here lives.
;
; These nine are what it reaches instead. Each is a call across to the body and
; a return, five bytes, and there is nothing else they could usefully do: a
; longer thunk here would be code sitting in the game's bank for no reason.
;
; ===========================================================================
; WHERE THEY SIT, AND HOW THAT WAS SETTLED RATHER THAN CHOSEN
; ===========================================================================
;
; $00:AD28 begins a run of 322 bytes that the retail image fills with $ff.
;
; A run of one repeated byte is not proof that nothing reads it. It was measured
; the way !PORTRAM was measured: 1,631 bytes across the fourteen such runs in
; this bank were overwritten with a marker, the demo was run for 1,800 console
; frames, and the console's whole 128 KiB of memory came out byte for byte
; identical to the unmodified build at every frame sampled. Nothing on this path
; reads any of them.
;
; Forty five bytes are used of the 322, so the rest stays as it was.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   org $00AD28   Put what follows at that address in the image.
;   jsl label     Call across banks. Four bytes.
;   rts           Return to whoever called with `jsr`. One byte.
;
; The pairing matters and it balances: the game's `jsr` pushes two bytes, the
; `jsl` here pushes three and its `rtl` takes those three back, and the `rts`
; takes the two. Nothing is left behind on the stack.
; ===========================================================================

org $00AD28

thunk_sta:
    jsl dsp_write               ; the accumulator, at the accumulator's width
    rts

thunk_lda:
    jsl dsp_read                ; the next word, at the accumulator's width
    rts

thunk_sty:
    jsl hook_sty
    rts

thunk_stx:
    jsl hook_stx
    rts

thunk_stz:
    jsl hook_stz
    rts

thunk_ldy:
    jsl hook_ldy
    rts

thunk_ldx:
    jsl hook_ldx
    rts

thunk_ldy_status:
    jsl hook_ldy_status
    rts

thunk_ldx_status:
    jsl hook_ldx_status
    rts

thunk_adc:
    jsl dsp_read_adc
    rts

thunk_bit_status:
    jsl hook_bit_status
    rts

thunk_sbc:
    jsl dsp_read_sbc
    rts

; The eight above reach the part. These reach the game's own memory, which the
; redirect moved along with it. asm/dsp1-hooks.asm says why.

thunk_adc_0130:
    jsl hook_adc_0130
    rts

thunk_sta_0130:
    jsl hook_sta_0130
    rts

thunk_lda_1800y:
    jsl hook_lda_1800y
    rts

thunk_lda_1808y:
    jsl hook_lda_1808y
    rts

thunk_lda_1810x:
    jsl hook_lda_1810x
    rts

thunk_lda_1812x:
    jsl hook_lda_1812x
    rts

thunk_lda_1814x:
    jsl hook_lda_1814x
    rts

; And the twenty in the four blocks beyond the flight model, which read the
; same tables and never write them.

thunk_lda_1aea:
    jsl hook_lda_1aea
    rts

thunk_lda_1848:
    jsl hook_lda_1848
    rts

thunk_lda_185a:
    jsl hook_lda_185a
    rts

thunk_lda_1858:
    jsl hook_lda_1858
    rts

thunk_lda_1828:
    jsl hook_lda_1828
    rts

thunk_lda_182a:
    jsl hook_lda_182a
    rts

thunk_lda_182c:
    jsl hook_lda_182c
    rts

thunk_lda_182e:
    jsl hook_lda_182e
    rts

thunk_cmp_182c:
    jsl hook_cmp_182c
    rts

thunk_cmp_182e:
    jsl hook_cmp_182e
    rts

thunk_lda_1820x:
    jsl hook_lda_1820x
    rts

thunk_lda_1828x:
    jsl hook_lda_1828x
    rts

thunk_lda_1840x:
    jsl hook_lda_1840x
    rts

thunk_lda_1860x:
    jsl hook_lda_1860x
    rts

thunk_lda_1ac3:
    jsl hook_lda_1ac3
    rts

thunk_lda_1870:
    jsl hook_lda_1870
    rts

thunk_lda_1876:
    jsl hook_lda_1876
    rts

thunk_ldx_1af9:
    jsl hook_ldx_1af9
    rts

print "thunks end at ", hex(thunk_ldx_1af9+5), ", the run they sit in ends at $00AE6A"
