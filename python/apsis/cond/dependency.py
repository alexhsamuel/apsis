import logging

from   apsis.lib.py import format_ctor, iterize
from   apsis.runs import Run, Instance, get_bind_args
from   .base import RunStoreCondition, _bind

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Dependency(RunStoreCondition):
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
        return f"dependency {inst} is {states}"


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


    async def wait(self, run_store):
        with run_store.query_live(
            job_id=self.job_id,
            args=self.args,
            state=self.states,
        ) as queue:
            _, (run, *_) = await queue.get()
        assert run.inst.job_id == self.job_id
        assert all( run.inst.args[k] == v for k, v in self.args.items() )
        assert run.state in self.states

        log.debug(f"dependency satisfied: {run}")
        return True



