; Pilotwings without the DSP-1: giving the screen back its top half.
;
; ===========================================================================
; WHAT THIS FILE IS FOR
; ===========================================================================
;
; The flight screen is not one picture. It is three bands, and the console is
; told to change what it draws between them while the beam is still moving down
; the screen. The game does that with an interrupt, which is a request for the
; processor to stop what it is doing at an exact scanline and run a short
; routine.
;
; There are three of those interrupts per picture, and the game keeps a counter
; at address $0080 saying which one comes next. Each interrupt does its own
; small job and then arms the following one:
;
;   scanline  47   swap the sky layer's scroll, so the clouds sit right
;   scanline  94   change the drawing mode and which layers are shown, which is
;                  what turns the top half's instrument panel into the bottom
;                  half's ground
;   scanline 255   nothing at all in the retail cartridge: a bare return
;
; Scanline 255 is below the picture, so the third interrupt is only there to
; close the sequence off. The whole sequence is set up again from the start by
; the game's own routine at $00:F168, which the main loop calls once for every
; frame of the game's clock.
;
; ===========================================================================
; WHY THAT BREAKS HERE, AND WHY IT IS NOT A FAULT IN THE CONVERSION
; ===========================================================================
;
; On the retail cartridge one frame of the game's clock is one picture, so
; "once per frame of the game's clock" and "once per picture" are the same
; sentence and nobody has to tell them apart.
;
; Here they are not the same sentence. The part this project replaces answered
; in hardware; the replacement answers in software, and one frame of the game's
; clock now takes about sixteen pictures. The sequence is therefore armed once
; and runs once, and the fifteen pictures that follow are drawn with whatever
; the last interrupt left behind: the bottom half's mode and layers, applied to
; the whole screen. The instrument panel and the sky are gone from those
; fifteen, the ground's own drawing mode is stretched over them, and what a
; person sees is the panel appearing for one picture in sixteen. That is the
; flicker.
;
; Nothing about it is a wrong answer or a corrupted table. The picture on the
; one good frame is correct, and the memory the two disagree over is this
; project's own multiply tables mid-rebuild. It is only the sequence not being
; started again.
;
; ===========================================================================
; WHAT THIS DOES INSTEAD
; ===========================================================================
;
; The third interrupt is the only thing in the game that is guaranteed to
; happen once per picture rather than once per frame of the game's clock, and
; in the retail cartridge it does nothing. So it is where the sequence gets
; started again.
;
; The handler for it is repointed here, and this arms the sequence from the top
; exactly as $00:F168 does. Scanline 255 is below the visible picture, so the
; work lands in the gap between one picture and the next, which is where
; setting up for the next picture belongs.
;
; $00:F168 itself is deliberately not called. It ends by enabling interrupts
; and it is shared with screens that are not the flight, and a build that
; called it stopped working the moment the demo reached the runway. What is
; below is the part of it that arms the sequence and nothing else.
;
; The values are read out of the same four tables $00:F168 reads rather than
; written in here as numbers. A number copied out of a routine is a number that
; stops agreeing with it.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   lda $1fef       Load the accumulator from that address.
;   cmp #$13        Compare what was loaded against that number.
;   beq label       If the comparison matched, carry on at that label.
;   sta $2105       Store the accumulator to that address.
;   stz $4208       Store zero to that address.
;   ldx #$00        Load the index register with that number.
;   lda $f14d,x     Load from that address plus whatever the index holds.
;   rts             Return to whoever called.
;
; Addresses beginning $21 and $42 are not memory. They are the console's own
; controls, and storing to one of them is how anything is asked of the screen.
;
; The interrupt arrives here with the accumulator and index registers eight
; bits wide, so every load and store below moves one byte. That is what the
; screen's controls want in any case.
; ===========================================================================

