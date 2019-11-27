import bisect
import logging
import ora
from   ora import Daytime, Time, TimeZone

from   .lib.exc import SchemaError
from   .lib.json import TypedJso
from   .lib.py import format_ctor

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Schedule(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    def __init__(self, *, enabled=True):
        self.enabled = bool(enabled)


    def __call__(self, start: Time):
        raise NotImplementedError



class DailySchedule(Schedule):

    TYPE_NAME = "daily"

    def __init__(
            self, tz, calendar, daytimes, args, *, enabled=True, date_shift=0):
        super().__init__(enabled=enabled)
        self.tz         = TimeZone(tz)
        self.calendar   = calendar
        self.daytimes   = tuple(sorted( Daytime(t) for t in daytimes ))
        self.args       = { str(k): str(v) for k, v in args.items() }
        self.date_shift = int(date_shift)


    def __str__(self):
        daytimes = ", ".join( format(y, "%C") for y in self.daytimes )
        res = f"{self.calendar} at {daytimes} {self.tz}"
        if len(self.args) > 0:
            args = ", ".join( f"{k}={v}" for k, v in self.args.items() )
            res = "(" + args + ") " + res
        return res


    def __call__(self, start: Time):
        """
        Generates scheduled times starting not before `start`.
        """
        start = Time(start)

        start_date, start_daytime = start @ self.tz
        start_date -= self.date_shift

        if start_date in self.calendar:
            date = start_date
            # Find the next daytime.
            for i, daytime in enumerate(self.daytimes):
                if start_daytime <= daytime:
                    break
            else:
                # All daytimes have passed for this date.
                date = self.calendar.after(date + 1)
                i = 0
        else:
            # Start at the beginning of the next date.
            date = self.calendar.after(start_date)
            i = 0

        # Now generate.
        common_args = {
            **self.args,
            "calendar": str(self.calendar),
            "tz": str(self.tz),
        }
        while True:
            sched_date = date + self.date_shift
            time = (sched_date, self.daytimes[i]) @ self.tz
            assert time >= start
            args = {**common_args, "date": str(date)}
            yield time, args

            i += 1
            if i == len(self.daytimes):
                # On to the next day.
                date = self.calendar.after(date + 1)
                i = 0


    def to_jso(self):
        return {
            **super().to_jso(),
            "enabled"   : self.enabled,
            "tz"        : str(self.tz),
            "calendar"  : repr(self.calendar),  # FIXME
            "daytime"   : [ str(y) for y in self.daytimes ],
            "date_shift": self.date_shift,
            "args"      : self.args,
        }


    @classmethod
    def from_jso(cls, jso):
        enabled = jso.pop("enabled", True)

        args = jso.pop("args", {})

        try:
            tz = jso.pop("tz")
        except KeyError:
            raise SchemaError("missing time zone")
        tz = TimeZone(tz)

        calendar = ora.get_calendar(jso.pop("calendar", "all"))

        try:
            daytimes = jso.pop("daytime")
        except KeyError:
            raise SchemaError("missing daytime")
        daytimes = [daytimes] if isinstance(daytimes, (str, int)) else daytimes
        daytimes = [ Daytime(d) for d in daytimes ]

        date_shift = jso.pop("date_shift", 0)

        return cls(
            tz, calendar, daytimes, args, 
            enabled=enabled, date_shift=date_shift
        )



#-------------------------------------------------------------------------------

class ExplicitSchedule(Schedule):

    def __init__(self, times, args={}, *, enabled=True):
        super().__init__(enabled=enabled)
        self.times = tuple(sorted( Time(t) for t in times) )
        self.args = args


    def __str__(self):
        res = ",".join( str(t) for t in self.times )
        if len(self.args) > 0:
            args = ", ".join( f"{k}={v}" for k, v in self.args.items() )
            res = "(" + args + ") " + res
        return res


    def __call__(self, start: Time):
        i = bisect.bisect_left(self.times, start)
        return ( (t, self.args) for t in self.times[i:] )


    def to_jso(self):
        return {
            **super().to_jso(),
            "enabled"   : self.enabled,
            "times"     : [ str(t) for t in self.times ],
            "args"      : self.args,
        }


    @classmethod
    def from_jso(cls, jso):
        enabled = jso.pop("enabled", True)
        try:
            times = jso.pop("times")
        except KeyError:
            raise SchemaError("missing times")
        times = times if isinstance(times, list) else [times]
        times = [ Time(t) for t in times ]

        args = jso.pop("args", {})

        return cls(times, args, enabled=enabled)



#-------------------------------------------------------------------------------

class IntervalSchedule(Schedule):

    def __init__(self, interval, args, *, enabled=True, phase=0.0):
        super().__init__(enabled=enabled)
        self.interval   = float(interval)
        self.phase      = float(phase)
        self.args       = { str(k): str(v) for k, v in args.items() }

        assert 0 <= self.phase < self.interval


    def __repr__(self):
        return format_ctor(self, self.interval, self.args)


    def __str__(self):
        res = f"every {self.interval} sec"
        if len(self.args) > 0:
            args = ", ".join( f"{k}={v}" for k, v in self.args.items() )
            res = "(" + args + ") " + res
        return res


    def __call__(self, start: Time):
        # Round to the next interval.
        start -= self.phase
        off = start - Time.EPOCH
        time = (
            start if off % self.interval == 0
            else Time.EPOCH + (off // self.interval + 1) * self.interval
        ) + self.phase

        while True:
            yield time, self.args
            time += self.interval


    def to_jso(self):
        return {
            **super().to_jso(),
            "enabled"   : self.enabled,
            "interval"  : self.interval,
            "phase"     : self.phase,
            "args"      : self.args,
        }


    @classmethod
    def from_jso(cls, jso):
        enabled     = jso.pop("enabled", True)
        try:
            interval = jso.pop("interval")
        except KeyError:
            raise SchemaError("missing interval")
        interval    = float(interval)
        phase       = float(jso.pop("phase", 0))
        args        = jso.pop("args", {})

        if not (0 <= phase < interval):
            raise SchemaError("require 0 <= phase < interval")

        return cls(interval, args, enabled=enabled, phase=phase)



#-------------------------------------------------------------------------------

Schedule.TYPE_NAMES.set(DailySchedule, "daily")
Schedule.TYPE_NAMES.set(ExplicitSchedule, "explicit")
Schedule.TYPE_NAMES.set(IntervalSchedule, "interval")

