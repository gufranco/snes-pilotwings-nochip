; Pilotwings without the DSP-1: the four tables the chip interpolates from.
;
; ===========================================================================
; WHAT THIS FILE IS
; ===========================================================================
;
; The DSP-1 is an NEC uPD77C25, a small processor with its own program burned
; into it. Beside that program it keeps 1024 words of read-only data. Four
; numeric tables sit in those words, and every trigonometric answer the chip
; gives is interpolated from them.
;
; This file rebuilds those same four tables. It does not copy them: it computes
; them here, while the ROM is being built, from the formulas the chip's own
; values obey. Each formula below reproduces the chip's table entry for entry,
; with no entry differing at all.
;
; Nothing is checked in as data. A table worked out where it is used cannot
; drift away from the code that uses it, and a table pasted in as a block of
; numbers can. It would also be a copy of the chip's own contents, which never
; enters this repository.
;
; ===========================================================================
; THE FORMULAS, AND HOW THEY WERE FOUND
; ===========================================================================
;
;   reciprocal    128 words   round(2^22 / (128 + k)), clamped to 32767
;   sine          128 words   truncate(sin(pi k / 128) * 32768)
;   cosine        128 words   truncate(cos(pi k / 128) * 32768)
;   arccosine     256 words   round(acos(k / 256) * 32768 / pi)
;
; Three of those four differ from what this project previously recorded, which
; said all of them scaled by 32767 and rounded. That description was accepted
; because the search that found it allowed each entry to sit one unit away from
; the formula, and a one-unit tolerance is exactly large enough to hide the
; difference between rounding and truncating, and between 32767 and 32768.
; Under the old description 84 of the 256 sine and cosine entries were wrong.
; Under these four, none is.
;
; Two of the four truncate rather than round, and truncation here means toward
; zero rather than downward: the negative half of the cosine truncates upward.
; That is what a C cast to an integer does, which is a hint about how the tables
; were produced in the first place, and it is a full unit of difference on every
; entry that is not already whole.
;
; There is no square root and no arctangent, and nothing expected an arccosine.
; The four together are 1,282 bytes. A table covering every possible 16-bit
; input would be 131,072 bytes each, so carrying what the chip carries and
; interpolating the way it does is both far smaller and the only way to be right
; rather than close.
;
; Both chip revisions hold the same four tables, byte for byte. The DSP-1B keeps
; them two words earlier than the DSP-1, and that shift is the entire difference
; between their data areas, so whatever the DSP-1B fixed, it fixed in the
; program rather than in the numbers.
;
; ===========================================================================
; WHY THERE IS NO sin() CALL BELOW
; ===========================================================================
;
; The assembler has no floating point. That was checked rather than assumed: on
; both v1.81 and v1.91, 1.0/2*100 gives 0 and 3.14159*1000 gives 3000, so a
; decimal point in the source is read and then discarded. Its sin() returns 0
; for every input.
;
; What it does have is 64-bit whole numbers: 1<<40 and 1000000*1000000 both come
; out right. So every value below is computed in fixed point, which means whole
; numbers standing for fractions. A number here is a count of 1/2^30ths, so
; 2^30 means 1.0 and 2^29 means 0.5. Multiplying two such numbers gives a count
; of 1/2^60ths, and shifting right by 30 brings it back to the original scale.
; That shift is the only unusual thing in the arithmetic below.
;
; The largest intermediate is a product of two of these, which needs 60 bits and
; therefore fits the assembler's 64 with room to spare.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
; There is no code in this file. Not one processor instruction. It is a list of
; numbers, and everything else is the assembler working those numbers out.
;
;   ; text          A comment. Everything after a semicolon is ignored.
;
;   !NAME = 5       Names a value for the build. The exclamation mark marks it
;                   as the assembler's own variable. The SNES never sees it.
;
;   !NAME #= 5+1    The same, but "#=" means work the sum out now and keep the
;                   result. Plain "=" keeps the text "5+1" and re-reads it
;                   later, which inside a loop that refers to itself is wrong.
;
;   label:          A name for "the address this point lands at". Code elsewhere
;                   writes dsp1_sine and never needs to know the number.
;
;   dw 1234         Place a 16-bit number here, in the ROM, low byte first. This
;                   is the only thing in this file that produces bytes.
;
;   while cond      Repeat up to the matching endwhile while the condition
;   endwhile        holds. The loop runs during the build. The SNES sees only
;                   the numbers it produced, never a loop.
;
;   if / else       Chooses between alternatives during the build.
;
;   print "..."     Prints a line while building. Produces no bytes. Used at the
;                   end so a wrong loop bound shows up in the build log rather
;                   than as wrong graphics much later.
;
; ===========================================================================
; SATURATION, AND WHY ONE ENTRY IS SPECIAL
; ===========================================================================
;
; These tables hold signed 16-bit numbers, which run from -32,768 to +32,767.
;
; The reciprocal's first entry is 2^22 / 128, which is exactly 32,768. That is
; one too large to fit. The real chip stores 32,767 there, so it clamps to the
; largest value that fits rather than wrapping round to a negative number.
;
; The clamp has to be reproduced. Without it the one input that reaches that
; entry comes back with the wrong sign, and a sign error in a reciprocal turns
; the ground the wrong way up.
; ===========================================================================

