; Pilotwings without the DSP-1: standing in for the port the part answered on.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; Everything else in this project answers a command. This is the piece that gets
; asked, because the game never calls anything: it reads and writes an address.
;
; The cartridge reaches the part in bank $3F. Every one of the 122 places it
; does so is a single four byte long instruction, 89 of them "sta $3Fxxxx" and
; 33 "lda $3Fxxxx". A "jsl" is also four bytes, so every one of those places can
; be replaced where it stands, with nothing moved and nothing relocated. That is
; the whole reason this approach works, and it is worth knowing before reading
; further.
;
;   sta $3F8000   ->  jsl dsp_write     the value is in A, as it was
;   lda $3F8000   ->  jsl dsp_read      the value comes back in A
;   lda $3FC000   ->  jsl dsp_status
;   sta $3FC000   ->  jsl dsp_ignore
;
; patch.py does the replacing, and reads the operand to decide which of the four
; each site gets: in bank $3F, below $C000 is the data port and $C000 and up is
; the status register.
;
; ===========================================================================
; THE PROTOCOL, AS THE RECORDINGS SHOW IT
; ===========================================================================
;
; A command is one byte written to the data port. Its arguments follow as
; sixteen bit words. When the last one arrives the answer is ready, and the game
; reads it back.
;
; How many arguments each command takes is fixed, and that is measured rather
; than assumed: across all three regions every one of the nineteen commands
; takes one argument count and never another. The table below is that
; measurement. Without it there is no way to know when a command is complete,
; because nothing in the byte stream marks the end.
;
; The status register answered $80 on every one of the 2,867,736 reads in the
; recordings and never anything else, so it is a constant here. Both halves of it
; are that constant: a sixteen bit read takes $c000 and $c001, and both are $80,
; so the constant this returns for a wide read is $8080 rather than $0080. The
; nine writes to it are ignored, which is what the part did with them.
;
; ===========================================================================
; TWO THINGS THIS FILE HAS TO GET EXACTLY RIGHT
; ===========================================================================
;
; The registers. Each of these routines stands where one instruction stood, and
; the game carries on with whatever that instruction left. A "sta" changes no
; flags and no registers at all, so dsp_write and dsp_ignore must change none
; either: the accumulator is put back on the way out, and X, Y and the direct
; page are pushed and pulled around everything. An "lda" sets negative and zero
; from the value it loaded, so dsp_read and dsp_status set them the same way, by
; loading the value they are about to return as their last act.
;
; Getting this wrong does not fail where the mistake is. Leaving the accumulator
; clobbered lets the game run for about thirty frames and then wedge in the tail
; of its interrupt handler, which is a symptom that points nowhere near a port.
;
; The width. The game switches the accumulator between eight and sixteen bits,
; and the same "sta" moves one byte in the first and two in the second. Nothing
; in the instruction says which, so these routines read the caller's own flags
; off the stack. That is the M bit, and php puts it exactly one byte above the
; stack pointer before anything else is pushed.
;
; Nothing here changes the data bank. Every access is long, which costs a byte
; and a cycle per instruction and removes a whole class of mistake: a routine
; that pushes the bank and the flags in one order and pulls them in the other.
;
; ===========================================================================
; WHY THE ANSWER IS NOT HELD WHOLE
; ===========================================================================
;
; Fifteen of the sixteen answering commands give four words or fewer, so their
; answers fit in eight bytes. `$0a` gives 704 words in one region and 764 in
; another, which is over 1,500 bytes, and there is nowhere in this console's
; memory to put that without taking it from the game.
;
; So `$0a` is served as it is asked for rather than from a buffer, and the state
; below stays small enough to fit in memory the game was measured never to
; write.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   sep #$20 / rep #$20   Make the accumulator eight bits wide, or sixteen.
;
;   xba                   Swap the two halves of the accumulator. It works on
;                         the whole sixteen bits even when the accumulator is in
;                         its eight bit mode, which is what lets this file grab
;                         both halves of a value without knowing the mode yet.
;
;   lda 1,s               Read a byte just above the stack pointer. Used once,
;                         to read the flags php has just pushed.
;
;   lda.l / sta.l         A load or store naming the full 24-bit address. Every
;                         access here is one, so the data bank never matters.
;
;   php / plp             Save and restore the flags.
; ===========================================================================

; ---------------------------------------------------------------------------
; The state, in work RAM the game was measured never to write.
;
; !PORTRAM is chosen by the build from a run of the recorded demo, by
; snapshotting work RAM after every frame and keeping the bytes that never
; changed. Putting this anywhere the game also writes would corrupt one or the
; other in a way that surfaces as a wrong answer long afterwards, so the address
; is measured and never guessed.
; ---------------------------------------------------------------------------
!PORT_CMD    = !PORTRAM+0       ; which command the arguments belong to
!PORT_LEFT   = !PORTRAM+1       ; argument words still to come, and nought when
                                ; no command is part way through
