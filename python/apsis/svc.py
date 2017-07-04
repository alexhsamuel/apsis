import asyncio
from   cron import *
from   functools import partial
import logging
import sanic
import sanic.response
import time
import websockets

from   apsis import scheduler, state
import apsis.testing

#-------------------------------------------------------------------------------

LOG_FORMATTER = logging.Formatter(
    fmt="%(asctime)s %(name)-16s [%(levelname)-7s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ"
)
LOG_FORMATTER.converter = time.gmtime  # FIXME: Use cron.Time?

#-------------------------------------------------------------------------------

api = sanic.Blueprint("api_v1")

@api.route("/result")
async def result(request):
    results = (
        r for j in state._results.values() for i in j.values() for r in i )
    return sanic.response.json([ r.to_jso() for r in results ])


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

@api.websocket("/log")
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


#-------------------------------------------------------------------------------

@api.websocket("/update")
async def update(request, ws):
    while True:
        await ws.send("update!\n")
        await asyncio.sleep(1)


app = sanic.Sanic(__name__, log_config=None)
app.config.LOGO = None

app.static("/static", "./static")
app.blueprint(api, url_prefix="/api/v1")

def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().handlers[0].formatter = LOG_FORMATTER
    logging.getLogger().handlers.append(WS_HANDLER)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    time = now()
    docket = scheduler.Docket(time)
    scheduler.schedule_insts(docket, apsis.testing.JOBS, time + 1 * 86400)

    loop = asyncio.get_event_loop()

    # Set off the recurring handler.
    loop.call_soon(scheduler.docket_handler, docket)

    server = app.create_server(
        host="127.0.0.1",
        port=5000,
        debug=True,
        log_config=None,
    )
    app.running = True
    asyncio.ensure_future(server, loop=loop)

    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == "__main__":
    main()

