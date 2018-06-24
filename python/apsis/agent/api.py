import json
import logging
from   pathlib import Path
import sanic

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

def json_rsp(jso, status=200):
    jso["status"] = status
    data = json.dumps(jso, indent=2).encode("utf-8")
    return sanic.response.raw(
        data, 
        headers={"Content-Type": "application/json"},
        status=status,
    )


def rusage_to_jso(rusage):
    return { 
        n: getattr(rusage, n) 
        for n in dir(rusage)
        if n.startswith("ru_")
    }


def proc_to_jso(proc):
    return {
        "proc_id"   : proc.proc_id,
        "state"     : proc.state,
        "pid"       : proc.pid,
        "exception" : str(proc.exception),
        "status"    : proc.status,
        "rusage"    : None if proc.rusage is None else rusage_to_jso(proc.rusage),
        "start_time": None if proc.start_time is None else str(proc.start_time),
        "end_time"  : None if proc.end_time is None else str(proc.end_time),
    }


#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

@API.exception(Exception)
def exception(request, exception):
    return json_rsp({"error": str(exception)}, 500)


@API.route("/processes", methods={"GET"})
async def processes_get(req):
    procs = req.app.processes
    return json_rsp({"processes": [ proc_to_jso(p) for p in procs ]})


@API.route("/processes", methods={"POST"})
async def processes_post(req):
    prog    = req.json["program"]
    argv    = prog["argv"]
    cwd     = Path(prog.get("cwd", "/")).absolute()
    env     = prog.get("env", None)
    stdin   = prog.get("stdin", None)

    proc = req.app.processes.start(argv, cwd, env, stdin)
    return json_rsp({"process": proc_to_jso(proc)}, 201)


@API.route("/processes/<proc_id>", methods={"GET"})
async def process_get(req, proc_id):
    proc = req.app.processes[proc_id]
    return json_rsp({"process": proc_to_jso(proc)})

    
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
    return json_rsp({})


@API.route("/processes/<proc_id>", methods={"DELETE"})
async def process_delete(req, proc_id):
    del req.app.processes[proc_id]
    return json_rsp({})