!PORT_AT     = !PORTRAM+2       ; how many argument words have arrived
!PORT_OUT    = !PORTRAM+3       ; which byte of the answer is read next
!PORT_WIDE   = !PORTRAM+4       ; zero when the caller had a sixteen bit A
!PORT_VALUE  = !PORTRAM+6       ; the value the caller was writing
!PORT_ARGS   = !PORTRAM+8       ; ten argument words
!PORT_ANSWER = !PORTRAM+28      ; four answer words
!PORT_PART   = !PORTRAM+36      ; a half written argument is waiting
!PORT_HALF   = !PORTRAM+37      ; and this is its low byte
!PORT_READY  = !PORTRAM+38      ; holds !READY once this state has been set up
!PORT_WRITES = !PORTRAM+39      ; how many writes have arrived, wrapping
!PORT_DONE   = !PORTRAM+40      ; how many commands have completed, wrapping
!PORT_READS  = !PORTRAM+41      ; how many reads have been served, wrapping
!PORT_LAST   = !PORTRAM+42      ; the last command byte that completed
!PORT_SITE   = !PORTRAM+44      ; where the first read came from
!PORT_SEEN   = !PORTRAM+47      ; whether that has been recorded yet
!PORT_POLLS  = !PORTRAM+48      ; how many status reads have been served
!PORT_LASTPC = !PORTRAM+50      ; where the last status read came from
!PORT_LINE   = !PORTRAM+54      ; the scanline $0a was asked to start from,
                                ; which never reaches the port because the
                                ; game writes that command through the window

; Three commands set up state that later ones are asked in terms of, and the
; recorded table keys those later ones on their own arguments followed by the
; setter's. lutbuild.py calls the setter a carrier and builds every key that
; way, so the port has to rebuild the same key or the search looks for
; something the table does not hold.
;
;   $02 carries for $06, $0d and $0e      seven words
;   $11 carries for $13 and $1b           four words
;   $14 carries for $03                   six words
;
; Their arguments are kept here as each one completes, and appended to the next
; command that names them.
!CARRY       = !PORTRAM+64      ; seventeen words, the three sets end to end
!CARRY_02    = !CARRY+0         ; seven words
!CARRY_11    = !CARRY+14        ; four words
!CARRY_14    = !CARRY+22        ; six words
!PORT_TAIL   = !CARRY+34        ; where a command's own arguments end
!PORT_WORD   = !CARRY+36        ; one word in transit, because the processor
                                ; indexes a long address by X and by nothing
                                ; else, so source and destination take turns

; A value the memory does not hold before this has written it.
;
; The idle state used to be all zeroes, on the reasoning that work RAM reads as
; nought before anything writes it. It does not: this game fills bank $7F with
; $55, so the count of arguments still to come started at 85, the port believed
; a command was permanently part way through, and not one exchange ever
; completed. Every argument slot was still $55 after nine hundred frames.
;
; So the state is not assumed, it is recognised. Anything other than this value
; means the block has not been set up, and the first access sets it up. There is
; nowhere to put an initialiser that would run once instead: the console's reset
; vector is sixteen bits and reaches only bank $00, which the game fills.
!READY = $A5

; The lookup's own variables, named as long addresses so this file can reach
; them whatever data bank the game happens to be in. That is the whole reason
; they are spelled out here rather than reused from dsp1-answer.asm: the names
; there are direct page offsets, and a direct page offset written with an
; absolute store goes through the data bank instead. Doing exactly that, once,
; sent every command to whichever bank the game was using and left the lookup
; reading a command nobody had written.
!ARGL = $000D00                 ; the arguments, ten words
!CMDL = $000D30                 ; the command byte, at !CMD inside that page
!OUTL = $000E00                 ; the answer

!STATUS_READY = $8080           ; what a sixteen bit read of the status gives
                                ; back. Both halves, because a sixteen bit load
                                ; reads $c000 and $c001 and the recording holds
                                ; 1,482,010 reads of the first and 1,385,726 of
                                ; the second, every one of them $80.
                                ;
                                ; It answered $0080 until the demo was watched
                                ; long enough to wedge. The game polls the status
                                ; with a sixteen bit accumulator at $00:a196 and
                                ; branches on the sign, so the top half is what
                                ; that branch reads: with the high byte nought
                                ; the poll never ends, and the game stops issuing
                                ; commands at all after about two minutes. The
                                ; eight bit path was right the whole time, which
                                ; is why nothing before this ever noticed.

