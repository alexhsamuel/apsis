import asyncio
import argparse
import logging
from   pathlib import Path
import sanic
import sanic.response
import sanic.router
import ujson as json
import websockets

from   . import api, control
from   . import DEFAULT_PORT
from   ..apsis import Apsis
from   ..jobs import JobsDir
from   ..sqlite import SqliteDB
import apsis.lib.logging

#-------------------------------------------------------------------------------

LOG_FORMATTER = apsis.lib.logging.Formatter()

# Logging handler that queues up log messages for serving to clients.
WS_HANDLER = apsis.lib.logging.QueueHandler(
    10000, 
    logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d %(name)-20s [%(levelname)-7s] %(message)s",
        datefmt="%H:%M:%S",
    )
)

SANIC_LOG_CONFIG = {
    **sanic.log.LOGGING_CONFIG_DEFAULTS,
    "formatters": {
        "generic": {
            "class": "apsis.lib.logging.Formatter",
        },
        "access": {
            "class": "apsis.lib.logging.AccessFormatter",
            "propagate": False,
        },
    }
}    
    
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
    logging.getLogger("websockets.protocol").setLevel(logging.INFO)

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

