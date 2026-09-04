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

thunk_adc:
    jsl hook_adc
    rts

print "thunks end at ", hex(thunk_adc+5), ", the run they sit in ends at $00AD6A"