!NO_COMMAND   = $00FF           ; no command is part way through
!MEMSEL       = $00420D         ; three cycle reads above bank $80, once set

; ---------------------------------------------------------------------------
; How many argument words each command takes, indexed by the command byte.
;
; Measured across all three recordings, where every command takes one count and
; never another. A table rather than a chain of comparisons: one long load
; against nineteen compares, on a path that runs tens of times a frame.
;
; All 256 entries, and that is not padding. An earlier version stopped at $2F,
; which covers every command but one: $80 is the part's reset and the game does
; send it. Reading past the end of a table returns whatever follows it in the
; ROM, so $80 came back with an argument count taken from the code, and the port
; then swallowed that many of the game's next writes as arguments to a command
; that takes none. Everything after that was one command out of step.
; ---------------------------------------------------------------------------
dsp_arity:
    db $02, $04, $07, $03, $02, $00, $03, $00     ; $00
    db $03, $00, $01, $00, $03, $03, $02, $00     ; $08
    db $02, $04, $00, $03, $06, $00, $00, $00     ; $10
    db $04, $00, $00, $03, $00, $00, $00, $00     ; $18
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $20
    db $03, $00, $00, $00, $00, $00, $00, $00     ; $28
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $30
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $38
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $40
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $48
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $50
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $58
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $60
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $68
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $70
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $78
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $80
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $88
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $90
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $98
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $a0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $a8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $b0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $b8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $c0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $c8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $d0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $d8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $e0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $e8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $f0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $f8

; ---------------------------------------------------------------------------
; How many answer words each command gives, in the same shape.
;
; $0a is nought here although it answers 704 words in one region and 764 in
; another. Its answer is served from the four word buffer a word at a time, so
; there is nothing for the copy below to move.
; ---------------------------------------------------------------------------
dsp_width:
    db $01, $00, $04, $03, $02, $00, $03, $00     ; $00
    db $02, $00, $00, $00, $02, $03, $02, $00     ; $08
    db $02, $00, $00, $03, $03, $00, $00, $00     ; $10
    db $01, $00, $00, $01, $00, $00, $00, $00     ; $18
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $20
    db $01, $00, $00, $00, $00, $00, $00, $00     ; $28
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $30
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $38
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $40
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $48
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $50
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $58
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $60
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $68
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $70
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $78
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $80
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $88
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $90
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $98
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $a0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $a8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $b0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $b8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $c0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $c8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $d0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $d8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $e0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $e8
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $f0
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $f8

; ---------------------------------------------------------------------------
; Take the caller's value and width, before anything else can disturb either.
;
; Both halves of the accumulator are stored whether or not the high one means
; anything, because working that out first needs the flags, and reading the
; flags needs the stack untouched. Storing both removes the ordering problem
; entirely.
;
; Both go in one store rather than two and a swap. The accumulator is sixteen
; bits wide inside the processor whatever mode the caller was in: eight bit mode
; hides the high half rather than discarding it, so widening the register and
; storing a word writes exactly the two bytes the swap used to write, seven
; cycles sooner. This runs 99 times a game frame.
;
; In:  A the caller's value, with php the only thing pushed.
; Out: !PORT_VALUE the value, !PORT_WIDE zero when the caller was sixteen bit.
; ---------------------------------------------------------------------------
macro capture()
    rep #$20
    sta.l !PORT_VALUE           ; the low half, which is always real, and above
                                ; it the high half, real only in sixteen bit mode
    sep #$20
    lda $01,s                   ; the flags php pushed, one byte above the stack
    and #$20                    ; the M bit: set means the caller had eight bits
    sta.l !PORT_WIDE
endmacro

; ---------------------------------------------------------------------------
; Copy a carried set of words in after this command's own arguments.
;
; Three commands answer nothing and are only there to leave arguments behind for
; later ones, so those later ones are keyed on their own words followed by the
; carried set. This is the copy.
;
; It used to run one index register between two places. The source is counted
; from nought and the destination from wherever this command's own arguments
; ended, so every word cost an add to reach the destination and a subtract to get
; back: fifty five cycles to move two bytes, and up to seven words a command on
; about twenty two commands a game frame.
;
; Two registers is the whole fix. X walks the source, Y walks the destination,
; and both step down together because the gap between them never changes.
;
; The source and the destination are in different banks, so only one of them can
; drop the bank from its instruction. The destination does: the data bank goes to
; nought for the copy and comes back after, because everything else in this file
; reaches its state as a long address and does not care where the bank is.
; ---------------------------------------------------------------------------
macro carry(from, last)
    phb
    lda.w #$0000
    pha
    plb
    plb

    ldx.w #<last>
    lda.w #<last>
    clc
    adc.l !PORT_TAIL
    tay