; ===========================================================================
; THE OTHER HALF OF THE SAME PROBLEM
; ===========================================================================
;
; Arming the sequence once per picture fixes the fifteen pictures that were
; drawn with the last interrupt's leftovers. It does not fix what the game's own
; arming routine does when it runs, and that is the flicker still left.
;
; $00:F168 is called once per frame of the game's clock, from the main loop. It
; writes the console's drawing mode, which layers are shown, and both of the sky
; layer's scroll registers, and then it points the first interrupt at its
; scanline. Every one of those is a control the screen reads while it is drawing.
;
; On the retail cartridge that is safe by arithmetic rather than by care. One
; frame of the clock is one picture there, so the main loop reaches $00:F168 at
; the same point every time, and measured across a run of the demo it lands
; below the picture on 98.9% of frames: scanline 245 to 258, in the gap.
;
; Here one frame of the clock is about five pictures, so the main loop reaches
; it at no particular scanline at all. Measured across the same run, 24.2% of
; the calls land inside the picture. When one does, the drawing mode changes
; part way down the screen: the panel at the top is cut off, the ground is drawn
; through the middle of it, and the next picture puts it back. That is one frame
; in four with a torn panel, which is what it looks like from a chair.
;
; The two numbers agree with each other. 24.2% of calls landing inside the
; picture, and 24.6% of the demo's frames showing a torn panel, are the same
; event counted twice.
;
; So this waits. The routine below is put in front of $00:F168 and holds it
; until the beam is past the bottom of the picture, which is the condition
; retail satisfies by accident. Then it jumps into $00:F168 unchanged, so the
; arming itself is still the game's own and nothing here can drift from it.
;
; The wait costs about half a picture on the frames that have to wait at all,
; against a frame that already takes five. What it buys is that the mode never
; changes while the screen is being drawn.
;
; The count is there so that a screen which never leaves the picture cannot hang
; the machine. If it ever runs out, the arming happens anyway and one picture is
; torn, which is what happened on every frame before this existed.
; ---------------------------------------------------------------------------
raster_arm_wait:
    php
    sep #$20
    lda $1fef                   ; the flight screen is the only one drawn in
    cmp #$13                    ; three bands, and the only one this project
    beq .flight                 ; arms once per picture of its own accord

    ; Every other screen keeps the retail behaviour, with the wait in front of
    ; it. They are not drawn in bands, nothing else here arms anything for them,
    ; and the sequence they set up is their own.
    rep #$10                    ; a whole word for the countdown
    ldx.w #$4000
-
    lda.l $004212               ; the console's own status: bit seven is set
    bmi +                       ; while the beam is below the picture
    dex
    bne -
+
    plp
    jml $00F168                 ; the game's own routine, untouched. jml rather
                                ; than a call, so its own rts returns to whoever
                                ; asked for the arming in the first place

; ---------------------------------------------------------------------------
; The flight screen arms without waiting, because there is nothing left for it
; to wait for.
;
; What made the wait necessary was five writes: $00:F168 sets the drawing mode,
; which layers are shown and both of the sky layer's scroll registers, and those
; are controls the screen reads while it is drawing. The arming itself, which is
; where the next interrupt lands and which routine runs there, is not.
;
; The five writes are already made once per picture, below the picture, by
; raster_rearm and raster_nmi, out of the same four tables and with the same
; values. Making them again from the main loop can only change where on the
; screen they land, so the flight screen does not make them at all.
;
; What it does instead is the arming, and it does that by jumping into the
; game's own half of it rather than by copying it out. $00:F1B9 reads the
; scanline and the handler for step nought, points the interrupt at them, and
; ends by letting interrupts through again, which is the one thing the callers
; of this depend on.
;
; The wait was 2.5% of a game frame doing nothing.
; ---------------------------------------------------------------------------
.flight:
    plp
    sep #$30                    ; the game's own routine is entered eight bits
                                ; wide by every one of its callers, and the code
                                ; below is the second half of it

    ldx #$00                    ; step nought is the one being armed
    stx $80
    stz $4208                   ; the across-the-screen position, high byte
    stz $420a                   ; and the scanline, high byte
    jmp $F1B9

