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
; So it is computed. Per scanline: one normalise, one table read for the
; reciprocal, one multiply and one shift for each of two scales, and four
; multiplies for the four words it answers with. The distance the part
; multiplies out is a running sum here instead, which is the same number
; rather than a near one: see ground_seed.
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

; The four words a multiply reads are each followed by a word held at nought.
; A multiply wants the high byte of its varying word, and reading the direct page
; one byte along gives that byte together with whatever follows it; when what
; follows is nought, the byte arrives on its own and nothing has to mask it. The
; four are cleared once per block, which buys three cycles in each of the six
; multiplies a scanline.
!G_LINE    = $76                ; which scanline is being answered
!G_NORM    = $78                ; what the normalise loop left
!G_COUNT   = $7A                ; and how many doublings it took
!G_RA      = $7C                ; the reciprocal's mantissa
!G_RAPAD   = $7E
!G_RB      = $80                ; and its exponent
!G_MA      = $82                ; the first chain's mantissa before its shift
!G_MAPAD   = $84
!G_EXP     = $86                ; the exponent the scale about to run will use
!G_S1      = $88                ; the two scales for this scanline
!G_S1PAD   = $8A
!G_S2      = $8C
!G_S2PAD   = $8E
!G_NEG     = $90                ; whether the reciprocal's sign has to go back
!G_SEEN    = $92                ; the distance the scanline before this one had
!G_STEP2   = $94                ; twice the step, for the doubled running sum

; The two the table reads need. There was a bisecting search here as well, over
; three tables recorded from playthroughs, and it is gone: every one of the ten
; words $02 leaves behind is now computed or read from a table covering the whole
; of its key, so there is nothing left to search and nothing left to miss.
!G_HELD    = $96                ; one value kept across a multiply
!G_ROW     = $AA                ; where a table entry is, as a long address

; The distance, kept as a running thirty two bit product rather than multiplied
; out on every scanline. See ground_seed for why that is exact rather than close.
!G_ACC     = $B2                ; the step times the line, to thirty two bits
!G_STEPHI  = $B6                ; the step's sign, so the running sum can carry

; The four running sums the table builder carries, and the four constants it is
; building from, held next to each other so one loop can walk both.
!G_SUM     = $B8                ; four thirty two bit sums, $B8 to $C7
!G_LAST    = $C8                ; the four constants the tables were built from
!G_AGAIN   = $D0                ; nought once the pads have been written

; ===========================================================================
; SIX MULTIPLIES A SCANLINE, AND HOW FOUR TABLES ANSWER ALL OF THEM
; ===========================================================================
;
; ground_line multiplies six times, and every one of the six has the same shape:
; a value that is the same for the whole stream, times a value that is not.
;
;   the first scale's mantissa   times the reciprocal
;   the second scale's mantissa  times the first chain
;   the cosine                   times the first scale
;   the sine                     times the second scale
;   the sine negated             times the first scale
;   the cosine                   times the second scale
;
; Four constants, because the last two repeat the first two: ground_state writes
; the cosine into two of the four matrix words and the sine, negated, into the
; other two, which is what the part does with them.
;
; A multiply by a value that does not change can be a table. Split the varying
; word into its two bytes and the product is
;
;     k * v  =  (k * high byte) * 256  +  (k * low byte)
;
; and both halves are one of 256 entries. The table is built by adding k to a
; running sum 256 times, which is 256 additions against the 256 multiplies it
; replaces, and it is built once per stream against six uses on each of 176
; scanlines.
;
; ===========================================================================
; WHY AN ENTRY IS FIVE BYTES AND NOT FOUR
; ===========================================================================
;
; Because both halves above want the same entry, one of them shifted up a byte,
; and shifting a thirty two bit value up a byte on this processor is eleven
; instructions. Storing a nought in front of each entry gives both readings for
; free: read the four bytes after the nought and it is k times b; read the four
; bytes starting at the nought and it is that times 256, with the byte that
; falls off the top being the sign extension the shift would have dropped.
;
; The cost is that an index is b times five rather than b times four, which is
; three instructions rather than one, and 1,280 bytes a table rather than 1,024.
;
; Eight bytes an entry was tried, so that an index would be three doublings and
; nothing else. It came out a tenth slower over the same 250 frames, which is
; the build loop and the noughts walking half again as far for four instructions
; a multiply, and it is why the awkward stride stays.
;
; ===========================================================================
; WHERE THEY LIVE
; ===========================================================================
;
; 5,120 bytes at $7E:E000, which is all four.
;
; The run !PORTRAM sits in was chosen by keeping the bytes that never changed
; across a run of the demo, and a byte the game reads but never writes passes
; that test as easily as a byte it never touches. $7FDE00 is such a byte, and
; 5,120 bytes of tables written over it stopped the demo before its second
; frame.
;
; What is actually spare is measured the other way here: bytes that hold the
; console's power-on fill in every one of 600 frames of the retail cartridge,
; which a byte the game reads cannot. Scanned across the whole 128 kilobytes
; rather than across the window !PORTRAM sits in, the longest such run is
; $7E:E000 to $7E:FFFF, 8,192 bytes, and there are 32,888 bytes of them
; altogether.
;
; The measurement is of the demo, so a byte this leaves alone during the demo
; and the game uses in play would not show. That is the same bet !PORTRAM makes
; and the same one the frame by frame comparison against the cartridge checks.
; ===========================================================================
; Each table is named outright rather than reached as a base plus an offset,
; because this assembler evaluates left to right: `!MULTAB+!MULSPAN*0+1` is
; ((!MULTAB+!MULSPAN)*0)+1, which is 1. Every read went to address 1 and every
; table stayed as the console left it, with nothing in the source looking wrong.
; Eight bytes an entry rather than five, and three of them never read. An
; entry's address is then its number shifted three places, where five bytes made
; it a shift, a shift, a store, an addition and a load. That is done twice per
; multiply and the multiply runs 1,056 times a frame, against 256 entries built
; at most once, so the three spare bytes an entry buy more than they cost: the
; build writes the same four bytes either way, and the nought each entry opens
; with is written once ever.
!MULTAB    = $7EE000            ; the four tables, 2,048 bytes each
!MULTAB0   = $7EE000            ; the cosine's
!MULTAB1   = $7EE800            ; the sine's
!MULTAB2   = $7EF000            ; the first scale's mantissa
!MULTAB3   = $7EF800            ; and the second's
!MULSPAN   = 2048
!MULSTRIDE = 8
!MULTABS   = 4

