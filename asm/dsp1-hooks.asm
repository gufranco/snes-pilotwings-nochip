; Pilotwings without the DSP-1: the accesses that are only three bytes wide.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; Sixteen more places reach the part the way $02, $0a and $10 do: the game sets
; the data bank and then uses three byte absolute instructions. Those three were
; each one run of code that talks to the part and then stops, so each was lifted
; out whole and answered in one call.
;
; This region cannot be. $00:CDB3 to $00:D4B0 is the flight model, and its 110
; accesses to the part are interleaved with the game's own arithmetic: it clamps,
; negates and accumulates between them. Replacing the region whole means
; rewriting how the plane flies.
;
; So each access is replaced where it stands. A three byte instruction has no
; room for a four byte call, but it has exactly enough for `jsr`, which is three
; bytes because it stays inside the bank it is called from:
;
;   sta $8000   ->   jsr thunk_sta
;   lda $8000   ->   jsr thunk_lda
;
; The catch is the bank. `jsr` reaches only the bank the code is in, which is the
; game's, and everything this project adds is in bank $10. So each hook is two
; pieces: a thunk in bank $00 that the `jsr` can reach, in asm/dsp1-thunks.asm,
; and the body here that the thunk calls across.
;
; ===========================================================================
; WHAT EACH SHAPE HAS TO PRESERVE
; ===========================================================================
;
; The instruction being replaced is the contract. Counted across the region
; rather than assumed:
;
;   52  sta $8000     sends the accumulator. Changes no register and no flag
;   22  sty $8000     sends Y, at the index width rather than the accumulator's
;   19  lda $8000     takes a word, setting negative and zero
;    6  adc $8000     takes a word and adds it, setting all four arithmetic flags
;    3  ldy $c000     takes the status into Y, setting negative and zero from Y
;    3  stx $8000     sends X
;    3  ldx $8000     takes into X
;    1  stz $8000     sends nought
;    1  ldy $8000     takes into Y
;
; Two of those are the ones to get right.
;
; The width of a send is the width of the register being sent, not of the
; accumulator. `sty` with an eight bit index sends one byte and `sta` with a
; sixteen bit accumulator sends two, and the port counts bytes, so reading the
; wrong flag desynchronises every argument after it and every answer with them.
;
; And `adc` is a read that also computes. It has to take the same number of bytes
; the original would, add them with the carry the caller arrived with, and leave
; negative, overflow, zero and carry as an add leaves them. Performing the add
; here rather than reproducing its flags is what makes that exact on every input.
;
; ===========================================================================
; HOW THE CALLER'S WIDTHS ARE READ
; ===========================================================================
;
; Not guessed: read back out of the stack. `php` pushes the caller's flags, and
; then everything below works at a known width, so the byte those flags landed on
; is at a fixed depth. With one `php` and one sixteen bit `pha` pushed, it is at
; $03,s.
;
; Bit $20 of that byte is the accumulator width and bit $10 is the index width,
; and in both cases set means eight bits.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   jsr / rts         Call and return inside one bank. Three bytes, which is the
;                     whole reason this file exists.
;   jsl / rtl         Call and return across banks. Four bytes.
;   php / plp         Push and pull the flags.
;   pha / pla         Push and pull the accumulator, one byte or two depending on
;                     the width it happens to be in.
;   lda $03,s         Read a byte at a known depth in the stack, used here to
;                     read back the flags a `php` pushed.
;   tya / txa         Move Y or X into the accumulator.
;   rep / sep         Make registers sixteen or eight bits wide.
;   and #$0010        Keep one bit and discard the rest, to test it.
; ===========================================================================

!HOOK_WORD = !PORTRAM+56        ; one word in transit, kept clear of !PORT_WORD
                                ; because dsp_write uses that one while these
                                ; hooks are inside it

; ---------------------------------------------------------------------------
; `sta $8000`, the commonest shape, needs nothing here.
;
; dsp_write already is it: the value in the accumulator, the width from the flags
; its own `php` pushes, and the accumulator and every flag given back untouched.
; The thunk for this shape calls it directly.
; ---------------------------------------------------------------------------

; ---------------------------------------------------------------------------
; `sty $8000`: send Y, at the index width.
;
; Out: nothing changed. A store alters no register and no flag, so the
; accumulator and the flags are both put back.
; ---------------------------------------------------------------------------
hook_sty:
    php
    rep #$30
    pha

    lda $03,s
    and #$0010                  ; the index width, set meaning eight bits
    beq .wide

    sep #$20                    ; so dsp_write sends one byte
    tya
    jsl dsp_write
    rep #$30
    bra .done

.wide:
    tya                         ; a whole word of it
    jsl dsp_write

.done:
    pla
    plp
    rtl