?word:
    lda.l <from>,x
    sta.w !ARGL&$FFFF,y
    dey
    dey
    dex
    dex
    bpl ?word

    plb
endmacro

; ---------------------------------------------------------------------------
; The game wrote to the data port.
;
; A byte arriving with no command in progress starts one. Everything after it is
; an argument, and when the last argument the table names has arrived the answer
; is worked out and the read side is rewound to its first byte.
;
; Out: the flags exactly as they arrived, because "sta" alters none of them.
; ---------------------------------------------------------------------------
dsp_write:
    php
    %capture()
    rep #$30
    phx
    phy

    ; The direct page is not saved here. Everything below reaches its state as a
    ; long address, so it does not care where the page is, and the three routines
    ; in this project that move the page all put it back themselves. Saving it
    ; again cost eight cycles on every one of the 99 writes a game frame.

    sep #$20
    lda.l !PORT_WRITES
    inc a
    sta.l !PORT_WRITES

    lda.l !PORT_LEFT
    bne .argument

    ; Nothing was in progress, so this byte is a command.
    ;
    ; The check that this block has been set up at all lives here rather than on
    ; every write. Work RAM reads as nought before anything writes it, so a
    ; console that starts clean arrives here with no command in progress and is
    ; set up before the first command is taken. A console that starts on a
    ; pattern can arrive at the argument path instead, and then the count of
    ; arguments still to come runs down to nought and reaches this on the write
    ; after it. That is the same self-correction the count already relied on, and
    ; it is one command's worth of wrong answers either way.
    lda.l !PORT_READY           ; has this block been set up at all?
    cmp #!READY
    beq .known
    jsl dsp_port_reset
    sep #$20

.known:
    lda.l !PORT_VALUE
    sta.l !PORT_CMD

    rep #$30
    and.w #$00FF                ; the command byte indexes both tables
    tax
    sep #$20

    lda #$00                    ; there is no stz that names a full address, so
    sta.l !PORT_AT              ; the zero is loaded once and stored four times
    sta.l !PORT_OUT
    sta.l !PORT_PART            ; no half written argument is outstanding

    lda.l dsp_arity,x           ; how many argument words to expect
    sta.l !PORT_LEFT
    beq .complete               ; none expected means the answer is ready now
    brl .done

; The count of arguments still to come is what says whether a command is part
; way through, and nought means none is. That is deliberate rather than
; incidental: work RAM reads as nought before anything has written it, so the
; port starts idle without anything having to initialise it. There is nowhere to
; put an initialiser: the console's reset vector is sixteen bits and reaches only
; bank $00, which this cartridge fills with the game.
;
; On hardware that powers up with a pattern rather than zeroes the count could
; start at anything, and then the first few writes are taken for arguments and
; one wrong answer comes back. It corrects itself on the next command, because
; the count reaches nought either way.

.argument:
    ; An argument is a word, and the game does not always send it as one. A
    ; sixteen bit store delivers the whole thing at once; an eight bit store
    ; delivers half, and the other half arrives as the next write. Counting
    ; that second half as an argument of its own is what desynchronised the
    ; protocol: the count of arguments still to come never reached nought, so
    ; every write after it was swallowed as an argument to a command that had
    ; already had all of them. It ran the argument index up past eighty and
    ; wrote 170 bytes beyond the end of the buffer.
    sep #$20
    lda.l !PORT_WIDE
    beq .whole                  ; the caller's accumulator was sixteen bits

    lda.l !PORT_PART
    bne .second

    lda.l !PORT_VALUE           ; the first half: keep it and wait
    sta.l !PORT_HALF
    lda #$01
    sta.l !PORT_PART
    brl .done

.second:
    lda #$00
    sta.l !PORT_PART
    lda.l !PORT_VALUE           ; the second half is the high byte
    xba
    lda.l !PORT_HALF            ; and the kept one is the low
    rep #$30
    bra .place

.whole:
    rep #$30
    lda.l !PORT_VALUE

    ; The word arrives here in the accumulator, and it is put on the stack rather
    ; than back in !PORT_VALUE and read out again. Working out where it goes needs
    ; the accumulator for the index, so something has to hold it in the meantime,
    ; and the stack holds it for nine cycles less than a long store and a long
    ; load do.
.place:
    pha
    lda.l !PORT_AT
    and.w #$00FF
    asl a                       ; two bytes to a word
    tax
    pla
    sta.l !PORT_ARGS,x

    sep #$20
    lda.l !PORT_AT
    inc a
    sta.l !PORT_AT
    lda.l !PORT_LEFT
    dec a
    sta.l !PORT_LEFT
    beq .complete
    brl .done

