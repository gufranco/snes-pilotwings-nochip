; Assemble the decoded command routines on their own, so a check can run them.
;
; Not part of the replacement. ops-check.py places arguments in the direct page,
; runs one routine on the processor model, and compares the answer with what the
; real chip gives for the same command. This file exists only to put the
; routines at an address that check knows.
;
; Bank $0F address $8000 is file offset $078000 under low ROM addressing, which
; is comfortably inside a one megabyte image and out of the way of anything.

lorom

org $0F8000
incsrc "dsp1-ops.asm"

print "mul16 at ", hex(mul16)
print "op_00 at ", hex(op_00)
print "op_08 at ", hex(op_08)
