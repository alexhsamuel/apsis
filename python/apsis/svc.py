import asyncio
from   cron import *
from   functools import partial
import logging
import sanic
import sanic.response
import websockets

from   apsis import scheduler
import apsis.testing

#-------------------------------------------------------------------------------

api = sanic.Blueprint("api_v1")

@api.route("/result")
async def result(request):
    from . import database
    jso = { j: 
            { i: [ r.to_jso() for r in rr ] for i, rr in ii.items() }
            for j, ii in database._results.items()
    }

    return sanic.response.json(jso)


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


WS_HANDLER = QueueHandler()

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
    logging.getLogger().handlers.append(WS_HANDLER)

    time = now()
    docket = scheduler.Docket(time)
    scheduler.schedule_insts(docket, apsis.testing.JOBS, time + 1 * 86400)

    event_loop = asyncio.get_event_loop()

    # Set off the handler.
    event_loop.call_soon(scheduler.docket_handler, docket)

    server = app.create_server(
        host="127.0.0.1",
        port=5000,
        debug=True,
        log_config=None,
    )
    app.running = True
    asyncio.ensure_future(server, loop=event_loop)

    try:
        event_loop.run_forever()
    finally:
        event_loop.close()


if __name__ == "__main__":
    main()

