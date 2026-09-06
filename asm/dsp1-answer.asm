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
                                ; and everything here fits in $0D00 to $0D79.

!LUT      = $998000             ; where lutbuild.py's blob starts, and it
                                ; has to be the bank lut-map.asm gives it:
                                ; naming a different one here reads whatever
                                ; else is there as the index, so every command
                                ; misses and every answer falls back
!LUTBANK  = $0099               ; and the bank that is. This has to agree with
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
!LOW      = $3E                 ; where a key that missed would have gone
!MID      = $46                 ; the row being compared

; The search walks down the bits of the row number rather than halving a range,
; and these five carry it. Every one is thirty two bits, for the reason !MID is:
; $06 has 75,278 rows and its byte offsets reach 1,505,560.
!KEYLAST  = $60                 ; how far past a key's first byte its last sits
!STEPI    = $62                 ; the bit being tried, as a row count
!STEPB    = $66                 ; the same bit, as the bytes it moves
!OFFS     = $6A                 ; where !MID's key sits, in bytes from the first
!TRY      = $6E                 ; the row this step would move to
!TRYB     = $72                 ; and where that row's key sits
!ANSAT    = $76                 ; where this command's answers begin, thirty two
                                ; bits, read from the index rather than derived

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

    ; Two banks in the middle of the address space are the console's memory
    ; rather than the cartridge, so a table that starts below them has to step
    ; over them and a table that starts above them does not. Which of those is
    ; the case is known when this is assembled, so the test is made then rather
    ; than on every row.
    ;
    ; It used to be made here on every row, unconditionally, and moving the
    ; table into the mirror where the cartridge reads three cycles faster put
    ; every bank of it above the hole. The comparison then answered the same way
    ; every time and two banks were added to every row address in the table.
if !LUTBANK < !WORKRAM
    cmp.w #!WORKRAM
    bcc +
    clc
    adc #$0002                  ; past the two banks that are memory, not ROM
+
endif
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

    txa                         ; step over this entry, which is sixteen bytes
    clc                         ; wide so that stepping is a shift rather than
    adc #$0010                  ; an addition wherever anything indexes it
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

    asl a                       ; and how far past a key's first byte its last
    dec a                       ; one sits, which is what the search adds to an
    sta !KEYLAST                ; address to ask whether the key fits the bank

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

    lda.l !LUT+12,x             ; and where this command's answers begin, which
    sta !ANSAT                  ; is past every key. lutbuild.py works it out
    lda.l !LUT+14,x             ; when it writes the table; the cartridge used to
    sta !ANSAT+2                ; work it out again on every lookup, and doing so
                                ; is a thirty two bit multiply

    plp
    sec
    rtl

; ---------------------------------------------------------------------------
; The row, without a search, for a command whose keys are every combination.
;
; ===========================================================================
; WHY THIS EXISTS
; ===========================================================================
;
; Two of the sixteen commands have keys that are the whole product of a few
; values per word rather than an arbitrary set. $13 is the one that matters:
; 1,512 rows, and its seven key words take 1, 7, 8, 9, 1, 3 and 1 distinct
; values, which multiply to exactly 1,512. $18 is the other, and the game asks
; it three times in a whole recording.
;
; $13 is a quarter of everything the table is ever asked, and halving 1,512 rows
; takes eleven compares, each of which works out a row's address with a thirty
; two bit multiply before it can read a single word of it.
;
; None of that is needed. The rows are sorted, and a sorted list of every
; combination is counting in mixed radix: the first key word changes slowest and
; the last fastest. So the row is the sum, over the key's words, of how far along
; that word's own list of values the wanted one sits, times the number of rows
; one step of that word covers. Both of those come out of the block lutbuild.py
; writes, and the multiply falls out with them: walking a word's values one at a
; time and adding its stride at each step gives the same number as the position
; times the stride, without multiplying.
;
; A value the block does not hold hands the call to the search, which will not
; find it either and will fall back. Nothing here can answer wrongly by being
; asked for something outside the domain.
;
; In:  the entry lut_entry found, and the wanted key in !ARG.
; Out: exactly what lut_find gives: carry set and !MID the row, or carry clear.
; ---------------------------------------------------------------------------
!AXBANK = $00F4                 ; where lutbuild.py places the blocks

