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



