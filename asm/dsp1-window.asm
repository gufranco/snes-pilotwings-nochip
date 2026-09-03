; Pilotwings without the DSP-1: the bank the redirected accesses land in.
;
; This is data rather than code, and it lives in its own file for exactly that
; reason. It used to sit at the bottom of dsp1-port.asm, where its `org` moved
; the assembler into bank $7D and every file included after the port landed on
; top of it. dsp1-ground.asm was the first one to, and it assembled over the
; window silently.
;
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
