import asyncio
import logging
import sanic

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("control")

@API.route("/shut_down", methods={"POST"})
async def shutdown(request):
    request.json  # FIXME: Ignored.
    await request.app.apsis.shut_down()
    return sanic.response.json({})  # FIXME: Use response_json().


# ws /control/log