.complete:
    ; Every argument is in. The command's own arguments are kept first, before
    ; anything else, because three commands answer nothing and two of those three
    ; are exactly the ones later commands are keyed on.
    ;
    ; That ordering is the whole of a fault that lasted from the first build to
    ; the day it was found. The width check below used to come first and jump
    ; straight to the end for a command that answers nothing, which is right for
    ; the lookup and wrong for the carry: $11 answers nothing, $13 and $1b are
    ; keyed on $11's arguments, and $13 is the command this cartridge asks more
    ; than any other. Its carried half stayed at the game's own $55 fill for
    ; every one of the 65,332 calls a recording holds, so its key matched no row,
    ; and every one of those answers came from the fallback instead of the table.
    rep #$30
    sep #$20
    lda.l !PORT_CMD
    rep #$30
    and.w #$00FF
    sta.l !CMDL
    jsr port_carry

    ; Now the lookup, and only for a command that has something to look up.
    ;
    ; Skipping it is a correctness fix before it is a saving. Reaching the lookup
    ; with a command that has no answer runs it to the fallback, and the
    ; fallback's first branch hands $80 to the signed-product routine, which
    ; borrows the console's one hardware multiplier. The game uses that
    ; multiplier too, and $4202 and $4203 are write only, so there is no way to
    ; give back what was in them. Not touching it is the only fix available.
    sep #$20
    lda.l !PORT_CMD
    rep #$30
    and.w #$00FF
    tax
    sep #$20
    lda.l dsp_width,x
    bne +
    brl .answered            ; the block below grew past a short branch
+

    ; The lookup moves the direct page itself, so nothing has to be done here.
    rep #$30
    lda.l !PORT_AT
    and.w #$00FF
    asl a
    tax
    beq .append
-
    dex
    dex
    lda.l !PORT_ARGS,x
    sta.l !ARGL,x
    cpx.w #$0000
    bne -

.append:
    ; And append the set this command is keyed on, after its own arguments.
    lda.l !PORT_AT
    and.w #$00FF
    asl a
    sta.l !PORT_TAIL

    lda.l !CMDL
    cmp.w #$0006
    beq .from02
    cmp.w #$000D
    beq .from02
    cmp.w #$000E
    beq .from02
    cmp.w #$0013
    beq .from11
    cmp.w #$001B
    beq .from11
    cmp.w #$0003
    beq .from14
    bra .asked

.from02:
    %carry(!CARRY_02, $000C)
    bra .asked

.from11:
    %carry(!CARRY_11, $0006)
    bra .asked

.from14:
    %carry(!CARRY_14, $000A)

.asked:
    jsl dsp1_answer

    ; Move the answer where the read side can find it without knowing where the
    ; lookup left it.
    sep #$20
    lda.l !PORT_CMD
    rep #$30
    and.w #$00FF
    tax
    sep #$20
    lda.l dsp_width,x
    rep #$30
    and.w #$00FF
    asl a
    tax
    beq .answered
-
    dex
    dex
    lda.l !OUTL,x
    sta.l !PORT_ANSWER,x
    cpx.w #$0000
    bne -

.answered:
    sep #$20
    lda.l !PORT_DONE
    inc a
    sta.l !PORT_DONE
    lda.l !PORT_CMD
    sta.l !PORT_LAST

.done:
    ; A "sta" leaves the accumulator exactly as it found it, so this has to as
    ; well. The value went into !PORT_VALUE on the way in, both halves of it,
    ; which is what makes it recoverable without knowing the caller's width: the
    ; high half is the caller's B register when the caller was eight bits wide,
    ; and restoring it puts that back too.
    rep #$30
    ply
    plx
    lda.l !PORT_VALUE
    plp
    rtl

; ---------------------------------------------------------------------------
; Keep this command's arguments, if later commands are keyed on them.
;
; Three commands carry for others, and two of the three answer nothing at all, so
; this has to run before anything that skips ahead on a command having no answer.
; It used to sit after that skip, which left $11's arguments unwritten for the
; life of the project and every $13 and $1b keyed on the game's own $55 fill.
;
; In:  !CMDL the command, !PORT_ARGS its arguments.
; Out: the matching !CARRY block, or nothing when this command carries for none.
; ---------------------------------------------------------------------------
port_carry:
    rep #$30

    lda.l !CMDL
    cmp.w #$0002
    bne ++
    ldx.w #$000C
-
    lda.l !PORT_ARGS,x
    sta.l !CARRY_02,x
    dex
    dex
    bpl -
    rts