; ---------------------------------------------------------------------------
; k times v, shifted right fifteen, out of the table built for k.
;
; The same answer op_00_body gives and reached without a multiply. The whole
; product is formed first and the shift comes last, because a shift of each half
; separately rounds twice and the part rounds once.
;
; The varying word is read as unsigned, so a negative one is too big by 65536
; and the product with it is too big by k times 65536. That is the constant
; itself taken off the high half, and the constant is the table's own entry one.
;
; In:  the varying word at `from`. Out: A the answer. Uses X and !TMP+4 to !TMP+7.
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; The lookup itself, inlined at all six sites.
;
; Inlined rather than called because the whole of it is thirty instructions and
; a call to it would be six of those. The tables all sit inside one bank, so an
; entry is a long read indexed by X and needs no pointer set up first.
;
; In:  the varying word at `from`. Out: !TMP+4 and !TMP+6 the whole product.
; Uses X.
; ---------------------------------------------------------------------------
macro mulk_product(table, from)
    lda <from>                  ; read twice rather than read once and parked:
                                ; the caller already holds it in the direct page
    and #$00FF                  ; the low byte, times eight, is where its entry is
    asl a                       ; and shifting a byte three places can never push
    asl a                       ; a bit out, so the carry is clear afterwards and
    asl a                       ; the addition below needs no clearing of its own
    tax
    lda.w (<table>&$FFFF)+1,x           ; past the nought, so this is k times that byte
    sta !TMP+4
    lda.w (<table>&$FFFF)+3,x
    sta !TMP+6

    lda <from>+1                ; and the high byte the same way. The direct page
                                ; one byte along is that byte with a nought above
                                ; it, so nothing has to swap and nothing to mask
    asl a
    asl a
    asl a
    tax
    lda.w (<table>&$FFFF)+0,x           ; from the nought, so this is that entry times 256
    adc !TMP+4                  ; the sum's low half is wanted only for the carry
    lda.w (<table>&$FFFF)+2,x           ; it leaves, so it is never written down
    adc !TMP+6

    ; The high byte's index carries the sign of the whole word. It is that byte
    ; shifted three places, so bit seven of it, which is the word's bit fifteen,
    ; lands at bit ten. Comparing the index against that bit is a cycle cheaper
    ; than reading the word back out of the direct page to test it.
    cpx.w #$0400                ; a negative word read as unsigned is too big by
    bcc ?whole                  ; 65536, so the constant comes off the high half,
    sec                         ; and entry one is the constant itself
    sbc.w (<table>&$FFFF)+9
?whole:
endmacro

; The product, shifted down fifteen places, which is what every multiply here
; wants. The shift is not done: the table holds twice the constant, so the high
; half %mulk_product leaves in the accumulator is already the shifted product.
macro mulk(table, from)
    %mulk_product(<table>, <from>)
endmacro

; ---------------------------------------------------------------------------
; Both products of one varying word, for the two tables the matrix uses.
;
; Four of the six multiplies a scanline are the two scales against the two
; matrix constants, so each scale is multiplied twice. An entry's address is its
; number shifted three places and that number is the same for both tables, so
; the address is worked out once and read from twice. Every table has the same
; shape, which is what makes one index reach into either.
;
; In:  the varying word at `from`. Out: the first table's product written
; through Y, the second's in !TMP+8 and !TMP+10, both sign-corrected.
; Uses X and !TMP+4 to !TMP+11.
; ---------------------------------------------------------------------------
macro mulk_products(one, two, first, from, keeplow)
    lda <from>                  ; read twice rather than read once and parked
    and #$00FF                  ; the low byte, times eight, is where its entry
    asl a                       ; is, and it is the entry in either table
    asl a
    asl a
    tax
    lda.w (<one>&$FFFF)+1,x
    sta !TMP+4
    lda.w (<one>&$FFFF)+3,x
    sta !TMP+6
    lda.w (<two>&$FFFF)+1,x
    sta !TMP+8
    lda.w (<two>&$FFFF)+3,x
    sta !TMP+10

    lda <from>+1                ; and the high byte the same way, once for both.
                                ; The direct page one byte along is that byte
                                ; with a nought above it
    asl a
    asl a
    asl a
    tax

    lda.w (<one>&$FFFF)+0,x
    adc !TMP+4                  ; the first product's low half is wanted only for
    lda.w (<one>&$FFFF)+2,x             ; the carry, so it is never written down either
    adc !TMP+6
    ; The high byte's index carries the sign of the whole word. It is that byte
    ; shifted three places, so bit seven of it, which is the word's bit fifteen,
    ; lands at bit ten. Comparing the index against that bit is a cycle cheaper
    ; than reading the word back out of the direct page to test it.
    cpx.w #$0400
    bcc ?first
    sec
    sbc.w (<one>&$FFFF)+9
?first:
    sta.w <first>,y             ; the first product is stored here rather than
                                ; parked, because the index the second needs is
                                ; already in X and nothing between disturbs it

    lda.w (<two>&$FFFF)+0,x
    clc
    adc !TMP+8
if <keeplow> == 1
    sta !TMP+8                  ; only the caller that negates reads this back
endif
    lda.w (<two>&$FFFF)+2,x
    adc !TMP+10
    cpx.w #$0400
    bcc ?second
    sec
    sbc.w (<two>&$FFFF)+9
?second:
endmacro

