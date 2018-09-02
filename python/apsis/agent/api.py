import logging
from   pathlib import Path
import sanic
import traceback
import ujson

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
    }


#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

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
async def process_running(req):
    return response({"running": True})


@API.route("/processes", methods={"GET"})
async def processes_get(req):
    procs = req.app.processes
    return response({"processes": [ proc_to_jso(p) for p in procs ]})


@API.route("/processes", methods={"POST"})
async def processes_post(req):
    prog    = req.json["program"]
    argv    = prog["argv"]
    cwd     = Path(prog.get("cwd", "/")).absolute()
    env     = prog.get("env", None)
    stdin   = prog.get("stdin", None)

    proc = req.app.processes.start(argv, cwd, env, stdin)
    return response({"process": proc_to_jso(proc)}, 201)


@API.route("/processes/<proc_id>", methods={"GET"})
async def process_get(req, proc_id):
    proc = req.app.processes[proc_id]
    return response({"process": proc_to_jso(proc)})

    
@API.route("/processes/<proc_id>/output", methods={"GET"})
async def process_get_output(req, proc_id):
    proc = req.app.processes[proc_id]
    with open(proc.proc_dir.out_path, "rb") as file:
        # FIXME: Stream it?
        data = file.read()
    return sanic.response.raw(data, status=200)


@API.route("/processes/<proc_id>/signal/<signum:int>", methods={"PUT"})
async def process_signal(req, proc_id, signum):
    req.app.processes.kill(proc_id, signum)
    return response({})


@API.route("/processes/<proc_id>", methods={"DELETE"})
async def process_delete(req, proc_id):
    del req.app.processes[proc_id]
    shutdown = req.app.config.auto_shutdown and len(req.app.processes) == 0
    if shutdown:
        req.app.add_task(req.app.stop())
    return response({"shutdown": shutdown})


@API.route("/shutdown", methods={"POST"})
async def process_shutdown(req):
    # FIXME: Add a query option to kill and shut down, or another endpoint.
    shutdown = len(req.app.processes) == 0
    if shutdown:
        req.app.add_task(req.app.stop())
    return response({"shutdown": shutdown})


