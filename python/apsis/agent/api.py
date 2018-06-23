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
        "exception" : proc.exception,
        "status"    : proc.status,
        "rusage"    : None if proc.rusage is None else rusage_to_jso(proc.rusage),
    }


#-------------------------------------------------------------------------------

API = sanic.Blueprint("v1")

@API.exception(Exception)
def exception(request, exception):
    return json_rsp({"error": str(exception)}, 500)


@API.route("/processes", methods={"GET"})
async def processes_get(req):
    return json_rsp(
        {"processes": [ proc_to_jso(p) for p in req.app.processes ]})


@API.route("/processes", methods={"POST"})
async def processes_post(req):
    prog    = req.json["program"]
    argv    = prog["argv"]
    cwd     = Path(prog.get("cwd", "/")).absolute()
    env     = prog.get("env", None)
    stdin   = prog.get("stdin", None)

    try:
        proc = req.app.processes.start(argv, cwd, env, stdin)
    except Exception as exc:
        return json_rsp({"error": str(exc)}, 400)
    else:
        return json_rsp({"process": proc_to_jso(proc)}, 201)
    

@API.route("/processes/<proc_id>", methods={"GET"})
async def process_get(req, proc_id):
    try:
        proc = req.app.processes[proc_id]
    except KeyError:
        return json_rsp({"error": f"proc_id {proc_id} not found"}, 404)
    else:
        return json_rsp({"process": proc_to_jso(proc)}, 200)

    