++
    cmp.w #$0011
    bne ++
    ldx.w #$0006
-
    lda.l !PORT_ARGS,x
    sta.l !CARRY_11,x
    dex
    dex
    bpl -
    rts
++
    cmp.w #$0014
    bne +
    ldx.w #$000A
-
    lda.l !PORT_ARGS,x
    sta.l !CARRY_14,x
    dex
    dex
    bpl -
+
    rts

; ---------------------------------------------------------------------------
; The game read the data port.
;
; Out: A the next byte or word of the answer, with negative and zero set from
;      it, the way the "lda" this replaced would have left them.
; ---------------------------------------------------------------------------
dsp_read:
    php
    rep #$30
    phx

    sep #$20
    lda.l !PORT_READY
    cmp #!READY
    beq .known
    jsl dsp_port_reset
    sep #$20

.known:
    lda.l !PORT_READS
    inc a
    sta.l !PORT_READS
    sta.l !PORT_POLLS
    sta.l !PORT_POLLS+1

    lda.l !PORT_SEEN            ; keep where the very first read came from
    bne .noted
    lda #$01
    sta.l !PORT_SEEN
    lda $04,s
    sta.l !PORT_SITE
    lda $05,s
    sta.l !PORT_SITE+1
    lda $06,s
    sta.l !PORT_SITE+2

.noted:

    lda.l !PORT_OUT
    rep #$30
    and.w #$0007                ; four words, and never past them however far
    tax                         ; the game asks: a read with nothing to give
    lda.l !PORT_ANSWER,x        ; returns a stale answer rather than memory
    sta.l !PORT_VALUE

    sep #$20
    lda $03,s                   ; the caller's flags, above the pushed X
    and #$20
    beq .wide

    lda.l !PORT_OUT             ; an eight bit read consumes one byte
    inc a
    sta.l !PORT_OUT
    rep #$30
    plx
    plp
    sep #$20
    lda.l !PORT_VALUE           ; loaded last, so the flags are this load's
    rtl

.wide:
    lda.l !PORT_OUT             ; a sixteen bit read consumes two
    inc a
    inc a
    sta.l !PORT_OUT
    rep #$30
    plx
    plp
    rep #$20
    lda.l !PORT_VALUE
    rtl

; ---------------------------------------------------------------------------
; The game read the status register, which always said the same thing.
; ---------------------------------------------------------------------------
dsp_status:
    php
    sep #$20

    lda.l !PORT_POLLS           ; counted so that a stub nobody counted cannot
    inc a                       ; be the one that breaks the game unseen
    sta.l !PORT_POLLS
    bne .counted
    lda.l !PORT_POLLS+1
    inc a
    sta.l !PORT_POLLS+1

.counted:
    lda $02,s                   ; where this was called from
    sta.l !PORT_LASTPC
    lda $03,s
    sta.l !PORT_LASTPC+1
    lda $04,s
    sta.l !PORT_LASTPC+2

    lda $01,s
    and #$20
    beq .wide

    plp
    sep #$20
    lda #$80                    ; eight bit: the ready byte
    rtl

.wide:
    plp
    rep #$20
    lda.w #!STATUS_READY
    rtl

; ---------------------------------------------------------------------------
; The game wrote to the status register, which the part ignored.
; ---------------------------------------------------------------------------
dsp_ignore:
    rtl

; ---------------------------------------------------------------------------
; Put the port back to where it starts, and mark it as set up.
;
; Called by the first access that finds the marker missing, which is the only
; moment available: there is nowhere to put an initialiser that runs once.
; ---------------------------------------------------------------------------
dsp_port_reset:
    php

    ; The cartridge answers a read in three cycles rather than four everywhere
    ; above bank $80, but only once this register says so, and a game written
    ; for the slower timing never says so. This project's own code and tables all
    ; live in that second view, so the game's own banks are untouched by it and
    ; only what this adds gets faster. Set here because this runs once, on the
    ; first write the game makes to the port.
    sep #$20
    lda #$01
    sta.l !MEMSEL

    rep #$10                    ; a sixteen bit index, for the loop below
    sep #$20
    lda #$00
    sta.l !PORT_AT
    sta.l !PORT_OUT
    sta.l !PORT_LEFT
    sta.l !PORT_PART
    sta.l !PORT_SEEN
    sta.l !PORT_WRITES
    sta.l !PORT_DONE
    sta.l !PORT_READS

    ; The answer buffer starts empty rather than holding whatever the memory
    ; held. The game reads the port before it has asked anything, and the part
    ; returns nought to those reads: the first data read in the recording comes
    ; back $00, and every byte of the four words after it does too. Leaving the
    ; buffer as found returned $55 instead, which is the game's own fill.
    ldx #$0008
