import asyncio
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
ACCESS_COLOR = COLOR(0x3b)


class Formatter(logging.Formatter):

    def formatMessage(self, record):
        time = ora.UNIX_EPOCH + record.created
        level = LEVEL_NAMES[record.levelname]
        return (
            f"{time:%.3C} {NAME_COLOR}{record.name:24s}{BLK} {level} "
            f"{record.message}"
        )



class AccessFormatter(logging.Formatter):

    def formatMessage(self, record):
        time = ora.UNIX_EPOCH + record.created
        level = LEVEL_NAMES[record.levelname]
        return (
            f"{time:%.3C} {NAME_COLOR}{record.name:24s}{BLK} {level} "
            f"{record.status} {ACCESS_COLOR}{record.request}{BLK} ({record.host})"
        )



def configure(*, level="WARNING"):
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logging.basicConfig(level=level)

    # Root logger's formatter.
    logging.getLogger().handlers[0].formatter = Formatter()
    # Quiet some noisy stuff.
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)


#-------------------------------------------------------------------------------

class QueueHandler(logging.Handler):
    """
    Publishes formatted log messages to registered async queues.
    """

    def __init__(self, length=1000, formatter=None):
        if formatter is None:
            formatter = logging.Formatter()

        super().__init__()
        self.__formatter = formatter
        self.__length = length
        self.__buffer = []
        self.__queues = []


    def register(self, length=None) -> asyncio.Queue:
        """
        Returns a new queue, to which log records will be published.
        """
        length = self.__length if length is None else min(self.__length, length)

        queue = asyncio.Queue()
        self.__queues.append(queue)

        # Send old messages.
        lines = self.__buffer[-length :]
        queue.put_nowait(lines)

        return queue


    def unregister(self, queue):
        """
        Removes a previously registered queue.
        """
        self.__queues.remove(queue)


    def emit(self, record):
        line = self.__formatter.format(record)

        # Store the log line in the buffer, for later connections.
        self.__buffer.append(line)
        if len(self.__buffer) > self.__length:
            del self.__buffer[: -self.__length]

        for queue in list(self.__queues):
            try:
                queue.put_nowait([line])
            except asyncio.QueueFull:
                pass


    def shut_down(self):
        """
        Signal to listeners to shut down.
        """
        for queue in list(self.__queues):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass



