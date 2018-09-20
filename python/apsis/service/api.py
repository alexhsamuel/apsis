import logging
import ora
import sanic
import ujson
from   urllib.parse import unquote
import websockets

from   ..jobs import jso_to_job, reruns_to_jso
from   ..runs import Instance, Run, RunError

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

def response_json(jso, status=200):
    return sanic.response.json(jso, status=status, indent=1, sort_keys=True)


def error(message, status=400, **kw_args):
    return response_json({"error": str(message), **kw_args}, status=status)


@API.exception(RunError)
def no_such_process_error(request, exception):
    return error(exception, status=400)


def time_to_jso(time):
    return format(time, "%.i")


def to_bool(string):
    if string in {"True", "true", "T", "t"}:
        return True
    elif string in {"False", "false", "F", "f"}:
        return False
    else:
        raise ValueError(f"unknown bool: {string}")


def to_state(state):
    return None if state is None else Run.STATE[state]


#-------------------------------------------------------------------------------

def program_to_jso(app, program):
    return {
        "type"  : type(program).__qualname__,
        **program.to_jso()
    }


def schedule_to_jso(app, schedule):
    return { 
        "type"  : type(schedule).__qualname__,
        "str"   : str(schedule),
        **schedule.to_jso()
    }


def _job_to_jso(app, job):
    return {
        "job_id"        : job.job_id,
        "params"        : list(sorted(job.params)),
        "schedules"     : [ schedule_to_jso(app, s) for s in job.schedules ],
        "program"       : program_to_jso(app, job.program),
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

    jso = {
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
    }

    # FIXME: For now, include output_id="output" only.
    OUTPUT_ID = "output"
    outputs = app.apsis.outputs.get_metadata(run.run_id)
    try:
        output = outputs[OUTPUT_ID]
    except KeyError:
        # No output.
        pass
    else:
        url = app.url_for(
            "v1.run_output", run_id=run.run_id, output_id=OUTPUT_ID)
        jso.update({
            "output_url": url,
            "output_len": output.length,
        })

    return jso


# FIXME: Attach to the apsis object?
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
        sanic.exceptions.abort(404, f"job_id: {job_id}")
    return response_json(job_to_jso(request.app, job))


@API.route("/jobs/<job_id>/runs")
async def job_runs(request, job_id):
    when, runs = request.app.apsis.runs.query(job_id=unquote(job_id))
    jso = runs_to_jso(request.app, when, runs)
    return response_json(jso)


@API.route("/jobs")
async def jobs(request):
    jso = [ 
        job_to_jso(request.app, j) 
        for j in request.app.apsis.jobs.get_jobs() 
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
            when, runs = await queue.get()
            runs = list(_filter_runs(runs, request.args))
            if len(runs) == 0:
                continue
            jso = runs_to_jso(request.app, when, runs)
            try:
                await ws.send(ujson.dumps(jso))
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
    

