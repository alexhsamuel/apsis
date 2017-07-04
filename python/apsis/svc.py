import asyncio
from   cron import *
import logging
import sanic
import sanic.response

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


app = sanic.Sanic(__name__, log_config=None)

app.blueprint(api, url_prefix="/api/v1")

def main():
    logging.basicConfig(level=logging.INFO)

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

