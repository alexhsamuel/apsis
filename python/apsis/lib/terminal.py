import sys

#-------------------------------------------------------------------------------

# Fix this at import time.
IS_TTY = sys.stdout.isatty()

if IS_TTY:
    SGR = lambda *cc: "\x1b[" + ";".join( str(c) for c in cc ) + "m"
else:
    SGR = lambda *cc: ""

RES = SGR( 0)
BLD = SGR( 1)
UND = SGR( 4)
NUN = SGR(24)
BLK = SGR(30)
RED = SGR(31)
GRN = SGR(32)
YEL = SGR(33)
BLU = SGR(34)
MAG = SGR(35)
CYN = SGR(36)
WHT = SGR(37)

COLOR = lambda n: SGR(38, 5, n)

