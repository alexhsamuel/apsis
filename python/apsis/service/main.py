import asyncio
import argparse
import logging
from   pathlib import Path
import sanic
import sanic.response
import sanic.router
import time
import ujson as json
import websockets

from   . import api, control
from   . import DEFAULT_PORT
from   ..apsis import Apsis
from   ..jobs import JobsDir
from   ..sqlite import SqliteDB

#-------------------------------------------------------------------------------

LOG_FORMATTER = logging.Formatter(
    fmt="%(asctime)s %(name)-24s [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S",
)
LOG_FORMATTER.converter = time.gmtime  # FIXME: Use cron.Time?

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


WS_HANDLER = QueueHandler(10000, LOG_FORMATTER)

#-------------------------------------------------------------------------------

SANIC_LOG_CONFIG = {
    **sanic.log.LOGGING_CONFIG_DEFAULTS,
    "formatters": {
        "generic": {
            "class": "logging.Formatter",
            "format": "%(asctime)s %(name)-24s [%(levelname)-7s] %(message)s",
            "datefmt": LOG_FORMATTER.datefmt,
        },
        "access": {
            "class": "logging.Formatter",
            "format": "%(asctime)s %(name)-24s [%(levelname)-7s] [%(host)s %(request)s %(status)d %(byte)d] %(message)s",
            "datefmt": LOG_FORMATTER.datefmt,
        },
    }
}    
    
#-------------------------------------------------------------------------------

class Router(sanic.router.Router):
    """
    Extended router that supports a catch-all path for missing pages.
    """

    CATCH_ALL_PATH = "/index.html"

    def get(self, request):
        logging.info(request.url)
        try:
            return super().get(request)
        except sanic.router.NotFound:
            return self._get(self.CATCH_ALL_PATH, request.method, "")



app = sanic.Sanic(__name__, router=Router(), log_config=SANIC_LOG_CONFIG)
app.config.LOGO = None

top_dir = Path(__file__).parents[3]

app.blueprint(api.API, url_prefix="/api/v1")
app.blueprint(control.API, url_prefix="/api/control")

# The SPA.
app.static("/index.html", str(top_dir / "vue" / "dist" / "index.html"))
# Web assets.
app.static("/static", str(top_dir / "vue" / "dist" / "static"))

@app.websocket("/api/log")
async def websocket_log(request, ws):
    queue = WS_HANDLER.register()
    try:
        while True:
            lines = await queue.get()
            data = json.dumps(lines)
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                break
    finally:
        WS_HANDLER.unregister(queue)


#-------------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().handlers[0].formatter = LOG_FORMATTER
    logging.getLogger().handlers.append(WS_HANDLER)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="run in debug mode")
    parser.add_argument(
        "--log-level", metavar="LEVEL", default="INFO",
        help="log at LEVEL [def: INFO]")
    # FIXME: Can't use localhost on OSX, where it resolves to an IPV6 address,
    # until we pick up this Sanic fix:
    # https://github.com/channelcat/sanic/pull/1053
    parser.add_argument(
        "--host", metavar="HOST", default="127.0.0.1",
        help="server host address")
    parser.add_argument(
        "--port", metavar="PORT", type=int, default=DEFAULT_PORT,
        help="server port")
    parser.add_argument(
        "--create", action="store_true", default=False,
        help="create a new state file and exit")
    parser.add_argument(
        "jobs", metavar="JOBS", 
        help="job directory")
    parser.add_argument(
        "state_path", metavar="PATH",
        help="state file")
    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    if args.create:
        SqliteDB.create(args.state_path)
        raise SystemExit(0)

    log.info(f"opening state file {args.state_path}")
    db      = SqliteDB.open(args.state_path)
    log.info(f"opening jobs dir {args.jobs}")
    jobs    = JobsDir(args.jobs)
    log.info("creating scheduler instance")
    apsis   = Apsis(jobs, db)

    app.apsis   = apsis
    app.running = True

    # Set up the HTTP server.
    log.info("creating HTTP service")
    server  = app.create_server(
        host        =args.host,
        port        =args.port,
        debug       =args.debug,
    )
    asyncio.ensure_future(server)

    log.info("scheduler ready to run")
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print()
    finally:
        loop.close()


if __name__ == "__main__":
    main()

