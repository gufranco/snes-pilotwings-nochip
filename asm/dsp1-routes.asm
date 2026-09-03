; ---------------------------------------------------------------------------
; The exchanges the game reaches through a data bank rather than a long address.
;
; Most of the game's traffic to the chip is a long store or load, and each of
; those is four bytes, which is exactly the size of a call. So each one is
; replaced where it stands and nothing has to move.
;
; Twelve places do it differently. They push $3F, pull it into the data bank,
; and then use three byte absolute addressing for everything that follows. Three
; bytes has no room for a long call, and there is nothing in the operand for a
; scanner to recognise, so none of those accesses can be replaced on its own.
;
; What they do have is length. The shortest of the twelve is 34 bytes and the
; longest is 273, against the four a call needs. So the run is replaced as a
; whole and the rest filled with instructions that do nothing, which is the same
; approach dsp_stream and dsp_route_10 already use for two of them.
;
; That means each routine here has to reproduce not just the exchange but every
; piece of arithmetic the game wrapped around it, because the run being replaced
; contains both. Where the original left a value in a variable, so does this.
;
; Why this matters more than it looks. Before these existed, ten of the twelve
; runs reached a bank this project fills with a fixed byte, so every answer they
; read was nought. The port's own counters show what that cost: sampled every
; four hundred frames, no argument was ever written and not one read was ever
; served. The demo faded out at its first three-dimensional scene and never came
; back, because the viewpoint it asked for came back as zero.
; ---------------------------------------------------------------------------

; dsp1-port.asm leaves the origin inside the window bank, which holds a fixed
; byte rather than code, so these need an origin of their own. It goes in the
; code bank, well past where the port ends: bank $10 carries 1,729 bytes of the
; 32,768 it can, and every bank above it up to $1c is full of the tables driven
; out of the part. There is no empty bank to move into, only the empty half of
; this one.
org $10A000




; ---------------------------------------------------------------------------
; $0e at $00:804e, the first exchange the game ever makes.
;
;   ldy #$0e / sty $8000        the command, one byte
;   stz $8000                   the first argument, which is always nought
;   lda #$ffb0 / sta $8000      the second, which is always the same
;   ldy $c000 / bpl             the wait
;   lda $8000 / sta $64         two answer words into two variables
;   lda $8000 / sta $66
;
; Both arguments are constants in the instruction stream, so there is nothing to
; gather: they are written here as the immediates they are in the original.
; ---------------------------------------------------------------------------
route_0e:
    php
    phb
    rep #$30

    lda.w #$0000
    sta.l !ARGL                 ; the first argument, the stz in the original
    lda.w #$FFB0
    sta.l !ARGL+2               ; the second
    lda.w #$000E
    sta.l !CMDL
    jsl dsp1_answer

    rep #$30
    lda.l !OUTL
    sta $64                     ; direct page, so the game's own page reaches it
    lda.l !OUTL+2
    sta $66

    plb
    plp
    rtl

; ---------------------------------------------------------------------------
; $02 at $00:cb4a, the viewpoint, and the one that everything else waits on.
;
; Seven argument words are gathered from five direct page variables and one
; absolute one, four answer words come back, and the game folds those four into
; seven variables before the run ends. All of that is reproduced below.
;
; The carry matters here and is easy to lose. The original sets it with "sec"
; and then reads an answer, stores it, ands it, and stores that, before reaching
; the "sbc" that consumes it. None of those four touch the carry, so it survives,
; and the order below keeps that true.
;
; One absolute variable, $18f4, is read while the data bank is $3f. That works on
; the real console because every bank up to $3f shows the console's own memory
; below $2000, so this sets the bank to $00 and reads the same word.
; ---------------------------------------------------------------------------
route_02:
    php
    phb
    rep #$30

    lda.w #$0000
    pha
    plb
    plb                         ; data bank $00, where the low variables live

    lda $54
    sta.l !ARGL
    lda $56
    sta.l !ARGL+2
    lda $58
    sta.l !ARGL+4
    lda $68
    sta.l !ARGL+6
    lda.w $18F4
    sta.l !ARGL+8
    lda $36
    sta.l !ARGL+10
    lda $2A
    sta.l !ARGL+12
    lda.w #$0002
    sta.l !CMDL
    jsl dsp1_answer

    rep #$30
    lda.w #$0000
    pha
    plb
    plb                         ; the lookup moves the bank, so set it again

    clc
    lda.w #$0098
    adc.l !OUTL
    sta $8A
    clc
    adc.l !OUTL+2
    sta.w $18F2

    sec
    lda.l !OUTL+4
    sta $60
    and $B2
    sta.w $09E0
    sbc.w #$007F
    sta.w $09E8

    sec
    lda.l !OUTL+6
    sta $62
    and $B2
    sta.w $09E2
    sbc $8A
    inc a
    sta.w $09EA

    plb
    plp
    rtl

