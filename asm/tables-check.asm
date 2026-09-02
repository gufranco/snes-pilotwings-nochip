; Pilotwings without the DSP-1: assemble the four tables on their own.
;
; ===========================================================================
; WHAT THIS FILE IS FOR
; ===========================================================================
;
; This is not part of the replacement. It exists so the tables can be built
; without anything else around them and then compared, word for word, against
; the chip's own data.
;
; The comparison is the point. dsp1-tables.asm claims to reproduce the chip's
; four tables exactly, and a claim like that is worth nothing unless something
; checks it. Building this file puts 1,282 bytes at a known place in an
; otherwise empty image, so a check can read them straight out and hold them
; against the chip:
;
;     docker run --rm -v "$PWD:/work" -w /work <asar image> \
;         --no-title-check asm/tables-check.asm build/blank.sfc
;
; where build/blank.sfc is one megabyte of nothing. The tables then start at
; file offset $078000, and 640 of their 641 words match the chip. The odd one
; out is the 129th reciprocal entry, which this replacement adds for its own
; interpolation and the chip does not carry.
;
; ===========================================================================
; HOW TO READ THIS FILE IF YOU DO NOT KNOW ASSEMBLY
; ===========================================================================
;
;   lorom           Tells the assembler how addresses map onto positions in the
;                   ROM file. The SNES sees a cartridge as banks of memory; a
;                   file is just a run of bytes. "lorom" is the simpler and more
;                   common of the two arrangements, and it is what this cartridge
;                   uses. Under it, bank $0F address $8000 is file offset
;                   $078000, which is where the tables land.
;
;   org $0F8000     Sets where the next thing assembled goes. Nothing is placed
;                   until something is assembled; org only moves the position.
;
;   incsrc "..."    Assembles another file here, as though its text had been
;                   pasted in at this point.
;
; Bank $0F is chosen only because it is comfortably inside a one megabyte file
; and out of the way. Nothing about the tables depends on where they sit; the
; real build places them wherever there is room.
; ===========================================================================

lorom                                   ; the cartridge's address arrangement

org $0F8000                             ; file offset $078000, well inside 1 MB
incsrc "dsp1-tables.asm"                ; the four tables, and nothing else
