import logging
import ora
import sanic
import ujson
from   urllib.parse import unquote
import websockets

from   apsis.lib.api import response_json, error, time_to_jso, to_bool
from   .. import actions
from   ..jobs import jso_to_job, reruns_to_jso
from   ..runs import Instance, Run, RunError

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

@API.exception(RunError)
def no_such_process_error(request, exception):
    return error(exception, status=400)


#-------------------------------------------------------------------------------

def to_state(state):
    return None if state is None else Run.STATE[state]


def program_to_jso(app, program):
    return {
        "type"  : type(program).__qualname__,
        "str"   : str(program),
        **program.to_jso()
    }


def schedule_to_jso(app, schedule):
    return { 
        "type"      : type(schedule).__qualname__,
        "enabled"   : schedule.enabled,
        "str"       : str(schedule),
        **schedule.to_jso()
    }


def action_to_jso(app, action):
    return actions.action_to_jso(action)


def _job_to_jso(app, job):
    return {
        "job_id"        : job.job_id,
        "params"        : list(sorted(job.params)),
        "schedules"     : [ schedule_to_jso(app, s) for s in job.schedules ],
        "program"       : program_to_jso(app, job.program),
        "actions"       : [ action_to_jso(app, a) for a in job.actions ],
        "reruns"        : reruns_to_jso(job.reruns),
        "metadata"      : job.meta,
        "ad_hoc"        : job.ad_hoc,
        "url"           : app.url_for("v1.job", job_id=job.job_id),
    }


# FIXME: Attach to the apsis object?
_job_jso_cache = {}

def job_to_jso(app, job):
    # Cache jobs' JSO.  Jobs don't change for the lifetime of a process.
    try:
        return _job_jso_cache[job.job_id]
    except KeyError:
        pass
    _job_jso_cache[job.job_id] = jso = _job_to_jso(app, job)
    return jso


def _run_to_jso(app, run):
    actions = {}
    # Start a scheduled job now.
    if run.state == run.STATE.scheduled:
        actions["cancel"] = app.url_for("v1.run_cancel", run_id=run.run_id)
        actions["start"] = app.url_for("v1.run_start", run_id=run.run_id)
    # Retry is available if the run didn't succeed.
    if run.state in {run.STATE.failure, run.STATE.error}:
        actions["rerun"] = app.url_for("v1.run_rerun", run_id=run.run_id)

    program = None if run.program is None else program_to_jso(app, run.program)

    return {
        "url"           : app.url_for("v1.run", run_id=run.run_id),
        "job_id"        : run.inst.job_id,
        "job_url"       : app.url_for("v1.job", job_id=run.inst.job_id),
        "args"          : run.inst.args,
        "run_id"        : run.run_id,
        "state"         : run.state.name,
        "program"       : program,
        "message"       : run.message,
        "times"         : { n: time_to_jso(t) for n, t in run.times.items() },
        # FIXME: Rename to metadata.
        "meta"          : run.meta,
        "actions"       : actions,
        "rerun"         : run.rerun,
        "expected"      : run.expected,
        "output_url"    : app.url_for("v1.run_output_meta", run_id=run.run_id),
    }


def _output_metadata_to_jso(app, run_id, outputs):
    return [
        {
            "output_id": output_id,
            "output_url": app.url_for(
                "v1.run_output", run_id=run_id, output_id=output_id),
            "output_len": output.length,
        }
        for output_id, output in outputs.items()
    ]


# FIXME: Attach to the apsis object?
# FIXME: Attach these to the Run objects?
# FIXME: Cache JSON instead of JSO?
_run_jso_cache = {}

def run_to_jso(app, run):
    # Cache runs' JSO.  The run changes only on a state change, so we only
    # need to check the state to determine if the cache is valid.
    try:
        state, jso = _run_jso_cache[run.run_id]
    except KeyError:
        pass
    else:
        if state == run.state:
            return jso

    jso = _run_to_jso(app, run)

    _run_jso_cache[run.run_id] = run.state, jso
    return jso


def runs_to_jso(app, when, runs):
    return {
        "when": time_to_jso(when),
        "runs": { r.run_id: run_to_jso(app, r) for r in runs },
    }


#-------------------------------------------------------------------------------
# Jobs

@API.route("/jobs/<job_id>")
async def job(request, job_id):
    try:
        job = request.app.apsis.jobs.get_job(unquote(job_id))
    except LookupError as exc:
        return error(f"no job_id {job_id}", status=404)
    return response_json(job_to_jso(request.app, job))


@API.route("/jobs/<job_id>/runs")
async def job_runs(request, job_id):
    when, runs = request.app.apsis.runs.query(job_id=unquote(job_id))
    jso = runs_to_jso(request.app, when, runs)
    return response_json(jso)


@API.route("/jobs")
async def jobs(request):
    """
    Returns (non ad-hoc) jobs.
    """
    jso = [ 
        job_to_jso(request.app, j) 
        for j in request.app.apsis.jobs.get_jobs(ad_hoc=False)
    ]
    return response_json(jso)


#-------------------------------------------------------------------------------
# Runs

@API.route("/runs/<run_id>", methods={"GET"})
async def run(request, run_id):
    try:
        when, run = request.app.apsis.runs.get(run_id)
    except KeyError:
        return error(f"unknown run {run_id}", 404)
            
    jso = runs_to_jso(request.app, when, [run])
    return response_json(jso)


