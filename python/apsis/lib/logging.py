import logging
import ora

from   .terminal import COLOR, BLK, BLD, NBL

#-------------------------------------------------------------------------------

LEVEL_NAMES = {
    "DEBUG"     : COLOR(0xf9) + "[d]" + BLK,
    "INFO"      : COLOR(0xf3) + "[i]" + BLK,
    "WARNING"   : COLOR(0x64) + "[w]" + BLK,
    "ERROR"     : COLOR(0x7d) + "[E]" + BLK,
    "CRITICAL"  : COLOR(0xc4) + BLD + "[C]" + NBL + BLK,
}

NAME_COLOR = COLOR(0x11)

class Formatter(logging.Formatter):

    def formatMessage(self, record):
        r = record
        time = ora.UNIX_EPOCH + r.created
        level = LEVEL_NAMES[r.levelname]
        return f"{time:%.3C} {NAME_COLOR}{r.name:20s}{BLK} {level} {r.message}"


