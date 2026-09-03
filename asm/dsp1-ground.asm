; Pilotwings without the DSP-1: $0a, the command that draws the ground.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; $0a is 78% of everything the cartridge ever asked the part, and until now it
; answered nought, which is why the demo flew over nothing. It cannot be looked
; up: it answers 764 words, the three recordings hold better than five thousand
; distinct answers each, and every one of the 764 positions differs between at
; least two of them, so the European recording alone would take 8.7 megabytes
; against 3.9 for the whole cartridge.
;
; So it is computed. Per scanline: one multiply for the distance, one normalise,
; one table read for the reciprocal, one multiply and one shift for each of two
; scales, and four multiplies for the four words it answers with.
;
; Every stage below was read out of the part's own program and then checked
; against the part stage by stage, on 60 argument sets drawn from all three
; recordings: 43,440 answer words, all of them exact, against the part and
; against the recordings both.
;
; ===========================================================================
; THE CHAIN, WITH THE PART'S OWN ADDRESSES
; ===========================================================================
;
; The part's loop runs from $364 to $390 and calls two subroutines. What each
; stage does, and where it lives inside the part:
;
;   $366  distance    (step * line) >> 15, plus the horizon. `step`, the
;                     horizon and everything else come from $02
;   $36a  normalise   $003a: double while the top two bits agree, and keep the
;                     last value that fitted. The count of doublings matters
;   $36b  reciprocal  $00d3: a mantissa, and an exponent that is the doubling
;                     count less six
;   $36d  first pair  mantissa = (first mantissa from $02 * reciprocal) >> 15
;                     exponent = reciprocal exponent + first exponent from $02
;   $371  first scale $0077: normalise again, then shift right by fifteen less
;                     the exponent, or saturate
;   $377  second pair mantissa = (second mantissa from $02 * the first
;                     mantissa, before its shift) >> 15
;                     exponent = the first exponent plus the second from $02
;   $37a  second scale the same $0077
;   $382  the answer  four words: the first scale against two matrix words and
;                     the second against the other two
;
; Two details cost several days each before they were read rather than guessed.
;
; The second scale is a cascade, not a parallel branch. It multiplies the first
; chain's mantissa *before* that mantissa was shifted, which is why every
; attempt to recover it from the answers found the exponent moving with the
; first scale's rather than with the distance.
;
; And an answer word is not a scale. It is the scale multiplied by a matrix
; word and shifted, and with a matrix word of $7fff that is one less than the
; scale, which quietly voided three separate measurements.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   lda / sta         Load the accumulator, store the accumulator.
;   lda [!X],y        Read through a three byte pointer held at !X, y bytes in.
;   clc / sec         Clear or set the carry, which add and subtract need.
;   adc / sbc         Add or subtract, using the carry.
;   asl a             Double the accumulator. The carry takes the bit pushed out.
;   ror a             Rotate right through the carry.
;   lsr               Halve, shifting the low bit into the carry.
;   eor #$FFFF / inc  Flip every bit then add one, which is a negation.
;   bcc / bcs         Branch on the carry being clear or set.
;   bpl / bmi         Branch on the last result being positive or negative.
;   beq / bne         Branch on the last result being zero or not.
;   jsr / rts         Call and return inside one bank.
;   jsl / rtl         Call and return across banks.
;   php / plp         Save and restore the flags.
;   rep #$30          Make the accumulator and both index registers sixteen bits.
;   -  and  +         Anonymous labels: `bne -` jumps back, `bcc +` forwards.
;
; An arithmetic shift right by one is written `cmp #$8000 : ror a`. The compare
; puts bit fifteen into the carry and the rotate brings it straight back into
; bit fifteen, so the sign is preserved. The processor has no instruction for it.
; ===========================================================================

