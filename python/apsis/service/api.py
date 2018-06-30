import json  # FIXME: ujson?
import logging
import sanic
import websockets

from   .. import state

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

def get_state():
    return state.STATE


def response_json(jso, status=200):
    return sanic.response.json(jso, status=status, indent=1, sort_keys=True)


#-------------------------------------------------------------------------------

def program_to_jso(app, program):
    return {
        "type"  : type(program).__qualname__,
        "str"   : str(program),
        **program.to_jso()
    }


def schedule_to_jso(app, schedule):
    return { 
        "type"  : type(schedule).__qualname__,
        "str"   : str(schedule),
        **schedule.to_jso()
    }


def job_to_jso(app, job):
    return {
        "job_id"        : job.job_id,
        "params"        : list(sorted(job.params)),
        "schedules"     : [ schedule_to_jso(app, s) for s in job.schedules ],
        "program"       : program_to_jso(app, job.program),
        "url"           : app.url_for("v1.job", job_id=job.job_id),
    }


def run_to_jso(app, run):
    actions = {}

    # Start a scheduled job now.
    if run.state == run.STATE.scheduled:
        actions["cancel"] = app.url_for("v1.run_cancel", run_id=run.run_id)
        actions["start"] = app.url_for("v1.run_start", run_id=run.run_id)

    # Retry is available if the run didn't succeed.
    if run.state in {run.STATE.failure, run.STATE.error}:
        actions["retry"] = app.url_for("v1.run_rerun", run_id=run.run_id)

    return {
        "url"           : app.url_for("v1.run", run_id=run.run_id),
        "job_id"        : run.inst.job_id,
        "job_url"       : app.url_for("v1.job", job_id=run.inst.job_id),
        "args"          : run.inst.args,
        "run_id"        : run.run_id,
        "state"         : run.state.name,
        "times"         : { n: str(t) for n, t in run.times.items() },
        "meta"          : run.meta,
        "actions"       : actions,
        "output_url"    : app.url_for("v1.run_output", run_id=run.run_id),
        "output_len"    :  None if run.output is None else len(run.output),
    }


def runs_to_jso(app, when, runs):
    return {
        "when": str(when),
        "runs": { r.run_id: run_to_jso(app, r) for r in runs },
    }


#-------------------------------------------------------------------------------
# Jobs

@API.route("/jobs/<job_id>")
async def job(request, job_id):
    try:
        return response_json(job_to_jso(request.app, get_state().get_job(job_id)))
    except LookupError as exc:
        sanic.exceptions.abort(404, f"job_id: {job_id}")


@API.route("/jobs/<job_id>/runs")
async def job_runs(request, job_id):
    when, runs = get_state().runs.query(job_id=job_id)
    jso = runs_to_jso(request.app, when, runs)
    return response_json(jso)


@API.route("/jobs")
async def jobs(request):
    jso = [ 
        job_to_jso(request.app, j) 
        for j in get_state().get_jobs() 
    ]
    return response_json(jso)


#-------------------------------------------------------------------------------
# Runs

@API.route("/runs/<run_id>")
async def run(request, run_id):
    when, run = get_state().runs.get(run_id)
    jso = runs_to_jso(request.app, when, [run])
    return response_json(jso)


@API.route("/runs/<run_id>/output")
async def run_output(request, run_id):
    when, run = get_state().runs.get(run_id)
    if run.output is None:
        raise sanic.exceptions.NotFound("no output")
    else:
        return sanic.response.raw(run.output)


@API.route("/runs/<run_id>/state", methods={"GET"})
async def run_state_get(request, run_id):
    _, run = get_state().runs.get(run_id)
    return response_json({"state": run.state})


@API.route("/runs/<run_id>/cancel", methods={"POST"})
async def run_cancel(request, run_id):
    _, run = get_state().runs.get(run_id)
    if run.state == run.STATE.scheduled:
        await state.cancel(run)
        return response_json({})
    else:
        return response_json(dict(
            error="invalid run state for cancel",
            state=run.state
        ), status=409)


@API.route("/runs/<run_id>/start", methods={"POST"})
async def run_start(request, run_id):
    _, run = get_state().runs.get(run_id)
    if run.state == run.STATE.scheduled:
        await state.start(run)
        return response_json({})
    else:
        return response_json(dict(
            error="invalid run state for start",
            state=run.state
        ), status=409)


@API.route("/runs/<run_id>/rerun", methods={"POST"})
async def run_rerun(request, run_id):
    _, run = get_state().runs.get(run_id)
    if run.state in {run.STATE.failure, run.STATE.error, run.STATE.success}:
        when, new_run = await state.rerun(run)
        jso = runs_to_jso(request.app, when, [new_run])
        return response_json(jso)
    else:
        return response_json(dict(
            error="invalid run state for rerun",
            state=run.state
        ), status=409)


def _run_filter_for_query(args):
    """
    Constructs a filter for runs from query args.
    """
    run_id = args.get("run_id", None)
    job_id = args.get("job_id", None)

    def filter(run):
        return (
                (run_id is None or run.run_id == run_id)
            and (job_id is None or run.inst.job_id == job_id)
        )

    return filter


@API.route("/runs")
async def runs(request):
    # Get runs from the selected interval.
    since,  = request.args.pop("since", (None, ))
    until,  = request.args.pop("until", (None, ))
    when, runs = get_state().runs.query(since=since, until=until)

    # Select runs based on query args.
    filter = _run_filter_for_query(request.args)
    runs = ( r for r in runs if filter(r) )

    return response_json(runs_to_jso(request.app, when, runs))


@API.websocket("/runs-live")  # FIXME: Do we really need this?
async def websocket_runs(request, ws):
    since,  = request.args.pop("since", (None, ))
    filter  = _run_filter_for_query(request.args)

    log.info("live runs connect")
    with get_state().runs.query_live(since=since) as queue:
        while True:
            # FIXME: If the socket closes, clean up instead of blocking until
            # the next run is available.
            when, runs = await queue.get()
            runs = [ r for r in runs if filter(r) ]
            if len(runs) == 0:
                continue
            jso = runs_to_jso(request.app, when, runs)
            try:
                await ws.send(json.dumps(jso))
            except websockets.ConnectionClosed:
                break
    log.info("live runs disconnect")

    
