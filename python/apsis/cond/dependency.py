import logging

from   apsis.lib.json import check_schema
from   apsis.lib.py import format_ctor, iterize
from   apsis.runs import Instance, get_bind_args
from   apsis.states import State, reachable
from   .base import RunStoreCondition, _bind

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

def join_states(states):
    return "|".join( s.name for s in sorted(states, key=lambda s: s.value) )


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
            assert len(set(states) - set(exist)) == 0

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
        states = join_states(self.states)
        exist = (
            "" if self.exist is None
            else ", must exist as " + join_states(self.exist)
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
        with check_schema(jso) as pop:
            states = pop("states", default="success")
            states = { State[s] for s in iterize(states) }
            exist = pop("exist", default=None)
            if exist is True:
                # Require the existence of a run in any state from which one of
                # the target states is reachable.
                exist = { s for s in State if reachable(s) & states }
            elif exist is not None:
                exist = { State[s] for s in iterize(exist) }
            return cls(
                pop("job_id"),
                pop("args", default={}),
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
        ) as sub:
            while True:
                if self.exist is not None:
                    # First check whether a valid dependency run exists, in one
                    # of the exist states.
                    _, exist_runs = run_store.query(
                        job_id  =self.job_id,
                        args    =self.args,
                        state   =self.exist,
                    )
                    if len(exist_runs) == 0:
                        # No dependency run exists in a valid starting state.
                        inst = Instance(self.job_id, self.args)
                        exst = join_states(self.exist)
                        return self.Transition(
                            State.error,
                            f"no dependency {inst} exists in {exst}"
                        )

                # Wait for something to happen.
                _, run = await anext(sub)
                # Is the run in any of the target states?
                if run.state in self.states:
                    assert run.inst.job_id == self.job_id
                    assert all( run.inst.args[k] == v for k, v in self.args.items() )
                    assert run.state in self.states

                    log.debug(f"dependency satisfied: {run}")
                    return True