; Negating the product and then shifting is the same as taking one off it,
; shifting, and flipping every bit of what comes out. Negating is flipping every
; bit and adding one, so the product negated is one less than it flipped, and
; flipping commutes with a shift that carries the sign down. Taking one off is
; cheaper than flipping thirty two bits and adding one to them.
;
; The shift itself has to come after, not before: the part negates the whole
; product, and negating a shifted answer would round the wrong way on every
; product the shift does not divide.
; The same, negated. Shifting a negated product and negating a shifted one are
; not the same number, so the negation is done on the product: minus p shifted
; down fifteen is the complement of p less one shifted down fifteen.
;
; Two comes off rather than one, because the pair holds twice the product.
macro mulk_shift_negated(low)
    ; The high half is already in the accumulator and only the borrow the low
    ; half's subtraction would leave is missing. A compare produces exactly that
    ; borrow without touching the accumulator, so nothing has to be parked and
    ; fetched back: the carry a compare clears is the borrow a subtraction of two
    ; from a low half below two would have made.
    ldx <low>
    cpx.w #$0002
    sbc #$0000
    eor #$FFFF
endmacro

                       ; there is a read, a change and a write

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
; The count is kept in X while the loop turns and written out at the end. A
; direct page increment is a read, a change and a write, and the direct page is
; the console's own memory, which is the slow half of the machine. The register
; costs nothing. This loop turns about 2,120 times per frame of the game's clock.
;
; X is free here: the multiplies set it themselves and ground_scale counts its
; own shift in Y.
macro normalise()
    ldx #$0000
    cmp #$0000
    beq ?settled

    ; Each of the two signs has its own turn, so neither pays a branch to reach
    ; the other's, and both leave the loop by falling out of it rather than by
    ; jumping over the tail. The three instructions that repeat are cheaper than
    ; the branches that sharing them cost.
?again:
    asl a                       ; carry the old sign, negative the new one
    bcs ?wasneg
    bmi ?stopped                ; was positive and is not any more
    inx
    bra ?again

?wasneg:
    bpl ?stopped                ; was negative and is not any more
    inx
    bra ?again

?stopped:
    ror a                       ; the doubling overflowed, so it is undone. The
                                ; bit it pushed out is still in the carry, which
                                ; is where a rotate right puts bit fifteen back
                                ; from, so this is the value exactly as it was
?settled:
    stx !G_COUNT
    sta !G_NORM
endmacro

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
macro reciprocal()
    lda !G_COUNT
    sec
    sbc #$0006
    sta !G_RB

    lda !G_NORM
    bne ?real

    lda #$7FFF                  ; $0f2 and $0f3, the answer for nought
    sta !G_RA
    lda #$002F
    sta !G_RB
    bra ?done

?real:
    ldy #$0000                  ; whether the sign has to go back afterwards, in
    lda !G_NORM                 ; a register rather than in the direct page,
    bpl ?magnitude              ; which is the console's own memory

    iny
    cmp #$8000
    bne ?flip
    lda #$7FFF                  ; the one value that cannot be negated
    bra ?magnitude

?flip:
    eor #$FFFF
    inc a

?magnitude:
    sec
    sbc #$4000                  ; the table starts where the normalise loop's
    asl a                       ; range does, and each entry is two bytes
    tax
    lda.l dsp1_reciprocal_of,x

    cpy #$0000
    beq ?tail
    eor #$FFFF                  ; the part negates its own answer for a
    inc a                       ; negative input

?tail:
    sta !G_RA
    bra ?done
?done:
endmacro

; ---------------------------------------------------------------------------
; $003a and $00d3 together, as three table reads and no loop.
;
; The two macros above are still here because ground_scale uses them, and there
; the value arriving has already been normalised by the multiply that produced
; it, so the loop turns nought or one time and costs almost nothing. The one
; place it was expensive is the scanline's own distance, which arrives raw and
; needs about ten doublings, and that is what this replaces.
;
; The tables are keyed on the folded value: a negative word complemented, so that
; a word and its complement share an entry for the exponent. asm/dsp1-derived.asm
; carries why, and derived.py builds them.
;
; A distance of exactly nought is entry nought of the upward table, so it needs no
; branch. Every other value takes one of four arms: sign, then which half of the
; table the index landed in, because a bank reaches 32,768 bytes and an entry is
; two.
;
; In:  A the value, the distance plus the horizon.
; Out: !G_RA the mantissa, !G_RB the exponent. Uses X and Y.
; ---------------------------------------------------------------------------
; The sign is branched on before anything else touches the accumulator. An
; earlier version loaded a register first to remember the sign, and a load sets
; the negative flag from what was loaded, so the test that followed read the
; register rather than the value and every negative distance took the positive
; arm. It cost 10,402 wrong answer bytes and one measurement to find.
macro invert()
    bmi ?down

    asl a                       ; two bytes an entry
    tax
    beq ?horizon                ; nought and the value one below it fold to the
                                ; same entry and want different exponents, so
                                ; the one of them that is positive is answered
                                ; here and the table holds the other
    cpx.w #$8000                ; which half of the table the index landed in
    bcs ?up_high
    lda.l dsp1_recip_up,x
    sta !G_RA
    lda.l dsp1_recip_exponent,x
    bra ?done

?up_high:
    lda.l dsp1_recip_up_high-$8000,x
    sta !G_RA
    lda.l dsp1_recip_exponent_high-$8000,x
    bra ?done

?down:
    eor #$FFFF                  ; the complement, not the negation: it is the
                                ; run of leading sign bits that has to survive,
                                ; and complementing keeps it while negating does
                                ; not
    asl a
    tax
    cpx.w #$8000
    bcs ?down_high
    lda.l dsp1_recip_down,x
    sta !G_RA
    lda.l dsp1_recip_exponent,x
    bra ?done

?down_high:
    lda.l dsp1_recip_down_high-$8000,x
    sta !G_RA
    lda.l dsp1_recip_exponent_high-$8000,x
    bra ?done

?horizon:
    lda.w #$7FFF                ; $0f2 and $0f3, the part's own answer for a
    sta !G_RA                   ; distance of nought: a scanline exactly on the
    lda.w #$002F                ; horizon, with an exponent large enough that
                                ; the shift after it saturates

