from   aslib import py

#-------------------------------------------------------------------------------

class ProgramError(RuntimeError):

    pass



class ProgramFailure(RuntimeError):

    pass



#-------------------------------------------------------------------------------

class Run:

    NEW     = "new"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR   = "error"

    STATES = frozenset((NEW, SCHEDULED, RUNNING, SUCCESS, FAILURE, ERROR))

    def __init__(self, run_id, inst, *, state=NEW, meta={}):
        assert state in self.STATES
        self.run_id = str(run_id)
        self.inst   = inst
        self.state  = self.NEW
        self.meta   = dict(meta)
        self.output = None


    def __repr__(self):
        return py.format_ctor(self, self.run_id, self.inst, state=self.state)


    def to_jso(self, *, full=True):
        return {
            "job_id"    : self.inst.job.job_id,
            "inst_id"   : self.inst.id,
            "run_id"    : self.run_id,
            "state"     : self.state,
            "meta"      : self.meta,
        }



