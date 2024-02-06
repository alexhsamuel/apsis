import logging
import sanic

from   apsis.lib.api import error, response_json
import apsis.program.procstar.agent

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

def get_server():
    return apsis.program.procstar.agent.SERVER


API = sanic.Blueprint("procstar")

@API.route("/connections")
def on_connections(request):
    """
    Returns a mapping from conn ID to connection info.
    """
    server = get_server()
    if server is None:
        return error("no Procstar server running")
    return response_json({
        i: c.to_jso()
        for i, c in server.connections.items()
    })


@API.route("/groups")
def on_groups(request):
    """
    Returns a mapping from group ID to list of connection info.
    """
    server = get_server()
    if server is None:
        return error("no Procstar server running")
    return response_json({
        i: [ server.connections[c].to_jso() for c in g ]
        for i, g in server.connections.groups.items()
    })


