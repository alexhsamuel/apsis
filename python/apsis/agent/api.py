import asyncio
import functools
import logging
from   pathlib import Path
import sanic
import socket
import traceback
import ujson

from   apsis.lib.sys import get_username
from   .processes import NoSuchProcessError

log = logging.getLogger("api")

#-------------------------------------------------------------------------------

def response(jso, status=200):
    jso["status"] = status
    return sanic.response.raw(
        ujson.dumps(jso, indent=2).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        status=status,
    )


def error(msg, status):
    return response({"error": str(msg)}, status=status)


def exc_error(exc, status, log=None):
    if log is not None:
        log(traceback.format_exc().rstrip())
    return error(str(exc), status)


def rusage_to_jso(rusage):
    usage = { 
        n: getattr(rusage, n) 
        for n in dir(rusage)
        if n.startswith("ru_")
    }
    # Round times to ns, to avoid silly rounding issues.
    return {
        n: round(v, 9) if isinstance(v, float) else v
        for n, v in usage.items()
    }


def proc_to_jso(proc):
    return {
        "proc_id"   : proc.proc_id,
        "state"     : proc.state,
        "program"   : proc.program,
        "pid"       : proc.pid,
        "exception" : str(proc.exception),
        "status"    : proc.status,
        "return_code": proc.return_code,
        "signal"    : proc.signal,
        "rusage"    : None if proc.rusage is None else rusage_to_jso(proc.rusage),
        "start_time": None if proc.start_time is None else str(proc.start_time),
        "end_time"  : None if proc.end_time is None else str(proc.end_time),
        "hostname"  : socket.gethostname(),
        "username"  : get_username(),
    }


#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

def auth(handler):
    """
    Wraps a handler to authorize the operation.

    Checks x-auth-token in the request header.
    """
    @functools.wraps(handler)
    def wrapped(req, *args, **kw_args):
        token = req.headers.get("x-auth-token", None)
        if token == req.app.token:
            return handler(req, *args, **kw_args)
        else:
            return error("forbidden", 403)

    return wrapped


@API.exception(NoSuchProcessError)
def no_such_process_error(request, exception):
    return exc_error(exception, 404)


@API.exception(RuntimeError)
def runtime_error(request, exception):
    return exc_error(exception, 400, log=log.error)


@API.exception(Exception)
def exception_(request, exception):
    return exc_error(exception, 500, log=log.error)


@API.route("/running", methods={"GET"})
@auth
async def process_running(req):
    return response({"running": True})


@API.route("/processes", methods={"GET"})
@auth
async def processes_get(req):
    procs = req.app.processes
    return response({"processes": [ proc_to_jso(p) for p in procs ]})


@API.route("/processes", methods={"POST"})
@auth
async def processes_post(req):
    prog    = req.json["program"]
    argv    = prog["argv"]
    cwd     = Path(prog.get("cwd", "/")).absolute()
    env     = prog.get("env", None)
    stdin   = prog.get("stdin", None)

    # We can only run procs for our own user.  Confirm that the request's
    # username matches.
    if prog["username"] != get_username():
        return response("wrong username", 421)

    proc = req.app.processes.start(argv, cwd, env, stdin)
    return response({"process": proc_to_jso(proc)}, 201)


@API.route("/processes/<proc_id>", methods={"GET"})
@auth
async def process_get(req, proc_id):
    proc = req.app.processes[proc_id]
    return response({"process": proc_to_jso(proc)})

    
@API.route("/processes/<proc_id>/output", methods={"GET"})
@auth
async def process_get_output(req, proc_id):
    proc = req.app.processes[proc_id]
    with open(proc.proc_dir.out_path, "rb") as file:
        # FIXME: Stream it?
        data = file.read()
    return sanic.response.raw(data, status=200)


@API.route("/processes/<proc_id>/signal/<signum:int>", methods={"PUT"})
@auth
async def process_signal(req, proc_id, signum):
    req.app.processes.kill(proc_id, signum)
    return response({})


@API.route("/processes/<proc_id>", methods={"DELETE"})
@auth
async def process_delete(req, proc_id):
    del req.app.processes[proc_id]
    stop = len(req.app.processes) == 0 and req.app.config.auto_stop is not None
    if stop:
        _schedule_auto_stop(req.app, req.app.config.auto_stop)
    return response({"stop": stop})


@API.route("/stop", methods={"POST"})
@auth
async def process_stop(req):
    # FIXME: Add a query option to kill and stop, or another endpoint.
    stop = len(req.app.processes) == 0
    if stop:
        _stop(req.app)
    return response({"stop": stop})


#-------------------------------------------------------------------------------

def _stop(app):
    res = app.stop()
    assert res is None, "old sanic used to return a coro here"


_auto_stop_task = None

def _schedule_auto_stop(app, delay):
    """
    Schedule `app` stop after `delay` sec, if there are no processes left.
    """
    global _auto_stop_task

    # Cancel any existing auto stop task.
    if _auto_stop_task is not None:
        _auto_stop_task.cancel()
        _auto_stop_task = None

    async def _stop():
        if delay > 0:
            log.info(f"auto stop in {delay} s")
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

        if len(app.processes) == 0:
            log.info("no processes left; stopping")
            app.stop()

    _auto_stop_task = asyncio.ensure_future(_stop())