lut_row:
    php
    rep #$30

    ; Is this one of them? The list is two entries long, so it is walked rather
    ; than searched.
    lda.l lut_axes_table
    beq .search
    sta !SCRATCH+4
    ldx #$0002                  ; past the count
.entry:
    lda.l lut_axes_table,x
    cmp !CMD
    beq .block
    inx
    inx
    inx
    inx
    dec !SCRATCH+4
    bne .entry

.search:
    plp
    jml lut_find                ; not one of them, so the search answers. jml
                                ; rather than jsl, because lut_find's own rtl
                                ; then returns to whoever called this

.block:
    lda.l lut_axes_table+2,x    ; where this command's block is
    sta !SCRATCH+0
    lda.w #!AXBANK
    sta !SCRATCH+2

    ldy #$0000
    lda [!SCRATCH],y            ; how many key words the block describes
    sta !SCRATCH+4
    iny
    iny

    stz !MID                    ; the row, built up a word at a time
    stz !MID+2
    ldx #$0000                  ; and which key word is being matched, in bytes

.word:
    lda [!SCRATCH],y            ; how many values this word takes
    sta !SCRATCH+6
    iny
    iny
    lda [!SCRATCH],y            ; and how many rows one step of it covers
    sta !SCRATCH+8
    iny
    iny

.value:
    lda.w !PAGE+!ARG,x          ; the wanted word, reached as an absolute
    cmp [!SCRATCH],y            ; address for the reason lut_compare gives
    beq .matched

    lda !MID                    ; not this one, so the row moves on by one step
    clc
    adc !SCRATCH+8
    sta !MID
    bcc +
    inc !MID+2
+
    iny
    iny
    dec !SCRATCH+6
    bne .value
    bra .search                 ; a value no row carries

.matched:
    iny                         ; past the one that matched and every one after
    iny                         ; it, so that Y reaches the next word's count
    dec !SCRATCH+6
    bne .matched

    inx
    inx
    dec !SCRATCH+4
    bne .word

    plp
    sec
    rtl

; ---------------------------------------------------------------------------
; Walk down the bits of the row number until the key is found or they run out.
;
; Compares word by word, most significant first, because that is the order the
; keys were sorted in. A key of ten words is compared ten words at a time only
; when the earlier words tie, which they almost never do.
;
; Every row number here is thirty two bits. $06 has 75,278 rows, which does not
; fit in sixteen, and a search that wraps finds a real row that is the wrong one
; rather than failing, so nothing downstream can notice.
;
; WHY THIS IS NOT A RANGE HALVED
;
; The obvious binary search keeps a low row and a high row, takes the row half
; way between them, and throws away the half that cannot hold the key. It is the
; same number of comparisons as this, and it was what stood here.
;
; What it cost was the arithmetic between the comparisons. A row number is not
; an address: the key of row n sits n key widths times two bytes along, so every
; step had to multiply a thirty two bit row number by the key width. That is
; lut_scale, a shift and add loop, and measured over one parachute flight it was
; the heaviest single routine in the whole frame, ahead of the ground and ahead
; of the game's own code.
;
; The multiply is avoidable because the row numbers a search visits are not
; arbitrary. Built one bit at a time from the top, each step either leaves the
; row alone or adds exactly one power of two to it, so the byte offset either
; stays or grows by that same power of two times the width. Both are kept side
; by side and both halve together, so a step is two shifts and an add where it
; used to be a multiply.
;
; The bit walked from is 17, because two to the seventeenth is 131,072 and the
; largest command here has 75,278 rows. Starting above the table costs one
; comparison of a row number and no table read at all, and it means the starting
; step needs no multiply either: a width shifted up seventeen places is that
; width doubled, sitting in the high word, with nothing in the low word.
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

    stz !STEPI                  ; the first bit to try: 1 shifted up seventeen
    lda #$0002                  ; places, which is 2 in the high word
    sta !STEPI+2

    lda !KEYW                   ; the same bit measured in bytes, which is the
    asl a                       ; key width doubled for the two bytes in a word
    asl a                       ; and doubled again for the seventeenth bit,
    sta !STEPB+2                ; sitting in the high word for the other sixteen
    stz !STEPB

    stz !MID                    ; the search starts at the first row and never
    stz !MID+2                  ; moves below it, so that row is checked here
                                ; rather than inside the walk

    ; The offset the walk carries is counted from the start of the whole table
    ; rather than from the start of this command's rows, so it begins at where
    ; those rows begin rather than at nothing. That is the only difference, and
    ; it takes a thirty two bit addition out of every step of every search: the
    ; comparison used to add this same number back on before it could read
    ; anything.
    lda !ROWAT
    sta !OFFS
    sta !TRYB
    lda !ROWAT+2
    sta !OFFS+2
    sta !TRYB+2

    jsr lut_compare             ; carry clear when the row is below what is
    beq .hit                    ; wanted, set when it is above or equal
    bcc .step

    stz !LOW                    ; the first row is already above the wanted key,
    stz !LOW+2                  ; so the key would have gone before it
    plp
    clc
    rtl

