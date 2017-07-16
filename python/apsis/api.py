import json  # FIXME: ujson?
import logging
import sanic
import websockets

from   .state import STATE

log = logging.getLogger("api/v1")

#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

def response_json(jso):
    return sanic.response.json(jso, indent=1, sort_keys=True)


#-------------------------------------------------------------------------------
# Jobs

def job_to_jso(app, job):
    jso = job.to_jso()
    jso.update({
        "url"           : app.url_for("v1.job", job_id=job.job_id),
        "program_str"   : str(job.program),
    })
    for schedule, schedule_jso in zip(job.schedules, jso["schedules"]):
        schedule_jso["str"] = str(schedule)
    return jso


@API.route("/jobs/<job_id>")
async def job(request, job_id):
    jso = job_to_jso(request.app, STATE.get_job(job_id))
    return response_json(jso)


@API.route("/jobs")
async def jobs(request):
    jso = [ 
        job_to_jso(request.app, j) 
        for j in STATE.get_jobs() 
    ]
    return response_json(jso)


#-------------------------------------------------------------------------------
# Runs

def run_to_jso(app, run):
    jso = run.to_jso()
    jso.update({
        "url"       : app.url_for("v1.run", run_id=run.run_id),
        "args"      : run.inst.args,
        # FIXME: "run_url"
        # FIXME: "inst_url"
        "job_url"   : app.url_for("v1.job", job_id=run.inst.job.job_id),
        "output_url": app.url_for("v1.run_output", run_id=run.run_id),
    })
    if run.output is not None:
        jso["output_len"] = len(run.output)
    return jso


def runs_to_jso(request, when, runs):
    filter  = _runs_filter(request.args)
    runs = filter(runs)
    runs = { r.run_id: r for r in runs }
    return {
        "when": when,
        "runs": { i: run_to_jso(request.app, r) for i, r in runs.items() },
    }


@API.route("/runs/<run_id>")
async def run(request, run_id):
    when, run = await STATE.runs.get(run_id)
    jso = runs_to_jso(request, when, [run])
    return response_json(jso)


@API.route("/runs/<run_id>/output")
async def run_output(request, run_id):
    when, run = await STATE.runs.get(run_id)
    if run.output is None:
        raise sanic.exceptions.NotFound("no output")
    else:
        return sanic.response.raw(run.output)


def _runs_filter(args):
    """
    Constructs a filter for runs from request arguments.
    """
    job_ids = args.pop("job_id", None)

    def filter(runs):
        if job_ids is not None:
            runs = ( 
                r for r in runs 
                if any( r.run.inst.job.job_id == i for i in job_ids )
            )
        return runs

    return filter


@API.route("/runs")
async def runs(request):
    since,  = request.args.pop("since", (None, ))
    until,  = request.args.pop("until", (None, ))
    when, runs = await STATE.runs.query(since=since, until=until)
    return response_json(runs_to_jso(request, when, runs))


@API.websocket("/runs-live")  # FIXME: Do we really need this?
async def websocket_runs(request, ws):
    since,  = request.args.pop("since", (None, ))

    log.info("live runs connect")
    with STATE.runs.query_live(since=since) as queue:
        while True:
            # FIXME: If the socket closes, clean up instead of blocking until
            # the next run is available.
            when, runs = await queue.get()
            jso = runs_to_jso(request, when, runs)
            try:
                await ws.send(json.dumps(jso))
            except websockets.ConnectionClosed:
                break
    log.info("live runs disconnect")

    
