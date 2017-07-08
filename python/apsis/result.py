class Result:

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR   = "error"

    OUTCOMES = frozenset((SUCCESS, FAILURE, ERROR))

    def __init__(self, run, outcome, meta={}, output={}):
        assert outcome in self.OUTCOMES
        self.run        = run
        self.program    = run.inst.job.program
        self.outcome    = outcome
        self.meta       = dict(meta)
        self.output     = dict(output)

    
    def to_jso(self, *, full=True):
        jso = {
            "job_id"    : self.run.inst.job.job_id,
            "inst_id"   : self.run.inst.id,
            "run_id"    : self.run.run_id,
            "outcome"   : self.outcome,
            "meta"      : self.meta,
        }
        # FIXME: Maybe output should just be a separate object.
        if full:
            jso["results"] = {
                "output": self.output,
            }
        return jso



