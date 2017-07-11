import json  # FIXME: ujson?
import logging
import sanic
import websockets

from   .state import state

log = logging.getLogger("api/v1")

#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

def response_json(jso):
    return sanic.response.json(jso, indent=1, sort_keys=True)


#-------------------------------------------------------------------------------
# Jobs

def job_to_jso(app, job):
    jso = job.to_jso()
    jso["url"] = app.url_for("v1.job", job_id=job.job_id)
    return jso


@API.route("/jobs/<job_id>")
async def job(request, job_id):
    jso = state.get_job(job_id).to_jso()
    return response_json(jso)


@API.route("/jobs")
async def jobs(request):
    jso = [ 
        job_to_jso(request.app, j) 
        for j in state.get_jobs() 
    ]
    return response_json(jso)


#-------------------------------------------------------------------------------
# Results

def result_to_jso(app, result):
    jso = result.to_jso()
    jso.update({
        "url"       : app.url_for("v1.result", run_id=result.run.run_id),
        # FIXME: "run_url"
        # FIXME: "inst_url"
        "job_url"   : app.url_for("v1.job", job_id=result.run.inst.job.job_id),
        "output_url": app.url_for("v1.result_output", run_id=result.run.run_id),
        "output_len": 0 if result.output is None else len(result.output),
    })
    return jso


@API.route("/results/<run_id>")
async def result(request, run_id):
    jso = result_to_jso(request.app, state.get_result(run_id))
    return response_json(jso)


@API.route("/results/<run_id>/output")
async def result_output(request, run_id):
    output = state.get_result(run_id).output
    return sanic.response.raw(output)


def _results_filter(args):
    """
    Constructs a filter for results from request arguments.
    """
    job_ids = args.pop("job_id", None)

    def filter(results):
        if job_ids is not None:
            results = ( 
                r for r in results 
                if any( r.run.inst.job.job_id == i for i in job_ids )
            )
        return results

    return filter


@API.route("/results")
async def results(request):
    since,  = request.args.pop("since", (None, ))
    until,  = request.args.pop("until", (None, ))
    filter  = _results_filter(request.args)
    when, results = await state.results.query(since=since, until=until)
    results = filter(results)

    jso = {
        "when": when,
        "results": [ result_to_jso(request.app, r) for r in results ]
    }
    return response_json(jso)


@API.websocket("/results-live")  # FIXME: Do we really need this?
async def websocket_results(request, ws):
    since,  = request.args.pop("since", (None, ))
    filter  = _results_filter(request.args)

    log.info("live results connect")
    with state.results.query_live(since=since) as queue:
        while True:
            # FIXME: If the socket closes, clean up instead of blocking until
            # the next result is available.
            results = await queue.get()
            results = filter(results)
            jso     = {
                "results": [ r.to_jso() for r in results ],
            }
            try:
                await ws.send(json.dumps(jso))
            except websockets.ConnectionClosed:
                break
    log.info("live results disconnect")

    
