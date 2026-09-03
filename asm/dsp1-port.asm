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

!ARGL = $000D00                 ; the lookup's arguments, as a long address
!OUTL = $000E00                 ; and its answer, so this file can reach both
                                ; without depending on the data bank. Both are
                                ; inside memory the game was measured never to
                                ; write.

!STATUS_READY = $0080           ; the one value the part's status ever returned

!NO_COMMAND   = $00FF           ; no command is part way through

; ---------------------------------------------------------------------------
; How many argument words each command takes, indexed by the command byte.
;
; Measured across all three recordings, where every command takes one count and
; never another. A command not listed takes none, which is what $80 does.
; A table rather than a chain of comparisons: one long load against nineteen
; compares, on a path that runs tens of times a frame.
; ---------------------------------------------------------------------------
dsp_arity:
    db $02, $04, $07, $03, $02, $00, $03, $00     ; $00 $01 $02 $03 $04 $05 $06 $07
    db $03, $00, $01, $00, $03, $03, $02, $00     ; $08 $09 $0a $0b $0c $0d $0e $0f
    db $02, $04, $00, $03, $06, $00, $00, $00     ; $10 $11 $12 $13 $14 $15 $16 $17
    db $04, $00, $00, $03, $00, $00, $00, $00     ; $18 $19 $1a $1b $1c $1d $1e $1f
    db $00, $00, $00, $00, $00, $00, $00, $00     ; $20 $21 $22 $23 $24 $25 $26 $27
    db $03, $00, $00, $00, $00, $00, $00, $00     ; $28 $29 $2a $2b $2c $2d $2e $2f

; ---------------------------------------------------------------------------
; How many answer words each command gives, in the same shape.
; ---------------------------------------------------------------------------
dsp_width:
    db $01, $00, $04, $03, $02, $00, $03, $00
    db $02, $00, $00, $00, $02, $03, $02, $00
    db $02, $00, $00, $03, $03, $00, $00, $00
    db $01, $00, $00, $01, $00, $00, $00, $00
    db $00, $00, $00, $00, $00, $00, $00, $00
    db $01, $00, $00, $00, $00, $00, $00, $00

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
    sta.l !PORT_AT              ; the zero is loaded once and stored three times
    sta.l !PORT_OUT

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
    rep #$30
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
    ; Every argument is in. The lookup moves the direct page itself, so nothing
    ; has to be done about it here.
    rep #$30
    sep #$20
    lda.l !PORT_CMD
    rep #$30
    and.w #$00FF
    sta.w !CMD

    lda.l !PORT_AT
    and.w #$00FF
    asl a
    tax
    beq .asked
-
    dex
    dex
    lda.l !PORT_ARGS,x
    sta.l !ARGL,x
    cpx.w #$0000
    bne -

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
; Put the port back to where it starts.
;
; Nothing calls this, and that is the point: the idle state is all zeroes, which
; is what work RAM already reads as. It is here so that a future caller with
; somewhere to put an initialiser has one to call.
; ---------------------------------------------------------------------------
dsp_port_reset:
    php
    sep #$20
    lda #$00
    sta.l !PORT_AT
    sta.l !PORT_OUT
    sta.l !PORT_LEFT
    plp
    rtl
