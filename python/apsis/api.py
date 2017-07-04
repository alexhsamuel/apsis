import sanic

from   . import state

#-------------------------------------------------------------------------------

API = sanic.Blueprint("api-v1")

@API.route("/result")
async def result(request):
    return sanic.response.json([ r.to_jso() for r in state._results ])


