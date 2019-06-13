import logging

from   . import runs
from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import tupleize

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Condition:

    def __init__(self, *, states=None):
        self.states = None if states is None else frozenset(states)


    def __call__(self, run):
        log.debug(f"check condition for run state {run.state}")
        return (
            self.states is None or run.state in self.states
        )


    @classmethod
    def from_jso(Class, jso):
        if jso is None:
            return None

        with no_unexpected_keys(jso):
            states = states_from_jso(jso.pop("states", None))
        return Class(states=states)


    def to_jso(self):
        return None if self is None else {
            "states": states_to_jso(self.states),
        }



def states_from_jso(jso):
    return (
        None if jso is None
        else tuple( runs.Run.STATE[s] for s in tupleize(jso) )
    )


def states_to_jso(states):
    return (
        None if states is None
        else [ s.name for s in states ]
    )


#-------------------------------------------------------------------------------

class ScheduleAction:

    # FIXME: Add schedule.
    def __init__(self, instance, *, condition=None):
        self.__inst = instance
        self.__condition = condition


    async def __call__(self, apsis, run):
        if self.__condition is not None and not self.__condition(run):
            return

        # Expand args templates.
        args = { 
            n: runs.template_expand(v, run.inst.args)
            for n, v in self.__inst.args.items()
        }
        inst = runs.Instance(self.__inst.job_id, args)
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
            "job_id": self.__inst.job_id,
            "args": self.__inst.args,
            "condition": self.__condition.to_jso()
        }


    @classmethod
    def from_jso(Class, jso):
        with no_unexpected_keys(jso):
            job_id = jso.pop("job_id")
            args = jso.pop("args", {})
            condition = Condition.from_jso(jso.pop("if", None))
        return Class(runs.Instance(job_id, args), condition=condition)



#-------------------------------------------------------------------------------

TYPES = Typed({
    "schedule": ScheduleAction,
})

def action_from_jso(jso):
    with no_unexpected_keys(jso):
        return TYPES.from_jso(jso)


action_to_jso = TYPES.to_jso


def successor_from_jso(jso):
    """
    Convert successors from JSO.

    Successors are syntactic sugar for and are converted into `ScheduleAction`
    records.
    """
    if isinstance(jso, str):
        jso = {"job_id": jso}

    with no_unexpected_keys(jso):
        job_id = jso.pop("job_id")
        args = jso.pop("args", {})
    return ScheduleAction(
        runs.Instance(job_id, args),
        condition=Condition(states=[runs.Run.STATE.success])
    )


