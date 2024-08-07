import asyncio
import logging
import ora
import re
import sanic
import ujson
from   urllib.parse import unquote
import websockets

from   apsis.lib import asyn
from   apsis.lib.api import response_json, error, time_to_jso, to_bool, encode_response, run_to_summary_jso, make_run_summary
import apsis.lib.itr
from   apsis.lib.timing import Timer
from   apsis.lib.sys import to_signal
from   ..jobs import jso_to_job
from   ..runs import Instance, Run, RunError

log = logging.getLogger(__name__)

# Time to wait for new items to arrive when bundling a websocket message.
WS_DRAIN_TIME = 0.5
# Max number of items to send in one websocket message.
WS_CHUNK = 4096
# Time to sleep between websocket messages.
WS_CHUNK_SLEEP = 0.001

#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

@API.exception(RunError)
def no_such_process_error(request, exception):
    return error(exception, status=400)


@API.route("/alive")
async def live(request):
    return response_json({})


@API.route("/stats")
async def stats(request):
    stats = request.app.apsis.get_stats()
    return response_json(stats)


#-------------------------------------------------------------------------------

def to_state(state):
    return None if state is None else Run.STATE[state]


def _to_jso(obj):
    return None if obj is None else {
        **obj.to_jso(),
        "str": str(obj),
    }


def _to_jsos(objs):
    return [] if objs is None else [ _to_jso(o) for o in objs ]


def job_to_jso(app, job):
    return {
        "job_id"        : job.job_id,
        "params"        : list(sorted(job.params)),
        "schedules"     : [ _to_jso(s) for s in job.schedules ],
        "program"       : _to_jso(job.program),
        "condition"     : [ _to_jso(c) for c in job.conds ],
        # FIXME: actions!
        "actions"       : [ _to_jso(a) for a in job.actions ],
        "metadata"      : job.meta,
        "ad_hoc"        : job.ad_hoc,
        "url"           : app.url_for("v1.job", job_id=job.job_id),
    }


def run_to_jso(app, run, summary=False):
    if run.state is None:
        # This run is being deleted.
        # FIXME: Hack.
        return {"run_id": run.run_id, "state": None}

    jso = run_to_summary_jso(run)

    if not summary:
        jso = {
            **jso,
            "conds": _to_jsos(run.conds),
            # FIXME: Rename to metadata.
            "meta": run.meta,
            "program": _to_jso(run.program),
        }

    return jso


def runs_to_jso(app, when, runs, summary=False):
    return {
        "when": time_to_jso(when),
        "runs": { r.run_id: run_to_jso(app, r, summary) for r in runs },
    }


def _output_metadata_to_jso(app, run_id, outputs):
    return [
        {
            "output_id": output_id,
            "output_len": output.length,
        }
        for output_id, output in outputs.items()
    ]


#-------------------------------------------------------------------------------
# Jobs

class JobLookupError(LookupError):
    pass


@API.exception(JobLookupError)
def job_lookup_error(request, exception):
    return error(exception, status=400)


class AmbiguousJobError(ValueError):
    pass


@API.exception(AmbiguousJobError)
def ambiguous_job_error(request, exception):
    return error(exception, status=400)


def match(choices, target):
    """
    Matches `target` to one of `choices`.

    Splits the target and each choice into words.  Selects a choice such that
    each word in the target appears as a word in the choice, at least as a
    prefix.

    :return:
      The matching choice.
    """
    REGEX = re.compile(r"[^A-Za-z0-9]")

    def words(target):
        return set(REGEX.split(target))

    target_words = words(target)

    def match(choice):
        choice_words = words(choice)
        return all(
            any( cw.startswith(sw) for cw in choice_words )
            for sw in target_words
        )

    choices = { c for c in choices if match(c) }

    if len(choices) == 0:
        raise JobLookupError("no job id match: " + target)
    elif len(choices) == 1:
        return next(iter(choices))
    else:
        if len(choices) > 8:
            choices = ", ".join(list(choices)[: 8]) + " …"
        else:
            choices = ", ".join(choices)
        raise AmbiguousJobError("ambiguous job id: " + choices)


def match_job_id(jobs, job_id):
    """
    Matches `job_id` as an exact or fuzzy match.
    """
    # Try for an exact match first.a
    try:
        jobs.get_job(job_id)
    except LookupError:
        pass
    else:
        return job_id

    # FIXME: Cache job ids (or word split job ids) to make this efficient.
    job_ids = [ j.job_id for j in jobs.get_jobs(ad_hoc=False) ]
    return match(job_ids, job_id)
 

@API.route("/jobs/<job_id:path>")
async def job(request, job_id):
    jobs = request.app.apsis.jobs
    try:
        job_id = match_job_id(jobs, unquote(job_id))
    except LookupError:
        return error(f"no job_id {job_id}", status=404)
    job = jobs.get_job(job_id)
    return response_json(job_to_jso(request.app, job))


@API.route("/jobs/<job_id:path>/runs")
async def job_runs(request, job_id):
    job_id = match_job_id(request.app.apsis.jobs, unquote(job_id))
    when, runs = request.app.apsis.run_store.query(job_id=job_id)
    jso = runs_to_jso(request.app, when, runs)
    return response_json(jso)


@API.route("/jobs")
async def jobs(request):
    """
    Returns (non ad-hoc) jobs.
    """
    args    = request.args
    try:
        label, = args["label"]
    except KeyError:
        label = None

    jso = [ 
        job_to_jso(request.app, j) 
        for j in request.app.apsis.jobs.get_jobs(ad_hoc=False)
        if label is None or label in j.meta.get("labels")
    ]
    return response_json(jso)


#-------------------------------------------------------------------------------
# Runs

@API.route("/runs/<run_id>", methods={"GET"})
async def run(request, run_id):
    try:
        when, run = request.app.apsis.run_store.get(run_id)
    except KeyError:
        return error(f"unknown run {run_id}", 404)

    jso = runs_to_jso(request.app, when, [run])
    return response_json(jso)


@API.route("/runs/<run_id>/log", methods={"GET"})
async def run_log(request, run_id):
    try:
        run_log = await request.app.apsis.get_run_log(run_id)
    except KeyError:
        return error(f"unknown run {run_id}", 404)

    return response_json({
        "run_log": [
            {
                "run_id"    : r["run_id"],
                "timestamp" : time_to_jso(r["timestamp"]),
                "message"   : r["message"],
            }
            for r in sorted(run_log, key=lambda r: r["timestamp"])
        ]
    })


@API.route("/runs/<run_id>/outputs", methods={"GET"})
async def run_output_meta(request, run_id):
    try:
        outputs = request.app.apsis.outputs.get_metadata(run_id)
    except KeyError:
        log.error(f"unknown run {run_id}", exc_info=True)
        return error(f"unknown run {run_id}", 404)

    jso = _output_metadata_to_jso(request.app, run_id, outputs)
    return response_json(jso)


@API.route("/runs/<run_id>/output/<output_id>", methods={"GET"})
async def run_output(request, run_id, output_id):
    try:
        output = request.app.apsis.outputs.get_output(run_id, output_id)
    except LookupError as exc:
        return error(exc, 404)
    else:
        headers, data = encode_response(
            request.headers, output.data, output.compression)
        headers["Content-Type"] = output.metadata.content_type
        return sanic.response.raw(data, headers=headers)


@API.route("/runs/<run_id>/state", methods={"GET"})
async def run_state_get(request, run_id):
    _, run = request.app.apsis.run_store.get(run_id)
    return response_json({"state": run.state})


@API.route("/runs/<run_id>/skip", methods={"POST"})
async def run_skip(request, run_id):
    state = request.app.apsis
    _, run = state.run_store.get(run_id)
    await state.skip(run)
    return response_json({})


@API.route("/runs/<run_id>/start", methods={"POST"})
async def run_start(request, run_id):
    state = request.app.apsis
    _, run = state.run_store.get(run_id)
    await state.start(run)
    return response_json({})


@API.route("/runs/<run_id>/rerun", methods={"POST"})
async def run_rerun(request, run_id):
    state = request.app.apsis
    _, run = state.run_store.get(run_id)
    new_run = await state.rerun(run)
    jso = runs_to_jso(request.app, ora.now(), [new_run])
    # Let UIs know to show the new run.
    jso["show_run_id"] = new_run.run_id
    return response_json(jso)


