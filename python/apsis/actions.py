import asyncio
import concurrent.futures
import logging

from   . import runs
from   .lib.json import TypedJso, check_schema
from   .lib.py import tupleize, format_ctor

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


    def __repr__(self):
        return format_ctor(self, states=self.states)


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
    """
    Abstract base action to perform when a run has transitioned to a new state.
    """

    TYPE_NAMES = TypedJso.TypeNames()

    async def __call__(self, apsis, run):
        """
        Performs the action on `run`.

        An implementation must be properly async, i.e. should not block the
        event loop for substantial periods of time.
        """
        raise NotImplementedError("Action.__call__")



#-------------------------------------------------------------------------------

class ThreadAction(Action):
    """
    Abstract base action that is invoked in a thread.

    An implementation should provide `run()`, which may perform blocking
    activities.  The implementation must take care not to access any global
    resources that aren't properly threadsafe, including all resources used by
    Apsis.  Logging is threadsafe, however.  The Apsis instance is not available
    to `run()`.
    """

    def __init__(self, *, condition=None):
        self.__condition = condition


    def __repr__(self):
        return format_ctor(self, condition=self.__condition)


    @property
    def condition(self):
        return self.__condition


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            condition = pop("condition", Condition.from_jso, None)
        return cls(condition=condition)


    def to_jso(self):
        jso = super().to_jso()
        if self.__condition is not None:
            jso["condition"] = self.__condition.to_jso()
        return jso


    def run(self, run):
        raise NotImplementedError("ThreadAction.run")


    async def __call__(self, apsis, run):
        if self.__condition and not self.__condition(run):
            return

        if self.__condition is None or self.__condition(run):
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exe:
                log.debug(f"thread action start: {self}")
                await loop.run_in_executor(exe, self.run, run)
                log.debug(f"thread action done: {self}")



class SleepThreadAction(ThreadAction):
    """
    Action that (blocking) sleeps; for testing.
    """

    def __init__(self, duration, *, condition=None):
        super().__init__(condition=condition)
        self.__duration = duration


    def __repr__(self):
        return format_ctor(self, self.__duration, condition=self.condition)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            condition   = pop("condition", Condition.from_jso, None)
            duration    = pop("duration", float)
        return cls(duration, condition=condition)


    def to_jso(self):
        return {
            **super().to_jso(),
            "duration"  : self.__duration,
        }


    def run(self, run):
        import time

        # Blocking actions are OK here.
        log.info(f"sleeping action for {self.__duration} s")
        time.sleep(self.__duration)
        log.info("sleeping action done")



class ErrorThreadAction(ThreadAction):
    """
    Thread action that raises an exception; for testing.
    """

    def run(self, run):
        log.info("error action")
        raise RuntimeError("something went wrong")



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

        apsis.run_log.info(
            run, f"action scheduling {inst} as {new_run.run_id}")
        apsis.run_log.info(
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


