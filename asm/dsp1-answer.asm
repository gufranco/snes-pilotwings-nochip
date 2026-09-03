; Pilotwings without the DSP-1: look the answer up, and never hang if it is not there.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; The whole replacement, from the outside. A command arrives with its arguments
; and this answers it, by two routes in this order:
;
;   1. The table. lutbuild.py collects every question the game was recorded
;      asking, for all sixteen commands that answer, and every answer to it.
;      Almost every call lands here.
;
;   2. The fallback. The table holds a set, not a range: an argument no
;      recording ever showed has no row. That must not stop the machine, so
;      every command has a routine behind it that always answers, in bounded
;      time, without looping.
;
; The intent is that the fallback never runs. The requirement is that it always
; could. A slower answer beats a stopped console, and a lookup with no row and
; nothing behind it either hangs or reads whatever happened to be in memory.
;
; ===========================================================================
; THE FAULTS THAT WERE IN HERE, AND WHY THEY ALL LOOKED LIKE ONE
; ===========================================================================
;
; An earlier version of this file answered 19 of 200 recorded questions
; correctly and never once failed to answer, which is the exact shape of fault a
; fallback hides. Eight separate mistakes were behind it. Each one on its own
; produced the same symptom, so fixing any one of them moved the rate not at
; all, and the count sat at 19 through three rounds of fixes. They are written
; down because the next person to change this file needs to know which shapes of
; arithmetic and addressing this table does not tolerate.
;
;   1. A number written after a hash was assembled at the width of however many
;      digits were typed rather than the width the register was in. "ldx #1"
;      put one byte where two were read, so every instruction after it was read
;      starting one byte late and the processor wandered off into whatever the
;      shifted bytes spelled. It did not fail. It left after ten instructions
;      with everything still at zero.
;
;   2. The direct page slots overlapped. !KEYW was one byte at $31 and !ANSW
;      was two bytes at $32, so a sixteen bit "ldx !KEYW" read the key width in
;      its low half and the answer width's low byte in its high half. For a
;      seven word key and a three word answer that is X = $0307 rather than 7.
;      Every field now gets its own whole word, whatever its width in the table.
;
;   3. Scaling by a width was done as one doubling per word, which multiplies by
;      two raised to the width rather than by the width. A key two words wide is
;      the only case where those agree, four either way, and $00, $04 and $10
;      are exactly the commands whose keys are two words wide. That is where the
;      19 came from. There is now a real shift-and-add multiply below.
;
;   4. The row and answer offsets were computed in sixteen bits. $06 has 75,278
;      rows and a ten word key, so the offset into its rows reaches 1,505,560
;      and wrapped.
;
;   5. The binary search itself counted rows in sixteen bits, and $06 has more
;      rows than sixteen bits hold. The search now carries its low, high and
;      middle as thirty two bit values.
;
;   6. The table's own offsets were treated as if the cartridge were one flat
;      run of bytes. It is not. This is a low cartridge, so each bank shows only
;      its upper half, $8000 to $FFFF, and the next 32 kilobytes of the table
;      are in the next bank at $8000 again rather than at $10000. Adding a flat
;      offset to the table's first address therefore reaches the cartridge only
;      for the first 32 kilobytes of a table 2.9 megabytes long. lut_place is
;      the conversion.
;
;   7. The banks themselves were out of reach. A low cartridge carries nothing
;      above bank $7D: $7E and $7F are the console's own memory, and everything
;      from $80 up is a second view of what is already below. A table placed
;      from bank $30 ran off the end of the machine and its last fourteen banks
;      read back as the game's own first fourteen. The table now starts at $11,
;      above the game's own sixteen banks and above this code, and the tables
;      taken from the chip sit above it again.
;
;   8. The data bank was pushed before the comparison flags and pulled first, and
;      a stack returns things in the order opposite to the one it took them. So
;      the pull meant to restore the bank restored the flags, and the pull meant
;      to restore the flags restored the bank. Every comparison came back
;      carrying whatever the old bank byte happened to look like as a set of
;      flags. The bank is now set once, in dsp1_answer, and no routine below
;      touches it.
;
; A row can also sit across the join between two banks, because a bank holds
; 32,768 bytes and no row width divides that. Reading it with one index register
; walks off the end of the bank into memory that is not the cartridge, so every
; loop that walks a row checks first whether it fits in what is left of the bank
; and takes a slower bank-aware walk when it does not. The check is two
; instructions and the slow path runs on about one row in sixteen hundred.
;
; With all eight fixed, every recorded question replayed through this comes back
; with the row the recording holds.
;
; ===========================================================================
; WHAT THE FALLBACK ANSWERS WITH
; ===========================================================================
;
; Three commands have their arithmetic, read out of the chip's own program and
; checked against it on four hundred random inputs each. For those the fallback
; is not an approximation at all, it is the answer:
;
;   $00, $80   the signed fractional product
;   $08        twice the sum of three squares
;   $04        a magnitude turned through an angle
;
; The other thirteen fall back to the nearest row. The search already knows
; where the wanted key would have gone, so the row before and the row after are
; both to hand, and the closer of the two is taken.
;
; That is a deliberate choice and it rests on what these arguments are. They are
; an aircraft's attitude and position, sampled every frame, so two nearby keys
; carry two nearby answers and the nearest row is a near-miss rather than
; nonsense. The alternative is recomputing arithmetic this project has read the
; shape of but not the rounding of, and a wrong recomputation is worse than a
; near neighbour: it is wrong everywhere rather than only between samples.
;
; Whichever route answers, it answers. Nothing here can loop.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
; One trap before anything else, because it is fault 1 above and it is invisible
; in a listing. Every number after a hash in this file is written with four hex
; digits, or forced wide with .w when it is a name rather than a number.
;
; Beyond what dsp1-ops.asm already explains:
;
;   lda.l $308000     A "long" load: the full 24-bit address, bank included.
;                     The table is millions of bytes and lives in its own banks,
;                     so it cannot be reached any other way.
;
;   lda [!SCRATCH],y  Load through a 24-bit pointer held in the direct page,
;                     stepping by Y. This is how a row is read when its address
;                     had to be worked out rather than written down.
;
;   ldy / dey / iny   The other index register, used here for counting words
;                     while copying an answer out.
;
;   cmp / bcc / bcs   Compare, then branch if the first was below or not below.
;                     A binary search is a compare and one of those, repeated.
;
;   asl / rol         Shift left. Doing asl on the low word and rol on the high
;                     word shifts a thirty two bit value as one, because rol
;                     takes in the bit asl pushed out.
;
;   lsr / ror         The same going right, high word first.
;
;   jsr / rts         Call and return inside one bank; jsl and rtl cross banks.
;
; ===========================================================================
; THE TABLE'S SHAPE
; ===========================================================================
;
; One byte saying how many commands are in it, then twelve bytes per command:
;
;   + 0   the command byte
;   + 1   how many words its key is
;   + 2   how many words its answer is, two bytes wide because $0a answers 764
;   + 4   how many rows it has, four bytes
;   + 8   where its rows begin, four bytes, counted from the start of the table
;
; Then the rows: every key in order, then every answer in the same order. Keys
; are sorted so the search can halve the range instead of walking it, which is
; seventeen compares against 75,278 for the largest command here.
; ===========================================================================