-
    dex
    sta.l !PORT_ANSWER,x
    bne -

    lda #!READY
    sta.l !PORT_READY
    plp
    rtl

; ---------------------------------------------------------------------------
; The $0a stream, in place of the loop that read it out of the port.
;
; This is the one exchange the game does not make through an instruction that
; names the part's address. It sets the data bank to $3F and then reads through
; three byte absolute instructions, "lda $8000", polling "bit $c000" between
; groups. A three byte instruction has no room for a four byte call, so there is
; nowhere to put a jsl and nothing for the site scanner to find.
;
; What there is room for is the loop as a whole. From "ldx #$0000" through the
; last of the four writes that close the exchange is 62 bytes, which is fifteen
; times what a call needs, so patch.py replaces the span rather than any
; instruction in it.
;
; The loop it replaces read 704 words in 176 turns of four, putting two into the
; buffer at $0420 and two into the one at $0700. This writes the same 704 words
; to the same two places, and they are the answers rather than nought:
; ground_block in asm/dsp1-ground.asm computes each scanline from the state $02
; left behind, which is arithmetic read out of the chip's own program and checked
; against the chip on 43,440 answer words.
;
; X and Y are left as the original loop left them, 704 and nought, because the
; code after the span is the game's and may still be using them. ground_block
; does that on the way out rather than by accident.
; ---------------------------------------------------------------------------
!STREAM_TURNS = $00B0           ; 176 groups of four words, which is 704
!STREAM_ONE   = $0420           ; where the first two of each group went
!STREAM_TWO   = $0700           ; and the other two

dsp_stream:
    jsl ground_block
    rtl

; ---------------------------------------------------------------------------
; $02, in place of the run that asked for it and read it back.
;
; This command matters twice over. It answers four words the game turns into its
; own state, and it leaves ten more words inside the part that $0a reads to draw
; the ground. Neither reached the cartridge before this routine existed, because
; the game asks for $02 the same way it asks for $10: it sets the data bank and
; then uses three byte absolute instructions, which have no room for a call and
; nothing in the operand a scanner could recognise.
;
; So every one of those stores went into the window at bank $7D, which is ROM,
; and every one of the reads came back nought. The game then computed its state
; from four zeroes, $0a was handed a line number derived from one of them, and
; the ground had no chance of being right however exact its arithmetic was.
;
; The run replaced is $00:CB4E through $00:CBB1, which is 100 bytes: the command
; byte, the seven arguments, the wait, the four reads, and the arithmetic the
; game does on them. That arithmetic is reproduced below rather than left in
; place, because the reads are three byte instructions in the middle of it.
;
; It does not start at $00:CB4A, where the `pea` that sets the data bank is. That
; instruction is jumped over on the path the demo takes, so the byte the closing
; `plb` at $00:CBB2 collects comes from the `pea` before the $10 run instead.
; Replacing from $CB4A unbalances the stack and blacks the screen.
;
; The direct page is the game's own throughout, which is what lets $54, $56 and
; the rest be read where the game reads them. Everything in bank zero is reached
; with a long address, because the data bank here is the window's rather than the
; game's usual one.
; ---------------------------------------------------------------------------
dsp_route_02:
    rep #$30

    lda $54                     ; the seven arguments, from where the game's
    sta.l !ARGL+0               ; own instructions took them
    lda $56
    sta.l !ARGL+2
    lda $58
    sta.l !ARGL+4
    lda $68
    sta.l !ARGL+6
    lda.l $0018F4
    sta.l !ARGL+8
    lda $36
    sta.l !ARGL+10
    lda $2A
    sta.l !ARGL+12

    ldx.w #$000C                ; and kept where $0a's own routine looks for
-                               ; them, which is the same place dsp_write keeps
    lda.l !ARGL,x               ; them for the commands that arrive through the
    sta.l !CARRY_02,x           ; port
    dex
    dex
    bpl -

    lda.w #$0002
    sta.l !CMDL
    jsl dsp1_answer

    ; What the game did with the four words it read back. The carry is set and
    ; cleared exactly where its own instructions did, because two of these are
    ; subtractions that borrow.
    clc
    lda.w #$0098
    adc.l !OUTL+0
    sta $8A
    clc
    adc.l !OUTL+2
    sta.l $0018F2

    lda.l !OUTL+4
    sta $60
    and $B2
    sta.l $0009E0
    sec
    sbc.w #$007F
    sta.l $0009E8

    lda.l !OUTL+6
    sta $62
    and $B2
    sta.l $0009E2
    sec
    sbc $8A
    inc a
    sta.l $0009EA
    rtl

