import asyncio
import logging
import sanic

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("control")

@API.route("/shutdown", methods={"POST"})
async def shutdown(request):
    request.json  # FIXME: Ignored.

    for task in asyncio.Task.all_tasks():
        if not task.cancelled():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    log.info(f"done gathering tasks")

    asyncio.get_event_loop().stop()
    return sanic.response.json({})  # FIXME: Use response_json().


# ws /control/log
# POST /control/shutdown
