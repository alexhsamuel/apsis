import logging

from   apsis.lib.py import format_ctor, iterize
from   apsis.runs import Instance, get_bind_args
from   apsis.states import State, reachable
from   .base import RunStoreCondition, _bind

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Dependency(RunStoreCondition):
    """
    Waits for a run in a given state or states.
    """

    DEFAULT_STATE = { State.success }

    def __init__(
            self, job_id, args={},
            *,
            states  =DEFAULT_STATE,
            exist   =None,
    ):
        states = frozenset(iterize(states))
        assert all( isinstance(s, State) for s in states )
        if exist is not None:
            assert all( isinstance(s, State) for s in exist )
            assert len(set(exist) - set(states)) == 0

        self.job_id = job_id
        self.args   = args
        self.states = states
        self.exist  = exist


    def __repr__(self):
        return format_ctor(
            self,
            self.job_id, self.args,
            states  =self.states,
            exist   =self.exist,
        )


    def __str__(self):
        inst = Instance(self.job_id, self.args)
        states = "|".join( s.name for s in self.states )
        exist = (
            "" if self.exist is None
            else ", must exist as " + "|".join( s.name for s in self.exist )
        )
        return f"dependency {inst} is {states}{exist}"


    def to_jso(self):
        return {
            **super().to_jso(),
            "job_id": self.job_id,
            "args"  : self.args,
            "states": [ s.name for s in self.states ],
            "exist" : 
                None if self.exist is None
                else [ s.name for s in self.exist ],
        }


    @classmethod
    def from_jso(cls, jso):
        states = { State[s] for s in iterize(jso.pop("states", "success")) }
        exist = jso.pop("exist", None)
        if exist is True:
            # Require the existence of a run in any state from which one of the
            # target states is reachable.
            exist = { s for s in State if reachable(s) & states }
        elif exist is not None:
            exist = { State[s] for s in iterize(exist) }
        return cls(
            jso.pop("job_id"),
            jso.pop("args", {}),
            states  =states,
            exist   =exist,
        )


    def bind(self, run, jobs):
        job = jobs[self.job_id]
        bind_args = get_bind_args(run)
        args = _bind(job, self.args, run.inst.args, bind_args)
        return type(self)(
            self.job_id, args,
            states  =self.states,
            exist   =self.exist,
        )


    async def wait(self, run_store):
        with run_store.query_live(
                job_id  =self.job_id,
                args    =self.args,
        ) as queue:
            while True:
                if self.exist is not None:
                    # First check whether a valid dependency run exists, in one
                    # of the exist states.
                    exist_runs = run_store.query(
                        job_id  =self.job_id,
                        args    =self.args,
                        state   =self.exist,
                    )
                    if next(exist_runs, None) is None:
                        # No dependency run exists in a valid starting state.
                        inst = Instance(self.job_id, self.args)
                        exst = "|".join(self.exist)
                        return self.Transaction(
                            State.error,
                            f"no dependency {inst} in {exst}"
                        )

                # Wait for something to happen.  
                _, runs = await queue.get()
                # Is there a run in any of the target states?
                runs = ( r for r in runs if r.state in self.states )
                run = next(runs, None)
                if run is not None:
                    assert run.inst.job_id == self.job_id
                    assert all( run.inst.args[k] == v for k, v in self.args.items() )
                    assert run.state in self.states

                    log.debug(f"dependency satisfied: {run}")
                    return True



