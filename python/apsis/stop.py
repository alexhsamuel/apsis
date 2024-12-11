import asyncio
from   signal import Signals

from   apsis.actions import Action
from   apsis.cond import Condition
from   apsis.lib.json import TypedJso, to_array, check_schema
from   apsis.lib.sys import to_signal

#-------------------------------------------------------------------------------

class StopMethod(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    async def __call__(self, apsis, run):
        raise NotImplementedError("StopMethod.__call__")



class StopSignalMethod:
    """
    Stops a program by sending a signal.

    Sends `signal`, waits `timeout` seconds, then sends SIGKILL.
    """

    def __init__(self, signal=Signals.SIGTERM, timeout=60):
        self.signal     = to_signal(signal)
        self.timeout    = float(timeout)
        assert 0 <= self.timeout


    def __eq__(self, other):
        return other.signal == self.signal and other.timeout == self.timeout


    def __repr__(self):
        return format_ctor(self, signal=self.signal, timeout=self.timeout)


    def __str__(self):
        return f"signal {self.signal.name}"


    def to_jso(self):
        return {
            **super().to_jso(),
            "signal"    : self.signal.name,
            "timeout"   : self.timeout,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            signal      = pop("signal", to_signal, Signal.SIGTERM),
            timeout     = pop("timeout", float, 60),
            return cls(signal, timeout)


    async def __call__(self, apsis, run):
        await apsis.send_signal(run, self.signal)
        await asyncio.sleep(self.timeout)
        if not run.state.finished:
            await asyncio.send_signal(run, Signal.SIGKILL)



#-------------------------------------------------------------------------------

class Stop:

    def __init__(self, method, schedules=[], conds=[], actions=[]):
        self.method     = method
        self.schedules  = schedules
        self.conds      = conds
        self.actions    = actions


    def __eq__(self, other):
        return (
                other.method    == self.method
            and other.schedules == self.schedules
            and other.conds     == self.conds
            and other.actions   == self.actions
        )


    def __repr__(self):
        return format_ctor(
            self,
            method      =self.method,
            schedules   =self.schedules,
            conds       =self.conds,
            actions     =self.actions,
        )


    def to_jso(self):
        return {
            "method"    : self.method,
            "schedules" : [ s.to_jso() for s in self.schedules ],
            "conds"     : [ c.to_jso() for c in self.conds ],
            "actions"   : [ a.to_jso() for a in self.actions ],
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            method      = pop("method", StopMethod.from_jso)
            schedules   = pop("schedule", to_array, [])
            schedules   = [ StopSchedule.from_jso(s) for s in schedules ]
            conds       = pop("conds", to_array, [])
            conds       = [ Condition.from_jso(c) for c in conds ]
            actions     = pop("actions", to_array, [])
            actions     = [ Action.from_jso(a) for a in actions ]
            return cls(method, schedules, conds, actions)