?done:
    sta !G_RB
endmacro

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
; $0077: a mantissa and an exponent turned into a scale, written out where it is
; used rather than called.
;
; It normalises again, works out how far to shift, and shifts. The part shifts by
; multiplying by a power of two out of its data ROM, whose words are 1, 2, 4 and
; so on up to 16,384 with nought below them, so the multiply is a shift and a
; shift of sixteen or more is a multiply by nought.
;
; The two exits above nought are the part's own:
;
;   exactly nought   hand back the normalised value untouched      $080, $086
;   above nought     clamp to $7fff or $8001 by sign               $083, $085
;
; $8001 rather than $8000. The part loads that constant, so the most negative
; scale it can answer is minus 32,767. Both exits are reached in practice: across
; 43,440 answer words the exact one fired 121 times and the clamp 132.
;
; The processor has no variable shift, so the shift is written out once per place
; and entered part way down. A value with bit fifteen clear shifts in noughts,
; which is one instruction a place; only one with bit fifteen set needs two, and
; measured over one call the shorter case is 72% of them at an average of 5.12
; places. The sign is read once and never changes inside the chain, because
; shifting a negative value right arithmetically leaves it negative.
;
; This was a subroutine that jumped to another. Both scales a scanline came
; through it, 352 times a frame of the game's clock, and the call, the jump and
; the return were fifteen cycles that did no arithmetic. Written out twice
; instead, it costs a couple of hundred bytes of an image with three free banks.
;
; In:  A the mantissa, !G_EXP the exponent. Out: A the scale. Uses X.
; ---------------------------------------------------------------------------
macro scale()
    %normalise()

    ; The count less the exponent is how many places to shift right, so it is
    ; subtracted that way round rather than the other way and negated. The
    ; multiplier's own fifteen is already off the exponent, taken out of the
    ; first one once per block.
    lda !G_COUNT
    sec
    sbc !G_EXP
    beq ?exact                  ; nothing to shift, and nothing to clamp either
    bmi ?clamp                  ; the exponent is above the count, so it saturates
    cmp #$0010
    bcs ?flat                   ; sixteen or more reads a ROM word of nought

    asl a                       ; two bytes an entry in the tables below
    tax
    lda !G_NORM
    bmi ?down
    jmp (?up_at,x)

?down:
    jmp (?down_at,x)

?flat:
    lda #$0000
    jmp ?done

?exact:
    lda !G_NORM                 ; exactly nought: untouched
    jmp ?done

?clamp:
    lda !G_NORM
    bmi ?low
    lda #$7FFF
    jmp ?done

?low:
    lda #$8001
    jmp ?done

?up_at:
    dw ?up_0
    dw ?up_1
    dw ?up_2
    dw ?up_3
    dw ?up_4
    dw ?up_5
    dw ?up_6
    dw ?up_7
    dw ?up_8
    dw ?up_9
    dw ?up_10
    dw ?up_11
    dw ?up_12
    dw ?up_13
    dw ?up_14
    dw ?up_15

?down_at:
    dw ?down_0
    dw ?down_1
    dw ?down_2
    dw ?down_3
    dw ?down_4
    dw ?down_5
    dw ?down_6
    dw ?down_7
    dw ?down_8
    dw ?down_9
    dw ?down_10
    dw ?down_11
    dw ?down_12
    dw ?down_13
    dw ?down_14
    dw ?down_15

?down_15:
    sec
    ror a
?down_14:
    sec
    ror a
?down_13:
    sec
    ror a
?down_12:
    sec
    ror a
?down_11:
    sec
    ror a
?down_10:
    sec
    ror a
?down_9:
    sec
    ror a
?down_8:
    sec
    ror a
?down_7:
    sec
    ror a
?down_6:
    sec
    ror a
?down_5:
    sec
    ror a
?down_4:
    sec
    ror a
?down_3:
    sec
    ror a
?down_2:
    sec
    ror a
?down_1:
    sec
    ror a
?down_0:
    jmp ?done

?up_15:
    lsr a
?up_14:
    lsr a
?up_13:
    lsr a
?up_12:
    lsr a
?up_11:
    lsr a
?up_10:
    lsr a
?up_9:
    lsr a
?up_8:
    lsr a
?up_7:
    lsr a
?up_6:
    lsr a
?up_5:
    lsr a
?up_4:
    lsr a
?up_3:
    lsr a
?up_2:
    lsr a
?up_1:
    lsr a
?up_0:
?done:
endmacro

; ---------------------------------------------------------------------------
; One scanline, which is the whole of $0a for one line of the screen.
;
; In:  !G_LINE, and the state ground_state loaded.
; Out: the four words the part answers, written into the two buffers at Y.
; ---------------------------------------------------------------------------
; The seven labels below name the stages rather than being jumped to. The
; assembler prints them, and tools/profile.py buckets a call's cycles by the
; nearest label above each address, so the stages report their own cost instead
; of a reader having to guess which of them the hot addresses belong to. They
; assemble to nothing.
macro line(mark)
if <mark> == 1
line_distance:
endif
    lda !G_ACC+2                ; the distance, out of the running product. The
    clc                         ; sum is kept at twice what the part holds it at,
    adc !G_HORIZON              ; so its high half is already the whole thirty two
                                ; bit value shifted down fifteen places, sign and
                                ; all, and the shift that used to stand here is
                                ; one instruction in ground_state instead

    ; Everything below this point is a function of that distance and of state the
    ; block fixed before the loop, so a scanline whose distance matches the one
    ; before it has the same four answers. Across the demo 63.6% of them do, in
    ; runs of up to eleven, because the distance is a running sum whose step is
    ; small next to the fifteen places it is shifted down: a block of 176
    ; scanlines holds about 64 distinct distances.
    ;
    ; The four answers are copied from the previous scanline's own slots rather
    ; than kept anywhere, which is four reads and four writes against the six
    ; multiplies, two scales and a reciprocal they stand in for.
if <mark> == 1
    cmp !G_SEEN
    bne ?fresh                  ; the scanline below is far too long to branch
    jmp ground_repeat           ; over with one
