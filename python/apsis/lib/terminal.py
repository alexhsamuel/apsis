import sys

#-------------------------------------------------------------------------------

if sys.stdout.isatty():
    SGR = lambda *cc: "\x1b[" + ";".join( str(c) for c in cc ) + "m"
else:
    SGR = lambda *cc: ""

BLD = SGR( 1)
NBL = SGR( 0)
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

