from   contextlib import contextmanager
from   pathlib import Path

#-------------------------------------------------------------------------------

_jobs = []

#-------------------------------------------------------------------------------

_scheduled = []

#-------------------------------------------------------------------------------

_running = {}

# FIXME: Asnyc?

def to_running(run):
    _running[run.id] = run


#-------------------------------------------------------------------------------

_results = []

def to_result(result):
    run = _running.pop(result.run.id)
    assert run is result.run
    _results.append(result)

    

