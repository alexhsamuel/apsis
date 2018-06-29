from   ora import now

from   .lib.py import format_ctor, tupleize

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
    """
    A job with bound parameters.  Not user-visible.
    """

    def __init__(self, job_id, args):
        self.job_id     = job_id
        self.args       = { str(k): str(v) for k, v in args.items() }


    def __repr__(self):
        return format_ctor(self, self.job_id, self.args)


    def __str__(self):
        return "{}({})".format(
            self.job_id, 
            " ".join( "{}={}".format(k, v) for k, v in self.args.items() )
        )


    def __hash__(self):
        return hash(self.job_id) ^ hash(tuple(sorted(self.args.items())))


    def __eq__(self, other):
        return (
            self.job_id == other.job_id
            and self.args == other.args
        ) if isinstance(other, Instance) else NotImplemented


    def __lt__(self, other):
        return (
            self.job_id < other.job_id
            or (
                self.job_id == other.job_id
                and sorted(self.args.items()) < sorted(other.args.items())
            )
        ) if isinstance(other, Instance) else NotImplemented



#-------------------------------------------------------------------------------

class Run:

    NEW         = "new"
    SCHEDULED   = "scheduled"
    RUNNING     = "running"
    SUCCESS     = "success"
    FAILURE     = "failure"
    ERROR       = "error"

    STATES = frozenset((NEW, SCHEDULED, RUNNING, SUCCESS, FAILURE, ERROR))

    def __init__(self, run_id, inst):
        self.run_id = str(run_id)
        self.inst   = inst
        self.state  = self.NEW
        self.times  = {}
        self.meta   = {}
        self.output = None


    def __repr__(self):
        return format_ctor(self, self.run_id, self.inst, state=self.state)


    def __str__(self):
        return f"{self.run_id} of {self.inst}"


    def set_running(self, meta={}):
        """
        Transitions to "running" state: started.
        """
        assert self.state == self.SCHEDULED
        self.times["running"] = str(now())
        self.meta.update(meta)
        self.state = self.RUNNING


    def set_error(self, msg, meta={}):
        """
        Transitions to "error" state: encountered an error while starting.
        """
        assert self.state == self.SCHEDULED
        self.times["error"] = str(now())
        self.meta.update(meta)
        self.meta["error"] = msg  # FIXME: Not in meta?
        self.state = self.ERROR


    def set_success(self, output, meta={}):
        """
        Transitions to "success" state: completed successfully.
        """
        assert self.state == self.RUNNING
        time = now()
        self.times["success"] = str(time)
        self.output = output
        self.state = self.SUCCESS

        
    def set_failure(self, msg, output, meta={}):
        """
        Transitions to "success" state: failed.
        """
        assert self.state == self.RUNNING
        time = now()
        self.times["failure"] = str(time)
        self.output = output
        self.state = self.FAILURE
        