; ---------------------------------------------------------------------------
; The working variables, in the same direct page dsp1-answer.asm uses.
;
; That page is at $0D00 and the lookup owns $00 to $61 of it, so everything
; here starts at $62. The two never run at the same time, but sharing bytes
; with them would still be a fault waiting for the first time one calls the
; other, which the fallback does.
;
; $0D62 through $0DAF is inside the run the game was measured never to write,
; $000CFC to $000FE3, which is the same measurement !PAGE itself rests on.
; ---------------------------------------------------------------------------
!G_STEP    = $62                ; how far the distance moves per scanline
!G_HORIZON = $64                ; where the ground meets the sky
!G_MAN1    = $66                ; the first scale's mantissa, from $02
!G_EXP1    = $68                ; and its exponent
!G_MAN2    = $6A                ; the second scale's mantissa
!G_EXP2    = $6C                ; and its exponent
!G_MAT     = $6E                ; the four matrix words, $6E to $74

!G_LINE    = $76                ; which scanline is being answered
!G_NORM    = $78                ; what the normalise loop left
!G_COUNT   = $7A                ; and how many doublings it took
!G_RA      = $7C                ; the reciprocal's mantissa
!G_RB      = $7E                ; and its exponent
!G_MA      = $80                ; the first chain's mantissa before its shift
!G_EXP     = $82                ; the exponent the scale about to run will use
!G_S1      = $84                ; the two scales for this scanline
!G_S2      = $86
!G_OUT     = $88                ; the four words this scanline answers, $88 to $8E
!G_NEG     = $90                ; whether the reciprocal's sign has to go back
!G_AT      = $92                ; how far into the two buffers the loop has got
!G_TURNS   = $94                ; how many scanlines are left

; The search's own variables. A row index fits in sixteen bits because the
; largest of the three tables has 3,302 rows, and a row offset fits too because
; the largest table is 30,330 bytes and every one of them starts at $8000.
!G_KEY     = $96                ; the key wanted, up to two words
!G_BASE    = $9A                ; where the table starts, as a long address
!G_STRIDE  = $9E                ; how many bytes one row takes
!G_KEYS    = $A0                ; how many words of that row are the key
!G_ROWS    = $A2                ; how many rows the table holds
!G_LOW     = $A4                ; the search's low bound
!G_HIGH    = $A6                ; and its high bound
!G_MID     = $A8                ; the row being compared
!G_ROW     = $AA                ; where that row is, as a long address
!G_WORK    = $AE                ; the row offset multiply, two words

; ---------------------------------------------------------------------------
; The signed fractional product, which is what every multiply here is.
;
; op_00_body is command $00's own arithmetic, read out of the part and checked
; exact against it on four hundred random argument sets. It takes two signed
; words, multiplies them to thirty two bits, doubles the product and keeps the
; high word, which is the part's multiplier exactly: (a * b) >> 15, rounded
; down even when the product is negative.
;
; Reused rather than written again. A second multiply would be a second place
; for the rounding to be wrong, and getting that rounding wrong is invisible
; until the ground is a few pixels out.
; ---------------------------------------------------------------------------
macro mul15(one, two)
    lda <one>
    sta !PAIR+0
    lda <two>
    sta !PAIR+2
    jsl op_00_body
endmacro

; ---------------------------------------------------------------------------
; $003a: normalise, which is where every earlier reading of $0a went wrong.
;
; It doubles the value until doubling would change its sign, then steps back to
; the last value that fitted. So what comes out has bit fourteen set and bit
; fifteen clear, or the other way round for a negative, and the magnitude lands
; in $4000 to $7fff. Every attempt before this one normalised to bit fifteen
; instead, one bit too far.
;
; The test for "doubling would change the sign" is that the top two bits differ.
; `asl a` leaves the old bit fifteen in the carry and the new one in the
; negative flag, so comparing those two is the whole test and costs no extra
; instruction.
;
; Nought is caught before the loop. Doubling nought never changes its sign, so
; the loop would never end.
;
; In:  A the value.
; Out: A and !G_NORM the value normalised, !G_COUNT the count of doublings.
; ---------------------------------------------------------------------------
ground_normalise:
    stz !G_COUNT
    sta !G_NORM
    cmp #$0000
    beq .settled

.again:
    sta !G_NORM                 ; the last value that fitted
    asl a                       ; carry the old sign, negative the new one
    bcs .wasneg
    bpl .keep                   ; was positive and still is
    bra .stop

.wasneg:
    bmi .keep                   ; was negative and still is

