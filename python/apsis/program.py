import asyncio
from   cron import *
from   functools import partial
import getpass
import logging
from   pathlib import Path
import socket
import subprocess

from   . import lib
from   .job import *
from   .state import state

log = logging.getLogger("program")

#-------------------------------------------------------------------------------

def done(fut_result):
    result = fut_result.result()
    log.info("done: {}".format(result.run))
    state.executing_to_result(result)


def run(inst):
    # FIXME: Abstract this all out.
    run = Run(None, inst)
    state.executing(run)
    fut_result = asyncio.ensure_future(inst.job.program(run))
    fut_result.add_done_callback(done)


class Result:

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR   = "error"

    OUTCOMES = frozenset((SUCCESS, FAILURE, ERROR))

    def __init__(self, run, outcome, fields):
        assert outcome in self.OUTCOMES
        self.run        = run
        self.program    = run.inst.job.program
        self.outcome    = outcome
        self.fields     = dict(fields)

    
    def to_jso(self):
        return {
            "job_id"    : self.run.inst.job.id,
            "inst_id"   : self.run.inst.id,
            "run_id"    : self.run.id,
            "outcome"   : self.outcome,
            "program"   : self.run.inst.job.program.to_jso(),
            "fields"    : self.fields,
        }



class ProcessProgram:

    def __init__(self, argv):
        self.__argv = tuple( str(a) for a in argv )
        self.__executable = Path(argv[0])


    def to_jso(self):
        return {
            "argv"      : list(self.__argv),
        }


    @classmethod
    def from_jso(class_, jso):
        return class_(
            jso["argv"],
        )


    async def __call__(self, run) -> Result:
        log.info("running: {}".format(run))

        start_time = now()
        fields = dict(
            hostname    =socket.gethostname(),
            username    =getpass.getuser(),
            start_time  =str(start_time),
        )

        try:
            with open("/dev/null") as stdin:
                proc = await asyncio.create_subprocess_exec(
                    *self.__argv, 
                    executable  =self.__executable,
                    stdin       =stdin,
                    # Merge stderr with stdin.  FIXME: Do better.
                    stdout      =asyncio.subprocess.PIPE,
                    stderr      =asyncio.subprocess.STDOUT,
                )

        except OSError as exc:
            fields["error"] = str(exc)
            outcome = Result.ERROR

        else:
            # FIXME: Stream output, rather than gulping it.
            stdout, stderr = await proc.communicate()
            end_time = str(now())
            return_code = proc.returncode

            assert stderr is None
            assert return_code is not None

            fields.update(
                start_time  =str(start_time),
                pid         =proc.pid,
                output      =stdout.decode(),  # FIXME: Might not be UTF-8.
                return_code =return_code,
                end_time    =str(end_time),
            )
            outcome = Result.SUCCESS if return_code == 0 else Result.FAILURE

        return Result(run, outcome, fields)



#-------------------------------------------------------------------------------

TYPES = (
    ProcessProgram,
)

to_jso      = partial(lib.to_jso, types=TYPES)
from_jso    = partial(lib.from_jso, types=TYPES)