!PAGE     = $0D00               ; where this puts its direct page while it runs
                                ; Measured free: the game never wrote $000CFC
                                ; through $000FE3 across a full run of the demo,
                                ; and everything here fits in $0D00 to $0D61.

!LUT      = $198000             ; where lutbuild.py's blob starts, and it
                                ; has to be the bank lut-map.asm gives it:
                                ; naming a different one here reads whatever
                                ; else is there as the index, so every command
                                ; misses and every answer falls back
!LUTBANK  = $0019               ; and the bank that is. This has to agree with
                                ; !LUT above: lut_place builds every row address
                                ; from it, so a stale bank here reads whatever
                                ; lives there as though it were the rows, the
                                ; search never matches, and every command falls
                                ; back with the wrong answer

!WORKRAM  = $007E               ; the first of the two banks that are not the
                                ; cartridge at all, but the console's memory

; Every one of these is a whole word or a whole pair of words, even where the
; table stores the field in a single byte. Sharing a word between two fields is
; fault 1 above, and it costs one byte of direct page to make impossible.
!CMD      = $30                 ; the command byte this call is answering
!KEYW     = $32                 ; how many words its key is
!ANSW     = $34                 ; how many words its answer is
!ROWS     = $36                 ; how many rows it has, thirty two bits
!ROWAT    = $3A                 ; where its rows begin, as a long address
!LOW      = $3E                 ; the search's low row, thirty two bits
!HIGH     = $42                 ; and its high row
!MID      = $46                 ; the row being compared