@API.route("/runs/<run_id>/history", methods={"GET"})
async def run_history(request, run_id):
    try:
        history = await request.app.apsis.get_run_history(run_id)
    except KeyError:
        return error(f"unknown run {run_id}", 404)

    return response_json({
        "run_history": [
            {
                "run_id"    : r["run_id"],
                "timestamp" : time_to_jso(r["timestamp"]),
                "message"   : r["message"],
            }
            for r in history
        ]
    })


@API.route("/runs/<run_id>/output", methods={"GET"})
async def run_output_meta(request, run_id):
    try:
        outputs = request.app.apsis.outputs.get_metadata(run_id)
    except KeyError:
        return error(f"unknown run {run_id}", 404)

    jso = _output_metadata_to_jso(request.app, run_id, outputs)
    return response_json(jso)


@API.route("/runs/<run_id>/output/<output_id>", methods={"GET"})
async def run_output(request, run_id, output_id):
    try:
        data = request.app.apsis.outputs.get_data(run_id, output_id)
    except LookupError as exc:
        return error(exc, 404)
    else:
        return sanic.response.raw(data)


@API.route("/runs/<run_id>/state", methods={"GET"})
async def run_state_get(request, run_id):
    _, run = request.app.apsis.runs.get(run_id)
    return response_json({"state": run.state})


@API.route("/runs/<run_id>/cancel", methods={"POST"})
async def run_cancel(request, run_id):
    state = request.app.apsis
    _, run = state.runs.get(run_id)
    if run.state == run.STATE.scheduled:
        await state.cancel(run)
        return response_json({})
    else:
        return error("invalid run state for cancel", 409, state=run.state)


@API.route("/runs/<run_id>/start", methods={"POST"})
async def run_start(request, run_id):
    state = request.app.apsis
    _, run = state.runs.get(run_id)
    if run.state == run.STATE.scheduled:
        await state.start(run)
        return response_json({})
    else:
        return error("invalid run state for start", 409, state=run.state)


@API.route("/runs/<run_id>/rerun", methods={"POST"})
async def run_rerun(request, run_id):
    state = request.app.apsis
    _, run = state.runs.get(run_id)
    if run.state not in {run.STATE.failure, run.STATE.error, run.STATE.success}:
        return error("invalid run state for rerun", 409, state=run.state)
    else:
        new_run = await state.rerun(run)
        jso = runs_to_jso(request.app, ora.now(), [new_run])
        # Let UIs know to show the new run.
        jso["show_run_id"] = new_run.run_id
        return response_json(jso)


def _filter_runs(runs, args):
    """
    Constructs a filter for runs from query args.
    """
    try:
        run_id, = args["run_id"]
    except KeyError:
        pass
    else:
        runs = ( r for r in runs if r.run_id == run_id )

    try:
        job_id, = args["job_id"]
    except KeyError:
        pass
    else:
        runs = ( r for r in runs if r.inst.job_id == job_id )

    return runs


@API.route("/runs")
async def runs(request):
    # Get runs from the selected interval.
    args    = request.args
    run_ids = args.pop("run_id", None)
    job_id, = args.pop("job_id", (None, ))
    state,  = args.pop("state", (None, ))
    since,  = args.pop("since", (None, ))
    until,  = args.pop("until", (None, ))
    reruns, = args.pop("reruns", ("False", ))

    when, runs = request.app.apsis.runs.query(
        run_ids =run_ids, 
        job_id  =job_id,
        state   =to_state(state),
        since   =since, 
        reruns  =to_bool(reruns),
        until   =until,
    )

    return response_json(runs_to_jso(request.app, when, runs))


@API.websocket("/runs-live")  # FIXME: Do we really need this?
async def websocket_runs(request, ws):
    since, = request.args.pop("since", (None, ))

    log.info("live runs connect")
    with request.app.apsis.runs.query_live(since=since) as queue:
        while True:
            # FIXME: If the socket closes, clean up instead of blocking until
            # the next run is available.
            next_runs = await queue.get()
            if next_runs is None:
                # Signalled to shut down.
                await ws.close()
                break

            when, runs = next_runs
            runs = list(_filter_runs(runs, request.args))
            if len(runs) == 0:
                continue
            log.debug(f"converting {len(runs)} runs to JSO")
            jso = runs_to_jso(request.app, when, runs)
            log.debug(f"converting {len(runs)} runs to JSON")
            json = ujson.dumps(jso)
            log.debug(f"sending {len(runs)} runs to live connection")
            try:
                await ws.send(json)
                log.debug(f"sent {len(runs)} runs")
            except websockets.ConnectionClosed:
                break

    log.info("live runs disconnect")


@API.route("/runs", methods={"POST"})
async def run_post(request):
    # The run may either contain a job ID, or a complete job.
    jso = request.json
    if "job" in jso:
        # A complete job.
        job = jso_to_job(jso["job"], None)
        job.ad_hoc = True
        request.app.apsis.jobs.add(job)
        job_id = job.job_id

    elif "job_id" in jso:
        # Just a job ID.
        job_id = jso["job_id"]

    else:
        return error("missing job_id or job")

    run = Run(Instance(job_id, jso.get("args", {})))
    request.app.apsis._validate_run(run)

    time = jso.get("times", {}).get("schedule", "now")
    time = None if time == "now" else ora.Time(time)
    await request.app.apsis.schedule(time, run)
    jso = runs_to_jso(request.app, ora.now(), [run])
    return response_json(jso)
    

