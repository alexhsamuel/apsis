import asyncio
import logging
import logging.handlers
import ora
import rich.highlighter
import rich.logging
import rich.text

import apsis.cmdline

#-------------------------------------------------------------------------------

LEVEL_STYLES = {
    "DEBUG"     : "color(249)",
    "INFO"      : "color(243)",
    "WARNING"   : "color(100)",
    "ERROR"     : "color(125)",
    "CRITICAL"  : "color(196) bold",
}

class Formatter(logging.Formatter):

    def formatMessage(self, record):
        time = ora.UNIX_EPOCH + record.created
        level = record.levelname
        level = f"[{LEVEL_STYLES[level]}]{level[0]}[/]"
        return (
            f"{time:%.3C} [color(24)]{record.name:24s}[/] {level} "
            f"{record.message}"
        )



class AccessFormatter(logging.Formatter):

    def formatMessage(self, record):
        time = ora.UNIX_EPOCH + record.created
        level = record.levelname
        level = f"[{LEVEL_STYLES[level]}]{level[0]}[/]"
        return (
            f"{time:%.3C} [color(24)]{record.name:24s}[/] {level} "
            f"{record.status} [color(59)]{record.request}[/] ({record.host})"
        )



class Handler(rich.logging.RichHandler):

    def render(self, *, record, traceback, message_renderable):
        return rich.text.Text.from_markup(str(message_renderable))
        


def configure(*, level="WARNING"):
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logging.basicConfig(
        level=level,
        format="%(message)",
        datefmt="[%X]",
        handlers=[Handler(console=apsis.cmdline.get_console())],
        # handlers=[rich.logging.RichHandler(
        #     highlighter=rich.highlighter.NullHighlighter(),
        #     markup=True,
        # )]
    )

    # Root logger's formatter.
    logging.getLogger().handlers[0].formatter = Formatter()
    # Quiet some noisy stuff.
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.INFO)
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



