import sanic

from   .state import state

#-------------------------------------------------------------------------------

API = sanic.Blueprint("api-v1")

@API.route("/jobs")
async def jobs(request):
    return sanic.response.json([ j.to_jso() for j in state.get_jobs() ])


@API.route("/results")
async def results(request):
    return sanic.response.json([ r.to_jso() for r in state.get_results() ])