; ---------------------------------------------------------------------------
; $00 at $00:d055, inside a routine that may skip the chip entirely.
;
; This run begins with two branches that leave it before any argument is sent,
; and both land three bytes past its end. A call cannot reproduce a branch, so
; only the tail is replaced: everything from the widening that precedes the
; first argument down to, but not including, the closing bank pull. The branches
; stay where they are and still work.
;
; The closing pull is left alone for a second reason. The push at the top of the
; routine puts two bytes on the stack and the pull at the top takes one, so the
; one at the bottom is what balances it. Swallowing it would leave a byte behind.
; ---------------------------------------------------------------------------
route_00_d03f:
    rep #$30
    lda.w #$B000
    sta.l !ARGL
    lda $4C
    asl a
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer

    rep #$30
    lda.l !OUTL
    sta $4C
    rtl

; ---------------------------------------------------------------------------
; Two $00 exchanges at $00:d522, where the first argument arrives in A.
;
; The run above this point folds two variables into an accumulator, and the
; branches that do it sit before any chip access, so again only the tail is
; replaced and the branches are untouched.
;
; The accumulator is the first argument, which is why this takes A as it finds
; it rather than gathering it. The answer to the first exchange is the first
; argument of the second, so the two are chained.
;
; The index registers stay eight bits wide throughout, as they were on entry, so
; the widening here is "rep #$20" rather than "rep #$30": widening the index
; registers as well would leave them a size the code after this run does not
; expect.
; ---------------------------------------------------------------------------
route_00_d507:
    ldy #$00
    rep #$20

    sta.l !ARGL
    lda $5A
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer

    rep #$20
    lda.l !OUTL
    sta.l !ARGL
    sec
    lda $58
    sbc.w #$1770
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer

    rep #$20
    clc
    lda.l !OUTL
    adc $40
    sta $40
    rtl

!RS_KEEP = $7FDD50              ; two words this file keeps across a lookup,
                                ; because the lookup saves the processor's flags
                                ; and its two pages but not its index registers

; ---------------------------------------------------------------------------
; Three products at $00:8071, all sharing one argument.
;
; The run sends the same index register as the first argument of all three
; exchanges and takes the second from a different variable each time, so the
; index is kept once here rather than read back three times.
;
;   sep #$21                    eight bit accumulator, and the carry set
;   lda #$00 / sta $8000        the command
;   stx $8000 / ldy $48         the two argument words, a register and a
;   sty $8000                   variable
;   rep #$20
;   lda $54 / sbc $00           the carry set above is what makes this a plain
;   clc / adc $8000             subtraction rather than one short
;   sta $00
;
; That block appears three times over $54/$00/$48, $56/$02/$4a and $58/$04/$4c.
; The third one never stores its result: the run ends with it still in the
; accumulator, and whatever follows reads it there, so this ends the same way.
; ---------------------------------------------------------------------------
route_00_8071:
    rep #$30
    txa
    sta.l !RS_KEEP              ; the argument all three exchanges share

    lda.l !RS_KEEP
    sta.l !ARGL
    lda $48
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer
    rep #$30
    sec
    lda $54
    sbc $00
    clc
    adc.l !OUTL
    sta $00

    lda.l !RS_KEEP
    sta.l !ARGL
    lda $4A
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer
    rep #$30
    sec
    lda $56
    sbc $02
    clc
    adc.l !OUTL
    sta $02

    lda.l !RS_KEEP
    sta.l !ARGL
    lda $4C
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer
    rep #$30
    sec
    lda $58
    sbc $04
    clc
    adc.l !OUTL                 ; left in the accumulator, as the original does
    rtl

; ---------------------------------------------------------------------------
; Two products at $00:d47c, both indexed by the same register.
;
; The arithmetic above this point picks an index and the run then uses it to
; read two tables, so only the tail from the first command onwards is replaced
; and the index arrives in X. The lookup keeps the flags and both pages but not
; the index registers, so X is put aside before the first call and taken back
; after each.
;
; The two tables it reads live below $2000, which every bank up to $3f shows as
; the console's own memory, so they are reachable whatever the data bank holds
; and no bank change is needed here.
; ---------------------------------------------------------------------------
route_00_d447:
    rep #$20
    txa
    and.w #$00FF
    sta.l !RS_KEEP+2            ; the index, kept across both lookups

    rep #$30
    lda.l !RS_KEEP+2
    tax
    lda.w $1828,x
    sta.l !ARGL
    lda $40
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer
    rep #$30
    lda.l !OUTL
    sta $00
    stz $02

    lda.l !RS_KEEP+2
    tax
    lda.w $1820,x
    sta.l !ARGL
    lda $3C
    sta.l !ARGL+2
    lda.w #$0000
    sta.l !CMDL
    jsl dsp1_answer
    rep #$30
    lda.l !OUTL
    sta $04

    sep #$10
    lda.l !RS_KEEP+2
    tax                         ; the index back where the run's tail expects it
    rtl

