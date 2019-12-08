import logging
import os
import sanic
import signal
import urllib.parse

import apsis.apsis
from   apsis.lib.api import response_json

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("control")

@API.route("/reload_jobs", methods={"POST"})
async def on_reload_jobs(request):
    # FIXME: Handle errors.
    rem_ids, add_ids, chg_ids = await apsis.apsis.reload_jobs(request.app.apsis)
    return response_json({
        "removed"   : rem_ids,
        "added"     : add_ids,
        "changed"   : chg_ids,
    })


# FIXME: Reload a single job id?

@API.route("/shut_down", methods={"POST"})
async def on_shut_down(request):
    # Sanic ignores query params without values.
    restart = "restart" in urllib.parse.parse_qs(request.query_string, True)
    request.json  # FIXME: Ignored.

    # Request to restart after shutdown.
    log.info(f"shut down starting; restart={restart}")
    request.app.restart = restart

    # Shut down the application.
    os.kill(os.getpid(), signal.SIGTERM)

    # shut_down() calls loop.stop(), so no further scheduled callbacks will be
    # invoked.  We need to respond to the request with no further await. (?)
    return response_json({})


# ws /control/log

