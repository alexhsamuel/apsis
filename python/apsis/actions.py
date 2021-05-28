import logging

from   . import runs
from   .lib.json import TypedJso, check_schema
from   .lib.py import tupleize

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

STATE = runs.Run.STATE
ALL_STATES = frozenset(STATE)

def states_from_jso(jso):
    return frozenset( runs.Run.STATE[s] for s in tupleize(jso) )


def states_to_jso(states):
    states = frozenset(states)
    return (
        None if states == ALL_STATES
        else [ s.name for s in states ]
    )


class Condition:

    def __init__(self, *, states=None):
        self.states = frozenset(states)


    def __call__(self, run):
        return run.state in self.states


    @classmethod
    def from_jso(cls, jso):
        if jso is None:
            return None
        with check_schema(jso) as pop:
            states = pop("states", states_from_jso, default=ALL_STATES)
        return cls(states=states)


    def to_jso(self):
        return None if self is None else {
            "states": states_to_jso(self.states),
        }



#-------------------------------------------------------------------------------

class Action(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    async def __call__(self, apsis, run):
        """
        Performs the action on `run`.
        """
        raise NotImplementedError



#-------------------------------------------------------------------------------

class ScheduleAction(Action):
    """
    Schedules a new run.
    """

    def __init__(self, instance, *, condition=None):
        self.job_id     = instance.job_id
        self.args       = instance.args
        self.condition  = condition


    async def __call__(self, apsis, run):
        if self.condition is not None and not self.condition(run):
            return

        # Expand args templates.
        args = { 
            n: runs.template_expand(v, run.inst.args)
            for n, v in self.args.items()
        }
        inst = runs.Instance(self.job_id, args)
        # Propagate missing args.
        inst = apsis._propagate_args(run.inst.args, inst)

        log.info(f"action for {run.run_id}: scheduling {inst}")
        new_run = await apsis.schedule(None, runs.Run(inst))
        log.info(f"action for {run.run_id}: scheduled {new_run.run_id}")

        apsis.run_history.info(
            run, f"action scheduling {inst} as {new_run.run_id}")
        apsis.run_history.info(
            new_run, f"scheduled by action of {run.run_id}")


    def to_jso(self):
        return {
            **super().to_jso(),
            "job_id"    : self.job_id,
            "args"      : self.args,
            "condition" : self.condition.to_jso()
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            job_id      = pop("job_id")
            args        = pop("args", default={})
            condition   = Condition.from_jso(pop("if", default=None))
        return cls(runs.Instance(job_id, args), condition=condition)



#-------------------------------------------------------------------------------

Action.TYPE_NAMES.set(ScheduleAction, "schedule")


def successor_from_jso(jso):
    """
    Convert successors from JSO.

    Successors are syntactic sugar for and are converted into `ScheduleAction`
    records.
    """
    if isinstance(jso, str):
        jso = {"job_id": jso}

    with check_schema(jso) as pop:
        job_id  = pop("job_id")
        args    = pop("args", default={})
    return ScheduleAction(
        runs.Instance(job_id, args),
        condition=Condition(states=[runs.Run.STATE.success])
    )


