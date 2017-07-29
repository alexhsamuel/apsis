from   aslib import py

#-------------------------------------------------------------------------------

class ProgramError(RuntimeError):

    pass



class ProgramFailure(RuntimeError):

    pass



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
        return py.format_ctor(self, self.run_id, self.inst, state=self.state)


    def __str__(self):
        return "{} #{} of {}".format(self.run_id, self.number, self.inst)



