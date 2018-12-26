import asyncio
import logging
from   pathlib import Path
import sanic
import sanic.response
import sanic.router
import signal
import sys
import ujson as json
import websockets

from   . import api, control
from   . import DEFAULT_PORT
from   ..apsis import Apsis
from   ..jobs import JobsDir
from   ..lib.async import cancel_task
from   ..sqlite import SqliteDB
import apsis.lib.logging

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# Logging handler that queues up log messages for serving to clients.
WS_HANDLER = apsis.lib.logging.QueueHandler(
    10000, 
    logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d %(name)-24s [%(levelname)-7s] %(message)s",
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

app.blueprint(api.API, url_prefix="/api/v1")
app.blueprint(control.API, url_prefix="/api/control")

vue_dir = Path(__file__).parent / "vue"
print(vue_dir)
assert vue_dir.is_dir()

# The SPA.
app.static("/index.html", str(vue_dir / "index.html"))
# Web assets.
app.static("/static", str(vue_dir / "static"))

@app.websocket("/api/log")
async def websocket_log(request, ws):
    queue = WS_HANDLER.register()
    try:
        while True:
            lines = await queue.get()
            if lines is None:
                log.info("closing log websocket")
                await ws.close()
                break
            data = json.dumps(lines)
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                log.info("websocket log closed")
                break
    finally:
        WS_HANDLER.unregister(queue)


#-------------------------------------------------------------------------------

def serve(jobs_path, state_path, host="127.0.0.1", port=DEFAULT_PORT, debug=False):
    """
    Runs the Apsis service.

    :return:
      True if the service should be restarted on exit.
    """
    # Install the websocket logging handler.
    root_log = logging.getLogger()
    root_log.handlers.append(WS_HANDLER)

    log.info(f"opening state file {state_path}")
    db      = SqliteDB.open(state_path)
    log.info(f"opening jobs dir {jobs_path}")
    jobs    = JobsDir(jobs_path)
    log.info("creating scheduler instance")
    apsis   = Apsis(jobs, db)

    app.apsis = apsis
    # Flag to indicate whether to restart after shutting down.
    app.restart = False
    app.running = True  # FIXME: ??  Remove?
 
    # Set up the HTTP server.
    log.info("creating HTTP service")
    server = app.create_server(
        host        =host,
        port        =port,
        debug       =debug,
    )
    server_task = asyncio.ensure_future(server)

    # Shut down on signals; this is the correct way to request shutdown.
    def on_shutdown(signum, stack_frame):
        if signum == signal.SIGINT:
            # If this was actually from the keyboard, there'll be a ^C to the
            # console without a newline; add it.
            print()
        log.error(f"caught {signal.Signals(signum).name}")

        async def stop():
            try:
                # Stop enqueuing log messages.
                log.info("removing logging websocket handler")
                root_log.handlers.remove(WS_HANDLER)

                log.info("shutting down logging websockets")
                WS_HANDLER.shut_down()

                # Shut down Apsis and all its bits.
                await apsis.shut_down()

                # Shut down the Sanic web service.
                await cancel_task(server_task, "Sanic", log)

            finally:
                # Then tell the asyncio event loop to stop.
                log.info("stopping event loop")
                asyncio.get_event_loop().stop()

        asyncio.ensure_future(stop())

    signal.signal(signal.SIGINT , on_shutdown)  # instead of KeyboardInterrupt
    signal.signal(signal.SIGTERM, on_shutdown)

    log.info("service ready to run")
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    finally:
        # Explicitly close the loop, so we find out about any pending tasks
        # we have incorrectly left behind.
        loop.close()
    log.info("service done")

    return app.restart