?fresh:
    sta !G_SEEN
    cmp #$0000                  ; a store sets no flags and the compare above
                                ; left its own, so the sign the lookup below
                                ; branches on has to be taken again
endif

if <mark> == 1
line_reciprocal:
endif
    %invert()

; The exponent is worked out before the multiply in both stages below, so the
; product goes straight into the scale rather than being parked and fetched back.
; In the second stage that also leaves Y untouched for the whole scanline, which
; is what lets the four answer words be written where they are wanted.
if <mark> == 1
line_mantissa:
endif
    lda !G_RB
    clc
    adc !G_EXP1
    sta !G_EXP

    %mulk(!MULTAB2, !G_RA)
    sta !G_MA
    %scale()
    sta !G_S1

    ; The second scale multiplies the first chain's mantissa, not the
    ; reciprocal. That is the cascade, and it is the whole reason six attempts
    ; to recover this from the answers failed.
if <mark> == 1
line_cascade:
endif
    lda !G_EXP
    clc
    adc !G_EXP2
    sta !G_EXP

    %mulk(!MULTAB3, !G_MA)
    %scale()
    sta !G_S2

    ; The four words. The first scale takes the two matrix words the part reads
    ; from $7f and $6f, and the second takes the two from $7e and $6e.
; Written straight into the two buffers the game reads, at the offset Y holds,
; rather than into four direct page words the caller then copied across. Y is
; the caller's own index and nothing between here and there disturbs it.
if <mark> == 1
line_words_first:
endif
    %mulk_products(!MULTAB0, !MULTAB1, !STREAM_ONE, !G_S1, 1)
    %mulk_shift_negated(!TMP+8)
    sta.w !STREAM_TWO,y

if <mark> == 1
line_words_second:
endif
    %mulk_products(!MULTAB1, !MULTAB0, !STREAM_ONE+2, !G_S2, 0)
    sta.w !STREAM_TWO+2,y

if <mark> == 1
    bra ground_advance

ground_repeat:
    lda.w !STREAM_ONE-4,y       ; the same distance, so the same four answers
    sta.w !STREAM_ONE,y
    lda.w !STREAM_ONE+2-4,y
    sta.w !STREAM_ONE+2,y
    lda.w !STREAM_TWO-4,y
    sta.w !STREAM_TWO,y
    lda.w !STREAM_TWO+2-4,y
    sta.w !STREAM_TWO+2,y

ground_advance:
endif

    ; One line further down the screen, which used to be its own subroutine. The
    ; caller has nothing to do between the two, so the call and the return were
    ; twelve cycles a scanline that did no arithmetic.
    lda !G_ACC+0
    clc
    adc !G_STEP2
    sta !G_ACC+0
    lda !G_ACC+2
    adc !G_STEPHI
    sta !G_ACC+2
endmacro

ground_line:
    %line(0)
    rts

; ---------------------------------------------------------------------------
; The distance, set up once for a whole stream instead of multiplied per line.
;
; The part computes `(step * line) >> 15` on every scanline, and `line` steps by
; one. So the thirty two bit product steps by `step`, and a running sum of it is
; the same number rather than a near one: the part's multiplier answers the top
; word of the product doubled, which is bits fifteen through thirty of the
; product, and those are exactly the bits ground_line reads out of the sum.
;
; It cannot overflow. The step is a word and the line runs 176 places from wherever
; it starts, so the product stays under 2^31 even at the extremes of both.
;
; In:  !G_STEP and !G_LINE.
; Out: !G_ACC the product, !G_STEPHI the step's sign for the running sum to carry.
; ---------------------------------------------------------------------------
ground_seed:
    stz !G_NEG

    lda !G_STEP
    bpl .stepped
    inc !G_NEG
    eor #$FFFF                  ; the multiply below is unsigned, so both
    inc a                       ; operands go in as magnitudes and the sign is
.stepped:                       ; put back on the product
    sta !TMP+0

    lda !G_LINE
    bpl .lined
    inc !G_NEG
    eor #$FFFF
    inc a
.lined:
    sta !TMP+2

    jsl mul16

    lda !G_NEG
    lsr a
    bcc .positive               ; both negative or neither, so the product stands

    lda !TMP+4                  ; one of them was, so negate all thirty two bits
    eor #$FFFF
    clc
    adc #$0001
    sta !TMP+4
    lda !TMP+6
    eor #$FFFF
    adc #$0000
    sta !TMP+6

.positive:
    lda !TMP+4
    sta !G_ACC+0
    lda !TMP+6
    sta !G_ACC+2

    lda !G_STEP                 ; the step widened to thirty two bits, so the
    bpl .up                     ; sum below carries the right way
    lda #$FFFF
    bra .kept
.up:
    lda #$0000
.kept:
    sta !G_STEPHI
    rts

; ---------------------------------------------------------------------------
; A signed sixteen by sixteen multiply, shifted down fifteen places.
;
; Both operands go in as magnitudes and the sign goes back on the whole thirty
; two bit product, because shifting a negated product and negating a shifted one
; are not the same number.
;
; In:  A the first operand, the second already in !TMP+2.
; Out: A the product shifted. Uses !TMP+0 through !TMP+13.
; ---------------------------------------------------------------------------
macro multiply_shifted()
    stz !TMP+10                 ; how many of the two were negative
    bpl ?first
    eor #$FFFF
    inc a
    inc !TMP+10
?first:
    sta !TMP+0

    lda !TMP+2
    bpl ?second
    eor #$FFFF
    inc a
    inc !TMP+10
?second:
    sta !TMP+2

    jsl mul16

    lda !TMP+10
    lsr a                       ; the carry now holds the low bit of the count
    bcc ?positive

    lda !TMP+4                  ; one of the two was negative, so the product is
    eor #$FFFF
    clc
    adc #$0001
    sta !TMP+4
    lda !TMP+6
    eor #$FFFF
    adc #$0000
    sta !TMP+6

