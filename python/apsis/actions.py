import logging

from   . import runs
from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import tupleize

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class ScheduleAction:

    # FIXME: Add schedule.
    def __init__(self, instance):
        self.__inst = instance


    async def __call__(self, apsis, run):
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

        apsis.log_run_history(
            run.run_id, f"action: scheduled {inst} as {new_run.run_id}")
        apsis.log_run_history(
            new_run.run_id, f"action: scheduled by {run.run_id}")


    def to_jso(self):
        return {
            "job_id": self.__inst.job_id,
            "args": self.__inst.args,
        }


    @classmethod
    def from_jso(Class, jso):
        with no_unexpected_keys(jso):
            job_id = jso.pop("job_id")
            args = jso.pop("args", {})
        return Class(runs.Instance(job_id, args))



#-------------------------------------------------------------------------------

class Condition:

    def __init__(self, *, states=None):
        self.states = None if states is None else frozenset(states)


    def __call__(self, run):
        log.debug(f"check condition for run state {run.state}")
        return (
            self.states is None or run.state in self.states
        )



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


def condition_from_jso(jso):
    if jso is None:
        return None

    with no_unexpected_keys(jso):
        states = states_from_jso(jso.pop("states", None))
    return Condition(states=states)


def condition_to_jso(condition):
    if condition is None:
        return None

    return {
        "states": states_to_jso(condition.states),
    }


#-------------------------------------------------------------------------------

TYPES = Typed({
    "schedule": ScheduleAction,
})

class ActionRec:
    """
    An action record from a job specification.

    Includes the action, plus conditions on it.
    """

    def __init__(self, action, *, condition=None):
        self.action = action
        self.condition = condition


    async def __call__(self, apsis, run):
        if self.condition is None or self.condition(run):
            await self.action(apsis, run)



def action_from_jso(jso):
    with no_unexpected_keys(jso):
        action = TYPES.from_jso(jso)
        condition = condition_from_jso(jso.pop("condition", None))

    return ActionRec(action, condition=condition)


def action_to_jso(action):
    jso = TYPES.to_jso(action.action)
    jso["condition"] = condition_to_jso(action.condition)
    return jso


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
    return ActionRec(
        ScheduleAction(runs.Instance(job_id, args)),
        condition=Condition(states=[runs.Run.STATE.success])
    )


