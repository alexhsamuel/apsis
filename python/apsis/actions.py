import logging

from   . import runs
from   .lib.json import Typed, no_unexpected_keys

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class ScheduleAction:

    # FIXME: Add schedule.
    def __init__(self, instance):
        self.__inst = instance


    def __call__(self, apsis, run):
        inst = apsis._propagate_args(run.inst.args, self.__inst)
        apsis.log_run_history(run.run_id, f"schedule action: scheduling {inst}")
        # FIXME: This is async!
        apsis.schedule(None, inst)


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
        self.__states = (
            None if states is None
            else { runs.Run.STATE[s] for s in states }
        )


    def __call__(self, run):
        log.debug(f"check condition for run state {run.state}")
        return (
            self.__states is None or run.state in self.__states
        )



# FIXME: Naming.
class Action:

    def __init__(self, action, *, condition=None):
        self.__action = action
        self.__condition = condition


    @property
    def action(self):
        return self.__action


    def __call__(self, apsis, run):
        if self.__condition is None or self.__condition(run):
            self.__action(apsis, run)



#-------------------------------------------------------------------------------

TYPES = Typed({
    "schedule": ScheduleAction,
})

def action_from_jso(jso):
    with no_unexpected_keys(jso):
        action = TYPES.from_jso(jso)
        # FIXME: Condition.
        condition = Condition(states={"success"})
    return Action(action, condition=condition)


def action_to_jso(action):
    jso = TYPES.to_jso(action.action)
    # FIXME: Condition.
    return jso