.step:
    lda !MID                    ; the row this step would move to
    clc
    adc !STEPI
    sta !TRY
    lda !MID+2
    adc !STEPI+2
    sta !TRY+2

    lda !TRY+2                  ; is it a row at all? the high halves first, and
    cmp !ROWS+2                 ; the low halves only when they tie
    bcc .inside
    bne .narrow
    lda !TRY
    cmp !ROWS
    bcs .narrow                 ; past the end of the table: leave the row alone

.inside:
    lda !OFFS                   ; where that row's key sits, which is where this
    clc                         ; row's key sits plus the bytes this bit moves
    adc !STEPB
    sta !TRYB
    lda !OFFS+2
    adc !STEPB+2
    sta !TRYB+2

    jsr lut_compare
    beq .took                   ; the key is there: stop with the row taken
    bcs .narrow                 ; the row is above what is wanted: do not move

    lda !TRY                    ; the row is below what is wanted, so it is the
    sta !MID                    ; new floor and the walk goes on from it
    lda !TRY+2
    sta !MID+2
    lda !TRYB
    sta !OFFS
    lda !TRYB+2
    sta !OFFS+2

.narrow:
    lsr !STEPI+2                ; the next bit down, in both measures at once.
    ror !STEPI                  ; shifting goes high word first, so the bit
    lsr !STEPB+2                ; falling out of it lands in the low word
    ror !STEPB

    lda !STEPI                  ; bits left to try?
    ora !STEPI+2
    bne .step

    lda !MID                    ; none matched. !MID is the last row below the
    clc                         ; wanted key, so the key would have gone one
    adc #$0001                  ; past it
    sta !LOW
    lda !MID+2
    adc #$0000
    sta !LOW+2
    plp
    clc
    rtl

.took:
    lda !TRY                    ; the row that matched becomes the answer's
    sta !MID
    lda !TRY+2
    sta !MID+2

.hit:
    plp
    sec
    rtl

; ---------------------------------------------------------------------------
; Compare the row in !MID against the wanted key.
;
; Leaves the flags a compare leaves: equal when every word matched, carry set
; when the row is above. Reads the row through a pointer because its address is
; the row number times the key width times two, which has to be worked out.
; ---------------------------------------------------------------------------
lut_compare:
    ; Working out where the row sits is written here rather than called, because
    ; this routine runs about thirteen times per lookup and twenty one lookups
    ; per game frame. Two calls and their returns are twenty one cycles of every
    ; step, against a step that measures around a hundred and twenty.
    ;
    ; lut_place still exists for the fallback and for the answer copy, which are
    ; handed a row number rather than an offset and reach it once rather than
    ; thirteen times. What is below has to stay the same arithmetic as that one;
    ; it is the only place in this file where a sequence is written twice.

    lda !TRYB                   ; how far into the bank, which is fifteen bits.
    and #$7FFF                  ; !TRYB counts from the start of the whole table
    ora #$8000                  ; because a low cartridge starts each bank there
    sta !SCRATCH

    lda !TRYB                   ; which bank: everything above those fifteen
    asl a                       ; bits, which is the high word doubled with the
    lda !TRYB+2                 ; low word's top bit carried into it
    rol a
    clc
    adc.w #!LUTBANK