; ===========================================================================
; THE SAME ARMING AGAIN, WHERE NOTHING CAN HOLD IT UP
; ===========================================================================
;
; The interrupt this file is hung on is the ordinary kind, and the ordinary kind
; can be switched off. The game switches it off once per frame of its clock and
; leaves it off for about a whole picture: $00:F24E turns the other kind of
; interrupt on, and then sits in a two instruction loop at $00:F257 waiting for
; that other kind to arrive. Measured across a run of the demo, the loop holds
; the ordinary interrupts back for a median of 14,389 instructions.
;
; Anything armed for a scanline inside that window does not run at that
; scanline. It runs when the game lets interrupts through again, which is inside
; the other kind's own handler at $00:F102, and by then the next picture has
; often begun. Measured the same way, 3.3% of the arming interrupts run inside
; the picture rather than below it, and every one of those writes the top band's
; drawing mode part way down a screen that is already being drawn. What that
; looks like is a band of ground cut through the instrument panel for one
; picture, which is the flicker.
;
; The other kind of interrupt cannot be switched off that way, and it arrives at
; scanline 225, which is below the picture. So the arming is done there as well,
; from in front of the game's own handler for it.
;
; Both are kept rather than one. The unswitchable kind only arrives once per
; frame of the game's clock, which is not often enough on its own; the ordinary
; kind arrives every picture but is late on 3.3% of them. Between them every
; picture is armed, and a late one now writes values that are already there,
; which changes nothing on the screen.
;
; The game's own handler is then reached unchanged, so nothing here can drift
; from what it does.
; ---------------------------------------------------------------------------
raster_nmi:
    php
    phb
    phk                         ; the data bank goes to this one, which is bank
    plb                         ; zero, because raster_rearm reaches the game's
                                ; tables and the screen's controls as plain
                                ; addresses and both live there
    sep #$30                    ; one byte at a time, which is what it expects
    jsr raster_rearm
    plb
    plp
    jmp $F0A0                   ; and on into the game's own handler

raster_rearm:
    lda $1fef                   ; which layers the middle band asks for. The
    cmp #$13                    ; flight is the only screen that asks for $13,
    beq +                       ; and every other screen wants the retail
    rts                         ; behaviour, which is to do nothing here
+

; ---------------------------------------------------------------------------
; The picture's top band. Same three writes $00:F168 makes, same three tables.
; ---------------------------------------------------------------------------

    ldx #$00                    ; step zero: the top of the picture

    lda $f14d,x
    sta $2105                   ; which drawing mode the top band uses

    lda $f150,x
    sta $212c                   ; which layers are shown in it

    lda $f153,x
    sta $2133                   ; the screen setting that goes with them

; ---------------------------------------------------------------------------
; The sky layer's starting scroll. These two are numbers inside $00:F168 as
; well, because they are not in any table there either.
;
; Each of the two controls below is written twice and keeps both bytes: the
; first write is the low half of the number, the second is the high half. So
; the pair below sets the sideways scroll to $0100 and the vertical one to
; $00d0. The scanline 47 interrupt overwrites both a moment later with the
; frame's real values; this is only what they start at.
; ---------------------------------------------------------------------------

    lda #$01
    stz $210f
    sta $210f                   ; sky layer, sideways

    lda #$d0
    sta $2110
    stz $2110                   ; sky layer, vertical

; ---------------------------------------------------------------------------
; Arm the first interrupt of the sequence and say what it lands on.
;
; A scanline is named by two bytes. The high byte of both is cleared first,
; because the tables hold only the low one and whatever is left in the high
; byte would otherwise put the interrupt on a scanline nobody asked for.
; ---------------------------------------------------------------------------

    stz $4208                   ; the across-the-screen position, high byte
    stz $420a                   ; the scanline, high byte

    lda $18fa,x
    sta $4207                   ; the across-the-screen position, low byte

    lda $18fd,x
    sta $4209                   ; the scanline, low byte

    lda $f147,x
    sta $0076
    lda $f148,x
    sta $0077                   ; the routine that interrupt will run

    lda #$01
    sta $0080                   ; and the step the counter will then be on

    rts