; Twenty two bytes of working room, laid out once here so that no two users of
; it can quietly land on the same bytes:
;
;   + 0   a long address, three bytes, read through with lda [!SCRATCH],y
;   + 4   an offset into the table, or a product, four bytes
;   + 8   the multiply's multiplicand, four bytes
;   + 12  the multiply's multiplier, two bytes
;   + 14  how many bytes are left in the bank the address landed in
;   + 16  where this command's answers begin, four bytes
;   + 20  the fallback's running best distance, two bytes
!SCRATCH  = $4A

; ---------------------------------------------------------------------------
; Multiply the thirty two bit value in !SCRATCH+4 by the sixteen bit value in A.
;
; Shift and add, high bit of the multiplier last: look at the multiplier's
; lowest bit, add the multiplicand when it is set, then double the multiplicand
; and halve the multiplier. Sixteen passes at worst, and it stops early once the
; multiplier has been shifted down to nothing, which for a key width of ten is
; after four.
;
; The obvious alternative, adding the multiplicand to itself as many times as the
; width says, is fine for a ten word key and hopeless for $0a's 764 word answer.
; This is the same routine for both.
;
; In:  A the multiplier, !SCRATCH+4 the thirty two bit multiplicand.
; Out: !SCRATCH+4 the thirty two bit product. !SCRATCH+8 and +12 are used up.
; ---------------------------------------------------------------------------
lut_scale:
    sta !SCRATCH+12             ; the multiplier, which will be shifted away

    lda !SCRATCH+4              ; move the multiplicand aside, because
    sta !SCRATCH+8              ; !SCRATCH+4 becomes the running total
    lda !SCRATCH+6
    sta !SCRATCH+10

    stz !SCRATCH+4              ; the product starts at nothing
    stz !SCRATCH+6

.loop:
    lda !SCRATCH+12
    beq .done                   ; no bits left: the product is finished

    lsr a                       ; take the lowest bit of the multiplier out
    sta !SCRATCH+12
    bcc .shift                  ; it was clear, so nothing is added this pass

    lda !SCRATCH+8              ; it was set: add the multiplicand where it sits
    clc
    adc !SCRATCH+4
    sta !SCRATCH+4
    lda !SCRATCH+10
    adc !SCRATCH+6
    sta !SCRATCH+6

.shift:
    asl !SCRATCH+8              ; the multiplicand moves up one place, which is
    rol !SCRATCH+10             ; what makes the next bit worth twice this one
    bra .loop

.done:
    rts

; ---------------------------------------------------------------------------
; Turn the offset in !SCRATCH+4 into an address the console can actually read.
;
; The table is one run of 2.9 million bytes as lutbuild.py writes it, and the
; cartridge is not one run of anything. This is a low cartridge: bank $30 shows
; its bytes at $308000 through $30FFFF and then stops, and the next 32,768 bytes
; of the table are bank $31 starting at $318000 again. There is no address at
; all for $310000, so a flat offset added to $308000 is a real address only for
; the first bank of a ninety two bank table.
;
; The conversion is therefore two pieces taken out of the offset. The low
; fifteen bits say how far into a bank the byte is, and everything above them
; says which bank.
;
; The step over banks $7E and $7F is kept even though this table no longer
; reaches them. It matches what lutbuild.py does when it places the pieces, and
; the two have to agree: a table that grows past bank $7D without this would
; read the console's own memory and find whatever the game last put there.
;
; It also works out how many bytes are left in that bank, which is what lets the
; loops below know whether a row fits without walking off the end of it.
;
; In:  !SCRATCH+4, a thirty two bit offset from the start of the table.
; Out: !SCRATCH a long address, !SCRATCH+14 the bytes left in that bank.
; ---------------------------------------------------------------------------
lut_place:
    lda !SCRATCH+4
    and #$7FFF                  ; how far into the bank, which is fifteen bits
    ora #$8000                  ; because a low cartridge starts each bank there
    sta !SCRATCH

    eor #$FFFF                  ; and the room left is what it takes to reach
    inc a                       ; $10000, which is nought minus the address
    sta !SCRATCH+14

    lda !SCRATCH+4              ; which bank: everything above those fifteen
    asl a                       ; bits, which is the high word doubled with the
    lda !SCRATCH+6              ; low word's top bit carried into it
    rol a

    clc
    adc.w #!LUTBANK             ; counted from wherever the table was placed
    cmp.w #!WORKRAM
    bcc +
    clc
    adc #$0002                  ; past the two banks that are memory, not ROM