.stop:
    lda !G_NORM                 ; the doubling would have overflowed, so the
    rts                         ; value before it is the answer

.keep:
    inc !G_COUNT
    bra .again

.settled:
    rts

; ---------------------------------------------------------------------------
; $00d3: the reciprocal, as one table read.
;
; The part does not read a table here. It sets a pointer into its own data ROM,
; multiplies, computes a new pointer from what it got, and refines twice, which
; is why reading it as a table of one word reproduced 14.8% of scanlines and
; interpolating between entries changed nothing.
;
; What makes a table right anyway is the domain. This is only ever asked for a
; value that has just come out of the normalise loop above, so its magnitude is
; always between $4000 and $7fff. That is 16,384 values, which is 32,768 bytes,
; which is exactly one bank. The table is therefore complete by construction:
; no input can miss it, and the routine behind it would never run.
;
; The sign is not stored. The part takes the magnitude at $0d6 through $0d9,
; refines that, and negates the answer at $0f0, so half the range answers both
; halves. One magnitude cannot be negated in a word, $8000, and the part's own
; absolute value clamps it to $7fff, which is copied here rather than reasoned
; about.
;
; The exponent is not stored either. It comes back as the doubling count less
; six, on every input, which is two instructions.
;
; A distance of exactly nought is the part's own special case: it answers $7fff
; with an exponent of $2f, which is large enough that the shift below saturates.
; That is a scanline exactly on the horizon.
;
; In:  !G_NORM and !G_COUNT, as ground_normalise left them.
; Out: !G_RA the mantissa, !G_RB the exponent.
; ---------------------------------------------------------------------------
ground_reciprocal:
    lda !G_COUNT
    sec
    sbc #$0006
    sta !G_RB

    lda !G_NORM
    bne .real

    lda #$7FFF                  ; $0f2 and $0f3, the answer for nought
    sta !G_RA
    lda #$002F
    sta !G_RB
    rts

.real:
    stz !G_NEG
    lda !G_NORM
    bpl .magnitude

    inc !G_NEG
    cmp #$8000
    bne .flip
    lda #$7FFF                  ; the one value that cannot be negated
    bra .magnitude

.flip:
    eor #$FFFF
    inc a

.magnitude:
    sec
    sbc #$4000                  ; the table starts where the normalise loop's
    asl a                       ; range does, and each entry is two bytes
    tax
    lda.l dsp1_reciprocal_of,x

    ldy !G_NEG
    beq .done
    eor #$FFFF                  ; the part negates its own answer for a
    inc a                       ; negative input

.done:
    sta !G_RA
    rts

; ---------------------------------------------------------------------------
; $0077: turn a mantissa and an exponent into a scale.
;
; It normalises again, works out how far to shift, and shifts by multiplying by
; a power of two out of its data ROM. Those ROM words were read off the part:
; $022 through $030 hold 1, 2, 4 and so on up to 16,384, and $000 through $021
; are all nought. So the multiply is a shift, and a shift of sixteen or more is
; a multiply by nought.
;
; The two exits above nought are the part's own:
;
;   exactly nought   hand back the normalised value untouched      $080, $086
;   above nought     clamp to $7fff or $8001 by sign               $083, $085
;
; $8001 rather than $8000. The part loads that constant, so the most negative
; scale it can answer is minus 32,767.
;
; Both exits are reached in practice: across 43,440 answer words the exact one
; fired 121 times and the clamp 132 times, which is why they are here rather
; than assumed unreachable.
;
; In:  A the mantissa, !G_EXP the exponent.
; Out: A the scale.
; ---------------------------------------------------------------------------
ground_scale:
    jsr ground_normalise

    lda !G_EXP
    sec
    sbc !G_COUNT
    sec
    sbc #$000F                  ; fifteen, the multiplier's own shift
    bpl .saturating

    eor #$FFFF                  ; how many places to shift right
    inc a
    cmp #$0010
    bcs .flat                   ; sixteen or more reads a ROM word of nought

    tay
    lda !G_NORM
-
    cmp #$8000                  ; bit fifteen into the carry, then straight
    ror a                       ; back into bit fifteen: an arithmetic shift
    dey
    bne -
    rts

