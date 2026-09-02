; Assemble the decoded command routines on their own, so a check can run them.
;
; Not part of the replacement. routines.retail.test.py places arguments in the
; direct page, runs one routine on the processor model, and compares the answer
; with what the real chip gives for the same command. This file exists only to
; put the routines and the tables they read at addresses that check knows.
;
; Bank $0F address $8000 is file offset $078000 under low ROM addressing. The
; derived tables are 393,216 bytes and go above the routines, at bank $20, which
; is file offset $100000, so the image has to be at least 2 megabytes for this
; to have somewhere to land.

lorom

org $0F8000
incsrc "dsp1-ops.asm"

org $208000
incsrc "dsp1-derived.asm"

print "mul16 at ", hex(mul16)
print "op_00 at ", hex(op_00)
print "op_08 at ", hex(op_08)
print "op_04 at ", hex(op_04)
