; Pilotwings without the DSP-1: what answers when the table has no row.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; Every command the cartridge sends has a route here, and every route answers.
; None of them loops, none of them can fail, and none of them reads memory it
; has not set. That is the whole requirement: a lookup with no row must not stop
; the machine.
;
; It is reached only on a miss, and a miss means the game asked something no
; recording ever showed it asking. On the recordings there are none. On a player
; doing something the recordings never did, there will be.
;
; ===========================================================================
; TWO KINDS OF FALLBACK
; ===========================================================================
;
; Three commands have their arithmetic. It was read out of the chip's own
; program and then checked against the chip on four hundred random argument
; sets each, drawn from the whole sixteen bit range. For these, falling back
; costs accuracy nothing:
;
;   $00, $80   op_00, the signed fractional product
;   $08        op_08, twice the sum of three squares
;   $04        op_04, a magnitude turned through an angle
;
; The other thirteen take the nearest row instead. The search that just failed
; left !LOW at the first row whose key is above the one wanted, so the row
; before it and the row at it are the two nearest, and the closer wins.
;
; Why the nearest row rather than the arithmetic. These arguments are an
; aircraft's attitude and position sampled every frame, so neighbouring keys
; carry neighbouring answers and the nearest row is a near miss. The arithmetic
; for these thirteen has been read as far as its shape and not as far as its
; rounding, and a recomputation that is wrong in the rounding is wrong on every
; input, where the nearest row is only wrong between samples. Guessing at
; rounding is also how three separate faults got into $00 and $08 before they
; were caught.
;
; When a command's arithmetic is read to the bit, its line here changes from a
; nearest-row branch to a call, and the accuracy of that command stops depending
; on what the recordings happened to cover.
;
; ===========================================================================
; WHAT NEAREST MEANS HERE
; ===========================================================================
;
; The distance between two keys is taken on the first word alone. Keys are
; sorted on the whole key, so rows adjacent in the table already agree on
; everything before the word they differ in, and the first word is where the
; difference is largest. Comparing every word would cost a multiply per row and
; change the choice almost never.
;
; At the ends of the table there is only one neighbour and the comparison is
; skipped rather than reaching past the edge.
; ===========================================================================

; ---------------------------------------------------------------------------
; The fallback, entered with !CMD set and the search's !LOW left behind it.
; ---------------------------------------------------------------------------
dsp1_fallback:
    php
    rep #$30

    lda !CMD
    cmp #$0000
    beq .product                ; $00
    cmp #$0080
    beq .product                ; $80 reaches the same routine in the chip
    cmp #$0008
    beq .squares
    cmp #$0004
    beq .turned
    cmp #$000A
    beq .stream

    ; Everything else takes the nearest row it can reach.
    bra .nearest

.product:
    jsl op_00
    plp
    rtl

.squares:
    jsl op_08
    plp
    rtl

.turned:
    jsl op_04
    plp
    rtl

; ---------------------------------------------------------------------------
; The nearest row, when there is no exact one.
;
; !LOW is where the wanted key would have gone. The row at !LOW is the first one
; above it and the row at !LOW minus one is the last one below. Both are read,
; both distances are taken on the first word, and the smaller wins.
; ---------------------------------------------------------------------------
.nearest:
    lda !LOW                    ; is there a row below at all? !LOW is thirty
    ora !LOW+2                  ; two bits, because $06 has more rows than
    bne .has_below              ; sixteen bits hold

    stz !MID                    ; nothing below: the first row is the answer
    stz !MID+2
    bra .take

.has_below:
    lda !LOW+2                  ; is there a row above? the same comparison the
    cmp !ROWS+2                 ; search uses, high halves first
    bcc .between
    bne .at_end
    lda !LOW
    cmp !ROWS
    bcc .between

.at_end:
    lda !LOW                    ; nothing above: the last row is the answer
    sec
    sbc #$0001
    sta !MID
    lda !LOW+2
    sbc #$0000
    sta !MID+2
    bra .take

.between:
    lda !LOW                    ; measure the row above, which is the row !LOW
    sta !MID                    ; itself names
    lda !LOW+2
    sta !MID+2
    jsr fallback_distance
    sta !SCRATCH+20             ; kept clear of everything lut_key_at uses

    lda !LOW                    ; then the row below, one place back
    sec
    sbc #$0001
    sta !MID
    lda !LOW+2
    sbc #$0000
    sta !MID+2
    jsr fallback_distance

    cmp !SCRATCH+20
    bcc .take                   ; the row below is closer, and !MID is on it

    lda !LOW                    ; the row above is closer
    sta !MID
    lda !LOW+2
    sta !MID+2

.take:
    jsl lut_answer
    plp
    rtl

; ---------------------------------------------------------------------------
; $0a, which has no row and cannot be given one, so it is computed.
;
; This command answers 764 words. Keyed on its own argument its answer is not a
; function of the key at all, and keyed on its argument plus $02's it is one
; exactly, with no ambiguity in any of the three recordings. It is still not
; storable: the recordings hold better than five thousand distinct answers each,
; every one of the 764 positions differs between at least two of them, and the
; European recording alone would take 8.7 megabytes against 3.9 for the whole
; cartridge. So lutbuild.py leaves it out and it arrives here every time.
;
; It used to answer nought here, which is why the demo flew over nothing.
; asm/dsp1-ground.asm now carries its arithmetic, read out of the chip's own
; program and checked against the chip on 43,440 answer words.
;
; Only four words are written rather than 764, because the port serves this
; command a word at a time from the same four. So this answers the one scanline
; the argument names, and the demo does not come this way at all: dsp_width says
; $0a answers nothing, so the port never reaches the lookup for it and
; ground_block serves every scanline the game actually reads.
;
; Nothing here can loop: one scanline, and every loop inside it is bounded by a
; sixteen bit shift count.
; ---------------------------------------------------------------------------
.stream:
    jsl ground_answer
    plp
    rtl

; ---------------------------------------------------------------------------
; How far the row in !MID is from the wanted key, on the first word.
;
; Reads the row's first key word through the same address arithmetic the search
; uses, subtracts the wanted one, and drops the sign, because what is wanted is
; a distance and not a direction.
;
; Out: A the distance. Everything from !SCRATCH to !SCRATCH+15 is used up by the
; address arithmetic, which is why the caller parks its running best further on.
; ---------------------------------------------------------------------------
fallback_distance:
    jsr lut_key_at
    ldy #$0000
    lda [!SCRATCH],y

    sec
    sbc !ARG
    bpl +
    eor #$FFFF                  ; below the wanted key: negate, so that the
    inc a                       ; comparison afterwards is on size alone
+
    rts
