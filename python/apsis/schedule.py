import bisect
import ora
from   ora import Daytime, Time, TimeZone

from   . import lib
from   .lib.exc import SchemaError
from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import format_ctor

#-------------------------------------------------------------------------------

class DailySchedule:

    TYPE_NAME = "daily"

    def __init__(self, tz, calendar, daytimes, args):
        self.tz         = TimeZone(tz)
        self.calendar   = calendar
        self.daytimes   = tuple(sorted( Daytime(t) for t in daytimes ))
        self.args       = { str(k): str(v) for k, v in args.items() }


    def __str__(self):
        return "on {} at {} in {} for {}".format(
            self.calendar,
            " ".join( format(y, "%H:%M:%S") for y in self.daytimes ),
            self.tz,
            " ".join( "{}={}".format(k, v) for k, v in self.args.items() )
        )


    def __call__(self, start: Time):
        """
        Generates scheduled times starting not before `start`.
        """
        start = Time(start)

        start_date, start_daytime = start @ self.tz
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
        while True:
            yield (date, self.daytimes[i]) @ self.tz
            i += 1
            if i == len(self.daytimes):
                # On to the next day.
                date = self.calendar.after(date + 1)
                i = 0


    def bind_args(self, params, sched_time: Time):
        args = dict(self.args)

        # Bind temporal params from the schedule time.
        if "time" in params:
            # FIXME: Localize to TZ?  Or not?
            args["time"] = lib.format_time(sched_time)
        if "date" in params:
            args["date"] = str((sched_time @ self.tz).date)

        return args


    def to_jso(self):
        return {
            "tz"        : str(self.tz),
            "calendar"  : repr(self.calendar),  # FIXME
            "daytime"   : [ str(y) for y in self.daytimes ],
            "args"      : self.args,
        }


    @classmethod
    def from_jso(Class, jso):
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

        return Class(tz, calendar, daytimes, args)



#-------------------------------------------------------------------------------

class ExplicitSchedule:

    TYPE_NAME = "explicit"

    def __init__(self, times, args={}):
        self.__times = tuple(sorted( Time(t) for t in times ))
        self.__args = args


    def __str__(self):
        return ",".join( str(t) for t in self.__times )


    def __call__(self, start: Time):
        i = bisect.bisect_left(self.__times, start)
        return iter(self.__times[i :])


    def bind_args(self, params, sched_time: Time):
        args = dict(self.__args)
        if "time" in params:
            args["time"] = lib.format_time(sched_time)
        return args


    def to_jso(self):
        return {
            "times" : [ str(t) for t in self.__times ],
            "args"  : self.__args,
        }


    @classmethod
    def from_jso(Class, jso):
        try:
            times = jso.pop("times")
        except KeyError:
            raise SchemaError("missing times")
        times = times if isinstance(times, list) else [times]
        times = [ Time(t) for t in times ]

        args = jso.pop("args", {})

        return Class(times, args)



#-------------------------------------------------------------------------------

class IntervalSchedule:

    TYPE_NAME = "interval"

    def __init__(self, interval, args):
        self.__interval = float(interval)
        self.__args     = { str(k): str(v) for k, v in args.items() }


    def __repr__(self):
        return format_ctor(self, self.__interval, self.__args)


    def __str__(self):
        return f"every {self.__interval} sec"


    def __call__(self, start: Time):
        # Round to the next interval.
        off = start - Time.EPOCH
        time = (
            start if off % self.__interval == 0 
            else Time.EPOCH + (off // self.__interval + 1) * self.__interval
        )

        while True:
            yield time
            time += self.__interval


    def bind_args(self, params, sched_time: Time):
        args = dict(self.__args)
        if "time" in params:
            args["time"] = lib.format_time(sched_time)
        return args


    def to_jso(self):
        return {
            "interval"  : self.__interval,
            "args"      : self.__args,
        }


    @classmethod
    def from_jso(Class, jso):
        try:
            interval = jso.pop("interval")
        except KeyError:
            raise SchemaError("missing interval")
        interval = float(interval)

        args = jso.pop("args", {})

        return Class(interval, args)



#-------------------------------------------------------------------------------

TYPES = Typed(
    {
        "daily"     : DailySchedule,
        "explicit"  : ExplicitSchedule,
        "interval"  : IntervalSchedule,
    }, 
    default=DailySchedule
)


def schedule_to_jso(schedule):
    jso = TYPES.to_jso(schedule)
    jso["enabled"] = schedule.enabled
    return jso


def schedule_from_jso(jso):
    with no_unexpected_keys(jso):
        schedule = TYPES.from_jso(jso)
        schedule.enabled = jso.pop("enabled", True)
    return schedule