# PUT is probably right, but run actions currently are POST only.
@API.route("/runs/<run_id>/signal/<signal>", methods={"PUT", "POST"})
async def run_signal(request, run_id, signal):
    apsis = request.app.apsis
    _, run = apsis.run_store.get(run_id)

    try:
        signal = to_signal(signal)
    except ValueError:
        return error(f"invalid signal: {signal}", 400)

    try:
        await apsis.send_signal(run, signal)
    except RuntimeError as exc:
        return error(str(exc), 400)
    else:
        return response_json({})


@API.route("/runs/<run_id>/mark/<state>", methods={"PUT", "POST"})
async def run_mark(request, run_id, state):
    try:
        apsis = request.app.apsis
        _, run = apsis.run_store.get(run_id)
        try:
            state = Run.STATE[state]
        except KeyError:
            return error(f"invalid state: {state}", status=400)

        await apsis.mark(run, state)
    except Exception:
        log.error("error", exc_info=True)
        raise
    return response_json({})


@API.route("/runs")
async def runs(request):
    apsis = request.app.apsis

    # Get runs from the selected interval.
    args        = request.args
    summary,    = args.pop("summary", ("False", ))
    summary     = to_bool(summary)
    run_id      = args.pop("run_id", None)
    job_id,     = args.pop("job_id", (None, ))
    if job_id is not None:
        job_id  = match_job_id(apsis.jobs, job_id)
    state,      = args.pop("state", (None, ))
    since,      = args.pop("since", (None, ))

    # Remainders are args to match, though strip off leading underscores, where
    # were added to avoid collision with fixed args.
    args = { n[1 :] if n.startswith("_") else n: a[-1] for n, a in args.items() }

    when, runs = apsis.run_store.query(
        run_ids     =run_id,
        job_id      =job_id,
        state       =to_state(state),
        since       =since,
        with_args   =args,
    )

    return response_json(runs_to_jso(request.app, when, runs, summary=summary))


async def _send_chunked(msgs, ws, prefix):
    # Break large sets into chunks, to avoid block for too long.
    for chunk in apsis.lib.itr.chunks(msgs, WS_CHUNK):
        json = ujson.dumps(chunk, escape_forward_slashes=False)
        log.debug(f"{prefix} sending {len(chunk)} msgs, {len(json)} bytes")
        await ws.send(json)
        # Take a break, let others go.
        await asyncio.sleep(WS_CHUNK_SLEEP)


@API.websocket("/summary")
async def websocket_summary(request, ws):
    # request.query_args doesn't work correctly for ws endpoints?
    init = "init" in request.query_string.split("&")

    addr, port = request.socket
    prefix = f"/summary {addr}:{port}:"
    log.debug(f"{prefix} connected init={init}")

    predicate = lambda msg: msg["type"] in {"run_summary", "run_delete"}
    with request.app.apsis.publisher.subscription(predicate=predicate) as sub:
        try:
            if init:
                # Full initialization.  Send summaries of all runs.
                _, runs = request.app.apsis.run_store.query()
                msgs = [ make_run_summary(r) for r in runs ]
                await _send_chunked(msgs, ws, prefix)

            while not sub.closed:
                # Wait for the next msg, then grab all that show up in a short time.
                # This avoids sending lots of short websocket traffic.
                msgs = await asyn.anext_and_drain(sub, WS_DRAIN_TIME)
                await _send_chunked(msgs, ws, prefix)

            await ws.close()

        except websockets.ConnectionClosed:
            log.debug(f"{prefix} closed")

    log.debug(f"{prefix} done")


@API.route("/runs", methods={"POST"})
async def run_post(request):
    apsis = request.app.apsis

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
        job_id = match_job_id(apsis.jobs, jso["job_id"])

    else:
        return error("missing job_id or job")

    run = Run(Instance(job_id, jso.get("args", {})))
    request.app.apsis._validate_run(run)

    time = jso.get("times", {}).get("schedule", "now")
    time = None if time == "now" else ora.Time(time)
    await apsis.schedule(time, run)
    jso = runs_to_jso(request.app, ora.now(), [run])
    return response_json(jso)