if !LUTBANK < !WORKRAM
    cmp.w #!WORKRAM
    bcc +
    clc
    adc #$0002                  ; past the two banks that are memory, not ROM
+
endif
    sta !SCRATCH+2

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
    ;
    ; Asked by adding rather than by subtracting. The room left used to be worked
    ; out first, as nought minus the address, and then compared against the key's
    ; width; adding the offset of the key's last byte to its first and reading the
    ; carry answers the same question in three instructions instead of eight, and
    ; the offset is worked out once per lookup rather than once per step.
    lda !SCRATCH
    clc
    adc !KEYLAST
    bcs .slow                   ; past the end of the bank, so it sits across

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
    ;
    ; It returned by falling into the routine below, which is where a word of
    ; every key comparison went. That worked, and only by accident: none of the
    ; instructions there touches the carry, and the zero flag came out clear
    ; because the address it left was not nought. Both are true today and
    ; neither is a property anybody stated. This is a key that did not match,
    ; which is almost every comparison the search makes, so it was also twenty
    ; one cycles of every step.
    rts

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
;
; The search no longer comes here, because it carries the offset down with it.
; The fallback still does: it is given a row number on its own.
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

    ; Where the answers begin is read from the index rather than worked out. It
    ; is where the rows begin plus the row count times the key width times two,
    ; and none of those three changes for the life of the table, so lutbuild.py
    ; writes the sum into the entry and the cartridge stops multiplying twice per
    ; lookup where once will do.
    lda !ANSAT                  ; parked where the multiply cannot reach it,
    sta !SCRATCH+16             ; because the product below uses those bytes
    lda !ANSAT+2
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

    ; Three commands never reach the table at all, because their arithmetic is
    ; known to the bit and the table can only ever agree with it.
    ;
    ; $00 and $80 are the signed fractional product and $08 is twice the sum of
    ; three squares. asm/dsp1-ops.asm computes each of them, and each was held
    ; against every distinct call the three recordings hold, 29,467 of them,
    ; with no disagreement. So the table's row and the routine's answer are the
    ; same word, and the only difference is what it costs to arrive at.
    ;
    ; It costs a great deal. Those three are a fifth of every lookup the game
    ; makes, and a lookup is a bisection over a table of millions of bytes: a
    ; thirty two bit multiply per step to turn a row number into an offset, a
    ; bank conversion, and a key comparison, all to fetch a word that two
    ; multiplies would have produced. Measured over one parachute flight, the
    ; search was 42% of the whole frame and the game ran at a sixth of speed.
    ;
    ; The routing is the branch below rather than a new one, because
    ; asm/dsp1-fallback.asm already sends these three to their arithmetic. It
    ; was written for the case where the table has no row; the case where the
    ; table has a row nobody needs to read is the same journey.
    lda !CMD
    beq .routed                 ; $00
    cmp #$0080
    beq .routed                 ; $80 reaches the same routine in the chip
    cmp #$0008
    beq .routed

    jsl lut_entry
    bcc .routed                 ; a command the table has never seen

    jsl lut_row
    bcc .routed                 ; a key the table has never seen

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

; Reached two ways, and they are the same journey. A command whose arithmetic is
; known comes straight here without touching the table. A command whose
; arithmetic is not known comes here having missed, and takes the nearest row.
.routed:
    jsl dsp1_fallback
    pld
    plb
    plp
    rtl
