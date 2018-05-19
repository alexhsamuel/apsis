from   aslib.py import format_ctor, tupleize
import json
from   ora import *
from   pathlib import Path
from   typing import *

from   .lib import format_time

__all__ = (
    "Instance",
    "Job",
    "ProgramError",
    "ProgramFailure",
    "Run",
)

#-------------------------------------------------------------------------------

class ProgramError(RuntimeError):

    pass



class ProgramFailure(RuntimeError):

    pass



#-------------------------------------------------------------------------------

class Job:

    def __init__(self, job_id, params, schedules, program):
        """
        @param schedules
          A sequence of `Schedule, args` pairs, where `args` is an arguments
          dict.
        """
        self.job_id     = str(job_id)
        self.params     = frozenset( str(p) for p in tupleize(params) )
        self.schedules  = tupleize(schedules)
        self.program    = program



#-------------------------------------------------------------------------------

class Instance:

    def __init__(self, inst_id, job, args, time):
        args = { str(k): str(v) for k, v in args.items() }
        assert args.keys() == job.params

        self.inst_id    = str(inst_id)
        self.job        = job
        self.args       = args
        self.time       = Time(time)


    def __repr__(self):
        return format_ctor(self, self.inst_id, self.job, self.args, self.time)


    def __str__(self):
        return "{}({})".format(
            self.job.job_id, 
            " ".join( "{}={}".format(k, v) for k, v in self.args.items() )
        )


    def __lt__(self, other):
        return (
            self.inst_id < other.inst_id if isinstance(other, Instance)
            else NotSupported
        )



#-------------------------------------------------------------------------------

class Run:

    NEW         = "new"
    SCHEDULED   = "scheduled"
    RUNNING     = "running"
    SUCCESS     = "success"
    FAILURE     = "failure"
    ERROR       = "error"

    STATES = frozenset((NEW, SCHEDULED, RUNNING, SUCCESS, FAILURE, ERROR))

    def __init__(self, run_id, inst, number=0):
        self.run_id = str(run_id)
        self.inst   = inst
        self.number = number
        self.state  = self.NEW
        self.times  = {}
        self.meta   = {}
        self.output = None


    def __repr__(self):
        return format_ctor(self, self.run_id, self.inst, state=self.state)


    def __str__(self):
        return "{} #{} of {}".format(self.run_id, self.number, self.inst)