; ---------------------------------------------------------------------------
; The line number $0a is asked to start from.
;
; The game writes $0a's command byte and its one argument through the window as
; well, so the port never sees either and nothing in the cartridge knew which
; scanline the stream began at. The argument is one less than $31 minus the byte
; $02 left at $8A, because the `rep` before it clears the carry and the
; subtraction borrows.
;
; The run replaced is $00:CAA8 through $00:CAB8, seventeen bytes: the command
; byte, the argument, and the width change between them. It leaves the widths
; the way that `rep` left them, sixteen bits and the carry clear, because the
; game's own code carries straight on from there.
; ---------------------------------------------------------------------------
dsp_route_0a:
    rep #$31
    lda.w #$0031
    sbc $8A
    sta.l !PORT_LINE
    rtl

; ---------------------------------------------------------------------------
; The four words the horizon carries from one frame to the next.
;
; This one is not an exchange at all. It is the game reaching its own memory,
; and it is here because the redirect that moves the part's accesses moves this
; as well.
;
; The eight instructions at $00:CAB9 copy $09E0 to $09E4, $09E2 to $09E6, $09E8
; to $09EC and $09EA to $09EE, so that the values $02 left this frame are still
; readable next frame after $02 has overwritten the originals. They are three
; byte absolute instructions, so the bank they land in is the data bank, and the
; data bank at that point is the one patch.py redirects.
;
; On the cartridge that bank is $3F, and the first eight kilobytes of every bank
; from $00 to $3F mirror work RAM, so $3F:09E0 is work RAM $09E0 and the copies
; land. The window this project sends them to instead is ROM at every address, so
; for the life of the project the reads returned nought, the writes went nowhere,
; and those four words held the console's power-on fill for the whole run. The
; demo diverged from the cartridge at game frame 175 because of it.
;
; Moving the window to a bank below $40 would fix this and thirty five other
; accesses like it in one line, and it was measured: it also changes every other
; windowed access to the game's own memory at once, and the run came out further
; from the cartridge rather than closer. So the accesses are corrected one run at
; a time, with each one measured, and this is the first.
;
; The addresses are named long, in bank $7E, which is where the mirror points.
; The order is the original's, so the accumulator and the flags on the way out
; are what the last `lda` left, and the widths are untouched: the `rep #$31` in
; dsp_route_0a above has already made both sixteen bits.
; ---------------------------------------------------------------------------
!HORIZON_LIVE = $7E09E0         ; the pair $02 writes every frame
!HORIZON_KEPT = $7E09E4         ; and the pair this copies them to
!HORIZON_EDGE = $7E09E8         ; the second pair, the same way
!HORIZON_HELD = $7E09EC

dsp_horizon:
    lda.l !HORIZON_LIVE
    sta.l !HORIZON_KEPT
    lda.l !HORIZON_LIVE+2
    sta.l !HORIZON_KEPT+2
    lda.l !HORIZON_EDGE
    sta.l !HORIZON_HELD
    lda.l !HORIZON_EDGE+2
    sta.l !HORIZON_HELD+2
    rtl

; ---------------------------------------------------------------------------
; $10, in place of the routine that asked for it.
;
; The original is at $00:CB17, just past the push that sets the data bank, and
; it reads like every one of these: send the command a byte at a time, send the
; arguments as words, wait on the status, take the answers back.
;
;   sep #$20 / lda #$10 / sta $8000        the command
;   rep #$31 / lda $58 / adc $18f6         the first argument, computed
;   sta $8000
;   lda $18f8 / sta $8000                  the second
;   bit $c000 / bpl                        the wait
;   lda $8000 / ldy $8000                  two words of answer
;
; None of those stores and loads can be replaced on its own, because each is
; three bytes and a call is four. The run of them is 34 bytes, so the run is
; replaced instead, and this stands in its place.
;
; The cut starts after the game's own push and pull of the data bank rather than
; at them, which keeps the stack exactly as the routine expects: that push
; leaves a byte behind that the routine's closing pull collects, and a
; replacement that swallowed the push would have to put the byte back by hand.
;
; Out: A the first answer word, Y the second, both in sixteen bit mode, which is
; what the instruction after the run reads.
; ---------------------------------------------------------------------------
dsp_route_10:
    rep #$30

    clc
    lda $58                     ; the game's own direct page, still in place
    adc.l $0018F6
    sta.l !ARGL
    lda.l $0018F8
    sta.l !ARGL+2
    lda.w #$0010
    sta.l !CMDL

    jsl dsp1_answer

    lda.l !OUTL+2
    tay
    lda.l !OUTL
    rtl
