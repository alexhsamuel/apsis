import logging

from   . import runs
from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import or_none, tupleize

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

        log.info(f"schedule action for {run.run_id} scheduling {inst}")
        apsis.log_run_history(run.run_id, f"schedule action: scheduling {inst}")
        await apsis.schedule(None, runs.Run(inst))


    def to_jso(self):
        return {
            "job_id": self.__inst.job_id,
            "args": self.__inst.args,
        }


    @classmethod
    def from_jso(Class, jso):
        return Class(runs.Instance(jso.pop("job_id"), jso.pop("args")))



#-------------------------------------------------------------------------------

class Condition:

    def __init__(self, *, states=None):
        self.states = None if states is None else frozenset(states)


    def __call__(self, run):
        log.debug(f"check condition for run state {run.state}")
        return (
            self.states is None or run.state in self.states
        )



@or_none
def states_from_jso(jso):
    return [ runs.Run.STATE[s] for s in tupleize(jso) ]


@or_none
def states_to_jso(states):
    return [ s.name for s in states ]


@or_none
def condition_from_jso(jso):
    with no_unexpected_keys(jso):
        states = states_from_jso(jso.pop("states", None))

    return Condition(states=states)


@or_none
def condition_to_jso(condition):
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