?positive:
    lda !TMP+4
    asl a                       ; bit fifteen of the low half into the carry,
    lda !TMP+6
    rol a                       ; then the high half doubled around it
endmacro

; ---------------------------------------------------------------------------
; A long pointer to one entry of a trig table, out of an angle in the accumulator.
;
; Each table is 65,536 entries of two bytes, which is 131,072 bytes, and a low
; addressed bank reaches 32,768. So each table is four consecutive banks, the
; angle's top two bits pick which, and the rest picks the entry inside it.
;
; The pointer lands in !G_ROW and the entry is read with `lda [!G_ROW],y` with Y
; at nought. Uses !TMP+0.
; ---------------------------------------------------------------------------
macro trig_pointer(table)
    sta !TMP+0

    and.w #$3FFF                ; where inside its own bank the angle sits
    asl a                       ; two bytes an entry
    clc
    adc.w #$8000                ; and a low addressed bank starts there
    sta !G_ROW+0

    lda !TMP+0
    xba                         ; the angle's high byte into the low half
    and.w #$00FF
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a                       ; which of the four banks this angle falls in
    clc
    adc.w #(<table>>>16)
    sta !G_ROW+2
endmacro

; ---------------------------------------------------------------------------
; The same, for the clamped cosine, whose four banks are not consecutive.
;
; The window the redirected accesses land in sits between the two pairs, so the
; upper half is one bank further along than counting would put it. Adding that
; one is the whole difference from the macro above.
; ---------------------------------------------------------------------------
macro clamped_pointer()
    sta !TMP+0

    and.w #$3FFF
    asl a
    clc
    adc.w #$8000
    sta !G_ROW+0

    lda !TMP+0
    xba
    and.w #$00FF
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a                       ; which of the four banks this angle falls in
    cmp.w #$0002
    bcc ?below
    inc a                       ; the upper pair sits past the window bank
?below:
    clc
    adc.w #(dsp1_clamped_cosine>>16)
    sta !G_ROW+2
endmacro

; ---------------------------------------------------------------------------
ground_state:
    ; The step, out of the part's own sine rather than out of a recorded table.
    ;
    ; Measured against the part across 676 keys spread over the whole word, and
    ; against all 1,193 rows the recorded table holds: the step is the sine of
    ; argument 6, with no exception anywhere. The sine table carries every angle
    ; a word can hold, so this cannot miss.
    ;
    ; It is the step that made the ground jump. The recorded table missed on 3%
    ; of the demo's frames, and a miss hands back the nearest key above the one
    ; asked for: at the worst frame measured that was $2b7e for a wanted $1e74,
    ; which is a step of $7021 where the part says $5702. The step is how far the
    ; ground moves per scanline, so a quarter of it is the whole picture landing
    ; somewhere else.
    lda.l !CARRY_02+12
    %trig_pointer(dsp1_sine_of)
    ldy #$0000
    lda [!G_ROW],y
    sta !G_STEP

    ; The horizon, the second mantissa and the second exponent, all three out of
    ; the one value $02 derives them from.
    ;
    ; asm/dsp1-derived.asm carries what that value is and why it is a table
    ; rather than the cosine: near and past a quarter turn the part holds it at a
    ; floor, and the floor has not been read out of the part's program. It does
    ; not need to be. The value depends on argument 6 alone, so every angle a
    ; word can hold was asked for and the answer cannot miss.
    ;
    ; Measured against the part across 737 angles spread over the whole word, all
    ; three are exact. The recorded table they replace missed on 3%, 21% and 3%
    ; of the demo's own frames.
    lda.l !CARRY_02+12
    %clamped_pointer()
    lda [!G_ROW],y
    sta !G_HELD

    ; The horizon is that value times argument 4, shifted down fifteen places.
    lda.l !CARRY_02+8           ; argument 4
    sta !TMP+2
    lda !G_HELD
    %multiply_shifted()
    sta !G_HORIZON

    ; The second mantissa and exponent are the normalise and the reciprocal of
    ; the same value, which is the chain every scanline already runs. The part's
    ; exponent there is the doubling count plus one, and %invert() leaves the
    ; count less six, so seven is the difference between them.
    lda !G_HELD
    %invert()
    lda !G_RA
    sta !G_MAN2
    lda !G_RB
    clc
    adc.w #$0007
    sta !G_EXP2

    ; The first scale, out of argument 2 and the part's own cosine.
    ;
    ; Measured against the part across 1,404 argument sets spanning both scales
    ; and the whole turn: the value behind the pair is argument 2 plus argument 3
    ; times the cosine of argument 6, shifted down fifteen places, and the pair
    ; is that value normalised with the exponent fifteen less the doublings.
    ;
    ; The cosine goes in one less than the table holds it wherever it is positive.
    ; That one is the part's own multiplier, not a correction: it was measured by
    ; asking the part with an argument of $8000, which turns the multiply into a
    ; negation and hands the multiplicand straight back.
    ;
    ; The sixteen sets that disagree are the ones where argument 2 plus the
    ; product overflows a signed word, which the part resolves in a way that has
    ; not been read out of its program. The recorded table this replaces answered
    ; the first mantissa wrongly on 39% of the demo's own frames.
    lda.l !CARRY_02+12
    %trig_pointer(dsp1_cosine_of)
    ldy #$0000
    lda [!G_ROW],y
    beq +
    bmi +
    dec a                       ; the part's multiplier hands back one less than
+                               ; the table holds, for a positive cosine
    sta !TMP+2
    lda.l !CARRY_02+6           ; argument 3
    %multiply_shifted()

    clc
    adc.l !CARRY_02+4           ; argument 2
    bne +

    ; The exponent is kept fifteen below what the part holds. Every scale
    ; subtracts that fifteen, twice a scanline, 352 times a frame of the game's
    ; clock; taken off once here it is never subtracted again. The second
    ; exponent is added to this one rather than to the part's, so the bias
    ; carries through the cascade untouched.
    stz !G_MAN1                 ; the part answers a pair of noughts for nought
    lda.w #$FFF1                ; which is nought less the fifteen
    sta !G_EXP1
    bra ++
