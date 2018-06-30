from   .lib.py import tupleize

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