.flat:
    lda #$0000
    rts

.saturating:
    bne .clamp
    lda !G_NORM                 ; exactly nought: untouched
    rts

.clamp:
    lda !G_NORM
    bmi .low
    lda #$7FFF
    rts

.low:
    lda #$8001
    rts

; ---------------------------------------------------------------------------
; One scanline, which is the whole of $0a for one line of the screen.
;
; In:  !G_LINE, and the state ground_state loaded.
; Out: !G_OUT+0 through !G_OUT+6, the four words the part answers.
; ---------------------------------------------------------------------------
ground_line:
    %mul15(!G_STEP, !G_LINE)    ; how far this line is from the viewpoint
    clc
    adc !G_HORIZON

    jsr ground_normalise
    jsr ground_reciprocal

    %mul15(!G_MAN1, !G_RA)
    sta !G_MA
    lda !G_RB
    clc
    adc !G_EXP1
    sta !G_EXP

    lda !G_MA
    jsr ground_scale
    sta !G_S1

    ; The second scale multiplies the first chain's mantissa, not the
    ; reciprocal. That is the cascade, and it is the whole reason six attempts
    ; to recover this from the answers failed.
    %mul15(!G_MAN2, !G_MA)
    tay                         ; keep it while the exponent is worked out
    lda !G_EXP
    clc
    adc !G_EXP2
    sta !G_EXP
    tya
    jsr ground_scale
    sta !G_S2

    ; The four words. The first scale takes the two matrix words the part reads
    ; from $7f and $6f, and the second takes the two from $7e and $6e.
    %mul15(!G_MAT+0, !G_S1)
    sta !G_OUT+0
    %mul15(!G_MAT+2, !G_S2)
    sta !G_OUT+2
    %mul15(!G_MAT+4, !G_S1)
    sta !G_OUT+4
    %mul15(!G_MAT+6, !G_S2)
    sta !G_OUT+6
    rts

; ---------------------------------------------------------------------------
; Where a row lives: the table's start plus the row index times the stride.
;
; Shift and add, because the strides are 6, 8 and 10 bytes and none of them is
; a power of two. Four passes at worst, and it runs three times per bisect step
; rather than per scanline.
;
; In:  !G_MID the row index, !G_BASE, !G_STRIDE.
; Out: !G_ROW a long pointer to that row.
; ---------------------------------------------------------------------------
ground_rowat:
    lda !G_MID
    sta !G_WORK+0               ; doubled on every pass
    lda !G_STRIDE
    sta !G_WORK+2               ; halved on every pass
    stz !G_ROW

-
    lsr !G_WORK+2
    bcc +
    lda !G_ROW
    clc
    adc !G_WORK+0
    sta !G_ROW
+
    asl !G_WORK+0
    lda !G_WORK+2
    bne -

    lda !G_ROW
    clc
    adc !G_BASE
    sta !G_ROW
    lda !G_BASE+2
    sta !G_ROW+2
    rts

; ---------------------------------------------------------------------------
; Whether the row in !G_ROW sits below the key wanted.
;
; Keys are argument words the cartridge wrote, so they are compared as unsigned
; and in the same order the builder sorted them in. A two word key compares the
; second word only when the first is equal, which is what sorting on the pair
; means.
;
; Out: carry clear when the row is below the key, set otherwise.
; ---------------------------------------------------------------------------
ground_below:
    ldy #$0000
    lda [!G_ROW],y
    cmp !G_KEY+0
    bcc .below
    bne .notbelow               ; above it on the first word alone

    lda !G_KEYS
    cmp #$0002
    bcc .notbelow               ; a one word key, and it matched

    ldy #$0002
    lda [!G_ROW],y
    cmp !G_KEY+2
    bcc .below

.notbelow:
    sec
    rts

.below:
    clc
    rts