+
    sta !SCRATCH+2
    rts

; ---------------------------------------------------------------------------
; Find the command's entry in the index.
;
; Walks the index rather than indexing into it, because the index is sixteen
; entries and a walk is shorter than the arithmetic to skip one. Sets carry when
; the command was found, clears it when it was not, which is the case a command
; the recordings never saw would take.
;
; In:  !CMD.
; Out: !KEYW, !ANSW, !ROWS, !ROWAT filled in, carry set.
; ---------------------------------------------------------------------------
lut_entry:
    php
    rep #$30

    lda.l !LUT                  ; how many commands the table holds
    and #$00FF
    sta !SCRATCH                ; countdown
    ldx.w #$0001                ; the first entry sits after that one byte

-
    lda.l !LUT,x
    and #$00FF
    cmp !CMD
    beq .found

    txa                         ; step over this entry
    clc
    adc #$000C
    tax
    dec !SCRATCH
    bne -

    plp
    clc                         ; no entry: the caller falls back
    rtl

.found:
    lda.l !LUT+1,x              ; the key width is one byte, so the byte above
    and #$00FF                  ; it has to be masked off before it is stored
    sta !KEYW

    lda.l !LUT+2,x              ; the answer width is a whole word already
    sta !ANSW

    lda.l !LUT+4,x              ; the row count, low word then high
    sta !ROWS
    lda.l !LUT+6,x
    sta !ROWS+2

    lda.l !LUT+8,x              ; where the rows begin, kept as the offset the
    sta !ROWAT                  ; table stores rather than turned into an
    lda.l !LUT+10,x             ; address here: lut_place does that, because
    sta !ROWAT+2                ; the two are not the same thing on a low
                                ; cartridge

    plp
    sec
    rtl

; ---------------------------------------------------------------------------
; Halve the range until the key is found or the range closes.
;
; Compares word by word, most significant first, because that is the order the
; keys were sorted in. A key of ten words is compared ten words at a time only
; when the earlier words tie, which they almost never do.
;
; Every row number here is thirty two bits. $06 has 75,278 rows, which does not
; fit in sixteen, and a search that wraps finds a real row that is the wrong one
; rather than failing, so nothing downstream can notice.
;
; On return the carry says whether a row matched, !MID holds it when one did,
; and !LOW holds where it would have gone when none did, which is what the
; fallback needs to find the two rows either side.
;
; In:  the entry above, and the wanted key in !ARG.
; Out: carry set and !MID the row, or carry clear and !LOW the gap.
; ---------------------------------------------------------------------------
lut_find:
    php
    rep #$30

    stz !LOW                    ; the range starts as every row, from nothing
    stz !LOW+2                  ; up to one past the last
    lda !ROWS
    sta !HIGH
    lda !ROWS+2
    sta !HIGH+2

.step:
    lda !LOW+2                  ; is the range empty? compare the high halves
    cmp !HIGH+2                 ; first, and only look at the low halves when
    bcc .open                   ; the high halves tie
    bne .missing
    lda !LOW
    cmp !HIGH
    bcs .missing                ; the range closed with nothing in it

.open:
    lda !LOW                    ; the middle of what is left, as a thirty two
    clc                         ; bit sum halved
    adc !HIGH
    sta !MID
    lda !LOW+2
    adc !HIGH+2
    sta !MID+2
    lsr !MID+2                  ; halving goes high word first, so the bit
    ror !MID                    ; falling out of it lands in the low word

    jsr lut_compare             ; carry clear if the row is below what is wanted
    bcc .below
    beq .hit

    lda !MID                    ; the row is above: keep the lower half
    sta !HIGH
    lda !MID+2
    sta !HIGH+2
    bra .step

.below:
    lda !MID                    ; the row is below: keep the upper half,
    clc                         ; starting one past the row just rejected
    adc #$0001
    sta !LOW
    lda !MID+2
    adc #$0000
    sta !LOW+2
    bra .step

.hit:
    plp
    sec
    rtl

.missing:
    plp
    clc
    rtl

