import asyncio
import ora
from   signal import Signals

from   apsis.lib.json import TypedJso, to_array, check_schema
from   apsis.lib.parse import parse_duration
from   apsis.lib.py import format_ctor
from   apsis.lib.sys import to_signal
from   apsis.states import State, to_state, reachable

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

class StopSchedule(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    # The schedule is called when the run is running.  These are the valid
    # states after which to schedule a stop.
    AFTERS = [
        "schedule",
        "waiting",
        "starting",
        "running",
    ]

    @classmethod
    def _get_run_time(cls, run, after):
        # Return the time for `after`, falling forward as needed.
        for a in cls.AFTERS[cls.AFTERS.index(after) :]:
            try:
                return ora.Time(run.times[a])
            except KeyError:
                pass
        else:
            raise RuntimeError(f"no {after} time for {run}")


    def __call__(self, run) -> ora.Time:
        """
        Returns the stop time of the run.
        """
        raise NotImplementedError("StopSchedule.__call__")



class DurationStopSchedule(StopSchedule):

    def __init__(self, duration, *, after="schedule"):
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = parse_duration(duration)
        after = str(after)
        if after not in self.AFTERS:
            names = " ".join( s.name for s in self.AFTERS )
            raise ValueError(f"after must be in {names}")

        self.duration   = duration
        self.after      = after


    def __eq__(self, other):
        return (
                other.duration == self.duration
            and other.after == self.after
        )


    def __repr__(self):
        return format_ctor(self, self.duration, after=self.after)


    def __str__(self):
        return f"stop after {self.duration} s after {self.after}"


    def to_jso(self):
        return {
            **super().to_jso(),
            "duration"  : self.duration,
            "after"     : self.after,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            duration    = pop("duration")
            after       = pop("after", str, "schedule")
        return cls(duration, after=after)


    def __call__(self, run):
        time = self._get_run_time(run, self.after)
        return time + self.duration



class DaytimeStopSchedule(StopSchedule):
    """
    Schedules to stop a run on the next occurrence of a daytime.
    """

    # FIXME: Add date_shift and cal_shift, as DailySchedule.

    def __init__(self, daytime, tz, *, after="schedule"):
        """
        Schedules to stop the run on the next occurrence of `daytime` in `tz`
        after the transition time for the state `after`.
        """
        daytime = ora.Daytime(daytime)
        tz      = ora.TimeZone(tz)
        after   = str(after)
        if after not in self.AFTERS:
            names = " ".join( s.name for s in self.AFTERS )
            raise ValueError(f"after must be in {names}")

        self.daytime    = daytime
        self.tz         = tz
        self.after      = after


    def __eq__(self, other):
        return (
                other.daytime == self.daytime
            and other.tz == self.tz
            and other.after == self.after
        )


    def __repr__(self):
        return format_ctor(self, self.daytime, self.tz, after=self.after)


    def __str__(self):
        return f"stop at {self.daytime} {self.tz} after {self.after}"


    def to_jso(self):
        return {
            **super().to_jso(),
            "daytime"   : str(self.daytime),
            "tz"        : str(self.tz),
            "after"     : self.after,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            daytime = pop("daytime", ora.Daytime)
            tz      = pop("tz", ora.TimeZone)
            after   = pop("after", str, "schedule")
        return cls(daytime, tz, after=after)


    def __call__(self, run):
        time = self._get_run_time(run, self.after)
        # FIXME: Handle invalid date/daytime pairs.
        date, daytime = time @ self.tz
        return (
            date if daytime < self.daytime else date + 1,
            self.daytime
        ) @ self.tz



StopSchedule.TYPE_NAMES.set(DurationStopSchedule, "duration")
StopSchedule.TYPE_NAMES.set(DaytimeStopSchedule, "daytime")

#-------------------------------------------------------------------------------

class Stop:

    def __init__(self, method, schedule):
        self.method     = method
        self.schedule   = schedule


    def __eq__(self, other):
        return (
                other.method    == self.method
            and other.schedule  == self.shedule
        )


    def __repr__(self):
        return format_ctor(self, self.method, self.schedule)


    def to_jso(self):
        return {
            "method"    : self.method.to_jso(),
            "schedule"  : self.schedule.to_jso(),
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            method      = pop("method", StopMethod.from_jso)
            schedule    = pop("schedule", StopSchedule.from_jso)
        return cls(method, schedule)



