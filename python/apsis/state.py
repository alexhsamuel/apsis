from   contextlib import contextmanager
from   pathlib import Path

#-------------------------------------------------------------------------------

_running = {}
_results = {}

# FIXME: Asnyc?

def to_running(run):
    _running[run.id] = run


def to_result(result):
    run = _running.pop(result.run.id)
    assert run is result.run

    _results.setdefault(run.inst.job.id, {}).setdefault(run.inst.id, []).append(result)
    

