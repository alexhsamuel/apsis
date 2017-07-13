from   aslib import py

from   .state import STATE

#-------------------------------------------------------------------------------

class ProgramError(RuntimeError):

    pass



class ProgramFailure(RuntimeError):

    pass



#-------------------------------------------------------------------------------

class Run:

    NEW     = "new"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR   = "error"

    STATES = frozenset((NEW, RUNNING, SUCCESS, FAILURE, ERROR))

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



#-------------------------------------------------------------------------------

async def execute(inst):
    # Create the run.
    run = Run(next(STATE.runs.run_ids), inst)
    await STATE.runs.add(run)

    # Start it.
    try:
        proc = await inst.job.program.start(run)
    except ProgramError as exc:
        run.meta["error"] = str(exc)
        run.state = Run.ERROR
        await STATE.runs.update(run)
    else:
        # Started successfully.
        run.state = Run.RUNNING
        await STATE.runs.update(run)
        # Wait for it to complete.
        try:
            await inst.job.program.wait(run, proc)
        except ProgramFailure as exc:
            run.meta["failure"] = str(exc)
            run.state = Run.FAILURE
        else:
            run.state = Run.SUCCESS
        await STATE.runs.update(run)



