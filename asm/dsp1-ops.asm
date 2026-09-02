; Pilotwings without the DSP-1: the commands whose arithmetic is fully known.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; One routine per command the cartridge sends the chip. Each was read out of the
; chip's own program with microcode.py, then checked by driving the real chip on
; random inputs and comparing. A routine only appears here once that check
; passes on every input tried; the commands still being read sit in
; OPEN-QUESTIONS.md rather than half-written here.
;
;   $00   ((a * b) >> 15), kept to 16 bits      400 of 400 random inputs exact
;   $08   twice (x*x + y*y + z*z), 32 bits      400 of 400 random inputs exact
;   $04   magnitude times sine and cosine       400 of 400 random inputs exact
;
; $04 reads the tables in dsp1-derived.asm, which are the chip's own answers
; rather than a formula. Everything else here is arithmetic.
;
; ===========================================================================
; WHY THE SHIFT IS 15 AND NOT 16
; ===========================================================================
;
; The chip's multiplier is fractional. It treats its two inputs as fractions of
; 32768 rather than as counts, so the 32-bit product it forms is already
; doubled relative to a plain integer multiply, and the word it hands back is
; bits 30 down to 15 rather than 31 down to 16.
;
; That is the whole of why $00 shifts by 15, and the whole of why $08 answers
; twice the sum of squares rather than the sum. Both were confirmed against the
; chip rather than reasoned about: $00 on 4660 x 4660 answers 662, which is
; 21,715,600 >> 15 and not >> 16.
;
; One input saturates. -32768 x -32768 is 2^30, so >> 15 is 32768, which does
; not fit a signed word. The chip hands back -32768, which is those same bits
; read as signed. So the routine keeps the low 16 bits and does not clamp:
; clamping to 32767 would be more correct and would not be what the chip does.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
; The SNES processor is a 65816. It has three working registers: A, the
; accumulator, where arithmetic happens; and X and Y, mostly used for counting
; and for pointing at things. Each can hold 8 or 16 bits, and which one is a
; mode the program switches.
;
;   rep #$30        Switch A, X and Y to 16 bits. "rep" clears mode bits; $30
;                   is the two bits that select 8-bit A and 8-bit X/Y, so
;                   clearing them selects 16.
;   sep #$20        Switch A back to 8 bits. "sep" sets those same bits.
;
;   lda $10         Load A from address $10. A one-byte address like this is
;                   the "direct page", the fastest memory the processor has:
;                   one byte in the instruction and one cycle less than a full
;                   address. Everything here uses it for working values.
;   sta $10         Store A to address $10.
;   ldx / stx       The same for X.
;
;   clc / sec       Clear or set the carry flag before adding or subtracting.
;                   The 65816 has no add-without-carry, so clc before adc is
;                   not optional, and sec before sbc is not either.
;   adc / sbc       Add or subtract, with carry.
;   asl / lsr       Shift left or right by one bit.
;   rol / ror       Rotate left or right through the carry, which is how a
;                   shift is carried from one word into the next.
;   eor #$FFFF      Flip every bit. With an inc after it, that negates.
;
;   bpl / bmi       Branch if the last result was positive or negative.
;   bcc / bcs       Branch if carry clear or set.
;   rtl             Return from a routine that was called across banks.
;
;   sta $004202     A full address. $4202 and $4203 are the console's hardware
;                   multiplier: write one byte to each and the 16-bit product
;                   appears at $4216 eight cycles later.
;
; ===========================================================================
; ONE ASSEMBLER TRAP, WRITTEN DOWN BECAUSE IT COST AN AFTERNOON
; ===========================================================================
;
; The assembler does not track which width A is in. It decides how wide an
; immediate is from how many digits were typed:
;
;     lda #$00      two digits, assembles an 8-bit immediate
;     lda #$0000    four digits, assembles a 16-bit immediate
;
; So writing "lda #0" while A is 16 bits emits a two-byte instruction where the
; processor will read three. Everything after it is then read at the wrong
; offset, and the routine runs into whatever the shifted bytes happen to spell.
; It does not fail where the mistake is, and it does not look wrong in the
; source.
;
; That is what made these routines return zeroes: one "lda #0" and one "adc #0"
; inside a 16-bit stretch. Every immediate below is therefore written to the
; width the register is in at that point, four digits for 16 and two for 8, and
; the two-digit ones are only ever the arguments to rep and sep, which are
; always 8 bits wide whatever the mode.
;
; ===========================================================================
; WHERE THE ARGUMENTS ARE
; ===========================================================================
;
; Each routine takes its arguments in the direct page and leaves its answer
; there. The caller puts the words the cartridge wrote at !ARG and reads the
; answer from !OUT. Direct page is used rather than the stack because it is the
; only memory the 65816 reaches in two cycles, and these run inside a frame the
; game has already spent.
; ===========================================================================