; --- Fixed point scale -----------------------------------------------------
; !Q is how many bits of a value stand for the fraction, so !ONE is the fixed
; point form of 1.0. Shifting a product right by !Q undoes the doubling of scale
; that multiplying two of them caused.
!Q    = 30
!ONE  = 1073741824              ; 1<<30, meaning 1.0

; Pi at the same scale, worked out once: round(pi * 2^30) and round(pi/2 * 2^30).
!PI     = 3373259426
!HALFPI = 1686629713

; The largest value a signed 16-bit word holds, used as the clamp.
!HIGHEST = 32767

; --- Scratch ---------------------------------------------------------------
; Declared before the loops because the assembler reads a define before the loop
; body has run once, and a define that does not exist yet is an error.
!value  = 0
!angle  = 0
!term   = 0
!total  = 0
!sq     = 0
!n      = 0
!lo     = 0
!hi     = 0
!mid    = 0
!target = 0
!probe  = 0

; ---------------------------------------------------------------------------
; TABLE 1 OF 4: the reciprocal, round(2^22 / (128 + k))
;
; A reciprocal table is how a chip with no divide instruction divides: to work
; out a/b it looks up 1/b and multiplies. The 2^22 on top is a fixed scale that
; keeps the results large enough to stay accurate as whole numbers.
;
; The assembler divides whole numbers and throws the remainder away, so a plain
; 4194304/(128+k) would come out one too low wherever there is a remainder.
; Adding half the divisor before dividing rounds instead:
;
;     round(a/d) is (2a + d) / (2d)
;
; With a = 2^22 that is (8388608 + d) / (2d), which is the line below.
;
; 129 entries, where the chip holds 128. The chip's table is 128 words and the
; word after it belongs to something else: searching its data for 128 entries
; finds them at word 101, and searching for 129 finds nothing anywhere.
;
; The 129th entry here is this replacement's own addition, not a copy of
; anything. Interpolating between the final pair of entries needs the value just
; past the end, and without it the last step would have to guess. It is computed
; by the same formula, so it continues the table rather than inventing a value.
;
; 129 entries x 2 bytes = 258 bytes, of which 256 match the chip.
; ---------------------------------------------------------------------------
dsp1_reciprocal:                        ; address where this table begins
!k = 0                                  ; entry counter
while !k < 129
    !value #= (8388608+(128+!k))/(2*(128+!k))    ; round(2^22 / (128+k))
    if !value > !HIGHEST                         ; does it overflow a word?
        dw !HIGHEST                              ; yes: clamp, as the chip does
    else
        dw !value                                ; no: store it as it stands
    endif
    !k #= !k+1
endwhile
dsp1_reciprocal_end:

; ---------------------------------------------------------------------------
; TABLE 2 OF 4: the sine, truncate(sin(pi k / 128) * 32768)
;
; k runs 0 to 127, so pi k / 128 runs from 0 to just under pi: half a full turn.
; The chip stores only that half. The other half is the same values negated, and
; whichever routine reads the table supplies the sign.
;
; The sine comes from its Taylor series, the sum
;
;     x - x^3/3! + x^5/5! - x^7/7! + ...
;
; Each term is the one before it multiplied by -x^2 and divided by two rising
; numbers. Seven terms are taken, which is more than enough here because the
; argument is first folded into 0..pi/2 using sin(pi - x) = sin(x), and the
; series converges fastest for small arguments.
;
; The last step multiplies by 32768 and shifts back down by 30, which truncates.
; Truncating is what the chip does, so this reproduces its behaviour rather than
; taking a shortcut.
;
; 128 entries x 2 bytes = 256 bytes.
; ---------------------------------------------------------------------------
dsp1_sine:
!k = 0
while !k < 128
    ; Fold into 0..pi/2 using sin(pi - x) = sin(x).
    if !k <= 64
        !angle #= (!PI*!k)/128
    else
        !angle #= (!PI*(128-!k))/128
    endif

    !sq    #= (!angle*!angle)>>!Q       ; x^2, back at Q30
    !term  #= !angle                    ; first term is x itself
    !total #= !angle
    !n = 2
    while !n < 9                        ; seven further terms
        !term  #= (0-(!term*!sq))>>!Q       ; multiply by -x^2, back to Q30
        !term  #= !term/((2*!n-1)*(2*!n-2)) ; divide by the two rising numbers
        !total #= !total+!term
        !n #= !n+1
    endwhile

    !value #= (!total*32768)>>!Q        ; to the chip's scale, truncating
    if !value > !HIGHEST
        dw !HIGHEST
    else
        dw !value
    endif
    !k #= !k+1
endwhile
dsp1_sine_end:

; ---------------------------------------------------------------------------
; TABLE 3 OF 4: the cosine, truncate(cos(pi k / 128) * 32768)
;
; The same series, reached through cos(x) = sin(pi/2 - x). Past a quarter turn
; the cosine is negative, and there the magnitude is worked out from
; cos(x) = -sin(x - pi/2) and negated at the end.
;
; Negating at the end is what makes this truncate toward zero rather than
; downward, which is what the chip does: -804 rather than -805. Shifting a
; negative number right in the assembler rounds the other way, and every
; negative entry would be one out.
;
; The table is kept separate rather than read from the sine at an offset. The
; chip carries both, and a replacement sharing one table would reach the same
; values by a different route. That difference stays invisible until it is wrong
; at an edge, and then it is very hard to find.
;
; 128 entries x 2 bytes = 256 bytes.
; ---------------------------------------------------------------------------
dsp1_cosine:
!k = 0
while !k < 128
    if !k <= 64
        !angle #= (!PI*(64-!k))/128     ; cos(x) = sin(pi/2 - x)
    else
        !angle #= (!PI*(!k-64))/128     ; magnitude only; negated below
    endif

    !sq    #= (!angle*!angle)>>!Q
    !term  #= !angle
    !total #= !angle
    !n = 2
    while !n < 9
        !term  #= (0-(!term*!sq))>>!Q
        !term  #= !term/((2*!n-1)*(2*!n-2))
        !total #= !total+!term
        !n #= !n+1
    endwhile

    !value #= (!total*32768)>>!Q
    if !value > !HIGHEST
        !value #= !HIGHEST
    endif
    if !k <= 64
        dw !value                       ; first quarter turn: positive
    else
        dw 0-!value                     ; past a quarter turn: negative
    endif
    !k #= !k+1
endwhile
dsp1_cosine_end:

; ---------------------------------------------------------------------------
; TABLE 4 OF 4: the arccosine, round(acos(k / 256) * 32768 / pi)
;
; The inverse of a cosine: given a ratio, give back the angle. k/256 runs from 0
; to just under 1, and the angle runs from a quarter turn down to nothing.
; Dividing by pi and scaling by 32768 expresses the angle as a fraction of half
; a turn, which is the form the chip's own angle arithmetic uses.
;
; No series for an inverse cosine behaves well across this whole range, so this
; searches instead. The cosine falls steadily from 1 to -1 as the angle goes
; from 0 to pi, so for each k the angle whose cosine equals k/256 can be found
; by repeatedly halving the interval that must contain it. Forty halvings settle
; a Q30 range exactly.
;
; The rounding at the end is why the search runs at full precision and converts
; afterwards rather than searching directly in units of 32768. A search in the
; coarse unit finds where the cosine crosses, which is not the same as the
; nearest whole angle, and 132 of the 256 entries came out one low when it was
; done that way.
;
; This is the widest of the four and the least used. Command $0a is the only
; command that reads it at all, measured by watching every data-read the chip
; made while it ran the game's own command stream. $0a is the command that draws
; the ground: one call, then 176 or 191 four-word answers read back, one per
; scanline.
;
; 256 entries x 2 bytes = 512 bytes.
; ---------------------------------------------------------------------------
dsp1_arccosine:
!k = 0
while !k < 256
    !target #= (!k*!ONE)/256            ; the ratio k/256, in Q30
    !lo = 0                             ; the angle lies somewhere in 0..pi
    !hi #= !PI
    !n = 0
    while !n < 40                       ; forty halvings settle Q30 exactly
        !mid #= (!lo+!hi)/2

        ; cos(mid), by the same series and the same fold as the cosine table.
        if !mid <= !HALFPI
            !angle #= !HALFPI-!mid
        else
            !angle #= !mid-!HALFPI
        endif
        !sq    #= (!angle*!angle)>>!Q
        !term  #= !angle
        !total #= !angle
        !probe = 2
        while !probe < 9
            !term  #= (0-(!term*!sq))>>!Q
            !term  #= !term/((2*!probe-1)*(2*!probe-2))
            !total #= !total+!term
            !probe #= !probe+1
        endwhile
        if !mid > !HALFPI
            !total #= 0-!total          ; past a quarter turn the cosine is negative
        endif

        if !total > !target             ; the cosine falls, so a larger cosine
            !lo #= !mid+1               ; means the angle is still too small
        else
            !hi #= !mid
        endif
        !n #= !n+1
    endwhile

    ; Convert the Q30 angle to the chip's unit and round: (a*32768*2/pi + 1)/2.
    dw ((!lo*65536)/!PI+1)/2
    !k #= !k+1
endwhile
dsp1_arccosine_end:

; ---------------------------------------------------------------------------
; Build-time report.
;
; Subtracting a start label from an end label gives the size in bytes. Printing
; each against the figure it should be means a mistake in a loop bound shows up
; in the build log immediately.
; ---------------------------------------------------------------------------
print "reciprocal ", dec(dsp1_reciprocal_end-dsp1_reciprocal), " bytes of 258, 256 of them the chip's"
print "sine       ", dec(dsp1_sine_end-dsp1_sine), " bytes of 256"
print "cosine     ", dec(dsp1_cosine_end-dsp1_cosine), " bytes of 256"
print "arccosine  ", dec(dsp1_arccosine_end-dsp1_arccosine), " bytes of 512"
print "all four   ", dec(dsp1_arccosine_end-dsp1_reciprocal), " bytes of 1282"