+
    %normalise()
    sta !G_MAN1
    lda.w #$0000
    sec
    sbc !G_COUNT
    sta !G_EXP1
++

    ; The matrix, out of the part's own sine and cosine rather than out of a
    ; table of what a recording happened to ask for.
    ;
    ; Measured across all 3,302 rows the recorded table holds: the first word is
    ; the cosine of argument 5 and the second is its sine negated, with no
    ; exception. Those two tables carry every angle a word can hold, so this
    ; cannot miss. The recorded table missed on 11% of the demo's own frames,
    ; and a miss there is not a small error: the search hands back the nearest
    ; angle above the one asked for, which at the worst frame measured was
    ; $732c in place of $5b0c. That is the ground drawn at a heading nobody
    ; asked for, for as long as the miss lasts, and it is what made the scenery
    ; jump and come back.
    ;
    ; Each trig table is 65,536 entries of two bytes, which is four low
    ; addressed banks, so the angle's top two bits pick the bank and the rest
    ; picks the entry inside it.
    lda.l !CARRY_02+10
    %trig_pointer(dsp1_cosine_of)
    ldy #$0000
    lda [!G_ROW],y              ; the cosine, which the part holds at $7f
    sta !G_MAT+0
    sta !G_MAT+6                ; and again at $6e

    lda.l !CARRY_02+10
    %trig_pointer(dsp1_sine_of)
    lda [!G_ROW],y
    eor #$FFFF                  ; the part holds the sine negated at $7e
    inc a
    sta !G_MAT+2
    eor #$FFFF                  ; and plain at $6f
    inc a
    sta !G_MAT+4

    jsr ground_tables
    rts

; ---------------------------------------------------------------------------
; One table: the constant times nought, then times one, and so on to 255.
;
; Additions rather than multiplies, which is the whole point: 256 of them build
; what 256 multiplies would, and the six uses on each of 176 scanlines then cost
; no multiply at all.
;
; The sum is stored before it moves on, so entry nought is nought.
;
; ===========================================================================
; WHY THIS IS A MACRO RATHER THAN A ROUTINE
; ===========================================================================
;
; It used to take the table as a pointer in the direct page and store through
; it. Storing through a pointer means reading the pointer first, and the direct
; page is the console's own memory, so each of the two stores an entry needs
; fetched three bytes from the slow half of the machine before writing two.
;
; Naming the table when this is assembled makes the store a plain indexed one.
; The price is the loop written out once per table, which the assembler does.
;
; The sum's low half also moves on the moment it has been stored rather than
; after the high half has been, which saves reloading both. The carry the
; addition leaves is what the high half needs, and nothing between the two
; touches it: a load does not, and neither does a store.
;
; In:  !TMP+0 the constant.
; Out: the named table filled. Uses X and !TMP+6 to !TMP+11.
; ---------------------------------------------------------------------------
macro build_table(table)
    lda !TMP+0
    bpl ?positive
    lda #$FFFF                  ; the constant's sign, for the high half of the
    bra ?signed                 ; running sum to carry
?positive:
    lda #$0000
?signed:
    sta !TMP+6

    ; Twice the constant, so an entry holds twice the product and the high half
    ; of it is the product already shifted down fifteen places. That shift was
    ; five instructions after every one of the six multiplies a scanline; now it
    ; is one instruction here, once per rebuild.
    ;
    ; Doubling a value that is already sign extended across the pair leaves the
    ; sign word alone: the bit the low half loses off the top is the one the high
    ; half's own doubling brings back in, and for a negative constant both are
    ; ones.
    asl !TMP+0

    ; The sum's high half lives in the index register. The direct page is the
    ; console's own memory and it answers more slowly than the cartridge, so an
    ; entry that read and wrote both halves there paid four times for it; this
    ; one pays twice.
    ;
    ; Sixteen entries a turn, because advancing the index and testing the loop
    ; were a third of what an entry cost when they were paid once an entry.
    ;
    ; The carry the low half's addition leaves is what the high half's needs, and
    ; neither a store nor a transfer between registers touches it.
    lda #$0000
    tay
    ldx #$0000
?turn:
    sta.l <table>+1,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+3,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+9,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+11,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+17,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+19,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+25,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+27,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+33,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+35,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+41,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+43,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+49,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+51,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+57,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+59,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+65,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+67,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+73,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+75,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+81,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+83,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+89,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+91,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+97,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+99,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+105,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+107,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+113,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+115,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta.l <table>+121,x
    clc
    adc !TMP+0
    sta !TMP+8
    tya
    sta.l <table>+123,x
    adc !TMP+6
    tay
    lda !TMP+8

    sta !TMP+8                  ; a hundred and twenty eight bytes a turn, which
    txa                         ; is sixteen entries of eight
    clc
    adc #$0080
    tax
    lda !TMP+8
    cpx.w #!MULSPAN
    bcs ?filled
    jmp ?turn
?filled:
endmacro

; ---------------------------------------------------------------------------
; The four tables the six multiplies read, rebuilt when their constant moves.
;
; A table is 256 entries of five bytes: a nought, then the constant times the
; entry number as thirty two bits. The nought is what lets the same entry answer
; both halves of a multiply, and it never changes, so it is written once ever
; rather than on every rebuild.
;
; Two of the four come from the scale table and two from the matrix table, and
; those two searches are keyed on different arguments, so the pairs are checked
; separately. Across the recording the matrix key repeats from one frame to the
; next 54% of the time and the scale keys 52%, so about half the rebuilds do not
; happen.
;
; !G_AGAIN is a word rather than a flag because the memory it sits in is the
; game's own and starts as whatever the console powered up with. A flag would
; read as set about half the time.
; ---------------------------------------------------------------------------
!MULREADY = $A57E               ; what !G_AGAIN holds once the noughts are in

ground_tables:
    lda !G_AGAIN
    cmp.w #!MULREADY
    beq .padded

    ; The noughts, one per entry across all four tables, and never again.
    ;
    ; Five increments rather than an addition, because an addition needs the
    ; accumulator and the accumulator is holding the nought being written.
    sep #$20
    lda #$00
    ldx.w #$0000