!ARG = $00                      ; first argument word, then $02, $04, ...
!OUT = $10                      ; first answer word, then $12
!TMP  = $20                     ; scratch, seven words
!PAIR = $40                     ; the two words op_00_body multiplies

!MULA   = $004202               ; hardware multiplier, first operand
!MULB   = $004203               ; hardware multiplier, second operand, starts it
!MULRES = $004216               ; the 16-bit product, ready 8 cycles later

; ---------------------------------------------------------------------------
; A 16 x 16 unsigned multiply, giving 32 bits.
;
; The console multiplies 8 bits by 8 unsigned, so a 16 by 16 is four of those
; added at their own weights:
;
;     (ah*256 + al) * (bh*256 + bl)
;   =  al*bl  +  (al*bh + ah*bl)*256  +  ah*bh*65536
;
; The four partial products are formed in the order that lets each one be
; started before the previous is read, so the eight cycle wait for one overlaps
; the setup of the next. That is why the writes and reads are interleaved rather
; than grouped.
;
; In:  !TMP+0 and !TMP+2, both 16 bits, unsigned.
; Out: !TMP+4 low word, !TMP+6 high word.
; Scratch: !TMP+8 and !TMP+12.
; Uses A only. The multiplier registers are 8-bit, so A is 8 bits while an
; operand is being handed over and 16 while a product is being taken back.
; ---------------------------------------------------------------------------
mul16:
    php                         ; remember the caller's register widths
    sep #$20                    ; A to 8 bits: the multiplier wants bytes

    lda !TMP+0                  ; low byte of the first operand
    sta !MULA
    lda !TMP+2                  ; low byte of the second
    sta !MULB                   ; this write starts the multiply
    nop                         ; eight cycles must pass before the result is
    nop                         ; ready; four two-cycle nops is the cheapest
    nop                         ; way to spend them, and cheaper than any
    nop                         ; loop or branch would be
    rep #$20                    ; A to 16 bits to take the whole product
    lda !MULRES
    sta !TMP+4                  ; al*bl, the lowest partial

    sep #$20
    lda !TMP+1                  ; high byte of the first operand
    sta !MULA
    lda !TMP+2                  ; low byte of the second
    sta !MULB
    nop
    nop
    nop
    nop
    rep #$20
    lda !MULRES
    sta !TMP+6                  ; ah*bl, weight 256

    sep #$20
    lda !TMP+0
    sta !MULA
    lda !TMP+3                  ; high byte of the second operand
    sta !MULB
    nop
    nop
    nop
    nop
    rep #$20
    lda !MULRES
    clc
    adc !TMP+6
    sta !TMP+6                  ; al*bh added in at the same weight

    ; That sum can be seventeen bits: two partials of up to $FE01 each reach
    ; $1FC02. The seventeenth bit sits at weight 256 within a word that is
    ; itself at weight 256, so it belongs in the high word as $0100. Dropping
    ; it is what made the high word wrong on large operands while the low word
    ; stayed right.
    lda #$0000
    adc #$0000                  ; 1 if that sum carried, 0 if not
    xba                         ; move it to the high byte, so it means $0100
    sta !TMP+12

    sep #$20
    lda !TMP+1
    sta !MULA
    lda !TMP+3
    sta !MULB
    nop
    nop
    nop
    nop
    rep #$20
    lda !MULRES
    clc
    adc !TMP+12                 ; the middle sum's seventeenth bit
    sta !TMP+8                  ; ah*bh, weight 65536, held for the fold below

    ; Fold the middle partials, which sit at weight 256, into the 32-bit sum.
    ; Their low byte belongs in the high half of the low word and their high
    ; byte in the low half of the high word, so the pair is split by hand.
    lda !TMP+6
    and #$00FF
    xba                         ; move that byte into the high half
    clc
    adc !TMP+4
    sta !TMP+4                  ; low word complete
    lda !TMP+6
    xba
    and #$00FF
    adc !TMP+8                  ; carry from the line above is wanted here
    sta !TMP+6                  ; high word complete

    plp                         ; restore the caller's widths
    rtl