; ---------------------------------------------------------------------------
; Find the row a key names, or the nearest one above it.
;
; A plain lower bound: halve the range until it is empty, and !G_LOW is then
; the first row whose key is not below the one wanted. That row is the answer
; when the key is in the table, and the nearest one above it when it is not.
;
; A key the table does not hold is possible. The tables carry every $02 argument
; set all three recordings hold, so the demo never misses, but a player doing
; something no recording did would. These arguments are an aircraft's attitude
; sampled every frame, so the row above is the next frame's worth away rather
; than anything: a near miss instead of a failure.
;
; Twelve compares at worst, for the largest of the three tables.
;
; In:  !G_KEY, !G_BASE, !G_STRIDE, !G_KEYS, !G_ROWS.
; Out: !G_ROW a long pointer to the row chosen.
; ---------------------------------------------------------------------------
ground_find:
    stz !G_LOW
    lda !G_ROWS
    sta !G_HIGH

.step:
    lda !G_LOW
    cmp !G_HIGH
    bcs .settled

    clc
    adc !G_HIGH                 ; low plus high cannot pass sixteen bits: the
    lsr a                       ; largest table has 3,302 rows
    sta !G_MID

    jsr ground_rowat
    jsr ground_below
    bcc .above

    lda !G_MID                  ; this row could still be the one, so it
    sta !G_HIGH                 ; becomes the top of the range
    bra .step

.above:
    lda !G_MID
    inc a
    sta !G_LOW
    bra .step

.settled:
    lda !G_LOW
    cmp !G_ROWS
    bcc .inside

    lda !G_ROWS                 ; every key in the table is below the one
    dec a                       ; wanted, so the last row is the nearest

.inside:
    sta !G_MID
    jsr ground_rowat
    rts

; ---------------------------------------------------------------------------
; The ten words $0a reads, out of the three tables $02's arguments key.
;
; $02 writes all ten into the part's own memory and answers four words that
; have nothing to do with them, which is why the recorded-answer table could
; never carry them. state02build.py drives the part across every $02 argument
; set the recordings hold and splits what it finds three ways:
;
;   keyed on argument 6        the step, the horizon, the second exponent
;   keyed on arguments 2 and 6 both mantissas and the first exponent
;   keyed on argument 5        the matrix, as two words
;
; The split is measured, not assumed: across all 6,980 distinct sets no key
; carries two different answers, which is what makes each table a function of
; its key rather than a hopeful reading.
;
; The matrix is two words because the other two are those two again. The part
; writes the cosine twice and the sine twice, once negated, on every one of
; those 6,980 sets, and state02build.py refuses a set that breaks it rather
; than storing half a matrix.
;
; !CARRY_02 is where dsp1-port.asm keeps $02's arguments as they arrive. Reading
; them here rather than doing the lookup when $02 completes costs nothing: the
; game asks $02 once per frame and $0a once per frame, so it is the same three
; searches either way, and it leaves the port untouched.
; ---------------------------------------------------------------------------
ground_state:
    ; The line table, keyed on argument 6.
    lda.l !CARRY_02+12
    sta !G_KEY+0
    lda.w #!STATE02_LINE_ROWS
    sta !G_ROWS
    lda.w #!STATE02_LINE_STRIDE
    sta !G_STRIDE
    lda.w #!STATE02_LINE_KEYS
    sta !G_KEYS
    lda.w #(state02_line&$FFFF)
    sta !G_BASE
    lda.w #(state02_line>>16)
    sta !G_BASE+2
    jsr ground_find

    ldy #$0002                  ; past the one key word
    lda [!G_ROW],y
    sta !G_STEP
    ldy #$0004
    lda [!G_ROW],y
    sta !G_HORIZON
    ldy #$0006
    lda [!G_ROW],y
    sta !G_EXP2

    ; The scale table, keyed on arguments 2 and 6 in that order, which is the
    ; order state02build.py sorted the rows in.
    lda.l !CARRY_02+4
    sta !G_KEY+0
    lda.l !CARRY_02+12
    sta !G_KEY+2
    lda.w #!STATE02_SCALE_ROWS
    sta !G_ROWS
    lda.w #!STATE02_SCALE_STRIDE
    sta !G_STRIDE
    lda.w #!STATE02_SCALE_KEYS
    sta !G_KEYS
    lda.w #(state02_scale&$FFFF)
    sta !G_BASE
    lda.w #(state02_scale>>16)
    sta !G_BASE+2
    jsr ground_find

    ldy #$0004                  ; past the two key words
    lda [!G_ROW],y
    sta !G_MAN1
    ldy #$0006
    lda [!G_ROW],y
    sta !G_EXP1
    ldy #$0008
    lda [!G_ROW],y
    sta !G_MAN2

    ; The matrix table, keyed on argument 5.
    lda.l !CARRY_02+10
    sta !G_KEY+0
    lda.w #!STATE02_MATRIX_ROWS
    sta !G_ROWS
    lda.w #!STATE02_MATRIX_STRIDE
    sta !G_STRIDE
    lda.w #!STATE02_MATRIX_KEYS
    sta !G_KEYS
    lda.w #(state02_matrix&$FFFF)
    sta !G_BASE
    lda.w #(state02_matrix>>16)
    sta !G_BASE+2
    jsr ground_find

    ldy #$0002
    lda [!G_ROW],y              ; the cosine, which the part holds at $7f
    sta !G_MAT+0
    sta !G_MAT+6                ; and again at $6e
    ldy #$0004
    lda [!G_ROW],y              ; the sine, at $7e
    sta !G_MAT+2
    eor #$FFFF                  ; and negated at $6f
    inc a
    sta !G_MAT+4
    rts

