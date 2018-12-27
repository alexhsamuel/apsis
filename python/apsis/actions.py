from   . import runs
from   .lib.json import Typed, no_unexpected_keys

#-------------------------------------------------------------------------------

class ScheduleAction:

    # FIXME: Add schedule.
    def __init__(self, instance):
        self.__inst = instance


    def __call__(self, apsis, run):
        inst = apsis._propagate_args(run.args, self.__inst)
        apsis.schedule(None, inst, expected=False)


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
        self.__states = None if states is None else frozenset(states)


    def __call__(self, run):
        return (
            self.__states is None or run.state in self.__states
        )



class Action:

    def __init__(self, action, *, condition=None):
        self.__action = action
        self.__condition = condition


    def __call__(self, run):
        if self.__condition is None or self.__condition(run):
            self.__action(run)



#-------------------------------------------------------------------------------

TYPES = Typed({
    "schedule": ScheduleAction,
})

def action_from_jso(jso):
    with no_unexpected_keys(jso):
        action = TYPES.from_jso(jso)
        # FIXME: Condition.
    return Action(action)


def action_to_jso(action):
    jso = TYPES.to_jso(action)
    # FIXME: Condition.
    return jso