; ---------------------------------------------------------------------------
; $00: the signed fractional product, ((a * b) >> 15) kept to 16 bits.
;
; The multiply above is unsigned, so the sign is handled around it rather than
; inside it: each operand is made positive, the product is formed, and the whole
; 32-bit result is negated once if exactly one operand was negative.
;
; The other way round is to multiply the operands as they stand and then correct
; the high word by subtracting each operand once for the other's sign. That is
; two instructions shorter and it is what this did first. It was wrong on two
; inputs in sixty, both with both operands negative, and the reason was not
; visible in the source. Making the signs explicit costs four cycles on the
; negative paths and nothing on the positive ones.
;
; The >> 15 is a shift of the 32-bit result right by fifteen, done as a shift
; left by one and a take of the high word: two instructions rather than thirty.
;
; In:  !ARG+0, !ARG+2.
; Out: !OUT+0.
; ---------------------------------------------------------------------------
op_00:
    php
    rep #$30

    lda !ARG+0                  ; the two words this command was given
    sta !PAIR+0
    lda !ARG+2
    sta !PAIR+2
    jsl op_00_body
    sta !OUT+0

    plp
    rtl

; The same arithmetic, reachable on its own, because $04 wants it twice with
; operands of its own choosing. Takes !PAIR+0 and !PAIR+2, leaves the answer in
; A, and expects the caller to be in sixteen bit mode already.
op_00_body:
    stz !TMP+10                 ; how many operands were negative

    lda !PAIR+0
    bpl +
    eor #$FFFF                  ; negate: flip every bit, then add one
    inc a
    inc !TMP+10
+
    sta !TMP+0

    lda !PAIR+2
    bpl +
    eor #$FFFF
    inc a
    inc !TMP+10
+
    sta !TMP+2

    jsl mul16                   ; 32-bit product of the two magnitudes

    lda !TMP+10
    lsr a                       ; carry now holds the low bit of the count
    bcc +                       ; even count: both or neither were negative

    lda !TMP+4                  ; negate the whole 32-bit product
    eor #$FFFF
    clc
    adc #$0001
    sta !TMP+4
    lda !TMP+6
    eor #$FFFF
    adc #$0000                  ; carry out of the low half lands here
    sta !TMP+6
+
    asl !TMP+4                  ; shift the pair left one, keep the high word
    rol !TMP+6
    lda !TMP+6
    rtl

; ---------------------------------------------------------------------------
; $08: twice the sum of three squares, as 32 bits, low word first.
;
; Each operand is made positive before it is squared. This first did not, on the
; reasoning that a square is never negative so the sign cannot matter, and that
; reasoning is wrong. Reading a negative operand as unsigned adds 65536 to it,
; and squaring what that gives is
;
;     (a + 65536)^2  =  a^2 + 131072*a + 65536^2
;
; The last term falls off the end of 32 bits and the middle one does not, so the
; answer is out by 131072*a. The low word survives that, which is why the fault
; showed only in the high word and only on negative operands.
;
; Written out three times rather than looped. Three passes of a loop cost an
; index, two increments, a compare and a branch per pass and save nothing.
;
; The doubling at the end is the multiplier's fractional shift, the same one
; that makes $00 shift by fifteen. One shift of the total, not three of the
; squares.
;
; In:  !ARG+0, !ARG+2, !ARG+4.
; Out: !OUT+0 low word, !OUT+2 high word.
; ---------------------------------------------------------------------------