; ---------------------------------------------------------------------------
; `stx $8000`: the same, for X.
; ---------------------------------------------------------------------------
hook_stx:
    php
    rep #$30
    pha

    lda $03,s
    and #$0010
    beq .wide

    sep #$20
    txa
    jsl dsp_write
    rep #$30
    bra .done

.wide:
    txa
    jsl dsp_write

.done:
    pla
    plp
    rtl

; ---------------------------------------------------------------------------
; `stz $8000`: send nought, at the accumulator width, and change nothing.
; ---------------------------------------------------------------------------
hook_stz:
    php
    rep #$30
    pha

    lda $03,s
    and #$0020                  ; the accumulator width this time
    beq .wide

    sep #$20
    lda #$00
    jsl dsp_write
    rep #$30
    bra .done

.wide:
    lda #$0000
    jsl dsp_write

.done:
    pla
    plp
    rtl

; ---------------------------------------------------------------------------
; `lda $8000`, the plain read, needs nothing here either.
;
; dsp_read already is it: the next word of the answer, at the caller's
; accumulator width, loaded last so that negative and zero come from it.
; ---------------------------------------------------------------------------

; ---------------------------------------------------------------------------
; `ldy $8000` and `ldx $8000`: take the next word into an index register.
;
; Neither index register has a long addressing mode, so the value cannot be
; loaded from the port's own memory in bank $7f the way the accumulator loads it.
; It goes through the stack instead: pushed at sixteen bits and pulled straight
; back into the register.
;
; What that costs is the flags. A real `ldx` sets negative and zero from what it
; loaded and this leaves the caller's own, because the flags are restored after
; the pull rather than before it.
;
; That is a deliberate difference and it is measured rather than hoped for. All
; four of these in the region are followed by a store or by an `adc`, and the
; next instruction to read negative or zero always comes after one that writes
; them, so nothing can observe the difference. It is a property of the code
; rather than of any recording, so no argument set can change it, and
; `patch.retail.test.py` checks it instruction by instruction rather than leaving
; it as a claim in a comment.
;
; The carry is untouched, which the `adc` after the `ldy` at $00:D27A depends on.
;
; Restoring the flags is also what narrows the register: putting the index width
; back to eight bits clears the high byte, leaving exactly the byte a real load
; would have taken.
; ---------------------------------------------------------------------------
hook_ldy:
    php
    rep #$30
    pha

    lda $03,s
    and #$0010
    beq .wide

    sep #$20                    ; eight bit index takes one byte of the answer
    jsl dsp_read
    rep #$30
    and #$00FF
    bra .done

.wide:
    jsl dsp_read

.done:
    pha
    ply                         ; through the stack, for want of a long load
    pla
    plp
    rtl

hook_ldx:
    php
    rep #$30
    pha

    lda $03,s
    and #$0010
    beq .wide

    sep #$20
    jsl dsp_read
    rep #$30
    and #$00FF
    bra .done

.wide:
    jsl dsp_read

.done:
    pha
    plx
    pla
    plp
    rtl

; ---------------------------------------------------------------------------
; `ldy $c000`: take the status into Y.
;
; This one does need its flags. All three of these are a poll: the instruction
; after each is a `bpl` back to it, so the sign of what lands in Y is what ends
; the wait, and a wrong sign is a game that stops.
;
; So the load is the last thing that happens, after the caller's flags are back,
; and it is an immediate rather than a fetch. The status answered one value on
; every one of the 2,867,736 reads the recordings hold, so there is nothing to
; fetch: both halves of it are the ready byte, for the reason !STATUS_READY
; gives, and either width has its top bit set.
; ---------------------------------------------------------------------------
hook_ldy_status:
    php
    rep #$30
    pha

    lda $03,s
    and #$0010
    beq .wide

    pla
    plp
    ldy.b #$80                  ; eight bit index sees the ready byte alone
    rtl

.wide:
    pla
    plp
    ldy.w #!STATUS_READY        ; sixteen bit sees both halves of it
    rtl

; ---------------------------------------------------------------------------
; `adc $8000`: take the next word and add it.
;
; The add happens here rather than having its flags reproduced. That is the whole
; reason this shape has a hook of its own: an add sets negative, overflow, zero
; and carry together, and the only thing that gets all four right on every input
; is an add.
;
; The accumulator is pushed and pulled at the caller's own width, so the same
; number of bytes come back off the stack as went on, and the carry the caller
; arrived with is restored by the `plp` immediately before the add.
; ---------------------------------------------------------------------------
hook_adc:
    php                         ; the caller's flags, the carry among them
    pha                         ; and the value being added to

    jsl dsp_read                ; the next word, at the caller's width
    sta.l !HOOK_WORD

    pla
    plp
    adc.l !HOOK_WORD
    rtl