-
    sta.l !MULTAB,x
    inx
    inx
    inx
    inx
    inx
    inx
    inx
    inx
    cpx.w #(!MULSPAN*!MULTABS)
    bcc -
    rep #$20

    lda.w #!MULREADY
    sta !G_AGAIN
    ; Nothing built yet, so no check below may match what it is about to be
    ; given. Each is set to the complement of the constant it guards, which no
    ; value can equal. A pair of constants that could not both be some fixed pair
    ; was enough while the tables were checked in pairs; checked one at a time,
    ; a sine of nought would have matched a nought held here.
    lda !G_MAT+0
    eor #$FFFF
    sta !G_LAST+0
    lda !G_MAT+2
    eor #$FFFF
    sta !G_LAST+2
    lda !G_MAN1
    eor #$FFFF
    sta !G_LAST+4
    lda !G_MAN2
    eor #$FFFF
    sta !G_LAST+6

.padded:
    ; Each table is checked on its own constant rather than in pairs. The two
    ; halves of a pair used to move together, when the constants came out of a
    ; table recorded from playthroughs and a whole row changed at once. They are
    ; computed now, and measured over 595 frame steps of the demo they move
    ; apart: 59%, 59%, 89% and 56%. Checking them in pairs rebuilds 2.978 tables
    ; a frame where checking them one at a time rebuilds 2.639.
    ;
    ; The branch over a build has to be a jump, because a build is sixteen
    ; entries written out and far too long to reach with one.
    lda !G_MAT+0
    cmp !G_LAST+0
    bne .cosine
    jmp .after_cosine
.cosine:
    sta !G_LAST+0
    sta !TMP+0
    %build_table(!MULTAB0)
.after_cosine:

    lda !G_MAT+2
    cmp !G_LAST+2
    bne .sine
    jmp .after_sine
.sine:
    sta !G_LAST+2
    sta !TMP+0
    %build_table(!MULTAB1)
.after_sine:

    lda !G_MAN1
    cmp !G_LAST+4
    bne .first
    jmp .after_first
.first:
    sta !G_LAST+4
    sta !TMP+0
    %build_table(!MULTAB2)
.after_first:

    lda !G_MAN2
    cmp !G_LAST+6
    bne .second
    jmp .after_second
.second:
    sta !G_LAST+6
    sta !TMP+0
    %build_table(!MULTAB3)
.after_second:

.done:
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
    ; The data bank points at the multiply tables rather than at bank zero. A
    ; read of a table is then an absolute one, which is a cycle cheaper than a
    ; long one, and there are twenty four of them a scanline. The index is a byte
    ; times eight, so it never reaches 253 within a page and the crossing penalty
    ; an absolute read can carry is never paid.
    ;
    ; The two buffers stay reachable: the first 8 KiB of bank $7e is the same
    ; memory as the bottom of bank zero, and both of them live there.
    lda.w #(!MULTAB>>8)&$FF00
    pha
    plb
    plb

    jsr ground_state

    lda.l !PORT_LINE            ; the one argument $0a takes is the first line,
    sta !G_LINE                 ; which dsp_route_0a works out and keeps, because
                                ; the game writes it through the window and the
                                ; port never sees it
    jsr ground_seed

    ; The first scanline has no previous one to copy from, so the distance it is
    ; about to compute is stored complemented, which nothing can match.
    ; The running sum is kept at twice what the part holds it at, so its high
    ; half is the whole thirty two bit value shifted down fifteen places and the
    ; distance is a load and an add rather than a load, a shift, a load and a
    ; rotate. The step it advances by is doubled to match.
    ;
    ; The step itself cannot be doubled where it is read, because ground_seed
    ; takes its magnitude and a step of $7fff doubled is a word that reads as
    ; minus two. So the doubling happens here, after the seed has used it.
    asl !G_ACC+0
    rol !G_ACC+2
    lda !G_STEP
    asl a
    sta !G_STEP2

    lda !G_ACC+2
    clc
    adc !G_HORIZON
    eor #$FFFF
    sta !G_SEEN

    stz !G_RAPAD                ; the nought above each multiply's high byte
    stz !G_MAPAD
    stz !G_S1PAD
    stz !G_S2PAD

    ; Y is where in the two buffers this scanline goes, and it is also the loop's
    ; counter. ground_line writes through it and leaves it alone, so nothing has
    ; to be parked in the direct page and fetched back a scanline later.
    ldy #$0000

ground_turn:                    ; a plain label rather than a local one: the
                                ; scanline written out below carries labels of
                                ; its own, and a local one would attach to the
                                ; last of those instead of to this loop
    %line(1)                    ; written out here rather than called: the loop
                                ; has nothing to do between the call and the
                                ; return, and they were twelve cycles a scanline.
                                ; ground_answer still calls it, once

    iny                         ; four bytes a scanline, two words in each buffer
    iny
    iny
    iny
    cpy.w #(!STREAM_TURNS*4)
    beq +                       ; the scanline is too long to branch back over
    jmp ground_turn
+

    tya                         ; what the original loop's own index reached
    tax
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
    phb
    rep #$30

    lda.w #(!MULTAB>>8)&$FF00   ; the multiply tables, as ground_block does, so
    pha                         ; the reads inside ground_line are absolute
    plb
    plb

    jsr ground_state

    lda !ARG+0
    sta !G_LINE
    jsr ground_seed

    ldy #$0000                  ; ground_line writes into the two buffers, so the
    jsr ground_line             ; first entry of each is where this one lands.
                                ; ground_block rewrites every entry from the
                                ; first on every call, so nothing reads what is
                                ; left here
    lda.w !STREAM_ONE+0
    sta.l !OUT+0
    lda.w !STREAM_ONE+2
    sta.l !OUT+2
    lda.w !STREAM_TWO+0
    sta.l !OUT+4
    lda.w !STREAM_TWO+2
    sta.l !OUT+6

    plb
    plp
    rtl