; Square the word at the given offset into !TMP+4 and !TMP+6, magnitude first.
macro square(source)
    lda <source>
    bpl ?positive
    eor #$FFFF                  ; negate, so the square is of the magnitude
    inc a
?positive:
    sta !TMP+0
    sta !TMP+2                  ; both operands the same squares it
    jsl mul16
endmacro

op_08:
    php
    rep #$30

    %square(!ARG+0)             ; first square starts the running total
    lda !TMP+4
    sta !OUT+0
    lda !TMP+6
    sta !OUT+2

    %square(!ARG+2)             ; second
    lda !OUT+0
    clc
    adc !TMP+4
    sta !OUT+0
    lda !OUT+2
    adc !TMP+6
    sta !OUT+2

    %square(!ARG+4)             ; third
    lda !OUT+0
    clc
    adc !TMP+4
    sta !OUT+0
    lda !OUT+2
    adc !TMP+6
    sta !OUT+2

    asl !OUT+0                  ; the multiplier's doubling, once for the sum
    rol !OUT+2

    plp
    rtl

; ---------------------------------------------------------------------------
; $04: a magnitude turned through an angle, as a pair.
;
; Answers the magnitude times the sine of the angle, then the magnitude times
; the cosine. The angle is a whole turn per 65,536, so it indexes the tables
; with nothing done to it beyond doubling for the entry width.
;
; The sine and cosine come from dsp1-derived.asm, which holds what the chip
; multiplies by rather than what it returns: asked with a magnitude of $7FFF
; the chip answers one short of the value it used internally, so a table built
; from its answers would be one out on almost every input. The generator
; recovers the internal value by asking with six magnitudes and keeping the one
; that explains them all.
;
; The multiply is the same fractional one $00 answers with, so this reuses
; op_00's body rather than repeating it: put the two words in place and call.
;
; In:  !ARG+0 the angle, !ARG+2 the magnitude.
; Out: !OUT+0 the first half, !OUT+2 the second.
; ---------------------------------------------------------------------------

; Index a table of words by a value already in A, leaving the entry in A.
;
; A table is 131,072 bytes and a bank holds 32,768, so it sits as four pieces in
; four consecutive banks and the piece has to be chosen. The top two bits of the
; index say which, the low fourteen say where inside it, and doubling turns an
; entry number into a byte offset.
;
; Written as four branches rather than a computed bank byte because a computed
; one needs the address assembled into memory and read back through a pointer,
; which is eight cycles a lookup against at most three here, and this runs twice
; per $04 and will run far more often than that once $01 uses it.
macro entry(table)
    pha
    and #$3FFF                  ; where inside the piece
    asl a                       ; two bytes an entry
    tax
    pla
    xba                         ; the high byte down into the low half
    and #$00C0                  ; the two bits that choose the piece
    beq ?first
    cmp #$0040
    beq ?second
    cmp #$0080
    beq ?third
    lda.l <table>+$030000,x
    bra ?done
?third:
    lda.l <table>+$020000,x
    bra ?done
?second:
    lda.l <table>+$010000,x
    bra ?done
?first:
    lda.l <table>,x
?done:
endmacro

op_04:
    php
    rep #$30

    lda !ARG+0                  ; the first half
    %entry(dsp1_sine_of)
    sta !PAIR+0                 ; stand it in as the multiply's first operand
    lda !ARG+2
    sta !PAIR+2
    jsl op_00_body
    sta !OUT+0

    lda !ARG+0                  ; the second half, the same way
    %entry(dsp1_cosine_of)
    sta !PAIR+0
    lda !ARG+2
    sta !PAIR+2
    jsl op_00_body
    sta !OUT+2

    plp
    rtl