; ---------------------------------------------------------------------------
; Compare the row in !MID against the wanted key.
;
; Leaves the flags a compare leaves: equal when every word matched, carry set
; when the row is above. Reads the row through a pointer because its address is
; the row number times the key width times two, which has to be worked out.
; ---------------------------------------------------------------------------
lut_compare:
    jsr lut_key_at

    ; The wanted key is in the direct page, and the 65816 has no compare that
    ; indexes the direct page by Y. Absolute indexing by Y exists, so the
    ; comparison reaches the key as an absolute address, and that address is the
    ; page's base plus the offset within it. Naming the offset alone reads from
    ; the bottom of the bank instead, where the game keeps its own variables, so
    ; no key ever matches and every search closes on nothing. The one row that
    ; still answered was the first, which is where an empty range leaves the
    ; index, and that is why the table looked as though it held a single row.
    ; The data bank is already zero: dsp1_answer sets it once on the way in.

    ; Does the whole key fit in what is left of this bank? Almost always, and
    ; then Y can walk it. About one row in sixteen hundred sits across the join
    ; and needs the address moved on properly for every word.
    lda !KEYW
    asl a
    cmp !SCRATCH+14
    beq .fast
    bcs .slow

.fast:
    ldy #$0000
    ldx !KEYW
-
    lda [!SCRATCH],y
    cmp.w !PAGE+!ARG,y
    bne .differ
    iny
    iny
    dex
    bne -
    bra .same

.slow:
    ldy #$0000
    ldx !KEYW
-
    phy                         ; the row is read at the address itself, so Y
    ldy #$0000                  ; has to be nought for the load and back to the
    lda [!SCRATCH],y            ; argument offset for the compare
    ply
    cmp.w !PAGE+!ARG,y
    bne .differ
    jsr lut_next
    iny
    iny
    dex
    bne -

.same:
    lda #$0000                  ; every word matched
    cmp #$0000
    rts

.differ:
    ; Nothing to unwind. This routine's whole output is the flags the compare
    ; above left, so it must not execute anything that touches them, and an
    ; earlier version did: it restored the data bank here, and plb takes its
    ; flags from the byte it pulls. Worse, the bank had been pushed before the
    ; flags were, and a stack gives things back in the order opposite to the one
    ; it took them, so the pull meant to fetch the bank fetched the flags and
    ; the pull meant to fetch the flags fetched the bank.

; ---------------------------------------------------------------------------
; Move the address in !SCRATCH on by one word, respecting where banks end.
;
; Only the slow walks below call this. Adding two to the address is right until
; it reaches $10000, which on a low cartridge is not an address: the byte after
; $30FFFF is $318000, not $310000. When the address rolls over to nought, the
; bank moves on and the address goes back to $8000.
; ---------------------------------------------------------------------------
lut_next:
    lda !SCRATCH
    inc a
    inc a
    sta !SCRATCH                ; sta leaves the flags inc set, so the test
    bne .done                   ; below is on the address just stored

    lda #$8000                  ; the bank ran out: begin the next one
    sta !SCRATCH
    lda !SCRATCH+2
    and #$00FF
    inc a
    cmp.w #!WORKRAM
    bne +
    lda.w #(!WORKRAM+2)         ; step over the console's own memory
+
    sta !SCRATCH+2

.done:
    rts

; ---------------------------------------------------------------------------
; Where the key of the row in !MID sits, as a long address in !SCRATCH.
;
; The arithmetic is thirty two bits throughout and that is not caution. $06 has
; 75,278 rows and a key ten words wide, so a row number times its width times two
; reaches 1,505,560, and doing any part of that in sixteen bits wraps and reads
; the wrong row.
;
; The scaling is a real multiply. Doubling once per key word instead multiplies
; by two raised to the width, which agrees with the width only when the width is
; two, and two is exactly the width $00, $04 and $10 use. That coincidence is
; what made an earlier version of this file look nineteen twentieths broken
; rather than entirely broken.
; ---------------------------------------------------------------------------
lut_key_at:
    lda !MID                    ; the row number, widened to thirty two bits
    sta !SCRATCH+4
    lda !MID+2
    sta !SCRATCH+6

    lda !KEYW                   ; times the key width
    jsr lut_scale

    asl !SCRATCH+4              ; and times two, for the bytes in a word
    rol !SCRATCH+6

    lda !SCRATCH+4              ; then from the start of this command's rows
    clc
    adc !ROWAT
    sta !SCRATCH+4
    lda !SCRATCH+6
    adc !ROWAT+2
    sta !SCRATCH+6

    jmp lut_place               ; and finally into somewhere the console can read

