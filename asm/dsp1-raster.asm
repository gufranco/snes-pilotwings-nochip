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
