import logging
import sanic

from   apsis.lib.api import response_json


log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("control")

@API.route("/shut_down", methods={"POST"})
async def shutdown(request):
    request.json  # FIXME: Ignored.
    await request.app.apsis.shut_down()
    return response_json({})


# ws /control/log

