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
; recordings and never anything else, so it is a constant here. The nine writes
; to it are ignored, which is what the part did with them.
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

!STATUS_READY = $0080           ; the one value the part's status ever returned

!NO_COMMAND   = $00FF           ; no command is part way through

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
; flags needs the stack untouched. Storing both costs four cycles and removes
; the ordering problem entirely.
;
; In:  A the caller's value, with php the only thing pushed.
; Out: !PORT_VALUE the value, !PORT_WIDE zero when the caller was sixteen bit.
; ---------------------------------------------------------------------------
macro capture()
    sep #$20
    sta.l !PORT_VALUE           ; the low half, which is always real
    xba
    sta.l !PORT_VALUE+1         ; the high half, real only in sixteen bit mode
    xba
    lda $01,s                   ; the flags php pushed, one byte above the stack
    and #$20                    ; the M bit: set means the caller had eight bits
    sta.l !PORT_WIDE
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
    phd

    sep #$20
    lda.l !PORT_READY           ; has this block been set up at all?
    cmp #!READY
    beq .known
    jsl dsp_port_reset
    sep #$20

.known:
    lda.l !PORT_WRITES
    inc a
    sta.l !PORT_WRITES

    lda.l !PORT_LEFT
    bne .argument

    ; Nothing was in progress, so this byte is a command.
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

.place:
    sta.l !PORT_VALUE
    lda.l !PORT_AT
    and.w #$00FF
    asl a                       ; two bytes to a word
    tax
    lda.l !PORT_VALUE
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
    ; Every argument is in. Three commands answer nothing at all: $80 resets the
    ; part, and $01 and $11 set the state later commands are keyed on. There is
    ; nothing to look up for those, so they stop here.
    ;
    ; This is a correctness fix before it is a saving. Reaching the lookup with
    ; a command that has no answer runs it to the fallback, and the fallback's
    ; first branch hands $80 to the signed-product routine, which borrows the
    ; console's one hardware multiplier. The game uses that multiplier too, and
    ; $4202 and $4203 are write only, so there is no way to give back what was
    ; in them. Not touching it is the only fix available.
    rep #$30
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
    sep #$20
    lda.l !PORT_CMD
    rep #$30
    and.w #$00FF
    sta.l !CMDL

    lda.l !PORT_AT
    and.w #$00FF
    asl a
    tax
    beq .carried
-
    dex
    dex
    lda.l !PORT_ARGS,x
    sta.l !ARGL,x
    cpx.w #$0000
    bne -

.carried:
    ; Keep this command's arguments if later commands are keyed on them.
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
    bra .append
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
    bra .append
++
    cmp.w #$0014
    bne .append
    ldx.w #$000A
-
    lda.l !PORT_ARGS,x
    sta.l !CARRY_14,x
    dex
    dex
    bpl -

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
    ldx.w #$000C
-
    lda.l !CARRY_02,x
    sta.l !PORT_WORD
    txa
    clc
    adc.l !PORT_TAIL
    tax
    lda.l !PORT_WORD
    sta.l !ARGL,x
    txa
    sec
    sbc.l !PORT_TAIL
    tax
    dex
    dex
    bpl -
    bra .asked

.from11:
    ldx.w #$0006
-
    lda.l !CARRY_11,x
    sta.l !PORT_WORD
    txa
    clc
    adc.l !PORT_TAIL
    tax
    lda.l !PORT_WORD
    sta.l !ARGL,x
    txa
    sec
    sbc.l !PORT_TAIL
    tax
    dex
    dex
    bpl -
    bra .asked

.from14:
    ldx.w #$000A
-
    lda.l !CARRY_14,x
    sta.l !PORT_WORD
    txa
    clc
    adc.l !PORT_TAIL
    tax
    lda.l !PORT_WORD
    sta.l !ARGL,x
    txa
    sec
    sbc.l !PORT_TAIL
    tax
    dex
    dex
    bpl -

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
    pld
    ply
    plx
    lda.l !PORT_VALUE
    plp
    rtl

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
; to the same two places. They are nought, because that is what $0a answers
; until its arithmetic is read: entry 2f in OPEN-QUESTIONS has the measurement
; that rules a table out for it.
;
; X and Y are left as the original loop left them, 704 and nought, because the
; code after the span is the game's and may still be using them.
; ---------------------------------------------------------------------------
!STREAM_TURNS = $00B0           ; 176 groups of four words, which is 704
!STREAM_ONE   = $0420           ; where the first two of each group went
!STREAM_TWO   = $0700           ; and the other two

dsp_stream:
    php
    phb
    rep #$30

    lda #$0000
    pha
    plb
    plb

    ldx #$0000
    ldy #!STREAM_TURNS
    lda #$0000

-
    sta.w !STREAM_ONE,x
    sta.w !STREAM_ONE+2,x
    sta.w !STREAM_TWO,x
    sta.w !STREAM_TWO+2,x
    inx
    inx
    inx
    inx
    dey
    bne -

    plb
    plp
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

; ---------------------------------------------------------------------------
; The window the game reaches when its data bank is redirected.
;
; Twelve places in the game set the data bank to $3F with "pea $003F" and then
; reach the part through three byte absolute instructions: "sta $8000" to send,
; "lda $8000" to receive, "bit $c000" to wait. None of those can be replaced by
; a call, because a call is four bytes and they are three, and none of them
; names the part's address in a way a scanner can recognise.
;
; What can be replaced is the "pea $003F", which is three bytes and names the
; bank outright. patch.py rewrites it to name this bank instead, and then every
; one of those instructions lands here without any of them being touched.
;
; What lands here has to satisfy the wait first. The game polls the status until
; its top bit is set, so a byte with that bit clear is an endless loop, and
; that is exactly what killed it: at frame 935 it entered the poll at $00CAD7
; and never came out. This answers with the top bit set at every address the
; poll can name, in both halves of a word, so the wait ends whichever width the
; accumulator happens to be.
; ---------------------------------------------------------------------------
!WINDOW_BANK = $7D

org (!WINDOW_BANK<<16)|$C000
dsp_window_status:
    fillbyte $80 : fill $2000

org (!WINDOW_BANK<<16)|$8000
dsp_window_data:
    fillbyte $00 : fill $100