; ---------------------------------------------------------------------------
; The whole stream, in place of the loop the game read it with.
;
; patch.py replaces 62 bytes of the game's own code with a call to this, because
; that loop reaches the part through three byte instructions with no room for a
; four byte call. The loop read four words per turn and put two in the buffer at
; $0420 and two in the one at $0700, so that is what this writes.
;
; X and Y are left where the original loop left them, 704 and nought, because
; the game's code carries on from there and may still be using either.
; ---------------------------------------------------------------------------
ground_block:
    php
    phb
    phd
    rep #$30

    lda.w #!PAGE                ; the working variables, off the game's own page
    tcd
    lda #$0000                  ; the two buffers and the multiplier are all in
    pha                         ; bank zero
    plb
    plb

    jsr ground_state

    lda.l !PORT_LINE            ; the one argument $0a takes is the first line,
    sta !G_LINE                 ; which dsp_route_0a works out and keeps, because
                                ; the game writes it through the window and the
                                ; port never sees it

    stz !G_AT
    lda.w #!STREAM_TURNS
    sta !G_TURNS

.turn:
    jsr ground_line

    ldx !G_AT
    lda !G_OUT+0
    sta.w !STREAM_ONE,x
    lda !G_OUT+2
    sta.w !STREAM_ONE+2,x
    lda !G_OUT+4
    sta.w !STREAM_TWO,x
    lda !G_OUT+6
    sta.w !STREAM_TWO+2,x

    inc !G_LINE
    lda !G_AT
    clc
    adc #$0004
    sta !G_AT

    dec !G_TURNS
    bne .turn

    ldx !G_AT                   ; what the original loop's own index reached
    ldy #$0000

    pld
    plb
    plp
    rtl

; ---------------------------------------------------------------------------
; $0a asked through the lookup rather than through the stream.
;
; The port serves $0a's answer out of a four word buffer a word at a time, so
; only one scanline fits in it. This answers the first, which is the scanline
; the argument names.
;
; It is not the path the demo takes. dsp_width says $0a answers nothing, so the
; port never reaches the lookup for it and ground_block above serves every
; scanline the game actually reads. This is here so that a command arriving by a
; route nobody has seen gets arithmetic rather than nought.
;
; In:  !ARG+0 the argument, with the direct page and the data bank already set
;      by dsp1_answer.
; Out: !OUT+0 through !OUT+6.
; ---------------------------------------------------------------------------
ground_answer:
    php
    rep #$30

    jsr ground_state

    lda !ARG+0
    sta !G_LINE
    jsr ground_line

    lda !G_OUT+0
    sta.l !OUT+0
    lda !G_OUT+2
    sta.l !OUT+2
    lda !G_OUT+4
    sta.l !OUT+4
    lda !G_OUT+6
    sta.l !OUT+6

    plp
    rtl
