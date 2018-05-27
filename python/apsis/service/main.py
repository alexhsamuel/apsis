import asyncio
import argparse
import logging
from   pathlib import Path
import sanic
import sanic.response
import time
import websockets

from   . import api
from   . import DEFAULT_PORT
from   .. import crontab, repo, state, testing

#-------------------------------------------------------------------------------

LOG_FORMATTER = logging.Formatter(
    fmt="%(asctime)s %(name)-18s [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S"
)
LOG_FORMATTER.converter = time.gmtime  # FIXME: Use cron.Time?

#-------------------------------------------------------------------------------

class QueueHandler(logging.Handler):
    """
    Publishes formatted log messages to registered async queues.
    """

    def __init__(self, formatter=None):
        if formatter is None:
            formatter = logging.Formatter()

        super().__init__()
        self.__formatter = formatter
        self.__queues = []


    def register(self) -> asyncio.Queue:
        """
        Returns a new queue, to which log records will be published.
        """
        queue = asyncio.Queue()
        self.__queues.append(queue)
        return queue


    def unregister(self, queue):
        """
        Removes a previously registered queue.
        """
        self.__queues.remove(queue)


    def emit(self, record):
        data = self.__formatter.format(record)
        for queue in list(self.__queues):
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                pass


WS_HANDLER = QueueHandler(LOG_FORMATTER)

#-------------------------------------------------------------------------------

app = sanic.Sanic(__name__, log_config=None)
app.config.LOGO = None

top_dir = Path(__file__).parents[3]

app.blueprint(api.API, url_prefix="/api/v1")
app.static("/static", str(top_dir / "web"))

@app.websocket("/log")
async def websocket_log(request, ws):
    queue = WS_HANDLER.register()
    try:
        while True:
            try:
                await ws.send(await queue.get())
            except websockets.ConnectionClosed:
                break
    finally:
        WS_HANDLER.unregister(queue)

app.static("/.*", str(top_dir / "web" / "index.html"))

#-------------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().handlers[0].formatter = LOG_FORMATTER
    logging.getLogger().handlers.append(WS_HANDLER)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="run in debug mode")
    parser.add_argument(
        "--host", metavar="HOST", default="localhost",
        help="server host address")
    parser.add_argument(
        "--port", metavar="PORT", type=int, default=DEFAULT_PORT,
        help="server port")
    parser.add_argument(
        "--crontab", action="store_true", default=False,
        help="JOBS in a crontab file")
    parser.add_argument(
        "jobs", metavar="JOBS", 
        help="job directory")
    args = parser.parse_args()

    if args.crontab:
        _, jobs = crontab.read_crontab_file(args.crontab)
    else:
        jobs = repo.load_yaml_files(args.jobs)
    for j in jobs:
        state.STATE.add_job(j)

    for job in testing.JOBS:
        state.STATE.add_job(job)

    # Kick off the docket.
    state.start_docket(state.STATE.docket)

    server = app.create_server(
        host        =args.host,
        port        =args.port,
        debug       =args.debug,
    )
    app.running = True
    asyncio.ensure_future(server)

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print()
    finally:
        loop.close()


if __name__ == "__main__":
    main()