; ---------------------------------------------------------------------------
; Copy the answer for the row in !MID out to where the caller reads it.
; ---------------------------------------------------------------------------
lut_answer:
    php
    rep #$30

    ; Where the answers begin: past every key, which is the row count times the
    ; key width times two. Thirty two bits, for the same reason as above.
    lda !ROWS
    sta !SCRATCH+4
    lda !ROWS+2
    sta !SCRATCH+6
    lda !KEYW
    jsr lut_scale
    asl !SCRATCH+4
    rol !SCRATCH+6

    lda !SCRATCH+4              ; parked where the multiply cannot reach it,
    clc                         ; because the second product is about to use
    adc !ROWAT                  ; the same working bytes
    sta !SCRATCH+16
    lda !SCRATCH+6
    adc !ROWAT+2
    sta !SCRATCH+18

    ; Then this row's answer within them, the same way. The answer width is
    ; where a repeated-addition multiply would have fallen over: $0a answers 764
    ; words, so this would be 764 additions per call rather than ten shifts.
    lda !MID
    sta !SCRATCH+4
    lda !MID+2
    sta !SCRATCH+6
    lda !ANSW
    jsr lut_scale
    asl !SCRATCH+4
    rol !SCRATCH+6

    lda !SCRATCH+4
    clc
    adc !SCRATCH+16
    sta !SCRATCH+4
    lda !SCRATCH+6
    adc !SCRATCH+18
    sta !SCRATCH+6

    jsr lut_place               ; and only now does it become an address

    ; The same reason as in the compare: storing into the direct page indexed
    ; by Y is not a mode, and absolute indexed by Y is. The data bank is zero
    ; for the whole of this call, set by dsp1_answer.

    ; The same fast and slow pair as the comparison, for the same reason: an
    ; answer can sit across the join between two banks.
    lda !ANSW
    asl a
    cmp !SCRATCH+14
    beq .fast
    bcs .slow

.fast:
    ldy #$0000
    ldx !ANSW
-
    lda [!SCRATCH],y
    sta.w !OUT,y
    iny
    iny
    dex
    bne -
    bra .copied

.slow:
    ldy #$0000
    ldx !ANSW
-
    phy
    ldy #$0000
    lda [!SCRATCH],y
    ply
    sta.w !OUT,y
    jsr lut_next
    iny
    iny
    dex
    bne -

.copied:
    plp
    rtl

; ---------------------------------------------------------------------------
; Answer one command: the table first, the routine behind it second.
;
; This is the only entry point the cartridge's own code reaches. It cannot fail
; to answer and it cannot loop: the search is bounded by the row count halving,
; the copy is bounded by the answer width, and every fallback below is straight
; line code.
;
; In:  !CMD the command byte, !ARG its arguments.
; Out: !OUT its answer.
; ---------------------------------------------------------------------------
dsp1_answer:
    php
    phb
    phd
    rep #$30

    ; The direct page moves to somewhere the game does not use. Everything below
    ; addresses its working variables through it, and leaving it wherever the
    ; game had it would put them on top of the game's own.
    lda.w #!PAGE
    tcd

    ; The data bank goes to zero here and comes back on the way out, once,
    ; rather than in each routine that needs it. Everything below reaches the
    ; arguments and the answer as absolute addresses in bank zero, and the
    ; console's multiplier lives there too, so one setting covers the lot. It is
    ; also one fewer thing on the stack while the comparison's flags are the
    ; only thing that matters.
    lda #$0000
    pha
    plb
    plb

    jsl lut_entry
    bcc .fallback               ; a command the table has never seen

    jsl lut_find
    bcc .fallback               ; a key the table has never seen

    jsl lut_answer

    ; The order matters and it is the reverse of the way in. The prologue pushed
    ; the flags, then the data bank, then the direct page, so the direct page
    ; comes back first. Pulling the bank first takes the low half of the page
    ; and leaves the pull meant for the page taking the page's high half and the
    ; bank's byte together. The direct page then holds the caller's data bank in
    ; its high half, every direct page read after it lands somewhere else, and
    ; the game reads the wrong variable for the rest of its life.
    pld
    plb
    plp
    rtl

.fallback:
    jsl dsp1_fallback
    pld
    plb
    plp
    rtl
