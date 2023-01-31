import logging

from   apsis.lib.py import format_ctor, iterize
from   apsis.runs import Run, Instance, get_bind_args
from   .base import Condition, _bind

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Dependency(Condition):
    """
    True if a run exists and is in a given state.
    """

    def __init__(self, job_id, args={}, states={Run.STATE.success}):
        states = frozenset(iterize(states))
        assert all( isinstance(s, Run.STATE) for s in states )

        self.job_id = job_id
        self.args = args
        self.states = states


    def __repr__(self):
        return format_ctor(self, self.job_id, self.args, states=self.states)


    def __str__(self):
        inst = Instance(self.job_id, self.args)
        states = "|".join( s.name for s in self.states )
        return f"dependency on {inst} → {states}"


    def to_jso(self):
        return {
            **super().to_jso(),
            "job_id": self.job_id,
            "args"  : self.args,
            "states": [ s.name for s in self.states ],
        }


    @classmethod
    def from_jso(cls, jso):
        states = { Run.STATE[s] for s in iterize(jso.pop("states", "success")) }
        return cls(
            jso.pop("job_id"),
            jso.pop("args", {}),
            states,
        )


    def bind(self, run, jobs):
        job = jobs[self.job_id]
        bind_args = get_bind_args(run)
        args = _bind(job, self.args, run.inst.args, bind_args)
        return type(self)(self.job_id, args, self.states)


    # FIXME: Handle exceptions when checking.

    def check_runs(self, run, run_store):
        _, deps = run_store.query(
            job_id=self.job_id, args=self.args, state=self.states)
        deps = iter(deps)
        try:
            dep = next(deps)
        except StopIteration:
            inst = Instance(self.job_id, self.args)
            log.debug(f"dep not satisified: {inst}")
            return False
        else:
            log.debug(f"dep satisfied: {dep}")
            return True



