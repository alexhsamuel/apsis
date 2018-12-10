import logging
import sanic
import urllib.parse

from   apsis.lib.api import response_json

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("control")

@API.route("/shut_down", methods={"POST"})
async def shut_down(request):
    # Sanic ignores query params without values.
    restart = "restart" in urllib.parse.parse_qs(request.query_string, True)
    request.json  # FIXME: Ignored.

    # Request to restart after shutdown.
    log.info(f"shut down starting; restart={restart}")
    request.app.restart = restart

    # Shut down Apsis and the event loop.
    await request.app.apsis.shut_down()
    # shut_down() calls loop.stop(), so no further scheduled callbacks will be
    # invoked.  We need to respond to the request with no further await. (?)
    return response_json({})


# ws /control/log

